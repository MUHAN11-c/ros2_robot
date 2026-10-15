from setuptools import find_packages, setup

package_name = 'py03_action'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ros2',
    maintainer_email='ros2@todo.todo',
    description='第15周动作通信（Python实现）：Progress 动作服务端与客户端',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'demo01_action_server_py = py03_action.demo01_action_server_py:main',
            'demo02_action_client_py = py03_action.demo02_action_client_py:main',
        ],
    },
)
