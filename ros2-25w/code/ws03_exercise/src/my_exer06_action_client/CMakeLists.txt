cmake_minimum_required(VERSION 3.8)
project(my_exer06_action_client)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(my_exer_interfaces REQUIRED)

add_executable(nav_client src/nav_client.cpp)
ament_target_dependencies(nav_client rclcpp rclcpp_action my_exer_interfaces)

install(TARGETS
  nav_client
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
