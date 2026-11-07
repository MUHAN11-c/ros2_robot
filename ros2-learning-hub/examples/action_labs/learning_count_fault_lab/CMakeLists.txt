# 本包独立构建；输入是本目录源码及已安装的 learning_count_interfaces。
# 输出为一个 C++ 可执行文件和一个 Python 脚本入口，不修改或重复生成 Count 接口。
cmake_minimum_required(VERSION 3.8)
project(learning_count_fault_lab)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(learning_count_interfaces REQUIRED)
add_executable(count_fault_cpp src/count_fault_server.cpp)
ament_target_dependencies(count_fault_cpp rclcpp rclcpp_action learning_count_interfaces)
install(TARGETS count_fault_cpp DESTINATION lib/${PROJECT_NAME})
# Python 是完整单文件，install(PROGRAMS) 设置安装入口执行权限；这里不伪装成 C++ 目标。
install(PROGRAMS scripts/count_fault_server.py
  DESTINATION lib/${PROJECT_NAME} RENAME count_fault_py)
ament_package()
