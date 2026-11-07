# 运动扫描、SLAM 栅格与位姿图恢复

实测环境为 ROS 2 Jazzy、SLAM Toolbox 2.8.5、Nav2 MapServer 1.3.13、Gazebo Harmonic 8.15.0 和 `ros_gz_bridge` 1.0.24。需要已有的 ROS、Gazebo 与可运行无窗口 Ogre2 的 EGL 驱动。所有进程在本机隔离 DDS 域与 Gazebo 分区运行，按阶段启用节点，结束后清理自建进程。

## 复现

从完整教材的 `ros2-learning-hub` 目录执行。解压 `atlas_examples.zip` 后，从 `atlas_examples/` 执行时将路径改为 `slam_labs/validate_slam.py`。同包的 `nav2_labs` 提供房间和服务辅助，`gazebo_labs` 提供有界等待及进程清理，保留目录结构即可。

```bash
# 加载本机 Jazzy。231 是本次试验的 DDS 域，可换成未占用的 1..232。
source /opt/ros/jazzy/setup.bash
# 输入是同包 SDF、配置和路线，结果写入新建的 /tmp/ros2-slam-lab-*。
python3 examples/slam_labs/validate_slam.py --domain-id 231
# 如果默认 EGL 无法生成激光，在命令末尾加本机已有的 vendor JSON。
# 本机实测使用 --egl-vendor-json /usr/share/glvnd/egl_vendor.d/10_nvidia.json。
# 需要另存报告时，--report 指向一个尚不存在的文件。
```

## 数据与验证顺序

1. `scan_run.py` 从同包房间生成可移位台架。每步先请求放置激光，再推进 80 个 0.005 s 步长，选窗口后半段的实际扫描和 Gazebo 世界位姿，核时间配对及盒形几何。主路线约 13.60 m。激光高 0.30 m，世界位姿是参考值。移动方式是离散移位，采样期间模型静止。
2. `trajectory.json` 保存 361 束的实际距离、采集时戳、配对位姿及采集窗口。回放另有时钟，给里程计的 x 每走 1 m 加 0.014 m，偏航每走 1 m 加 0.002 rad。回放先供时钟及 `odom → base_link → laser_link`，再发扫描。以同戳 `pose`、地图内容及 `map → odom` 验收。
3. 在同步建图节点保存 `learned.pgm` 与 `learned.yaml`，同时序列化 `learned.posegraph` 和 `learned.data`。新 MapServer 用 PGM/YAML 重载，新同步节点用位姿图对恢复并追加扫描。`learned.occupancy` 为实际发布栅格的行主序字节，首行对应较小的 y。值 255 对应 `OccupancyGrid` 的未知值 −1。
4. 新定位节点用 `LOCALIZE_AT_POSE` 恢复原始图。比较定位前、短期扫描加入后、清空定位缓冲后的栅格与节点数。该流程分别核对实时栅格、图中定位节点和磁盘原图文件。

等待和退出用单调墙钟计时。`report.json` 保存两类地图恢复的逐格比对、文件指纹、实际位姿与图约束。传感器来自固定环境中的实际仿真渲染，里程计偏差由实验注入。路线闭合描述采集路径，图中边数记录实际约束。完整导航控制、轮地动力学、物理传感器和跨版本位姿图兼容性各需另行验收。
