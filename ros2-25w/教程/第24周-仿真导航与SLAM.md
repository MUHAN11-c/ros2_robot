# 第24章 仿真环境与 SLAM 建图

> 本章搭建两类仿真环境（Stage 与 Ignition/Gz Gazebo），并以 slam_toolbox / cartographer 完成 SLAM 建图链路，为第25周的 Nav2 导航与多车编队备好「仿真环境 + 地图」两块地基。
>
> 本章对应代码：`code/ws06_sim_nav/src/demo_ign_sim`、`demo_stage_sim`、`demo_slam`；实测日志与视频帧见 `out/verify/ws06_sim_nav/`、`out/stills/`。

## 24.1 概览与课时结构

### 24.1.1 本周概览

本周进入「仿真 → 建图」核心环节，三大板块递进：**第1课 stage_ros2** 先建立「仿真是什么、为什么」的概念（应用场景、实体机器人开发缺陷、优势与不足），再用最轻量的 2D 仿真器跑通「world 文件 → 仿真器 → ROS2 话题」全链路，覆盖窗体、基本模型、地图、机器人（底盘/摄像头/雷达）与多车环境；**第2课 Ignition Gazebo** 换用物理级 3D 仿真器，从安装与界面开始，经 ros_gz_bridge 桥接、launch 工程化、SDF 环境创建、Fuel 模型添加、机器人与运动控制器（DiffDrive 插件），一路到雷达/单目相机/深度相机/点云的传感器仿真与整体集成；**第3课 导航概述与 SLAM** 先建立导航全局观（概念、Nav2 作用、架构、安装与前提条件），再落地两种建图方案——slam_toolbox（在线同步/异步、launch 移植优化）与 cartographer（lua 配置、双节点执行）。

在 25 周体系中，本周是「从传感器数据到地图产出」的转折点：第22~23周的 `/scan`、`/odom`、tf 在这里成为建图输入，第25周的定位、导航与编队在本周产出的仿真环境与地图上运行。学完本章，你能独立搭建可复用的仿真工程，并驱动机器人边走边建图。

### 24.1.2 课时总表

课程信息：视频 85 个，总时长约 10h34m，难度：高阶。

| 课 | 小节 | 时长 | 一句话导览 |
|---|---|---|---|
| 第1课 ROS2仿真与仿真器stage_ros2 | 20 节 | 2h12m | 仿真概念与优劣、stage_ros2 world/窗体/模型/地图/机器人（底盘/摄像头/雷达）与多车环境 |
| 第2课 仿真器之ignition gazebo | 35 节 | 5h02m | 安装与界面、ros_gz_bridge 集成与 launch 工程化、仿真环境创建、模型/机器人添加、运动控制与传感器仿真 |
| 第3课 ROS2机器人导航概述与SLAM导航详解 | 30 节 | 3h19m | 导航概念与 Nav2 架构、导航条件、slam_toolbox 在线同步/异步建图、cartographer 建图 |

### 24.1.3 第1课视频主题清单（20讲）

| # | 视频主题 | 核心要点 |
|---|---|---|
| 1 | 仿真引言 | 本阶段定位：仿真 → SLAM → 导航的学习路线 |
| 2 | 仿真概述01_仿真应用场景_实体机器人开发缺陷 | 硬件贵、易损坏、不可复现、危险场景难测试 |
| 3 | 仿真概述01_仿真概念、优势与不足 | 低成本/可重复/可加速/安全 vs sim-to-real 鸿沟 |
| 4 | stage_ros2_简介 | Stage 2D 仿真器的 ROS2 封装，轻量专注移动机器人 |
| 5 | stage_ros2_安装与运行 | 安装后 `ros2 run stage_ros2 stage_ros2 <world>` |
| 6 | 仿真框架搭建01_基本流程 | 写 `.world` → 启动仿真器 → ROS2 话题通信 |
| 7 | 仿真框架搭建02_world全局参数 | `resolution`、`interval_sim/realtime`、`update_gui` |
| 8 | 设置窗体_00前言仿真环境组成 | 窗体 + 地图 + 模型三要素 |
| 9 | 设置窗体_01窗体操作 | 缩放、平移、跟随机器人等交互 |
| 10 | 设置窗体_02窗体参数 | `window(size/center/rotate/scale)` |
| 11 | 基本模型_01概念以及使用流程 | `define` 定义模板 → 实例化引用 |
| 12 | 基本模型_02参数 | `position`/`ranger`/`camera`/`model(block)` 参数 |
| 13 | 添加地图 | `floorplan` 位图 + `size`/`resolution` |
| 14 | 添加机器人_01代码框架搭建 | world 中 `define robot position(...)` 骨架 |
| 15 | 添加机器人_02基本实现 | 实例化机器人并启动验证 |
| 16 | 添加机器人_03底盘设置 | `drive "diff"`、`size`、`odom_err` |
| 17 | 添加机器人_04摄像头设置 | `camera` 模型 `resolution`/`range` |
| 18 | 添加机器人_05雷达设置 | `ranger` 模型 `range`/`fov`/`samples` |
| 19 | 添加机器人_06与ROS2通信 | 自动桥接 `/cmd_vel`、`/odom`、`/scan`、相机话题 |
| 20 | 添加机器人_07多车环境 | 多 `positionmodel` 实例 + 命名空间/`tf_prefix` |

### 24.1.4 第2课视频主题清单（35讲）

| # | 视频主题 | 核心要点 |
|---|---|---|
| 1 | 安装与运行_01基本实现 | 安装 ros-gz 发行包，命令行启动世界文件 |
| 2 | 安装与运行_02界面介绍 | 场景/实体树/检查器/资源浏览器/时间控制 |
| 3 | 集成_步骤1启动仿真环境 | 命令行或 launch 拉起 Gazebo 加载世界 |
| 4 | 集成_步骤2创建桥接以及通信实现 | `parameter_bridge` 打通 gz topic 与 ROS2 话题 |
| 5 | 集成_ros_gz_bridge_01简介 | 桥接动机（Transport vs DDS）与描述符语法 |
| 6 | 集成_ros_gz_bridge_02补充 | 更多消息类型与方向组合 |
| 7 | 集成优化_01流程简介 | 「仿真环境 + rviz2 + 桥接」三步合一 |
| 8 | 集成优化_02代码框架 | 功能包目录（launch/config/rviz）规划 |
| 9 | 集成优化_03launch实现之启动仿真环境 | `ExecuteProcess`/`ros_gz_sim` 启动世界文件 |
| 10 | 集成优化_04launch实现之rviz2 | launch 中启动 rviz2 并统一 `use_sim_time` |
| 11 | 集成优化_05launch实现之桥接节点 | 桥接配置迁移到 YAML 由 launch 加载 |
| 12 | 集成优化_06测试以及小结 | 话题/频率/显示三层验证 |
| 13 | 集成优化_07BUG说明 | 话题名不匹配、QoS、时间不一致等坑 |
| 14 | 环境创建_00概述 | SDF 世界文件的结构总览 |
| 15 | 环境创建_01框架搭建 | `<sdf><world>` + 物理参数 + 系统插件骨架 |
| 16 | 环境创建_02墙体轮廓 | `<model><link>` + box 几何画墙 |
| 17 | 环境创建_03墙体尺寸设置 | `pose` 定位 + `size` 尺寸微调 |
| 18 | 添加模型01_资源下载与配置 | Fuel 在线模型库与本地资源路径 |
| 19 | 添加模型02_模型资源添加 | 世界中 `<include><uri>` 引入模型 |
| 20 | 添加模型03_BUG修复以及小结 | 模型路径/版本不匹配的排障 |
| 21 | 添加机器人_01准备工作 | URDF/xacro 与依赖检查 |
| 22 | 添加机器人_02添加机器人模型 | `ros_gz_sim create`/spawn 放入世界 |
| 23 | 添加机器人_03launch集成以及小结 | spawn 步骤并入统一 launch |
| 24 | 运动控制器_01urdf插件配置 | `<gazebo>` 标签加载 DiffDrive 系统插件 |
| 25 | 运动控制器_02launch编写 | launch 下发 `/cmd_vel` 验证运动 |
| 26 | 传感器_01简介与准备工作 | 传感器系统插件与渲染引擎 |
| 27 | 传感器_02雷达仿真基本流程 | `<sensor type="gpu_lidar">` → 桥接 → rviz 显示 |
| 28 | 传感器_03雷达仿真参数 | samples/角度/量程/update_rate 逐项 |
| 29 | 传感器_04单目相机添加 | `<sensor type="camera">` 挂载 |
| 30 | 传感器_05单目相机参数 | `update_rate`/`horizontal_fov`/分辨率 |
| 31 | 传感器_06深度相机添加 | `<sensor type="depth_camera">` |
| 32 | 传感器_07深度相机参数 | 深度图格式、量程、坐标系 |
| 33 | 传感器_08深度相机点云添加上 | 深度 → 点云话题配置（上） |
| 34 | 传感器_09深度相机点云添加下 | 点云桥接与 rviz PointCloud2 显示（下） |
| 35 | 传感器_10整体集成 | 全部桥接/显示收口到统一 launch |

