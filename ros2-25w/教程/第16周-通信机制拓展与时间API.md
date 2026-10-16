# 第16章 通信机制拓展与时间 API

> 所属阶段：阶段5 ROS2 核心架构解析 ｜ 视频 63 个 ｜ 时长约 10h17m ｜ 难度：进阶
>
> 本章包含两部分：ROS2 时间相关 API（Time/Duration/Rate 及运算）与**期中大作业**——在 turtlesim 上综合运用话题、服务、动作、参数四种机制；随后给出分布式、工作空间覆盖、元功能包、节点/话题重映射四个工程化主题的可运行验证。
>
> 本章对应代码：`code/ws01_plumbing/src/cpp01_time`、`code/ws02_middle/src/cpp02_homework`、`py02_homework`、`code/examples/overlay_demo/cpp00_hello_world`、`cobot_metapackage`。

## 16.1 概览与课时结构

本周把第15章的四种通信放进**真实工程语境**：多机分布式（域 ID 隔离）、工作空间覆盖与元功能包、节点/话题重名与命名空间治理——这些是"demo 能跑、上机器人就翻车"的典型坑。随后补齐时间相关 API（Rate / Time / Duration / Timer / 时钟与仿真时间），这是控制周期、超时判断、bag 回放与仿真的基础。再用一周末的篇幅系统过一遍 `ros2` 命令行与 rqt 工具箱，最后以**期中大作业**（话题/服务/动作/参数四通信综合实现）完成本阶段中检。

| 课 | 小节 | 时长 | 一句话导览 |
|---|---|---|---|
| 第1课 ROS2 通信机制扩展 | 20 节 | 2h50m | 分布式/域 ID、工作空间覆盖、元功能包、节点重名、话题重名与命名规则 |
| 第2课 ROS2 时间相关 API 与通信机制工具 | 14 节 | 2h17m | Rate/Time/Duration/运算/Timer/仿真时间 + ros2 CLI 全家桶 + rqt |
| 第3课 作业：话题、服务、动作通信及参数服务实现 | 29 节 | 5h08m | 期中大作业：四通信综合实现与 BUG 复盘 |

**学习目标**：

1. 理解 DDS 域隔离机制，会用 `ROS_DOMAIN_ID` 组织/隔离多机通信；
2. 掌握工作空间叠加（overlay/underlay）规则，能独立排查"改码不生效"；
3. 会用重映射、命名空间与编码参数化三层方案解决节点/话题重名；
4. 掌握 Rate/Time/Duration 的创建、运算法则与时钟语义，理解仿真时间 `use_sim_time`；
5. 独立完成期中大作业：一只乌龟上的四通信综合系统，并整理个人错题本。

## 16.2 知识点梳理

### 16.2.1 第1课 ROS2 通信机制扩展

**A. 分布式概念与应用**

- **场景、概念与作用**：机器人系统常由多台计算单元组成（工控机跑决策、Jetson 跑视觉、STM32 跑电机），ROS2 **天然支持跨机通信**：同一 DDS 域（Domain）内的节点通过网络自动发现彼此，话题/服务/动作可直接跨机使用，无需改代码。作用是把计算负载分布到多机，也支持"机器人 ↔ 工控台"远程调试。
- **实现**：两端安装同一 ROS2 发行版、处于同一网段（或可路由网络）、设置**相同的 `ROS_DOMAIN_ID`**；防火墙放行 DDS 端口（默认 UDP 7400-7500 与 SPDS 单播 7412/7413 等，视 DDS 实现）；用 `ros2 node list` 互见即成功。也可用 `ROS_LOCALHOST_ONLY=1` 限制仅本机。
- **域 ID 计算规则**：域 ID 取值 0~232（0~101 留给自动分配），同一域 ID 的节点才能互通。课程给出的推荐规则：**域 ID = 系统内编号（如机器人编号）+ 应用编号**，并按 `域ID = 用户ID % 101`（或网络 IP 尾段取模）之类规则生成，目的是"不同小组/不同机器人/不同用户自动隔离，避免同域串线"。多用户共用一台机器时尤其要用 `echo $UID % 101` 之类规则区分。
- **小结**：分布式 = 同域 ID + 网络可达 + 防火墙放行；域 ID 是隔离手段，不是加密手段。

