# SPDX-License-Identifier: Apache-2.0
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):
    def __init__(self):
        super().__init__('atlas_listener_py')
        self.subscription = self.create_subscription(
            String, 'chatter', self.receive_message, 10)

    def receive_message(self, message):
        self.get_logger().info(f'RECEIVED {message.data}')


def main(args=None):
    rclpy.init(args=args)
    node = Listener()
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
