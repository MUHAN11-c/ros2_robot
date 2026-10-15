cmake_minimum_required(VERSION 3.8)
project(plugin_impl)

find_package(ament_cmake REQUIRED)
find_package(pluginlib REQUIRED)
find_package(plugin_base REQUIRED)

add_library(polygon_impl SHARED src/polygon_plugins.cpp)
target_include_directories(polygon_impl PRIVATE include)
ament_target_dependencies(polygon_impl pluginlib plugin_base)

pluginlib_export_plugin_description_file(plugin_base plugin_impl.xml)

install(TARGETS polygon_impl
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

ament_package()
