# 【中文教学注释】 foundation-examples/lessons/actions/server.py
# 输入输出：输入为 Count 目标 target 或取消请求；输出为 current 反馈、completed 结果及终态，计数无量纲。
# 执行顺序与边界：服务端接受 1..20 且同一时刻只运行一个目标；每步约 0.5 秒。取消请求被接受与任务已取消是两个事件，共享 busy 状态按线程模型保护。
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from learning_count_interfaces.action import Count


class CountServer(Node):
    def __init__(self):
        # 构造 Node 基类并确定节点名；后续相对话题/服务名由命名空间解析，重命名需与参数文件选择器对应。
        super().__init__('learning_count_py')
        # 为目标接纳与任务完成共享的状态建立互斥锁；锁内只做短操作，不在持锁时长时间执行任务。
        self.lock = threading.Lock()
        self.busy = False
        # 允许该组回调重入/并发；它不自动保护 busy 等共享变量，必须另用锁或状态机。
        self.group = ReentrantCallbackGroup()
        # 建立动作服务端，分别接线目标接纳、执行和取消回调；这些阶段不能混作一次普通服务调用。
        self.server = ActionServer(
            self, Count, 'count', self.execute,
            goal_callback=self.on_goal,
            cancel_callback=self.on_cancel,
            callback_group=self.group)

    def on_goal(self, goal):
        # 原子检查并更新忙闲标志，防止并发目标同时被接受；离开 with 后自动释放锁。
        with self.lock:
            if self.busy or not 1 <= goal.target <= 20:
                return GoalResponse.REJECT
            self.busy = True
        return GoalResponse.ACCEPT

    def on_cancel(self, goal_handle):
        return CancelResponse.ACCEPT

    def execute(self, goal_handle):
        result = Count.Result()
        try:
            for current in range(1, goal_handle.request.target + 1):
                # 检查 ROS 上下文仍有效，避免退出流程重复 shutdown；它不表示节点业务健康。
                if not rclpy.ok():
                    return result
                # 按秒阻塞当前工作线程；本例只模拟耗时，不保证实时周期，动作服务器需要其他可运行线程处理取消。
                time.sleep(0.5)
                # 检查任务取消标志，并在任务自身的可中断边界主动退出；仅接收请求不会自动终止耗时业务。
                if goal_handle.is_cancel_requested:
                    # 将目标置为已取消终态；执行回调还须返回当前 Result，不能随后再调用 succeed。
                    goal_handle.canceled()
                    return result
                result.completed = current
                feedback = Count.Feedback()
                feedback.current = current
                # 发布中间进度而不结束目标；current 是无量纲计数，反馈不等于最终结果。
                goal_handle.publish_feedback(feedback)
            # 只在业务达到成功条件后设置 SUCCEEDED；Python 动作回调仍须返回 Result 对象。
            goal_handle.succeed()
            return result
        finally:
            with self.lock:
                self.busy = False


# 程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。
def main():
    # 初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。
    rclpy.init()
    node = CountServer()
    # 创建给定 num_threads 的执行器工作线程；并发还受回调组、共享状态锁以及 Python GIL 影响。
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        # 进入执行器事件循环，定时器、订阅、服务和 Future 回调在这里才被推进；通常阻塞到中断或上下文关闭。
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        # 先停止执行器并等待其工作回调结束，再销毁节点；避免回调继续访问已释放对象。
        executor.shutdown()
        # 显式释放节点所属端点与定时器；应在相关执行器不再访问节点后执行。
        node.destroy_node()
        if rclpy.ok():
            # 关闭本进程 ROS 上下文；先停止执行器、销毁端点/节点，再在上下文仍有效时调用。
            rclpy.shutdown()


if __name__ == '__main__':
    main()
