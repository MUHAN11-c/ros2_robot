# 输入：Jazzy依赖及两个原创C++文件；输出共享组件库、独立Config入口及可观察管理容器。
# 构建目录由colcon参数放到/tmp；这里不修改官方包或生成物。
cmake_minimum_required(VERSION 3.8)
project(runtime_lab_components)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)
add_library(runtime_components SHARED src/components.cpp)
target_compile_features(runtime_components PUBLIC cxx_std_17)
ament_target_dependencies(runtime_components rclcpp rclcpp_components rcl_interfaces std_msgs std_srvs)
# 同一Config类既可被容器装入，也可由生成的独立main入口创建；不是复制另一套算法。
rclcpp_components_register_node(runtime_components
  PLUGIN "runtime_lab_components::ConfigComponent" EXECUTABLE config_node)
rclcpp_components_register_nodes(runtime_components
  "runtime_lab_components::SlowComponent" "runtime_lab_components::HeartbeatComponent")
add_executable(observable_manager src/observable_manager.cpp)
target_compile_features(observable_manager PUBLIC cxx_std_17)
ament_target_dependencies(observable_manager rclcpp rclcpp_components)
install(TARGETS runtime_components observable_manager
  ARCHIVE DESTINATION lib LIBRARY DESTINATION lib RUNTIME DESTINATION lib/${PROJECT_NAME})
ament_package()
