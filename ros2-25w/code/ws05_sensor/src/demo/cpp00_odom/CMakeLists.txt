cmake_minimum_required(VERSION 3.8)
project(cpp00_odom)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav_msgs REQUIRED)

add_executable(odom2path src/odom2path.cpp)
ament_target_dependencies(odom2path rclcpp nav_msgs)

install(TARGETS
  odom2path
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
