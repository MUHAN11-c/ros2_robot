from setuptools import find_packages, setup

package_name = 'py05_gnss_demo'

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
    description='第23周 GNSS 案例：NavSatFix 转 Path（Python实现）',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'gnss_demo_py = py05_gnss_demo.gnss_demo_py:main',
        ],
    },
)
