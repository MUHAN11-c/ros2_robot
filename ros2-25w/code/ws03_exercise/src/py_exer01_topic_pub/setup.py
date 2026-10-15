from setuptools import find_packages, setup

package_name = 'py_exer01_topic_pub'

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
    description='第19周 Mycar 实战：速度指令发布(Python实现，圆周运动+动态调参)',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pub_vel_py = py_exer01_topic_pub.pub_vel_py:main',
        ],
    },
)
