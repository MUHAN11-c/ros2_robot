cmake_minimum_required(VERSION 3.8)
project(cpp04_tf_listener)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(demo01_tf_listener src/demo01_tf_listener.cpp)
ament_target_dependencies(demo01_tf_listener rclcpp tf2 tf2_ros tf2_geometry_msgs geometry_msgs)

add_executable(demo02_point_listener src/demo02_point_listener.cpp)
ament_target_dependencies(demo02_point_listener rclcpp tf2 tf2_ros tf2_geometry_msgs geometry_msgs)

install(TARGETS
  demo01_tf_listener
  demo02_point_listener
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
