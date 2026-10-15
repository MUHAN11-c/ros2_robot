# -*- coding: utf-8 -*-
# 第20周 需求1-1 机器人启动 launch：简单集成(雷达/底盘/相机 驱动节点 + rviz2)
# 说明：驱动节点依赖实体机器人上的驱动包；本 launch 为课程"简单集成/优化集成"结构的还原，
#       实体硬件缺失时各节点会报设备打开失败，可注释对应节点仅做流程验证。
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    # 参数声明；
    declare_use_sim_time = DeclareLaunchArgument("use_sim_time", default_value="false")

    # 1.底盘驱动(里程计)；
    base_driver = Node(
        package="my_exer07_bringup",
        executable="base_driver.py",
        parameters=[{"use_sim_time": use_sim_time}]
    )
    # 2.激光雷达驱动；
    lidar_driver = Node(
        package="my_exer07_bringup",
        executable="lidar_driver.py",
        parameters=[{"use_sim_time": use_sim_time}]
    )
    # 3.相机驱动(usb_cam)；
    camera_driver = Node(
        package="usb_cam", executable="usb_cam_node_exe",
        parameters=[{"use_sim_time": use_sim_time}]
    )
    # 4.机器人模型发布；
    urdf = os.path.join(get_package_share_directory("my_exer07_bringup"), "model", "mycar.urdf.xacro")
    import xacro
    robot_description = xacro.process_file(urdf).toxml()
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description, "use_sim_time": use_sim_time}]
    )

    return LaunchDescription([
        declare_use_sim_time,
        base_driver,
        lidar_driver,
        camera_driver,
        robot_state_publisher,
    ])