### 24.1.5 第3课视频主题清单（30讲）

| # | 视频主题 | 核心要点 |
|---|---|---|
| 1 | 导航概述00_简介 | 导航板块路线图 |
| 2 | 导航概述01_导航概念 | 定位 + 全局规划 + 局部避障跟踪 |
| 3 | 导航概述02_Nav2在导航中的作用 | 官方导航栈提供感知→决策→控制全链路 |
| 4 | 导航架构 | bt_navigator/planner/controller/behavior 等组件分工 |
| 5 | 导航安装 | `navigation2` + `nav2-bringup` |
| 6 | 导航条件 | tf 树、里程计、激光、地图、速度接口五要素 |
| 7 | 导航条件准备 | 逐项验收上述输入 |
| 8 | SLAM_概念与作用 | 同时定位与建图，输出栅格地图 + `map→odom` |
| 9 | SLAM_slam_toolbox概念功能与优点 | 图优化、在线/离线、可序列化继续建图 |
| 10 | slam_toolbox_安装 | 二进制安装与依赖 |
| 11 | slam_toolbox_节点说明 | sync/async/localization/map_saver 四类节点 |
| 12 | 基本使用00_流程简介 | 建图整体流程图 |
| 13 | 基本使用01_功能包创建 | 自建功能包放 launch/yaml，不改官方包 |
| 14 | 基本使用02_在线同步建图launch与yaml编写 | 18 分钟重点课，逐参数精讲 |
| 15 | 基本使用03_在线同步建图构建与运行 | colcon 构建并启动验证 |
| 16 | 基本使用04_在线异步建图 | async 节点，实时性更好 |
| 17 | 基本使用05_rqt_graph查看节点关系 | 验证 `/scan`、`/odom`、tf 输入 |
| 18 | 基本使用06_launch移植优化上 | 参数化、环境无关化（上） |
| 19 | 基本使用07中 | 兼容仿真/实机（中） |
| 20 | 基本使用08下 | 收尾与整理（下） |
| 21 | 基本使用09_小结 | slam_toolbox 知识收束 |
| 22 | SLAM_cartographer_概述 | Google 图优化 SLAM，2D/3D、可融合 IMU |
| 23 | cartographer_安装 | `cartographer`、`cartographer-ros` |
| 24 | cartographer_节点说明 | `cartographer_node` + `occupancy_grid_node` |
| 25 | cartographer_基本使用01_流程简介以及框架搭建 | 功能包与 lua 配置骨架 |
| 26 | 基本使用02_launch文件编写上 | 启动核心节点并加载 lua（上） |
| 27 | 基本使用03下 | 栅格节点 + rviz（下） |
| 28 | 基本使用04_执行 | 运行建图并观察 |
| 29 | 基本使用05_launch优化 | 配置路径与参数整理 |
| 30 | SLAM_小结 | 两种方案对比与选型 |

## 24.2 知识点梳理

### 24.2.1 第1课 ROS2仿真与仿真器stage_ros2（2h12m · 20讲）

#### 1. 仿真概述：为什么需要仿真（第1~3讲）

- **实体机器人开发的缺陷**（第2讲）：硬件成本高、调试中易损坏、实验不可复现（同一段代码两次跑结果受环境干扰）、危险/极端场景（楼梯、火场、人群）难以在开发期测试。
- **仿真概念与优势**（第3讲）：在计算机中构建机器人的数字模型与物理环境，替代真实硬件执行控制与感知闭环；优势是低成本、可重复、可加速、安全。
- **仿真的不足**：存在「仿真到实机的鸿沟（sim-to-real gap）」——物理接触、传感器噪声、通信延迟在仿真中被简化或理想化，仿真通过的算法实机仍需调参。结论：仿真是开发流程的「前半程」，不是替代品。

#### 2. stage_ros2 简介与安装运行（第4~5讲）

- Stage 是经典 2D 仿真器，stage_ros2 是其 ROS2 移植：轻量、专注 2D 移动机器人（差速/全向底盘 + 2D 雷达 + 低分辨率相机），CPU 占用极低，可同屏跑多车；安装 `sudo apt install ros-<distro>-stage-ros2`，运行 `ros2 run stage_ros2 stage_ros2 <world文件>`。资源受限、只关心 2D 导航/编队逻辑时选它；需要相机物理、点云、惯导等高保真传感器时换 Ignition Gazebo。

#### 3. 仿真框架搭建与 world 全局参数（第6~7讲）

- 基本流程 = 编写 `.world` 文件（Stage 专有 Lisp 风格语法）→ `ros2 run stage_ros2 stage_ros2 xxx.world` → 仿真器自动把模型话题桥接为 ROS2 话题。
- world 全局参数（本仓库 `stage.world` 实例）：`resolution 0.05`（栅格分辨率，米/格）、`interval_sim 100`（仿真步长，毫秒/步）、`interval_realtime 100`（实时步长，与前者相等即 1 倍速）、`update_gui 100`（窗体刷新间隔）。

#### 4. 设置窗体（第8~10讲）

- 仿真环境组成（第8讲前言）：**窗体**（window，人机交互视口）+ **地图**（floorplan，位图栅格）+ **模型**（model，机器人与障碍）三要素。
- 窗体操作（第9讲）：滚轮缩放、拖拽平移、视角跟随机器人。窗体参数（第10讲，本仓库实例）：`size [700 700]`（像素）、`center [0 0]`（初始视野中心，米）、`rotate [0 0]`、`scale 25`（像素/米）。

#### 5. 基本模型（第11~12讲）

- 使用流程：`define <名称> <类型>` 定义模板 → 场景区按 `<名称>(...)` 多次实例化。四类基本模型：

  | 模型类型 | 作用 | 关键参数 |
  |---|---|---|
  | `position` | 移动底盘（差速/全向/阿克曼） | `drive`、`size`、`origin`、`odom_err` |
  | `ranger` | 2D 激光雷达/声呐阵列 | `sensor(range/fov/samples)`、`pose` |
  | `camera` | 低分辨率相机 | `resolution`、`range`、`fov` |
  | `model` + `block` | 静态障碍（墙体、箱体） | `points`、`z`、`size`、`pose` |

#### 6. 添加地图（第13讲）

- `floorplan( bitmap "map.pgm" size [24 24 0.5] )`：位图黑=占据、白=空闲，`size` 把位图缩放到真实米制尺寸。本仓库演示用四面 `block` 墙拼出 8m×8m 房间替代位图，思路等价。

#### 7. 添加机器人（第14~20讲，七讲连播）

- **01 代码框架搭建**：在 world 中搭 `define robot position(...)` 骨架，预留底盘/摄像头/雷达插槽。
- **02 基本实现**：实例化 `robot( pose [0 -2 0 0] name "robot1" )`，启动仿真器看到机器人。
- **03 底盘设置**：`drive "diff"`（差速）；`size [0.35 0.35 0.25]` 外形；`odom_err [...]` 注入里程计误差（第6、7 项设 999999 表示屏蔽该方向误差，模拟理想里程计）。
- **04 摄像头设置**：`camera` 模型 `resolution [宽 高]`、`range [min max]`；Stage 相机是低分辨率 2D 投影，仅作占位验证。
- **05 雷达设置**：`ranger` 定义 `range [0.15 12.0]`、`fov 360.0`、`samples 360`，挂到机器人 `laser( pose [0.08 0 0 0] )`。
- **06 与ROS2通信**：stage_ros2 自动发布 `/cmd_vel`（订阅）、`/odom`、`/scan`、`/camera/image_raw` 等话题，与实机驱动同构——上层导航代码零修改。
- **07 多车环境**：多次实例化 robot（`robot1`、`robot2`...），仿真器按名称生成命名空间话题（如 `/robot1/cmd_vel`），并需 `tf_prefix` 区分 tf；这是第25章多车编队的仿真底座。

#### 8. teleop 遥控（贯穿演示）

- 与 Gazebo 侧一致：`ros2 run teleop_twist_keyboard teleop_twist_keyboard_node` 发布 `/cmd_vel`，机器人即动，`/odom`、`/scan` 随之更新——这是后续 SLAM 建图的「油门」。

### 24.2.2 第2课 仿真器之ignition gazebo（5h02m · 35讲）

#### 1. 安装与运行、界面（第1~2讲）

- 安装：`sudo apt install ros-humble-ros-gz`（课程环境；Jazzy 为 `ros-jazzy-ros-gz`），内含 `ros_gz_sim`（启动仿真）、`ros_gz_bridge`（桥接）。
- 基本运行：`ign gazebo shapes.sdf`（课程/Fortress）或 `gz sim shapes.sdf`（Harmonic）；`-r` 表示启动即自动运行。
- 界面五要素：3D 场景（Scene）、实体树（Entity Tree，world/model/link 层级）、组件检查器（ECM 键值）、资源浏览器（Fuel 模型拖放）、时间控制（暂停/单步/倍速）。

