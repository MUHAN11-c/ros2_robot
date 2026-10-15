# xacro 优化：加载 xacro 文件并集成 rviz2 显示
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    xacro_dir = os.path.join(get_package_share_directory("cpp07_xacro"), "xacro")
    rviz_dir = os.path.join(get_package_share_directory("cpp07_xacro"), "rviz")

    # 1.加载 xacro 文件(xacro 工具会将 .xacro 处理为 urdf 内容)；
    xacro_file = os.path.join(xacro_dir, "xacro_car.xacro")
    import xacro
    robot_description = xacro.process_file(xacro_file).toxml()

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
    # 3.启动 rviz2；
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", os.path.join(rviz_dir, "urdf.rviz")]
    )

    return LaunchDescription([robot_state_publisher, joint_state_publisher, rviz2])