**B. 工作空间覆盖与元功能包**

- **工作空间覆盖（Overlay/Underlay）**：ROS2 支持工作空间叠加——`source /opt/ros/humble/setup.bash` 是最底层（underlay），在其上 `source ~/ws/install/setup.bash` 是覆盖层（overlay）。同名功能包/可执行文件时**后 source 的覆盖先 source 的**。
- **演示**：两个工作空间都有 `talker` 可执行文件，先 source A 再 source B，`ros2 run pkg talker` 实际运行 B 的版本；`ros2 pkg prefix pkg` 显示当前生效包的安装路径，可用来确认"我到底在跑哪个"。
- **原因以及隐患**：colcon 生成的 `install/setup.bash` 会把自身路径前置到 `AMENT_PREFIX_PATH`/`PYTHONPATH`/`PATH`。隐患——改了 A 空间的代码却跑着 B 的旧版本（"改码不生效"）、第三方包遮蔽系统包、团队成员环境不一致。规避：单终端只 source 一层、用 `ros2 pkg prefix` 核对、CI 里清空环境重建、工作空间命名清晰。
- **元功能包（metapackage）**：场景——把一组相关功能包"打包成一个"，方便一键安装依赖（如 `ros-humble-navigation2` 聚合 Nav2 全家桶）。实现——建一个只有 `package.xml` 的空包：`<buildtool_depend>ament_cmake</buildtool_depend>`、`<exec_depend>` 逐个列出成员包、`<export><metapackage/></export>`（ament 下用 `ament_cmake` + 空 `CMakeLists.txt` 仅 `ament_package()`）。`ros2 pkg list` 里可见，安装它即拉齐全部成员。

**C. 节点重名解决方法**

- **问题、解决思路与解决方案**：同名节点在同一域内会相互覆盖（`ros2 node list` 显示一个，参数/服务归属混乱）。解决思路是**改名或加命名空间**。三层方案：(1) `ros2 run` 命令行重映射；(2) launch 文件统一配置；(3) 编码时参数化节点名。
- **ros2run 解决重名**：`ros2 run pkg node --ros-args -r __node:=new_name`，还可用 `-r __ns:=/robot1` 加命名空间。
- **launch 解决重名（简介 + 实现）**：launch 可一次起多个节点并对每个节点设 `name=` 与 `namespace=`；Python launch 里 `Node(package=..., executable=..., name='talker1', namespace='robot1')`；同一 launch 文件中重复 `Node` 声明即实现多实例。launch 的优势是**集中配置、可复现、可参数化**（配合 `LaunchConfiguration`）。
- **编码解决重名**：节点名从参数/环境变量读取——`rclcpp::NodeOptions().arguments({"--ros-args", "-r", "__node:=my_node"})` 或 Python `Node('my_node')` 处传变量；也可在构造节点时用 `allow_undeclared_parameters` + 启动参数动态指定；多机器人常结合 `PushRosNamespace`。

**D. 话题重名解决方法**

