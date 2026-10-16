# 第24章 仿真环境与 SLAM 建图

> 本章搭建两类仿真环境（Gazebo 与 Stage），并以 slam_toolbox 为例完成 SLAM 建图链路。
>
> 本章对应代码：`code/ws06_sim_nav/src/demo_ign_sim`、`demo_stage_sim`、`demo_slam`。

## 24.1 概览与课时结构

### 24.1.1 本周概览

本周进入「仿真 → 建图」核心环节，三大板块递进：先用 stage_ros2 建立轻量 2D 仿真直觉，再用 Ignition Gazebo 搭建物理级 3D 仿真环境（含 URDF 插件、运动控制、雷达/相机/深度相机），最后打开导航大门——理解 Nav2 架构并用 slam_toolbox / cartographer 完成 SLAM 建图。在 25 周体系中，本周是「从传感器数据到地图产出」的转折点：前两周的 `/scan`、`/odom` 在这里成为建图输入，下周的定位与导航在此产出的地图上运行。学完本章，你能独立搭建可复用的仿真工程，并完成机器人边走边建图。

### 24.1.2 课时结构

课程信息：视频 85 个，总时长约 10h34m，难度：高阶。

| 课 | 小节 | 时长 | 一句话导览 |
|---|---|---|---|
| 第1课 ROS2仿真与仿真器stage_ros2 | 20 节 | 2h12m | 仿真概念与优劣、stage_ros2 world/窗体/模型/地图/机器人（底盘/摄像头/雷达）与多车环境 |
| 第2课 仿真器之ignition gazebo | 35 节 | 5h02m | 安装与界面、ros_gz_bridge 集成与 launch 工程化、仿真环境创建、模型/机器人添加、运动控制与传感器仿真 |
| 第3课 ROS2机器人导航概述与SLAM导航详解 | 30 节 | 3h19m | 导航概念与 Nav2 架构、导航条件、slam_toolbox 在线同步/异步建图、cartographer 建图 |

## 24.2 知识点梳理

### 24.2.1 第1课 ROS2仿真与仿真器stage_ros2（2h12m · 20 节）

- **核心概念**：仿真（Simulation）是在计算机中构建机器人的数字模型与物理环境，替代部分实机开发；stage_ros2 是 Stage 2D 仿真器的 ROS2 封装，轻量、专注 2D 移动机器人（差速底盘 + 2D 雷达 + 低分辨率相机）。
- **要点 1 · 仿真概述**：实体机器人开发的缺陷——硬件贵、易损坏、实验不可复现、危险场景难测试；仿真的优势是低成本、可重复、可加速、安全，不足是「仿真到实机的鸿沟（sim-to-real gap）」：物理参数、传感器噪声、延迟在仿真中都被简化。
- **要点 2 · stage_ros2 框架搭建**：基本流程 = 编写 `.world` 文件 → `ros2 run stage_ros2 stageros <world文件>` → 话题通信。`.world` 的全局参数：`interval`（仿真步长）、`gui`（是否开窗口）等。
- **要点 3 · 窗体与模型**：仿真环境组成 = 窗体（window，视口/缩放/跟随）+ 地图（floorplan，基于位图的二维占据栅格）+ 模型（model）。基本模型三件套：

  | 模型块 | 作用 | 关键参数 |
  |---|---|---|
  | `positionmodel` | 差速/全向/阿克曼运动底盘 | `odom`、`localization`、`size` |
  | `ranger` | 2D 激光雷达/声呐 | `scans`、`fov`、`range` |
  | `camera` | 低分辨率相机 | `resolution`、`range` |

- **要点 4 · 添加地图与机器人**：地图用 PGM/BMP 位图 + 分辨率；机器人代码框架中逐块配置底盘（轮径/轮距/最大速度）、摄像头、雷达，并通过 `stage_ros2` 自动桥接的 `/cmd_vel`、`/odom`、`/scan`、`/camera/image_raw` 与 ROS2 通信；多车环境通过在 `.world` 中定义多个 `positionmodel` 并配 `tf_prefix`/命名空间实现。
- **要点 5 · stage_ros2 的定位**：适合快速验证导航/编队算法逻辑（如第25 章多车编队即用它），不适合传感器算法（相机物理、点云、惯导）——那要交给 Ignition Gazebo。

### 24.2.2 第2课 仿真器之ignition gazebo（5h02m · 35 节）

