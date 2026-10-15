cmake_minimum_required(VERSION 3.8)
project(my_exer02_topic_sub)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(sub_vel src/sub_vel.cpp)
ament_target_dependencies(sub_vel rclcpp geometry_msgs)

install(TARGETS
  sub_vel
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