- **问题、解决思路与解决方案**：话题重名会导致数据"串台"（两个发布者混进同一话题）或订阅错源。解决靠**命名空间 + 名称解析规则 + 重映射（remap）**。
- **ros2run 实现**：`ros2 run pkg node --ros-args -r /topic:=/robot1/topic`；也可给节点加命名空间让其下所有相对话题自动前缀化。
- **launch 实现**：`Node(..., remappings=[('/topic', '/robot1/topic')])` 或 XML 的 `<remap from="/topic" to="/robot1/topic"/>`；配合 `PushRosNamespace('robot1')` 实现整组节点的话题隔离，是多机器人（如乌龟护航）的标准做法。
- **话题类型（名称解析规则）**：三种写法——**全局话题**（`/topic`，绝对名，不受命名空间影响）、**相对话题**（`topic`，拼上当前命名空间，最常用）、**私有话题**（`~/topic`，拼上节点私有命名空间 `/节点名/topic`，多用于节点内部状态）。举例：节点 `/robot1/cam` 写 `image` 得 `/robot1/image`，写 `~/image` 得 `/robot1/cam/image`。
- **话题设置**：话题名可用 launch 的 remap 在不改代码的前提下调整；`ros2 topic list` 与 `ros2 node info` 可核对最终解析结果；编码中建议把话题名做成**参数**（如 `~/topic_name`），部署时按机器人改参数而非改代码。

### 16.2.2 第2课 ROS2 时间相关 API 与通信机制工具

**A. ROS2 时间相关 API**

- **概述**：机器人算法离不开"时间"——控制周期、超时判断、时间戳对齐、轨迹插值。ROS2 提供 `Rate`（频率控制）、`Time`（时刻）、`Duration`（时长）三大类与 `Timer`（定时器）；关键设计是**时间源（Clock）可切换系统时钟或仿真时钟**（`use_sim_time`），保证仿真与真机代码一致。
- **Rate**：按目标频率循环（`rclcpp::Rate` / `rclpy.rate.Rate`），内部按"上次睡眠时刻 + 周期"补偿，比裸 `sleep` 稳。用法：`while (rclcpp::ok()) { ... rate.sleep(); }`。注意：回调耗时超过周期会掉频；`Rate` 默认用系统时钟，仿真下应改用基于 ROS 时钟的 `rclcpp::Rate(node->get_clock(), ...)` 或 `create_wall_timer` 的对应版本。
- **Time**：表示时刻，含**秒 + 纳秒**两段（`rclcpp::Time` / `rclpy.time.Time`），绑定具体 Clock（SYSTEM_TIME 或 ROS_TIME）。用法：`auto t0 = node->now();`、`msg.header.stamp = node->now();`。跨节点比较时间前必须确认同源（都用仿真时钟或都用系统时钟）。
- **Duration**：表示时长（`rclcpp::Duration` / `rclpy.duration.Duration`），可由 `Time - Time` 得到。用法：`auto dt = node->now() - t0;`、`dt.seconds()`。典型场景：计算回调耗时、判断超时（`if (dt > rclcpp::Duration::from_seconds(1.0))`）。
- **运算**：`Time + Duration = Time`、`Time - Duration = Time`、`Time - Time = Duration`、`Duration ± Duration = Duration`，支持比较运算（`<`、`==`）；Python 版方法为 `from_seconds`/`nanoseconds`/`to_msg`/`from_msg`。注意：不同 Clock 的 `Time` 相减会抛异常（"can't subtract times with different time sources"）。
- **Timer 与时钟补充**：`create_wall_timer`（墙钟，仿真不减速）与 `create_timer`（ROS 时钟，跟随仿真）要分清——控制类逻辑在仿真里应随仿真时间走。**仿真时间**：launch 里设 `use_sim_time=True` 参数后，节点 `now()` 返回 `/clock` 话题的时间，Gazebo/回放 bag 时算法行为与真实时间解耦。

**B. ROS2 通信机制工具**

