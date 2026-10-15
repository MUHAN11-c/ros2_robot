cmake_minimum_required(VERSION 3.8)
project(cpp01_laser_sim)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(laser_sim src/laser_sim.cpp)
ament_target_dependencies(laser_sim rclcpp sensor_msgs)

install(TARGETS
  laser_sim
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
