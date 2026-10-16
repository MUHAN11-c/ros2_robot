# 第19章 Mycar 自定义接口与运动控制

> 从本章进入 **Mycar 智能车实战**：先认识整车与远程开发环境、跑通建图与导航，再为小车定义运动控制接口，依次用话题、服务、动作三种通信机制实现「提交控制指令 → 执行 → 响应/反馈」。
>
> 本章对应代码：`code/ws03_exercise/src/my_exer_interfaces`、`my_exer01_topic_pub`、`my_exer02_topic_sub`、`my_exer03_service_server`、`my_exer04_service_client`、`my_exer05_action_server`、`my_exer06_action_client`、`py_exer01_topic_pub`。

## 19.1 概览与课时结构

本章是 Mycar 实战的第一周，目标是**把这台车完整地「用起来」**：先通过远程开发把环境搭好，跑通建图与导航这些现成功能，再下沉到底盘、雷达、摄像头的驱动层，最后亲手实现车辆控制。在 25 周体系中，本章是「ROS2 知识 → 机器人产品」的第一次完整落地；学完能独立部署一台差速驱动小车的驱动与控制程序，并理解三种通信机制在真实运动控制中的选型差异。

| 课 | 小节 | 时长 | 一句话导览 |
|---|---|---|---|
| 第1课 Mycar概述与基本功能实现 | 3 节 16 个视频 | 1h45m | 认识 Mycar 硬件与功能，搭好远程开发环境，现场演示三种建图方案与单点/多点导航 |
| 第2课 Mycar开发环境与基础硬件实践 | 3 节 18 个视频 | 2h15m | 验证分布式环境，驱动 Arduino/STM32 底盘并显示里程计，接入雷达与摄像头，用 rqt/TF/stage_ros2 调试 |
| 第3课 Mycar话题通信与服务通信实践 | 2 节 26 个视频 | 3h59m | 话题发布/订阅控制速度与读取里程计（含动态调参），服务实现带里程计闭环的定点运动 |
| 第4课 Mycar动作通信实践 | 1 节 19 个视频 | 3h11m | 定义 Action 接口，实现带反馈、可取消的导航任务服务端与客户端，并做实车测试 |

> 全周视频 79 个，总时长约 11h12m（1h45m + 2h15m + 3h59m + 3h11m），难度入门→进阶。19.5 节的输出均为本机实测，「视频对照」「兼容提示」注记逐条保留。

## 19.2 知识点梳理

### 19.2.1 第1课 Mycar概述与基本功能实现

**核心概念**：Mycar 是一台差速驱动智能车，主控板跑 ROS2，PC 通过局域网远程开发；上层功能（建图、导航）全部通过 ROS2 话题/服务接口与底层驱动解耦。

**要点 1：硬件介绍与功能说明**——整车四层结构：

| 层级 | 组成 | 对应 ROS2 接口 |
|---|---|---|
| 底盘执行层 | Arduino / STM32 + 电机编码器 | 订阅 `cmd_vel`，发布 `odom`（里程计） |
| 传感层 | 激光雷达、摄像头 | 发布 `scan`、`image_raw` / `camera_info` |
| 计算层 | 车载主控板（Linux + ROS2） | 运行驱动节点、TF、SLAM/导航 |
| 交互层 | PC（VSCode Remote） | rviz2、rqt、调试命令、算法开发 |

**要点 2：远程开发四步走**：① 获取开发板 IP（`ifconfig` / 路由器后台 / 串口终端查看；建议路由器绑定静态 IP 或配置 mDNS 主机名）；② SSH 远程登录 `ssh user@<board-ip>`（首次连接确认指纹，`ssh-keygen` + `ssh-copy-id` 免密）；③ VSCode Remote - SSH 插件连接后打开工作空间目录并安装 ROS 扩展（语法、CMake Tools、Python）；④ `rosdep install` 装依赖、`colcon build` 编译、把 `source install/setup.bash` 写入 `~/.bashrc`，最后用一键启动脚本 bringup 整车。

**要点 3：三种建图方案对比**。建图（SLAM）是把雷达 `scan` + 里程计 `odom` 融合成地图 `map` 的过程：

