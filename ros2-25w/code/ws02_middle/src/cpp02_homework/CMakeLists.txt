cmake_minimum_required(VERSION 3.8)
project(cpp02_homework)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(turtlesim REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(std_srvs REQUIRED)

add_executable(homework_topic_pub src/homework_topic_pub.cpp)
ament_target_dependencies(homework_topic_pub rclcpp geometry_msgs)

add_executable(homework_param_client src/homework_param_client.cpp)
ament_target_dependencies(homework_param_client rclcpp rcl_interfaces std_srvs)

install(TARGETS
  homework_topic_pub
  homework_param_client
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
