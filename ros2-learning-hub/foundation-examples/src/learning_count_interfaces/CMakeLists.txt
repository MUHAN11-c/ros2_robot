# 【中文教学注释】 foundation-examples/src/learning_count_interfaces/CMakeLists.txt
# 输入输出：输入是本包源码、已安装依赖及目标配置；输出为构建目标、安装文件和ament导出元数据。
# 执行顺序与边界：先find_package再建立/连接目标并install，最后ament_package；VERSION是工具/语言版本而非物理单位，源码存在不等于已安装入口。
# 声明配置所需最低CMake版本；它不是C++语言标准，也不会自动安装构建工具。
cmake_minimum_required(VERSION 3.8)
# 工程名应与package.xml包名一致，PROJECT_NAME供安装和接口生成目标引用。
project(learning_count_interfaces)
# 在已source的安装前缀查找此依赖并加载导出配置；REQUIRED使缺失时配置失败，不自动从网络获取依赖。
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(action_msgs REQUIRED)
# 从本包msg/srv/action生成各语言接口；DEPENDENCIES必须列出引用的外部接口包。
rosidl_generate_interfaces(${PROJECT_NAME}
  "action/Count.action"
  DEPENDENCIES action_msgs
)
# 把运行期/构建使用者需要的依赖导出，接口包通常需要rosidl_default_runtime。
ament_export_dependencies(rosidl_default_runtime)
# 完成ament包元数据导出，应在目标、依赖和安装规则之后调用。
ament_package()