#### 2. 与 ROS2 集成：两步走（第3~6讲）

- **步骤1 启动仿真环境**（第3讲）：命令行或 launch 拉起 Gazebo 并加载 SDF 世界。
- **步骤2 创建桥接**（第4讲）：Gazebo 内部用 gz Transport（gz topic）通信，ROS2 用 DDS，互不相通，靠 `ros_gz_bridge` 的 `parameter_bridge` 节点按「桥接描述符」转发：

  ```bash
  ros2 run ros_gz_bridge parameter_bridge /cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist \
    /scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan \
    /odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry
  # 描述符语法：<ros_topic>@<ros_type>[|]<gz_type>
  #   |  双向；[  单向 gz→ros；]  单向 ros→gz
  ```

- **ros_gz_bridge 01/02**（第5~6讲）：方向符写反会出现「话题存在但无数据」；常用类型对：Twist↔Twist、LaserScan↔LaserScan、Odometry↔Odometry、Image↔Image、PointCloudPacked↔PointCloud2、Pose_V↔TFMessage、Clock↔Clock。

#### 3. 集成优化：launch 工程化（第7~13讲，七讲连播）

- **01 流程简介 / 02 代码框架**：目标「一条 launch 启动 仿真环境 + rviz2 + 桥接节点」；建功能包，目录按 `launch/`、`config/`（桥接 YAML）、`rviz/` 划分。
- **03 启动仿真环境**：launch 中 `ExecuteProcess(cmd=["gz","sim","-r",world])`（Fortress 用 `["ign","gazebo","-r",world]`），或 `ros_gz_sim` 的 `gz_sim.launch.py`。
- **04 rviz2**：launch 加 rviz2 节点并 `use_sim_time: True`，加载统一 `.rviz` 配置（LaserScan/TF/Odometry 预摆好）。
- **05 桥接节点**：命令行描述符迁移到 `config/bridge.yaml`，launch 用 `config_file:=` 加载，可维护、可版本管理。
- **06 测试小结**：三层验证——`ros2 topic list`（话题在）、`ros2 topic hz /scan`（有频率）、rviz2（有数据形状）。
- **07 BUG 说明**：常见坑——gz 侧话题名与桥接配置不一致（常带 `/model/<name>/...` 前缀）、QoS 不匹配、`use_sim_time` 漏设、插件短名加载失败（Harmonic 兼容问题，见 24.5.1）。

#### 4. 仿真环境创建（第14~17讲）

- **00 概述 / 01 框架搭建**：SDF（Simulation Description Format）世界 = `<world>` 内依次放 physics（步长/实时因子）、系统插件（Physics/UserCommands/SceneBroadcaster/Sensors）、scene 光照、地面、墙体、模型。本仓库 `demo.sdf` 即此骨架的完整实例（逐段讲解见 24.4.1）。
- **02 墙体轮廓**：`<model><static>true</static><link>` + `<collision>`/`<visual>` 的 `<box>` 几何画墙；collision 管物理碰撞，visual 管显示外观。
- **03 墙体尺寸设置**：`<pose>x y z roll pitch yaw</pose>` 定位（z 取墙高一半使其落地）+ `<size>长 宽 高</size>` 调尺寸；改 pose 的 x/y 即平移墙体围出房间。

#### 5. 添加模型：Fuel 资源库（第18~20讲）

- **01 资源下载与配置**：Gazebo Fuel 是官方在线模型库（桌椅、货架、环境等）；下载后的模型放本地资源路径（如 `~/.gz/fuel`），确保 Gazebo 能索引。
- **02 模型资源添加**：世界中 `<include><uri>...</uri></include>` 或引用本地模型目录，把静态模型搬进世界。
- **03 BUG修复以及小结**：模型路径写错/版本不存在导致加载失败，日志提示找不到资源；建议离线保存模型并固定版本。

#### 6. 添加机器人（第21~23讲）

- **01 准备工作**：整理机器人 URDF/xacro（第23周成果），确认依赖（robot_state_publisher、ros_gz）就绪。
- **02 添加机器人模型**：launch 用 `ros_gz_sim create`（`-file robot.urdf -name robot1`）动态 spawn；或 `xacro` 展开后经 `robot_description` 传入。
- **03 launch集成以及小结**：把 spawn 步骤并入统一 launch，机器人与世界、桥接、rviz2 一键起。

#### 7. 运动控制器（第24~25讲）

- **01 urdf插件配置**：在 URDF 的 `<gazebo>` 标签中加载差速驱动系统插件（SDF 世界里则直接在 `<model>` 下挂 `<plugin>`，本仓库即后者）：

  ```xml
  <gazebo>
    <plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
      <left_joint>left_wheel_joint</left_joint>
      <right_joint>right_wheel_joint</right_joint>
      <topic>cmd_vel</topic>
      <odom_topic>odom</odom_topic>
      <frame_id>odom</frame_id>
      <child_frame_id>base_link</child_frame_id>
    </plugin>
  </gazebo>
  ```

- **02 launch编写**：launch 后用 `ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{ linear: {x: 0.3}, angular: {z: 0.5} }"` 或 teleop 遥控，验证前进/转弯与 `/odom` 回传。

#### 8. 传感器仿真（第26~35讲，十讲连播）

- **01 简介与准备工作**：传感器由世界级系统插件 `gz::sim::systems::Sensors`（渲染引擎 `ogre2`）驱动，GPU 类传感器依赖显卡渲染；先挂好插件再谈传感器。
- **02 雷达仿真基本流程**（对应视频 727s，参数见 24.5.1 视频对照）：`<sensor type="gpu_lidar">` 声明 → 桥接 `LaserScan` → rviz2 Add LaserScan 显示点云。本仓库视频帧（`out/stills/e2e_ign_500s.png`）可见 rviz2 的 Create visualization 弹窗中勾选 LaserScan；`e2e_ign_620s.png` 可见 SDF 编辑器中 `<gazebo reference="laser">` 下 `sensor name='gpu_lidar'`、`topic scan`、`update_rate 30` 等片段，与流程一致。
- **03 雷达仿真参数**：`topic`、`update_rate`、水平 `samples`/`min_angle`/`max_angle`、垂直线数与角度、`range` 的 min/max/resolution、`gz_frame_id`；逐项讲解见 24.4.1 参数表。
- **04/05 单目相机添加与参数**：`<sensor type="camera">`，关键参数 `update_rate`、`horizontal_fov`、`image` 的 `width/height/format`、`clip` 近远裁剪面；桥接 `ignition.msgs.Image → sensor_msgs/msg/Image`（另有 CameraInfo）。
- **06/07 深度相机添加与参数**：`<sensor type="depth_camera">`，在相机参数基础上增加深度通道与 `min/max depth`；输出深度图（32FC1 米制）。
- **08/09 深度相机点云添加上/下**：深度相机自带点云输出话题，桥接 `ignition.msgs.PointCloudPacked → sensor_msgs/msg/PointCloud2`，rviz2 用 PointCloud2 显示；上篇配 SDF，下篇配桥接与显示并处理 `frame_id`/tf。
- **10 整体集成**：把雷达、单目、深度相机的全部桥接项并入 `config/bridge.yaml`，rviz2 预配 LaserScan/Image/PointCloud2 显示，一条 launch 收口。
- **拓展（非本课视频，举一反三）**：IMU 同理——`<sensor type="imu">` + 桥接 `ignition.msgs.IMU → sensor_msgs/msg/Imu`，SDF 中可配 `<imu><noise>` 噪声模型，为 cartographer 融合建图备料。
- **工程习惯**：世界文件（SDF/world）、机器人描述（URDF/xacro）、桥接配置（YAML）、launch、rviz2 配置五类文件分目录管理（`worlds/`、`urdf/`、`config/`、`launch/`、`rviz/`），是本阶段所有仿真作业的推荐骨架，也直接演化为实机 bringup 包结构。

### 24.2.3 第3课 ROS2机器人导航概述与SLAM导航详解（3h19m · 30讲）

#### 1. 导航概述与 Nav2 的作用（第1~3讲）

- **导航概念**：机器人在地图中**定位自身** + **规划全局路径** + **局部避障跟踪**到目标点的完整能力。
- **Nav2 在导航中的作用**：ROS2 官方导航框架，提供感知→决策→控制完整栈——代价地图（costmap）、全局/局部规划器、控制器、恢复行为、路点跟踪，全部插件化（planner 可换 NavFn/Smac/Theta*，controller 可换 DWB/MPPI/RPP），由生命周期管理统一编排。

#### 2. 导航架构（第4讲，30 分钟大课，务必精读）

