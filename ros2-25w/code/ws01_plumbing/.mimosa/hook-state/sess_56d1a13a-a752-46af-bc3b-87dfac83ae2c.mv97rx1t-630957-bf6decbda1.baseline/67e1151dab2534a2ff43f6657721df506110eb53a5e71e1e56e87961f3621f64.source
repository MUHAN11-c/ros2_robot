# -*- coding: utf-8 -*-
"""
    需求：编写参数服务端节点，实现参数的增、删、改、查操作。
    流程：
        1.导包；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.增(声明参数)；
            3-2.查；
            3-3.改；
            3-4.删。
        4.调用spin函数，并传入节点对象；
        5.释放资源。
"""
# 1.导包；
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter


# 3.自定义节点类；
class ParamServer(Node):

    def __init__(self):
        super().__init__("param_server_node_py")
        self.get_logger().info("参数服务端创建了!(python)")
        self.names = ["car_name", "width", "wheels"]
        # 3-1.增(声明参数)；
        self.declare_param()
        # 3-2.查；
        self.get_param()
        # 3-3.改；
        self.update_param()
        self.get_param()
        # 3-4.删；
        self.del_param()
        self.get_param()

    # 3-1.增(声明参数)；
    def declare_param(self):
        self.get_logger().info("-------------增-------------")
        self.declare_parameter("car_name", "tiger")
        self.declare_parameter("width", 1.55)
        self.declare_parameter("wheels", 5)

    # 3-2.查；
    def get_param(self):
        self.get_logger().info("-------------查-------------")
        for name in self.names:
            if self.has_parameter(name):
                self.get_logger().info("%s = %s" % (name, self.get_parameter(name).value))

    # 3-3.改；
    def update_param(self):
        self.get_logger().info("-------------改-------------")
        self.set_parameters([Parameter("width", Parameter.Type.DOUBLE, 1.65)])

    # 3-4.删；
    def del_param(self):
        self.get_logger().info("-------------删-------------")
        self.undeclare_parameter("car_name")


def main():
    # 2.初始化 ROS2 客户端；
    rclpy.init()
    # 4.调用spin函数，并传入节点对象；
    rclpy.spin(ParamServer())
    # 5.释放资源；
    rclpy.shutdown()


if __name__ == '__main__':
    main()
