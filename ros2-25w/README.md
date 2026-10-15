# ROS2 机器人应用开发工程师（前 25 周）——代码工程 + 教程 + 实测验证

> 本目录是慕课网《ROS2 机器人应用开发工程师（前 25 周）》课程的自包含交付物：
> **深度阅读 1613 个课程视频后还原的 6 个 colcon 工作空间 / 63 个功能包**，
> 配套按 [zhangzhiwei-zzw.github.io](https://zhangzhiwei-zzw.github.io) 教程格式重写的 25 章教程，
> 以及**逐一运行并与视频效果比对**的完整验证记录。

## 目录结构

```
ros2-25w/
├── README.md            # 本文件
├── code/                # 6 个 colcon 工作空间（63 个功能包，源码）
│   ├── ws01_plumbing/   # 第14-18周：话题/服务/动作/参数、launch/rosbag2、tf、乌龟案例、URDF/Xacro
│   ├── ws02_middle/     # 第16周：时间 API + 期中大作业（turtlesim 综合）
│   ├── ws03_exercise/   # 第19-20周：Mycar 自定义接口、服务/动作、bringup、多机 tf
│   ├── ws04_advanced/   # 第21周：生命周期、进程内通信、组件、插件、参数事件
│   ├── ws05_sensor/     # 第22-23周：里程计、激光/点云/相机/IMU/GNSS 仿真
│   └── ws06_sim_nav/    # 第24-25周：Gz/Stage 仿真、SLAM、Nav2、编队、语音
├── 教程/                # 25 章教程（参考 zhangzhiwei 格式）+ site/ 静态站点
├── out/verify/          # 端到端运行验证日志（164+ 份，含复现命令）
└── 学习笔记附录/        # 代码项目导览
```

## 快速开始

```bash
# 环境：Ubuntu 22.04(Humble) 或 24.04(Jazzy)；本仓库全部包已在 Jazzy 实测通过
cd ros2-25w/code/ws01_plumbing
colcon build
source install/setup.bash
ros2 run cpp01_topic demo01_talker_str        # 第一个话题 demo
```

每个工作空间独立构建；跨工作空间案例（如 ws02 大作业依赖 ws01 接口包）请依次 source。

## 教程与验证

- **教程**：[教程/SUMMARY.md](教程/SUMMARY.md) —— 第 1~13 章为基础篇（Python/C/C++/Linux，示例均实测），第 14~25 章为 ROS2 实战篇（与 code/ 一一对应，运行效果全部来自实测）；静态站点在 [教程/site/](教程/site/index.html)；
- **运行验证矩阵**：[教程/验证矩阵.md](教程/验证矩阵.md) —— 63 包逐一验证结论（60 通过 / 3 项环境受阻）；
- **深度对照报告**：[教程/深度对照报告.md](教程/深度对照报告.md) —— 105 张课程视频帧 × 实测运行，22 个证据系列逐系列比对；
- **端到端核对报告**：[教程/端到端核对报告.md](教程/端到端核对报告.md) —— 回到课程视频文件的运行段落抽帧核对（含 odom/IMU/lifecycle 全状态链）；
- **验证日志**：`out/verify/<工作空间>/<案例>.log`，每份首行附复现命令。

## 还原与适配说明（诚实标注）

- 代码结构与命名按视频逐帧核对还原；`Cru.srv`/`Nav.action` 字段为按课程需求重建；
- Humble ↔ Jazzy 的 API 差异（动作回调签名、rosbag2 读取返回值、参数删除、进程内通信选项、Gz 命令与插件全名等）以「兼容提示」写进教程，并已回写代码；
- 受阻项（非代码问题）：stage_ros2 / usb_cam 本机无法安装，对应 demo_stage_sim、demo_formation、my_exer07_bringup 完整链路，安装依赖后即可复现；
- 安全：`demo_voice` 讯飞凭据仅经 `IFLYTEK_APPID` 环境变量注入，仓库不含任何凭据字面量。
