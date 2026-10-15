# -*- coding: utf-8 -*-
"""
    需求：监听两只乌龟的坐标变换，生成速度指令控制 turtle2 朝向 turtle1(乌龟跟随)——Python实现。
"""
import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
import tf_transformations
import tf2_ros


class Exer03TFListenerPy(Node):

    def __init__(self):
        super().__init__("exer03_tf_listener_node_py")
        # 1.声明参数服务；
        self.declare_parameter("father_frame", "t2")
        self.declare_parameter("child_frame", "turtle1")
        self.father_frame = self.get_parameter("father_frame").get_parameter_value().string_value
        self.child_frame = self.get_parameter("child_frame").get_parameter_value().string_value
        # 2.创建tf缓存对象；
        self.buffer = tf2_ros.Buffer()
        # 3.创建tf监听器；
        self.listener = tf2_ros.TransformListener(self.buffer, self)
        # 4.创建速度发布方；
        self.cmd_pub = self.create_publisher(Twist, "/" + self.father_frame + "/cmd_vel", 10)
        # 5.创建一个定时器，实现坐标的变换，并且生成速度指令并发布。
        self.timer = self.create_timer(1.0, self.on_timer)

    def on_timer(self):
        try:
            # 坐标变换
            ts = self.buffer.lookup_transform(self.father_frame, self.child_frame, rclpy.time.Time())
            # 计算规则：
            #     线速度 = 系数 * 开平方(x² + y²)；
            #     角速度 = 系数 * 反正切(y / x)；
            twist = Twist()
            twist.linear.x = 0.5 * math.sqrt(pow(ts.transform.translation.x, 2) + pow(ts.transform.translation.y, 2))
            twist.angular.z = 1.0 * math.atan2(ts.transform.translation.y, ts.transform.translation.x)
            self.cmd_pub.publish(twist)
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            self.get_logger().info("异常提示:%s" % str(e))


def main():
    rclpy.init()
    rclpy.spin(Exer03TFListenerPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
