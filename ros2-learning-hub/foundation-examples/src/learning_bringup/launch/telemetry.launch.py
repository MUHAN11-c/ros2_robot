from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robot_ns = LaunchConfiguration('robot_ns')
    return LaunchDescription([
        DeclareLaunchArgument('robot_ns', default_value='robot1'),
        Node(
            package='demo_nodes_cpp', executable='talker',
            name='source', namespace=robot_ns, output='screen',
            remappings=[('chatter', 'telemetry')]),
        Node(
            package='demo_nodes_py', executable='listener',
            name='sink', namespace=robot_ns, output='screen',
            remappings=[('chatter', 'telemetry')]),
    ])
