# -*- coding: utf-8 -*-
"""
    需求：ROS2 快速体验 —— HelloWorld(Python)。
"""
import rclpy
from rclpy.node import Node


class HelloWorld(Node):

    def __init__(self):
        super().__init__("hello_world_node_py")
        self.get_logger().info("Hello World!(python)")


def main():
    rclpy.init()
    rclpy.spin(HelloWorld())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