| 方案 | 特点 | 适用场景 |
|---|---|---|
| gmapping | 粒子滤波，配置简单，2D 激光经典方案 | 小场景、快速出图 |
| cartographer | 图优化，精度高，支持子图/回环 | 大场景、追求地图质量 |
| slamtoolbox | 支持终身建图与序列化地图，在线/离线两种模式 | 需要地图保存与继续建图 |

三者输出一致（`/map` 话题 + map→odom 变换），可以按需求替换而不动导航部分。

**要点 4：导航与分布式环境**。导航 = 地图定位（AMCL）+ 全局/局部路径规划 + 控制器（输出 `cmd_vel`）。课程演示了**基本导航**（rviz2 设目标点）、**多点导航**（依次下发多个目标点，注意 `NavigateToPose` 的排队与取消）、**边建图边导航**（SLAM 与导航同时运行，无现成地图时使用）。分布式环境搭建即「算法在 PC、驱动在车」：两端同一网段、同一 ROS_DOMAIN_ID，PC 端 `source` 同版本 ROS2 即可互相发现。

> **注意：** 建图时底盘里程计质量直接决定地图是否重影。如果地图出现拖影/错层，先检查 `odom` 话题的频率与 TF 是否连续，再调 SLAM 参数。

### 19.2.2 第2课 Mycar开发环境与基础硬件实践

**核心概念**：把每个硬件抽象成「订阅指令话题 / 发布数据话题」的 ROS2 节点，是 Mycar 全部驱动的统一设计。

**要点 1：分布式环境搭建与验证**。两台机器分别运行 `ros2 topic list` / `ros2 node list`，互相能看到对方的节点即验证通过；再用 `ros2 topic pub` 跨机发布、`ros2 topic echo` 跨机订阅确认数据互通。不通时按顺序排查：网段 → 防火墙（UDP 7400+）→ ROS_DOMAIN_ID → `ROS_LOCALHOST_ONLY` 是否误设为 1。

**要点 2：底盘驱动（Arduino / STM32）**。驱动节点订阅 `/cmd_vel`（`geometry_msgs/msg/Twist`）→ 换算左右轮速 → 通过串口下发给单片机（PID 闭环由单片机完成）；读取编码器计数 → 换算实际线速度/角速度 → 积分出位姿 → 发布 `/odom`（`nav_msgs/msg/Odometry`）并广播 odom→base_footprint 变换。两种主控的差异只在固件与串口协议（波特率、帧格式），ROS2 侧节点结构完全一致——这正是「硬件节点抽象」的价值。

**要点 3：rviz2 显示里程计**。添加 Odometry 显示项并绑定 `/odom` 话题，推车/遥控小车观察箭头轨迹；同时添加 TF 显示确认 odom→base_footprint 存在。里程计跳变、方向反了、转不动多半是：轮径/轮距参数错、编码器方向反、`cmd_vel` 分量（linear.x / angular.z）用错。

**要点 4：远程启动底盘**。把驱动做成可远程启动的服务（如 `systemd` 服务、启动脚本 + SSH 命令），PC 侧一条命令拉起车上底盘驱动，避免每次接显示器调试。

**要点 5：激光雷达驱动**。安装官方 ROS2 驱动包（二进制 `apt` 或源码编译），发布 `/scan`（`sensor_msgs/msg/LaserScan`）；**雷达端口映射**：USB 转串口设备名 `/dev/ttyUSB0` 不稳定，用 `udev` 规则绑定固定名（如 `/dev/lidar`）；远程启动后用 `ros2 topic hz /scan` 验证帧率。

**要点 6：摄像头驱动**。两条安装路线：**二进制安装**（`apt install ros-<distro>-usb-cam`，快、够用）与**源码安装**（可改参数、支持自定义格式）；发布 `/image_raw` 与 `/camera_info`。集成时关注分辨率/帧率与编码格式（`sensor_msgs/Image` 未压缩、带宽大，多机传输常配合 `image_transport` 压缩）。

**要点 7：工具三件套**。**rqt 工具**：rqt_image_view 看图像、rqt_plot 看曲线、rqt_graph 看拓扑，是「不写代码就能调试」的利器；**TF 坐标系相对关系**：`ros2 run tf2_ros tf2_echo <parent> <child>` 查询两坐标系实时变换，理解树状结构与父子关系；**stage_ros2 模拟器**：用 2D 模拟环境替代实体车，练习遥控、建图、导航与传感器数据流，是无硬件时的主要练习场。

