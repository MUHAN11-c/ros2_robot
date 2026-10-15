from setuptools import find_packages, setup

package_name = 'py02_service'

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
    description='第15周服务通信（Python实现）：AddInts 服务端与客户端',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'demo01_server_py = py02_service.demo01_server_py:main',
            'demo02_client_py = py02_service.demo02_client_py:main',
        ],
    },
)
