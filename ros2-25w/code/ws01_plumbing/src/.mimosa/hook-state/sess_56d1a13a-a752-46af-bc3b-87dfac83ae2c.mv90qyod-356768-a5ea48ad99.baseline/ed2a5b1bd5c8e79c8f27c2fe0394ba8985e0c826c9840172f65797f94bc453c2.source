# -*- coding: utf-8 -*-
"""
    需求：发布两个坐标系之间的相对关系(静态坐标变换)。
         依赖命令行参数传入：x y z 欧拉角roll pitch yaw 父坐标系id 子坐标系id。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建广播对象；
            3-2.组织并发布数据。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import math
import sys

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster


# 3.自定义节点类；
class TFStaticBroadcaster(Node):

    def __init__(self, argv):
        super().__init__("tf_static_broadcaster_node_py")
        self.get_logger().info("静态坐标变换广播方创建!(python)")
        # 3-1.创建广播对象；
        self.broadcaster = StaticTransformBroadcaster(self)
        # 3-2.组织并发布数据。
        self.pub_static_tf(argv)

    def pub_static_tf(self, argv):
        # 组织消息；
        ts = TransformStamped()
        ts.header.stamp = self.get_clock().now().to_msg()
        # 父坐标系；
        ts.header.frame_id = argv[7]
        # 子坐标系；
        ts.child_frame_id = argv[8]
        # 设置偏移量；
        ts.transform.translation.x = float(argv[1])
        ts.transform.translation.y = float(argv[2])
        ts.transform.translation.z = float(argv[3])
        # 根据欧拉角获取四元数；
        roll, pitch, yaw = float(argv[4]), float(argv[5]), float(argv[6])
        qx = math.sin(roll / 2) * math.cos(pitch / 2) * math.cos(yaw / 2) - math.cos(roll / 2) * math.sin(pitch / 2) * math.sin(yaw / 2)
        qy = math.cos(roll / 2) * math.sin(pitch / 2) * math.cos(yaw / 2) + math.sin(roll / 2) * math.cos(pitch / 2) * math.sin(yaw / 2)
        qz = math.cos(roll / 2) * math.cos(pitch / 2) * math.sin(yaw / 2) - math.sin(roll / 2) * math.sin(pitch / 2) * math.cos(yaw / 2)
        qw = math.cos(roll / 2) * math.cos(pitch / 2) * math.cos(yaw / 2) + math.sin(roll / 2) * math.sin(pitch / 2) * math.sin(yaw / 2)
        ts.transform.rotation.x = qx
        ts.transform.rotation.y = qy
        ts.transform.rotation.z = qz
        ts.transform.rotation.w = qw
        # 发布；
        self.broadcaster.sendTransform(ts)


def main():
    if len(sys.argv) != 9:
        rclpy.logging.get_logger("rclpy").info("请传入 x y z roll pitch yaw 父坐标系id 子坐标系id!")
        return
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    # 4.调用spin函数，并传入节点对象；
    rclpy.spin(TFStaticBroadcaster(sys.argv))
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
