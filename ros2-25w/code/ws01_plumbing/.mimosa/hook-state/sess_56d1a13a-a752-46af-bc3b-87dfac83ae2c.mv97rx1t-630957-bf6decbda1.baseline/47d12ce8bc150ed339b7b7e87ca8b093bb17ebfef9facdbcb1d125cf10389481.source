# -*- coding: utf-8 -*-
"""
    需求：订阅发布方发布的消息，并输出到终端。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建订阅方；
            3-2.处理订阅到的消息。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


# 3.自定义节点类；
class MinimalSubscriber(Node):

    def __init__(self):
        super().__init__('listener_node_py')
        self.get_logger().info('订阅方创建!(python)')
        # 3-1.创建订阅方；
        self.subscription = self.create_subscription(
            String,
            'chatter',
            self.listener_callback,
            10)
        self.subscription

    # 3-2.处理订阅到的消息；
    def listener_callback(self, msg):
        self.get_logger().info("订阅的消息：'%s'" % msg.data)


def main():
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    # 4.调用spin函数，并传入节点对象；
    rclpy.spin(MinimalSubscriber())
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
