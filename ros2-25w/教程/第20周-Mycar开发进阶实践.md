# 第20章 Mycar 整车集成与多机协同

> 本章把第 19 章的驱动节点集成为**整车 bringup**，并实现**多机器人多 tf 树**与**航点跟随**；同时补齐多机通信隔离、launch 工程化、rosbag2 数据管理与 URDF 机器人模型等系统能力。
>
> 本章对应代码：`code/ws03_exercise/src/my_exer07_bringup`、`my_exer08_follow`、`my_exer09_multi_tf`。

## 20.1 概览与课时结构

本章把 Mycar 从「能跑」推进到「能交付、能协同」：先解决多机/多车并存时的**通信隔离与命名规范**问题，再用 launch 把整车驱动与坐标变换**一键集成**、用 rosbag2 做**数据管理**，最后深入坐标变换（TF）——实现多机器人 TF 树、车辆跟随与多车编队护航，并把 URDF 机器人模型接入 rviz2。在 25 周体系中，本章是把 ROS2 系统工程能力（隔离、编排、数据、TF、模型）在真实机器人上做完整闭环的收尾阶段；学完能独立 bringup 一台车，并具备多车协同开发的基础。

| 课 | 小节 | 时长 | 一句话导览 |
|---|---|---|---|
| 第1课 系统管理与工具应用 | 1 节 17 个视频 | 2h12m | 本地/分组通信隔离、节点与话题命名规范、rqt_graph 拓扑分析、日志与 rqt_console、rqt_plot 曲线监控 |
| 第2课 launch 与数据管理实践 | 2 节 25 个视频 | 3h46m | 整车启动 launch 集成与优化（含静态 TF），launch 封装与仿真/实体两套集成，rosbag2 录制回放 |
| 第3课 坐标变换、多机器人协同与模型应用实践 | 4 节 46 个视频 | 6h55m | map/odom 概念与关系、多机器人 TF 树与实体部署、车辆跟随与多车编队护航、URDF 模型显示/修改/集成 |

> 全周视频 88 个，总时长约 12h54m（2h12m + 3h46m + 6h55m），难度进阶→高阶。20.5 节的输出均为本机（Jazzy）实测。

## 20.2 知识点梳理

### 20.2.1 第1课 系统管理与工具应用

**核心概念**：ROS2 默认「全网同 domain 自由发现」，真实项目必须主动做**隔离（Isolation）**与**命名（Naming）**管理，再用可视化工具观测系统。

**要点 1：本地隔离（ROS_LOCALHOST_ONLY）**。`export ROS_LOCALHOST_ONLY=1` 后节点只走 loopback，不与外界通信——用于本机调试/上课演示避免「串台」。特点：影响整机所有节点、优先级高、粒度最粗；只隔离「本机 ↔ 外界」，不隔离本机内部。

**要点 2：分组隔离（ROS_DOMAIN_ID）**。DDS 用 domain 划分「发现域」：`export ROS_DOMAIN_ID=0` 的机器只能看到同 ID 的机器。多机器人/多组实验时给每组分配不同 ID（0~232），这是**多机通信与多车协同的分组基础**。注意：ID 相同才互通，且两台机器 ID 冲突会互相「串台」。

**要点 3：话题名称设置**。话题名支持相对名（`scan`）、绝对名（`/scan`）与命名空间修饰（`camera/image_raw`）；通过 launch 的 `namespace` 参数或 remap（`--ros-args -r scan:=mycar/scan`）统一加前缀。规范：传感器话题带命名空间，控制话题统一 `/xxx/cmd_vel` 结构。

**要点 4：节点名称设置**。节点名可在代码构造时指定，也可用 `--ros-args -r __node:=my_driver` 覆盖；同名节点会导致旧节点被踢下线，驱动类节点建议「车型+功能」命名（如 `mycar_lidar_driver`）。

**要点 5：节点与话题名称联合设置**。多车场景的标准做法：**命名空间 = 车名**（`/robot1/...`、`/robot2/...`），节点名在空间内唯一，话题自动继承空间前缀；配合 `push_ros_namespace`（launch）或 `GroupAction` 成组管理。

