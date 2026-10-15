cmake_minimum_required(VERSION 3.8)
project(cpp06_urdf)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch rviz urdf meshes
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
