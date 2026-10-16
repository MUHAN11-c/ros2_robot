# 第19章 Mycar 自定义接口与运动控制

> 从本章进入 **Mycar 智能车实战**：为小车定义运动控制接口，分别以服务与动作两种方式实现「提交控制指令 → 执行 → 响应」。
>
> 本章对应代码：`code/ws03_exercise/src/my_exer_interfaces`、`my_exer01_topic_pub`、`my_exer02_topic_sub`、`my_exer03_service_server`、`my_exer04_service_client`、`my_exer05_action_server`、`my_exer06_action_client`、`py_exer01_topic_pub`。

## 19.1 自定义接口

`my_exer_interfaces` 包中定义两组接口：

**运动控制服务 `srv/Cru.srv`**（客户端提交速度与时长，服务端执行后响应）：

```text
float64 linear_x
float64 angular_z
float64 duration
---
bool success
string message
```

**导航动作 `action/Nav.action`**（目标点 + 连续反馈剩余距离 + 最终结果）：

```text
geometry_msgs/Point goal
---
bool reached
float64 distance
---
float64 remaining
```

> 注意：接口文件名首字母必须大写（`Cru.srv` 而非 `cru.srv`），否则 rosidl 生成阶段报 `InvalidResourceName`。
>
> 兼容提示：Cru.srv / Nav.action 的**字段为按课程需求重建**（视频未展示字段细节），结构与课程演示行为对齐。

## 19.2 话题练习：速度发布与订阅

`my_exer01_topic_pub`（C++）与 `py_exer01_topic_pub`（Python）：参数 `linear_x`/`angular_z`，10Hz 发布 `/cmd_vel`；`my_exer02_topic_sub` 订阅并打印。

实测（C++ 发布，参数 linear_x:=0.4）：

```bash
ros2 topic echo /cmd_vel --once
```

```text
linear:
  x: 0.4
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.2
---
```

## 19.3 服务实现运动控制

### 19.3.1 实现要点

服务端 `cru_server.cpp`：解析请求中的线速度/角速度/时长，执行期间周期发布 `/cmd_vel`，执行完毕后响应 `success=true, message=运动执行完成`；客户端 `cru_client.cpp` 从命令行读取三个参数并提交。

### 19.3.2 运行效果（实测）

```bash
ros2 run my_exer03_service_server cru_server        # 终端1
ros2 run my_exer04_service_client cru_client 0.5 0.1 2   # 终端2
```

服务端：

```text
[INFO] [...]: 收到请求: linear=0.50 angular=0.10 duration=2.0
[INFO] [...]: 运动执行完成
```

客户端：

```text
[INFO] [...]: Cru 客户端创建!
[INFO] [...]: 成功: 运动执行完成
```

> **视频对照**：课程在**实车**上验证本服务——rviz（Fixed Frame odom）中 Odometry 红色箭头呈扇形展开（原地旋转即 angular_z 的运动效果）+ 底盘实拍。本机无实车，服务执行/响应链已实测一致，运动效果以视频为准。

## 19.4 动作实现导航控制

### 19.4.1 实现要点

服务端 `nav_server.cpp`：

- 接收目标点 `goal(x,y)`；
- 执行体（子线程）订阅 `/odom` 实时计算剩余距离 `remaining = sqrt((gx-ox)² + (gy-oy)²)`；
- 以 `Rate(1Hz)` 连续反馈，到达阈值内响应 `reached=true`；
- 执行期间将速度发布到 `/cmd_vel`。

客户端 `nav_client.cpp` 提交目标并注册三个回调。

> 兼容提示：Jazzy 的目标响应回调签名是 `void goal_response_callback(GoalHandleNav::SharedPtr)`；Humble 为 `std::shared_future<GoalHandleNav::SharedPtr>`。

### 19.4.2 运行效果（实测）

无实车时以虚拟里程计替代（10Hz 在原点发布 `/odom`）：

```bash
ros2 topic pub --rate 10 /odom nav_msgs/msg/Odometry "{...position: {x: 0.0, y: 0.0}}"
ros2 run my_exer05_action_server nav_server
ros2 action send_goal /nav my_exer_interfaces/action/Nav "{goal: {x: 3.0, y: 4.0}}" --feedback
```

```text
Sending goal:
     goal:
  x: 3.0
  y: 4.0

Goal accepted with ID: 58a952618ead43c5b7e2959b22a21e90

Feedback:
    remaining: 5.0
```

反馈值 5.0 正是目标 (3,4) 到原点的欧氏距离——剩余距离计算正确。实车运动时 remaining 随里程递减直至到达。

## 19.5 本章小结

- 服务适合「短时执行、一次反馈」，动作适合「长时执行、连续反馈」——同一辆小车的运动控制用两者实现后差异一目了然；
- 动作执行体必须运行在**子线程**，避免阻塞 executor；
- 剩余距离依赖 `/odom`，实车与仿真只需保证里程计话题一致。
