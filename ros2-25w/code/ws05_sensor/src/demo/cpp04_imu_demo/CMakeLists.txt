cmake_minimum_required(VERSION 3.8)
project(cpp04_imu_demo)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(imu_demo src/imu_demo.cpp)
ament_target_dependencies(imu_demo rclcpp sensor_msgs)

install(TARGETS
  imu_demo
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