**要点 6：rqt_graph 三种视角**。两种启动方式（独立 `rqt_graph` 或 rqt 插件面板）；节点视图查看单节点连接、多节点关系视图看清「谁发谁收」、话题筛选（按前缀/正则过滤）在大系统里快速定位问题链路。多车时配合命名空间筛选，能一眼看出两台车是否互相干扰。

**要点 7：日志系统**。rclpy `get_logger().info/warn/error`（rclcpp `RCLCPP_INFO/WARN/ERROR`），支持**节流输出**（throttle）避免刷屏；日志落盘到 `~/.ros/log/`，配合 **rqt_console** 按级别/节点/关键词过滤，是复盘偶发故障的第一手材料。调试期多打 INFO，交付期收敛到 WARN 以上并保留关键状态迁移日志。

**要点 8：rqt_plot**。把话题里的数值字段画成实时曲线（如 `/odom/pose/pose/position/x`、`/battery/voltage`），用于验证速度平滑度、里程计抖动、PID 响应等「看数字没感觉」的问题。

### 20.2.2 第2课 launch 与数据管理实践

**核心概念**：launch 是机器人应用的「总装线」——把驱动、TF、参数、命名空间编排成一键启动；rosbag2 是「黑匣子」——把运行数据录下来离线复现。

**要点 1：机器人启动 launch（bringup）**。集成顺序：硬件准备与单体测试 → **雷达端口映射**（udev 规则绑定 `/dev/lidar`，避免 ttyUSB 编号漂移）→ 每个驱动各自写 launch（底盘、雷达、摄像头）→ 摄像头驱动优化（参数化分辨率/帧率/设备名，失败自动重启）→ 简单集成 → 优化集成（分组、参数文件、条件启动、respawn）→ 整车测试（`ros2 node list` / `ros2 topic hz` 逐项验收）。

**要点 2：launch 中发布静态坐标变换**。雷达/相机安装位姿是常量，用 `static_transform_publisher`（CLI 或 launch 节点）发布 laser→base_footprint、camera→base_link；**base_footprint 与 base_link 的约定**：base_footprint 在地面投影（供导航/定位使用），base_link 在车体中心，二者只差一个 z（及安装偏移），由静态 TF 连接。

**要点 3：launch 应用与封装**。四层递进：简单集成（全写在一个 launch.py）→ 仿真集成（stage_ros2 + 传感器模拟）→ 实体机器人集成（真实串口/设备参数）→ **文件封装**（公共部分抽 `IncludeLaunchDescription` + `launch_arguments` 传参 + `PythonLaunchDescriptionSource` 复用，仿真/实体共用一套上层 launch）。其他案例：条件启动（IfCondition）、事件处理（OnProcessExit 顺序拉起）、参数 YAML 加载。

**要点 4：数据管理（rosbag2）**。rqt bag 插件可视化录制/回放/查看信息；命令行 `ros2 bag record`（可指定话题、QoS、分卷）与 `ros2 bag play`（`-r` 倍速、`--loop`、`-s` 起始偏移、`--clock` 发布仿真时钟）。把「雷达丢帧」「里程计跳变」录下来，离线反复回放调试，不用反复跑车。

> **注意：** 回放 rosbag 时若节点依赖 `/tf_static`，需包含 TF 相关话题（`/tf`、`/tf_static`）一起录制；带时间戳的算法（如 SLAM）回放时记得加 `--clock` 并把节点 `use_sim_time` 设为 true。

### 20.2.3 第3课 坐标变换、多机器人协同与模型应用实践

**核心概念**：TF2 是机器人系统的「坐标骨架」；多机器人 = 多棵 TF 树 + 命名空间隔离；URDF 是「模型骨架」，与 TF 共同构成 rviz2 中可理解的机器人表示。

**要点 1：静态坐标变换**。安装关系（雷达相对车体）不随时间变化，用静态 TF 发布一次即可（`static_transform_publisher x y z yaw pitch roll frame_id child_frame_id`）；动态变换（车体在世界中的位姿）则由里程计/定位节点持续发布。

**要点 2：map 与 odom**。四层坐标系经典结构：

