# 【中文教学注释】 foundation-examples/src/learning_bringup/launch/with_parameters.launch.py
# 输入输出：输入为 launch 参数、包内文件路径和 YAML 配置；输出为具有指定命名空间、重映射和参数的节点进程。
# 执行顺序与边界：launch 描述在启动阶段解释，动作书写顺序不等于应用已就绪；相对话题继承命名空间，参数文件顶层节点名必须匹配实际节点。
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


# launch 系统调用此工厂获取动作描述；函数本身不是节点的执行回调，参数替换可延后求值。
def generate_launch_description():
    config_file = PathJoinSubstitution([
        FindPackageShare('learning_bringup'), 'config', 'sim.yaml'])
    # 建立延后求值的 launch 参数替换对象；它不是普通 Python 字符串，执行启动动作时才解析。
    red = ParameterValue(LaunchConfiguration('red'), value_type=int)
    # 返回 launch 动作集合，由启动系统执行；列表顺序不能作为节点发现/生命周期就绪屏障。
    return LaunchDescription([
        # 声明启动参数和默认值；外部 name:=value 可覆盖，参数名需与 LaunchConfiguration 相同。
        DeclareLaunchArgument('red', default_value='160'),
        # 这是launch的Node启动动作：package/executable定位已安装入口，name/namespace决定ROS名称，parameters与remappings在启动阶段配置；不等于rclpy运行期Node对象。
        Node(
            package='turtlesim', executable='turtlesim_node',
            name='config_sim', output='screen',
            parameters=[config_file, {'background_r': red}]),
    ])
