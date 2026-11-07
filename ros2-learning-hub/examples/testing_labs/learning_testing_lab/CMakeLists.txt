# 完整独立测试包：算法gtest、消息解释pytest、真实进程/话题launch_testing各注册一个CTest。
cmake_minimum_required(VERSION 3.8)
project(learning_testing_lab)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
add_executable(wheel_processor src/wheel_processor.cpp)
target_include_directories(wheel_processor PRIVATE include)
ament_target_dependencies(wheel_processor rclcpp geometry_msgs std_msgs)
install(TARGETS wheel_processor DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY python/ DESTINATION share/${PROJECT_NAME}/python)

# 只改变测试启动配置，不覆盖源文件、不故意写坏算法；默认关闭受控就绪故障。
option(TESTING_LAB_READY_FAULT "Suppress the application's readiness marker in the launch test" OFF)
if(TESTING_LAB_READY_FAULT)
  set(READY_FAULT_VALUE 1)
else()
  set(READY_FAULT_VALUE 0)
endif()

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  find_package(ament_cmake_pytest REQUIRED)
  find_package(launch_testing_ament_cmake REQUIRED)
  ament_add_gtest(test_wheel_math test/test_wheel_math.cpp)
  target_include_directories(test_wheel_math PRIVATE include)
  ament_add_pytest_test(test_rate_reader test/test_rate_reader.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}/python TIMEOUT 15)
  # ReadyToTest只是框架屏障；文件内另查业务ready标记和真实消息，不用任意长sleep代替。
  add_launch_test(test/test_wheel_launch.py TARGET test_wheel_launch TIMEOUT 25
    ENV TESTING_LAB_READY_FAULT=${READY_FAULT_VALUE})
endif()
ament_export_include_directories(include)
ament_package()