### 19.2.3 第3课 Mycar话题通信与服务通信实践

**核心概念**：话题适合**持续、单向、容忍丢帧**的数据流；服务适合**一次请求、一次结果**的可靠交互。Mycar 中速度指令与里程计用话题，定点运动控制用服务。

**要点 1：话题发布（速度控制）**。按「需求 → 案例分析 → 主逻辑 → 动态调参 → Python 实现」五步推进：主逻辑用定时器（rclpy `create_timer` / rclcpp `create_wall_timer`）按固定周期发布 `/cmd_vel`，保证控制平滑；**动态调参**把线速度/角速度做成 ROS2 参数，运行中用 `ros2 param set` 调整而不用重启节点。

**要点 2：话题订阅（里程计）**。订阅 `/odom` 解析 `pose.pose.position` 与 `twist.twist`，可计算行驶路程、判断是否到达目标；注意 QoS：传感器数据常用 `SensorDataQoS`（Best Effort），里程计默认 Reliable，两端 QoS 不匹配会导致**收不到消息**（`ros2 topic echo` 有数据但自己的节点没有）。动态调参同样适用于订阅端（如调整处理频率、目标阈值）。

**要点 3：服务通信（定点运动控制）**。完整链路：定义接口（`.srv`，需自建接口包并被 server/client 两个包依赖）→ 服务端实现 → 客户端连接 → 客户端发送请求 → 客户端处理响应。服务端内部逻辑是闭环：接收目标距离/速度 → 持续发布 `cmd_vel` → **订阅里程计**判断是否到达 → 到达后停止并填入响应（实际距离、是否成功）。这演示了「服务接口封装复杂控制流程」的典型模式。

> **注意：** 服务端在回调里长时间循环会阻塞 executor，导致无法响应其他请求。工程做法是把运动控制放到独立线程/定时器状态机里，回调只负责启动与状态查询。

### 19.2.4 第4课 Mycar动作通信实践

**核心概念**：动作（Action）= 服务的「长任务版」：目标（Goal）→ 反馈（Feedback）→ 结果（Result），支持取消（Cancel），适合导航这类**耗时且需要进度**的任务。

**要点 1：接口定义**。`.action` 文件三段式：目标（如目标点坐标/距离、速度）、结果（实际位移、是否成功）、反馈（实时进度百分比、剩余距离）；接口包需在 `CMakeLists.txt` 中用 `rosidl_generate_interfaces()` 生成，并被服务端/客户端包依赖。

**要点 2：服务端全流程**。代码框架（rclcpp `rclcpp_action::Server` / rclpy `ActionServer`）：接受目标回调（可拒绝非法目标）→ 执行回调（主逻辑）→ 周期发布 `cmd_vel` 并订阅里程计计算进度 → `publish_feedback` 上报 → 到位后填结果 → 响应取消请求（收到 Cancel 后减速停车、返回「已取消」）。

**要点 3：两类典型 BUG 与处理**。其一，**执行回调阻塞**：把控制循环塞进 execute 回调导致取消请求得不到响应，应改用定时器 + 状态机；其二，**里程计与控制不同步**：里程计回调与控制回调竞态、到达判断阈值抖动，需加互斥/用最新里程计快照并设置速度平滑与到位死区。

**要点 4：客户端全流程**。发送目标 → 等待服务端接受（不接受则退出）→ 处理反馈回调（打印进度）→ 处理结果回调（成功/失败/放弃）→ **取消任务**（如超时或用户中断时调用异步取消）。

**要点 5：实体机器人测试与 Python 实现**。在实车上测试时先用小速度、短距离；rclpy 实现用 `ActionClient` + `rclpy.spin` + 回调，代码量明显少于 C++，适合快速验证逻辑。

## 19.3 重点与难点

