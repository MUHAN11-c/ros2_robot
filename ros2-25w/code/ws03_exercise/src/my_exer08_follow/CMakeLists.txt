cmake_minimum_required(VERSION 3.8)
project(my_exer08_follow)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(goal_broadcaster src/goal_broadcaster.cpp)
ament_target_dependencies(goal_broadcaster rclcpp tf2 tf2_ros tf2_geometry_msgs geometry_msgs)

add_executable(follow_controller src/follow_controller.cpp)
ament_target_dependencies(follow_controller rclcpp tf2 tf2_ros tf2_geometry_msgs geometry_msgs)

install(TARGETS
  goal_broadcaster
  follow_controller
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch data
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
