# -*- coding: utf-8 -*-
# 底盘驱动占位节点：发布里程计(实体车由串口驱动实现，此处发布静态里程计便于流程验证)。
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node


class BaseDriver(Node):

    def __init__(self):
        super().__init__("base_driver_node_py")
        self.get_logger().info("底盘驱动(占位)启动")
        self.pub = self.create_publisher(Odometry, "odom", 10)
        self.create_timer(0.1, self.on_timer)

    def on_timer(self):
        odom = Odometry()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_footprint"
        self.pub.publish(odom)


def main():
    rclpy.init()
    rclpy.spin(BaseDriver())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
