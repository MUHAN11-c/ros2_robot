# SPDX-License-Identifier: Apache-2.0
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    def __init__(self):
        super().__init__('atlas_talker_py')
        self.publisher = self.create_publisher(String, 'chatter', 10)
        self.count = 0
        self.timer = self.create_timer(0.25, self.publish_message)

    def publish_message(self):
        message = String()
        message.data = f'ATLAS_MESSAGE python {self.count}'
        self.count += 1
        self.publisher.publish(message)
        self.get_logger().info(f'SENT {message.data}')


def main(args=None):
    rclpy.init(args=args)
    node = Talker()
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