| 组件 | 职责 | 关键话题/接口 |
|---|---|---|
| `map_server` | 提供静态地图 | `/map`（OccupancyGrid） |
| `amcl` / SLAM | 定位，发布 `map → odom` | `/amcl_pose`、tf |
| `planner_server` | 全局路径规划 | `/plan`（Path）、`ComputePathToPose` 动作 |
| `controller_server` | 局部路径跟踪，输出速度 | `/cmd_vel`、`FollowPath` 动作 |
| `bt_navigator` | 行为树调度整条导航流程 | `NavigateToPose` 动作入口 |
| `behavior_server` | 恢复行为（spin/backup/wait/clear costmap） | `Spin`/`BackUp`/`Wait` 动作 |
| `waypoint_follower` | 路点依次巡航 | `FollowWaypoints` 动作 |
| `smoother_server` / `velocity_smoother` | 路径平滑 / 速度平滑 | `/smoothed_plan`、平滑后 `/cmd_vel` |
| `lifecycle_manager` | 统一管理各节点 configure/activate | 生命周期（Lifecycle）服务 |

数据流：`NavigateToPose(goal)` → `bt_navigator` 拉起行为树 → `planner_server` 规划 `/plan` → `controller_server` 跟踪生成 `/cmd_vel` → 底盘执行；受阻时 `behavior_server` 执行恢复行为后重规划。

#### 3. 导航安装与条件（第5~7讲）

- 安装：`sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup`（Jazzy 对应 `ros-jazzy-*`）。
- 导航五前提：① 完整 tf 树（`map → odom → base_link → <sensors>`）；② 里程计（`/odom` 或融合里程计）；③ 激光/点云障碍数据；④ 静态地图（导航模式）或 SLAM；⑤ 速度控制接口 `/cmd_vel`。条件准备课逐项验收：`view_frames` 查 tf、`topic hz /scan` 查雷达、`topic echo /odom` 查里程计——本章仿真正是把这五项凑齐。

#### 4. SLAM 概念与作用（第8讲）

SLAM（Simultaneous Localization and Mapping，同时定位与地图构建）：机器人在未知环境中边走边估计自身位姿并构建地图，解决「定位需要地图、建图需要定位」的鸡蛋问题。输出：2D 占据栅格地图（`/map`）+ `map → odom` 变换。

#### 5. slam_toolbox：概念/安装/节点（第9~11讲）

- **概念功能与优点**：ROS2 默认 2D SLAM 方案，基于图优化（pose graph）；支持在线/离线、同步/异步建图与纯定位模式；地图可序列化（`.posegraph` + `.data`）继续建图或转纯定位；工程化好、与 Nav2 无缝。
- **安装**：`sudo apt install ros-<distro>-slam-toolbox`。
- **节点说明**：`sync_slam_toolbox_node`（在线同步）、`async_slam_toolbox_node`（在线异步）、`localization_slam_toolbox_node`（纯定位）、`map_saver_cli`（保存地图）；另有 rviz2 交互插件。

#### 6. slam_toolbox 基本使用（第12~21讲，十讲连播）

- **00 流程简介**：仿真/实机提供 `/scan`+`/odom`+tf → 启动建图节点（yaml 配参数）→ teleop 遥控走图 → rviz2 观察 `/map` → 保存地图。
- **01 功能包创建**：自建功能包（如 `demo_slam`）放 launch 与 yaml，**不改动官方 slam_toolbox 包**——升级不丢配置，ROS2 工程铁律。
- **02 在线同步建图 launch与yaml编写**（18 分钟重点课）：yaml 逐组精讲（本仓库 `mapper_params_online_sync.yaml` 全量还原，逐项讲解见 24.4.5）；launch 启动 `sync_slam_toolbox_node` + rviz2。
- **03 构建与运行**：`colcon build` 后 `ros2 launch` 启动，rviz2 添加 Map（话题 `/map`）+ LaserScan + TF，遥控走图。
- **04 在线异步建图**：换 `async_slam_toolbox_node`（参数文件同款），处理频率自适应、允许丢帧，探索式建图实时性更好。
- **05 rqt_graph查看节点关系**：`ros2 run rqt_graph rqt_graph` 确认 `/scan`、`/odom` → `slam_toolbox` → `/map`、tf 的拓扑，输入断链一目了然。
- **06~08 launch移植优化上/中/下**：世界/配置路径参数化（`DeclareLaunchArgument`），仿真/实机共用一个 launch 只换参数；rviz2 配置 `-d` 独立加载；`use_sim_time` 由 launch 统一注入。
- **09 小结**：sync/async/localization 三模式一张表收束。

#### 7. cartographer（第22~29讲）

- **概述**：Google 开源图优化 SLAM，支持 2D/3D、激光+IMU 融合，精度高、配置复杂（Lua 配置文件）。
- **安装**：`sudo apt install ros-<distro>-cartographer ros-<distro>-cartographer-ros`。
- **节点说明**：`cartographer_node`（建图核心，输出 `.pbstream` 位姿图）+ `cartographer_occupancy_grid_node`（把位姿图渲染为占据栅格 `/map`），两节点必须同时启动。
- **基本使用 01 流程以及框架搭建**：建功能包 `config/`（lua）+ `launch/`；lua 是唯一配置入口。
- **02/03 launch文件编写上/下**：上篇启动 `cartographer_node` 并以 `-configuration_directory`/`-configuration_basename` 传入 lua；下篇补 `cartographer_occupancy_grid_node` 与 rviz2。
- **04 执行**：`ros2 launch` 启动后 rviz2 观察 `/map`（submap 与概率栅格双显示）。
- **05 launch优化**：lua 路径经 `get_package_share_directory` 解析，`use_sim_time` 统一注入。
- lua 配置要点（本仓库 `cartographer.lua` 全文见 24.4.6）：`tracking_frame`（传感器汇聚帧）、`published_frame`、`use_odometry: true`（吃 `/odom`）、`num_laser_scans: 1`、`use_trajectory_builder_2d`（2D 建图）、`use_online_correlative_scan_matching`（在线相关扫描匹配）。
- **SLAM 小结与选型（第30讲）**：纯 2D 激光、求稳、赶进度 → slam_toolbox；需要激光+IMU 融合、追求建图质量、可接受 Lua 调参成本 → cartographer。二者输入输出同构（`/scan`+`/odom`+tf → `/map`+`map→odom`），可互换。

## 24.3 重点与难点

1. **tf 链路是导航的命脉**：`map → odom`（SLAM/AMCL）+ `odom → base_link`（里程计/EKF）+ `base_link → <sensor>`（URDF）缺一环即瘫痪。每换一个仿真器/实机，第一件事是 `ros2 run tf2_tools view_frames` 查图。
2. **`use_sim_time` 全局一致性**：仿真中所有节点（含 rviz2、Nav2、SLAM）都必须设 `use_sim_time: true`，否则消息时间戳与 tf 时间错位，报 `extrapolation into the past/future`。
3. **ros_gz_bridge 桥接描述符语法**：`[` / `]` / `|` 决定方向，写反会出现「有话题无数据」；桥接 YAML 化后要用 `ros2 topic info -v` 确认 publisher/subscriber 数量符合预期。
4. **Gz 侧话题名的「隐式前缀」**：插件输出的话题常带模型路径前缀（如 `/model/robot1/odometry`、`/model/robot1/tf`），而传感器用 `<topic>` 显式指定（`/scan`）——写 bridge.yaml 前先 `gz topic -l` 核对真实名字。
5. **Harmonic 插件类名**：`<plugin name>` 用短名（如 `diff_drive`）会报 `library does not contain requested plugin`，必须写完整类名 `gz::sim::systems::DiffDrive`（实测报错全文见 24.5.1）。
6. **SLAM 建图质量控制**：行走速度慢而匀、转弯缓、回环闭合走回起点、`max_laser_range` 与实际雷达一致、里程计标定（第23章）先行——里程计烂，地图就重影。
7. **同步 vs 异步建图**：sync 每帧处理保证一致性、CPU 压力大；async 允许丢帧、实时性好。探索式建图用 async，精细建图用 sync。
8. **仿真 → 实机迁移要点**：仿真插件话题名（`/scan`、`/cmd_vel`）尽量与实机驱动保持一致；传感器噪声参数在仿真中模拟出来，才能提前暴露导航鲁棒性问题。
9. **Stage 与 Ignition 的分工**：Stage 验证 2D 逻辑（快、省资源、多车易），Ignition 做传感器与 3D 物理（真、重、单车主场）——用错工具会同时损失效率与保真度。

## 24.4 代码与命令实战

### 24.4.0 工程总览

```text
code/ws06_sim_nav/src/
├── demo_ign_sim/     # worlds/demo.sdf + config/bridge.yaml + launch/sim_launch.py
├── demo_stage_sim/   # worlds/stage.world + launch/sim.launch.py
└── demo_slam/        # config/(mapper yaml + cartographer.lua) + launch/(两个建图 launch)
```

构建：`cd code/ws06_sim_nav && colcon build --packages-select demo_ign_sim demo_stage_sim demo_slam && source install/setup.bash`。

