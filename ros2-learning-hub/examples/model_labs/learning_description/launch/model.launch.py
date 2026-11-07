"""从安装share读取Xacro并只启动RSP；不启动GUI、关节状态源或仿真器。

输入：可选轮半径/轮距m、TF帧前缀；输出robot_description和固定/活动TF。
默认尺寸只在Xacro定义，空launch参数沿用它们。校验在创建节点前完成。
"""
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import xacro


def setup(context):
    mappings = {}
    # 教学几何有效范围，不是任意硬件的安全限位。轮距下限留出本例车体/轮宽间隙。
    ranges = {'wheel_radius': (0.04, 0.15), 'wheel_separation': (0.35, 0.80)}
    for name, (low, high) in ranges.items():
        value = LaunchConfiguration(name).perform(context)
        if value:
            try:number = float(value)
            except ValueError:raise ValueError(name + '必须为有限数，单位m')
            if not math.isfinite(number) or not low <= number <= high:
                raise ValueError(f'{name}必须在[{low},{high}]m内且有限')
            mappings[name] = str(number)
    prefix = LaunchConfiguration('frame_prefix').perform(context)
    if prefix and (prefix.startswith('/') or not prefix.endswith('/')):
        raise ValueError('frame_prefix为空或以/结尾，且不以/开头')
    share = Path(get_package_share_directory('learning_description'))
    expanded = xacro.process_file(str(share / 'urdf/robot.urdf.xacro'), mappings=mappings).toxml()
    # 同样核默认值，避免以后只改Xacro默认而绕过launch的尺寸合同。
    model = ET.fromstring(expanded)
    radius = float(model.find("link[@name='left_wheel']/visual/geometry/cylinder").get('radius'))
    origin = model.find("joint[@name='left_wheel_joint']/origin")
    separation = 2 * float(origin.get('xyz').split()[1])
    for name, number in [('wheel_radius', radius), ('wheel_separation', separation)]:
        low, high = ranges[name]
        if not math.isfinite(number) or not low <= number <= high:raise ValueError('Xacro默认'+name+'超出合同')
    # URDF字符串强制str，避免launch_ros按YAML猜测其类型。
    return [Node(package='robot_state_publisher', executable='robot_state_publisher',
                 namespace='model_lab', name='state_publisher', output='screen',
                 parameters=[{'robot_description': ParameterValue(expanded, value_type=str),
                              'frame_prefix': prefix, 'publish_frequency': 20.0}])]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('wheel_radius', default_value='', description='轮半径m；空值采用Xacro默认'),
        DeclareLaunchArgument('wheel_separation', default_value='', description='轮距m；空值采用Xacro默认'),
        DeclareLaunchArgument('frame_prefix', default_value='model/', description='只前缀TF frame，不改关节名字'),
        OpaqueFunction(function=setup)])
