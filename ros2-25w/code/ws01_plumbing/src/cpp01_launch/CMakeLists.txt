cmake_minimum_required(VERSION 3.8)
project(cpp01_launch)

find_package(ament_cmake REQUIRED)

# 安装三种格式的 launch 文件；
install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
