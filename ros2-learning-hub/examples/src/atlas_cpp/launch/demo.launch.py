from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='atlas_cpp', executable='talker', namespace='atlas',
             name='talker', output='screen'),
        Node(package='atlas_py', executable='listener', namespace='atlas',
             name='listener', output='screen'),
    ])
