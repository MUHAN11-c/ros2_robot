# ROS 2 学习图谱 · 完整通信工程

目标环境：Ubuntu 24.04 / ROS 2 Jazzy。包含 `atlas_cpp` 与 `atlas_py`，各有一个发布者、订阅者、加法服务端与异步客户端，以及等价的 Python / XML / YAML launch 文件。所有消息都是教学字符串；没有设备或电机控制接口。

## 构建

在独立目录解压 `atlas_examples.zip`，进入其中的 `atlas_examples/`：

```bash
source /opt/ros/jazzy/setup.bash
# 尚未安装这些依赖时：
sudo apt install python3-colcon-common-extensions ros-jazzy-rclcpp ros-jazzy-rclpy \
  ros-jazzy-std-msgs ros-jazzy-launch-ros ros-jazzy-launch-xml ros-jazzy-launch-yaml
sudo apt install ros-jazzy-example-interfaces
colcon build --symlink-install
source install/setup.bash
```

## 实验一：C++ 发布，Python 订阅

每个终端都先加载 Jazzy 和刚构建的 `install/setup.bash`。为了不与其他练习混淆，可在每个终端设置同一个独立域与本机发现范围：

```bash
export ROS_DOMAIN_ID=197
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
```

终端 A：

```bash
ros2 run atlas_cpp talker --ros-args -r __ns:=/atlas
```

终端 B：

```bash
ros2 run atlas_py listener --ros-args -r __ns:=/atlas
```

每 250ms 发布一条 `ATLAS_MESSAGE cpp N`，订阅者显示 `RECEIVED ATLAS_MESSAGE ...`。两端 Ctrl+C 退出。Domain ID 不是安全权限控制。

## 实验二：交换语言

把 A 改为 `ros2 run atlas_py talker --ros-args -r __ns:=/atlas`，B 改为 `ros2 run atlas_cpp listener --ros-args -r __ns:=/atlas`。观察消息后检查 `ros2 topic info /atlas/chatter --verbose`。所有发布/订阅对象都保持为节点成员，避免生命周期结束。

## 实验三：三种启动文件

每次只启动其中一种；Ctrl+C 退出再换下一种：

```bash
ros2 launch atlas_cpp demo.launch.py
ros2 launch atlas_cpp demo.launch.xml
ros2 launch atlas_cpp demo.launch.yaml
```

三者都启动 `/atlas/talker`（C++）和 `/atlas/listener`（Python），使用 `/atlas/chatter`。启动文件的语言不限制节点实现语言。

## 实验四：跨语言服务与异步响应

沿用两个终端的相同 Domain ID 与环境。终端 A：

```bash
ros2 run atlas_cpp add_server --ros-args -r __ns:=/atlas
```

终端 B：

```bash
ros2 run atlas_py add_client --ros-args -r __ns:=/atlas
```

客户端请求 7+5，输出 `SUM=12` 后退出。服务端继续等待请求。退出服务端，再把它换成 `atlas_py add_server`、客户端换成 `atlas_cpp add_client`，验证相同类型和接口可跨语言使用。每次只运行一个同名服务端。

客户端先等待服务发现，随后发送异步请求并调度执行器等待 Future，两阶段分别设置 5 秒超时。这里的等待在主程序中，不位于互斥回调组的回调内部。关闭服务端再运行客户端，应在超时后返回错误，而非永远等待。请求使用小整数；生产接口还需定义允许范围和失败响应。

## 练习

1. 改变发布周期，分别说明 timer 周期和 QoS 队列深度的作用。
2. 只改变一端命名空间，预测结果再检查端点。
3. 让发布者用 best effort、订阅者用 reliable，解释为何可发现但收不到。
4. 把 CLI 的命名空间配置移入三种 launch，验证完整话题名相同。

本工程为原创教学代码，参考 ROS 官方 Jazzy examples 的客户端库用法，使用 Apache-2.0 许可。构建和通信验证状态见随包 `VALIDATION.md`；网站其他示例片段不因此视为已执行。

## 四个无需 ROS 环境的离线实验

`offline_labs/` 下的程序只需 Python 3 标准库。分别对应教材的强化学习、语言模型任务规划、模仿学习与数据流程章节：

```bash
python3 offline_labs/rl_gain_search.py
python3 offline_labs/plan_contract.py
python3 offline_labs/policy_gate.py
python3 offline_labs/dataset_manifest.py /path/to/your/data
```

最后一个命令只读指定目录并输出清单；保存清单时请放在输入目录之外。详细原理、预期输出与练习答案已包含在离线教材中。