- **场景、概念与作用**：节点跑起来后如何"看见"系统状态？ros2 CLI + rqt 是两大手段：CLI 用于快速查看/操作（脚本化、远程 SSH 友好），rqt 用于图形化持续观察。调试顺序：节点 → 接口 → 话题/服务/动作/参数。
- **ros2node**：`ros2 node list`（列出节点）、`ros2 node info /n`（查看订阅/发布/服务/参数）；配合 `--no-daemon` 可避免守护进程缓存旧信息。
- **ros2interface**：`ros2 interface list`、`ros2 interface show <pkg>/msg/X`（看字段）、`ros2 interface proto <pkg>/srv/Y`（生成调用模板，直接粘给 `ros2 service call` 用）。
- **ros2topic**：`list`、`info -v`（含 QoS 详情，排查 QoS 不匹配必备）、`echo`（订阅打印，`--field` 看单字段）、`hz`（测发布频率）、`bw`（带宽）、`pub`（手动发布，`-1` 发一次、`-r 10` 周期发）、`delay`、`find`。
- **ros2service**：`list`、`info`、`type`、`call <srv> <pkg>/srv/X "{a: 1, b: 2}"`（YAML 填请求，配合 `interface proto` 生成模板）。
- **ros2action**：`list`、`info`、`send_goal <action> <pkg>/act/X "{target: 1.0}" --feedback`（带反馈打印）。
- **ros2param**：`list`、`get/set`、`dump/load`（导出/加载 YAML，常配合 launch 参数文件）、`describe`（看描述与只读属性）。
- **rqt 工具箱**：rqt_graph（计算图）、rqt_topic（话题监控与手动发布）、rqt_service_caller、rqt_console/rqt_logger_level（日志）、rqt_reconfigure（参数动态调）、rqt_plot（波形）、rqt_image_view（图像）、rqt_bag（bag 图形化）。统一入口 `rqt` 可插拔加载。

### 16.2.3 第3课 期中大作业：话题、服务、动作通信及参数服务实现

- **作业概述**：综合运用四种通信机制实现一个多节点协作小系统——本仓库以 turtlesim 为载体落地：话题控制乌龟运动、服务生成乌龟、动作驱动乌龟前进、参数修改背景色。目标是把第15章的碎片实现整合成**多节点协作小系统**。

| 子任务 | 机制 | 内容 |
| --- | --- | --- |
| 话题 | /t1/cmd_vel | 按参数 linear_x/angular_z 周期发布速度，控制乌龟运动 |
| 服务 | /spawn | 请求生成一只新乌龟 |
| 动作 | turtle_forward | 提交前进距离目标，连续反馈并驱动乌龟前进 |
| 参数 | /turtlesim/set_parameters + /clear | 修改乌龟背景色并刷新生效 |

- **分项训练重点**：话题部分练框架搭建与"发布没数据"的排查全过程；服务部分练 `.srv` 设计与客户端时序（`wait_for_service`/`spin_until_future_complete`）；动作部分练三回调与执行循环（课程服务端讲解近 1 小时，是最难部分）；参数部分练参数声明、校验回调与业务逻辑联动（热生效）。
- **C++ 实现要点**（`cpp02_homework`）：
  - `homework_topic_pub.cpp`：参数 `linear_x`/`angular_z` → 10Hz 发布 `Twist`；
  - `homework_param_client.cpp`：远程调用 `/turtlesim/set_parameters` 修改 `background_r/g/b`，成功后再调用 `std_srvs/srv/Empty` 类型的 `/turtlesim/clear` 刷新背景。

> 兼容提示：`/turtlesim/clear` 是 **std_srvs/Empty** 类型（初学常见错误是误用 rcl_interfaces 的 Empty）。

- **Python 实现**（`py02_homework`）提供四个节点：`homework_topic_pub`、`homework_service_client`（生成乌龟）、`homework_action_server`（动作名 `turtle_forward`，复用 `Progress` 接口，周期发布 `/t1/cmd_vel` 直到前进量达标）、`homework_param_client`。实测输出见 16.5.2。
- **复盘**：作业暴露的典型问题——接口包依赖顺序、服务客户端阻塞、动作取消无效、参数未声明——都已在前文"重点与难点"覆盖，建议整理成个人错题本。

## 16.3 重点与难点

