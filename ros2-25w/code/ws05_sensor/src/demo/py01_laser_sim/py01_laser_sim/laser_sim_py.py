# -*- coding: utf-8 -*-
"""
    需求：单线激光雷达仿真（Python实现）—— 周期性组织并发布 LaserScan 消息。
"""
import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class LaserSimPy(Node):

    def __init__(self):
        super().__init__("laser_sim_node_py")
        self.get_logger().info("单线激光雷达仿真节点创建!(python)")
        self.pub = self.create_publisher(LaserScan, "scan", 10)
        self.timer = self.create_timer(0.1, self.on_timer)

    def on_timer(self):
        scan = LaserScan()
        scan.header.frame_id = "laser"
        scan.header.stamp = self.get_clock().now().to_msg()
        # 组织点云基本参数；
        scan.angle_min = -math.pi
        scan.angle_max = math.pi
        scan.angle_increment = math.pi / 180.0
        scan.time_increment = 0.0
        scan.scan_time = 0.1
        scan.range_min = 0.15
        scan.range_max = 12.0
        count = int((scan.angle_max - scan.angle_min) / scan.angle_increment)
        # 设置扫描点参数：正前方 2m 障碍物；
        distance = 2.0 + 0.2 * math.sin(self.get_clock().now().nanoseconds / 1e9)
        scan.ranges = [distance if abs(scan.angle_min + i * scan.angle_increment) < 0.05 else float("inf") for i in range(count)]
        scan.intensities = [100.0 if r != float("inf") else 0.0 for r in scan.ranges]
        self.pub.publish(scan)


def main():
    rclpy.init()
    rclpy.spin(LaserSimPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
