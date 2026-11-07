#!/usr/bin/env python3
"""运行 Gazebo 扫描采集、Jazzy SLAM 建图、栅格重载和位姿图恢复。

输入为同包世界、采集路线及桥接和 SLAM 参数。输出为 /tmp 中的原始扫描、
实际栅格、PGM/YAML、位姿图对、日志及 JSON。坐标用 m/rad，消息戳用仿真 ns，
等待上界用单调秒。采集和回放分别用时钟；回放 odom 加入确定的教学偏差。
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
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
from nav2_labs.validate_nav2 import Grid, NavigationLab, sha
from scan_run import capture, route, stamp, yaw, yaw_error

NANO = 10**9
TF_ALLOWANCE_NS = 200_000_000


def grid_bytes(message):
    """将 ROS 有符号占据值按原位压成字节，未知格 -1 保存为 255。"""
    return bytes(value & 0xff for value in message.data)


def grid_info(message):
    info = message.info
    return Grid(info.width, info.height, info.resolution, info.origin.position.x, info.origin.position.y)


def summarize_grid(message):
    grid = grid_info(message)
    values = grid_bytes(message)
    assert message.header.frame_id == "map" and len(values) == grid.width * grid.height > 0
    assert set(values) <= {0, 100, 255}
    assert math.isclose(grid.resolution, 0.05, abs_tol=1e-7)
    assert math.isclose(message.info.origin.orientation.w, 1.0, abs_tol=1e-9)
    return dict(frame="map", stampNs=stamp(message), size=[grid.width, grid.height],
                originM=[grid.x, grid.y], resolutionM=grid.resolution,
                cells={str(-1 if value == 255 else value): count for value, count in Counter(values).items()},
                dataSha256=hashlib.sha256(values).hexdigest())


def compare_grids(left, right):
    """比较尺寸、分辨率、原点和同索引占据值，不把新消息头算作数据差异。"""
    a, b = grid_info(left), grid_info(right)
    assert (a.width, a.height) == (b.width, b.height), (a, b)
    assert math.isclose(a.resolution, b.resolution, abs_tol=1e-7)
    shift = math.hypot(a.x - b.x, a.y - b.y)
    assert shift < 0.01 * a.resolution, shift
    changed = sum(x != y for x, y in zip(left.data, right.data, strict=True))
    return dict(cells=len(left.data), changedCells=changed, originDeltaM=shift)


def graph_snapshot(message):
    """使用 SLAM 发布的 MarkerArray，节点按 ID 排序，线列表两个点代表一条约束。"""
    nodes = sorted((m.id, m.pose.position.x, m.pose.position.y, bool(m.color.g > 0.5))
                   for m in message.markers if m.ns == "slam_toolbox" and m.action == 0)
    edges = {}
    for marker in message.markers:
        if marker.ns == "slam_toolbox_edges" and marker.action == 0:
            assert len(marker.points) % 2 == 0
            edges[marker.id] = len(marker.points) // 2
    return dict(nodes=len(nodes), mappingNodes=sum(not localized for _, _, _, localized in nodes),
                localizationNodes=sum(localized for _, _, _, localized in nodes),
                mappingEdges=edges.get(0, 0), localizationEdges=edges.get(1, 0), positionsM=nodes)


class MappingLab(NavigationLab):
    def start_ros(self, package, executable, name, *extra):
        from ament_index_python.packages import get_package_prefix

        binary = Path(get_package_prefix(package)) / "lib" / package / executable
        self.start(name, [str(binary), "--ros-args", "-r", "__ns:=" + self.namespace, "-r", "__node:=" + name,
                          "-r", "/clock:=" + self.namespace + "/replay_clock", *extra])
        assert self.state(name) == "unconfigured"
        self.wait(lambda: any(info.node_name == name for info in self.node.get_subscriptions_info_by_topic(
            self.namespace + "/replay_clock")), f"{name} 尚未接入回放钟")
        if self.play_ns:
            self.set_clock(self.play_ns + 5_000_000)

    def activate(self, name):
        from lifecycle_msgs.msg import Transition

        self.transition(name, Transition.TRANSITION_CONFIGURE, "inactive")
        self.transition(name, Transition.TRANSITION_ACTIVATE, "active")

    def retire(self, name):
        from lifecycle_msgs.msg import Transition

        self.transition(name, Transition.TRANSITION_DEACTIVATE, "inactive")
        self.transition(name, Transition.TRANSITION_CLEANUP, "unconfigured")

    @staticmethod
    def time_msg(nanoseconds):
        from builtin_interfaces.msg import Time

        return Time(sec=nanoseconds // NANO, nanosec=nanoseconds % NANO)

    def set_clock(self, nanoseconds):
        from rosgraph_msgs.msg import Clock

        assert nanoseconds > self.play_ns, (nanoseconds, self.play_ns)
        self.play_ns = nanoseconds
        self.clock_pub.publish(Clock(clock=self.time_msg(nanoseconds)))

    def emit(self, sample, expected, offset_ns=0, frame="laser_link"):
        """先供钟和按时戳的局部 TF，再发布一条真实扫描。正例以对应 Pose 作为处理确认。"""
        from geometry_msgs.msg import TransformStamped
        from rclpy.time import Time
        from sensor_msgs.msg import LaserScan

        when = sample["stampNs"] + offset_ns
        self.set_clock(when)
        x, y, theta = sample["truth"]
        # 只给局部里程计的 x 和偏航加入已知漂移。Gazebo 参考坐标单独保存。
        x += 0.014 * sample["distanceM"]
        theta += 0.002 * sample["distanceM"]
        tf = TransformStamped()
        tf.header.frame_id, tf.child_frame_id = "odom", "base_link"
        tf.header.stamp = self.time_msg(when)
        tf.transform.translation.x, tf.transform.translation.y = x, y
        tf.transform.rotation.z, tf.transform.rotation.w = math.sin(theta / 2), math.cos(theta / 2)
        self.odom_tf.sendTransform(tf)
        self.wait(lambda: self.buffer.can_transform("odom", "laser_link", Time.from_msg(tf.header.stamp)),
                  "回放激光在采集时戳的局部 TF 尚未就绪")
        scan = LaserScan()
        scan.header.frame_id, scan.header.stamp = frame, tf.header.stamp
        scan.angle_min, scan.angle_max, scan.angle_increment = sample["angleMin"], sample["angleMax"], sample["angleIncrement"]
        scan.range_min, scan.range_max = sample["rangeMin"], sample["rangeMax"]
        scan.time_increment, scan.scan_time, scan.ranges = sample["timeIncrement"], sample["scanTime"], sample["ranges"]
        self.scan_pub.publish(scan)

        def received():
            return next((pose for pose in reversed(self.poses) if stamp(pose) == when), None)

        row = dict(sample=sample["index"], captureNs=sample["stampNs"], replayNs=when, frame=frame,
                   truth=sample["truth"], odom=[x, y, theta], acceptedPose=False)
        if expected:
            self.wait(received, f"第 {sample['index']} 帧未产生 SLAM 位姿", seconds=4.0)
            msg = received()
            pose = msg.pose.pose
            position = [pose.position.x, pose.position.y, yaw(pose.orientation)]
            assert msg.header.frame_id == "map" and all(map(math.isfinite, position))
            row.update(acceptedPose=True, estimated=position,
                       positionErrorM=math.dist(position[:2], sample["truth"][:2]),
                       yawErrorRad=yaw_error(position[2], sample["truth"][2]))
        else:
            self.observe(0.12)
            assert received() is None, row
        return row

    def require_map(self, expected_stamp):
        from nav_msgs.srv import GetMap

        # scan_header 会先于建图线程改变。处理回执之后再等一次地图发布，避免使用早一轮的栅格。
        self.maps.clear()
        self.wait(lambda: self.maps and self.maps[-1].info.width > 0 and stamp(self.maps[-1]) == expected_stamp,
                  "没有收到当前扫描对应的地图", seconds=7.0)
        result = self.call(GetMap, "slam_toolbox/dynamic_map").map
        assert stamp(result) == expected_stamp and grid_bytes(result) == grid_bytes(self.maps[-1])
        return result

    def start_mapper(self, name, localization=False):
        executable = "localization_slam_toolbox_node" if localization else "sync_slam_toolbox_node"
        args = ["--params-file", str(HERE / "slam.yaml")]
        if localization:
            args.extend(["-p", "mode:=localization", "-p", "use_map_saver:=false"])
        self.start_ros("slam_toolbox", executable, name, *args)
        self.maps.clear()
        self.graphs.clear()
        self.activate(name)
        self.wait(lambda: self.scan_pub.get_subscription_count() == 1, "SLAM 实际扫描订阅未就绪")
        self.wait(lambda: [info.node_name for info in self.node.get_publishers_info_by_topic(self.namespace + "/map")] == [name],
                  "地图发布者未切换为本阶段节点")

    def verify_graph(self, nodes, require_mapping=True):
        self.wait(lambda: self.graphs and graph_snapshot(self.graphs[-1])["nodes"] >= nodes,
                  "未收到预期的实际位姿图节点", seconds=6.0)
        graph = graph_snapshot(self.graphs[-1])
        assert graph["nodes"] == nodes, graph
        assert graph["mappingEdges"] >= graph["mappingNodes"] - 1, graph
        if require_mapping:
            assert graph["mappingNodes"] == nodes and graph["localizationNodes"] == 0, graph
        return graph

    def inspect_geometry(self, learned):
        grid = grid_info(learned)
        free = [(-2.1, -1.35), (2.3, -1.35), (2.3, 1.05), (-2.1, 1.05)]
        observed = [[x, y, learned.data[grid.index(x, y)]] for x, y in free]
        assert all(value == 0 for _, _, value in observed), observed
        occupied = [grid.center(i) for i, value in enumerate(learned.data) if value == 100]
        checks = [("西墙内侧", -3.40, 0.0), ("北墙内侧", 0.0, 2.40), ("中央箱体前缘", -0.25, 0.0),
                  ("非对称柱南侧", 1.65, 1.20)]
        distances = [[label, x, y, min(math.hypot(x - a, y - b) for a, b in occupied)] for label, x, y in checks]
        assert max(row[-1] for row in distances) < 0.20, distances
        return dict(freeProbes=observed, nearestOccupiedM=distances)

    def save_and_reload_map(self, learned):
        from nav_msgs.srv import GetMap
        from slam_toolbox.srv import SaveMap, SerializePoseGraph

        prefix = self.output / "learned"
        save_request = SaveMap.Request()
        save_request.name.data = str(prefix)
        raster_result = self.call(SaveMap, "slam_toolbox/save_map", save_request, seconds=12.0).result
        assert raster_result == SaveMap.Response.RESULT_SUCCESS, raster_result
        graph_result = self.call(SerializePoseGraph, "slam_toolbox/serialize_map", SerializePoseGraph.Request(filename=str(prefix))).result
        assert graph_result == SerializePoseGraph.Response.RESULT_SUCCESS, graph_result
        paths = [prefix.with_suffix(ext) for ext in (".pgm", ".yaml", ".posegraph", ".data")]
        occupancy = self.output / "learned.occupancy"
        occupancy.write_bytes(grid_bytes(learned))
        assert all(path.is_file() and path.stat().st_size > 0 for path in paths)
        self.retire("mapper")

        # 新 MapServer 只得到地图 YAML，不接原来的 SLAM 节点或位姿图。
        self.start_ros("nav2_map_server", "map_server", "map_server", "-p", "use_sim_time:=true", "-p",
                       "yaml_filename:=" + str(prefix.with_suffix(".yaml")))
        self.activate("map_server")
        reloaded = self.call(GetMap, "map_server/map").map
        comparison = compare_grids(learned, reloaded)
        assert comparison["changedCells"] == 0, comparison
        self.retire("map_server")
        self.report["artifacts"] = dict(rasterServiceCode=raster_result, graphServiceCode=graph_result,
                                        mapServer=summarize_grid(reloaded), rasterCompared=comparison,
                                        files={path.name: dict(bytes=path.stat().st_size, sha256=sha(path))
                                               for path in (*paths, occupancy)})
        return prefix

    def restore_graph(self, prefix, learned, original_nodes, held_out):
        from nav_msgs.srv import GetMap
        from slam_toolbox.srv import DeserializePoseGraph, SerializePoseGraph
        from std_srvs.srv import Empty

        self.start_mapper("mapper_restored")
        get = lambda: self.call(GetMap, "slam_toolbox/dynamic_map").map
        assert get().info.width == 0

        def restore(path, mode, pose=None):
            request = DeserializePoseGraph.Request(filename=str(path), match_type=mode)
            if pose:
                request.initial_pose.x, request.initial_pose.y, request.initial_pose.theta = pose
            return self.call(DeserializePoseGraph, "slam_toolbox/deserialize_map", request, seconds=9.0)

        mode = DeserializePoseGraph.Request
        missing = restore(self.output / "missing_graph", mode.START_AT_FIRST_NODE)
        assert missing.get_fields_and_field_types() == {} and get().info.width == 0
        wrong_mode = restore(prefix, mode.LOCALIZE_AT_POSE, held_out[0]["truth"])
        assert wrong_mode.get_fields_and_field_types() == {} and get().info.width == 0
        reply = restore(prefix, mode.START_AT_FIRST_NODE)
        assert reply.get_fields_and_field_types() == {}
        self.wait(lambda: self.maps and self.maps[-1].info.width > 0, "新同步节点未由位姿图恢复地图", seconds=7.0)
        restored = get()
        comparison = compare_grids(learned, restored)
        assert comparison["changedCells"] == 0, comparison
        graph = self.verify_graph(original_nodes)
        # 同一进程尚未回放扫描。先固定恢复结果，再提供第一节点附近及新位置的扫描。
        continuation = [self.emit(row, i == 0 or i >= 4) for i, row in enumerate(held_out)]
        additions = sum(row["acceptedPose"] for row in continuation)
        continued_graph = self.verify_graph(original_nodes + additions)
        continued_map = self.require_map(continuation[-1]["replayNs"])
        continued_prefix = self.output / "continued"
        code = self.call(SerializePoseGraph, "slam_toolbox/serialize_map", SerializePoseGraph.Request(filename=str(continued_prefix))).result
        assert code == SerializePoseGraph.Response.RESULT_SUCCESS
        assert all(sha(prefix.with_suffix(ext)) != sha(continued_prefix.with_suffix(ext)) for ext in (".posegraph", ".data"))
        self.retire("mapper_restored")
        self.report["restore"] = dict(missingPrefixResponseFields=0, missingPrefixMapCells=0, wrongModeResponseFields=0,
                                      wrongModeMapCells=0, responseFields=0, matchType=mode.START_AT_FIRST_NODE,
                                      beforeReplayMap=summarize_grid(restored), compared=comparison, graph=graph,
                                      continuation=continuation, continuedMap=summarize_grid(continued_map),
                                      continuedGraph=continued_graph, continuationSaveCode=code)

        # 定位进程加载原始图。使用指定地图姿态，扫描戳整体加偏移以保持本次回放时间单调。
        self.start_mapper("localizer", localization=True)
        loc_reply = restore(prefix, mode.LOCALIZE_AT_POSE, held_out[0]["truth"])
        assert loc_reply.get_fields_and_field_types() == {}
        self.wait(lambda: self.maps and self.maps[-1].info.width > 0, "定位节点未恢复原始栅格", seconds=7.0)
        localization_map = get()
        local_comp = compare_grids(learned, localization_map)
        assert local_comp["changedCells"] == 0, local_comp
        shift = 60 * NANO
        localized = [self.emit(row, i == 0 or i >= 4, offset_ns=shift) for i, row in enumerate(held_out)]
        errors = [row["positionErrorM"] for row in localized if row["acceptedPose"]]
        assert max(errors) < 0.18, errors
        after_map = self.require_map(localized[-1]["replayNs"])
        local_count = sum(row["acceptedPose"] for row in localized)
        rolling = self.verify_graph(original_nodes + local_count, require_mapping=False)
        assert rolling["mappingNodes"] == original_nodes and rolling["localizationNodes"] == local_count
        changed = compare_grids(localization_map, after_map)
        transitions = Counter(f"{before}→{after}" for before, after in zip(localization_map.data, after_map.data, strict=True)
                              if before != after)
        assert changed["changedCells"] == sum(transitions.values())
        # 清理短期定位缓冲后重新接图。以栅格内容和标记节点对照，而不是只看空服务回执。
        self.call(Empty, "slam_toolbox/clear_localization_buffer")
        self.graphs.clear()
        cleared = self.verify_graph(original_nodes)
        cleared_map = self.require_map(localized[-1]["replayNs"])
        cleared_comp = compare_grids(learned, cleared_map)
        assert cleared_comp["changedCells"] == 0, cleared_comp
        original_files = self.report["artifacts"]["files"]
        assert all(sha(self.output / name) == original_files[name]["sha256"] for name in ("learned.posegraph", "learned.data"))
        self.retire("localizer")
        self.report["localization"] = dict(matchType=mode.LOCALIZE_AT_POSE, replayShiftNs=shift,
                                           mapBefore=summarize_grid(localization_map), loadedMapCompared=local_comp,
                                           mapWithBuffer=summarize_grid(after_map), rollingMapCompared=changed,
                                           rollingCellTransitions=dict(transitions), rollingGraph=rolling,
                                           mapAfterClear=summarize_grid(cleared_map), clearedMapCompared=cleared_comp,
                                           clearedGraph=cleared, originalGraphFilesIntact=True,
                                           poseResults=localized, maxPositionErrorM=max(errors))

    def run(self, egl_vendor):
        from ament_index_python.packages import get_package_prefix
        from geometry_msgs.msg import PoseWithCovarianceStamped, TransformStamped
        from nav_msgs.msg import OccupancyGrid
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.parameter import Parameter
        from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
        from rclpy.signals import SignalHandlerOptions
        from rclpy.time import Time
        from rosgraph_msgs.msg import Clock
        from sensor_msgs.msg import LaserScan
        from slam_toolbox.srv import SaveMap
        from tf2_msgs.msg import TFMessage
        from tf2_ros import Buffer, StaticTransformBroadcaster, TransformBroadcaster, TransformListener
        from visualization_msgs.msg import MarkerArray

        versions = self.report["versions"]
        versions["gazebo"] = subprocess.check_output(["gz", "sim", "--version"], text=True, timeout=5).splitlines()[0]
        for name in ("ros_gz_bridge", "slam_toolbox", "nav2_map_server", "rclpy"):
            versions[name] = ET.parse(Path(get_package_prefix(name)) / "share" / name / "package.xml").findtext("version")
        self.context = Context()
        rclpy.init(context=self.context, signal_handler_options=SignalHandlerOptions.NO)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.node = Node("slam_probe", namespace=self.namespace, context=self.context,
                         parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.executor.add_node(self.node)
        mapping, held_out = route()
        samples, scene, boxes, height = capture(self, egl_vendor, mapping + held_out)
        total = 0.0
        last = samples[0]
        for sample in samples:
            total += math.dist(last["truth"][:2], sample["truth"][:2])
            sample["distanceM"] = total
            last = sample
        samples_file = self.output / "trajectory.json"
        samples_file.write_text(json.dumps(dict(mappingSamples=len(mapping), geometryBoxesM=boxes, lidarHeightM=height,
                                               samples=samples), ensure_ascii=False, allow_nan=False) + "\n")
        capture_end = self.node.get_clock().now().nanoseconds
        self.report["capture"] = dict(sceneSha256=sha(scene), sampleFile=samples_file.name, sampleSha256=sha(samples_file),
                                      samples=len(samples), mappingSamples=len(mapping), heldOutSamples=len(held_out),
                                      raysPerSample=len(samples[0]["ranges"]), captureEndNs=capture_end,
                                      exactPosePairs=sum(not row["poseDeltaNs"] for row in samples),
                                      maxPairDeltaNs=max(abs(row["poseDeltaNs"]) for row in samples),
                                      maxRangeP95ErrorM=max(row["rangeP95ErrorM"] for row in samples),
                                      traveledM=samples[len(mapping)-1]["distanceM"], lidarHeightM=height)

        self.play_ns = 0
        self.clock_pub = self.node.create_publisher(Clock, "replay_clock", qos_profile_sensor_data)
        self.scan_pub = self.node.create_publisher(LaserScan, "scan", qos_profile_sensor_data)
        self.poses, self.maps, self.graphs, transforms = deque(maxlen=128), deque(maxlen=16), deque(maxlen=32), deque(maxlen=800)
        self.node.create_subscription(PoseWithCovarianceStamped, "pose", lambda msg: self.poses.append(msg), 10)
        self.node.create_subscription(OccupancyGrid, "map", lambda msg: self.maps.append(msg),
                                      QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.node.create_subscription(MarkerArray, "slam_toolbox/graph_visualization", lambda msg: self.graphs.append(msg), 10)
        self.node.create_subscription(TFMessage, "/tf", lambda msg: transforms.extend(msg.transforms), 100)
        self.buffer = Buffer()
        listener = TransformListener(self.buffer, self.node, spin_thread=False)
        self.odom_tf = TransformBroadcaster(self.node)
        extrinsics = StaticTransformBroadcaster(self.node)
        laser = TransformStamped()
        laser.header.frame_id, laser.child_frame_id = "base_link", "laser_link"
        laser.transform.translation.z, laser.transform.rotation.w = height, 1.0
        extrinsics.sendTransform(laser)

        self.start_mapper("mapper")
        early = SaveMap.Request()
        early.name.data = str(self.output / "too_early")
        empty_save = self.call(SaveMap, "slam_toolbox/save_map", early).result
        assert empty_save == SaveMap.Response.RESULT_NO_MAP_RECEIEVD
        assert not (self.output / "too_early.yaml").exists()
        invalid = self.emit(samples[0], False, offset_ns=-50_000_000, frame="unlinked_laser")
        assert not self.poses and not self.maps
        observed = [self.emit(samples[0], True)]
        initial_map = self.require_map(observed[0]["replayNs"])
        observed.extend(self.emit(row, i >= 4) for i, row in enumerate(samples[1:len(mapping)], 1))
        last = observed[-1]
        learned = self.require_map(last["replayNs"])
        geometry = self.inspect_geometry(learned)
        accepted = sum(row["acceptedPose"] for row in observed)
        graph = self.verify_graph(accepted)
        assert accepted >= 30 and last["positionErrorM"] < 0.20 and last["yawErrorRad"] < 0.15, last
        expected_tf_stamp = last["replayNs"] + TF_ALLOWANCE_NS
        self.wait(lambda: any(tf.header.frame_id == "map" and tf.child_frame_id == "odom" and
                              stamp(tf) == expected_tf_stamp for tf in transforms), "未收到对应扫描的 SLAM 全局 TF")
        when = Time.from_msg(self.time_msg(last["replayNs"]))
        self.wait(lambda: self.buffer.can_transform("map", "laser_link", when), "按扫描时刻未查到 map 到激光")
        frame = self.buffer.lookup_transform("map", "laser_link", when)
        assert abs(frame.transform.translation.z - height) < 1e-6
        assert self.node.get_clock().now().nanoseconds == capture_end
        self.report["mapping"] = dict(saveBeforeMapCode=empty_save, badFrame=invalid, poses=observed,
                                      acceptedPoses=accepted, initialMap=summarize_grid(initial_map),
                                      learnedMap=summarize_grid(learned), geometryChecks=geometry, graph=graph,
                                      transformStampNs=expected_tf_stamp, lookupStampNs=last["replayNs"],
                                      mapToLaserZ=frame.transform.translation.z, captureClockStayedNs=capture_end)
        prefix = self.save_and_reload_map(learned)
        self.restore_graph(prefix, learned, accepted, samples[len(mapping):])
        assert self.node.get_clock().now().nanoseconds == capture_end
        listener.unregister()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-id", type=int, default=231, help="未占用的本机 DDS 域，范围 1..232")
    parser.add_argument("--egl-vendor-json", type=Path, help="仅为本次 Gazebo 选择可用 EGL vendor")
    parser.add_argument("--report", type=Path, help="将报告另写到尚不存在的文件")
    args = parser.parse_args()
    if not 1 <= args.domain_id <= 232 or args.report and args.report.exists() or args.egl_vendor_json and not args.egl_vendor_json.is_file():
        parser.error("请检查 DDS 域、报告路径和 EGL vendor 文件")
    if os.environ.get("ROS_DISTRO") != "jazzy":
        raise SystemExit("请先加载 ROS 2 Jazzy。")
    output = Path(tempfile.mkdtemp(prefix="ros2-slam-lab-"))
    (output / "fuel").mkdir()
    suffix = output.name.rsplit("-", 1)[-1]
    for key in ("ROS_LOCALHOST_ONLY", "ROS_STATIC_PEERS", "ROS_DISCOVERY_SERVER", "FASTDDS_DEFAULT_PROFILES_FILE",
                "FASTRTPS_DEFAULT_PROFILES_FILE", "GZ_RELAY"):
        os.environ.pop(key, None)
    os.environ.update(ROS_DOMAIN_ID=str(args.domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
                      RMW_IMPLEMENTATION="rmw_fastrtps_cpp", SKIP_DEFAULT_XML="1", ROS_HOME=str(output / "ros-home"),
                      ROS_LOG_DIR=str(output / "ros-log"), GZ_PARTITION="hub_slam_" + suffix, GZ_IP="127.0.0.1",
                      GZ_FUEL_CACHE_PATH=str(output / "fuel"), MESA_SHADER_CACHE_DISABLE="true")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    files = [*("slam_labs/" + file for file in ("validate_slam.py", "scan_run.py", "slam.yaml", "bridge.yaml")),
             "nav2_labs/nav_room.sdf", "nav2_labs/validate_nav2.py", "gazebo_labs/validate_sensors.py"]
    report = dict(passed=False, domainId=args.domain_id, discovery="LOCALHOST", output=str(output),
                  namespace="/slamlab_" + suffix, gazeboPartition=os.environ["GZ_PARTITION"], versions={}, lifecycle=[],
                  sourceHashes={name: sha(EXAMPLES / name) for name in files}, processes=[])
    lab = MappingLab(output, report)
    lab.namespace = report["namespace"]
    lab.deadline = time.monotonic() + 130.0
    try:
        lab.run(args.egl_vendor_json)
    except (Exception, KeyboardInterrupt):
        report["error"] = traceback.format_exc()
        print(report["error"], end="")
    finally:
        lab.close()
    report["passed"] = ("error" not in report and len(report["processes"]) == 6 and
                        all(p["returnCode"] == 0 and p["pidGone"] and p["signals"] == ["SIGINT"] for p in report["processes"]))
    result = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    (output / "report.json").write_text(result)
    if args.report:
        with args.report.open("x") as target:
            target.write(result)
    print(json.dumps(dict(passed=report["passed"], report=str(output / "report.json")), ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
