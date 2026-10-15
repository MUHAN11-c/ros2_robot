cmake_minimum_required(VERSION 3.8)
project(cpp03_tf_broadcaster)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(turtlesim REQUIRED)

add_executable(demo01_static_tf_broadcaster src/demo01_static_tf_broadcaster.cpp)
ament_target_dependencies(demo01_static_tf_broadcaster rclcpp tf2 tf2_ros geometry_msgs)

add_executable(demo02_dynamic_tf_broadcaster src/demo02_dynamic_tf_broadcaster.cpp)
ament_target_dependencies(demo02_dynamic_tf_broadcaster rclcpp tf2 tf2_ros geometry_msgs turtlesim)

install(TARGETS
  demo01_static_tf_broadcaster
  demo02_dynamic_tf_broadcaster
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
