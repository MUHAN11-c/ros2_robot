import rclpy
from rclpy.node import Node
from learning_interfaces.msg import Telemetry


class FeedbackSource(Node):
    def __init__(self):
        super().__init__('learning_feedback_source')
        self.publisher = self.create_publisher(Telemetry, 'wheel_feedback', 10)
        self.timer = self.create_timer(1.0, self.publish_sample)

    def publish_sample(self):
        message = Telemetry()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = 'base_link'
        message.left_velocity_rad_s = 0.7
        message.right_velocity_rad_s = 0.5
        message.valid = True
        self.publisher.publish(message)


def main():
    rclpy.init()
    node = FeedbackSource()
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
