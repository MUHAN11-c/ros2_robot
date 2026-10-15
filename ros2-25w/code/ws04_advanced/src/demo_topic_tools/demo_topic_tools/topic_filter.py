# -*- coding: utf-8 -*-
"""
    需求：话题内容过滤(Python实现) —— 只接收满足条件的话题消息。
    说明：Humble 的 rclpy 暂未开放 ContentFilterOptions，
          此处以软件过滤器演示"话题内容过滤"效果。
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TopicFilter(Node):

    def __init__(self):
        super().__init__("topic_filter_node_py")
        self.get_logger().info("话题内容过滤节点创建!(python)")
        # 1.订阅话题；
        self.sub = self.create_subscription(String, "chatter", self.on_msg, 10)

    def on_msg(self, msg):
        # 2.过滤：只处理包含 "world" 的消息；
        if "world" in msg.data:
            self.get_logger().info("通过过滤，收到:%s" % msg.data)


def main():
    rclpy.init()
    rclpy.spin(TopicFilter())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
