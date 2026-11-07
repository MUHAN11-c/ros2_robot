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
# 本节只构建src下的通信两包；附加动作/组件实验在各自目录单独构建。
colcon build --base-paths src --symlink-install
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

## 看门狗、数学与机器人应用实验

`offline_labs/watchdog_model.py` 是第五个基础离线模型，检查速度有限性、时间戳、过期与限幅；返回零不证明实际电机已停车。

```bash
python3 offline_labs/watchdog_model.py
# 以下每个入口运行八个相互独立的标准库实验。
python3 theory_labs/math_labs.py
python3 theory_labs/applied_labs.py
```

数学实验包括线性代数、刚体、概率、估计、优化、运动学、动力学、控制；应用包括工程预算、位姿图、搜索、LQR、足式、无人机坐标、导航合同和机械臂轨迹。输入单位、前提、预期数值与边界见源码和 `theory_labs/` 内两个核查说明。

`navigation/bounded_navigation.py` 是需要 Jazzy、rclpy 和 nav2_msgs 的完整单目标客户端。每个协议阶段使用单调软期限。准备、CLI、终态语义和 12 类隔离假服务端实验见 `navigation/README.md`。真实规划分段由下方台架覆盖，完整导航和实机另行验收。

`nav2_labs/` 用 Gazebo 的固定激光接入真实 MapServer、AMCL 和 NavFn。输入配置和运行脚本见 [固定激光台架](nav2_labs/README.md)。检查占据图、晚加入 QoS、定位初值、实时标记、同目标重规划和故障码。台架没有新增 ROS 包，首次通信构建的范围仍是 `src`。

`slam_labs/` 采集 Gazebo 在不同位姿的真实激光，以隔离回放钟和已知里程计偏差运行 SLAM Toolbox。实验保存占据栅格与位姿图，在新进程分别恢复，并核对短期定位缓冲对栅格的影响。参见 [运动扫描与位姿图实验](slam_labs/README.md)。

`runtime_labs/` 保存QoS、时钟、tf2、异步轮询，以及慢消费者、执行器/Future、参数三阶段和服务迟到响应实验。它们使用真实Jazzy API与合成数据，输入、单位、报告路径、清理及未覆盖分支见 `runtime_labs/README.md`；不能用这些软件实验推断硬件行为。

`action_labs/` 是独立Count故障扩展包及原/扩展服务端验收，复用另行构建的基础Count接口；`component_labs/` 是独立组件包与三容器对照。两者按各自README构建到专属安装前缀。上面的通信命令限定src，防止把需要额外接口的附加实验一起扫描进首次通信构建。

`lifecycle_labs/` 提供真实生命周期API与软件假资源；`testing_labs/` 提供完整gtest/pytest/launch_testing注册包和受控失败变体，分别按README构建。`testing_policy/` 保留旧四测试的基线与修订整数纳秒策略，区分测试通过和合同覆盖。`deployment_labs/` 只读审计显式安装前缀，并另测宿主直接exec信号；复制安装副本和Docker未运行。实验新报告另存/tmp，避免覆盖教材绑定证据。

`bag_labs/` 用标准合成消息完成真实CLI录制、关闭读回与暂停就绪后的筛选回放；另有不启动DDS的SQLite/MCAP字段探针。它不是新增ROS包，不改变首次构建的两包范围。按目录README准备rosbag2及两个存储插件，运行结果写独立/tmp；真实采集、GUI、性能、压缩/恢复及父中断注入未覆盖。

`model_labs/` 提供一个完整learning_description资源包、Xacro/URDF/launch、数值自检与无GUI TF driver。普通复制安装后异目录启动，默认/覆盖尺寸、固定边晚加入、位置状态/非法长度/合法velocity-only及光学单位点分别检查。目录现在共7个ROS包，首次构建仍仅扫描src两包；新增包按自身README准备依赖。没有RViz、动力学、真实相机或硬件验收。

只下载`atlas_examples.zip`时，解压后进入`atlas_examples/`，实验路径从该工程根目录计算。例如模型完整验收直接用`python3 model_labs/validate_model.py`；其README里的`python3 examples/model_labs/...`写法对应完整教材工作区，从独立工程运行时去掉开头`examples/`。模型driver用自身文件位置查找描述包，不要求下载目录改名为examples。

## Nav2 行为树与差速车闭环

`nav2_execution/` 读取前一轮 SLAM 的 PGM/YAML，在同一房间运行 Gazebo 差速车、NavFn、RPP、闭环速度平滑与安装版默认行为树。它保存到达、途中取消、两个失败分支和恢复有效控制器后的实际动作及世界位姿。地图输入来自验证记录，目录关系和复现步骤见 [台架说明](nav2_execution/README.md)。
