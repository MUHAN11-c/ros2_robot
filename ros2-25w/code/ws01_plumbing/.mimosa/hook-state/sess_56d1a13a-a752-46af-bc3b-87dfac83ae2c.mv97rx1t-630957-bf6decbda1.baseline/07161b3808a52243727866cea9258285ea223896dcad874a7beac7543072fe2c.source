# -*- coding: utf-8 -*-
"""
    需求：提交目标值到服务端，处理连续反馈与最终响应。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建动作客户端；
            3-2.等待服务连接；
            3-3.发送目标；
            3-4.处理目标响应(是否被接受)；
            3-5.处理连续反馈；
            3-6.处理最终响应。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from base_interfaces_demo.action import Progress


# 3.自定义节点类；
class ProgressActionClient(Node):

    def __init__(self):
        super().__init__("progress_action_client_node_py")
        self.get_logger().info("动作通信客户端创建!(python)")
        # 3-1.创建动作客户端；
        self._action_client = ActionClient(self, Progress, "get_sum")

    # 3-2.等待服务连接；
    def connect_server(self):
        while not self._action_client.wait_for_server(1.0):
            if not rclpy.ok():
                self.get_logger().info("客户端退出...")
                return False
            self.get_logger().info("服务连接中，请稍候...")
        return True

    # 3-3.发送目标；
    def send_goal(self, num):
        goal = Progress.Goal()
        goal.num = num
        self.get_logger().info("发送目标值:%d" % num)
        self._action_client.send_goal_async(goal, self.feedback_callback).add_done_callback(self.goal_response_callback)

    # 3-4.处理目标响应(是否被接受)；
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info("目标被服务端拒绝了!")
            return
        self.get_logger().info("目标被服务端接受，请等待连续反馈与最终响应!")
        goal_handle.get_result_async().add_done_callback(self.result_callback)

    # 3-5.处理连续反馈；
    def feedback_callback(self, feedback):
        self.get_logger().info("收到连续反馈:%.2f" % feedback.feedback.progress)

    # 3-6.处理最终响应；
    def result_callback(self, future):
        result = future.result().result
        self.get_logger().info("最终响应结果:%d" % result.sum)


def main():
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    if len(sys.argv) != 2:
        rclpy.logging.get_logger("rclpy").info("请提交一个大于等于1的整型数据!")
        rclpy.shutdown()
        return
    num = int(sys.argv[1])
    client = ProgressActionClient()
    if not client.connect_server():
        rclpy.shutdown()
        return
    client.send_goal(num)
    # 4.调用spin函数，并传入节点对象；
    rclpy.spin(client)
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