| 变换 | 来源 | 特点 |
|---|---|---|
| map→odom | SLAM / AMCL | 可能跳变，修正累积误差（全局、绝对） |
| odom→base_footprint | 底盘里程计积分 | 平滑连续，但会漂移（局部、相对） |
| base_footprint→base_link | 静态安装关系 | 固定不变 |
| base_link→sensor | 静态安装关系 | 固定不变 |

**概念**：odom 是「连续但漂移」的局部位姿，map 是「精确但会跳」的全局位姿；**关系**：map→odom 就是二者的修正量。导航要求 TF 树完整且时间连续，缺一环全链路瘫痪。

**要点 3：多机器人坐标变换**。多车时每台车一棵 TF 树：`robot1/odom → robot1/base_footprint → robot1/laser`。实现要点：全部 frame_id 加车名前缀、命名空间隔离话题、仿真中用不同初始位姿/不同 domain 启动多车，launch 用 `GroupAction + push_ros_namespace` 集成；实体部署时每台车独立主控板 + 独立 ROS_DOMAIN_ID（或同 domain + 命名空间），PC 侧统一查看。课程视频覆盖仿真实现 → launch 集成 → 实体机器人需求/分析 → 底盘集成 → 雷达集成 → 摄像头集成 → 部署全流程。

**要点 4：view_frames 工具**。`ros2 run tf2_tools view_frames` 生成 TF 树 PDF，用于验证父子关系、查找断链与多余发布者（两个节点发布同一变换是常见事故源）。

**要点 5：车辆跟随**。需求：后车保持与前车的固定位姿关系。实现链路：前车发布自身目标坐标系（如 `robot1/odom` 下的车身 frame，或专设 `follow_target` frame）→ 后车**订阅坐标变换**（tf2 监听两车 base_footprint 的相对变换）→ 计算位置/航向误差 → 输出后车 `/cmd_vel`（P 控制即可）→ 移植到实体机器人。这是「TF 当作跨车状态接口」的典型用法。

**要点 6：多车编队护航**。在仿真环境准备多车 → 每车发布目标坐标系（编队队形偏移：领航车 + 2~N 跟随车位姿）→ 跟随车订阅 TF 计算期望位姿并控制跟随，实现「护航」队形。编队核心是把**队形几何**编码成各车的目标 frame 偏移，控制层复用车辆跟随逻辑。

**要点 7：机器人模型（URDF）应用**。URDF（Unified Robot Description Format）用 link/joint 描述刚体树，配合 `robot_state_publisher` 把关节状态转成 TF。三步走：**本地显示**（`joint_state_publisher_gui` + `robot_state_publisher` + rviz2 RobotModel）→ **分布式显示**（模型在车上发布、rviz2 在 PC 显示，TF 经 DDS 跨机）→ **修改模型**（改尺寸/颜色/添加雷达与相机 link）→ **集成模型**（把 URDF 放进 bringup launch，与静态 TF、驱动一起启动，形成完整机器人描述）。

## 20.3 重点与难点

1. **隔离策略的分层选择**：`ROS_LOCALHOST_ONLY`（单机封闭）→ `ROS_DOMAIN_ID`（多机分组）→ 命名空间（同域内多车/多实例）→ 话题 remap（细粒度改名）。四者常叠加使用，理解各自作用域是多机开发的第一道门槛。
2. **map/odom/base 的职责划分**：何时该看 odom（控制反馈）、何时必须用 map（全局定位）；map→odom 跳变对导航的影响与排查思路。
3. **多机器人 TF 树设计**：frame 前缀 + 命名空间 + 独立 odom 源，三者必须一致；漏改一个 frame_id 就会出现「两车抢同一坐标系」的灵异现象。
4. **bringup launch 的工程化**：参数外置 YAML、设备名 udev 固定、respawn 自愈、仿真/实体复用同一上层 launch——这些决定项目能否长期维护。
5. **车辆跟随/编队的控制闭环**：TF 查询有延迟与时戳要求（用 `lookup_transform` 的 timeout），控制频率、误差平滑、到达死区都要调；先仿真后实车，先单车后多车。

## 20.4 代码与命令实战

### 20.4.1 通信隔离与命名规范（bash）

