# -*- coding: utf-8 -*-
"""
    需求：期中大作业 —— 动作通信：乌龟前进指定距离，期间连续反馈当前里程。
    说明：使用标准 action 接口 example_interfaces/action/Fibonacci 复用其 int32 goal 语义，
          课程使用自定义 Progress.action（见 ws01_plumbing/base_interfaces_demo），
          此处演示乌龟版实现：goal.num 为目标距离(整型，单位: 米的100倍)。
"""
import math
import time

import rclpy
from base_interfaces_demo.action import Progress
from geometry_msgs.msg import Twist
from rclpy.action import ActionServer
from rclpy.node import Node
from turtlesim.msg import Pose


class HomeworkActionServer(Node):

    def __init__(self):
        super().__init__("hw_action_server_node_py")
        self.get_logger().info("期中大作业-动作通信服务端(python)")
        self.pose = None
        self.pub = self.create_publisher(Twist, "/t1/cmd_vel", 10)
        self.sub = self.create_subscription(Pose, "/t1/pose", self.on_pose, 10)
        self.server = ActionServer(self, Progress, "turtle_forward", self.execute_callback)

    def on_pose(self, pose):
        self.pose = pose

    def execute_callback(self, goal_handle):
        target = goal_handle.request.num / 100.0
        self.get_logger().info("收到目标:前进 %.2f 米" % target)
        start = self.pose
        start_x, start_y = (start.x, start.y) if start else (5.544, 5.544)
        feedback = Progress.Feedback()
        rate = self.create_rate(10.0)
        while rclpy.ok():
            if self.pose is None:
                time.sleep(0.1)
                continue
            dist = math.sqrt((self.pose.x - start_x) ** 2 + (self.pose.y - start_y) ** 2)
            progress = min(dist / target, 1.0)
            feedback.progress = progress
            goal_handle.publish_feedback(feedback)
            self.get_logger().info("连续反馈，进度:%.2f" % progress)
            if goal_handle.is_cancel_requested or dist >= target:
                break
            twist = Twist()
            twist.linear.x = 1.0
            self.pub.publish(twist)
            rate.sleep()
        twist = Twist()
        self.pub.publish(twist)
        goal_handle.succeed()
        result = Progress.Result()
        result.sum = int(dist * 100)
        return result


def main():
    rclpy.init()
    rclpy.spin(HomeworkActionServer())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
