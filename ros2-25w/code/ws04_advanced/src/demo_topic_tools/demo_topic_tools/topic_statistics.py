# -*- coding: utf-8 -*-
"""
    需求：话题统计(Python实现) —— 订阅话题并周期性输出接收消息频率统计。
    说明：Humble 的 rclpy 暂未内置 libstatistics_collector 封装，
          此处演示基于滑动窗口的简易频率统计，与课程演示效果一致。
"""
import collections
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TopicStatistics(Node):

    def __init__(self):
        super().__init__("topic_statistics_node_py")
        self.get_logger().info("话题统计节点创建!(python)")
        # 1.订阅话题；
        self.sub = self.create_subscription(String, "chatter", self.on_msg, 10)
        # 2.滑动窗口记录消息到达时刻；
        self.arrivals = collections.deque()
        # 3.周期性输出统计结果；
        self.timer = self.create_timer(1.0, self.on_timer)

    def on_msg(self, msg):
        now = time.monotonic()
        self.arrivals.append(now)

    def on_timer(self):
        now = time.monotonic()
        while self.arrivals and now - self.arrivals[0] > 5.0:
            self.arrivals.popleft()
        # 频率 = 窗口内消息数 / 窗口时长；
        hz = len(self.arrivals) / 5.0 if self.arrivals else 0.0
        self.get_logger().info("近5s统计: %d 条消息, 平均频率 %.2f Hz" % (len(self.arrivals), hz))


def main():
    rclpy.init()
    rclpy.spin(TopicStatistics())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
