from setuptools import find_packages, setup

package_name = 'py00_hello_world'

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
    description='第14周 ROS2 快速体验：HelloWorld（Python实现）',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'demo01_hello_world_py = py00_hello_world.demo01_hello_world_py:main',
        ],
    },
)
