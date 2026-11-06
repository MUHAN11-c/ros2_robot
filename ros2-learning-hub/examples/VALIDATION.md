# 示例验证记录

日期：2026-11-06。环境：Ubuntu 24.04、ROS 2 Jazzy、Python 3.12、系统 C++ 编译器。只使用本机教学节点，没有连接或控制真实机器人。

已完成：

1. `atlas_cpp` 与 `atlas_py` 经 colcon 构建并安装，构建日志无编译错误。
2. C++ 发布 / Python 订阅，接收 `ATLAS_MESSAGE`。
3. Python 发布 / C++ 订阅，接收 `ATLAS_MESSAGE`。
4. C++ 服务端 / Python 客户端，返回 `SUM=12`。
5. Python 服务端 / C++ 客户端，返回 `SUM=12`。
6. Python、XML、YAML launch 均经 Jazzy 解析器加载，各产生两个节点动作。此项验证解析和结构，未声称三套 launch 全部进行了长时间运行。
7. 四个标准库离线实验完成正常与故障输入检查，结果记录在网站项目的 `VALIDATION.md`。

集成测试使用 `ROS_DOMAIN_ID=197`、`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`，在测试结束时关闭其创建的进程。复现时在网站工程根目录执行：

```bash
source /opt/ros/jazzy/setup.bash
colcon --log-base /tmp/ros2-atlas-build/log build \
  --base-paths examples/src --build-base /tmp/ros2-atlas-build/build \
  --install-base /tmp/ros2-atlas-build/install --merge-install --symlink-install
source /tmp/ros2-atlas-build/install/setup.bash
python3 tests/test_examples.py
```

这组结果只覆盖随包通信工程。正文中其他生态命令、硬件配置、网络配置、仿真、学习框架与模型不因此视为在本机全部运行过；各章另有适用环境和验证说明。
