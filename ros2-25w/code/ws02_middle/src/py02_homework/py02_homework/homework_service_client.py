# -*- coding: utf-8 -*-
"""
    需求：期中大作业 —— 服务通信：向 /spawn 发送请求生成一只新乌龟。
"""
import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn


class HomeworkServiceClient(Node):

    def __init__(self):
        super().__init__("hw_spawn_node_py")
        self.get_logger().info("期中大作业-服务通信客户端(python)")
        self.client = self.create_client(Spawn, "/spawn")

    def connect_server(self):
        while not self.client.wait_for_service(1.0):
            if not rclpy.ok():
                self.get_logger().info("客户端退出...")
                return False
            self.get_logger().info("服务连接中，请稍候...")
        return True

    def send_request(self, name):
        request = Spawn.Request()
        request.x = 5.0
        request.y = 5.0
        request.theta = 0.0
        request.name = name
        return self.client.call_async(request)


def main():
    rclpy.init()
    client = HomeworkServiceClient()
    if not client.connect_server():
        rclpy.shutdown()
        return
    future = client.send_request("t1")
    rclpy.spin_until_future_complete(client, future)
    client.get_logger().info("已生成乌龟:%s" % future.result().name)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
