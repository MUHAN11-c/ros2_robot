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

## 16.3 本章小结

- Time/Duration/Rate 是周期任务与超时控制的基础，时刻与时段的运算法则要区分；
- 期中大作业把四种通信机制落在同一只乌龟上，是通信篇的验收案例；
- 远程修改 turtlesim 参数后必须调用 `/clear` 才会刷新显示。
