cmake_minimum_required(VERSION 3.8)
project(cpp02_rosbag2)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rosbag2_cpp REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(demo01_writer src/demo01_writer.cpp)
ament_target_dependencies(demo01_writer rclcpp rosbag2_cpp geometry_msgs)

add_executable(demo02_reader src/demo02_reader.cpp)
ament_target_dependencies(demo02_reader rclcpp rosbag2_cpp geometry_msgs)

install(TARGETS
  demo01_writer
  demo02_reader
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
