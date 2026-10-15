# -*- coding: utf-8 -*-
"""
    需求：多车编队 —— 跟随车控制节点(robot2)。
    说明：领航车(robot1) 广播 map→robot1 的位姿；本节点查询 robot2→robot1 的相对位姿，
          生成速度指令保持编队队形(间距 formation_offset)。
"""
import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
import tf2_ros


class Follower(Node):

    def __init__(self):
        super().__init__("formation_follower_node_py")
        self.get_logger().info("多车编队-跟随车控制方(python)")
        # 1.编队参数；
        self.declare_parameter("leader_frame", "robot1")
        self.declare_parameter("follower_frame", "robot2")
        self.declare_parameter("formation_offset", 2.0)
        self.leader_frame = self.get_parameter("leader_frame").value
        self.follower_frame = self.get_parameter("follower_frame").value
        self.offset = self.get_parameter("formation_offset").value
        # 2.tf 缓存与监听器；
        self.buffer = tf2_ros.Buffer()
        self.listener = tf2_ros.TransformListener(self.buffer, self)
        # 3.跟随车速度发布方(命名空间下)；
        self.pub = self.create_publisher(Twist, "/robot2/cmd_vel", 10)
        # 4.定时器；
        self.create_timer(0.2, self.on_timer)

    def on_timer(self):
        try:
            ts = self.buffer.lookup_transform(
                self.follower_frame, self.leader_frame, rclpy.time.Time())
            dx = ts.transform.translation.x
            dy = ts.transform.translation.y
            dist = math.sqrt(dx * dx + dy * dy)
            twist = Twist()
            # 与领航车的实际间距 = dist；期望间距 = offset；
            err = dist - self.offset
            if abs(err) > 0.2:
                twist.linear.x = 0.5 * max(min(err, 1.0), -1.0)
                twist.angular.z = 1.0 * math.atan2(dy, dx)
            self.pub.publish(twist)
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            self.get_logger().info("异常提示:%s" % str(e), throttle_duration_sec=2.0)


def main():
    rclpy.init()
    rclpy.spin(Follower())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
