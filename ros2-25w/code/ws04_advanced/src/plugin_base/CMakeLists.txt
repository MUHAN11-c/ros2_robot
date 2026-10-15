cmake_minimum_required(VERSION 3.8)
project(plugin_base)

find_package(ament_cmake REQUIRED)
find_package(pluginlib REQUIRED)

install(DIRECTORY include/
  DESTINATION include
)

ament_export_include_directories(include)
ament_package()
