# 导航服务器 launch：加载地图 + 各导航节点 + 生命周期管理器 + rviz2
# 用法：ros2 launch demo_nav2 bringup_launch.py map:=<地图yaml绝对路径>
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    map_file = LaunchConfiguration("map")
    params_file = os.path.join(get_package_share_directory("demo_nav2"), "param", "nav2_params.yaml")

    declare_use_sim_time = DeclareLaunchArgument("use_sim_time", default_value="true")
    declare_map = DeclareLaunchArgument(
        "map",
        default_value=os.path.join(get_package_share_directory("demo_nav2"), "maps", "demo_map.yaml"))

    # 1.地图服务(map_server)；
    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}, {"yaml_filename": map_file}]
    )
    # 2.AMCL 定位；
    amcl = Node(
        package="nav2_amcl",
        executable="amcl",
        name="amcl",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}]
    )
    # 3.规划、控制、行为树、恢复行为；
    planner_server = Node(
        package="nav2_planner",
        executable="planner_server",
        name="planner_server",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}]
    )
    controller_server = Node(
        package="nav2_controller",
        executable="controller_server",
        name="controller_server",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}]
    )
    bt_navigator = Node(
        package="nav2_bt_navigator",
        executable="bt_navigator",
        name="bt_navigator",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}]
    )
    behavior_server = Node(
        package="nav2_behaviors",
        executable="behavior_server",
        name="behavior_server",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}]
    )
    # 4.生命周期管理器(统一激活以上节点)；
    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_navigation",
        output="screen",
        parameters=[params_file, {"use_sim_time": use_sim_time}]
    )
    # 5.rviz2(Navigation2 面板下发目标点)；
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        parameters=[{"use_sim_time": use_sim_time}]
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_map,
        map_server,
        amcl,
        planner_server,
        controller_server,
        bt_navigator,
        behavior_server,
        lifecycle_manager,
        rviz2,
    ])
