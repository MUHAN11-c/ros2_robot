cmake_minimum_required(VERSION 3.8)
project(cpp05_exercise)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(turtlesim REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(exer01_spawn src/exer01_spawn.cpp)
ament_target_dependencies(exer01_spawn rclcpp turtlesim)

add_executable(exer02_tf_broadcaster src/exer02_tf_broadcaster.cpp)
ament_target_dependencies(exer02_tf_broadcaster rclcpp tf2 tf2_ros geometry_msgs turtlesim)

add_executable(exer03_tf_listener src/exer03_tf_listener.cpp)
ament_target_dependencies(exer03_tf_listener rclcpp tf2 tf2_ros tf2_geometry_msgs geometry_msgs)

install(TARGETS
  exer01_spawn
  exer02_tf_broadcaster
  exer03_tf_listener
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
