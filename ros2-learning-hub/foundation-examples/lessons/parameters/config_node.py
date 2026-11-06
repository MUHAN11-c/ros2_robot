import math
import sys
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import Float64


class ConfigNode(Node):
    def __init__(self):
        super().__init__('learning_config')
        initial = self.declare_parameter('gain', 1.0)
        initial_gain = initial.value
        self.declare_parameter('enabled', True)
        if initial.type_ != Parameter.Type.DOUBLE or not self.valid_gain(initial_gain):
            raise ValueError('gain must be finite and within [0, 2]')
        self.add_on_set_parameters_callback(self.validate)
        self.publisher = self.create_publisher(Float64, 'configured_value', 10)
        self.timer = self.create_timer(1.0, self.tick)

    @staticmethod
    def valid_gain(value):
        return math.isfinite(value) and 0.0 <= value <= 2.0

    def validate(self, parameters):
        for parameter in parameters:
            if parameter.name == 'gain':
                if parameter.type_ != Parameter.Type.DOUBLE or not self.valid_gain(parameter.value):
                    return SetParametersResult(
                        successful=False,
                        reason='gain must be a finite double within [0, 2]')
        return SetParametersResult(successful=True)

    def tick(self):
        message = Float64()
        enabled = self.get_parameter('enabled').value
        message.data = 0.2 * self.get_parameter('gain').value if enabled else 0.0
        self.publisher.publish(message)
        self.get_logger().info(f'value={message.data:.3f}')


def main():
    rclpy.init()
    node = None
    exit_code = 0
    try:
        node = ConfigNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f'configuration failed: {error}', file=sys.stderr)
        exit_code = 1
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
