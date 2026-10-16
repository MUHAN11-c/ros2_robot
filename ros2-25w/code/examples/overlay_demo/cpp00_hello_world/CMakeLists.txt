cmake_minimum_required(VERSION 3.8)
project(cpp00_hello_world)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)

add_executable(demo01_hello_world src/demo01_hello_world.cpp)
ament_target_dependencies(demo01_hello_world rclcpp)

install(TARGETS demo01_hello_world
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
