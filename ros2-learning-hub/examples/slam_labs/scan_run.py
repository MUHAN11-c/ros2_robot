#!/usr/bin/env python3
"""从实际 Harmonic 采集可重复的移动扫描。

输入为同包 Nav2 台架房间与本文件路线。x/y/z 用 m，偏航用 rad，戳用仿真 ns。
每步先请求 Gazebo 改位姿，再推进固定仿真步数，按 Header 配激光与世界位姿。
输出为实际扫描帧、独立参考位姿与几何校验。固定装置离散移位，不模拟行驶或滚动快门。
"""
from __future__ import annotations

from bisect import bisect_left
from collections import deque
import math
import os
from pathlib import Path
import statistics
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SCENE = HERE.parent / "nav2_labs/nav_room.sdf"
WORLD = "/world/hub_mapping_room"
STEP_NS = 5_000_000
CAPTURE_STEPS = 80


def stamp(message):
    time = message.header.stamp
    return time.sec * 10**9 + time.nanosec


def yaw(quaternion):
    q = quaternion
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def yaw_error(a, b):
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


def route():
    """返回分段移动和留出的恢复路线。主路线闭合位置，步距不超过 0.40 m。"""
    first = (-2.10, -1.35, 0.0)
    mapping = [first] * 4  # 首帧建图，其余三帧给启动计数和无位移对照。
    for x, y, angle in ((2.30, -1.35, 0.0), (2.30, 1.05, math.pi / 2),
                        (-2.10, 1.05, math.pi), (-2.10, -1.35, -math.pi / 2)):
        ax, ay, _ = mapping[-1]
        count = math.ceil(math.hypot(x - ax, y - ay) / 0.40)
        mapping.extend((ax + (x - ax) * i / count, ay + (y - ay) * i / count, angle) for i in range(1, count + 1))
    # 先回第一节点附近，再提供三个未在上面作为建图输入的扫描位置。
    held_out = [first] * 4 + [(first[0] + distance, first[1], 0.0) for distance in (0.32, 0.64, 0.96)]
    return mapping, held_out


def prepare_scene(output):
    """复用房间几何并增加移动命令及世界位姿观测，原始 SDF 保持独立。"""
    tree = ET.parse(SCENE)
    world = tree.find("world")
    world.set("name", WORLD.rsplit("/", 1)[1])
    ET.SubElement(world, "plugin", filename="gz-sim-user-commands-system", name="gz::sim::systems::UserCommands")
    rig = world.find("model[@name='scan_rig']")
    rig.find("link/sensor/topic").text = "/hub_mapping/scan"
    plugin = ET.SubElement(rig, "plugin", filename="gz-sim-odometry-publisher-system", name="gz::sim::systems::OdometryPublisher")
    for key, value in {"odom_frame": "gazebo_world", "robot_base_frame": "gazebo_rig", "odom_publish_frequency": "50",
                       "odom_topic": "/hub_mapping/ground_pose", "dimensions": "3"}.items():
        ET.SubElement(plugin, key).text = value
    scene = output / "mapping_room.sdf"
    tree.write(scene, encoding="utf-8", xml_declaration=True)
    boxes = []
    for model in world.findall("model"):
        if model is rig:
            continue
        x, y, _, roll, pitch, angle = map(float, model.findtext("pose").split())
        assert roll == pitch == angle == 0.0
        sx, sy, _ = map(float, model.findtext("link/visual/geometry/box/size").split())
        boxes.append((x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2))
    height = float(rig.findtext("pose").split()[2])
    return scene, boxes, height


def wall_distance(x, y, angle, boxes):
    """在已知场景中求平面射线与轴对齐盒的最近正交点，单位 m。"""
    dx, dy = math.cos(angle), math.sin(angle)
    intersections = []
    for x0, x1, y0, y1 in boxes:
        if abs(dx) > 1e-10:
            for edge in (x0, x1):
                d = (edge - x) / dx
                if d > 0 and y0 - 1e-9 <= y + dy * d <= y1 + 1e-9:
                    intersections.append(d)
        if abs(dy) > 1e-10:
            for edge in (y0, y1):
                d = (edge - y) / dy
                if d > 0 and x0 - 1e-9 <= x + dx * d <= x1 + 1e-9:
                    intersections.append(d)
    return min(intersections)


