ROS 2 Jazzy 履带底盘参考工程
核对日期：2026-11-06

阅读顺序：
1. ros2_control_demos/example_2：先了解完整的 Jazzy 控制示例。
2. ros2_controllers/diff_drive_controller：阅读标准差速控制器。
3. AgroSenseBot：阅读农业履带平台的实机工程组织。
4. bunker_ros2 与 ugv_sdk：阅读成品底盘通信与状态反馈。
5. linorobot2 与 linorobot2_hardware：阅读另一套上下位机控制链。

版本与下载范围：
- 除 ugv_sdk 外，下载项目均已核实为远端 jazzy 分支。
- ugv_sdk 是 BUNKER 配套通用 C++ SDK，远端没有 jazzy 分支，使用 main。
- OpenRE 远端没有 jazzy 分支，未下载。
- 各仓库为浅克隆，包含所选提交的当前源码，历史仅保留一层；子模块按仓库固定版本递归获取。
- projects.json 记录每个项目的实际分支、提交和核对结果。
- references.repos 使用固定提交，便于后续复现来源。

当前仅下载和核对源码，没有安装依赖、编译、运行 ROS 节点或连接底盘。
本文件夹是参考源码集合；没有改动现有 aubo_e5_jazzy_ws，也没有替换 /opt/ros/jazzy 的软件包。

项目清单：
ros2_control_demos [jazzy] 完成
优先阅读 example_2：差速底盘硬件接口、模型、控制器配置和启动文件
https://github.com/ros-controls/ros2_control_demos.git
提交：fbab026e147824971c97996f3789f97c2ee9e9ac

ros2_control [jazzy] 完成
控制管理器、SystemInterface 与硬件抽象源码
https://github.com/ros-controls/ros2_control.git
提交：f9e24287fc1d6996e5ba1656a9ee24e5f33adef7

ros2_controllers [jazzy] 完成
diff_drive_controller 与 joint_state_broadcaster 源码
https://github.com/ros-controls/ros2_controllers.git
提交：bee185cbb98815116af9cfb00ff595b0b800e91a

AgroSenseBot [jazzy] 完成
农业履带底盘：控制、硬件接入、实机与导航工程参考
https://github.com/AIRLab-POLIMI/AgroSenseBot.git
提交：4ad700b090b9f3ddb8513c7519938bd7f0974709

bunker_ros2 [jazzy] 完成
履带成品底盘的 ROS 2 驱动与 CAN 接入参考
https://github.com/agilexrobotics/bunker_ros2.git
提交：f24f722b245eb1d2572c47d091fc847d9fd68cf4

ugv_sdk [main] 完成
BUNKER 配套通用 C++ 通信 SDK；不按 ROS 发行版划分，远端无 jazzy 分支
https://github.com/agilexrobotics/ugv_sdk.git
提交：f2704eacdc90357078cd93ec60aae08bb4baab35

linorobot2 [jazzy] 完成
ROS 2 上位机：模型、启动、里程计与自主导航
https://github.com/linorobot/linorobot2.git
提交：f6b0bd0350c4a9d6b815ef4bb5c701a1e5129711

linorobot2_hardware [jazzy] 完成
Linorobot2 配套 micro-ROS 下位机固件与硬件配置
https://github.com/linorobot/linorobot2_hardware.git
提交：fbbbb922f4bd778e23268210b7bd7a6ac4c75d83

