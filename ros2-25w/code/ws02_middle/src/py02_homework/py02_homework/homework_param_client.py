# -*- coding: utf-8 -*-
"""
    需求：期中大作业 —— 参数服务：通过参数客户端修改 turtlesim 的背景色(r/g/b)。
    说明：远程调用 /turtlesim/set_parameters 服务，修改 background_r、background_g、
          background_b 后，还需调用 /turtlesim/clear 使背景生效。
"""
import rclpy
from rcl_interfaces.srv import SetParameters
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_srvs.srv import Empty


class HomeworkParamClient(Node):

    def __init__(self):
        super().__init__("hw_param_client_node_py")
        self.get_logger().info("期中大作业-参数服务客户端(python)")
        self.client = self.create_client(SetParameters, "/turtlesim/set_parameters")
        self.clear_client = self.create_client(Empty, "/turtlesim/clear")

    def connect_server(self):
        while not self.client.wait_for_service(1.0):
            if not rclpy.ok():
                self.get_logger().info("客户端退出...")
                return False
            self.get_logger().info("服务连接中，请稍候...")
        return True

    def set_background(self, r, g, b):
        request = SetParameters.Request()
        request.parameters = [
            Parameter("background_r", Parameter.Type.INTEGER, r).to_parameter_msg(),
            Parameter("background_g", Parameter.Type.INTEGER, g).to_parameter_msg(),
            Parameter("background_b", Parameter.Type.INTEGER, b).to_parameter_msg(),
        ]
        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        if future.result() is not None:
            for re in future.result().results:
                self.get_logger().info("修改背景色:%s" % ("成功" if re.successful else "失败"))
        # 调用 /clear 让新背景色生效；
        clear_future = self.clear_client.call_async(Empty.Request())
        rclpy.spin_until_future_complete(self, clear_future)


def main():
    rclpy.init()
    client = HomeworkParamClient()
    if not client.connect_server():
        rclpy.shutdown()
        return
    client.set_background(100, 84, 105)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