### 24.4.1 demo.sdf 逐段讲解（`demo_ign_sim/worlds/demo.sdf`，127 行）

**第 1 段 · 文件头与物理参数**

```xml
<sdf version="1.8">
  <world name="demo_world">
    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
```

- SDF 版本 1.8（Fortress/Harmonic 均兼容）；`max_step_size 0.001` 即 1ms 物理步长，`real_time_factor 1.0` 表示仿真时间与真实时间 1:1 流动——步长越小越精确、越耗 CPU。

**第 2 段 · 世界级系统插件（四件套）**

```xml
    <plugin name="gz::sim::systems::Physics" filename="gz-sim-physics-system"/>
    <plugin name="gz::sim::systems::UserCommands" filename="gz-sim-user-commands-system"/>
    <plugin name="gz::sim::systems::SceneBroadcaster" filename="gz-sim-scene-broadcaster-system"/>
    <plugin name="gz::sim::systems::Sensors" filename="gz-sim-sensors-system">
      <render_engine>ogre2</render_engine>
    </plugin>
```

- `Physics`：动力学求解（无它万物不动）；`UserCommands`：接收 create/remove 命令；`SceneBroadcaster`：向 GUI/桥接广播场景状态；`Sensors`：驱动传感器渲染，`ogre2` 渲染引擎是 GPU 雷达/相机出数据的必要条件——漏挂 Sensors 插件是「传感器话题无数据」的头号原因。

**第 3 段 · 场景光照**

```xml
    <!-- scene：ambient 1.0 1.0 1.0、background 0.8 0.8 0.8，略 -->
    <light type="directional" name="sun">
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <direction>-0.5 0.1 -0.9</direction>
    </light>
```

- 环境光/背景色影响视觉与相机成像；`directional` 平行光模拟太阳（对应课程「环境创建」框架搭建与墙体轮廓两讲的场景基础）。

**第 4 段 · 地面**

```xml
    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry><plane><normal>0 0 1</normal><size>100 100</size></plane></geometry>
          <surface><friction><ode><mu>1</mu><mu2>1</mu2></ode></friction></surface>
        </collision>
        <!-- visual 与 collision 几何一致，材质灰色，略 -->
      </link>
    </model>
```

- `static true` 静态模型不参与动力学积分；`normal 0 0 1` 平面朝上；摩擦系数 `mu/mu2` 影响轮子打滑程度（建图漂移可在仿真里先复现）。

**第 5 段 · 墙体（north 一例，south/east/west 同构）**

```xml
    <model name="wall_north">
      <static>true</static>
      <pose>0 4 0.5 0 0 0</pose>
      <link name="link">
        <collision name="collision"><geometry><box><size>8 0.2 1</size></box></geometry></collision>
        <!-- visual 与 collision 同构，材质灰色，略 -->
      </link>
    </model>
```

- `pose x y z`：z=0.5 是墙高 1m 的一半，让墙体恰好落地；`size 长 宽 高 = 8 0.2 1`（对应课程「墙体轮廓 + 墙体尺寸设置」两讲：box 画轮廓、pose/size 调位置尺寸）。雷达打在 `<collision>` 上才有回波，只有 visual 的墙是「幻影墙」。

**第 6 段 · 差速小车：底盘与 gpu_lidar 传感器**

```xml
    <model name="robot1">
      <pose>0 -2 0.1 0 0 0</pose>
      <link name="chassis">
        <inertial>
          <mass>10</mass>
          <inertia><ixx>0.1</ixx><iyy>0.1</iyy><izz>0.1</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia>
        </inertial>
        <!-- collision/visual：box 0.35 0.25 0.1，材质蓝色，略 -->
        <sensor name="gpu_lidar" type="gpu_lidar">
          <pose>0.15 0 0.08 0 0 0</pose>
          <topic>scan</topic>
          <update_rate>10</update_rate>
          <gz_frame_id>laser</gz_frame_id>
          <lidar>
            <scan><horizontal><samples>360</samples><resolution>1</resolution><min_angle>-3.14159</min_angle><max_angle>3.14159</max_angle></horizontal></scan>
            <range><min>0.15</min><max>12.0</max><resolution>0.01</resolution></range>
          </lidar>
          <always_on>1</always_on>
          <visualize>true</visualize>
        </sensor>
      </link>
```

- `inertial` 质量 10kg + 惯量张量是动力学必需项；传感器挂进 chassis link，`pose 0.15 0 0.08` 即雷达在车头前上方。
- **gpu_lidar 参数逐项**：

  | 参数 | 取值 | 含义与调法 |
  |---|---|---|
  | `type` | gpu_lidar | GPU 光线投射雷达（另有 `lidar` CPU 版，大线数时慢） |
  | `topic` | scan | gz 侧话题名，桥接后即 ROS2 `/scan`，与实机驱动对齐 |
  | `update_rate` | 10 | 发送频率 Hz，应与真实雷达一致（常见 5~30） |
  | `gz_frame_id` | laser | 消息 `header.frame_id`，必须与 tf 树中雷达帧同名 |
  | `horizontal/samples` | 360 | 水平采样线数（课程视频为 640） |
  | `horizontal/min_angle`/`max_angle` | -3.14159 / 3.14159 | 水平视场 ±π（360° 全向） |
  | `horizontal/resolution` | 1 | 采样插值分辨率（1 = 不插值） |
  | `range/min`/`max` | 0.15 / 12.0 | 量程（米）；min 过小地面噪声入图，max 须 ≤ 真实雷达 |
  | `range/resolution` | 0.01 | 距离量化精度（米） |
  | `always_on` | 1 | 世界加载即开始采集 |
  | `visualize` | true | 在 Gazebo 场景中画雷达射线（调试用） |

- 未配 `vertical`（垂直线数）即为单线 2D 雷达——这正是课程视频中「垂直 16 线 ±0.2618」与本文 2D 用法的差异点（多线时消息桥接为 PointCloud2 更合适）。

**第 7 段 · 车轮与关节**

```xml
      <link name="left_wheel">
        <pose>-0.1 0.16 0 -1.5708 0 0</pose>
        <inertial><mass>1</mass><inertia><ixx>0.01</ixx><iyy>0.01</iyy><izz>0.01</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <!-- collision/visual：cylinder radius 0.05 length 0.02，略 -->
      </link>
      <!-- right_wheel：pose -0.1 -0.16 0 -1.5708 0 0，其余同 left_wheel -->
      <joint name="left_wheel_joint" type="revolute">
        <parent>chassis</parent><child>left_wheel</child>
        <axis><xyz>0 1 0</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis>
      </joint>
      <!-- right_wheel_joint 同理 -->
```

- 轮子是圆柱（半径 0.05、厚 0.02），`roll -1.5708`（-90°）把圆柱放倒成轮；`revolute` 关节绕 y 轴转，limit ±1e16 表示不限转角（差速轮常态）。

**第 8 段 · DiffDrive 差速驱动插件**

```xml
      <plugin name="gz::sim::systems::DiffDrive" filename="gz-sim-diff-drive-system">
        <left_joint>left_wheel_joint</left_joint>
        <right_joint>right_wheel_joint</right_joint>
        <wheel_separation>0.32</wheel_separation>
        <wheel_radius>0.05</wheel_radius>
        <odom_publish_frequency>10</odom_publish_frequency>
        <topic>cmd_vel</topic>
        <odom>odom</odom>
        <tf_topic>tf</tf_topic>
      </plugin>
```

| 参数 | 取值 | 含义 |
|---|---|---|
| `name` | gz::sim::systems::DiffDrive | **完整类名**（Harmonic 必须，短名报错见 24.5.1） |
| `filename` | gz-sim-diff-drive-system | 插件库文件名 |
| `left_joint`/`right_joint` | left/right_wheel_joint | 绑定两个轮关节 |
| `wheel_separation` | 0.32 | 轮距（米），= 两轮 y 坐标差 0.16×2，算错转弯半径就错 |
| `wheel_radius` | 0.05 | 轮半径（米），与 cylinder radius 一致 |
| `odom_publish_frequency` | 10 | 里程计发布频率 Hz |
| `topic` | cmd_vel | 订阅的 Twist 话题 |
| `odom` | odom | 里程计话题（gz 侧实际为 `/model/robot1/odometry`） |
| `tf_topic` | tf | 位姿话题（gz 侧实际为 `/model/robot1/tf`，Pose_V） |

### 24.4.2 bridge.yaml 逐行讲解（`demo_ign_sim/config/bridge.yaml`，5 条）