1. **域 ID 与分布式排错**：互不可见先查 `ROS_DOMAIN_ID` 是否一致、网络是否互通（`ping`）、防火墙/DDS 端口、`ROS_LOCALHOST_ONLY` 是否误设为 1。
2. **工作空间覆盖的"改码不生效"**：这是本周最隐蔽的坑。每次开终端 `echo $ROS_DISTRO`、`ros2 pkg prefix <pkg>` 确认生效路径；理解 `setup.bash` 是"叠加"而不是"替换"。
3. **话题名称解析三种规则**：`/x`（全局）、`x`（相对）、`~/x`（私有）决定 remap 与命名空间能否生效；多机器人务必用相对话题 + 命名空间，避免全局话题写死。
4. **Time/Duration 的时钟一致性**：系统时钟与 ROS（仿真）时钟混用会抛异常或得到负 dt；控制循环在仿真下用 ROS 时钟 Timer。
5. **大作业的整合**：单个通信会写不难，难的是**在一个节点里组合多种通信**（如"动作执行中改参数、用服务查询、用话题广播状态"），注意回调阻塞与线程安全。

## 16.4 代码与命令实战

### 16.4.1 实战 1：多机分布式与域 ID（场景：两台机器人/两台电脑互联）

```bash
# 两端都要执行：同一域 ID 才能互通（0~232；建议按用户/机器人编号取模生成）
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0          # 0 = 允许跨机；调试本机时设 1 隔离
ros2 multicast receive &             # 一端监听组播，验证 DDS 发现
ros2 multicast send                  # 另一端发送；能收到即网络/域配置正确
ros2 node list                       # 两端应能看到彼此的节点
```

### 16.4.2 实战 2：工作空间覆盖验证与隐患排查（场景："改了代码不生效"）

```bash
source /opt/ros/humble/setup.bash    # underlay
source ~/wsA/install/setup.bash      # overlay A
source ~/wsB/install/setup.bash      # overlay B（后 source，生效）
ros2 pkg prefix my_pkg               # 打印生效包的安装路径——一眼看出跑的是 A 还是 B
echo $AMENT_PREFIX_PATH              # 空间叠加顺序在这里体现
```

### 16.4.3 实战 3：节点/话题重名——ros2run 与 launch 双方案（场景：一台机器跑两个同款节点）

```bash
# 方案一：命令行重映射（临时）
ros2 run my_pkg talker --ros-args -r __node:=talker2 -r __ns:=/robot2 -r /topic:=/robot2/topic
```

```python
# 方案二：launch 统一配置（工程推荐）——talkers.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node, PushRosNamespace
from launch.actions import GroupAction


def generate_launch_description():
    def make_talker(ns, name):
        return GroupAction([
            PushRosNamespace(ns),                 # 组内节点统一加命名空间
            Node(package='my_pkg', executable='talker', name=name,
                 remappings=[('topic', 'topic')],  # 相对话题自动拼上命名空间
                 parameters=[{'rate': 2.0}]),
        ])
    return LaunchDescription([
        make_talker('robot1', 'talker'),
        make_talker('robot2', 'talker'),          # 名字相同也不冲突：命名空间隔离
    ])
```

### 16.4.4 实战 4：Time / Duration / Rate（C++ 要点 + Python 节点）

```cpp
// Time：now() 获取当前时刻；
rclcpp::Time t1 = this->now();
// Duration：两种构造方式；
rclcpp::Duration d1 = 3s;
rclcpp::Duration d2(2,0);
// 运算；
rclcpp::Time t2 = t1 + d1;      // 时刻 + 时段 = 时刻
rclcpp::Duration d3 = d1 - d2;  // 时段 - 时段 = 时段
bool flag = d1 > d2;            // 时段可比较
// Rate：固定周期休眠；
rclcpp::Rate rate(1.0);          // 1Hz
rate.sleep();
// 定时器区分：create_wall_timer（墙钟）vs create_timer(node->get_clock(), ...)（随仿真）
```