1. **三种通信机制的选型**：话题用于连续流（速度、里程计、激光）；服务用于快速问答（开关、单次查询）；动作用于可取消的长任务（导航、定点运动）。能说清「定点运动为什么用动作而不是服务」，本章就过关了一半。
2. **里程计闭环的实现**：服务/动作的「到位判断」都依赖 `/odom`，需要掌握坐标积分、距离阈值、速度平滑与控制频率的关系——这是后续导航调参的基础。
3. **QoS 兼容性**：发布/订阅端 QoS 不匹配时静默无数据，是最隐蔽的坑；用 `ros2 topic info /odom -v` 查看两端 QoS。
4. **接口包工程化**：`.srv` / `.action` 必须放在独立接口包，修改接口后必须重新 `colcon build` 并 `source`，且所有依赖包要重编。
5. **动态调参的落地**：把速度、阈值、频率做成参数（并写好描述与范围），是让程序「可交付」而非「能跑」的关键一步。

## 19.4 代码与命令实战

### 19.4.1 自定义接口（Cru / Nav）

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

### 19.4.2 话题：速度发布与里程计订阅

`my_exer01_topic_pub`（C++）与 `py_exer01_topic_pub`（Python）：参数 `linear_x`/`angular_z`，10Hz 发布 `/cmd_vel`；`my_exer02_topic_sub` 订阅并打印。rclpy 参考实现（含动态调参）：

```python
#!/usr/bin/env python3
"""按固定频率发布 /cmd_vel，线速度/角速度为可动态调整的参数。"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class VelocityPublisher(Node):
    def __init__(self):
        super().__init__('velocity_publisher')
        self.declare_parameter('linear_speed', 0.2)   # m/s
        self.declare_parameter('angular_speed', 0.5)  # rad/s
        self.declare_parameter('rate_hz', 20.0)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(
            1.0 / self.get_parameter('rate_hz').value, self.on_timer)

    def on_timer(self):
        msg = Twist()
        # 每次回调重新读取参数，支持 ros2 param set 在线调整
        msg.linear.x = self.get_parameter('linear_speed').value
        msg.angular.z = self.get_parameter('angular_speed').value
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = VelocityPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

订阅 `/odom` 的要点：解析 `pose.pose.position` 与 `twist.twist`，用 `math.hypot` 累计相邻位姿间距得到行驶路程，超过目标阈值即判到达（参考 `odom_monitor.py` 模式）。rclcpp 对照写法（完整节点 `odom_listener.cpp`）：

```cpp
// 订阅 /odom 并打印当前线速度；体现 rclcpp 与 rclpy 的回调写法差异
sub_ = create_subscription<nav_msgs::msg::Odometry>(
    "/odom", 10,
    [this](nav_msgs::msg::Odometry::SharedPtr msg) {
      RCLCPP_INFO(get_logger(), "linear.x = %.3f m/s",
                  msg->twist.twist.linear.x);
    });
```

### 19.4.3 服务实现运动控制（Cru）

服务端 `cru_server.cpp`：解析请求中的线速度/角速度/时长，执行期间周期发布 `/cmd_vel`，执行完毕后响应 `success=true, message=运动执行完成`；客户端 `cru_client.cpp` 从命令行读取三个参数并提交。课堂同款「里程计闭环定点运动」的 rclpy 参考骨架（注意工作线程避免阻塞 executor）：

```python
#!/usr/bin/env python3
"""服务端：接收定点运动请求，用里程计闭环控制并在到位后返回结果。"""
import math
import threading
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from mycar_interfaces.srv import SetMotion

class SetMotionServer(Node):
    def __init__(self):
        super().__init__('set_motion_server')
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.srv = self.create_service(SetMotion, 'set_motion', self.on_request)
        self.get_logger().info('set_motion server ready')

    def on_odom(self, msg: Odometry):
        self.odom_x = msg.pose.pose.position.x
        self.odom_y = msg.pose.pose.position.y

    def on_request(self, request, response):
        # 注意：示例放在工作线程，避免阻塞 executor
        threading.Thread(target=self.run_motion,
                         args=(request, response), daemon=True).start()
        return response

    def run_motion(self, request, response):
        x0, y0 = self.odom_x, self.odom_y
        rate = self.create_rate(20.0)
        while rclpy.ok():
            moved = math.hypot(self.odom_x - x0, self.odom_y - y0)
            if moved >= request.distance:
                break
            cmd = Twist()
            cmd.linear.x = min(request.speed, request.distance - moved)
            self.cmd_pub.publish(cmd)
            rate.sleep()
        self.cmd_pub.publish(Twist())  # 停车
        response.actual = math.hypot(self.odom_x - x0, self.odom_y - y0)
        response.success = True
        return response

