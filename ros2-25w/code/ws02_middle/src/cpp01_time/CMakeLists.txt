cmake_minimum_required(VERSION 3.8)
project(cpp01_time)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)

add_executable(demo01_time_api src/demo01_time_api.cpp)
ament_target_dependencies(demo01_time_api rclcpp)

install(TARGETS
  demo01_time_api
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