```python
# time_demo/time_demo/time_node.py —— Python 主力写法
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration


class TimeNode(Node):
    def __init__(self):
        super().__init__('time_node')
        self.t0 = self.now()                       # 时刻：绑定本节点时钟
        self.rate = self.create_rate(10.0)         # 10 Hz 频率控制器
        # 仿真下让时间跟随 /clock：launch 中 parameters=[{'use_sim_time': True}]

    def step(self):
        dt = self.now() - self.t0                  # Duration = Time - Time
        if dt > Duration(seconds=1.0):             # 超时判断
            self.get_logger().info(f'elapsed {dt.nanoseconds / 1e9:.2f}s')
            self.t0 = self.now()
        self.rate.sleep()                          # 频率稳定的关键
```

### 16.4.5 实战 5：ros2 CLI 调试全家桶（场景：接手陌生系统的 5 分钟摸底）

```bash
ros2 node list && ros2 node info /talker          # 节点连了什么
ros2 interface show std_msgs/msg/String           # 消息字段
ros2 interface proto example_interfaces/srv/AddTwoInts   # 生成 service call 模板
ros2 topic hz /topic -w 20                        # 测频率（滑窗 20 帧）
ros2 topic info /topic -v                         # 看 QoS（排查不匹配）
ros2 topic pub -1 /topic std_msgs/msg/String "{data: hi}"   # 手动注入一条
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 1, b: 2}"
ros2 action send_goal /navigate my_pkg/act/Navigate "{target_x: 1.0}" --feedback
ros2 param dump /time_node > params.yaml          # 导出参数，供 launch 复用
```

### 16.4.6 实战 6：仿真时间 use_sim_time（场景：bag 回放/Gazebo 仿真时算法随仿真时钟走）

```python
# launch 中为所有节点统一开仿真时间（launch 细节见第17章）
Node(package='my_pkg', executable='time_node',
     parameters=[{'use_sim_time': True}])
```

```bash
ros2 bag play my_bag --clock      # 回放时发布 /clock，供 use_sim_time 节点取用
ros2 param get /time_node use_sim_time   # 确认 True；此时 node.now() 跟随 bag 时间
```

## 16.5 运行效果（实测）

### 16.5.1 时间 API 演示（cpp01_time）

```bash
ros2 run cpp01_time demo01_time_api
```

```text
[INFO] [...]: 当前时刻:1792040770.29603
[INFO] [...]: t2:1.50
[INFO] [...]: d1 = 3.00 s, d2 = 2.00 s
[INFO] [...]: t1 + 3s = 1792040773.29603
[INFO] [...]: d1 - d2 = 1.00 s
[INFO] [...]: d1 > d2 ? true
[INFO] [...]: Rate 循环 0
```

> 兼容提示：`rclpy` 中对应 `self.get_clock().now()`、`Duration(seconds=3)`、`Rate(self, 1.0)`，语义一致。

### 16.5.2 期中大作业实测

先启动乌龟（`ros2 run turtlesim turtlesim_node`），再运行参数客户端：

```text
[INFO] [...]: 期中大作业-参数服务客户端(C++)
[INFO] [...]: 修改背景色:成功
[INFO] [...]: 修改背景色:成功
[INFO] [...]: 修改背景色:成功
```

窗口背景即时变为设定颜色；话题客户端可用 `ros2 topic echo /t1/cmd_vel` 验证：

```text
linear:
  x: 0.5
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.2
---
```

Python 版实测生成乌龟：

```text
[INFO] [...]: 期中大作业-服务通信客户端(python)
[INFO] [...]: 已生成乌龟:t1
```

实测动作目标（需同时 source 接口包所在工作空间 ws01）：

```bash
ros2 action send_goal /turtle_forward base_interfaces_demo/action/Progress "{num: 3}" --feedback
```

> **视频对照**：课程大作业实现于 `cpp07_exercise` 包（exer01_pub_sub / exer02_server / exer03_client / exer04_action_server / exer05_action_client / exer06_param，各配 `*_launch.py`）。其中 exer06 参数客户端的**背景色循环渐变**逻辑已按视频还原并升级进本仓库 `cpp02_homework`：计数在 [0,511] 循环（步进 5），[0,255] 区间 red 递增、[256,511] 递减，`set_parameters` + 5Hz Rate。实测采样 background_r：`130 → 200 → 235 → 145`（三角波，见 hw_cycle.log）。

