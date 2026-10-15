cmake_minimum_required(VERSION 3.8)
project(plugin_loader)

find_package(ament_cmake REQUIRED)
find_package(pluginlib REQUIRED)
find_package(plugin_base REQUIRED)

add_executable(demo_plugin_loader src/demo_plugin_loader.cpp)
ament_target_dependencies(demo_plugin_loader pluginlib plugin_base)

install(TARGETS
  demo_plugin_loader
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
