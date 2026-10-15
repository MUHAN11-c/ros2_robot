# launch 之 Python 实现：启动两个 turtlesim 窗口（helloworld 案例）
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    turtle1 = Node(package="turtlesim",executable="turtlesim_node",name="t1")
    turtle2 = Node(package="turtlesim",executable="turtlesim_node",name="t2")
    return LaunchDescription([turtle1, turtle2])
