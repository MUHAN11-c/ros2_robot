cmake_minimum_required(VERSION 3.8)
project(intra_process_cpp)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

add_executable(demo_intra_process src/demo_intra_process.cpp)
ament_target_dependencies(demo_intra_process rclcpp std_msgs)

install(TARGETS
  demo_intra_process
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
