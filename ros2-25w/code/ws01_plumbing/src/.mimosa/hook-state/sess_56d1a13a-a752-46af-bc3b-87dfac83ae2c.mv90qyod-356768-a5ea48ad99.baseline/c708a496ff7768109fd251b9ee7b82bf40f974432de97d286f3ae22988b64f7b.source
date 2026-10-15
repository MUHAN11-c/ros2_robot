# -*- coding: utf-8 -*-
"""
    需求：编写参数客户端，远程操作其他节点参数(查、改)。
    说明：远程操作依赖节点自带的参数服务，服务名为
          <节点名>/get_parameters 与 <节点名>/set_parameters。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建参数客户端；
            3-2.等待服务连接；
            3-3.查(远程获取参数)；
            3-4.改(远程设置参数)。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import rclpy
from rcl_interfaces.srv import GetParameters, SetParameters
from rclpy.node import Node
from rclpy.parameter import Parameter


# 3.自定义节点类；
class ParamClient(Node):

    def __init__(self, target_node="param_server_node_py"):
        super().__init__("param_client_node_py")
        self.get_logger().info("参数客户端创建了!(python)")
        # 3-1.创建参数客户端；
        self.get_client = self.create_client(GetParameters, "%s/get_parameters" % target_node)
        self.set_client = self.create_client(SetParameters, "%s/set_parameters" % target_node)

    # 3-2.等待服务连接；
    def connect_server(self):
        while not (self.get_client.wait_for_service(1.0) and self.set_client.wait_for_service(1.0)):
            if not rclpy.ok():
                self.get_logger().info("客户端退出...")
                return False
            self.get_logger().info("服务连接中，请稍候...")
        return True

    # 3-3.查(远程获取参数)；
    def get_param(self, names):
        request = GetParameters.Request()
        request.names = names
        future = self.get_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        if future.result() is not None:
            for name, value in zip(names, future.result().values):
                self.get_logger().info("'%s' = %s" % (name, value))
        else:
            self.get_logger().info("请求失败...")

    # 3-4.改(远程设置参数)；
    def update_param(self, name, value):
        request = SetParameters.Request()
        request.parameters = [Parameter(name, Parameter.Type.DOUBLE, value).to_parameter_msg()]
        future = self.set_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        if future.result() is not None:
            for re in future.result().results:
                self.get_logger().info("修改参数结果：%s" % ("成功" if re.successful else "失败"))
        else:
            self.get_logger().info("请求失败...")


def main():
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    client = ParamClient()
    if not client.connect_server():
        rclpy.shutdown()
        return
    client.get_param(["width"])
    client.update_param("width", 1.65)
    client.get_param(["width"])
    # 4.调用spin函数，并传入节点对象；
    # rclpy.spin(client)
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
