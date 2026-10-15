# launch 之 Python 实现：启动两个 turtlesim 窗口（helloworld 案例）
from launch import LaunchDescription
from launch_ros.actions import Node

# 封装终端指令相关类-------------
# from launch.actions import ExecuteProcess
# 参数声明与获取--------------
# from launch.actions import DeclareLaunchArgument
# from launch.substitutions import LaunchConfiguration
# 文件包含相关--------------
# from launch.actions import IncludeLaunchDescription
# from launch.launch_description_sources import PythonLaunchDescriptionSource
# 分组相关------------------
# from launch_ros.actions import PushRosNamespace
# from launch.actions import GroupAction
# 事件相关------------------
# from launch.event_handlers import OnProcessStart, OnProcessExit
# from launch.actions import ExecuteProcess, RegisterEventHandler,LogInfo
# 获取功能包下share目录路径-------
# from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # 1.启动 turtlesim_node 节点；
    turtle1 = Node(package="turtlesim",executable="turtlesim_node",name="t1")
    # 2.启动第二只乌龟节点；
    turtle2 = Node(package="turtlesim",executable="turtlesim_node",name="t2")

    return LaunchDescription([turtle1, turtle2])
