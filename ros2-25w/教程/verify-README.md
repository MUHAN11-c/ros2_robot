# 运行验证存档说明（out/verify/）

本目录保存教程全部「运行效果」的实测终端输出，由验证脚本逐包运行产生：

| 目录 | 工作空间 | 内容 |
| --- | --- | --- |
| `out/verify/ws01_plumbing/` | code/ws01_plumbing | 话题/服务/动作/参数/launch/rosbag2/tf/URDF/Xacro 共 30+ 案例 |
| `out/verify/ws02_middle/` | code/ws02_middle | 时间 API 与期中大作业（turtlesim 综合） |
| `out/verify/ws03_exercise/` | code/ws03_exercise | Mycar 练习（pub_vel/Cru 服务/Nav 动作/bringup/multi_tf/follow） |
| `out/verify/ws04_advanced/` | code/ws04_advanced | 生命周期/进程内通信/参数事件/组件/插件 |
| `out/verify/ws05_sensor/` | code/ws05_sensor | 里程计/激光/点云/相机/IMU/GNSS 仿真话题 |
| `out/verify/ws06_sim_nav/` | code/ws06_sim_nav | 语音控制/Gazebo 仿真/SLAM/Nav2 启动 |

- 每个文件开头注明了复现命令（`--- run: ...`），任何一条都可在本机直接复现；
- 教程正文中「运行效果」小节引用的输出均摘自这些日志（时间戳为实测时刻）。

## 复现环境

```bash
# Jazzy + turtlesim(源码编译) + rosidl 中文路径补丁，见 /tmp/ros_env.sh 同款配置
source /opt/ros/jazzy/setup.bash
cd code/<工作空间>
colcon build
source install/setup.bash
# 然后按教程各节命令运行
```

## 已知受阻项（环境不可用，非代码问题）

| 案例 | 原因 | 教程处理 |
| --- | --- | --- |
| demo_stage_sim（Stage 仿真器） | 本机未安装 stage_ros2 且无 sudo | 正文给出安装命令，效果以课程视频为准 |
| voice_input（键盘模拟语音输入） | 需要交互式终端/真实 ASR 通道 | 以手动发布 `/voice_cmd_text` 实测替代 |
