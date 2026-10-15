# rviz2 集成 URDF：启动 robot_state_publisher、joint_state_publisher 与 rviz2
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    urdf_dir = os.path.join(get_package_share_directory("cpp06_urdf"), "urdf")
    rviz_dir = os.path.join(get_package_share_directory("cpp06_urdf"), "rviz")

    # 1.加载 urdf 文件内容；
    urdf = os.path.join(urdf_dir, "urdf02_car.urdf")
    with open(urdf, "r") as f:
        robot_description = f.read()

    # 2.发布 robot_description 与 joint_states；
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description}]
    )
    joint_state_publisher = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher"
    )
    # 3.启动 rviz2(加载预置配置)；
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", os.path.join(rviz_dir, "urdf.rviz")]
    )

    return LaunchDescription([robot_state_publisher, joint_state_publisher, rviz2])
