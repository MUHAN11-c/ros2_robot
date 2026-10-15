# -*- coding: utf-8 -*-
"""
    需求：订阅乌龟位姿并转换成坐标系相对关系后发布(动态坐标变换)，
         乌龟名称由参数 turtle 指定（Python实现）。
"""
import math

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from tf2_ros import TransformBroadcaster
from turtlesim.msg import Pose


class Exer02TFBroadcasterPy(Node):

    def __init__(self):
        super().__init__("exer02_tf_broadcaster_node_py")
        self.declare_parameter("turtle", "t1")
        self.turtle = self.get_parameter("turtle").value
        self.get_logger().info("广播 %s 的坐标变换!(python)" % self.turtle)
        self.broadcaster = TransformBroadcaster(self)
        self.sub = self.create_subscription(Pose, "/" + self.turtle + "/pose", self.do_pose, 10)

    def do_pose(self, pose):
        ts = TransformStamped()
        ts.header.stamp = self.get_clock().now().to_msg()
        ts.header.frame_id = "world"
        ts.child_frame_id = self.turtle
        ts.transform.translation.x = pose.x
        ts.transform.translation.y = pose.y
        ts.transform.translation.z = 0.0
        qz = math.sin(pose.theta / 2)
        qw = math.cos(pose.theta / 2)
        ts.transform.rotation.x = 0.0
        ts.transform.rotation.y = 0.0
        ts.transform.rotation.z = qz
        ts.transform.rotation.w = qw
        self.broadcaster.sendTransform(ts)


def main():
    rclpy.init()
    rclpy.spin(Exer02TFBroadcasterPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
