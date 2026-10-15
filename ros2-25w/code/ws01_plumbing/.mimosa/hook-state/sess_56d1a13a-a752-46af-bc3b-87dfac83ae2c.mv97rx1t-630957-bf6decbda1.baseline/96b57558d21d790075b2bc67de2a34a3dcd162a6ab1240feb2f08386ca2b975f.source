# -*- coding: utf-8 -*-
"""
    需求：以某个固定频率发送文本"hello world!"，文本后缀编号，每发送一条消息，编号递增1。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建消息发布方；
            3-2.创建定时器；
            3-3.组织并发布消息。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


# 3.自定义节点类；
class MinimalPublisher(Node):

    def __init__(self):
        super().__init__('talker_node_py')
        self.get_logger().info('发布节点创建!(python)')
        # 3-1.创建消息发布方；
        self.publisher_ = self.create_publisher(String, 'chatter', 10)
        # 3-2.创建定时器；
        timer_period = 1.0
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.i = 0

    # 3-3.组织并发布消息；
    def timer_callback(self):
        msg = String()
        msg.data = 'hello world!%d' % self.i
        self.get_logger().info('发布方发布的消息:%s' % msg.data)
        self.publisher_.publish(msg)
        self.i += 1


def main():
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    # 4.调用spin函数，并传入节点对象；
    rclpy.spin(MinimalPublisher())
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
