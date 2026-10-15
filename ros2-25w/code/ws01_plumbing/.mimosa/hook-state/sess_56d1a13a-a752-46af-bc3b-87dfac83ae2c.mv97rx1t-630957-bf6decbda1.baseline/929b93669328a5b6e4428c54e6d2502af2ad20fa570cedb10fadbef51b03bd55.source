# -*- coding: utf-8 -*-
"""
    需求：向 /spawn 服务发送请求，生成一只新乌龟（Python实现）。
"""
import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn


class Exer01SpawnPy(Node):

    def __init__(self):
        super().__init__("exer01_spawn_node_py")
        self.get_logger().info("乌龟生成客户端创建!(python)")
        self.client = self.create_client(Spawn, "/spawn")
        self.declare_parameter("turtle_name", "t2")

    def connect_server(self):
        while not self.client.wait_for_service(1.0):
            if not rclpy.ok():
                self.get_logger().info("客户端退出...")
                return False
            self.get_logger().info("服务连接中，请稍候...")
        return True

    def send_request(self):
        request = Spawn.Request()
        request.x = 3.0
        request.y = 3.0
        request.theta = 0.0
        request.name = self.get_parameter("turtle_name").value
        self.get_logger().info("请求生成乌龟:%s" % request.name)
        return self.client.call_async(request)


def main():
    rclpy.init()
    client = Exer01SpawnPy()
    if not client.connect_server():
        rclpy.shutdown()
        return
    future = client.send_request()
    rclpy.spin_until_future_complete(client, future)
    client.get_logger().info("新乌龟名称:%s" % future.result().name)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