```bash
# 车载板（robot1）：命名空间=车名，domain 分组
export ROS_DOMAIN_ID=1
export ROS_NAMESPACE=robot1
source /opt/ros/humble/setup.bash && source ~/mycar_ws/install/setup.bash
ros2 run mycar_bringup lidar_driver --ros-args -r __node:=lidar_driver -r scan:=scan

# PC（调试终端）：只做本机调试时开启本地隔离，跨机调试务必取消
export ROS_LOCALHOST_ONLY=1   # 1=禁止跨机；调试多机时改为 0 或 unset

# 验证隔离是否生效
ros2 node list                 # 只应看到本组节点
ros2 topic list                # 话题应带 /robot1/ 前缀
```

### 20.4.2 整车 bringup launch

**需求**：一条命令启动小车的全部底层节点——底盘驱动（base_driver）、雷达驱动（lidar_driver）、机器人模型发布（robot_state_publisher + mycar.urdf.xacro）、参数加载（mycar.yaml）。

`car_bringup_launch.py` 结构：

```python
robot_description = Command(["xacro ", model_path])   # 加载 xacro 模型
Node(package="robot_state_publisher", executable="robot_state_publisher",
     parameters=[{"robot_description": robot_description, "use_sim_time": use_sim_time}]),
Node(package="my_exer07_bringup", executable="base_driver.py",   # 底盘驱动(占位实现)
     parameters=[mycar_yaml]),
Node(package="my_exer07_bringup", executable="lidar_driver.py",  # 雷达驱动(占位实现)
     parameters=[mycar_yaml]),
```

> 注意：ament_python 包的 launch/model/config 需在 setup.py 中按**带子目录的目标路径**安装：
>
> ```python
> ('share/' + package_name + '/model', ['model/mycar.urdf.xacro']),
> ```
> 直接写 `('share/' + package_name, ['model/mycar.urdf.xacro'])` 会平铺到 share 根目录，导致 xacro 找不到文件。

launch 工程化模式清单：`DeclareLaunchArgument` + `LaunchConfiguration` 参数化（如 `use_sim`、`namespace`）；`GroupAction` + `PushRosNamespace` 一组节点统一命名空间；`IncludeLaunchDescription` + `PythonLaunchDescriptionSource` 复用子 launch 并传 `launch_arguments`；`IfCondition`/`UnlessCondition` 切换仿真与实体节点；`respawn=True` + `respawn_delay` 自愈重启；`parameters=[yaml]` 外置参数；`static_transform_publisher` 节点发布安装位姿（laser→base_footprint、base_footprint→base_link）。

### 20.4.3 车辆跟随控制器（rclpy）

后车订阅领航车与本车的 TF，P 控制保持跟随距离——`mycar_formation/follow_controller.py` 模式：

```python
#!/usr/bin/env python3
"""后车订阅 robot1（领航车）与 robot2（本车）的 TF，P 控制保持跟随距离。"""
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException

class FollowController(Node):
    def __init__(self):
        super().__init__('follow_controller')
        self.declare_parameter('follow_distance', 1.0)   # 期望跟车距离（米）
        self.declare_parameter('kp_linear', 0.6)
        self.declare_parameter('kp_angular', 1.2)
        self.declare_parameter('leader_frame', 'robot1/base_footprint')
        self.declare_parameter('self_frame', 'robot2/base_footprint')
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.cmd_pub = self.create_publisher(Twist, '/robot2/cmd_vel', 10)
        self.create_timer(0.05, self.on_timer)  # 20 Hz 控制

    def on_timer(self):
        try:
            t = self.tf_buffer.lookup_transform(
                self.get_parameter('self_frame').value,
                self.get_parameter('leader_frame').value,
                rclpy.time.Time())  # 最新可用变换
        except (LookupException, ConnectivityException, ExtrapolationException):
            return
        dx = t.transform.translation.x
        dy = t.transform.translation.y
        dist = math.hypot(dx, dy)
        heading = math.atan2(dy, dx)          # 领航车在本车坐标系中的方位
        err = dist - self.get_parameter('follow_distance').value

        cmd = Twist()
        cmd.linear.x = max(-0.5, min(0.5, self.get_parameter('kp_linear').value * err))
        cmd.angular.z = max(-1.0, min(1.0, self.get_parameter('kp_angular').value * heading))
        if abs(err) < 0.05 and abs(heading) < 0.05:   # 到位死区：避免抖动
            cmd = Twist()
        self.cmd_pub.publish(cmd)
        self.get_logger().info(
            f'dist={dist:.2f} heading={heading:.2f}', throttle_duration_sec=1.0)

def main():
    rclpy.init()
    rclpy.spin(FollowController())

if __name__ == '__main__':
    main()
```

