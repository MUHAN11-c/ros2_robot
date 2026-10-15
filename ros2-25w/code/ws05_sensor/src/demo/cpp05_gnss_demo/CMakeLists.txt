cmake_minimum_required(VERSION 3.8)
project(cpp05_gnss_demo)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(gnss_demo src/gnss_demo.cpp)
ament_target_dependencies(gnss_demo rclcpp sensor_msgs nav_msgs geometry_msgs)

install(TARGETS
  gnss_demo
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
