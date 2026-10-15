# 多车编队 launch：stage 双车仿真 + 领航车目标点发布 + 跟随车控制 + rviz2
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    world = os.path.join(get_package_share_directory("demo_formation"), "worlds", "formation.world")

    # 1.stage 仿真器(双车)；
    stage = Node(
        package="stage_ros2",
        executable="stage_ros2",
        arguments=[world],
        parameters=[{"use_sim_time": True}],
        output="screen"
    )
    # 2.跟随车控制节点；
    follower = Node(
        package="demo_formation",
        executable="formation_follower",
        parameters=[{
            "leader_frame": "robot1",
            "follower_frame": "robot2",
            "formation_offset": 2.0,
            "use_sim_time": True
        }],
        output="screen"
    )
    # 3.rviz2；
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        parameters=[{"use_sim_time": True}]
    )

    return LaunchDescription([stage, follower, rviz2])
