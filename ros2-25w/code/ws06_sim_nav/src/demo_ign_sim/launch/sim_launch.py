# ignition gazebo 与 ROS2 集成 launch：启动仿真环境 + 桥接节点 + rviz2
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node


def generate_launch_description():
    world_path = os.path.join(get_package_share_directory("demo_ign_sim"), "worlds", "demo.sdf")
    bridge_yaml = os.path.join(get_package_share_directory("demo_ign_sim"), "config", "bridge.yaml")

    # 1.启动仿真环境；
    # 兼容提示：Humble+Fortress 课程环境为 ["ign","gazebo","-r",world_path]；
    #          Jazzy 配套 Gz Harmonic，命令为 gz sim -r；
    gz_sim = ExecuteProcess(
        cmd=["gz", "sim", "-r", world_path],
        output="screen"
    )
    # 2.桥接节点(ROS2 与 ignition 双向通信)；
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["--ros-args", "-p", f"config_file:={bridge_yaml}"],
        output="screen"
    )
    # 3.rviz2 查看 /scan、/odom、/tf；
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        parameters=[{"use_sim_time": True}]
    )
    # 4.键盘控制；
    teleop = Node(
        package="teleop_twist_keyboard",
        executable="teleop_twist_keyboard",
        output="screen"
    )

    return LaunchDescription([gz_sim, bridge, rviz2])
