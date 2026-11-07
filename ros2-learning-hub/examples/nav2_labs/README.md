# 固定激光台架的 Nav2 地图、定位和规划

在 Ubuntu 24.04、ROS 2 Jazzy、Gazebo Harmonic 8.15.0 和 `ros_gz_bridge` 1.0.24 上运行。实测 `nav2_map_server`、`nav2_amcl`、`nav2_planner`、`nav2_costmap_2d`、`nav2_navfn_planner` 和 `nav2_msgs` 均为 1.3.13。配套 Python 使用 `rclpy`、Nav2 消息、标准生命周期与参数服务、`tf2_ros`。环境还需要能用 Ogre2 在无窗口模式生成激光的 EGL 驱动。

## 运行

从完整教材的 `ros2-learning-hub` 目录运行。需要另存时，给 `--report` 指定一个尚不存在的路径。

```bash
# 先加载实际安装的 Jazzy。229 是示例使用的本机隔离域，可换成未占用的 1..232。
source /opt/ros/jazzy/setup.bash
python3 examples/nav2_labs/validate_nav2.py --domain-id 229
# 本机复现采用已经安装的 NVIDIA EGL vendor；其他机器可省略该参数或选择本机可用的 JSON。
python3 examples/nav2_labs/validate_nav2.py --domain-id 229 \
  --egl-vendor-json /usr/share/glvnd/egl_vendor.d/10_nvidia.json
```

解压 `atlas_examples.zip` 后进入 `atlas_examples/`，将命令路径换成 `nav2_labs/validate_nav2.py`。旁边的 `gazebo_labs/validate_sensors.py` 提供进程管理和单调等待，须随包保留。该台架不需要编译新的 ROS 包。DDS 使用 LOCALHOST，Gazebo 使用独立分区。所有本次生成的文件、日志和服务回执写入一个新建的 `/tmp/ros2-nav2-lab-*` 目录。

## 按输出检查

1. `nav_room.sdf` 含四面墙和一根非对称柱。脚本从这些几何生成 80×60、0.10 m/格的先验图，图像第 0 行位于地图的最高 y 侧。另一个箱体只存在于模拟世界，固定激光的正前方距离为 1.95 m。`bridge.yaml` 转发世界时钟和原采集时戳的扫描。
2. `map_server` 配置后仍为 `inactive`，激活后提供 `map`。两个订阅者都在激活后加入，只有瞬态本地订阅得到已有地图。三类加载失败分别对照 `GetMap`，最后重载同一文件，两个订阅者都能收到新发布。
3. 台架发布固定 `odom → base_link → laser_link`。AMCL 激活后先接收 `odom` 系的初始位姿请求，检查有回执而无新位姿或 `map → odom`。再给 `map` 系的近真值初值，检查定位、无运动更新与按扫描时戳查 TF。初值的 x/y 方差为 0.0025 m²、偏航方差为 0.0025 rad²。
4. PlannerServer 激活后读取 `GetCostmap` 的主图字节，先以 `use_start=false` 验证实际 TF 起点。对比路径固定同一数值起点和目标，先只用静态与膨胀层，再开启真实扫描障碍层的标记。参数回执、箱体附近的致命代价值、旧路径与新路径的 `IsPathValid` 分开检查。两幅原始代价值文件 `static.raw` 和 `marked.raw` 均为每格一字节，按从最低 y 到最高 y 的行主序保存。
5. 对于致命格、图外目标、未知区、无效插件和无效目标帧，分别记录接受回执、终态、错误码和路径数量。关闭顺序与激活相反，验证节点先退出活动状态并清理，然后检查自建进程退出。

各场景的实际坐标、计数、服务结果与日志见报告。相同环境的 AMCL 估计可能随粒子采样小幅变化，验收比较误差和语义。报告中的 `planningNs` 来自仿真 ROS 时间。要测计算耗时，应另建单调时钟测量。

台架验证的是本地静态激光、占据栅格、定位初始化与全局规划。旧路径和新路径按中心线采样对照代价值，未执行足印连续扫掠、SLAM 建图、控制器、行为树、底盘动力学、物理停车或硬件。固定 `odom` 边在运动机器人上应由实际里程计或局部估计器负责。
