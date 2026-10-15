from setuptools import find_packages, setup

package_name = 'demo_formation'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/formation_launch.py']),
        ('share/' + package_name + '/worlds', ['worlds/formation.world']),
        ('share/' + package_name + '/data', ['data/waypoints.csv']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ros2',
    maintainer_email='ros2@todo.todo',
    description='第25周多车编队：双车仿真 + 跟随控制',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'formation_follower = demo_formation.follower:main',
        ],
    },
)
