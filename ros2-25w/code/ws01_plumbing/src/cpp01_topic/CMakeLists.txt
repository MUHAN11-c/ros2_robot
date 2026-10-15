cmake_minimum_required(VERSION 3.8)
project(cpp01_topic)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(base_interfaces_demo REQUIRED)

add_executable(demo01_talker_str src/demo01_talker_str.cpp)
ament_target_dependencies(demo01_talker_str rclcpp std_msgs)

add_executable(demo02_listener_str src/demo02_listener_str.cpp)
ament_target_dependencies(demo02_listener_str rclcpp std_msgs)

add_executable(demo03_talker_stu src/demo03_talker_stu.cpp)
ament_target_dependencies(demo03_talker_stu rclcpp base_interfaces_demo)

add_executable(demo04_listener_stu src/demo04_listener_stu.cpp)
ament_target_dependencies(demo04_listener_stu rclcpp base_interfaces_demo)

install(TARGETS
  demo01_talker_str
  demo02_listener_str
  demo03_talker_stu
  demo04_listener_stu
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
