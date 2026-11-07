# 【中文教学注释】 async_poll.py 完整脚本
# 本例作用：tick 的每条路径都快速返回，响应回调因此可以运行；done 只读完成状态，不阻塞。显式STEADY定时器负责检查节奏，monotonic计算请求年龄；执行器繁忙仍可能推迟检查，二秒是软期限。捕获结果异常是为了把服务失败与调度失败分开。
# 输入输出：输入为定时事件、异步服务 Future 和单调时钟；输出为轮询得到的响应或超时日志。
# 执行顺序与边界：0.2 秒回调只推进状态，不同步阻塞等待服务；2 秒请求超时用单调时钟，检查定时器使用STEADY时钟；移除待处理请求不取消远端业务，多线程仍受回调组与 Python GIL 约束。
import time
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts

class AsyncPoll(Node):
    def __init__(self):
        # 构造 Node 基类并确定节点名；后续相对话题/服务名由命名空间解析，重命名需与参数文件选择器对应。
        super().__init__('async_poll')
        # 创建服务客户端，接口类型和服务名须与服务端一致；此调用不保证服务已经发现。
        self.client = self.create_client(AddTwoInts, 'add_two_ints')
        self.pending = None
        self.sent_at = 0.0
        # 显式持有稳态时钟：即使use_sim_time启用而/clock停止，轮询节奏仍推进。
        # 0.2单位为秒；执行器必须继续spin，长回调/CPU饥饿仍会延迟检查。
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(0.2, self.tick, clock=self.steady_clock)

    def tick(self):
        if self.pending is not None:
            # 先检查 Future 是否已经结束；完成仍可能包含异常，需要与 result()/exception() 的错误处理配合。
            if self.pending.done():
                try:
                    # 提取已经完成的异步结果；可能抛出传输/服务异常，不能把未完成 Future 的结果当作有效 Response。
                    result = self.pending.result()
                    if result is None:
                        raise RuntimeError('service returned no response')
                    # 输出可观测日志用于核对状态；日志成功写出不等于对端收到消息或任务执行成功。
                    self.get_logger().info(f'sum={result.sum}')
                except Exception as error:
                    self.get_logger().error(str(error))
                self.pending = None
            # 读取只用于测量经过时长的单调时钟，单位 s；不会随 ROS 仿真时间暂停或回拨。
            elif time.monotonic() - self.sent_at > 2.0:
                # 从客户端本地待响应表移除此 Future；只回收本地跟踪，不撤销服务端可能正在执行的工作。
                self.client.remove_pending_request(self.pending)
                self.get_logger().warning('response timeout')
                self.pending = None
            return
        # 非阻塞检查服务是否已发现；未就绪时让当前回调尽快返回，避免阻塞其他事件。
        if not self.client.service_is_ready():
            return
        request = AddTwoInts.Request()
        request.a = 7
        request.b = 5
        self.sent_at = time.monotonic()
        # 提交请求并立即返回 Future；仍需执行器处理响应，保存 Future 才能关联完成、异常与超时。
        self.pending = self.client.call_async(request)

# 程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。
def main():
    # 初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。
    rclpy.init()
    node = AsyncPoll()
    try:
        # 进入执行器事件循环，定时器、订阅、服务和 Future 回调在这里才被推进；通常阻塞到中断或上下文关闭。
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 显式释放节点所属端点与定时器；应在相关执行器不再访问节点后执行。
        node.destroy_node()
        # 检查 ROS 上下文仍有效，避免退出流程重复 shutdown；它不表示节点业务健康。
        if rclpy.ok():
            # 关闭本进程 ROS 上下文；先停止执行器、销毁端点/节点，再在上下文仍有效时调用。
            rclpy.shutdown()

if __name__ == '__main__':
    main()
