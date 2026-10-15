# -*- coding: utf-8 -*-
"""
    需求：提交两个整数到服务端，并处理响应结果。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建客户端；
            3-2.等待服务连接；
            3-3.组织并提交请求数据；
            3-4.处理响应。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import sys

import rclpy
from rclpy.node import Node
from base_interfaces_demo.srv import AddInts


# 3.自定义节点类；
class AddIntsClient(Node):

    def __init__(self):
        super().__init__("add_ints_client_node_py")
        self.get_logger().info("客户端创建了!(python)")
        # 3-1.创建客户端；
        self.client = self.create_client(AddInts, "add_ints")

    # 3-2.等待服务连接；
    def connect_server(self):
        while not self.client.wait_for_service(1.0):
            if not rclpy.ok():
                self.get_logger().info("客户端退出...")
                return False
            self.get_logger().info("服务连接中，请稍候...")
        return True

    # 3-3.组织并提交请求数据；
    def send_request(self, num1, num2):
        request = AddInts.Request()
        request.num1 = num1
        request.num2 = num2
        self.get_logger().info("发送请求: num1=%d, num2=%d" % (num1, num2))
        return self.client.call_async(request)


def main():
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    if len(sys.argv) != 3:
        rclpy.logging.get_logger("rclpy").info("请提交两个整型数据!")
        rclpy.shutdown()
        return
    num1 = int(sys.argv[1])
    num2 = int(sys.argv[2])
    client = AddIntsClient()
    if not client.connect_server():
        rclpy.shutdown()
        return
    # 3-4.处理响应；
    future = client.send_request(num1, num2)
    # 4.调用spin函数，并传入节点对象；
    rclpy.spin_until_future_complete(client, future)
    response = future.result()
    client.get_logger().info("收到响应: sum=%d" % response.sum)
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