### 16.5.3 分布式：域隔离实测（域 42 / 域 0）

```bash
# 域 42（与发布端同域）
export ROS_DOMAIN_ID=42
ros2 topic list    # 可见 chatter（1 个）
# 不设置（默认域 0）
ros2 topic list    # chatter 不可见（0 个）
```

分布式实测：同域 42 的 `ros2 topic list` 可见 chatter（1 个）；默认域 0 不可见（0 个）——DDS 域隔离生效。

### 16.5.4 工作空间覆盖实测（OVERLAY）

后 source 的工作空间**覆盖**先 source 的同名包——这是「不改上游包、只改自己扩展」的标准做法。本仓库提供了同名的覆盖演示包（`code/examples/overlay_demo/cpp00_hello_world`）：

```bash
# 1.先 source 底层工作空间（underlay）
source ws01_plumbing/install/setup.bash
# 2.再构建并 source 覆盖层（overlay）
cd /tmp/overlay_ws && colcon build && source install/setup.bash
# 3.运行同名包：执行的是覆盖层版本
ros2 run cpp00_hello_world demo01_hello_world
```

实测（本机 Jazzy）：

```text
[INFO] [...]: [hello_world_node_cpp]: Hello from OVERLAY workspace!（覆盖层版本）
```

### 16.5.5 元功能包实测（cobot_metapackage）

元功能包（metapackage）本身没有源码，只通过 `exec_depend` 聚合一组包，实现「一键安装」。本仓库新增 `cobot_metapackage`（聚合课程通信篇的功能包），`colcon build` 即可验证依赖解析：

```bash
cd ws02_middle && colcon build --packages-select cobot_metapackage
ros2 pkg xml cobot_metapackage    # 查看聚合清单
ros2 pkg executables cpp01_topic  # 被聚合包可直接使用
```

### 16.5.6 节点/话题重映射实测（remap.log）

不修改源码即可解决重名——启动时用 `--ros-args -r` 重映射：

```bash
# 节点重名：把 talker 重命名为 talker2
ros2 run cpp01_topic demo01_talker_str --ros-args -r __node:=talker2
# 话题重名：把 /chatter 重映射为 /chatter2
ros2 run cpp01_topic demo01_talker_str --ros-args -r /chatter:=/chatter2
```

实测（remap.log）：

```text
[INFO] [...]: [talker2]: 发布节点创建!
[INFO] [...]: [talker2]: 发布方发布的消息:hello world!0
--- ros2 node list ---
/force_web
/serial_force
/talker2                ← 重映射后的节点名
--- 话题重映射 ---
/chatter2               ← 重映射后的话题名
--- ros2 topic echo /chatter2 --once
data: hello world!7
---
```

## 16.6 与 ROS2 / 机器人开发的关联

1. **多机是机器人系统常态**：Jetson 视觉 + 工控机决策 + 单片机驱动的架构全靠同域 ID + 命名空间组织；课程后段的 ARM 平台部署就是分布式实践。
2. **命名空间是多机器人基础**：乌龟护航（第18章）、多车编队都用 `PushRosNamespace` + 相对话题隔离；写话题名时避免全局名是工程素养。
3. **时间 API 直通控制与仿真**：控制周期（Rate）、时间戳对齐（Time）、超时保护（Duration）是导航与滤波算法标配；`use_sim_time` 让同一套代码跑真机与仿真。
4. **调试工具决定开发效率**：真实项目 70% 时间在排查运行时问题，`ros2 topic info -v`、`ros2 node info`、rqt_graph/rqt_console 是定位问题的最快路径。
5. **期中大作业 = 阶段验收**：第19-20章 Mycar 项目会要求把感知、决策、控制多节点整合，正是大作业的放大版。

