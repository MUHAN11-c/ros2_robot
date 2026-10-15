from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    turtle = Node(package="turtlesim", executable="turtlesim_node", name="sim")
    spawn = Node(
        package="py05_exercise", executable="exer01_spawn_py",
        parameters=[{"turtle_name": "t2"}]
    )
    broadcaster1 = Node(package="py05_exercise", executable="exer02_tf_broadcaster_py", name="b1",
        parameters=[{"turtle": "t1"}]
    )
    broadcaster2 = Node(package="py05_exercise", executable="exer02_tf_broadcaster_py", name="b2",
        parameters=[{"turtle": "t2"}]
    )
    listener = Node(package="py05_exercise", executable="exer03_tf_listener_py",
        parameters=[{"father_frame": "t2", "child_frame": "turtle1"}]
    )
    return LaunchDescription([turtle, spawn, broadcaster1, broadcaster2, listener])