def main():
    rclpy.init()
    rclpy.spin(SetMotionServer())

if __name__ == '__main__':
    main()
```

> 注意：本章实测用的是 `my_exer_interfaces/srv/Cru`（按时长执行的 `cru_server`/`cru_client`，见 19.5.2）；上例演示的是「按里程闭环」的同类模式，两者服务端都在子线程执行运动。

### 19.4.4 动作实现导航控制（Nav）

服务端 `nav_server.cpp`：

- 接收目标点 `goal(x,y)`；
- 执行体（子线程）订阅 `/odom` 实时计算剩余距离 `remaining = sqrt((gx-ox)² + (gy-oy)²)`；
- 以 `Rate(1Hz)` 连续反馈，到达阈值内响应 `reached=true`；
- 执行期间将速度发布到 `/cmd_vel`。

客户端 `nav_client.cpp` 提交目标并注册三个回调（目标响应/反馈/结果）。动作接口三段式示例：

```text
# 目标
float32 distance
float32 speed
---
# 结果
bool success
float32 actual
---
# 反馈
float32 progress        # 0.0 ~ 1.0
float32 remaining       # 剩余距离（米）
```

rclpy 客户端参考（含反馈打印与用户中断取消）：

```python
#!/usr/bin/env python3
"""动作客户端：发送目标、打印反馈、支持 Ctrl+C 取消任务。"""
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from mycar_interfaces.action import NavigatePoint

class NavigateClient(Node):
    def __init__(self):
        super().__init__('navigate_client')
        self.client = ActionClient(self, NavigatePoint, 'navigate_point')

    def send(self, distance, speed):
        self.client.wait_for_server()
        goal = NavigatePoint.Goal()
        goal.distance, goal.speed = distance, speed
        future = self.client.send_goal_async(
            goal, feedback_callback=lambda fb: self.get_logger().info(
                f'进度 {fb.feedback.progress:.0%}，剩余 {fb.feedback.remaining:.2f} m'))
        future.add_done_callback(self.on_goal)

    def on_goal(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('目标被拒绝')
            return
        self.get_logger().info('目标已接受')
        goal_handle.get_result_async().add_done_callback(self.on_result)

def main():
    rclpy.init()
    node = NavigateClient()
    node.send(1.5, 0.2)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('用户中断：请求取消')  # 实际调用 goal_handle.cancel_goal_async()
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

> 兼容提示：Jazzy 的目标响应回调签名是 `void goal_response_callback(GoalHandleNav::SharedPtr)`；Humble 为 `std::shared_future<GoalHandleNav::SharedPtr>`。

### 19.4.5 常用调试命令速查

```bash
# 分布式环境验证：两台机器互查节点/话题
ros2 node list && ros2 topic list
ros2 topic hz /odom          # 里程计发布频率
ros2 topic echo /odom --once # 查看一帧里程计（含位姿与速度）
ros2 topic info /odom -v     # 查看 QoS 详情，排查"有数据但收不到"
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}" -r 10

# 参数动态调参（配合 19.4.2 的节点）
ros2 param describe /velocity_publisher linear_speed
ros2 param set /velocity_publisher linear_speed 0.3

# 服务与动作调试
ros2 service list -t
ros2 service call /set_motion mycar_interfaces/srv/SetMotion "{distance: 1.0, speed: 0.2}"
ros2 action list -t
ros2 action send_goal /nav my_exer_interfaces/action/Nav "{goal: {x: 3.0, y: 4.0}}" --feedback

# TF 查询
ros2 run tf2_ros tf2_echo odom base_footprint
```

## 19.5 运行效果（实测）

### 19.5.1 话题发布与订阅

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

`my_exer02_topic_sub` 订阅端同步打印出相同字段。

### 19.5.2 服务实现运动控制（Cru，实测）

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

### 19.5.3 动作实现导航控制（Nav，实测）

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

## 19.6 与 ROS2 / 机器人开发的关联

1. **硬件节点抽象**：底盘/雷达/摄像头都建模为「订阅指令话题 + 发布数据话题」的标准节点，换硬件（Arduino→STM32、换雷达品牌）只换驱动节点，上层建图、导航、控制代码零改动——这是写任何机器人驱动时的模板。
2. **cmd_vel 速度控制**：`/cmd_vel`（`geometry_msgs/msg/Twist`）是差速车的事实标准接口。键盘遥控、导航控制器、手写运动控制，最终都汇到这一个话题；理解 linear.x 与 angular.z 的配合，是后续导航调参（DWB/MPPI 控制器）的前提。
3. **里程计话题（Odometry）**：`/odom` 与 odom→base_footprint 变换同时提供「位姿估计」与「速度反馈」，是建图、定位、导航以及本章运动闭环的共同基石；里程计精度直接决定上层算法上限。
4. **三种通信机制的真实分工**：本章案例就是一套「选型教材」——连续传感数据用话题、单次配置/查询用服务、可取消的长任务用动作。这套判断标准会直接迁移到机械臂抓取、导航任务下发等任何机器人场景。
5. **分布式开发习惯**：SSH + VSCode Remote + 分布式验证的流程，就是真实机器人团队的日常；为第 20 周的 ROS_DOMAIN_ID 分组隔离与多机编队打下操作基础。

## 19.7 自测与练习

1. **概念题**：Mycar 中速度控制、里程计上报、定点运动控制分别应选话题、服务还是动作？说明理由。
2. **动手任务**：把 19.4.2 的速度发布节点改成「键盘遥控」（`teleop` 模式）：W/X 增减线速度、A/D 增减角速度、空格停车。验收标准：`ros2 topic echo /cmd_vel` 能看到速度平滑变化，实体车（或 stage_ros2）能前进/后退/原地转。
3. **动手任务**：实现「到达目标点」动作客户端并支持超时取消：发送 2 米目标，若 15 秒未完成则调用 `cancel_goal_async()` 并打印最终结果。验收标准：能看到反馈进度打印，超时后小车停车、客户端收到 `CANCELED` 状态。

> 参考答案要点：1) 速度与里程计是持续数据流 → 话题；定点运动是有明确完成时刻的长任务 → 动作（若只要求结果、无需进度与取消，可用服务）。2) 键盘节点用 `getch`/`termios` 读键，定时器周期发布 Twist，参数保存当前速度。3) 客户端保存 goal_handle，定时器检查超时后发起取消；动作服务端在取消回调中清零 `cmd_vel` 并返回取消结果。