```yaml
# ignition gazebo 与 ROS2 桥接配置：/cmd_vel 下发（ROS→GZ），/scan /odom /tf /clock 上传（GZ→ROS）
- ros_topic_name: "/cmd_vel"
  gz_topic_name: "/cmd_vel"
  ros_type_name: "geometry_msgs/msg/Twist"
  gz_type_name: "ignition.msgs.Twist"
  direction: ROS_TO_GZ
- ros_topic_name: "/scan"
  gz_topic_name: "/scan"
  ros_type_name: "sensor_msgs/msg/LaserScan"
  gz_type_name: "ignition.msgs.LaserScan"
  direction: GZ_TO_ROS
- ros_topic_name: "/odom"
  gz_topic_name: "/model/robot1/odometry"
  ros_type_name: "nav_msgs/msg/Odometry"
  gz_type_name: "ignition.msgs.Odometry"
  direction: GZ_TO_ROS
- ros_topic_name: "/tf"
  gz_topic_name: "/model/robot1/tf"
  ros_type_name: "tf2_msgs/msg/TFMessage"
  gz_type_name: "ignition.msgs.Pose_V"
  direction: GZ_TO_ROS
- ros_topic_name: "/clock"
  gz_topic_name: "/clock"
  ros_type_name: "rosgraph_msgs/msg/Clock"
  gz_type_name: "ignition.msgs.Clock"
  direction: GZ_TO_ROS
```

- 每条五要素：`ros_topic_name`（ROS2 侧名，可重映射成实机一致的名字）、`gz_topic_name`（gz 侧真实话题，**前缀要对**）、`ros_type_name`/`gz_type_name`（两侧消息类型必须成对兼容）、`direction`（`ROS_TO_GZ`/`GZ_TO_ROS`/`BIDIRECTIONAL`）。
- 五条分工：`/cmd_vel` 是唯一下行（ROS → 仿真）；`/scan`、`/odom`、`/tf` 是数据上行；`/clock` 是**仿真时钟**上行——所有 ROS 节点配 `use_sim_time: true` 后都靠它对时，漏桥时钟是时间戳错位的根源。
- 加载方式：`ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=<该yaml>`，launch 中见 24.4.3。

### 24.4.3 sim_launch.py 讲解（`demo_ign_sim/launch/sim_launch.py`）

```python
world_path = os.path.join(get_package_share_directory("demo_ign_sim"), "worlds", "demo.sdf")
bridge_yaml = os.path.join(get_package_share_directory("demo_ign_sim"), "config", "bridge.yaml")

gz_sim = ExecuteProcess(cmd=["gz", "sim", "-r", world_path], output="screen")
bridge = Node(package="ros_gz_bridge", executable="parameter_bridge",
              arguments=["--ros-args", "-p", f"config_file:={bridge_yaml}"], output="screen")
rviz2 = Node(package="rviz2", executable="rviz2", parameters=[{"use_sim_time": True}])
teleop = Node(package="teleop_twist_keyboard", executable="teleop_twist_keyboard", output="screen")

return LaunchDescription([gz_sim, bridge, rviz2])
```

- `ExecuteProcess` 直接起 `gz sim -r`（源码注释中保留了 Fortress 用 `ign gazebo -r` 的兼容说明）；桥接节点用 `config_file` 参数吃 YAML；rviz2 统一 `use_sim_time`。
- 注意：`teleop` 节点已定义但**未加入** `LaunchDescription` 列表——遥控需另开终端 `ros2 run teleop_twist_keyboard teleop_twist_keyboard_node`，避免抢占当前终端。

### 24.4.4 stage.world 逐段讲解 + sim.launch.py（`demo_stage_sim/`）

**全局参数与窗体**（对应第1课第6~10讲）：

```lisp
resolution 0.05
interval_sim 100
interval_realtime 100
update_gui 100

window
(
  size [ 700.000 700.000 ]
  center [ 0.000 0.000 ]
  scale 25.000
)
```

**雷达与机器人定义**（对应第11~12、16~18讲）：

```lisp
define laser ranger
(
  sensor
  (
    range [0.15 12.0]
    fov 360.0
    samples 360
    size [0.025 0.025 0.025]
  )
  color "black"
)

define robot position
(
  drive "diff"
  size [0.35 0.35 0.25]
  origin [0 0 0 0]
  odom_err [0.0 0.0 999999 0.0 0.0 999999]
  color "blue"
  laser ( pose [0.08 0 0 0] )
)
```

- `range [0.15 12.0]`/`fov 360`/`samples 360` 与 Ignition 侧 gpu_lidar 参数对齐，两边 SLAM 输入同构；`drive "diff"` 声明差速底盘；`odom_err` 六元组是注入里程计误差（x/y/角度漂移），999999 表示该项误差被压到无穷小（理想里程计）。

**墙体与场景实例**（对应第13讲地图与第20讲多车）：

```lisp
define wall model
(
  size [0.2 0.2 0.5]
  color "gray"
  block
  (
    points 4
    point [0 0]  point [1 0]  point [1 1]  point [0 1]
    z [0 0.5]
  )
)

wall ( pose [4 0 0 90] size [8 0.2 0.5] name "wall_north" )
wall ( pose [-4 0 0 90] size [8 0.2 0.5] name "wall_south" )
wall ( pose [0 4 0 0] size [8 0.2 0.5] name "wall_east" )
wall ( pose [0 -4 0 0] size [8 0.2 0.5] name "wall_west" )
wall ( pose [0 0 0 0] size [1 1 0.5] name "obstacle_center" )

robot ( pose [0 -2 0 0] name "robot1" )
```

- `block` 用点列定义多边形轮廓 + `z` 拉伸成体；实例化时 `pose [x y z 角度]`、`size` 覆盖模板默认值；`robot1` 一行实例化机器人。要造多车（第20讲），再写 `robot ( pose [2 -2 0 0] name "robot2" )` 即可，话题自动按名称隔离。

**sim.launch.py**：三个节点——`stage_ros2`（`arguments=[world_path]`）、`robot_state_publisher`（发布 URDF 与静态 tf）、`rviz2`，全部 `use_sim_time: True`；teleop 同样定义未启用。

### 24.4.5 mapper_params_online_sync.yaml 逐项讲解（`demo_slam/config/`，40 行）

**第一组 · 插件配置（帧与话题）**

| 参数 | 取值 | 说明 |
|---|---|---|
| `odom_frame` | odom | 里程计帧，`odom→base` 的父帧 |
| `map_frame` | map | 地图帧，SLAM 发布 `map→odom` |
| `base_frame` | base_footprint | 机器人基准帧，须与 URDF/仿真一致 |
| `scan_topic` | scan | 输入激光话题 |
| `use_map_saver` | true | 允许节点内保存地图 |
| `mode` | mapping | mapping / localization 二选一 |

**第二组 · 调试模式（性能与节流）**

| 参数 | 取值 | 说明 |
|---|---|---|
| `debug_logging` | false | 调试日志开关，排查时可开 |
| `throttle_scans` | 1 | 每 N 帧取 1 帧雷达（1 = 全取） |
| `transform_publish_period` | 0.02 | tf 发布周期（秒），0.02 = 50Hz |
| `map_update_interval` | 5.0 | 地图发布间隔（秒） |
| `resolution` | 0.05 | 栅格分辨率（米/格），与 Stage/世界分辨率呼应 |
| `max_laser_range` | 12.0 | 建图使用的最大雷达量程，须 ≤ 传感器实际量程 |
| `minimum_time_interval` | 0.5 | 两次处理的最小时间间隔（秒） |
| `transform_timeout` | 0.2 | tf 查找超时（秒） |
| `tf_buffer_duration` | 30.0 | tf 缓冲时长（秒） |
| `stack_size_to_use` | 40000000 | 节点栈大小（字节），递归优化需要（启动日志可见同值回显） |

**第三组 · 在线同步建图（运动阈值）**

| 参数 | 取值 | 说明 |
|---|---|---|
| `minimum_travel_distance` | 0.5 | 平移超过 0.5m 才插入新节点（课程演示用大值让图稀疏易观察；精细建图建议 0.2 左右） |
| `minimum_travel_heading` | 0.5 | 旋转超过 0.5rad 才插入新节点 |

**第四组 · 建图保存与加载**

| 参数 | 取值 | 说明 |
|---|---|---|
| `map_file_name` | my_map | 序列化文件名（.posegraph/.data 与 pgm） |
| `map_start_pose` | [0.0, 0.0, 0.0] | 继续建图时的初始位姿 |

**第五组 · 优化参数（Ceres 求解器）**

| 参数 | 取值 | 说明 |
|---|---|---|
| `solver_plugin` | solver_plugins::CeresSolver | 图优化后端 |
| `ceres_linear_solver` | SPARSE_NORMAL_CHOLESKY | 稀疏乔列斯基分解 |
| `ceres_preconditioner` | SCHUR_JACOBI | 预条件器 |
| `ceres_trust_strategy` | LEVENBERG_MARQUARDT | 信赖域策略 |
| `ceres_dogleg_type` | TRADITIONAL_DOGLEG | Dogleg 类型 |
| `ceres_loss_function` | None | 鲁棒核函数 |

- 这组是回环优化的数值细节，入门阶段保持默认即可；真正影响建图手感的是第二、三组（分辨率、量程、运动阈值）。

