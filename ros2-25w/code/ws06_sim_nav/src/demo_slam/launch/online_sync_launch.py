# slam_toolbox 在线同步建图 launch：仿真(或实体车) + slam_toolbox
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory("demo_slam"),
        "config", "mapper_params_online_sync.yaml")

    # 1.slam_toolbox 在线同步建图节点；
    slam_toolbox = Node(
        package="slam_toolbox",
        executable="sync_slam_toolbox_node",
        name="slam_toolbox",
        output="screen",
        parameters=[config, {"use_sim_time": True}]
    )
    # 2.rviz2(添加 Map/LaserScan/TF 插件查看建图过程)；
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        parameters=[{"use_sim_time": True}]
    )

    return LaunchDescription([slam_toolbox, rviz2])