### 20.4.4 URDF 模型片段与显示

`mycar_description/urdf/mycar.urdf.xacro`（link/joint 描述 + 雷达/相机安装位姿）：

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="mycar">
  <link name="base_footprint"/>

  <joint name="base_joint" type="fixed">
    <parent link="base_footprint"/>
    <child link="base_link"/>
    <origin xyz="0 0 0.10" rpy="0 0 0"/>
  </joint>

  <link name="base_link">
    <visual>
      <geometry><box size="0.40 0.30 0.15"/></geometry>
      <material name="blue"><color rgba="0.1 0.3 0.8 1.0"/></material>
    </visual>
    <collision>
      <geometry><box size="0.40 0.30 0.15"/></geometry>
    </collision>
  </link>

  <!-- 雷达：相对 base_link 的安装位姿 -->
  <joint name="laser_joint" type="fixed">
    <parent link="base_link"/>
    <child link="laser_link"/>
    <origin xyz="0.10 0 0.15" rpy="0 0 0"/>
  </joint>
  <link name="laser_link">
    <visual>
      <geometry><cylinder radius="0.035" length="0.04"/></geometry>
    </visual>
  </link>

  <!-- 摄像头 -->
  <joint name="camera_joint" type="fixed">
    <parent link="base_link"/>
    <child link="camera_link"/>
    <origin xyz="0.20 0 0.12" rpy="0 0 0"/>
  </joint>
  <link name="camera_link">
    <visual>
      <geometry><box size="0.03 0.06 0.03"/></geometry>
    </visual>
  </link>
</robot>
```

```bash
# 本地显示机器人模型：joint_state_publisher_gui + robot_state_publisher + rviz2
ros2 launch mycar_description display.launch.py
# 分布式显示：模型与 robot_state_publisher 跑在车上，PC 只开 rviz2 并连接同一 ROS_DOMAIN_ID
ros2 run tf2_ros tf2_echo base_link laser_link     # 验证模型 TF
```

### 20.4.5 多机器人集成与数据管理命令

```bash
# 多车编队仿真：两台车、两棵 TF 树、同一 domain 不同命名空间
ros2 launch mycar_formation multi_robot.launch.py use_sim:=true robot_count:=2

# TF 树检查：确认 robot1/robot2 各自成树、无交叉发布
ros2 run tf2_tools view_frames          # 生成 frames.pdf，检查断链与重复发布者

# rosbag2 录制回放：录编队数据用于离线调参
ros2 bag record -a -o mycar_run1        # -a 录全部话题；建议实战改为指定话题集
ros2 bag record /robot1/odom /robot2/odom /tf /tf_static -o odom_debug
ros2 bag play mycar_run1 --clock -r 0.5 # 0.5 倍速回放并发布 /clock
ros2 bag info mycar_run1                # 查看话题清单、消息数、时长

# rqt 系列：拓扑/曲线/日志三视角
ros2 run rqt_graph rqt_graph            # 多节点关系 + 话题筛选
ros2 run rqt_plot rqt_plot /robot1/odom/pose/pose/position/x
ros2 run rqt_console rqt_console        # 过滤日志级别与节点
```

### 20.4.6 rclcpp 对照：代码方式发布静态变换

```cpp
// 代码方式发布 base_link -> camera_link 静态变换（等价 static_transform_publisher）
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/static_transform_broadcaster.h"
#include "geometry_msgs/msg/transform_stamped.hpp"

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = rclcpp::Node::make_shared("camera_static_tf");
  auto broadcaster = std::make_shared<tf2_ros::StaticTransformBroadcaster>(node);

  geometry_msgs::msg::TransformStamped tf;
  tf.header.stamp = node->now();
  tf.header.frame_id = "base_link";
  tf.child_frame_id = "camera_link";
  tf.transform.translation.x = 0.20;
  tf.transform.translation.z = 0.12;
  tf.transform.rotation.w = 1.0;
  broadcaster->sendTransform(tf);

  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
