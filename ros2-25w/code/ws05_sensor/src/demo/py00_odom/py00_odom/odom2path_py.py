# -*- coding: utf-8 -*-
"""
    需求：订阅机器人的里程计消息，生成并发布路径（Path）消息（Python实现）。
"""
import rclpy
from nav_msgs.msg import Odometry, Path
from rclpy.node import Node


class Odom2PathPy(Node):

    def __init__(self):
        super().__init__("odom2path_node_py")
        self.get_logger().info("odom2path 节点创建!(python)")
        # 1.订阅里程计消息；
        self.sub = self.create_subscription(Odometry, "odom", self.odom_callback, 10)
        # 2.发布轨迹消息；
        self.pub = self.create_publisher(Path, "path", 10)
        self.path = Path()
        self.path.header.frame_id = "odom"

    def odom_callback(self, odom):
        # 将当前位姿追加到轨迹；
        self.path.poses.append(odom.pose.pose)
        # 发布轨迹消息；
        self.path.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(self.path)


def main():
    rclpy.init()
    rclpy.spin(Odom2PathPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
