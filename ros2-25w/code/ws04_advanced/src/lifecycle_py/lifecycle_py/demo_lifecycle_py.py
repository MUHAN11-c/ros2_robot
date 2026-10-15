# -*- coding: utf-8 -*-
"""
    需求：生命周期节点(Python实现) —— 节点在配置/激活/待激活/清理/关闭各状态切换时输出日志。
    说明：类名/节点名/日志文案与课程视频（demo_lifecycle_py.py）一致。
"""
import rclpy
from rclpy.node import Node
from rclpy.lifecycle import LifecycleNode
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn


class MyNode(LifecycleNode):

    def __init__(self):
        super().__init__("demo_lifecycle_py_node")

    # 编写状态切换函数实现
    def on_configure(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("配置中......(py)")
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("激活中......(py)")
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("待激活......(py)")
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("清空....(py)")
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("关闭......(py)")
        return TransitionCallbackReturn.SUCCESS


def main():
    rclpy.init()
    rclpy.spin(MyNode())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