### 24.4.6 cartographer.lua 配置要点（`demo_slam/config/cartographer.lua`）

```lua
include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  map_frame = "map",
  tracking_frame = "base_footprint",
  published_frame = "odom",
  odom_frame = "odom",
  provide_odom_frame = false,
  publish_frame_projected_to_2d = true,
  use_odometry = true,
  use_nav_sat = false,
  use_landmarks = false,
  num_laser_scans = 1,
  num_multi_echo_laser_scans = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 0,
  lookup_transform_timeout_sec = 0.2,
  submap_publish_period_sec = 0.3,
  pose_publish_period_sec = 5e-3,
  trajectory_publish_period_sec = 30e-3,
  -- 六项 *_sampling_ratio（rangefinder/odometry/fixed_frame_pose/imu/gps/landmark）均为 1.0，略
}

MAP_BUILDER.use_trajectory_builder_2d = true
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true

return options
```

- 帧配置四件套：`map_frame`/`tracking_frame`/`published_frame`/`odom_frame`——`tracking_frame` 是传感器数据汇聚的 tf 帧（此处 base_footprint），写错报 `lookupTransform` 失败。
- `use_odometry: true` 融合 `/odom`；`num_laser_scans: 1` 与单线雷达对应；`num_point_clouds: 0` 表示不吃 3D 点云。
- 两个关键开关：`use_trajectory_builder_2d = true`（2D 建图）与 `use_online_correlative_scan_matching = true`（在线相关扫描匹配，里程计误差大时显著改善鲁棒性）。
- launch 侧（`cartographer_launch.py`）：`cartographer_node` 以 `-configuration_directory` + `-configuration_basename` 吃 lua，`cartographer_occupancy_grid_node` 负责把位姿图渲染成 `/map`，再加 rviz2，全部 `use_sim_time: True`。

### 24.4.7 构建与调试命令集

```bash
# 构建
cd code/ws06_sim_nav && colcon build --packages-select demo_ign_sim demo_stage_sim demo_slam
source install/setup.bash

# Gz 仿真一键启动 + 遥控
ros2 launch demo_ign_sim sim_launch.py
ros2 run teleop_twist_keyboard teleop_twist_keyboard_node   # 另开终端

# 验证桥接
gz topic -l                       # gz 侧真实话题名（写 bridge.yaml 前先看）
ros2 topic list                   # ROS2 侧话题
ros2 topic hz /scan               # 雷达频率（应约 10Hz）
ros2 topic info -v /cmd_vel       # publisher/subscriber 数量核对

# Stage 仿真（需已安装 ros-jazzy-stage-ros2）
ros2 launch demo_stage_sim sim.launch.py

# SLAM 建图（slam_toolbox 同步模式 / cartographer）
ros2 launch demo_slam online_sync_launch.py
ros2 launch demo_slam cartographer_launch.py

# 建图调试三件套
ros2 run rqt_graph rqt_graph                        # 节点关系
ros2 run tf2_tools view_frames                      # tf 树完整性
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map   # 保存 pgm+yaml
```

## 24.5 运行效果（实测）

### 24.5.1 Gz（Ignition/Gz）仿真一键启动

**需求**：编写 SDF 世界（四面墙 + 差速小车 + GPU 激光雷达 + diff_drive 插件），launch 一键启动「仿真器 + ros_gz 桥接 + rviz2」。

> 兼容提示：课程环境为 Humble + Ignition Fortress，启动命令 `ign gazebo -r`；Jazzy 配套 **Gz Harmonic**，命令为 `gz sim -r`。Harmonic 下 `<plugin name>` 需写**完整插件类名**（如 `gz::sim::systems::DiffDrive`），短名会报 `library does not contain requested plugin`。

```bash
ros2 launch demo_ign_sim sim_launch.py
```

桥接节点自动建立三条通道：

```text
Creating GZ->ROS Bridge: [/cmd_vel (ignition.msgs.Twist) -> /cmd_vel (geometry_msgs/msg/Twist)]
Creating GZ->ROS Bridge: [/scan (ignition.msgs.LaserScan) -> /scan (sensor_msgs/msg/LaserScan)]
Creating GZ->ROS Bridge: [/model/robot1/odometry (ignition.msgs.Odometry) -> /odom (nav_msgs/msg/Odometry)]
```

系统插件加载失败数为 0；此时用 `teleop_twist_keyboard` 发布 `/cmd_vel` 即可在 rviz2 中看到 `/scan`、`/odom`、`/tf` 实时更新。

> **视频对照**：课程 `ignition_gazebo仿真之传感器_02雷达仿真基本流程`（727s）中 gpu_lidar SDF 参数为 topic `scan`、update_rate 30、水平 640 线 ±π、垂直 16 线 ±0.2618、量程 0.08~10.0，rviz 中 Add LaserScan 后可见点云——本仓库 demo.sdf 同构（360 线/量程 0.15~12.0），差异仅在采样密度与量程。

**实测过程补记**（摘自 `out/verify/ws06_sim_nav/ign_sim_launch.log`，两次运行）：

- 第一次运行 launch 曾写 `["ign","gazebo","-r",...]`，Jazzy 环境无 `ign` 命令，直接报错后改为 `gz sim`：

```text
FileNotFoundError: [Errno 2] No such file or directory: 'ign'
```

- 第二次以 `gz sim -r` 启动成功。曾用短名 `<plugin name="diff_drive">` 复现课程 BUG（正是上方兼容提示的出处），实测报错全文：

```text
[Err] [SystemLoader.cc:164] Failed to load system plugin: (Reason: library does not contain requested plugin)
- Requested plugin name: [diff_drive]
- Requested library name: [gz-sim-diff-drive-system]
- Resolved library path: [/opt/ros/jazzy/opt/gz_sim_vendor/lib/gz-sim-8/plugins/libgz-sim-diff-drive-system.so]
- Detected Plugins:
  - gz::sim::v8::systems::DiffDrive
    aliases:
      gz::sim::systems::DiffDrive
```

  日志明确列出可用类名——仓库 `demo.sdf` 已按此改为完整类名 `gz::sim::systems::DiffDrive`，此后系统插件加载失败数为 0。
- 本次实测桥接五条通道全部建立（比上方三条展示多出 `/tf` 与 `/clock` 两条）：

```text
Creating GZ->ROS Bridge: [/model/robot1/tf (ignition.msgs.Pose_V) -> /tf (tf2_msgs/msg/TFMessage)]
Creating GZ->ROS Bridge: [/clock (ignition.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)]
```

- 启动时另有两条 SDF 警告（`ground_plane`、`gz_frame_id` 元素 `not defined in SDF`，属 libsdformat 对非标准元素的提示，不影响运行），以及 NVIDIA 显卡下的 `libEGL warning: ... failed to create dri2 screen` 渲染警告（不影响 server 与传感器数据）；Ctrl-C 退出时 gz 进程以退出码 1 结束（信号处理时的已知现象）。

### 24.5.2 Stage 仿真

`demo_stage_sim` 提供 Stage 版本的世界（`worlds/stage.world`，Stage 专有语法）与 launch：

```bash
sudo apt install ros-jazzy-stage-ros2
ros2 launch demo_stage_sim sim.launch.py
```

> 受阻说明：本教程实测环境无 stage_ros2 且无 sudo 权限，未做运行验证；Stage 语法要点（`resolution 0.05`、`define robot position (drive "diff" ...)`）保留在 world 文件中，安装后可直接运行，效果以课程视频为准。

受阻的实测证据（`ros2 launch demo_stage_sim sim.launch.py` 报）：`package 'stage_ros2' not found, searching: [...]`——安装该包后即可消除。

### 24.5.3 SLAM 建图

**需求**：以 slam_toolbox 的**同步模式**（online_sync）为例建图；输入 `/scan` + `/odom` + `/tf`，输出 `/map`；另附 cartographer 的 lua 配置作对照。

`config/mapper_params_online_sync.yaml` 关键参数：

```yaml
slam_toolbox:
  ros__parameters:
    odom_frame: odom
    map_frame: map
    base_frame: base_footprint
    mode: mapping
```

`launch/online_sync_launch.py` 启动 `sync_slam_toolbox_node` + rviz2：

```bash
ros2 launch demo_slam online_sync_launch.py
```

```text
[INFO] [sync_slam_toolbox_node-1]: process started with pid [441135]
[sync_slam_toolbox_node-1] [INFO] [...]: Node using stack size 40000000
[INFO] [rviz2-2]: process started with pid [441136]
```

节点正常上线并等待 `/scan`；配合 24.5.1 的仿真（遥控小车）即可完成建图（课程视频展示完整建图过程）。cartographer 版本提供 `config/cartographer.lua` 与 `cartographer_launch.py`，输入话题一致。

