from setuptools import find_packages, setup

package_name = 'demo_topic_tools'

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
    description='第21周话题统计与话题内容过滤（Python实现）',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'topic_statistics = demo_topic_tools.topic_statistics:main',
            'topic_filter = demo_topic_tools.topic_filter:main',
        ],
    },
)
