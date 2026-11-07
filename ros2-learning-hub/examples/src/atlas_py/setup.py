# 【中文教学注释】 examples/src/atlas_py/setup.py
# 输入输出：输入为包名、Python模块、资源文件及入口映射；输出为可安装Python包和console_scripts可执行入口。
# 执行顺序与边界：resource索引/package.xml需安装到正确share目录；入口名=模块:function，setup.cfg将脚本装入lib/包名；此配置没有物理单位或ROS回调循环。
from setuptools import setup

# setuptools读取包元数据、安装资源和入口；name应匹配package.xml，源码模块存在仍须console_scripts和setup.cfg才能由ros2 run找到。
setup(
    name='atlas_py', version='0.1.0', packages=['atlas_py'],
    # 安装ament资源索引、package.xml及需要的share文件；缺失索引时包可能已被pip装入却无法被ROS工具发现。
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/atlas_py']),
        ('share/atlas_py', ['package.xml']),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='ROS 2 Atlas contributors', maintainer_email='learner@example.com',
    description='ROS 2 学习图谱 Python 发布订阅示例', license='Apache-2.0',
    # 把可执行入口名映射到Python模块:function；ros2 run查找的是安装入口，不是任意.py文件名。
    entry_points={'console_scripts': [
        'talker = atlas_py.talker:main',
        'listener = atlas_py.listener:main',
        'add_server = atlas_py.add_server:main',
        'add_client = atlas_py.add_client:main',
    ]},
)
