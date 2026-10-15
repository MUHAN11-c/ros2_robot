from setuptools import find_packages, setup

package_name = 'py02_pointcloud_sim'

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
    description='第22周多线激光雷达仿真案例（Python实现）',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pointcloud_sim_py = py02_pointcloud_sim.pointcloud_sim_py:main',
        ],
    },
)