- **核心概念**：Ignition Gazebo（现更名为 Gazebo，即 "New Gazebo" / gz-sim）是物理级 3D 仿真器，支持刚体动力学、接触、光照与高保真传感器（GPU 雷达、相机、深度相机、IMU）。
- **要点 1 · 安装运行与界面**：`sudo apt install ros-humble-ros-gz`（含 `ros_gz_sim`、`ros_gz_bridge`）；界面含场景（Scene）、实体树（Entity Tree）、组件/ECM 检查器、资源浏览器、时间控制（暂停/单步/加速比）。
- **要点 2 · 与 ROS2 集成（桥接）**：Gazebo 用 Transport（gz topic）通信，ROS2 用 DDS，二者靠 `ros_gz_bridge` 的 `parameter_bridge` 节点按「桥接描述符」双向转发：

  ```bash
  ros2 run ros_gz_bridge parameter_bridge /cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist \
    /odom@nav_msgs/msg/Odometry[gz.msgs.Odometry \
    /scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan
  # 语法：<ros_topic>@<ros_type>[|]<gz_type>：| 双向、[ 单向 gz→ros、] 单向 ros→gz
  ```

  集成优化环节把桥接配置迁移到 YAML（`config/bridge.yaml`），由 launch 统一加载，避免命令行爆炸。
- **要点 3 · 集成工程化**：一个 launch 完成「启动仿真环境（`ros_gz_sim launch`）→ 启动 rviz2（加载统一配置）→ 启动桥接节点」；测试中记录的 BUG（如话题名不匹配、QoS 不兼容、`use_sim_time` 未统一）与修复方法是实机迁移的预演。
- **要点 4 · 仿真环境创建**：SDF（Simulation Description Format）文件定义世界：框架搭建 → 墙体轮廓（`<model>` + `<link>` + `<collision>`/`<visual>` 的 `<box>` 几何）→ 墙体尺寸设置（pose 定位 + scale 尺寸）；添加模型（Fuel 资源库下载 桌椅/货架 等模型并配置 `~/.gz/fuel` 资源路径）。
- **要点 5 · 添加机器人与运动控制**：把 URDF/xacro 机器人模型经 `ros_gz_sim create`（或 spawn launch）放入世界；运动控制靠 URDF `<gazebo>` 标签加载 gz 系统插件，典型是差速驱动插件：

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

- **要点 6 · 传感器仿真**：URDF/xacro 中用 `<sensor>` 声明并由 `gz-sim-sensors-system`（含 `gz::sim::systems::Sensors` 渲染）加载：

  | 传感器 | SDF sensor type | 桥接到 ROS2 |
  |---|---|---|
  | 单线雷达 | `gpu_lidar` | `sensor_msgs/LaserScan`（2D 时）或 `PointCloud2` |
  | 单目相机 | `camera` | `sensor_msgs/Image` + `CameraInfo` |
  | 深度相机 | `depth_camera` | `Image`（深度）+ `PointCloud2` |

  每类都分「添加」与「参数」两讲：采样率（`update_rate`）、分辨率/线数、视场角（hfov/vfov）、噪声（`<noise><type>gaussian`）需按真实传感器填写；深度相机点云还需配置 `gz.msgs.PointCloudPacked` 到 `sensor_msgs/PointCloud2` 的桥接；最后「整体集成」把全部桥接与显示收口到统一 launch。

- **要点 7 · 工程习惯**：世界文件（SDF）、机器人描述（URDF/xacro）、桥接配置（YAML）、launch、rviz2 配置五类文件分目录管理（`worlds/`、`urdf/`、`config/`、`launch/`、`rviz/`），是本阶段所有仿真作业的推荐骨架。

### 24.2.3 第3课 ROS2机器人导航概述与SLAM导航详解（3h19m · 30 节）

- **核心概念**：导航（Navigation）= 在地图中定位自身 + 规划全局路径 + 局部避障跟踪到目标点；Nav2（Navigation2）是 ROS2 官方导航框架，由一组生命周期管理的服务端（server）节点 + 行为树（Behavior Tree）协调器组成。
- **要点 1 · Nav2 在导航中的作用**：提供感知→决策→控制的完整栈：代价地图（costmap）、全局/局部规划器、控制器、恢复行为、路点跟踪，支持插件化替换算法（如 planner：NavFn / Smac / Theta*；controller：DWB / MPPI / RPP）。
- **要点 2 · 导航架构（30 分钟大课，务必精读）**：

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

