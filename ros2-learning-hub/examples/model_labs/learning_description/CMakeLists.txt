cmake_minimum_required(VERSION 3.8)
project(learning_description)
find_package(ament_cmake REQUIRED)
# 输入：本包urdf/launch资源；输出：安装前缀share/learning_description。
# 普通复制安装，实验不启用symlink-install；不能由此推广跨机依赖闭包。
install(DIRECTORY urdf launch DESTINATION share/${PROJECT_NAME}
  PATTERN "__pycache__" EXCLUDE PATTERN "*.pyc" EXCLUDE)
ament_package()
