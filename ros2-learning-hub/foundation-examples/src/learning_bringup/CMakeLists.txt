# 【中文教学注释】 foundation-examples/src/learning_bringup/CMakeLists.txt
# 输入输出：输入是本包源码、已安装依赖及目标配置；输出为构建目标、安装文件和ament导出元数据。
# 执行顺序与边界：先find_package再建立/连接目标并install，最后ament_package；VERSION是工具/语言版本而非物理单位，源码存在不等于已安装入口。
# 声明配置所需最低CMake版本；它不是C++语言标准，也不会自动安装构建工具。
cmake_minimum_required(VERSION 3.8)
# 工程名应与package.xml包名一致，PROJECT_NAME供安装和接口生成目标引用。
project(learning_bringup)
# 在已source的安装前缀查找此依赖并加载导出配置；REQUIRED使缺失时配置失败，不自动从网络获取依赖。
find_package(ament_cmake REQUIRED)
# 将launch/config等运行所需目录复制到包share目录；未安装时源码中存在文件也可能无法按包名启动。
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})
# 完成ament包元数据导出，应在目标、依赖和安装规则之后调用。
ament_package()
