from setuptools import find_packages, setup

package_name = 'py02_homework'

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
    description='第16周期中大作业（Python）：话题/服务/动作/参数在 turtlesim 上的综合实现',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'homework_topic_pub = py02_homework.homework_topic_pub:main',
            'homework_service_client = py02_homework.homework_service_client:main',
            'homework_action_server = py02_homework.homework_action_server:main',
            'homework_param_client = py02_homework.homework_param_client:main',
        ],
    },
)
