# ROS 2 本地教程与官方示例资料库

清点时间：2026-11-07T01:34:51+08:00。

本轮下载 **99 个来源条目、151 份分支快照**，另复用原有 **11 份快照**；已补充子模块 **12 份**、LFS 资源 **7 个**。
资料文件合计约 **3.40 GiB**，保留的原始压缩包另外占用空间。

这份记录只说明原始资料下载、清点与完整性核查；原始第三方工程未批量构建或运行。当前中文教材及原创示例的独立整合/实测范围见 [教材验证](../VALIDATION.md)，不宣称这些资料已经逐段全部编入教材。

99是来源配置条目数，其中ros2/rttest与ros2/realtime_support使用相同归档，不视为两门独立课程；准确重复关系见 `../source/local-library.json`。
文件数量包含导航、配置、图片与测试，文档文件数量也包含 README 等辅助文档，均不代表教学细节已穷尽。

## 查阅入口

- [完整来源、分支、提交、许可与缺项清单](manifest.json)
- [文档文件索引：Markdown、RST、PDF、Notebook](documents.csv)
- [ROS 包与其声明许可证索引](packages.csv)
- [原始压缩包 SHA256](ARCHIVES.sha256)；[源码逐文件 SHA256](SOURCE_FILES.sha256)
- [下载来源配置](catalog.json)
- [本轮核查记录与验证边界](VALIDATION.md)

## 官方版本范围

`ros2/examples`、`ros2/demos` 和 `ros2/ros2` 按实际存在的发行版分支保存；官方文档库保存当前能取到的发行版分支。
`ros2/ros2_documentation` 没有独立的 Ardent、Bouncy 分支，未把其他分支冒充这两个版本的完整历史文档。
其余项目以 Jazzy 分支优先；无 Jazzy 分支时使用清单中明确记录的其他分支。main、master、rolling、ros2 分支不等于已验证兼容 Jazzy。

## 来源与许可

每个目录保留上游许可证与原注释，不对第三方源码重新许可。许可证未明确的资料只登记实际情况，不能因公开可访问就视为自由转载。
带 NC/ND 等条件的正文与代码可能适用不同许可，后续整合需逐项查看原始条款；下载资料尚未统一添加中文教学注释。
`sources/` 和 `archives/` 已从 Git 跟踪中排除，也不自动打入现有教材 ZIP；迁移这些本地资料需要额外复制整个 references 目录。

## 下载与校验

从工作区根目录执行：

```bash
# 下载：并发单位为独立公开仓库或快照；复用本轮锁定的提交。
python3 ros2-learning-hub/scripts/download_ros2_references.py --jobs 6
# 补齐源码归档未包含的子模块，严格使用父仓库记录的提交。
python3 ros2-learning-hub/scripts/complete_reference_submodules.py --include-lfs
# 清点：完全离线，逐文件计算 SHA256；不会运行第三方工程。
python3 ros2-learning-hub/scripts/index_ros2_references.py
# 验证压缩包：需要从 references 目录运行，路径均相对该目录。
cd ros2-learning-hub/references
sha256sum --check --quiet ARCHIVES.sha256
# 原有参考快照也在校验范围；正常完成不应有 FAILED。
sha256sum --check --quiet SOURCE_FILES.sha256
```

## 本地快照目录

### 官方文档

