#!/usr/bin/env python3
"""以固定 Gazebo 激光验证 Jazzy 地图、AMCL 与 NavFn 规划链。

输入为同目录 SDF、桥映射和 Nav2 参数。距离用 m，角度用 rad，观测期限用单调秒。
输出为独立临时目录内的 PGM/YAML、原始代价值、路径坐标、ROS 回执和日志。
依次启动仿真时钟与激光、地图、定位和规划。没有启动控制器，也不发送速度命令。
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE.parent
sys.path.insert(0, str(EXAMPLES))
from gazebo_labs.validate_sensors import Lab, ns, sha, stamp

LETHAL, INSCRIBED, UNKNOWN = 254, 253, 255


@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    resolution: float
    x: float
    y: float

    def center(self, index):
        """输入为从地图下边缘开始的行主序下标，返回栅格中心的世界坐标 (m)。"""
        return (self.x + (index % self.width + 0.5) * self.resolution,
                self.y + (index // self.width + 0.5) * self.resolution)

    def index(self, x, y):
        column = math.floor((x - self.x) / self.resolution)
        row = math.floor((y - self.y) / self.resolution)
        if not (0 <= column < self.width and 0 <= row < self.height):
            raise ValueError(f"地图外坐标 {(x, y)} m")
        return row * self.width + column


def build_map(output):
    """由 SDF 的四堵墙与非对称柱生成先验地图，保留墙外未知区域。"""
    models = {model.attrib["name"]: model for model in ET.parse(HERE / "nav_room.sdf").findall("world/model")}

    def box(name):
        model = models[name]
        pose = tuple(map(float, model.findtext("pose").split()))
        size = tuple(map(float, model.findtext("link/collision/geometry/box/size").split()))
        visual = tuple(map(float, model.findtext("link/visual/geometry/box/size").split()))
        assert pose[3:] == (0.0, 0.0, 0.0) and size == visual and min(size) > 0.0
        return pose[:3], size

    walls = {name: box(name) for name in ("map_west", "map_east", "map_south", "map_north")}
    pillar = box("map_pillar")
    obstacle = box("observation_box")
    rig = tuple(map(float, models["scan_rig"].findtext("pose").split()))
    assert rig[3:] == (0.0, 0.0, 0.0)
    grid = Grid(80, 60, 0.10, -4.0, -3.0)
    west, east = (walls[name][0][0] for name in ("map_west", "map_east"))
    south, north = (walls[name][0][1] for name in ("map_south", "map_north"))
    geometry = [*walls.values(), pillar]
    values = []
    for index in range(grid.width * grid.height):
        x, y = grid.center(index)
        occupied = any(abs(x - pos[0]) <= size[0] / 2 + 1e-9 and abs(y - pos[1]) <= size[1] / 2 + 1e-9
                       for pos, size in geometry)
        values.append(100 if occupied else 0 if west < x < east and south < y < north else -1)

    # OccupancyGrid 的首行在 y 最小处，PGM 的首行在图像最上方。先反转行，再写灰度字节。
    palette = {100: 0, 0: 254, -1: 127}
    pixels = bytes(palette[value] for row in range(grid.height - 1, -1, -1)
                   for value in values[row * grid.width:(row + 1) * grid.width])
    pgm = output / "room.pgm"
    pgm.write_bytes(f"P5\n{grid.width} {grid.height}\n255\n".encode() + pixels)
    yaml = output / "room.yaml"
    yaml.write_text(f"image: {pgm.name}\nmode: trinary\nresolution: {grid.resolution}\n"
                    f"origin: [{grid.x}, {grid.y}, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n")
    return yaml, grid, values, dict(pillar=pillar, obstacle=obstacle, rig=rig[:3])


def path_cells(points, grid, step=0.025):
    """沿折线每最多 0.025 m 采一次栅格，包含端点；用于对比中心线与代价值。"""
    cells = {grid.index(*point) for point in points}
    length = 0.0
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        segment = math.hypot(bx - ax, by - ay)
        length += segment
        count = max(1, math.ceil(segment / step))
        cells.update(grid.index(ax + (bx - ax) * i / count, ay + (by - ay) * i / count) for i in range(1, count))
    return cells, length


class NavigationLab(Lab):
    def call(self, service, topic, request=None, seconds=5.0):
        client = self.node.create_client(service, topic)
        try:
            self.wait(client.service_is_ready, f"服务未就绪：{topic}", seconds)
            future = client.call_async(request if request is not None else service.Request())
            self.wait(future.done, f"服务无回应：{topic}", seconds)
            return future.result()
        finally:
            self.node.destroy_client(client)

    def state(self, name):
        from lifecycle_msgs.srv import GetState

        return self.call(GetState, name + "/get_state").current_state.label

    def transition(self, name, transition, expected):
        from lifecycle_msgs.srv import ChangeState

        request = ChangeState.Request()
        request.transition.id = transition
        reply = self.call(ChangeState, name + "/change_state", request, seconds=9.0)
        state = self.state(name)
        self.report["lifecycle"].append(dict(node=name, transition=transition, success=reply.success, state=state))
        assert reply.success and state == expected, (name, transition, state)

    def start_nav(self, package, node, *extra):
        from ament_index_python.packages import get_package_prefix

        binary = Path(get_package_prefix(package)) / "lib" / package / node
        self.start(node, [str(binary), "--ros-args", "-r", "__ns:=" + self.namespace,
                          "--params-file", str(HERE / "nav2.yaml"), *extra])
        assert self.state(node) == "unconfigured"

    def test_map(self, yaml, grid, expected, positions):
        from lifecycle_msgs.msg import Transition
        from nav2_msgs.srv import LoadMap
        from nav_msgs.msg import OccupancyGrid
        from nav_msgs.srv import GetMap
        from rclpy.qos import DurabilityPolicy, QoSProfile

        self.start_nav("nav2_map_server", "map_server", "-p", "yaml_filename:=" + str(yaml))
        self.transition("map_server", Transition.TRANSITION_CONFIGURE, "inactive")
        before = self.call(GetMap, "map_server/map").map
        assert before.info.width == 0 and len(before.data) == 0
        self.transition("map_server", Transition.TRANSITION_ACTIVATE, "active")

        # 两个订阅者均在激活之后创建，区别是是否请求瞬态本地保留的旧样本。
        retained, volatile = deque(maxlen=8), deque(maxlen=8)
        self.node.create_subscription(OccupancyGrid, "map", lambda msg: retained.append(msg),
                                      QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        late = self.node.create_subscription(OccupancyGrid, "map", lambda msg: volatile.append(msg), 1)
        self.wait(lambda: retained and late.get_publisher_count() == 1, "晚加入地图端点未就绪")
        self.observe(0.35)
        assert not volatile
        original = retained[-1]
        info = original.info
        assert original.header.frame_id == "map" and stamp(original) > 0
        assert (info.width, info.height) == (grid.width, grid.height)
        assert math.isclose(info.resolution, grid.resolution, abs_tol=1e-7)
        assert (info.origin.position.x, info.origin.position.y, info.origin.orientation.w) == (grid.x, grid.y, 1.0)
        assert list(original.data) == expected
        assert self.call(GetMap, "map_server/map").map == original
        pillar = positions["pillar"][0][:2]
        probes = [(*positions["rig"][:2], 0), (*pillar, 100), (pillar[0], -pillar[1], 0), (0.0, 0.0, 0), (3.85, 2.85, -1)]
        for x, y, value in probes:
            assert original.data[grid.index(x, y)] == value

        # 三种失败逐个对照 GetMap，避免把错误响应中的默认 map 当作新地图。
        no_image = self.output / "missing-image.yaml"
        no_image.write_text(yaml.read_text().replace("image: room.pgm", "image: nonexistent.pgm"))
        failures = []
        for case, value, code in (
            ("empty-url", "", LoadMap.Response.RESULT_MAP_DOES_NOT_EXIST),
            ("missing-yaml", str(self.output / "nonexistent.yaml"), LoadMap.Response.RESULT_INVALID_MAP_METADATA),
            ("missing-image", str(no_image), LoadMap.Response.RESULT_INVALID_MAP_DATA),
        ):
            reply = self.call(LoadMap, "map_server/load_map", LoadMap.Request(map_url=value))
            unchanged = self.call(GetMap, "map_server/map").map == original
            failures.append(dict(case=case, code=reply.result, unchanged=unchanged))
            assert reply.result == code and unchanged, failures[-1]
        self.observe(0.20)
        assert not volatile
        reply = self.call(LoadMap, "map_server/load_map", LoadMap.Request(map_url=str(yaml)))
        assert reply.result == LoadMap.Response.RESULT_SUCCESS
        assert list(reply.map.data) == expected and stamp(reply.map) > stamp(original)
        self.wait(lambda: volatile and volatile[-1] == reply.map, "易失订阅未收到后续成功发布")
        self.report["map"] = dict(frame=original.header.frame_id, size=[grid.width, grid.height],
                                  originM=[grid.x, grid.y], resolutionM=info.resolution,
                                  cells=dict(Counter(expected)), probes=probes, checkedCells=len(expected),
                                  inactiveCells=len(before.data), lateTransientLocal=True, lateVolatileBeforeReload=0,
                                  volatileAfterReload=len(volatile), failedLoads=failures, reloadCode=reply.result,
                                  mapStampNs=stamp(original), reloadedStampNs=stamp(reply.map),
                                  files={name: sha(self.output / name) for name in ("room.pgm", "room.yaml")})

    def localize(self, buffer, positions, scans):
        from geometry_msgs.msg import PoseWithCovarianceStamped
        from lifecycle_msgs.msg import Transition
        from nav2_msgs.srv import SetInitialPose
        from rclpy.time import Time
        from std_srvs.srv import Empty

        poses = deque(maxlen=32)
        self.node.create_subscription(PoseWithCovarianceStamped, "amcl_pose", lambda msg: poses.append(msg), 10)
        self.start_nav("nav2_amcl", "amcl")
        self.transition("amcl", Transition.TRANSITION_CONFIGURE, "inactive")
        self.transition("amcl", Transition.TRANSITION_ACTIVATE, "active")
        self.wait(lambda: any(info.node_name == "amcl" for info in self.node.get_subscriptions_info_by_topic(
            self.namespace + "/scan")), "AMCL 未订阅实际扫描")
        x, y = positions["rig"][:2]

        def send_initial(frame):
            request = SetInitialPose.Request()
            request.pose.header.frame_id = frame
            request.pose.header.stamp = self.node.get_clock().now().to_msg()
            request.pose.pose.pose.position.x, request.pose.pose.pose.position.y = x, y
            request.pose.pose.pose.orientation.w = 1.0
            # x/y 为 m²、偏航为 rad²。较小协方差表达已知台架位置，并非全局重定位。
            for index in (0, 7, 35):
                request.pose.pose.covariance[index] = 0.0025
            self.call(SetInitialPose, "set_initial_pose", request)

        wrong_window_start = stamp(scans[-1])
        send_initial("odom")
        self.wait(lambda: stamp(scans[-1]) >= wrong_window_start + 300_000_000, "错误坐标帧窗口内无新扫描")
        assert not poses and not buffer.can_transform("map", "base_link", Time())
        wrong_window_end = stamp(scans[-1])
        send_initial("map")
        self.wait(lambda: poses and buffer.can_transform("map", "base_link", Time()), "AMCL 未输出地图位姿和 TF", 9.0)
        update_start = stamp(poses[-1])
        self.call(Empty, "request_nomotion_update")
        self.wait(lambda: stamp(poses[-1]) > update_start, "无运动更新后未收到新位姿")
        pose = poses[-1]
        state = pose.pose.pose
        q = state.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        error = math.hypot(state.position.x - x, state.position.y - y)
        assert pose.header.frame_id == "map" and error < 0.15 and abs(yaw) < 0.20
        assert abs(math.sqrt(q.x**2 + q.y**2 + q.z**2 + q.w**2) - 1.0) < 1e-6
        self.wait(lambda: buffer.can_transform("map", "laser_link", Time.from_msg(scans[-2].header.stamp)),
                  "按真实扫描时刻查不到 map 到激光的 TF")
        sampled_scan = scans[-2]
        at_scan = buffer.lookup_transform("map", "laser_link", Time.from_msg(sampled_scan.header.stamp))
        latest = buffer.lookup_transform("map", "base_link", Time())
        parents = {topic: [info.node_name for info in self.node.get_publishers_info_by_topic(topic)]
                   for topic in ("/tf", "/tf_static")}
        assert parents == {"/tf": ["amcl"], "/tf_static": ["nav_probe"]}, parents
        self.report["amcl"] = dict(wrongFrame="odom", wrongFrameServiceReplied=True, wrongFramePoseSamples=0,
                                   wrongFrameMapToBase=False, wrongFrameScanWindowS=(wrong_window_end - wrong_window_start) / 1e9,
                                   validFrame="map", initialM=[x, y], covarianceDiag=[0.0025] * 3,
                                   positionM=[state.position.x, state.position.y], yawRad=yaw, errorM=error,
                                   initialUpdateStampNs=update_start, noMotionUpdateStampNs=stamp(pose),
                                   transformStampNs=stamp(latest), scanLookupStampNs=stamp(sampled_scan),
                                   laserOriginAtScanM=[at_scan.transform.translation.x, at_scan.transform.translation.y,
                                                       at_scan.transform.translation.z], tfPublishers=parents)
        return latest

    def plan(self, grid, positions, localized):
        from action_msgs.msg import GoalStatus
        from geometry_msgs.msg import PoseStamped
        from lifecycle_msgs.msg import Transition
        from nav2_msgs.action import ComputePathToPose
        from nav2_msgs.srv import GetCostmap, IsPathValid
        from rcl_interfaces.srv import GetParameters, SetParameters
        from rclpy.action import ActionClient
        from rclpy.parameter import Parameter

        # 内部节点还有一层命名空间。用限定节点名的 remap 让两条输入接回台架所在命名空间。
        remaps = [part for topic in ("map", "scan") for part in ("-r", f"global_costmap:{topic}:={self.namespace}/{topic}")]
        self.start_nav("nav2_planner", "planner_server", *remaps)
        self.transition("planner_server", Transition.TRANSITION_CONFIGURE, "inactive")
        self.transition("planner_server", Transition.TRANSITION_ACTIVATE, "active")
        costmap_ns = "global_costmap"
        input_topics = {key: self.namespace + "/" + key for key in ("map", "scan")}
        for topic in input_topics.values():
            self.wait(lambda: any(info.node_name == "global_costmap" and info.node_namespace == self.namespace + "/" + costmap_ns
                                  for info in self.node.get_subscriptions_info_by_topic(topic)), f"代价地图未订阅 {topic}")

        def snapshot():
            message = self.call(GetCostmap, costmap_ns + "/get_costmap").map
            meta = message.metadata
            return message, Grid(meta.size_x, meta.size_y, meta.resolution, meta.origin.position.x, meta.origin.position.y)

        pillar = positions["pillar"][0][:2]
        obstacle, size = positions["obstacle"]
        goal_xy = (2.35, 0.0)
        outside_unknown = (3.85, 2.85)
        static, actual_grid = snapshot()
        assert (actual_grid.width, actual_grid.height) == (grid.width, grid.height)
        assert (actual_grid.x, actual_grid.y) == (grid.x, grid.y)
        assert math.isclose(actual_grid.resolution, grid.resolution, abs_tol=1e-7)
        assert static.header.frame_id == "map" and static.metadata.layer == "master"
        assert static.data[actual_grid.index(*pillar)] == LETHAL
        assert static.data[actual_grid.index(*outside_unknown)] == UNKNOWN
        assert static.data[actual_grid.index(*obstacle[:2])] == 0

        action = ActionClient(self.node, ComputePathToPose, "compute_path_to_pose")
        self.wait(action.server_is_ready, "ComputePathToPose 未就绪")
        self.report["actions"] = {}
        start_xy = (localized.transform.translation.x, localized.transform.translation.y)

        def pose(xy, frame):
            message = PoseStamped()
            message.header.frame_id = frame
            message.header.stamp = self.node.get_clock().now().to_msg()
            message.pose.position.x, message.pose.position.y = xy
            message.pose.orientation.w = 1.0
            return message

        def compute(case, xy, code=0, use_start=True, plugin="GridBased", frame="map"):
            request = ComputePathToPose.Goal(goal=pose(xy, frame), planner_id=plugin, use_start=use_start)
            if use_start:
                request.start = pose(start_xy, "map")
            future = action.send_goal_async(request)
            self.wait(future.done, f"规划目标无接受回执：{case}")
            handle = future.result()
            assert handle.accepted, case
            terminal = handle.get_result_async()
            self.wait(terminal.done, f"规划目标无终态：{case}")
            result = terminal.result()
            path = result.result.path
            points = [(item.pose.position.x, item.pose.position.y) for item in path.poses]
            cells, length = path_cells(points, actual_grid)
            self.report["actions"][case] = dict(goalM=xy, goalFrame=frame, plugin=plugin, useStart=use_start,
                                                explicitStartM=start_xy if use_start else None, accepted=True,
                                                status=result.status, code=result.result.error_code, error=result.result.error_msg,
                                                pathFrame=path.header.frame_id, planningNs=ns(result.result.planning_time),
                                                pathStampNs=stamp(path), poseCount=len(points), pointsM=points, lengthM=length)
            assert result.result.error_code == code, (case, result.status, result.result.error_code, result.result.error_msg)
            if code == 0:
                assert result.status == GoalStatus.STATUS_SUCCEEDED and path.header.frame_id == "map"
                assert len(points) > 2 and math.dist(points[0], start_xy) < 0.20 and math.dist(points[-1], xy) < 0.08
            else:
                assert result.status == GoalStatus.STATUS_ABORTED and not points
            return path, cells

        def is_valid(path):
            return self.call(IsPathValid, "is_path_valid", IsPathValid.Request(path=path)).is_valid

        compute("from-tf", goal_xy, use_start=False)
        before_path, before_cells = compute("static", goal_xy)
        before_valid = is_valid(before_path)
        assert before_valid
        result = ComputePathToPose.Result
        compute("occupied", pillar, result.GOAL_OCCUPIED)
        compute("outside", (4.60, 0.0), result.GOAL_OUTSIDE_MAP)
        compute("unknown", outside_unknown, result.NO_VALID_PATH)
        compute("bad-planner", goal_xy, result.INVALID_PLANNER, plugin="NotConfigured")
        compute("bad-frame", goal_xy, result.TF_ERROR, frame="missing_goal_frame")

        # 参数回执、代价改变、同一起终点的新路径是三个独立检查。
        param_name = "obstacle_layer.enabled"
        param_ns = costmap_ns + "/global_costmap"
        request = GetParameters.Request(names=[param_name])
        assert not self.call(GetParameters, param_ns + "/get_parameters", request).values[0].bool_value
        enabled = Parameter(param_name, value=True).to_parameter_msg()
        reply = self.call(SetParameters, param_ns + "/set_parameters", SetParameters.Request(parameters=[enabled]))
        assert reply.results[0].successful
        assert self.call(GetParameters, param_ns + "/get_parameters", request).values[0].bool_value

        def new_marks(message):
            result = set()
            for i, value in enumerate(message.data):
                if value == LETHAL and static.data[i] != LETHAL:
                    x, y = actual_grid.center(i)
                    # 包围盒外加 0.15 m，允许栅格化和固定台架 AMCL 的小残差。
                    if abs(x - obstacle[0]) < size[0] / 2 + 0.15 and abs(y - obstacle[1]) < size[1] / 2 + 0.15:
                        result.add(i)
            return result

        end = time.monotonic() + 5.0
        while True:
            marked, updated_grid = snapshot()
            assert updated_grid == actual_grid
            added = new_marks(marked)
            if added:
                break
            if time.monotonic() >= end:
                raise TimeoutError("参数生效后未见运行期障碍的致命代价值")
            self.observe(0.10)
        # 给静止场景的代价地图再一个更新窗口，然后以读到的主图做验算。
        self.observe(0.30)
        marked, updated_grid = snapshot()
        assert updated_grid == actual_grid
        added = new_marks(marked)
        old_valid = is_valid(before_path)
        after_path, after_cells = compute("marked", goal_xy)
        new_valid = is_valid(after_path)
        hits = sorted(before_cells & added)
        after_lethal = sorted(i for i in after_cells if marked.data[i] in (LETHAL, INSCRIBED, UNKNOWN))
        assert hits and not old_valid and new_valid and not after_lethal, (hits, old_valid, new_valid, after_lethal)
        assert self.report["actions"]["marked"]["lengthM"] > self.report["actions"]["static"]["lengthM"]
        self.report["costmap"] = dict(frame=static.header.frame_id, layer=static.metadata.layer, inputs=input_topics,
                                      service=self.namespace + "/" + costmap_ns + "/get_costmap",
                                      originM=[actual_grid.x, actual_grid.y], resolutionM=actual_grid.resolution,
                                      size=[actual_grid.width, actual_grid.height], goalM=goal_xy, frozenStartM=start_xy,
                                      obstacleCenterM=obstacle[:2], obstacleSizeM=size[:2], addedLethalCellIndices=sorted(added),
                                      oldPathNewLethalCellIndices=hits, detourRejectedCells=after_lethal,
                                      isPathValid=dict(static=before_valid, oldAfterMarking=old_valid, detour=new_valid),
                                      sampledStepM=0.025, snapshots={})
        for label, message in (("static", static), ("marked", marked)):
            file = self.output / (label + ".raw")
            file.write_bytes(bytes(message.data))
            self.report["costmap"]["snapshots"][label] = dict(file=file.name, sha256=sha(file),
                valueCounts=dict(Counter(message.data)), sampleStampNs=stamp(message))
        action.destroy()

    def run(self, egl_vendor):
        from ament_index_python.packages import get_package_prefix
        from geometry_msgs.msg import TransformStamped
        from lifecycle_msgs.msg import Transition
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.parameter import Parameter
        from rclpy.qos import qos_profile_sensor_data
        from rclpy.signals import SignalHandlerOptions
        from sensor_msgs.msg import LaserScan
        from tf2_ros import Buffer, StaticTransformBroadcaster, TransformListener

        yaml, grid, truth, positions = build_map(self.output)
        self.report["geometry"] = positions
        self.report["versions"]["gzSim"] = subprocess.check_output(["gz", "sim", "--version"], text=True, timeout=5).splitlines()[0]
        for package in ("ros_gz_bridge", "nav2_map_server", "nav2_amcl", "nav2_planner", "nav2_costmap_2d", "nav2_navfn_planner", "nav2_msgs", "rclpy"):
            manifest = Path(get_package_prefix(package)) / "share" / package / "package.xml"
            self.report["versions"][package] = ET.parse(manifest).findtext("version")
        render_env = dict(os.environ)
        if egl_vendor:
            render_env["__EGL_VENDOR_LIBRARY_FILENAMES"] = str(egl_vendor.resolve())
            render_env.pop("LIBGL_ALWAYS_SOFTWARE", None)
        self.report["eglVendor"] = render_env.get("__EGL_VENDOR_LIBRARY_FILENAMES")
        self.start("gazebo", ["gz", "sim", "-s", "-r", "--headless-rendering", "-v", "4", str(HERE / "nav_room.sdf")], render_env)
        bridge = Path(get_package_prefix("ros_gz_bridge")) / "lib/ros_gz_bridge/parameter_bridge"
        self.start("bridge", [str(bridge), "--ros-args", "-r", "__ns:=" + self.namespace, "-r", "__node:=nav_bridge",
                              "-p", "config_file:=" + str(HERE / "bridge.yaml"), "-p", "override_timestamps_with_wall_time:=false"])
        self.context = Context()
        rclpy.init(context=self.context, signal_handler_options=SignalHandlerOptions.NO)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.node = Node("nav_probe", namespace=self.namespace, context=self.context,
                         parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.executor.add_node(self.node)
        scans = deque(maxlen=80)
        self.node.create_subscription(LaserScan, "scan", lambda msg: scans.append(msg), qos_profile_sensor_data)
        buffer = Buffer()
        listener = TransformListener(buffer, self.node, spin_thread=False)
        broadcaster = StaticTransformBroadcaster(self.node)
        transforms = []
        # 在本台架中 odom 只定义为固定的车体局部原点。map→odom 由 AMCL 独自输出。
        for parent, child, z in (("odom", "base_link", 0.0), ("base_link", "laser_link", positions["rig"][2])):
            transform = TransformStamped()
            transform.header.frame_id, transform.child_frame_id = parent, child
            transform.transform.translation.z, transform.transform.rotation.w = z, 1.0
            transforms.append(transform)
        broadcaster.sendTransform(transforms)
        self.wait(lambda: len(scans) >= 3 and self.node.get_clock().now().nanoseconds > 0, "未收到 Gazebo 时钟与三帧实际扫描", 16.0)
        scan = scans[-1]
        assert scan.header.frame_id == "laser_link" and len(scan.ranges) == 361 and stamp(scan) > stamp(scans[-2])
        obstacle, size = positions["obstacle"]
        expected = obstacle[0] - size[0] / 2 - positions["rig"][0]
        assert math.isclose(scan.ranges[180], expected, abs_tol=0.03)
        assert abs(scan.angle_min + scan.angle_increment * 180) < 1e-5
        clocks = self.node.get_publishers_info_by_topic("/clock")
        endpoints = self.node.get_publishers_info_by_topic(self.namespace + "/scan")
        assert [endpoint.node_name for endpoint in clocks] == ["nav_bridge"]
        assert len(endpoints) == 1 and endpoints[0].node_name == "nav_bridge"
        assert endpoints[0].qos_profile.reliability.name == "BEST_EFFORT"
        self.report["scan"] = dict(frame=scan.header.frame_id, stampNs=stamp(scan), beams=len(scan.ranges),
                                   finiteRanges=sum(map(math.isfinite, scan.ranges)), centerRangeM=scan.ranges[180],
                                   expectedRangeM=expected, frameStepS=(stamp(scan) - stamp(scans[-2])) / 1e9,
                                   clockPublishers=[endpoint.node_name for endpoint in clocks], reliability="BEST_EFFORT")
        self.test_map(yaml, grid, truth, positions)
        localized = self.localize(buffer, positions, scans)
        self.plan(grid, positions, localized)
        for name in ("planner_server", "amcl", "map_server"):
            self.transition(name, Transition.TRANSITION_DEACTIVATE, "inactive")
            self.transition(name, Transition.TRANSITION_CLEANUP, "unconfigured")
        listener.unregister()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-id", type=int, default=229, help="空闲的本机 DDS 域，范围 1..232")
    parser.add_argument("--egl-vendor-json", type=Path, help="为本次 Gazebo 进程选择可用的 EGL vendor")
    parser.add_argument("--report", type=Path, help="将报告另写到尚不存在的文件")
    args = parser.parse_args()
    if not 1 <= args.domain_id <= 232 or args.report and args.report.exists() or args.egl_vendor_json and not args.egl_vendor_json.is_file():
        parser.error("请检查 DDS 域、报告路径和 EGL vendor 文件")
    if os.environ.get("ROS_DISTRO") != "jazzy":
        raise SystemExit("请先加载 ROS 2 Jazzy。")
    output = Path(tempfile.mkdtemp(prefix="ros2-nav2-lab-"))
    (output / "fuel").mkdir()
    suffix = output.name.rsplit("-", 1)[-1]
    # DDS 与 Gazebo Transport 分别隔离。只读本地几何，路径和日志写临时目录。
    for key in ("ROS_LOCALHOST_ONLY", "ROS_STATIC_PEERS", "ROS_DISCOVERY_SERVER", "FASTDDS_DEFAULT_PROFILES_FILE",
                "FASTRTPS_DEFAULT_PROFILES_FILE", "GZ_RELAY"):
        os.environ.pop(key, None)
    os.environ.update(ROS_DOMAIN_ID=str(args.domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
                      RMW_IMPLEMENTATION="rmw_fastrtps_cpp", SKIP_DEFAULT_XML="1",
                      ROS_LOG_DIR=str(output / "ros-log"), ROS_HOME=str(output / "ros-home"),
                      GZ_PARTITION="hub_nav_" + suffix, GZ_IP="127.0.0.1",
                      GZ_FUEL_CACHE_PATH=str(output / "fuel"), MESA_SHADER_CACHE_DISABLE="true")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    files = [*(HERE / name for name in ("validate_nav2.py", "nav_room.sdf", "bridge.yaml", "nav2.yaml")),
             EXAMPLES / "gazebo_labs/validate_sensors.py"]
    report = dict(passed=False, domainId=args.domain_id, discovery="LOCALHOST", output=str(output),
                  namespace="/navlab_" + suffix, gazeboPartition=os.environ["GZ_PARTITION"], versions={},
                  sourceHashes={path.relative_to(EXAMPLES).as_posix(): sha(path) for path in files}, lifecycle=[], processes=[])
    lab = NavigationLab(output, report)
    lab.namespace = report["namespace"]
    lab.deadline = time.monotonic() + 75.0
    try:
        lab.run(args.egl_vendor_json)
    except (Exception, KeyboardInterrupt):
        report["error"] = traceback.format_exc()
        print(report["error"], end="")
    finally:
        lab.close()
    report["passed"] = ("error" not in report and len(report["processes"]) == 5 and
                        all(p["returnCode"] == 0 and p["pidGone"] and p["signals"] == ["SIGINT"] for p in report["processes"]))
    data = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    (output / "report.json").write_text(data)
    if args.report:
        with args.report.open("x") as target:
            target.write(data)
    print(json.dumps(dict(passed=report["passed"], report=str(output / "report.json")), ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
