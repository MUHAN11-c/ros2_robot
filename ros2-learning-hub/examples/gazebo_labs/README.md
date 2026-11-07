# Gazebo Harmonic 传感器与 ROS 桥接实验

一个固定台架与一块红板组成完整 SDF 世界。相机、GPU 激光和点云都来自实际运行的 Gazebo 服务端。ROS 端用世界控制服务切换暂停状态，再核对数据、QoS、内参和采集时戳。SDF 没有引用远程模型。

## 运行

需已有 Jazzy、Harmonic、ros_gz_bridge、cv_bridge 与 OpenCV，系统需能创建 Ogre2 的 EGL 渲染上下文。从教材目录运行。

```bash
# 加载已有的 ROS 与 Gazebo vendor 包。gz sim --version 核对模拟器的实际版本。
source /opt/ros/jazzy/setup.bash
gz sim --version
# 输入是同目录的 sensors.sdf 和 bridge.yaml。227 是隔离本机 DDS 域。
# 输出为脚本打印的新 /tmp 报告目录，含 RGB 帧、mono8 边缘与进程日志。
python3 examples/gazebo_labs/validate_sensors.py --domain-id 227
```

从原创示例 ZIP 解压后，可在 `atlas_examples/` 目录运行 `python3 gazebo_labs/validate_sensors.py`。如果 Ogre2 未能选择可用的 EGL vendor，`--egl-vendor-json` 只给本次 Gazebo 子进程指定本机已有的 vendor JSON。记录中的 NVIDIA 配置文件是 `/usr/share/glvnd/egl_vendor.d/10_nvidia.json`。其他设备的路径和支持情况以本机为准。[Gazebo Harmonic 渲染排查](https://gazebosim.org/docs/harmonic/troubleshooting/)

## 验收顺序

| 阶段 | 读哪项证据 |
| --- | --- |
| 发现和方向 | 世界专属 Gazebo 时钟转到 ROS /clock。五条数据映射只有桥的 ROS 发布端。控制请求从 ROS 到世界，并有 Gazebo 回执 |
| 时钟 | 初始 ROS 时间为零。运行、暂停、恢复分开检查，暂停窗口的超时使用单调时钟 |
| 相机与边缘 | 同戳配对 RGB Image、CameraInfo 和 mono8 边缘。核对 96×64 像素、行字节数、焦距像素值与光学 frame |
| 激光和点云 | 41 束，正前方约 2.20 m。对同戳 PointCloud2 用字段偏移和行步长读出中心点 |
| 反例 | BEST_EFFORT 扫描发布端能被发现，同时给匹配订阅与不匹配的 RELIABLE 订阅分别计数 |

台架静止、两个传感器共原点，测试变换为光学 Z 前与激光 X 前都转成台架 +X。报告保留实测图像，红通道阈值 40/120 是针对这个场景的处理。该实验范围为无窗口软件仿真与消息合同，运动畸变、SLAM、导航控制和实物需各自验证。