- **要点 3 · 导航安装与条件**：`sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup`；导航前提条件：① 完整 tf 树（`map → odom → base_link → <sensors>`）；② 里程计（`/odom` 或融合里程计）；③ 激光/点云障碍数据；④ 静态地图（导航模式）或 SLAM；⑤ 速度控制接口 `/cmd_vel`。条件准备课即逐项验收这些输入。
- **要点 4 · SLAM 概念与作用**：SLAM（Simultaneous Localization and Mapping，同时定位与地图构建）让机器人在未知环境中边走边估计自身位姿并构建地图；输出 2D 占据栅格地图 + `map → odom` 变换。
- **要点 5 · slam_toolbox**：ROS2 默认 2D SLAM 方案，基于图优化（pose graph），支持在线/离线、同步/异步建图与纯定位模式，可序列化地图（`.posegraph` + `.data`）继续建图。关键节点：`async_slam_toolbox_node`（在线异步）、`sync_slam_toolbox_node`（在线同步）、`localization_slam_toolbox_node`（纯定位）、`map_saver_cli`（地图保存）。核心参数：`odom_frame`/`base_frame`/`map_frame`、`scan_topic`、`mode`（mapping/localization）、`resolution`（默认 0.05 m）、`max_laser_range`、`minimum_travel_distance`/`minimum_travel_heading`。
- **要点 6 · slam_toolbox 基本使用（九讲）**：流程简介 → 自建功能包（放 launch/yaml，勿改动官方包）→ **在线同步建图**：launch + yaml 编写（18 分钟重点课，逐参数讲解）→ 构建与运行 → **在线异步建图**（`async` 节点，实时性更好，适合边走边建）→ `rqt_graph` 查看节点关系（验证 `/scan`、`/odom`、tf 输入）→ launch 移植优化（参数化、兼容仿真/实机）→ 小结。
- **要点 7 · cartographer**：Google 开源的图优化 SLAM，支持 2D/3D、激光+IMU 融合建图，精度高但配置复杂（Lua 配置文件）。组成：`cartographer_node`（建图核心，输出 `.pbstream` 位姿图）+ `cartographer_occupancy_grid_node`（把位姿图渲染为占据栅格地图）。基本使用：安装 → 节点说明 → 功能包框架 → launch 文件（加载 `*.lua` 配置 + URDF + 启动两节点）→ 执行 → launch 优化。
- **要点 8 · 选型建议**：纯 2D 激光、求稳用 slam_toolbox（工程化好、与 Nav2 无缝）；需要激光+IMU 融合、追求建图质量、可接受 Lua 调参成本时用 cartographer。

## 24.3 重点与难点

1. **tf 链路是导航的命脉**：`map → odom`（SLAM/AMCL）+ `odom → base_link`（里程计/EKF）+ `base_link → <sensor>`（URDF）缺一环即瘫痪。每换一个仿真器/实机，第一件事是 `ros2 run tf2_tools view_frames` 查图。
2. **`use_sim_time` 全局一致性**：仿真中所有节点（含 rviz2、Nav2、SLAM）都必须设 `use_sim_time: true`，否则消息时间戳与 tf 时间错位，报 `extrapolation into the past/future`。
3. **ros_gz_bridge 桥接描述符语法**：`[` / `]` / `|` 决定方向，写反会出现「有话题无数据」；桥接 YAML 化后要用 `ros2 topic info -v` 确认 publisher/subscriber 数量符合预期。
4. **SLAM 建图质量控制**：行走速度慢而匀、转弯缓、回环闭合走回起点、`max_laser_range` 与实际雷达一致、里程计标定（第23 章）先行——里程计烂，地图就重影。
5. **同步 vs 异步建图**：sync 每帧处理保证一致性、CPU 压力大；async 允许丢帧、实时性好。探索式建图用 async，精细建图用 sync。
6. **仿真 → 实机迁移要点**：仿真插件话题名（`/scan`、`/cmd_vel`）尽量与实机驱动保持一致；传感器噪声参数在仿真中模拟出来，才能提前暴露导航鲁棒性问题。

## 24.4 代码与命令实战

### 24.4.1 场景 1：stage_ros2 世界文件骨架（文件 `worlds/my_robot.world`）

```lisp
# Stage world 文件（简化示意）
size [24 24]            # 世界尺寸（米）
interval 100            # 仿真步长（毫秒）

window
( center [0 0] scale 20 show_data 1 )

floorplan
( name "map" bitmap "map.png" size [24 24 0.5] pose [0 0 0 0] )

define differential_robot position
( size [0.4 0.3] origin [0 0 0 0] odom "odom" localization "gps" )
  # 底盘
  power
  ( velocity [0.5 0 1.0] )         # 最大线速度/角速度

define lidar ranger
( scount 360 spose [0 0 0] ssize [0.02] sview [0 360] srange [0.05 8.0] )

differential_robot( name "robot1" pose [2 2 0 0] color "blue"
  power.unit( actuator )
  lidar( scount 360 )
  camera( resolution [64 48] range [0.2 8] )
)
```

