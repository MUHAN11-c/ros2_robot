# -*- coding: utf-8 -*-
# 车辆跟随 launch：目标坐标系广播方 + 跟随控制器
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    goal_broadcaster = Node(
        package="my_exer08_follow", executable="goal_broadcaster",
        parameters=[{"goal_x": 1.0, "goal_y": 1.0}]
    )
    follow_controller = Node(
        package="my_exer08_follow", executable="follow_controller"
    )
    return LaunchDescription([goal_broadcaster, follow_controller])
