cmake_minimum_required(VERSION 3.8)
project(my_exer03_service_server)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(my_exer_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(cru_server src/cru_server.cpp)
ament_target_dependencies(cru_server rclcpp my_exer_interfaces geometry_msgs)

install(TARGETS
  cru_server
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