| 资料 | 实际分支 | 本地目录 |
| --- | --- | --- |
| [ROS 2 架构设计文档](https://github.com/ros2/design) | `gh-pages` | [打开](sources/official-docs/ros2--design/gh-pages--93a415bf9287) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `ardent` | [打开](sources/official-docs/ros2--ros2/ardent--dd8abd45da39) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `bouncy` | [打开](sources/official-docs/ros2--ros2/bouncy--8b84845cdd33) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `crystal` | [打开](sources/official-docs/ros2--ros2/crystal--ce076e12432d) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `dashing` | [打开](sources/official-docs/ros2--ros2/dashing--2826393d1f06) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `eloquent` | [打开](sources/official-docs/ros2--ros2/eloquent--9305b269f38b) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `foxy` | [打开](sources/official-docs/ros2--ros2/foxy--3bc9b4cd9a66) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `galactic` | [打开](sources/official-docs/ros2--ros2/galactic--9e3abd607de3) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `humble` | [打开](sources/official-docs/ros2--ros2/humble--0c6ced5a1903) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `iron` | [打开](sources/official-docs/ros2--ros2/iron--bfd587fdda36) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `jazzy` | [打开](sources/official-docs/ros2--ros2/jazzy--cf1dbea3c2df) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `kilted` | [打开](sources/official-docs/ros2--ros2/kilted--dbce0ebefe09) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `lyrical` | [打开](sources/official-docs/ros2--ros2/lyrical--c2cce9847436) |
| [ROS 2 各发行版源码清单与发行说明](https://github.com/ros2/ros2) | `rolling` | [打开](sources/official-docs/ros2--ros2/rolling--f6edfcd522ab) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `crystal` | [打开](sources/official-docs/ros2--ros2_documentation/crystal--87cfe1360ac0) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `dashing` | [打开](sources/official-docs/ros2--ros2_documentation/dashing--04cc5b685e3d) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `eloquent` | [打开](sources/official-docs/ros2--ros2_documentation/eloquent--8bef6176f27e) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `foxy` | [打开](sources/official-docs/ros2--ros2_documentation/foxy--0fc549645b3c) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `galactic` | [打开](sources/official-docs/ros2--ros2_documentation/galactic--805725ee6952) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `humble` | [打开](sources/official-docs/ros2--ros2_documentation/humble--53b09f47a579) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `iron` | [打开](sources/official-docs/ros2--ros2_documentation/iron--a7f82a0fdd3e) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `jazzy` | [打开](sources/official-docs/ros2--ros2_documentation/jazzy--929e37c4c6d0) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `kilted` | [打开](sources/official-docs/ros2--ros2_documentation/kilted--7af7bf24d084) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `lyrical` | [打开](sources/official-docs/ros2--ros2_documentation/lyrical--feb7ce6372c5) |
| [ROS 2 官方完整文档与教程（含图片和代码片段）](https://github.com/ros2/ros2_documentation) | `rolling` | [打开](sources/official-docs/ros2--ros2_documentation/rolling--30e509d6839c) |

### 官方及官方教程配套示例

| 资料 | 实际分支 | 本地目录 |
| --- | --- | --- |
| [官方 rqt_bag 插件教程配套源码](https://github.com/MetroRobots/rqt_bag_diagnostics_demo) | `main` | [打开](sources/official-examples/MetroRobots--rqt_bag_diagnostics_demo/main--3a370f1bccd9) |
| [官方 RViz 自定义面板教程配套源码](https://github.com/MetroRobots/rviz_panel_tutorial) | `main` | [打开](sources/official-examples/MetroRobots--rviz_panel_tutorial/main--cd472fe33e15) |
| [官方 RViz 自定义显示插件教程配套源码](https://github.com/MetroRobots/rviz_plugin_tutorial) | `main` | [打开](sources/official-examples/MetroRobots--rviz_plugin_tutorial/main--77596e8122f9) |
| [Gazebo 官方 ROS 2 工程模板与示例](https://github.com/gazebosim/ros_gz_project_template) | `main` | [打开](sources/official-examples/gazebosim--ros_gz_project_template/main--045e981d03aa) |
| [tf2 坐标变换官方教学代码](https://github.com/ros/geometry_tutorials) | `jazzy` | [打开](sources/official-examples/ros--geometry_tutorials/jazzy--f9aaaff7e61d) |
| [官方 turtlesim 与 ROS 基础示例](https://github.com/ros/ros_tutorials) | `humble` | [打开](sources/official-examples/ros--ros_tutorials/humble--23877fdd9ad9) |
| [官方 turtlesim 与 ROS 基础示例](https://github.com/ros/ros_tutorials) | `iron` | [打开](sources/official-examples/ros--ros_tutorials/iron--441071ee5227) |
| [官方 turtlesim 与 ROS 基础示例](https://github.com/ros/ros_tutorials) | `jazzy` | [打开](sources/official-examples/ros--ros_tutorials/jazzy--c83136eb8d0d) |
| [官方 turtlesim 与 ROS 基础示例](https://github.com/ros/ros_tutorials) | `kilted` | [打开](sources/official-examples/ros--ros_tutorials/kilted--afd34def0720) |
| [官方 turtlesim 与 ROS 基础示例](https://github.com/ros/ros_tutorials) | `lyrical` | [打开](sources/official-examples/ros--ros_tutorials/lyrical--578a96d76f98) |
| [官方 turtlesim 与 ROS 基础示例](https://github.com/ros/ros_tutorials) | `rolling` | [打开](sources/official-examples/ros--ros_tutorials/rolling--6d39ef7bf992) |
| [URDF 运动与仿真教学示例](https://github.com/ros/urdf_sim_tutorial) | `ros2` | [打开](sources/official-examples/ros--urdf_sim_tutorial/ros2--b11f6aff4377) |
| [URDF 建模官方教程](https://github.com/ros/urdf_tutorial) | `ros2` | [打开](sources/official-examples/ros--urdf_tutorial/ros2--050f1e47cfdb) |
| [图像传输发布订阅官方教程](https://github.com/ros-perception/image_transport_tutorials) | `jazzy` | [打开](sources/official-examples/ros-perception--image_transport_tutorials/jazzy--77fa02f7023b) |
| [ROS 安全工作组 TurtleBot3 安全示例](https://github.com/ros-swg/turtlebot3_demo) | `master` | [打开](sources/official-examples/ros-swg--turtlebot3_demo/master--2719e0f57902) |
| [RViz Marker 与交互可视化教程](https://github.com/ros-visualization/visualization_tutorials) | `rolling` | [打开](sources/official-examples/ros-visualization--visualization_tutorials/rolling--9193554ffe90) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `ardent` | [打开](sources/official-examples/ros2--demos/ardent--ac2db5662a45) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `bouncy` | [打开](sources/official-examples/ros2--demos/bouncy--4c632b30ee1d) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `crystal` | [打开](sources/official-examples/ros2--demos/crystal--f2ad8eba721b) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `dashing` | [打开](sources/official-examples/ros2--demos/dashing--2ed9bb4c44bb) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `eloquent` | [打开](sources/official-examples/ros2--demos/eloquent--eb904895a136) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `foxy` | [打开](sources/official-examples/ros2--demos/foxy--1d01c8e3d066) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `galactic` | [打开](sources/official-examples/ros2--demos/galactic--26e048b88ac1) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `humble` | [打开](sources/official-examples/ros2--demos/humble--1fc7a62ee591) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `iron` | [打开](sources/official-examples/ros2--demos/iron--afbf8c012419) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `jazzy` | [打开](sources/official-examples/ros2--demos/jazzy--37e25e0dece3) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `kilted` | [打开](sources/official-examples/ros2--demos/kilted--576916001b18) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `lyrical` | [打开](sources/official-examples/ros2--demos/lyrical--0ccaf57c2b1d) |
| [官方通信、Action、QoS、生命周期、组件与实时演示](https://github.com/ros2/demos) | `rolling` | [打开](sources/official-examples/ros2--demos/rolling--40461d6a82f5) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `ardent` | [打开](sources/official-examples/ros2--examples/ardent--c501af0ddaaa) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `bouncy` | [打开](sources/official-examples/ros2--examples/bouncy--f6027edfb3a2) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `crystal` | [打开](sources/official-examples/ros2--examples/crystal--62b2132f8e03) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `dashing` | [打开](sources/official-examples/ros2--examples/dashing--166c8294ab99) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `eloquent` | [打开](sources/official-examples/ros2--examples/eloquent--fbab64492748) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `foxy` | [打开](sources/official-examples/ros2--examples/foxy--fa10c2261064) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `galactic` | [打开](sources/official-examples/ros2--examples/galactic--1e8401d1c4b3) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `humble` | [打开](sources/official-examples/ros2--examples/humble--09899ca6b636) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `iron` | [打开](sources/official-examples/ros2--examples/iron--d36053ef0a88) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `jazzy` | [打开](sources/official-examples/ros2--examples/jazzy--07008852303f) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `kilted` | [打开](sources/official-examples/ros2--examples/kilted--86ad8cf99d21) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `lyrical` | [打开](sources/official-examples/ros2--examples/lyrical--cc721964a791) |
| [官方 C++、Python、launch_testing 示例](https://github.com/ros2/examples) | `rolling` | [打开](sources/official-examples/ros2--examples/rolling--74deefcf9d6d) |
| [micro-ROS C API 与 rclc 官方示例](https://github.com/ros2/rclc) | `jazzy` | [打开](sources/official-examples/ros2--rclc/jazzy--45ef3de56758) |

### 官方工具与配套库

| 资料 | 实际分支 | 本地目录 |
| --- | --- | --- |
| [插件加载与插件教程配套库](https://github.com/ros/pluginlib) | `jazzy` | [打开](sources/official-core/ros--pluginlib/jazzy--3e59af469b27) |
| [官方追踪教程所用分析示例与 Notebook](https://github.com/ros-tracing/tracetools_analysis) | `jazzy` | [打开](sources/official-core/ros-tracing--tracetools_analysis/jazzy--aebecc5a3abf) |
| [交互 Marker 服务与示例依赖](https://github.com/ros-visualization/interactive_markers) | `jazzy` | [打开](sources/official-core/ros-visualization--interactive_markers/jazzy--4a525577788b) |
| [rqt_bag 官方插件教程依赖](https://github.com/ros-visualization/rqt_bag) | `jazzy` | [打开](sources/official-core/ros-visualization--rqt_bag/jazzy--843c19f26fda) |
| [标准消息接口](https://github.com/ros2/common_interfaces) | `jazzy` | [打开](sources/official-core/ros2--common_interfaces/jazzy--a941f14bb318) |
| [官方示例配套消息、服务、Action](https://github.com/ros2/example_interfaces) | `jazzy` | [打开](sources/official-core/ros2--example_interfaces/jazzy--4ed406d1277d) |
| [tf2 库、工具、测试和说明](https://github.com/ros2/geometry2) | `jazzy` | [打开](sources/official-core/ros2--geometry2/jazzy--f702874b1c85) |
| [launch 核心、前端语法与示例](https://github.com/ros2/launch) | `jazzy` | [打开](sources/official-core/ros2--launch/jazzy--ede227f7d0d0) |
| [ROS launch 与 launch_testing_ros 示例](https://github.com/ros2/launch_ros) | `jazzy` | [打开](sources/official-core/ros2--launch_ros/jazzy--97b758478d8b) |
| [参数、日志与生命周期接口](https://github.com/ros2/rcl_interfaces) | `jazzy` | [打开](sources/official-core/ros2--rcl_interfaces/jazzy--7aa3caf43377) |
| [C++ 客户端 API 文档与示例](https://github.com/ros2/rclcpp) | `jazzy` | [打开](sources/official-core/ros2--rclcpp/jazzy--35b821a9fb1f) |
| [Python 客户端 API 文档与示例](https://github.com/ros2/rclpy) | `jazzy` | [打开](sources/official-core/ros2--rclpy/jazzy--521012e60ba2) |
| [ROS 2 实时分配器与实时编程示例依赖](https://github.com/ros2/realtime_support) | `jazzy` | [打开](sources/official-core/ros2--realtime_support/jazzy--bdb771125271) |
| [Zenoh 通信后端文档与示例](https://github.com/ros2/rmw_zenoh) | `jazzy` | [打开](sources/official-core/ros2--rmw_zenoh/jazzy--d328f2644fda) |
| [ROS 1 与 ROS 2 桥接官方示例](https://github.com/ros2/ros1_bridge) | `master` | [打开](sources/official-core/ros2--ros1_bridge/master--611755fd9172) |
| [ROS 2 跟踪与性能分析教程](https://github.com/ros2/ros2_tracing) | `jazzy` | [打开](sources/official-core/ros2--ros2_tracing/jazzy--615d3dc1ea9c) |
| [ROS 2 命令行与扩展机制](https://github.com/ros2/ros2cli) | `jazzy` | [打开](sources/official-core/ros2--ros2cli/jazzy--221ce584a937) |
| [录制回放、存储插件与相关示例](https://github.com/ros2/rosbag2) | `jazzy` | [打开](sources/official-core/ros2--rosbag2/jazzy--12b5e8ba4eb5) |
| [自定义接口生成器与说明](https://github.com/ros2/rosidl) | `jazzy` | [打开](sources/official-core/ros2--rosidl/jazzy--63d63e8ec68e) |
| [ROS 2 实时性能测量工具和示例](https://github.com/ros2/rttest) | `jazzy` | [打开](sources/official-core/ros2--rttest/jazzy--bdb771125271) |
| [RViz2 插件、默认显示与使用说明](https://github.com/ros2/rviz) | `jazzy` | [打开](sources/official-core/ros2--rviz/jazzy--e2e1a1562ae5) |
| [DDS 安全工具与官方安全示例](https://github.com/ros2/sros2) | `jazzy` | [打开](sources/official-core/ros2--sros2/jazzy--80a08ffa1bcc) |

### 主要生态教程与示例

| 资料 | 实际分支 | 本地目录 |
| --- | --- | --- |
| [Isaac ROS 官方示例与配置](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_examples) | `main` | [打开](sources/ecosystem/NVIDIA-ISAAC-ROS--isaac_ros_examples/main--3c00ed97e104) |
| [PX4 ROS 2 示例配套消息](https://github.com/PX4/px4_msgs) | `main` | [打开](sources/ecosystem/PX4--px4_msgs/main--2734ff829935) |
| [PX4 官方 ROS 2 飞行控制示例](https://github.com/PX4/px4_ros_com) | `main` | [打开](sources/ecosystem/PX4--px4_ros_com/main--86e9aeb20e55) |
| [TurtleBot3 官方教学机器人功能包](https://github.com/ROBOTIS-GIT/turtlebot3) | `jazzy` | [打开](sources/ecosystem/ROBOTIS-GIT--turtlebot3/jazzy--0c0be84e3f5c) |
| [TurtleBot3 示例消息依赖](https://github.com/ROBOTIS-GIT/turtlebot3_msgs) | `jazzy` | [打开](sources/ecosystem/ROBOTIS-GIT--turtlebot3_msgs/jazzy--9209e01b4708) |
| [TurtleBot3 官方仿真教程工程](https://github.com/ROBOTIS-GIT/turtlebot3_simulations) | `jazzy` | [打开](sources/ecosystem/ROBOTIS-GIT--turtlebot3_simulations/jazzy--45633014a14e) |
| [SLAM Toolbox 建图定位说明与示例](https://github.com/SteveMacenski/slam_toolbox) | `jazzy` | [打开](sources/ecosystem/SteveMacenski--slam_toolbox/jazzy--f84dad92a657) |
| [状态估计、传感器融合教程与配置示例](https://github.com/cra-ros-pkg/robot_localization) | `jazzy-devel` | [打开](sources/ecosystem/cra-ros-pkg--robot_localization/jazzy-devel--fea7fc3dcad8) |
| [状态估计、传感器融合教程与配置示例](https://github.com/cra-ros-pkg/robot_localization) | `rolling-devel` | [打开](sources/ecosystem/cra-ros-pkg--robot_localization/rolling-devel--b1e373177cc8) |
| [Webots 官方 ROS 2 教程与示例机器人](https://github.com/cyberbotics/webots_ros2) | `master` | [打开](sources/ecosystem/cyberbotics--webots_ros2/master--5f1a18219a6b) |
| [Gazebo 各版本教程（含 Harmonic）](https://github.com/gazebosim/docs) | `master` | [打开](sources/ecosystem/gazebosim--docs/master--05287873c23e) |
| [ROS 2 与 Gazebo 桥接、仿真演示](https://github.com/gazebosim/ros_gz) | `jazzy` | [打开](sources/ecosystem/gazebosim--ros_gz/jazzy--3c15c8edeb74) |
| [micro-ROS Agent 官方源码与说明](https://github.com/micro-ROS/micro-ROS-Agent) | `jazzy` | [打开](sources/ecosystem/micro-ROS--micro-ROS-Agent/jazzy--7c932329ad55) |
| [micro-ROS 官方演示程序](https://github.com/micro-ROS/micro-ROS-demos) | `jazzy` | [打开](sources/ecosystem/micro-ROS--micro-ROS-demos/jazzy--83c438183761) |
| [micro-ROS 官方教程网站源码（历史入口）](https://github.com/micro-ROS/micro-ROS.github.io) | `master` | [打开](sources/ecosystem/micro-ROS--micro-ROS.github.io/master--1b1b14116183) |
| [micro-ROS Arduino 官方示例与发布库](https://github.com/micro-ROS/micro_ros_arduino) | `jazzy` | [打开](sources/ecosystem/micro-ROS--micro_ros_arduino/jazzy--5917738c089d) |
| [micro-ROS ESP-IDF 实践与示例](https://github.com/micro-ROS/micro_ros_espidf_component) | `jazzy` | [打开](sources/ecosystem/micro-ROS--micro_ros_espidf_component/jazzy--5cd71f525eed) |
| [micro-ROS PlatformIO 实践与示例](https://github.com/micro-ROS/micro_ros_platformio) | `main` | [打开](sources/ecosystem/micro-ROS--micro_ros_platformio/main--cfee17faffaa) |
| [micro-ROS Pico 官方示例](https://github.com/micro-ROS/micro_ros_raspberrypi_pico_sdk) | `jazzy` | [打开](sources/ecosystem/micro-ROS--micro_ros_raspberrypi_pico_sdk/jazzy--339ae3f166bd) |
| [micro-ROS 固件工作空间教程与构建配置](https://github.com/micro-ROS/micro_ros_setup) | `jazzy` | [打开](sources/ecosystem/micro-ROS--micro_ros_setup/jazzy--ed45678c6c0b) |
| [MoveIt 2 官方源码与教程对应实现](https://github.com/moveit/moveit2) | `jazzy` | [打开](sources/ecosystem/moveit--moveit2/jazzy--f11204b8a9b9) |
| [MoveIt 2 官方完整教程与示例](https://github.com/moveit/moveit2_tutorials) | `main` | [打开](sources/ecosystem/moveit--moveit2_tutorials/main--e1b3727d4bbd) |
| [MoveIt 教程所用机器人模型与资源](https://github.com/moveit/moveit_resources) | `ros2` | [打开](sources/ecosystem/moveit--moveit_resources/ros2--e1657c128ea6) |
| [MoveIt Task Constructor 抓取规划示例](https://github.com/moveit/moveit_task_constructor) | `ros2` | [打开](sources/ecosystem/moveit--moveit_task_constructor/ros2--f527048b3db1) |
| [Open-RMF 多机器人协调官方演示](https://github.com/open-rmf/rmf_demos) | `jazzy` | [打开](sources/ecosystem/open-rmf--rmf_demos/jazzy--3f7b9727ce39) |
| [Programming Multiple Robots with ROS 2 教材](https://github.com/osrf/ros2multirobotbook) | `master` | [打开](sources/ecosystem/osrf--ros2multirobotbook/master--efc728d764c2) |
| [机器人状态发布与 TF 教程依赖](https://github.com/ros/robot_state_publisher) | `jazzy` | [打开](sources/ecosystem/ros--robot_state_publisher/jazzy--d1b994d2d2eb) |
| [Xacro 模型宏与文档示例](https://github.com/ros/xacro) | `ros2` | [打开](sources/ecosystem/ros--xacro/ros2--da4b3849f832) |
| [ros2_control 官方文档站源文件](https://github.com/ros-controls/control.ros.org) | `jazzy` | [打开](sources/ecosystem/ros-controls--control.ros.org/jazzy--6d979c634bd9) |
| [Gazebo 与 ros2_control 集成示例](https://github.com/ros-controls/gz_ros2_control) | `jazzy` | [打开](sources/ecosystem/ros-controls--gz_ros2_control/jazzy--b49f1ff7de1b) |
| [ros2_control 官方分步实操讲习班](https://github.com/ros-controls/roscon2022_workshop) | `master` | [打开](sources/ecosystem/ros-controls--roscon2022_workshop/master--358534017cc7) |
| [CANopen 教程、机器人总线示例](https://github.com/ros-industrial/ros2_canopen) | `humble` | [打开](sources/ecosystem/ros-industrial--ros2_canopen/humble--fef50e54b1c9) |
| [Nav2 官方完整教程与配置文档](https://github.com/ros-navigation/docs.nav2.org) | `jazzy` | [打开](sources/ecosystem/ros-navigation--docs.nav2.org/jazzy--b22554cb703b) |
| [Nav2 官方最小机器人仿真示例](https://github.com/ros-navigation/nav2_minimal_turtlebot_simulation) | `jazzy` | [打开](sources/ecosystem/ros-navigation--nav2_minimal_turtlebot_simulation/jazzy--b9d523ad7ea0) |
| [Nav2 框架与 Simple Commander 示例](https://github.com/ros-navigation/navigation2) | `jazzy` | [打开](sources/ecosystem/ros-navigation--navigation2/jazzy--94d1c2a345dd) |
| [Nav2 官方教程配套工程](https://github.com/ros-navigation/navigation2_tutorials) | `jazzy` | [打开](sources/ecosystem/ros-navigation--navigation2_tutorials/jazzy--f3bd892a60d3) |
| [图像传输与相机标定配套库](https://github.com/ros-perception/image_common) | `jazzy` | [打开](sources/ecosystem/ros-perception--image_common/jazzy--1a0970345d50) |
| [相机标定、深度与立体视觉教程](https://github.com/ros-perception/image_pipeline) | `jazzy` | [打开](sources/ecosystem/ros-perception--image_pipeline/jazzy--6c3df3099bc7) |
| [PCL 点云与 ROS 2 集成示例](https://github.com/ros-perception/perception_pcl) | `jazzy` | [打开](sources/ecosystem/ros-perception--perception_pcl/jazzy--c5e7e72d20cb) |
| [cv_bridge 与 OpenCV 集成说明](https://github.com/ros-perception/vision_opencv) | `humble` | [打开](sources/ecosystem/ros-perception--vision_opencv/humble--9800f67cea47) |

### 中文社区课程

| 资料 | 实际分支 | 本地目录 |
| --- | --- | --- |
| [Seeed 中英文 ROS 2 与机器人课程](https://github.com/Seeed-Projects/AI_Robotics_Academy) | `main` | [打开](sources/community-zh/Seeed-Projects--AI_Robotics_Academy/main--31101a9e0fe2) |
| [动手学 ROS 2 中文教程正文](https://github.com/fishros/d2l-ros2) | `humble` | [打开](sources/community-zh/fishros--d2l-ros2/humble--45e357ad1ee9) |
| [FishBot 建模、仿真、建图与导航工程](https://github.com/fishros/fishbot) | `humble` | [打开](sources/community-zh/fishros--fishbot/humble--3e486537c2ce) |
| [动手学 ROS 2 配套示例源码](https://github.com/fishros/ros2_town) | `master` | [打开](sources/community-zh/fishros--ros2_town/master--26620aefcb7b) |
| [ROS 2 机器人开发书籍配套源码](https://github.com/fishros/ros2bookcode) | `master` | [打开](sources/community-zh/fishros--ros2bookcode/master--eae7589392c2) |
| [古月 ROS 2 入门 21 讲示例](https://github.com/guyuehome/ros2_21_tutorials) | `master` | [打开](sources/community-zh/guyuehome--ros2_21_tutorials/master--a12b2ee9d5f3) |

### 英文社区课程

| 资料 | 实际分支 | 本地目录 |
| --- | --- | --- |
| [大学课程 C++ 与 Python ROS 2 详细注释示例](https://github.com/IntelligentSystemsLabUTV/ros2-examples) | `jazzy` | [打开](sources/community-en/IntelligentSystemsLabUTV--ros2-examples/jazzy--bbd9848713b3) |
| [ROS Simplified 入门系列正文](https://github.com/Satyarth-Shree/ros2-guides) | `main` | [打开](sources/community-en/Satyarth-Shree--ros2-guides/main--f589de46aa75) |
| [ROS 2 接口、通信、仿真教学工作空间](https://github.com/alejotoro-o/ros2-tutorials-ws) | `main` | [打开](sources/community-en/alejotoro-o--ros2-tutorials-ws/main--84f52a5a87b5) |
| [Automatic Addison Jazzy 基础教学示例](https://github.com/automaticaddison/jazzy_ros2_fundamentals_examples) | `main` | [打开](sources/community-en/automaticaddison--jazzy_ros2_fundamentals_examples/main--88b87438da37) |
| [Automatic Addison MoveIt 2 与机械臂教程](https://github.com/automaticaddison/mycobot_ros2) | `jazzy` | [打开](sources/community-en/automaticaddison--mycobot_ros2/jazzy--a75c80dfbf60) |
| [Automatic Addison ROS 2 基础教学示例](https://github.com/automaticaddison/ros2_fundamentals_examples) | `main` | [打开](sources/community-en/automaticaddison--ros2_fundamentals_examples/main--29645563fe9e) |
| [Automatic Addison Nav2 移动机器人教程](https://github.com/automaticaddison/yahboom_rosmaster) | `jazzy` | [打开](sources/community-en/automaticaddison--yahboom_rosmaster/jazzy--b0e7b5ccfdad) |
| [Articulated Robotics 移动机器人完整教学工程](https://github.com/joshnewans/articubot_one) | `humble` | [打开](sources/community-en/joshnewans--articubot_one/humble--44d512788152) |
| [Articulated Robotics 差速底盘硬件接口](https://github.com/joshnewans/diffdrive_arduino) | `humble` | [打开](sources/community-en/joshnewans--diffdrive_arduino/humble--e5eddd2982f4) |
| [Articulated Robotics 移动机器人教学工程](https://github.com/joshnewans/my_bot) | `main` | [打开](sources/community-en/joshnewans--my_bot/main--bc8b67fed5ce) |
| [ROS 2 Jazzy 课程与实验手册](https://github.com/likerobotics/ros2_course) | `main` | [打开](sources/community-en/likerobotics--ros2_course/main--5173def30f42) |
| [ROS 2 Cookbook 工程实践速查](https://github.com/mikeferguson/ros2_cookbook) | `main` | [打开](sources/community-en/mikeferguson--ros2_cookbook/main--5824c7abe080) |
| [Murilo 的 ROS 2 Jazzy 教程正文与示例](https://github.com/mmmarinho/ROS2_Tutorial) | `main` | [打开](sources/community-en/mmmarinho--ROS2_Tutorial/main--4ea84eeff3b2) |
| [ROS 2 Jazzy 七模块课程、幻灯片与实验](https://github.com/pawelir/ros2_course) | `main` | [打开](sources/community-en/pawelir--ros2_course/main--ff7ceed67f7e) |
| [LIMO Cobot 四天 ROS 2 教学讲义](https://github.com/zeeshanhaider1007/ROS2_Limo_Cobot_Training) | `main` | [打开](sources/community-en/zeeshanhaider1007--ROS2_Limo_Cobot_Training/main--5d8b300474b9) |

### 原有教程与参考工程

| 资料 | 实际分支 | 本地目录 |
| --- | --- | --- |
| [AgroSenseBot](https://github.com/AIRLab-POLIMI/AgroSenseBot.git) | `jazzy` | [打开](../../AgroSenseBot) |
| [ROS2_Tuition](https://github.com/Rzl6/ROS2_Tuition.git) | `main` | [打开](../../ROS2_Tuition) |
| [Robotics_Tutorial](https://github.com/Michael-Jetson/Robotics_Tutorial.git) | `main` | [打开](../../Robotics_Tutorial) |
| [bunker_ros2](https://github.com/agilexrobotics/bunker_ros2.git) | `jazzy` | [打开](../../bunker_ros2) |
| [linorobot2](https://github.com/linorobot/linorobot2.git) | `jazzy` | [打开](../../linorobot2) |
| [linorobot2_hardware](https://github.com/linorobot/linorobot2_hardware.git) | `jazzy` | [打开](../../linorobot2_hardware) |
| [ros2_control](https://github.com/ros-controls/ros2_control.git) | `jazzy` | [打开](../../ros2_control) |
| [ros2_control_demos](https://github.com/ros-controls/ros2_control_demos.git) | `jazzy` | [打开](../../ros2_control_demos) |
| [ros2_controllers](https://github.com/ros-controls/ros2_controllers.git) | `jazzy` | [打开](../../ros2_controllers) |
| [ros2_tutorial](https://github.com/zsc/ros2_tutorial.git) | `main` | [打开](../../ros2_tutorial) |
| [ugv_sdk](https://github.com/agilexrobotics/ugv_sdk.git) | `main` | [打开](../../ugv_sdk) |

## 尚未纳入的范围

互联网教程持续增加，本次清单不代表全网无遗漏；付费课程、视频流、登录后资料、完整 ROS 二进制镜像和所有传递依赖未自动下载。
官方文档和大部分社区课程保存的是源码（RST/Markdown 等），没有统一构建成原站 HTML；可直接用编辑器离线阅读正文和代码。
下列独立网站需与代码仓库的下载情况分别理解：

- [ROS 2 官方教程在线入口](https://docs.ros.org/en/jazzy/Tutorials.html)：文档站返回访问限制，改取官方源码仓库。
- [Articulated Robotics 教程文章](https://articulatedrobotics.xyz/tutorials/)：配套公开源码列入下载；文章正文尚未镜像。
- [Automatic Addison 教程](https://automaticaddison.com/tutorials/)：已发现入口；未将全部文章或收费课程标为已下载。
- [The Robotics Back-End 教程](https://roboticsbackend.com/category/ros2/)：已发现入口；未将全部文章或收费课程标为已下载。

当前未下载的清单仓库：0；压缩包校验失败：0；子模块处理失败：0；未补齐的 LFS 指针：0；LFS 校验失败：0。
