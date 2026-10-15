# stage_ros2 仿真启动：仿真器 + 机器人模型发布 + rviz2
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    world_path = os.path.join(get_package_share_directory("demo_stage_sim"), "worlds", "stage.world")

    # 1.启动 stage 仿真器；
    stage = Node(
        package="stage_ros2",
        executable="stage_ros2",
        arguments=[world_path],
        parameters=[{"use_sim_time": True}]
    )
    # 2.发布机器人模型与 TF(base_footprint→base_link→laser)；
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"use_sim_time": True}],
        remappings=[("robot_description", "robot_description")]
    )
    # 3.启动 rviz2(添加 LaserScan/TF/RobotModel 插件查看)；
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        parameters=[{"use_sim_time": True}]
    )
    # 4.键盘控制(可选)；
    teleop = Node(
        package="teleop_twist_keyboard",
        executable="teleop_twist_keyboard",
        output="screen",
        remappings=[("cmd_vel", "cmd_vel")]
    )

    return LaunchDescription([stage, robot_state_publisher, rviz2])
