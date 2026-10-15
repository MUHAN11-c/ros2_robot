cmake_minimum_required(VERSION 3.8)
project(cpp03_camera_sim)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(camera_sim src/camera_sim.cpp)
ament_target_dependencies(camera_sim rclcpp sensor_msgs)

install(TARGETS
  camera_sim
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