## 16.7 自测与练习

1. **概念题**：解释 `/cmd_vel`、`cmd_vel`、`~/cmd_vel` 三种写法在节点 `/robot1/base` 下的最终话题名。说明工作空间覆盖为什么会"改码不生效"，给出两种排查命令。
2. **动手任务**：写一个节点用 `Rate` 以 10 Hz 发布 `std_msgs/Float64`（值为 `now()` 的秒数），订阅端用 `Duration` 计算并打印每条消息的到达间隔。**验收标准**：`ros2 topic hz` 显示约 10 Hz；打印的间隔约 0.1s 且抖动小于 20ms。
3. **综合任务（期中自测）**：在两个命名空间 `robot1`、`robot2` 下各起一个同款 talker 节点，要求 `ros2 topic list` 中话题互不重叠、`ros2 node list` 节点名互不冲突。**验收标准**：不改源码，仅用 launch 配置实现。

> 参考答案要点：1) 分别得 `/cmd_vel`（全局原样）、`/robot1/cmd_vel`（相对拼命名空间）、`/robot1/base/cmd_vel`（私有拼节点名）；排查用 `ros2 pkg prefix` 与 `echo $AMENT_PREFIX_PATH`。2) 发布端 `create_rate`/`rclcpp::Rate`；注意 Python 的 `create_rate` 依赖节点时钟，仿真下挂 use_sim_time；用 `now() - last_time` 算间隔。3) 用 `GroupAction([PushRosNamespace('robot1'), Node(...)])` 两组，节点 `name` 相同、话题用相对名，即自动隔离。

## 16.8 常见问题（FAQ）

- **Q：两台机器 `ros2 node list` 互相看不到？** A：依次确认 `ROS_DOMAIN_ID` 相同、`ROS_LOCALHOST_ONLY=0`、`ping` 通、防火墙放行 DDS 端口（或临时 `sudo ufw disable` 验证）、两端 ROS2 版本兼容。
- **Q：`use_sim_time` 开了但节点时间不动？** A：确认有 `/clock` 话题在发布（`ros2 bag play --clock` 或仿真器），且参数确实设置成功（`ros2 param get`）；启动顺序上 `/clock` 需在节点运行期间持续发布。
- **Q：remap 了话题名但没生效？** A：检查话题名是全局还是相对——对全局话题（`/x`）remap 必须写全名；对相对话题，remap 的 `from` 应写解析前的名字。`ros2 node info` 看最终连接的话题名。
- **Q：`ros2 node list` 显示旧节点？** A：ros2 CLI 有守护进程缓存，用 `ros2 daemon stop && ros2 daemon start` 刷新，或命令加 `--no-daemon`。
- **Q：元功能包编译报错？** A：ament 的元包只需空 `CMakeLists.txt`（`cmake_minimum_required` + `find_package(ament_cmake)` + `ament_package()`）+ `package.xml` 里 `<export><metapackage/></export>` 与成员包的 `<exec_depend>`，不要写源码目标。

## 16.9 本章小结

- Time/Duration/Rate 是周期任务与超时控制的基础，时刻与时段的运算法则要区分；系统时钟与 ROS 时钟不能混用，仿真下统一挂 `use_sim_time`；
- 分布式 = 同域 ID + 网络可达 + 防火墙放行，`ROS_DOMAIN_ID` 域 42/域 0 的隔离实测已验证；
- 工作空间覆盖遵循"后 source 覆盖先 source"，`ros2 pkg prefix` 是排查"改码不生效"的第一命令；元功能包用 `exec_depend` 聚合成员包实现一键安装；
- 节点/话题重名用 `--ros-args -r` 重映射即可不改源码解决（talker2 / chatter2 实测通过）；
- 期中大作业把四种通信机制落在同一只乌龟上，是通信篇的验收案例；远程修改 turtlesim 参数后必须调用 `/clear` 才会刷新显示。
