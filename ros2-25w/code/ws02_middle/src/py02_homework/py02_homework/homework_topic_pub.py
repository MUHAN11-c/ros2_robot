# -*- coding: utf-8 -*-
"""
    需求：期中大作业 —— 话题通信：发布速度指令控制乌龟作圆周运动，支持动态调参。
    说明：turtlesim 订阅 /t1/cmd_vel；参数 linear_x / angular_z 可通过
          ros2 param set /hw_pub_vel_node_py ... 动态修改。
"""
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class HomeworkTopicPub(Node):

    def __init__(self):
        super().__init__("hw_pub_vel_node_py")
        self.get_logger().info("发布速度指令，控制机器人作圆周运动(python)!")
        # 1.声明并获取参数(动态调参)；
        self.declare_parameter("linear_x", 1.0)
        self.declare_parameter("angular_z", 1.0)
        # 2.创建速度发布方；
        self.pub = self.create_publisher(Twist, "/t1/cmd_vel", 10)
        # 3.创建定时器，在定时器回调函数中组织并发布速度指令。
        self.timer = self.create_timer(0.1, self.on_timer)

    def on_timer(self):
        twist = Twist()
        twist.linear.x = self.get_parameter("linear_x").value
        twist.angular.z = self.get_parameter("angular_z").value
        self.pub.publish(twist)


def main():
    rclpy.init()
    rclpy.spin(HomeworkTopicPub())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
