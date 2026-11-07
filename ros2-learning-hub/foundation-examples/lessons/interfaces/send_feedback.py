# 【中文教学注释】 foundation-examples/lessons/interfaces/send_feedback.py
# 输入输出：输入为 msg/srv/action 定义及生成配置；输出为两种语言可使用的类型和 wheel_feedback 测量。
# 执行顺序与边界：接口必须先生成并加载再导入；轮速单位 rad/s，Header 指定采样时刻与坐标系，gain 无量纲，valid 不能被缺省数值替代。
import rclpy
from rclpy.node import Node
from learning_interfaces.msg import Telemetry


class FeedbackSource(Node):
    def __init__(self):
        # 构造 Node 基类并确定节点名；后续相对话题/服务名由命名空间解析，重命名需与参数文件选择器对应。
        super().__init__('learning_feedback_source')
        # 创建指定消息类型和话题的发布端并持久保存；整数 QoS 是 KeepLast 历史深度，不是 Hz，真正发送由 publish 调用决定。
        self.publisher = self.create_publisher(Telemetry, 'wheel_feedback', 10)
        # 定时周期单位为秒，回调由执行器调度而非自动新建独占线程；使用节点时钟，仿真时间暂停可能影响触发。
        self.timer = self.create_timer(1.0, self.publish_sample)

    def publish_sample(self):
        message = Telemetry()
        # 取得节点当前 ROS 时刻并转换为 sec/nanosec 消息；use_sim_time 时来自 /clock，采样时刻应尽量靠近数据生成。
        message.header.stamp = self.get_clock().now().to_msg()
        # 坐标系名称是离散标识；它必须与数值实际表达的坐标系相符，改字符串不会完成坐标变换。
        message.header.frame_id = 'base_link'
        # 轮关节角速度单位 rad/s；正方向按本接口定义，不能直接当作底盘线速度 m/s。
        message.left_velocity_rad_s = 0.7
        message.right_velocity_rad_s = 0.5
        message.valid = True
        # 提交已填好的消息给 ROS 发布端；这不是业务处理完成确认，端到端接收仍取决于发现、类型、QoS 和执行器。
        self.publisher.publish(message)


# 程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。
def main():
    # 初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。
    rclpy.init()
    node = FeedbackSource()
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
