# -*- coding: utf-8 -*-
"""
    需求：解析客户端提交的目标值，循环累加并发布连续反馈，最终响应求和结果。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建动作服务端；
            3-2.处理请求数据(解析目标值，判断是否要执行)；
            3-3.处理取消请求；
            3-4.生成连续反馈与最终响应(回调函数)。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import time

import rclpy
from rclpy.action import ActionServer
from rclpy.node import Node
from base_interfaces_demo.action import Progress


# 3.自定义节点类；
class ProgressActionServer(Node):

    def __init__(self):
        super().__init__("progress_action_server_node_py")
        self.get_logger().info("动作通信服务端创建!(python)")
        # 3-1.创建动作服务端；
        self._action_server = ActionServer(
            self,
            Progress,
            "get_sum",
            self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback)

    # 3-2.处理请求数据(解析目标值，判断是否要执行)；
    def goal_callback(self, goal_request):
        self.get_logger().info("接收到客户端请求，目标值:%d" % goal_request.num)
        if goal_request.num >= 1:
            return rclpy.action.server.GoalResponse.ACCEPT
        return rclpy.action.server.GoalResponse.REJECT

    # 3-3.处理取消请求；
    def cancel_callback(self, goal_handle):
        self.get_logger().info("接受到取消请求")
        return rclpy.action.server.CancelResponse.ACCEPT

    # 3-4.生成连续反馈与最终响应(回调函数)；
    def execute_callback(self, goal_handle):
        # 1.生成连续反馈；
        # 首先要获取目标值，然后遍历，遍历中进行累加，且每循环一次就计算进度，并作为连续反馈发布；
        num = goal_handle.request.num
        sum_ = 0
        feedback = Progress.Feedback()
        for i in range(1, num + 1):
            sum_ += i
            feedback.progress = i / num
            goal_handle.publish_feedback(feedback)
            self.get_logger().info("连续反馈:%.2f" % feedback.progress)
            time.sleep(1.0)
        # 2.响应最终结果；
        goal_handle.succeed()
        result = Progress.Result()
        result.sum = sum_
        self.get_logger().info("最终结果:%d" % sum_)
        return result


def main():
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    # 4.调用spin函数，并传入节点对象；
    rclpy.spin(ProgressActionServer())
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
