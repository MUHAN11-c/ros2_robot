# 第20章 Mycar 整车集成与多机协同

> 本章把第 19 章的驱动节点集成为**整车 bringup**，并实现**多机器人多 tf 树**与**航点跟随**。
>
> 本章对应代码：`code/ws03_exercise/src/my_exer07_bringup`、`my_exer08_follow`、`my_exer09_multi_tf`。

## 20.1 整车 bringup

### 20.1.1 案例以及案例分析

**需求**：一条命令启动小车的全部底层节点——底盘驱动（base_driver）、雷达驱动（lidar_driver）、机器人模型发布（robot_state_publisher + mycar.urdf.xacro）、参数加载（mycar.yaml）。

### 20.1.2 实现

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

### 20.1.3 运行效果（实测）

```bash
ros2 launch my_exer07_bringup car_bringup_launch.py
```

本机（Jazzy）实测：launch 正常拉起 robot_state_publisher / base_driver / lidar_driver；由于 base_driver、lidar_driver 为**硬件占位实现**（真车需要串口/网口雷达），且整车还需要 `usb_cam` 等传感器包，在无硬件环境会报 `package 'usb_cam' not found`——属预期现象，实车/仿真环境按课程视频效果运行。

## 20.2 多机器人多 tf 树

### 20.2.1 案例以及案例分析

**需求**：同一颗 tf 树上挂载两台机器人（robot1/robot2），各自拥有独立的 odom 坐标系，再统一挂到 map 下：

```
map ── robot1_odom ── robot1_base
   └── robot2_odom ── robot2_base
```

### 20.2.2 实现

`multi_tf_launch.py` 用两个 `static_transform_publisher` 分别发布 `map→robot1_odom`、`map→robot2_odom`：

```python
Node(package="tf2_ros", executable="static_transform_publisher",
     arguments=["--x","0","--y","0","--z","0","--frame-id","map","--child-frame-id","robot1_odom"]),
Node(package="tf2_ros", executable="static_transform_publisher",
     arguments=["--x","2","--y","0","--z","0","--frame-id","map","--child-frame-id","robot2_odom"]),
```

### 20.2.3 运行效果（实测）

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

## 20.3 航点跟随

### 20.3.1 案例以及案例分析

**需求**：目标位姿广播方（goal_broadcaster）按 `data/waypoints.csv` 中的航点序列循环发布目标 tf；跟随控制器（follow_controller）监听 `map→follow_goal` 变换并输出控制量，实现小车按航点巡航。

### 20.3.2 运行效果（实测）

```bash
ros2 launch my_exer08_follow follow_launch.py
```

```text
[INFO] [goal_broadcaster-1]: process started with pid [437527]
[INFO] [follow_controller-2]: process started with pid [437528]
```

两个节点启动后按 1Hz 轮播航点、计算控制量；接入实车 `/cmd_vel` 即可巡航。

## 20.4 本章小结

- bringup 的意义是「一条命令拉起整车」，launch + yaml + xacro 是标准三件套；
- 多机器人共处一个系统时，tf 树的**根坐标系隔离**（map 下多 odom）是关键；
- 航点跟随 = 目标广播（数据驱动）+ 变换监听（控制驱动）的典型组合。
