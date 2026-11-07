# 【中文教学注释】 foundation-examples/lessons/services/server.py
# 输入输出：输入为 AddTwoInts 请求中的两个小整数；输出为 sum 响应和成功/失败退出码，无物理单位。
# 执行顺序与边界：先发现服务再发请求；Future 返回不等于响应已完成，等待超时不会撤销服务端已经发生的业务副作用。
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class SumServer(Node):
    def __init__(self):
        # 构造 Node 基类并确定节点名；后续相对话题/服务名由命名空间解析，重命名需与参数文件选择器对应。
        super().__init__('learning_sum_py')
        # 创建服务端并保存句柄；收到请求后执行回调，需返回填好的 Response，服务发现与请求执行是不同阶段。
        self.service = self.create_service(AddTwoInts, 'sum', self.on_request)

    def on_request(self, request, response):
        response.sum = request.a + request.b
        # 输出可观测日志用于核对状态；日志成功写出不等于对端收到消息或任务执行成功。
        self.get_logger().info('request handled')
        return response


# 程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。
def main():
    # 初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。
    rclpy.init()
    node = SumServer()
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