def capture(lab, egl_vendor, waypoints):
    from ament_index_python.packages import get_package_prefix
    from nav_msgs.msg import Odometry
    from ros_gz_interfaces.msg import Entity
    from ros_gz_interfaces.srv import ControlWorld, SetEntityPose
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan

    scene, boxes, height = prepare_scene(lab.output)
    subprocess.run(["gz", "sdf", "-k", str(scene)], check=True, timeout=5, stdout=subprocess.PIPE, text=True)
    render = dict(os.environ)
    if egl_vendor:
        render["__EGL_VENDOR_LIBRARY_FILENAMES"] = str(egl_vendor.resolve())
        render.pop("LIBGL_ALWAYS_SOFTWARE", None)
    lab.start("gazebo", ["gz", "sim", "-s", "--headless-rendering", "-v", "4", str(scene)], render)
    for _ in range(8):
        lab.assert_live()
        services = subprocess.check_output(["gz", "service", "-l"], text=True, timeout=3).splitlines()
        if all(WORLD + "/" + service in services for service in ("control", "set_pose")):
            break
    else:
        raise RuntimeError("未发现本次 Gazebo 世界的控制与移位服务")
    bridge = Path(get_package_prefix("ros_gz_bridge")) / "lib/ros_gz_bridge/parameter_bridge"
    service_specs = (WORLD + "/control@ros_gz_interfaces/srv/ControlWorld@gz.msgs.WorldControl@gz.msgs.Boolean",
                     WORLD + "/set_pose@ros_gz_interfaces/srv/SetEntityPose@gz.msgs.Pose@gz.msgs.Boolean")
    lab.start("bridge", [str(bridge), *service_specs, "--ros-args", "-r", "__ns:=" + lab.namespace,
                         "-r", "__node:=mapping_capture_bridge", "-p", "config_file:=" + str(HERE / "bridge.yaml"),
                         "-p", "override_timestamps_with_wall_time:=false"])
    scans, poses = deque(maxlen=80), deque(maxlen=240)
    laser = lab.node.create_subscription(LaserScan, "capture_scan", lambda msg: scans.append(msg), qos_profile_sensor_data)
    truth = lab.node.create_subscription(Odometry, "capture_pose", lambda msg: poses.append(msg), qos_profile_sensor_data)
    lab.wait(lambda: laser.get_publisher_count() == 1 and truth.get_publisher_count() == 1, "采集端点未配对")
    clock = lab.node.get_clock()
    assert clock.now().nanoseconds == 0
    samples = []
    for index, (x, y, angle) in enumerate(waypoints):
        before = clock.now().nanoseconds
        move = SetEntityPose.Request()
        move.entity.name, move.entity.type = "scan_rig", Entity.MODEL
        move.pose.position.x, move.pose.position.y, move.pose.position.z = x, y, height
        move.pose.orientation.z, move.pose.orientation.w = math.sin(angle / 2), math.cos(angle / 2)
        assert lab.call(SetEntityPose, WORLD + "/set_pose", move).success
        advance = ControlWorld.Request()
        advance.world_control.pause = True
        advance.world_control.multi_step = CAPTURE_STEPS
        assert lab.call(ControlWorld, WORLD + "/control", advance).success
        end = before + CAPTURE_STEPS * STEP_NS
        # 只从后半段的稳定窗口取样，避免把排队中的旧图像或旧位姿用于当前步。
        late = before + CAPTURE_STEPS * STEP_NS // 2
        lab.wait(lambda: clock.now().nanoseconds >= end and scans and stamp(scans[-1]) >= late and
                 poses and stamp(poses[-1]) >= late, f"第 {index} 个采集窗没有时钟、激光与位姿", seconds=6.0)
        lab.observe(0.04)
        assert clock.now().nanoseconds == end, (index, before, end, clock.now().nanoseconds)
        scan = next(msg for msg in reversed(scans) if late <= stamp(msg) <= end)
        pose_candidates = sorted((stamp(msg), i, msg) for i, msg in enumerate(poses) if late <= stamp(msg) <= end)
        pose_stamps = [entry[0] for entry in pose_candidates]
        slot = bisect_left(pose_stamps, stamp(scan))
        closest = min(pose_candidates[max(0, slot - 1):slot + 1], key=lambda entry: abs(entry[0] - stamp(scan)))
        pose = closest[2].pose.pose
        reference = (pose.position.x, pose.position.y, yaw(pose.orientation))
        delta = closest[0] - stamp(scan)
        assert abs(delta) <= 21_000_000, (index, delta)
        assert closest[2].header.frame_id == "gazebo_world" and closest[2].child_frame_id == "gazebo_rig"
        assert math.dist(reference[:2], (x, y)) < 0.02 and abs(pose.position.z - height) < 0.02 and yaw_error(reference[2], angle) < 0.02, (index, reference, (x, y, angle))
        assert scan.header.frame_id == "laser_link" and len(scan.ranges) == 361 and all(map(math.isfinite, scan.ranges))
        errors = sorted(abs(value - wall_distance(*reference[:2], reference[2] + scan.angle_min + i * scan.angle_increment, boxes))
                        for i, value in enumerate(scan.ranges))
        assert statistics.median(errors) < 0.02 and errors[math.floor(0.95 * len(errors))] < 0.04, (index, errors[-10:])
        samples.append(dict(index=index, stampNs=stamp(scan), poseStampNs=closest[0], poseDeltaNs=delta,
                            controlWindowNs=[before, end], commanded=[x, y, angle], truth=list(reference),
                            rangeMedianErrorM=statistics.median(errors), rangeP95ErrorM=errors[math.floor(0.95 * len(errors))],
                            angleMin=scan.angle_min, angleMax=scan.angle_max, angleIncrement=scan.angle_increment,
                            rangeMin=scan.range_min, rangeMax=scan.range_max, timeIncrement=scan.time_increment,
                            scanTime=scan.scan_time, ranges=list(scan.ranges)))
    assert all(b["stampNs"] > a["stampNs"] for a, b in zip(samples, samples[1:]))
    return samples, scene, boxes, height
