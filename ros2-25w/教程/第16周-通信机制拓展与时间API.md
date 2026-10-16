# 第16章 通信机制拓展与时间 API

> 本章包含两部分：ROS2 时间相关 API（Time/Duration/Rate 及运算）与**期中大作业**——在 turtlesim 上综合运用话题、服务、动作、参数四种机制。
>
> 本章对应代码：`code/ws01_plumbing/src/cpp01_time`、`code/ws02_middle/src/cpp02_homework`、`py02_homework`。

## 16.1 时间相关 API

### 16.1.1 案例以及案例分析

**需求**：演示 `rclcpp::Time`、`rclcpp::Duration`、`rclcpp::Rate` 的创建与运算（时刻加减时段、时段比较等）。

### 16.1.2 C++ 实现要点

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
```

### 16.1.3 运行效果（实测）

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

## 16.2 期中大作业

### 16.2.1 案例以及案例分析

**需求**：综合运用四种通信机制控制乌龟：

| 子任务 | 机制 | 内容 |
| --- | --- | --- |
| 话题 | /t1/cmd_vel | 按参数 linear_x/angular_z 周期发布速度，控制乌龟运动 |
| 服务 | /spawn | 请求生成一只新乌龟 |
| 动作 | turtle_forward | 提交前进距离目标，连续反馈并驱动乌龟前进 |
| 参数 | /turtlesim/set_parameters + /clear | 修改乌龟背景色并刷新生效 |

### 16.2.2 C++ 实现要点

- `homework_topic_pub.cpp`：参数 `linear_x`/`angular_z` → 10Hz 发布 `Twist`；
- `homework_param_client.cpp`：远程调用 `/turtlesim/set_parameters` 修改 `background_r/g/b`，成功后再调用 `std_srvs/srv/Empty` 类型的 `/turtlesim/clear` 刷新背景。

> 兼容提示：`/turtlesim/clear` 是 **std_srvs/Empty** 类型（初学常见错误是误用 rcl_interfaces 的 Empty）。

### 16.2.3 运行效果（实测）

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

### 16.2.4 Python 实现

`py02_homework` 提供四个节点：`homework_topic_pub`、`homework_service_client`（生成乌龟）、`homework_action_server`（动作名 `turtle_forward`，复用 `Progress` 接口，周期发布 `/t1/cmd_vel` 直到前进量达标）、`homework_param_client`。

实测生成乌龟：

```text
[INFO] [...]: 期中大作业-服务通信客户端(python)
[INFO] [...]: 已生成乌龟:t1
```

实测动作目标（需同时 source 接口包所在工作空间 ws01）：

```bash
ros2 action send_goal /turtle_forward base_interfaces_demo/action/Progress "{num: 3}" --feedback
```

> **视频对照**：课程大作业实现于 `cpp07_exercise` 包（exer01_pub_sub / exer02_server / exer03_client / exer04_action_server / exer05_action_client / exer06_param，各配 `*_launch.py`）。其中 exer06 参数客户端的**背景色循环渐变**逻辑已按视频还原并升级进本仓库 `cpp02_homework`：计数在 [0,511] 循环（步进 5），[0,255] 区间 red 递增、[256,511] 递减，`set_parameters` + 5Hz Rate。实测采样 background_r：`130 → 200 → 235 → 145`（三角波，见 hw_cycle.log）。

## 16.3 通信机制拓展（分布式/工作空间覆盖/元功能包/重映射）

课程第 16 周第 1 课还包括四个工程化主题，本节逐一给出可运行的最小验证：

### 16.3.1 分布式

同一 DDS 域内的两台机器自动互相发现，无需任何中心节点。用 `ROS_DOMAIN_ID` 隔离/互通：

```bash
# 两台机器（或两个终端）设置相同 Domain 即互通，不同即隔离
export ROS_DOMAIN_ID=42
ros2 topic list    # 只能看到同域的设备
```

### 16.3.2 工作空间覆盖

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

### 16.3.3 元功能包

元功能包（metapackage）本身没有源码，只通过 `exec_depend` 聚合一组包，实现「一键安装」。本仓库新增 `cobot_metapackage`（聚合课程通信篇的功能包），`colcon build` 即可验证依赖解析：

```bash
cd ws02_middle && colcon build --packages-select cobot_metapackage
ros2 pkg xml cobot_metapackage    # 查看聚合清单
ros2 pkg executables cpp01_topic  # 被聚合包可直接使用
```

### 16.3.4 节点/话题重名（重映射）

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

分布式（16.3.1）实测：同域 42 的 `ros2 topic list` 可见 chatter（1 个）；默认域 0 不可见（0 个）——DDS 域隔离生效。

## 16.4 本章小结

- Time/Duration/Rate 是周期任务与超时控制的基础，时刻与时段的运算法则要区分；
- 期中大作业把四种通信机制落在同一只乌龟上，是通信篇的验收案例；
- 远程修改 turtlesim 参数后必须调用 `/clear` 才会刷新显示。