## 19.8 常见问题（FAQ）

- **Q：两台机器互相 `ros2 topic list` 看不到对方节点？** A：按顺序检查——是否同一网段且能 ping 通；防火墙是否放行 DDS 端口（默认 UDP 7400 起）；两端 `ROS_DOMAIN_ID` 是否一致；任一端是否设置了 `ROS_LOCALHOST_ONLY=1`（它会禁止跨机通信）。
- **Q：`ros2 topic echo /odom` 有数据，但我的订阅节点收不到？** A：大概率是 QoS 不匹配。用 `ros2 topic info /odom -v` 查看发布端 QoS（如 Best Effort），订阅端改用 `qos_profile_sensor_data`（rclpy）或 `rclcpp::SensorDataQoS()`（rclcpp）。
- **Q：底盘驱动起来后 rviz2 里里程计不更新？** A：依次确认：串口设备权限（`sudo usermod -aG dialout $USER` 后重新登录）、串口波特率与固件一致、`/odom` 频率正常、odom→base_footprint TF 已发布（`ros2 run tf2_tools view_frames`）。
- **Q：动作服务端为什么收不到取消请求？** A：执行回调被长循环阻塞、executor 无法调度取消回调。把控制逻辑移到定时器/状态机，或使用多线程 executor（`rclcpp::executors::MultiThreadedExecutor`）。
- **Q：改了 `.srv` / `.action` 后客户端报「类型不支持」？** A：接口包需重新 `colcon build --packages-select` 并重新 `source install/setup.bash`，同时所有依赖它的包也要重编（`colcon build` 全量最稳妥）。

## 19.9 本章小结

- 服务适合「短时执行、一次反馈」，动作适合「长时执行、连续反馈」——同一辆小车的运动控制用两者实现后差异一目了然；
- 动作执行体必须运行在**子线程**，避免阻塞 executor；
- 剩余距离依赖 `/odom`，实车与仿真只需保证里程计话题一致；
- 硬件节点抽象 + 三种通信机制选型 + 动态调参，是从「ROS2 知识」走向「机器人产品」的第一步。
