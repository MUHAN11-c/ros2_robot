# 示例验证记录

日期：2026-11-07（本轮重新构建并运行）。环境：Ubuntu 24.04、ROS 2 Jazzy、Python 3.12、系统 C++ 编译器。只使用本机教学节点，没有连接或控制真实机器人。

已完成：

1. `atlas_cpp` 与 `atlas_py` 经 colcon 构建并安装，构建日志无编译错误。
2. C++ 发布 / Python 订阅，接收 `ATLAS_MESSAGE`。
3. Python 发布 / C++ 订阅，接收 `ATLAS_MESSAGE`。
4. C++ 服务端 / Python 客户端，返回 `SUM=12`。
5. Python 服务端 / C++ 客户端，返回 `SUM=12`。
6. Python、XML、YAML launch 均经 Jazzy 解析器加载，各产生两个节点动作。此项验证解析和结构，未声称三套 launch 全部进行了长时间运行。
7. 四个基础标准库实验、看门狗边界及16个数学/应用实验通过，范围见网站工程的 `VALIDATION.md`。

集成测试使用 `ROS_DOMAIN_ID=197`、`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`，在测试结束时关闭其创建的进程。复现时在网站工程根目录执行：

```bash
source /opt/ros/jazzy/setup.bash
colcon --log-base /tmp/ros2-atlas-build/log build \
  --base-paths examples/src --build-base /tmp/ros2-atlas-build/build \
  --install-base /tmp/ros2-atlas-build/install --merge-install --symlink-install
source /tmp/ros2-atlas-build/install/setup.bash
ATLAS_INSTALL_PREFIX=/tmp/ros2-atlas-build/install /usr/bin/python3 tests/test_examples.py
```

这组结果只覆盖随包通信工程。正文中其他生态命令、硬件配置、网络配置、仿真、学习框架与模型不因此视为在本机全部运行过；各章另有适用环境和验证说明。

新增导航客户端的12类假服务端协议验证另见 `navigation/README.md`，不纳入此通信5项计数。

`nav2_labs/` 的独立台架实际运行 Jazzy MapServer、AMCL、PlannerServer 与 Harmonic 固定激光。先验地图逐格核对，路径对照覆盖障碍层切换和五类规划错误。复现及边界见 [固定激光台架](nav2_labs/README.md)。完整导航行为树、控制和机器人运动需要另行验证。

`slam_labs/` 另行实测运动位置的仿真激光、SLAM Toolbox 建图、栅格重载、位姿图恢复、续建及定位缓冲。原始扫描、地图与图文件按相应报告绑定，见 [SLAM 复现说明](slam_labs/README.md)。

## 真实 Nav2 导航执行

本机 Jazzy Nav2 1.3.13、Harmonic 8.15.0 与 ros_gz_bridge 1.0.24 在隔离域 223 实测。MapServer 重载前一轮地图并核 13,426 个格。真实默认行为树完成到达、途中取消、越界 204、无效控制器 101 及切回有效控制器后恢复到达。两级速度置零、世界采样的停稳与轮速分别记录。复跑源码包与报告指纹见教材验证记录。实际轮地接触由仿真引擎计算，真实硬件另有验收范围。
