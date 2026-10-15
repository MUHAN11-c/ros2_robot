# -*- coding: utf-8 -*-
"""
    需求：多线激光雷达仿真（Python实现）—— 周期性组织并发布 PointCloud2 消息。
"""
import struct

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2


class PointCloudSimPy(Node):

    def __init__(self):
        super().__init__("pointcloud_sim_node_py")
        self.get_logger().info("多线激光雷达仿真节点创建!(python)")
        self.pub = self.create_publisher(PointCloud2, "point_cloud", 10)
        self.timer = self.create_timer(0.1, self.on_timer)

    def on_timer(self):
        # 组织点云数据：一圈 360 个点，半径 2m；
        import math
        radius = 2.0 + 0.2 * math.sin(self.get_clock().now().nanoseconds / 1e9)
        points = []
        for i in range(360):
            theta = math.radians(i)
            points.append((radius * math.cos(theta), radius * math.sin(theta), 0.0))
        cloud = point_cloud2.create_cloud_xyz32(
            self.get_clock().now().to_msg(), points)
        cloud.header.frame_id = "laser"
        self.pub.publish(cloud)


def main():
    rclpy.init()
    rclpy.spin(PointCloudSimPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
