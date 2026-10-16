cmake_minimum_required(VERSION 3.8)
project(demo_component)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(std_msgs REQUIRED)

# 1.生成组件库(可被容器动态加载)；
add_library(talker_component SHARED src/talker_component.cpp)
target_compile_definitions(talker_component PRIVATE "COMPOSITION_BUILDING_DLL")
ament_target_dependencies(talker_component rclcpp rclcpp_components std_msgs)

add_library(listener_component SHARED src/listener_component.cpp)
target_compile_definitions(listener_component PRIVATE "COMPOSITION_BUILDING_DLL")
ament_target_dependencies(listener_component rclcpp rclcpp_components std_msgs)

# 2.注册组件(同时生成独立的可执行程序便于测试)；
rclcpp_components_register_nodes(talker_component
  "my_component::TalkerComponent"
)
rclcpp_components_register_nodes(listener_component
  "my_component::ListenerComponent"
)

# 3.安装组件库；
install(TARGETS
  talker_component
  listener_component
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

ament_package()
