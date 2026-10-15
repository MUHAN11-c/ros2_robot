# -*- coding: utf-8 -*-
# 第20周 需求1-3 多机器人坐标变换：以 launch 集成方式为两台小车分别广播
# map→robot1_odom、map→robot2_odom 的静态变换，实现多机器人 TF 树隔离。
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    declare_use_sim_time = DeclareLaunchArgument("use_sim_time", default_value="true")

    # 1.广播 map→robot1 的静态坐标变换；
    tf_robot1 = Node(
        package="tf2_ros", executable="static_transform_publisher",
        name="tf_robot1", namespace="robot1",
        arguments=["0", "0", "0", "0", "0", "0", "map", "robot1_odom"],
        parameters=[{"use_sim_time": use_sim_time}]
    )
    # 2.广播 map→robot2 的静态坐标变换；
    tf_robot2 = Node(
        package="tf2_ros", executable="static_transform_publisher",
        name="tf_robot2", namespace="robot2",
        arguments=["1", "0", "0", "0", "0", "0", "map", "robot2_odom"],
        parameters=[{"use_sim_time": use_sim_time}]
    )

    return LaunchDescription([declare_use_sim_time, tf_robot1, tf_robot2])
