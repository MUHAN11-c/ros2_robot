cmake_minimum_required(VERSION 3.8)
project(cobot_metapackage)

find_package(ament_cmake REQUIRED)

# 元功能包：无源码、无安装目标，仅聚合依赖（见 package.xml 的 exec_depend）
ament_package()
