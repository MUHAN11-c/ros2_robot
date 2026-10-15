# -*- coding: utf-8 -*-
"""
    需求：IMU 案例（Python实现）—— 订阅 IMU 数据，输出姿态、角速度与线加速度。
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu


class ImuDemoPy(Node):

    def __init__(self):
        super().__init__("imu_node_py")
        self.get_logger().info("IMU 案例节点创建!(python)")
        self.sub = self.create_subscription(Imu, "imu", self.imu_callback, 10)

    def imu_callback(self, imu):
        self.get_logger().info("---------IMU 数据---------")
        self.get_logger().info("姿态四元数:(%.2f,%.2f,%.2f,%.2f)" % (
            imu.orientation.w, imu.orientation.x, imu.orientation.y, imu.orientation.z))
        self.get_logger().info("角速度:(%.2f,%.2f,%.2f) rad/s" % (
            imu.angular_velocity.x, imu.angular_velocity.y, imu.angular_velocity.z))
        self.get_logger().info("线加速度:(%.2f,%.2f,%.2f) m/s^2" % (
            imu.linear_acceleration.x, imu.linear_acceleration.y, imu.linear_acceleration.z))


def main():
    rclpy.init()
    rclpy.spin(ImuDemoPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
