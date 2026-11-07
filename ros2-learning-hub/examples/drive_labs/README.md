# 差速控制与局部定位软件实验

使用 Jazzy 自带的 ros2_control、差速控制器、关节广播器、robot_state_publisher 和 robot_localization。实验复用同一套下载中的 Xacro 模型，并在内存里运行 GenericSystem。没有电机、总线、仿真器或真实传感器。

从教材目录执行。解压原创示例包时，保留并排的 drive_labs 和 model_labs，从 atlas_examples 目录运行同一脚本。

```bash
# 载入已安装的 Jazzy 二进制环境。需有 xacro、robot_state_publisher、
# controller_manager、joint_state_broadcaster、diff_drive_controller 与 robot_localization。
source /opt/ros/jazzy/setup.bash
# 输入是旁边的配置与固定合成速度。225 是本机实验 DDS 域，可换成一个空闲的 1..232 域。
python3 examples/drive_labs/validate_drive.py --domain-id 225
# 解压示例 ZIP 后从 atlas_examples 目录运行 python3 drive_labs/validate_drive.py。
```

脚本打印新生成的报告路径，所有过程日志和 ROS 日志都放入该目录。它用独立命名空间和 LOCALHOST 发现，检查模型、配置及实际消息后自动停止自己的进程。每次运行写新目录，显式报告路径也须是新文件。

| 阶段 | 观察项 |
| --- | --- |
| 载入模型 | 半径 0.08 m、轮距 0.36 m，静态 TF 和轮子活动 TF 分开验证 |
| 激活与竞争 | 激活 drive 后两轮速度命令被占用。直接激活 reserve 被严格切换拒绝，资源保持原状态 |
| 驱动与反馈 | 直行和转弯输入分别对应 2/2 和 1.1/2.9 rad/s。比较模拟轮反馈、原始里程计与局部 EKF |
| 命令过期 | 停发后分别检查轮反馈和原始里程计，记录本机观测时延。带一秒旧时戳的非零指令另作拒收反例 |
| 切换与 TF | 显式零速后切换到 reserve。两个观测话题分别出现同名的 odom → base_footprint，作为错误接线反例。它们在实验中保持隔离 |

正常阶段的 RSP 发布车体内部几何关系，EKF 发布局部里程计边。drive 保留原始 Odometry 并关闭相同 TF 边。EKF 只接收原始里程计中的前向速度和偏航速度，停更后的估计输出来自预测。

此处的半径、方差和超时是教学配置。观测结果只适用于已记录的安装版本、消息和软件模型。FIFO 调度、实时性、URDF 限位、控制器链、地图定位、实际打滑与物理制动需各自验收。
