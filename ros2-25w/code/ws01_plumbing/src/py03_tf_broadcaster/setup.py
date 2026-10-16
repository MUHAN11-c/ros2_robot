from setuptools import find_packages, setup

package_name = 'py03_tf_broadcaster'

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
    description='第17周坐标变换广播：静态与动态广播器（Python实现）',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'demo01_static_tf_broadcaster_py = py03_tf_broadcaster.demo01_static_tf_broadcaster_py:main',
            'demo02_dynamic_tf_broadcaster_py = py03_tf_broadcaster.demo02_dynamic_tf_broadcaster_py:main',
            'demo02_point_listener_py = py03_tf_broadcaster.demo02_point_listener_py:main',
        ],
    },
)