```

## 20.5 运行效果（实测）

### 20.5.1 整车 bringup（实测）

```bash
ros2 launch my_exer07_bringup car_bringup_launch.py
```

本机（Jazzy）实测：launch 正常拉起 robot_state_publisher / base_driver / lidar_driver；由于 base_driver、lidar_driver 为**硬件占位实现**（真车需要串口/网口雷达），且整车还需要 `usb_cam` 等传感器包，在无硬件环境会报 `package 'usb_cam' not found`——属预期现象，实车/仿真环境按课程视频效果运行。

### 20.5.2 多机器人多 tf 树（实测）

**需求**：同一颗 tf 树上挂载两台机器人（robot1/robot2），各自拥有独立的 odom 坐标系，再统一挂到 map 下：

```
map ── robot1_odom ── robot1_base
   └── robot2_odom ── robot2_base
```

`multi_tf_launch.py` 用两个 `static_transform_publisher` 分别发布 `map→robot1_odom`、`map→robot2_odom`：

```python
Node(package="tf2_ros", executable="static_transform_publisher",
     arguments=["--x","0","--y","0","--z","0","--frame-id","map","--child-frame-id","robot1_odom"]),
Node(package="tf2_ros", executable="static_transform_publisher",
     arguments=["--x","2","--y","0","--z","0","--frame-id","map","--child-frame-id","robot2_odom"]),
```

```bash
ros2 launch my_exer09_multi_tf multi_tf_launch.py
```

```text
[INFO] [static_transform_publisher-1]: process started with pid [429415]
[INFO] [static_transform_publisher-2]: process started with pid [429416]
[static_transform_publisher-1]: Spinning until stopped - publishing transform
    from 'map' to 'robot1_odom'
[static_transform_publisher-2]: Spinning until stopped - publishing transform
    from 'map' to 'robot2_odom'
