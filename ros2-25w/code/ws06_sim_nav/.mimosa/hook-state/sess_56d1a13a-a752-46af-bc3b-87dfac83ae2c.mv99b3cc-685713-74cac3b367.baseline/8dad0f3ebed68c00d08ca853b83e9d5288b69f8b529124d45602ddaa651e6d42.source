# cartographer 建图 launch
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    lua = os.path.join(get_package_share_directory("demo_slam"), "config", "cartographer.lua")

    cartographer = Node(
        package="cartographer_ros",
        executable="cartographer_node",
        output="screen",
        arguments=["-configuration_directory", os.path.dirname(lua),
                   "-configuration_basename", "cartographer.lua"],
        parameters=[{"use_sim_time": True}]
    )
    occupancy_grid = Node(
        package="cartographer_ros",
        executable="cartographer_occupancy_grid_node",
        output="screen",
        parameters=[{"use_sim_time": True}]
    )
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        parameters=[{"use_sim_time": True}]
    )

    return LaunchDescription([cartographer, occupancy_grid, rviz2])
