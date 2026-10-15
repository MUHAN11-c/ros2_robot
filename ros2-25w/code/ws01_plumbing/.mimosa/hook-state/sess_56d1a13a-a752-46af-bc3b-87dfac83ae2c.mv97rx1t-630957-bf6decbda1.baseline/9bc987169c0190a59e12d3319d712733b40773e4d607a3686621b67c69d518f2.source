# -*- coding: utf-8 -*-
"""
    需求：订阅乌龟位姿，并转换成坐标系相对关系再发布(动态坐标变换)。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建一个动态广播器；
            3-2.创建一个乌龟位姿订阅方；
            3-3.回调函数中，获取乌龟位姿并生成相对关系然后发布。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import math

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from tf2_ros import TransformBroadcaster
from turtlesim.msg import Pose


# 3.自定义节点类；
class TFDynaBroadcaster(Node):

    def __init__(self):
        super().__init__("tf_dyna_broadcaster_node_py")
        self.get_logger().info("动态坐标变换广播方创建!(python)")
        # 3-1.创建一个动态广播器；
        self.broadcaster = TransformBroadcaster(self)
        # 3-2.创建一个乌龟位姿订阅方；
        self.sub = self.create_subscription(Pose, "/turtle1/pose", self.do_pose, 10)

    # 3-3.回调函数中，获取乌龟位姿并生成相对关系然后发布；
    def do_pose(self, pose):
        # 组织消息；
        ts = TransformStamped()
        ts.header.stamp = self.get_clock().now().to_msg()
        ts.header.frame_id = "world"
        ts.child_frame_id = "turtle1"
        # 设置偏移量；
        ts.transform.translation.x = pose.x
        ts.transform.translation.y = pose.y
        ts.transform.translation.z = 0.0
        # 根据欧拉角(乌龟的朝向)获取四元数；
        qz = math.sin(pose.theta / 2)
        qw = math.cos(pose.theta / 2)
        ts.transform.rotation.x = 0.0
        ts.transform.rotation.y = 0.0
        ts.transform.rotation.z = qz
        ts.transform.rotation.w = qw
        # 发布；
        self.broadcaster.sendTransform(ts)


def main():
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    # 4.调用spin函数，并传入节点对象；
    rclpy.spin(TFDynaBroadcaster())
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
