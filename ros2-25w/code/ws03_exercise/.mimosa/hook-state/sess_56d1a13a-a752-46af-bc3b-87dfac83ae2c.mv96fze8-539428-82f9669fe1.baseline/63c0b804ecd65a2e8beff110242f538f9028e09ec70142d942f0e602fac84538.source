# -*- coding: utf-8 -*-
# 激光雷达驱动占位节点：实体车由 rplidar_ros / ldlidar 驱动实现，此处仅打印日志。
import rclpy
from rclpy.node import Node


class LidarDriver(Node):

    def __init__(self):
        super().__init__("lidar_driver_node_py")
        self.get_logger().info("激光雷达驱动(占位)启动 —— 实体车请启动 rplidar_ros/ldlidar 驱动")


def main():
    rclpy.init()
    rclpy.spin(LidarDriver())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
