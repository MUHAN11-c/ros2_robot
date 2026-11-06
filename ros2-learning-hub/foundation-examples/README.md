# 基础章节 ROS 2 示例工作空间

这些源码于 2026-11-06 从本机临时验证工作区保存到项目，避免换机丢失。`src/` 包含 10 个教学包：启动、话题、接口、服务、Action、参数以及三种 launch。`lessons/` 保留对应 Python 独立示例。

## 重建

```bash
# 在 Ubuntu 24.04、已安装 ROS 2 Jazzy 的终端执行。
source /opt/ros/jazzy/setup.bash
cd foundation-examples

# 如果依赖尚未安装，先在已初始化 rosdep 的环境中安装。
rosdep install --from-paths src --ignore-src -r -y

# 构建产物生成在当前工作空间，新电脑不要复用旧电脑的 install。
colcon build --symlink-install
source install/setup.bash

# 分别在两个已 source 的终端运行，观察跨语言通信。
ros2 run learning_topic_cpp talker
# 第二个终端：ros2 run learning_topic_py listener
```

其余包按教材中接口、服务、Action、参数与 launch 章节的文件路径和命令阅读。某些 Python 示例在 `lessons/`，应在本工作空间构建并 source 后用 `python3` 运行。

此前已报告 10 包构建成功、跨语言服务、C++/Python Action 成功及取消、三种 launch 解析通过。残留构建/运行日志已保存在 `../validation-evidence/foundation/`；这里没有为迁移再次运行全部 ROS 测试。部分代码的详细中文注释仍待补齐，这是继续任务的一部分。
