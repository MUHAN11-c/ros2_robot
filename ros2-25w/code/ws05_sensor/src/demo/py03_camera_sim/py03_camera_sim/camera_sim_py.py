# -*- coding: utf-8 -*-
"""
    需求：单目相机仿真（Python实现）—— 周期性组织并发布 Image 消息(黑白条纹)。
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class CameraSimPy(Node):

    def __init__(self):
        super().__init__("camera_sim_node_py")
        self.get_logger().info("单目相机仿真节点创建!(python)")
        self.pub = self.create_publisher(Image, "image_raw", 10)
        self.timer = self.create_timer(0.1, self.on_timer)
        self.flip = False

    def on_timer(self):
        # 组织图片基本参数；
        image = Image()
        image.header.frame_id = "camera"
        image.header.stamp = self.get_clock().now().to_msg()
        image.height = 240
        image.width = 320
        image.encoding = "mono8"
        image.is_bigendian = 0
        image.step = image.width
        # 组织图片数据：黑白条纹；
        data = bytearray(image.height * image.width)
        for r in range(image.height):
            for c in range(image.width):
                band = ((c // 20) % 2 == 0) ^ self.flip
                data[r * image.width + c] = 255 if band else 0
        image.data = bytes(data)
        self.flip = not self.flip
        self.pub.publish(image)


def main():
    rclpy.init()
    rclpy.spin(CameraSimPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
