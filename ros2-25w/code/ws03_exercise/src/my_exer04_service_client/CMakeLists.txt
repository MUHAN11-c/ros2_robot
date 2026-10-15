cmake_minimum_required(VERSION 3.8)
project(my_exer04_service_client)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(my_exer_interfaces REQUIRED)

add_executable(cru_client src/cru_client.cpp)
ament_target_dependencies(cru_client rclcpp my_exer_interfaces)

install(TARGETS
  cru_client
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
