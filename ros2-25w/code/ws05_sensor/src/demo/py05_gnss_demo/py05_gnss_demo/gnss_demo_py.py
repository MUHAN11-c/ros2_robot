# -*- coding: utf-8 -*-
"""
    需求：GNSS 案例（Python实现）—— 订阅 NavSatFix，以首个有效坐标为原点组织 Path 发布。
"""
import math

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix


class Gnss2PathPy(Node):

    def __init__(self):
        super().__init__("gnss_node_py")
        self.get_logger().info("GNSS 案例节点创建!(python)")
        self.sub = self.create_subscription(NavSatFix, "fix", self.gnss_callback, 10)
        self.pub = self.create_publisher(Path, "gnss_path", 10)
        self.path = Path()
        self.path.header.frame_id = "map"
        self.has_origin = False
        self.origin_lat = 0.0
        self.origin_lon = 0.0

    def gnss_callback(self, fix):
        # 原点确定(以首个有效坐标为原点)；
        if not self.has_origin:
            if fix.status.status < 0 or abs(fix.latitude) < 1e-9:
                return
            self.origin_lat = fix.latitude
            self.origin_lon = fix.longitude
            self.has_origin = True
            self.get_logger().info("定位原点:(%.6f,%.6f)" % (self.origin_lat, self.origin_lon))
        # 经纬度 -> 平面坐标(米)，等距圆柱近似；
        dlat = fix.latitude - self.origin_lat
        dlon = fix.longitude - self.origin_lon
        x = dlon * 111319.49079327358 * math.cos(math.radians(self.origin_lat))
        y = dlat * 111319.49079327358
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        self.path.poses.append(pose)
        self.path.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(self.path)


def main():
    rclpy.init()
    rclpy.spin(Gnss2PathPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
