# -*- coding: utf-8 -*-
"""
    需求：智能语音 —— 语音识别(ASR)与 ROS2 集成骨架。
    说明：课程使用讯飞语音 SDK(需要 APPID/AK/SK 密钥，务必通过环境变量注入，
          不要写入源码)；本节点封装"文本指令 → ROS2 控制指令"链路：
          1. ASR 结果以 std_msgs/String 发布到 voice_cmd_text 话题；
          2. 控制指令映射: "前进/后退/左转/右转/停止" → cmd_vel。
"""
import os

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String


class VoiceController(Node):

    # 语音指令 → 速度指令映射；
    COMMANDS = {
        "前进": (0.3, 0.0),
        "后退": (-0.3, 0.0),
        "左转": (0.0, 1.0),
        "右转": (0.0, -1.0),
        "停止": (0.0, 0.0),
    }

    def __init__(self):
        super().__init__("voice_controller_node_py")
        self.get_logger().info("语音控制节点创建!")
        # 讯飞 SDK 密钥只从环境变量读取；
        self.iflytek_appid = os.environ.get("IFLYTEK_APPID", "")
        if not self.iflytek_appid:
            self.get_logger().warn("未设置 IFLYTEK_APPID 环境变量，仅支持文本指令模拟")
        # 控制指令发布方；
        self.pub = self.create_publisher(Twist, "cmd_vel", 10)
        # 指令订阅方(由 ASR 节点/键盘模拟节点发布 String 文本)；
        self.sub = self.create_subscription(String, "voice_cmd_text", self.on_text, 10)

    def on_text(self, msg):
        self.asr_callback(msg.data)

    def asr_callback(self, text):
        """由语音识别结果驱动的控制回调。"""
        self.get_logger().info("收到语音指令:%s" % text)
        twist = Twist()
        for key, (lx, az) in self.COMMANDS.items():
            if key in text:
                twist.linear.x = lx
                twist.angular.z = az
                self.pub.publish(twist)
                self.get_logger().info("执行: linear=%.2f angular=%.2f" % (lx, az))
                return
        self.get_logger().info("未知指令，已忽略")


def main():
    rclpy.init()
    rclpy.spin(VoiceController())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