```bash
ros2 run stage_ros2 stageros worlds/my_robot.world   # 启动仿真
ros2 topic list        # 应出现 /robot1/cmd_vel /robot1/odom /robot1/scan 等
```

### 24.4.2 场景 2：Ignition Gazebo 桥接 YAML（文件 `config/bridge.yaml`）

```yaml
- ros_topic_name: "/cmd_vel"
  gz_topic_name: "/model/robot/cmd_vel"
  ros_type_name: "geometry_msgs/msg/Twist"
  gz_type_name: "gz.msgs.Twist"
  direction: ROS_TO_GZ          # 控制指令：ROS → 仿真
- ros_topic_name: "/odom"
  gz_topic_name: "/model/robot/odometry"
  ros_type_name: "nav_msgs/msg/Odometry"
  gz_type_name: "gz.msgs.Odometry"
  direction: GZ_TO_ROS
- ros_topic_name: "/scan"
  gz_topic_name: "/world/demo/model/robot/link/lidar_link/sensor/lidar/scan"
  ros_type_name: "sensor_msgs/msg/LaserScan"
  gz_type_name: "gz.msgs.LaserScan"
  direction: GZ_TO_ROS
```

```bash
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=config/bridge.yaml
ros2 topic hz /scan        # 验证桥接后话题频率
```

### 24.4.3 场景 3：URDF 中的雷达传感器插件（xacro 片段）

```xml
<gazebo reference="lidar_link">
  <sensor name="lidar" type="gpu_lidar">
    <topic>scan</topic>
    <update_rate>10</update_rate>            <!-- 10 Hz -->
    <ray>
      <scan><horizontal><samples>360</samples>
        <min_angle>-3.14159</min_angle><max_angle>3.14159</max_angle></horizontal></scan>
      <range><min>0.05</min><max>8.0</max><resolution>0.01</resolution></range>
      <noise><type>gaussian</type><mean>0.0</mean><stddev>0.01</stddev></noise>
    </ray>
  </sensor>
</gazebo>
```

### 24.4.4 场景 4：slam_toolbox 在线同步建图 launch（文件 `launch/sync_slam.launch.py`）

```python
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

pkg = get_package_share_directory('my_slam_pkg')
params = os.path.join(pkg, 'config', 'slam_toolbox.yaml')

def generate_launch_description():
    return LaunchDescription([
        Node(package='slam_toolbox', executable='sync_slam_toolbox_node',
             name='slam_toolbox', output='screen',
             parameters=[params, {'use_sim_time': True}]),
    ])
```

```yaml
# config/slam_toolbox.yaml 核心参数
slam_toolbox:
  ros__parameters:
    odom_frame: odom
    map_frame: map
    base_frame: base_link
    scan_topic: /scan
    mode: mapping                 # mapping / localization
    resolution: 0.05              # 栅格 5cm
    max_laser_range: 8.0
    minimum_travel_distance: 0.2  # 走 20cm 才更新一次节点
    minimum_travel_heading: 0.2
```

### 24.4.5 场景 5：SLAM 调试命令集

