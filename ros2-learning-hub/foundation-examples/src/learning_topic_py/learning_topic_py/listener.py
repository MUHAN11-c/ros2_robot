import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class LearningListener(Node):
    def __init__(self):
        super().__init__('learning_listener_py')
        self.subscription = self.create_subscription(
            String, 'telemetry', self.on_message, 10)

    def on_message(self, message):
        self.get_logger().info(f'received: {message.data}')


def main(args=None):
    rclpy.init(args=args)
    node = LearningListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
