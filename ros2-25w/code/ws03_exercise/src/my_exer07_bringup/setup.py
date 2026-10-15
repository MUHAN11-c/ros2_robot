from setuptools import find_packages, setup

package_name = 'my_exer07_bringup'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/car_bringup_launch.py']),
        ('share/' + package_name + '/config', ['config/mycar.yaml']),
        ('share/' + package_name + '/model', ['model/mycar.urdf.xacro']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ros2',
    maintainer_email='ros2@todo.todo',
    description='第20周 Mycar 机器人启动集成：launch + 模型 + 配置',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'base_driver.py = my_exer07_bringup.base_driver:main',
            'lidar_driver.py = my_exer07_bringup.lidar_driver:main',
        ],
    },
)
