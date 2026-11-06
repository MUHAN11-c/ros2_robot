from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config_file = PathJoinSubstitution([
        FindPackageShare('learning_bringup'), 'config', 'sim.yaml'])
    red = ParameterValue(LaunchConfiguration('red'), value_type=int)
    return LaunchDescription([
        DeclareLaunchArgument('red', default_value='160'),
        Node(
            package='turtlesim', executable='turtlesim_node',
            name='config_sim', output='screen',
            parameters=[config_file, {'background_r': red}]),
    ])
