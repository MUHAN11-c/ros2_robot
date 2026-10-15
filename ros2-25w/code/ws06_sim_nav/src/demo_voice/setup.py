from setuptools import find_packages, setup

package_name = 'demo_voice'

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
    description='第25周智能语音：语音指令控制机器人(讯飞SDK集成骨架)',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'voice_controller = demo_voice.voice_controller:main',
            'voice_input = demo_voice.voice_input:main',
        ],
    },
)
