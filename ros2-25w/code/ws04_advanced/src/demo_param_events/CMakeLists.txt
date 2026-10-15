cmake_minimum_required(VERSION 3.8)
project(demo_param_events)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rcl_interfaces REQUIRED)

add_executable(demo_param_events src/demo_param_events.cpp)
ament_target_dependencies(demo_param_events rclcpp rcl_interfaces)

install(TARGETS
  demo_param_events
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
