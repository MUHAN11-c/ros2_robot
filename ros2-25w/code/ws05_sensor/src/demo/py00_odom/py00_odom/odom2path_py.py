# -*- coding: utf-8 -*-
"""
    需求：订阅机器人的里程计消息，生成并发布路径（Path）消息（Python实现）。
    流程：当前坐标点与轨迹末点距离大于 0.5 米时才追加（首点直接入轨迹）。
"""
import math

import rclpy
from geometry_msgs.msg import PoseStamped
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
        # 1.获取当前坐标点与轨迹中最后一个坐标点的距离数据；
        x = odom.pose.pose.position.x
        y = odom.pose.pose.position.y
        if self.path.poses:
            last_x = self.path.poses[-1].pose.position.x
            last_y = self.path.poses[-1].pose.position.y
            distance = math.sqrt((x - last_x) ** 2 + (y - last_y) ** 2)
        else:
            distance = float("inf")           # 首点直接入轨迹
        # 2.距离大于 0.5 米，才将当前坐标点添加进轨迹；
        if distance > 0.5:
            ps = PoseStamped()
            ps.header.frame_id = "odom"
            ps.header.stamp = odom.header.stamp
            ps.pose = odom.pose.pose
            self.path.poses.append(ps)
            self.get_logger().info(
                "轨迹点入轨(%.2f,%.2f)，累计 %d 个点" %
                (ps.pose.position.x, ps.pose.position.y, len(self.path.poses)))
            # 3.发布轨迹消息；
            self.path.header.stamp = self.get_clock().now().to_msg()
            self.pub.publish(self.path)


def main():
    rclpy.init()
    rclpy.spin(Odom2PathPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
