# 【中文教学注释】 foundation-examples/src/learning_action_cpp/CMakeLists.txt
# 输入输出：输入是本包源码、已安装依赖及目标配置；输出为构建目标、安装文件和ament导出元数据。
# 执行顺序与边界：先find_package再建立/连接目标并install，最后ament_package；VERSION是工具/语言版本而非物理单位，源码存在不等于已安装入口。
# 声明配置所需最低CMake版本；它不是C++语言标准，也不会自动安装构建工具。
cmake_minimum_required(VERSION 3.8)
# 工程名应与package.xml包名一致，PROJECT_NAME供安装和接口生成目标引用。
project(learning_action_cpp)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# 在已source的安装前缀查找此依赖并加载导出配置；REQUIRED使缺失时配置失败，不自动从网络获取依赖。
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(learning_count_interfaces REQUIRED)
# 把本行源码编成命名可执行目标；还需声明依赖和install规则，才能通过ros2 run找到。
add_executable(server src/server.cpp)
# 为指定目标连接ROS依赖及其包含目录；与package.xml的声明互补，不能只写其中一处。
ament_target_dependencies(server rclcpp rclcpp_action learning_count_interfaces)
# 安装已构建目标到ROS约定位置；普通节点运行入口通常放lib/${PROJECT_NAME}，库与组件的安装规则分别核对。
install(TARGETS server DESTINATION lib/${PROJECT_NAME})
# 完成ament包元数据导出，应在目标、依赖和安装规则之后调用。
ament_package()
