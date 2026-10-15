cmake_minimum_required(VERSION 3.8)
project(cpp02_pointcloud_sim)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(pointcloud_sim src/pointcloud_sim.cpp)
ament_target_dependencies(pointcloud_sim rclcpp sensor_msgs)

install(TARGETS
  pointcloud_sim
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
