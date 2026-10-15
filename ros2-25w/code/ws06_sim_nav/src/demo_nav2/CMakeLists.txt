cmake_minimum_required(VERSION 3.8)
project(demo_nav2)

find_package(ament_cmake REQUIRED)

install(DIRECTORY maps param behavior_trees launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
