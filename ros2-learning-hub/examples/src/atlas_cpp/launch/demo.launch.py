# 【中文教学注释】 examples/src/atlas_cpp/launch/demo.launch.py
# 输入输出：输入为 launch 参数、包内文件路径和 YAML 配置；输出为具有指定命名空间、重映射和参数的节点进程。
# 执行顺序与边界：launch 描述在启动阶段解释，动作书写顺序不等于应用已就绪；相对话题继承命名空间，参数文件顶层节点名必须匹配实际节点。
from launch import LaunchDescription
from launch_ros.actions import Node


# launch 系统调用此工厂获取动作描述；函数本身不是节点的执行回调，参数替换可延后求值。
def generate_launch_description():
    # 返回 launch 动作集合，由启动系统执行；列表顺序不能作为节点发现/生命周期就绪屏障。
    return LaunchDescription([
        # 这是launch的Node启动动作：package/executable定位已安装入口，name/namespace决定ROS名称，parameters与remappings在启动阶段配置；不等于rclpy运行期Node对象。
        Node(package='atlas_cpp', executable='talker', namespace='atlas',
             name='talker', output='screen'),
        Node(package='atlas_py', executable='listener', namespace='atlas',
             name='listener', output='screen'),
    ])
