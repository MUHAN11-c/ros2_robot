import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class LearningTalker(Node):
    def __init__(self):
        super().__init__('learning_talker_py')
        self.publisher = self.create_publisher(String, 'telemetry', 10)
        self.sequence = 0
        self.timer = self.create_timer(0.5, self.on_tick)

    def on_tick(self):
        message = String()
        message.data = f'py sample={self.sequence}'
        self.sequence += 1
        self.publisher.publish(message)
        self.get_logger().info(message.data)


def main(args=None):
    rclpy.init(args=args)
    node = LearningTalker()
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
