cmake_minimum_required(VERSION 3.8)
project(my_exer05_action_server)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(my_exer_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)

add_executable(nav_server src/nav_server.cpp)
ament_target_dependencies(nav_server rclcpp rclcpp_action my_exer_interfaces geometry_msgs nav_msgs)

install(TARGETS
  nav_server
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
