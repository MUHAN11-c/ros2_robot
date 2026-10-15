cmake_minimum_required(VERSION 3.8)
project(my_exer01_topic_pub)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(pub_vel src/pub_vel.cpp)
ament_target_dependencies(pub_vel rclcpp geometry_msgs)

install(TARGETS
  pub_vel
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
