# 【中文教学注释】 foundation-examples/src/learning_topic_py/learning_topic_py/talker.py
# 输入输出：输入为定时触发或收到的 String 消息；输出为带序号的消息及接收日志，序号无量纲。
# 执行顺序与边界：初始化→创建并持有节点/端点→spin 分发回调→清理；历史深度 10 不是 10 Hz，定时周期以秒或毫秒单独指定。
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class LearningTalker(Node):
    def __init__(self):
        # 构造 Node 基类并确定节点名；后续相对话题/服务名由命名空间解析，重命名需与参数文件选择器对应。
        super().__init__('learning_talker_py')
        # 创建指定消息类型和话题的发布端并持久保存；整数 QoS 是 KeepLast 历史深度，不是 Hz，真正发送由 publish 调用决定。
        self.publisher = self.create_publisher(String, 'telemetry', 10)
        self.sequence = 0
        # 定时周期单位为秒，回调由执行器调度而非自动新建独占线程；使用节点时钟，仿真时间暂停可能影响触发。
        self.timer = self.create_timer(0.5, self.on_tick)

    def on_tick(self):
        message = String()
        message.data = f'py sample={self.sequence}'
        self.sequence += 1
        # 提交已填好的消息给 ROS 发布端；这不是业务处理完成确认，端到端接收仍取决于发现、类型、QoS 和执行器。
        self.publisher.publish(message)
        # 输出可观测日志用于核对状态；日志成功写出不等于对端收到消息或任务执行成功。
        self.get_logger().info(message.data)


# 程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。
def main(args=None):
    # 初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。
    rclpy.init(args=args)
    node = LearningTalker()
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