```

rviz2 中即可同时显示两台机器人的 tf 树。

### 20.5.3 航点跟随（实测）

**需求**：目标位姿广播方（goal_broadcaster）按 `data/waypoints.csv` 中的航点序列循环发布目标 tf；跟随控制器（follow_controller）监听 `map→follow_goal` 变换并输出控制量，实现小车按航点巡航。

```bash
ros2 launch my_exer08_follow follow_launch.py
```

```text
[INFO] [goal_broadcaster-1]: process started with pid [437527]
[INFO] [follow_controller-2]: process started with pid [437528]
```

两个节点启动后按 1Hz 轮播航点、计算控制量；接入实车 `/cmd_vel` 即可巡航。

## 20.6 与 ROS2 / 机器人开发的关联

1. **多机通信与 DDS domain（ROS_DOMAIN_ID）**：同一 domain 内自动发现、跨 domain 完全隔离。多机器人、多组实验、实车与仿真并存时，靠 domain 分组 + 命名空间 + `ROS_LOCALHOST_ONLY` 三层手段管理通信边界，这是 ROS2 分布式系统设计的必修课。
2. **硬件节点抽象的系统化落地**：把「底盘/雷达/摄像头 = 标准节点」的抽象写进 bringup launch：设备参数外置、udev 固定端口、respawn 自愈、仿真/实体条件切换。任何新传感器（IMU、深度相机）都按同一模板接入。
3. **cmd_vel 速度控制的闭环升级**：车辆跟随/编队把 TF 误差直接映射为 `/cmd_vel`，复用了第 19 周的速度控制接口与里程计反馈——同一话题接口，从「键盘遥控」升级为「多车协同控制」。
4. **里程计话题与 TF 树的分工**：`/odom` 提供速度与局部位姿，TF 提供全链路坐标关系；导航（map→odom→base_link→sensor）、SLAM、多车协同全部依赖这棵 TF 树的完整与连续。
5. **机器人模型 URDF 应用**：URDF + robot_state_publisher 是 rviz2、导航代价地图（footprint）、仿真（Gazebo/stage）共享的机器人描述；模型即「数字孪生骨架」，改一个安装位姿，全系统坐标自动一致。
6. **数据驱动调试（rosbag2）**：录包-回放-离线复现是机器人领域的标准排障流程，也是后续做算法回归测试、数据集采集的基础工具。

## 20.7 自测与练习

1. **概念题**：`ROS_LOCALHOST_ONLY=1` 与 `ROS_DOMAIN_ID=5` 各自隔离了什么？两台机器人想既互通又与其他实验互不干扰，应如何组合配置？
2. **动手任务**：写一个 `robot.launch.py`，集成底盘、雷达、摄像头与三个静态 TF（laser、camera、base_footprint→base_link），支持 `use_sim` 参数切换仿真/实体。验收标准：一条命令启动后 `ros2 run tf2_tools view_frames` 显示完整 TF 树、`ros2 topic hz` 中 `/scan` `/odom` `/image_raw` 均有稳定频率。
3. **动手任务**：实现双车跟随仿真：robot1 用 `ros2 topic pub` 或键盘遥控做领航，robot2 用 20.4.3 的控制器保持 1 米距离。验收标准：robot1 转弯时 robot2 稳定跟随，误差在 0.2 米内波动且不发散。

> 参考答案要点：1) `ROS_LOCALHOST_ONLY` 限制只走本机 loopback（与外界完全断开）；`ROS_DOMAIN_ID` 划分 DDS 发现域（同 ID 才互通）。组合：两车设相同 `ROS_DOMAIN_ID` 保持互通、各自 `ROS_NAMESPACE=robot1/robot2` 隔离话题节点、实验环境用不同于 0 的 domain 避免与其他组串台。2) 参数外置 + GroupAction 分组 + respawn；验收看 TF 树与话题频率。3) 用 TF lookup 取相对位姿做 P 控制 + 到位死区；先 rviz2 观察队形，再调 kp 与控制频率。

## 20.8 常见问题（FAQ）

- **Q：两台机器设了不同 `ROS_DOMAIN_ID` 还是能看到对方话题？** A：检查是否残留桥接工具（如 ros1_bridge/zenoh bridge）、是否实际读到了旧环境变量（`env | grep ROS_` 确认），以及是否在同一台机器上开多终端时部分终端未重新 export。
- **Q：rviz2 里机器人模型显示正常，但雷达数据对不上模型位置？** A：模型 link（URDF 里的 laser_link）与雷达消息 `frame_id`（如 `laser`）不一致，或静态 TF 的安装位姿与 URDF 数值不一致。统一 frame 命名，并让 URDF 的 joint origin 与静态 TF 参数保持同一份数据（推荐只由 URDF + robot_state_publisher 发布，不再手写静态 TF）。
- **Q：多车时 TF 报错「extrapolation into the past/future」？** A：多机时钟不同步。车载板启用 NTP/chrony 对时（`sudo timedatectl set-ntp true`），或控制端查询 TF 时使用 `lookup_transform(..., timeout)` 等待变换就绪，并统一使用最新变换而非指定旧时刻。
- **Q：`ros2 bag play` 回放时 SLAM/导航不工作？** A：未发布 `/clock` 或节点没开 `use_sim_time`。回放加 `--clock`，所有消费时间的节点设 `use_sim_time: true`（可在 launch 里统一设置）。
- **Q：rqt_graph 打开后节点图很大很乱怎么办？** A：用话题筛选按命名空间过滤（如 `robot1`），或切换节点/话题视图；平时保持「一车一命名空间」的规范，图自然清晰。
- **Q：launch 集成后摄像头节点反复重启？** A：设备名 `/dev/video0` 被占用或 USB 带宽不足。用 udev 固定设备名、降低分辨率/帧率，或把摄像头与雷达分到不同 USB 控制器；`respawn_delay` 给足间隔避免疯狂重启。

## 20.9 本章小结

- bringup 的意义是「一条命令拉起整车」，launch + yaml + xacro 是标准三件套；
- 多机器人共处一个系统时，tf 树的**根坐标系隔离**（map 下多 odom）是关键；
- 航点跟随 = 目标广播（数据驱动）+ 变换监听（控制驱动）的典型组合；
- 隔离（domain/命名空间）+ 编排（launch）+ 数据（rosbag2）+ 模型（URDF/TF），构成一台车「可交付」的全部工程底座。
