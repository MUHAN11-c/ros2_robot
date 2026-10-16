# 第24章 仿真环境与 SLAM 建图

> 本章搭建两类仿真环境（Gazebo 与 Stage），并以 slam_toolbox 为例完成 SLAM 建图链路。
>
> 本章对应代码：`code/ws06_sim_nav/src/demo_ign_sim`、`demo_stage_sim`、`demo_slam`。

## 24.1 Gazebo（Ignition/Gz）仿真

### 24.1.1 案例以及案例分析

**需求**：编写 SDF 世界（四面墙 + 差速小车 + GPU 激光雷达 + diff_drive 插件），launch 一键启动「仿真器 + ros_gz 桥接 + rviz2」。

> 兼容提示：课程环境为 Humble + Ignition Fortress，启动命令 `ign gazebo -r`；Jazzy 配套 **Gz Harmonic**，命令为 `gz sim -r`。Harmonic 下 `<plugin name>` 需写**完整插件类名**（如 `gz::sim::systems::DiffDrive`），短名会报 `library does not contain requested plugin`。

### 24.1.2 运行效果（实测）

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

## 24.2 Stage 仿真

`demo_stage_sim` 提供 Stage 版本的世界（`worlds/stage.world`，Stage 专有语法）与 launch：

```bash
sudo apt install ros-jazzy-stage-ros2
ros2 launch demo_stage_sim sim.launch.py
```

> 受阻说明：本教程实测环境无 stage_ros2 且无 sudo 权限，未做运行验证；Stage 语法要点（`resolution 0.05`、`define robot position (drive "diff" ...)`）保留在 world 文件中，安装后可直接运行，效果以课程视频为准。

## 24.3 SLAM 建图

### 24.3.1 案例以及案例分析

**需求**：以 slam_toolbox 的**同步模式**（online_sync）为例建图；输入 `/scan` + `/odom` + `/tf`，输出 `/map`；另附 cartographer 的 lua 配置作对照。

### 24.3.2 实现

`config/mapper_params_online_sync.yaml` 关键参数：

```yaml
slam_toolbox:
  ros__parameters:
    odom_frame: odom
    map_frame: map
    base_frame: base_footprint
    mode: mapping
```

`launch/online_sync_launch.py` 启动 `sync_slam_toolbox_node` + rviz2。

### 24.3.3 运行效果（实测）

```bash
ros2 launch demo_slam online_sync_launch.py
```

```text
[INFO] [sync_slam_toolbox_node-1]: process started with pid [441135]
[sync_slam_toolbox_node-1] [INFO] [...]: Node using stack size 40000000
[INFO] [rviz2-2]: process started with pid [441136]
```

节点正常上线并等待 `/scan`；配合 24.1 的仿真（遥控小车）即可完成建图（课程视频展示完整建图过程）。cartographer 版本提供 `config/cartographer.lua` 与 `cartographer_launch.py`，输入话题一致。

## 24.4 本章小结

- Gazebo 世界 = 模型 + 系统插件（physics/sensors/diff_drive），桥接由 `ros_gz_bridge` 按 yaml 配置建立；
- SLAM 输入的三件套：`/scan`、`/odom`、tf 树（odom→base）；
- slam_toolbox 与 cartographer 可互换，重点是 tf 帧名与话题名对齐。
