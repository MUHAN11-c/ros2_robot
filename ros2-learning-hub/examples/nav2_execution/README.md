# Nav2 行为树与 Gazebo 差速车实跑

输入为 SLAM 台架留下的 `learned.yaml`、`learned.pgm`，同目录若有 `learned.occupancy` 则逐格核对重载结果。复用前一实验房间的六个碰撞盒，换成具有轮关节、随动球、GPU 激光和独立世界位姿观测的差速车。导航使用 Nav2 的真实进程与安装版默认行为树。

## 复现

需要本机 Jazzy 的 Nav2 地图、AMCL、规划、控制、行为树、行为服务和速度平滑器，以及 Harmonic、ros_gz_bridge 和无窗口 Ogre2 EGL。验证记录 ZIP 含输入地图。若从下载包复跑，分别解压原创示例与验证记录，保留 `atlas_examples` 内目录关系，把地图参数指向验证记录中的同名文件。

从教材目录运行：

```bash
# 加载本机 Jazzy。示例域 223，实际执行时选择未使用的 1..232。
source /opt/ros/jazzy/setup.bash
# 地图 YAML 引用同目录的 PGM，原始占据数组用于额外的逐格比对。
python3 examples/nav2_execution/validate_execution.py \
  --map-yaml validation-evidence/slam-mapping-captures/learned.yaml --domain-id 223
# 无窗口渲染如需指定驱动，可附加 --egl-vendor-json，指向本机可用的 EGL vendor。
# 解压后从 atlas_examples 运行时，脚本路径改为 nav2_execution/validate_execution.py。
# --report 可把报告另存到尚不存在的文件。
```

## 核对顺序

1. 先起本地 Gazebo 世界与桥。核查唯一 ROS 仿真时钟、真实激光、轮速积分里程计、两轮关节和世界位姿。静态激光安装变换与 SDF 一致。
2. 分阶段配置、激活 MapServer、AMCL、PlannerServer、Velocity Smoother、ControllerServer、BehaviorServer、BT Navigator。启动前用到地图系近参考初值。发送目标前验证两个代价图的实际输入，以及导航器晚加入后两条动态 TF 边的共同时间窗。
3. 默认行为树对真实 `NavigateToPose` 目标运行 NavFn 和 Regulated Pure Pursuit。检查到达、真实行驶后的同 UUID 取消、越界目标、无效控制器 ID，以及选择有效控制器后重新导航。
4. 将动作状态、业务码、取消应答、子动作回执、两级速度及模拟世界和轮速分开记录。回执之后用连续仿真采样核停稳。所有等待另受单调墙钟约束。
5. 依次停用、清理节点。平滑器晚于控制器关闭。只回收本次自建进程。日志、`telemetry.json`、地图与报告在脚本打印的临时目录中。

速度命令为无 Header 的 `Twist`，报告记录旁路收到时的 ROS 时钟及单调时钟。车辆和关节记录使用发布消息的采样时戳。行为树批次时间与内部事件时间分别保留。实际坐标在仿真世界以 m 表示，偏航用 rad。测得的停车与误差适用于该仿真环境和配置，实际硬件制动、外部急停和动态人车交互各需独立验证。