实测日志补记（`out/verify/ws06_sim_nav/slam_launch.log`）：上例第三行之后，日志还回显 rviz2 的渲染环境检查（`Stereo is NOT SUPPORTED`、`OpenGl version: 4.6 (GLSL 4.6)`）；仿真源未同时启动时节点静默等待输入，Ctrl-C 后两进程均 `process has finished cleanly` 正常退出——「无输入不报错」正是 slam_toolbox 的默认行为，排查时用 `ros2 node info /slam_toolbox` 看订阅。

## 24.6 与 ROS2 / 机器人开发的关联

1. **tf2 坐标树的收口**：SLAM 补上最后一环 `map → odom`。导航场景完整 tf 链：`map →(SLAM/AMCL) odom →(里程计/EKF) base_link →(URDF) laser_link/camera_link/imu_link`，这条链贯穿第22–25章全部内容。
2. **nav2 架构的全景认知**：本章的导航架构表是第25章「导航服务器」逐个实操的总纲——先懂 `bt_navigator` 如何调度 planner/controller/behavior，下一章写配置才有的放矢。
3. **传感器接口即插即用**：仿真中的 `LaserScan`/`Image`/`PointCloud2` 话题与实机驱动完全同构，这正是 ROS2「传感器抽象层」的价值：SLAM、Nav2 代码不改一行即可迁移。
4. **launch/参数工程化**：仿真环境（SDF/world）、机器人描述（URDF）、桥接（YAML）、SLAM（yaml/lua）分离管理的思路，直接迁移为实机 bringup 包的标准结构；`use_sim_time`、命名空间、话题 remap 是 bringup 的三个开关。
5. **为多车与实机铺路**：stage_ros2 的多车环境与 Ignition 的命名空间隔离，是第25章多车编队的仿真基础；本章沉淀的「仿真先验证、实机再调参」流程是机器人团队的通用工作法。
6. **时钟域管理**：`/clock` 桥接 + `use_sim_time` 是 ROS2 仿真体系的标准时间方案（bag 回放同理），理解它就理解了「为什么仿真里所有节点要对同一块表」。

## 24.7 自测与练习

1. **概念题**：Nav2 中 `bt_navigator`、`planner_server`、`controller_server`、`behavior_server` 各自的职责是什么？机器人在目标点附近反复绕圈时，你先查哪个组件？
2. **概念题**：仿真的优势与不足各列三条；「sim-to-real gap」在传感器层面体现为什么（提示：噪声、延迟、畸变）？
3. **概念题**：slam_toolbox 的 sync 与 async 节点有何区别？纯定位用哪个节点？
4. **动手任务**：在 Ignition Gazebo 中搭建「带单线雷达的差速底盘机器人 + 简单房间地图」，经 `ros_gz_bridge` 输出 `/scan`、`/odom`、`/tf`，rviz2 中显示雷达扫描。验收标准：`ros2 topic hz /scan` 稳定在 10 Hz 左右，遥控 `/cmd_vel` 时 rviz2 中扫描随机器人移动。
5. **动手任务**：用 slam_toolbox 在上题仿真环境中建图并保存。验收标准：地图中墙体闭合无重影，`map_saver_cli` 产出 `my_map.pgm` 与 `my_map.yaml`，再次启动 `localization` 模式加载该地图能正常定位。
6. **排障任务**：把 `demo.sdf` 的 DiffDrive 插件 `name` 改回短名 `diff_drive`，运行 launch 观察报错，再改回完整类名——用自己的话解释报错链（Requested plugin name → Detected Plugins）。
7. **排障任务**：把 `bridge.yaml` 中 `/clock` 一条删掉再启动，观察哪些节点最先异常（提示：时间戳/tf 外推报错），体会时钟桥接的必要性。

> 参考答案要点：1. `bt_navigator` 行为树调度整条导航；`planner_server` 全局规划；`controller_server` 局部跟踪出 `/cmd_vel`；`behavior_server` 恢复行为；反复绕圈先查局部 costmap 膨胀半径与 controller 参数，再查全局路径是否频繁重规划。2. 优势：低成本/可重复/安全（或可加速）；不足：物理简化、传感器理想化；gap 体现在噪声模型、通信延迟、镜头畸变。3. sync 每帧处理一致性强、CPU 压力大；async 允许丢帧实时性好；纯定位用 `localization_slam_toolbox_node`。4. 桥接方向写反是「有话题无数据」的最常见原因；`use_sim_time` 需全局一致。5. 建图重影优先怀疑里程计标定与 `max_laser_range` 配置；闭合墙体依赖回环（走回起点）。6. 报错说明库中没有注册名为 `diff_drive` 的插件，可用的是 `gz::sim::v8::systems::DiffDrive` 及其别名，故 name 必须写完整类名或其别名。7. 无 `/clock` 时使用仿真时间的节点时间不前进，最先表现为 tf 外推失败与消息时间戳冻结。

## 24.8 常见问题（FAQ）

- **Q：Ignition Gazebo 启动黑屏或卡死？** A：多为 GPU 渲染问题；核显机器可试 `LIBGL_ALWAYS_SOFTWARE=1`，并确认显卡驱动与 `gz-sim` 版本匹配；服务器无显示器时用 `-s`（server only）模式。本仓库实测日志中的 `libEGL warning` 属同类渲染告警，未阻断 server。
- **Q：`gz sim` 报 `library does not contain requested plugin`？** A：Harmonic 下插件短名失效，`<plugin name>` 必须写完整类名（如 `gz::sim::systems::DiffDrive`）；报错会同时列出该库 Detected Plugins，照抄其中之一即可。
- **Q：桥接后 `/scan` 有消息但 rviz2 不显示？** A：先查 `frame_id` 是否在 tf 树中（`ros2 topic echo /scan --field header.frame_id`）；再查 rviz2 Fixed Frame 与 QoS（LaserScan 显示的 Reliability 设为 Best Effort）。
- **Q：`/odom` 或 `/tf` 桥接不上？** A：gz 侧话题名带模型前缀（`/model/robot1/odometry`、`/model/robot1/tf`），用 `gz topic -l` 核对 bridge.yaml 的 `gz_topic_name` 是否与实际一致。
- **Q：slam_toolbox 建图时地图错位/拉花？** A：按顺序排查——里程计是否标定、雷达安装 tf 是否准确、行走是否过快导致扫描畸变、`use_sim_time` 是否统一、`max_laser_range` 是否大于实际量程。
- **Q：`map → odom` 一直不发布？** A：确认 SLAM 节点已收到 `/scan`（`ros2 node info /slam_toolbox`）且 tf 中 `odom → base_link` 存在；SLAM 输入缺失时它会静默等待不报错。
- **Q：stage_ros2 与 Ignition Gazebo 怎么选？** A：验证 2D 导航/编队逻辑、机器资源有限 → stage_ros2；需要 3D 物理、相机/深度/点云、精细传感器模型 → Ignition Gazebo。课程路线是「stage 建直觉、Ignition 做正菜」。
- **Q：cartographer 启动即报 lua/lookupTransform 错误？** A：先核对 `tracking_frame` 与 URDF 中实际帧名（base_footprint/base_link 一字之差即失败）；再确认 `-configuration_directory` 指向 install 后 share 目录中的 lua。
- **Q：深度相机点云在 rviz2 中一片白或错位？** A：多半是 `frame_id` 与 tf 不符或点云密度过大；桥接用 `PointCloudPacked ↔ PointCloud2`，rviz2 中对该显示项的 Size（m）调小、Decay 关闭。

## 24.9 本章小结

- **两大仿真器各司其职**：Stage 用 `.world` 语法（resolution/interval/window/define/实例化）搭 2D 世界，轻量多车；Ignition Gazebo 用 SDF（physics + 四件套系统插件 + 模型/链接/关节 + 系统插件）做 3D 物理与高保真传感器，二者输出的话题接口同构。
- **桥接是 Gazebo 与 ROS2 的唯一通道**：`ros_gz_bridge` 按 yaml 建立五条通道（cmd_vel 下行，scan/odom/tf/clock 上行），`[`/`]`/`|` 方向符与 gz 侧话题前缀是「有话题无数据」的两大嫌疑；`/clock` + `use_sim_time` 构成仿真时钟域。
- **传感器仿真的套路统一**：`<sensor>` 声明（gpu_lidar/camera/depth_camera/imu）→ Sensors 系统插件（ogre2）渲染 → 桥接对应消息类型 → rviz2 显示；参数按真实传感器填（update_rate、samples/fov、量程、噪声）。
- **SLAM 输入三件套、输出两件套**：`/scan`、`/odom`、tf 树（odom→base）进，`/map`、`map→odom` 出；slam_toolbox（yaml 配置、四类节点）与 cartographer（lua 配置、双节点）可互换，重点是 tf 帧名与话题名对齐。
- **一票否决三件事**：`use_sim_time` 全局一致、tf 链路完整、里程计先行标定；再加 Harmonic 的插件完整类名，这四条守住，本章所有实验一次通过。
- **承上启下**：本章产出的仿真环境与栅格地图，正是第25章 Nav2 导航（map_server/amcl/planner/controller）与多车编队的直接输入。