```bash
ros2 launch my_slam_pkg sync_slam.launch.py        # 启动建图
ros2 run teleop_twist_keyboard teleop_twist_keyboard_node   # 慢速遥控走图
ros2 run rqt_graph rqt_graph                        # 检查 /scan /odom 是否接入
ros2 run tf2_tools view_frames                      # 确认 map->odom->base_link 齐全
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map   # 保存地图（pgm+yaml）
ros2 bag record /scan /odom /tf /tf_static -o slam_raw     # 录数据离线复现建图
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

### 24.5.2 Stage 仿真

`demo_stage_sim` 提供 Stage 版本的世界（`worlds/stage.world`，Stage 专有语法）与 launch：

```bash
sudo apt install ros-jazzy-stage-ros2
ros2 launch demo_stage_sim sim.launch.py
```

> 受阻说明：本教程实测环境无 stage_ros2 且无 sudo 权限，未做运行验证；Stage 语法要点（`resolution 0.05`、`define robot position (drive "diff" ...)`）保留在 world 文件中，安装后可直接运行，效果以课程视频为准。

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

## 24.6 与 ROS2 / 机器人开发的关联

1. **tf2 坐标树的收口**：SLAM 补上最后一环 `map → odom`。导航场景完整 tf 链：`map →(SLAM/AMCL) odom →(里程计/EKF) base_link →(URDF) laser_link/camera_link/imu_link`，这条链贯穿第22–25 章全部内容。
2. **nav2 架构的全景认知**：本章的导航架构表是第25 章「导航服务器」逐个实操的总纲——先懂 `bt_navigator` 如何调度 planner/controller/behavior，下一章写配置才有的放矢。
3. **传感器接口即插即用**：仿真中的 `LaserScan`/`Image`/`PointCloud2` 话题与实机驱动完全同构，这正是 ROS2「传感器抽象层」的价值：SLAM、Nav2 代码不改一行即可迁移。
4. **launch/参数工程化**：仿真环境（SDF/URDF）、桥接（YAML）、SLAM（yaml）分离管理的思路，直接迁移为实机 bringup 包的标准结构；`use_sim_time`、命名空间、话题 remap 是 bringup 的三个开关。
5. **为多车与实机铺路**：stage_ros2 的多车环境与 Ignition 的命名空间隔离，是第25 章多车编队的仿真基础；本章沉淀的「仿真先验证、实机再调参」流程是机器人团队的通用工作法。

## 24.7 自测与练习

1. **概念题**：Nav2 中 `bt_navigator`、`planner_server`、`controller_server`、`behavior_server` 各自的职责是什么？机器人在目标点附近反复绕圈时，你先查哪个组件？
2. **动手任务**：在 Ignition Gazebo 中搭建「带单线雷达的差速底盘机器人 + 简单房间地图」，经 `ros_gz_bridge` 输出 `/scan`、`/odom`、`/tf`，rviz2 中显示雷达扫描。验收标准：`ros2 topic hz /scan` 稳定在 10 Hz 左右，遥控 `/cmd_vel` 时 rviz2 中扫描随机器人移动。
3. **动手任务**：用 slam_toolbox 在上题仿真环境中建图并保存。验收标准：地图中墙体闭合无重影，`map_saver_cli` 产出 `my_map.pgm` 与 `my_map.yaml`，再次启动 `localization` 模式加载该地图能正常定位。

> 参考答案要点：1. `bt_navigator` 行为树调度整条导航；`planner_server` 全局规划；`controller_server` 局部跟踪出 `/cmd_vel`；`behavior_server` 恢复行为。反复绕圈先查局部 costmap 膨胀半径与 controller 参数（如 goal checker 容差），再查全局路径是否频繁重规划。2. 桥接方向写反是「有话题无数据」的最常见原因；`use_sim_time` 需全局一致。3. 建图重影优先怀疑里程计标定与 `max_laser_range` 配置；闭合墙体依赖回环（走回起点）。

## 24.8 常见问题（FAQ）

- **Q：Ignition Gazebo 启动黑屏或卡死？** A：多为 GPU 渲染问题；核显机器可试 `LIBGL_ALWAYS_SOFTWARE=1`，并确认显卡驱动与 `gz-sim` 版本匹配；服务器无显示器时用 `-s`（server only）模式。
- **Q：桥接后 `/scan` 有消息但 rviz2 不显示？** A：先查 `frame_id` 是否在 tf 树中（`ros2 topic echo /scan --field header.frame_id`）；再查 rviz2 Fixed Frame 与 QoS（LaserScan 显示的 Reliability 设为 Best Effort）。
- **Q：slam_toolbox 建图时地图错位/拉花？** A：按顺序排查——里程计是否标定、雷达安装 tf 是否准确、行走是否过快导致扫描畸变、`use_sim_time` 是否统一、`max_laser_range` 是否大于实际量程。
- **Q：`map → odom` 一直不发布？** A：确认 SLAM 节点已收到 `/scan`（`ros2 node info /slam_toolbox`）且 tf 中 `odom → base_link` 存在；SLAM 输入缺失时它会静默等待不报错。
- **Q：stage_ros2 与 Ignition Gazebo 怎么选？** A：验证 2D 导航/编队逻辑、机器资源有限 → stage_ros2；需要 3D 物理、相机/深度/点云、精细传感器模型 → Ignition Gazebo。课程路线是「stage 建直觉、Ignition 做正菜」。

## 24.9 本章小结

- Gazebo 世界 = 模型 + 系统插件（physics/sensors/diff_drive），桥接由 `ros_gz_bridge` 按 yaml 配置建立，`[`/`]`/`|` 三个方向符是「有话题无数据」的头号嫌疑；
- Stage 适合 2D 导航/编队逻辑的轻量验证，Ignition Gazebo 承担 3D 物理与高保真传感器仿真，二者互补；
- SLAM 输入的三件套：`/scan`、`/odom`、tf 树（odom→base）；slam_toolbox 与 cartographer 可互换，重点是 tf 帧名与话题名对齐；
- `use_sim_time` 全局一致、tf 链路完整、里程计先行标定，是本章三个一票否决项。
