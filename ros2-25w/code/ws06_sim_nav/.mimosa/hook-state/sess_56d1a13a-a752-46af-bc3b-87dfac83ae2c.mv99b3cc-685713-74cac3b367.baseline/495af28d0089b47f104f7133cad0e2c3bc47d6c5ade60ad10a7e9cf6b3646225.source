# -*- coding: utf-8 -*-
"""
    需求：智能语音 —— 键盘文本指令模拟 ASR 输出(便于无 SDK 环境联调)。
    运行：ros2 run demo_voice voice_input，输入 前进/后退/左转/右转/停止。
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class VoiceInput(Node):

    def __init__(self):
        super().__init__("voice_input_node_py")
        self.get_logger().info("语音指令输入(模拟)创建! 输入: 前进/后退/左转/右转/停止 + 回车")
        self.pub = self.create_publisher(String, "voice_cmd_text", 10)

    def spin_input(self):
        while rclpy.ok():
            try:
                text = input()
            except EOFError:
                break
            msg = String()
            msg.data = text.strip()
            self.pub.publish(msg)


def main():
    rclpy.init()
    node = VoiceInput()
    import threading
    thread = threading.Thread(target=node.spin_input, daemon=True)
    thread.start()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
