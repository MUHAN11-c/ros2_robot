# -*- coding: utf-8 -*-
"""
    需求：坐标点变换监听(Python) —— 订阅 turtle1 坐标系下的坐标点，变换到 world 并输出。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建 tf 缓存对象与监听器；
            3-2.创建坐标点订阅方；
            3-3.回调中变换坐标点并输出。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
from tf2_ros import Buffer
from tf2_ros import TransformListener
import tf2_geometry_msgs                              # 注册 PointStamped 转换器（必须导入）


# 3.自定义节点类；
class PointListenerPy(Node):

    def __init__(self):
        super().__init__("point_listener_node_py")
        # 3-1.创建 tf 缓存对象与监听器（Jazzy 需传入节点对象）；
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        # 3-2.创建坐标点订阅方；
        self.sub = self.create_subscription(PointStamped, "/turtle1/point", self.on_point, 10)

    # 3-3.回调中变换坐标点并输出；
    def on_point(self, point):
        try:
            out = self.buffer.transform(point, "world", timeout=rclpy.duration.Duration(seconds=1.0))
            self.get_logger().info(
                "坐标点(%.2f,%.2f) 变换到 world 系下: (%.2f,%.2f)" %
                (point.point.x, point.point.y, out.point.x, out.point.y))
        except Exception as e:
            self.get_logger().info("变换异常:%s" % str(e))


def main():
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    # 4.调用spin函数，并传入节点对象；
    rclpy.spin(PointListenerPy())
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
