from setuptools import setup

setup(
    name='atlas_py', version='0.1.0', packages=['atlas_py'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/atlas_py']),
        ('share/atlas_py', ['package.xml']),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='ROS 2 Atlas contributors', maintainer_email='learner@example.com',
    description='ROS 2 学习图谱 Python 发布订阅示例', license='Apache-2.0',
    entry_points={'console_scripts': [
        'talker = atlas_py.talker:main',
        'listener = atlas_py.listener:main',
        'add_server = atlas_py.add_server:main',
        'add_client = atlas_py.add_client:main',
    ]},
)
