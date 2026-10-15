cmake_minimum_required(VERSION 3.8)
project(lifecycle_cpp)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)

add_executable(demo_lifecycle src/demo_lifecycle.cpp)
ament_target_dependencies(demo_lifecycle rclcpp rclcpp_lifecycle)

install(TARGETS
  demo_lifecycle
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
