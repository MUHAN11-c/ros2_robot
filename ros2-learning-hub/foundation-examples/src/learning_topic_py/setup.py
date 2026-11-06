from setuptools import setup

package_name = 'learning_topic_py'
setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Learner',
    maintainer_email='learner@example.com',
    description='Python publisher and subscriber lesson',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'talker = learning_topic_py.talker:main',
        'listener = learning_topic_py.listener:main',
    ]},
)
