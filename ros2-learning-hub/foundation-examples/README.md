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

2026-11-07 已在本机重新构建10包，并完成15项隔离域集成检查：双向话题/服务，C++与Python Count成功及取消，参数有限值/类型/启动边界、逐项与原子提交差别，以及三种launch解析。26个示例子进程均已清理，没有连接设备。当前记录见 `../validation-evidence/foundation-current-validation.json`；旧日志保留在 `../validation-evidence/foundation/`。

源代码、接口、参数和launch已补充中文注释。完整文件依赖匹配的Jazzy环境；launch解析通过不表示三套文件都做过长时间运行。复现测试从 `ros2-learning-hub` 执行：

```bash
# 安装位置可以自行指定，以下与上述默认工作空间构建一致。
source /opt/ros/jazzy/setup.bash
source foundation-examples/install/setup.bash
FOUNDATION_INSTALL_PREFIX="$PWD/foundation-examples/install" \
  /usr/bin/python3 tests/test_foundation_examples.py
```

独立下载本工作空间时，可按教材完成相同手工实验；自动测试脚本与当前记录保存在完整教材源码工作区。验证范围和前两轮测试夹具/权限问题均在JSON记录中保留。
