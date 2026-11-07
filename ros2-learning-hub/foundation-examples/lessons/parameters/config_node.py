# 【中文教学注释】 foundation-examples/lessons/parameters/config_node.py
# 输入输出：输入为启动覆盖值或动态参数请求；输出为 gain/enabled 的验证结果和 configured_value。
# 执行顺序与边界：gain 为有限无量纲 double，范围 [0,2]；先验证启动值，再注册动态验证器。回调通过后才应提交配置，参数回调不能阻塞执行器。
import math
import sys
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import Float64


class ConfigNode(Node):
    def __init__(self):
        # 构造 Node 基类并确定节点名；后续相对话题/服务名由命名空间解析，重命名需与参数文件选择器对应。
        super().__init__('learning_config')
        # 声明参数的名称、类型/默认值，并接收启动覆盖值；默认值不等于最终生效值，启动值仍需检查范围。
        initial = self.declare_parameter('gain', 1.0)
        initial_gain = initial.value
        self.declare_parameter('enabled', True)
        if initial.type_ != Parameter.Type.DOUBLE or not self.valid_gain(initial_gain):
            raise ValueError('gain must be finite and within [0, 2]')
        # 注册参数提交前验证器；只判断本次请求是否合法，不在这里产生不可回滚的业务副作用。
        self.add_on_set_parameters_callback(self.validate)
        # 创建指定消息类型和话题的发布端并持久保存；整数 QoS 是 KeepLast 历史深度，不是 Hz，真正发送由 publish 调用决定。
        self.publisher = self.create_publisher(Float64, 'configured_value', 10)
        # 定时周期单位为秒，回调由执行器调度而非自动新建独占线程；使用节点时钟，仿真时间暂停可能影响触发。
        self.timer = self.create_timer(1.0, self.tick)

    @staticmethod
    def valid_gain(value):
        return math.isfinite(value) and 0.0 <= value <= 2.0

    # 先校验类型、字段集合与数值边界，再返回计划/参数验证结果；通过校验不表示环境或动作执行一定成功。
    def validate(self, parameters):
        for parameter in parameters:
            if parameter.name == 'gain':
                if parameter.type_ != Parameter.Type.DOUBLE or not self.valid_gain(parameter.value):
                    # 返回本次参数验证是否接受以及原因；successful=False 会拒绝相应更新，而非悄悄限幅改值。
                    return SetParametersResult(
                        successful=False,
                        reason='gain must be a finite double within [0, 2]')
        return SetParametersResult(successful=True)

    def tick(self):
        message = Float64()
        # 读取当前已提交参数；value 的 Python 类型必须与声明一致，动态更新后的值在后续业务回调生效。
        enabled = self.get_parameter('enabled').value
        message.data = 0.2 * self.get_parameter('gain').value if enabled else 0.0
        # 提交已填好的消息给 ROS 发布端；这不是业务处理完成确认，端到端接收仍取决于发现、类型、QoS 和执行器。
        self.publisher.publish(message)
        # 输出可观测日志用于核对状态；日志成功写出不等于对端收到消息或任务执行成功。
        self.get_logger().info(f'value={message.data:.3f}')


# 程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。
def main():
    # 初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。
    rclpy.init()
    node = None
    exit_code = 0
    try:
        node = ConfigNode()
        # 进入执行器事件循环，定时器、订阅、服务和 Future 回调在这里才被推进；通常阻塞到中断或上下文关闭。
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f'configuration failed: {error}', file=sys.stderr)
        exit_code = 1
    finally:
        if node is not None:
            # 显式释放节点所属端点与定时器；应在相关执行器不再访问节点后执行。
            node.destroy_node()
        # 检查 ROS 上下文仍有效，避免退出流程重复 shutdown；它不表示节点业务健康。
        if rclpy.ok():
            # 关闭本进程 ROS 上下文；先停止执行器、销毁端点/节点，再在上下文仍有效时调用。
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
