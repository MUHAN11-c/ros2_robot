# -*- coding: utf-8 -*-
"""
    需求：参数事件(Python实现) —— 监听节点参数的变化事件并输出。
"""
import rclpy
from rcl_interfaces.msg import ParameterEvent, SetParametersResult
from rclpy.node import Node
from rclpy.parameter import Parameter, Parameter


class ParamEventsPy(Node):

    def __init__(self):
        super().__init__("param_events_node_py")
        self.get_logger().info("参数事件节点创建!(python)")
        # 1.声明参数；
        self.declare_parameter("width", 1.0)
        # 2.添加参数事件回调(add_on_set_parameters_callback)；
        self.add_on_set_parameters_callback(self.on_param_change)
        # 3.监听其他节点参数事件(通过参数事件话题)；
        self.create_subscription(ParameterEvent, "/parameter_events", self.on_param_event, 10)
        # 4.周期性修改参数以触发事件；
        self.timer = self.create_timer(3.0, self.on_timer)

    def on_param_change(self, params):
        result = SetParametersResult()
        result.successful = True
        for param in params:
            self.get_logger().info("监听到参数修改事件: %s -> %s" % (param.name, str(param.value)))
        return result

    def on_param_event(self, event):
        self.get_logger().info("收到参数事件，来自节点:%s" % event.node)

    def on_timer(self):
        width = self.get_parameter("width").value + 1.0
        self.set_parameters([Parameter("width", Parameter.Type.DOUBLE, width)])


def main():
    rclpy.init()
    rclpy.spin(ParamEventsPy())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
