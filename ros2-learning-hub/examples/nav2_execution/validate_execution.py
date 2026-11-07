#!/usr/bin/env python3
"""在本机隔离仿真中运行完整 NavigateToPose 行为树与差速底盘反馈链。

输入为上一轮同场景的地图 YAML、PGM 和可选的原始占据数组，以及本目录的 SDF 和配置。
输出为临时目录内的世界、实测轨迹、两级速度、轮反馈、行为树事件、Action 回执与日志。
时间戳为 ns，位姿用 m 与 rad。等待使用单调墙钟，停稳判据使用实际仿真样本。
"""
from __future__ import annotations

import argparse
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
from nav2_labs.validate_nav2 import Grid, NavigationLab, ns, sha, stamp

NANO = 1_000_000_000
POSITION_TOLERANCE_M = 0.27
STILL_LINEAR_MPS = 0.018
STILL_ANGULAR_RADPS = 0.055
STILL_WINDOW_NS = 500_000_000
WHEEL_NAMES = ("left_wheel_joint", "right_wheel_joint")


def yaw(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def yaw_error(a, b):
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


def prepare_scene(output):
    """取固定台架的六个盒形障碍，换成双驱动轮车辆并添加地面。原始 SDF 只读。"""
    source = ET.parse(EXAMPLES / "nav2_labs/nav_room.sdf")
    world = source.find("world")
    world.set("name", "hub_navigation_execution")
    world.remove(world.find("model[@name='scan_rig']"))
    boxes = []
    for model in world.findall("model"):
        x, y, _, roll, pitch, angle = map(float, model.findtext("pose").split())
        assert roll == pitch == angle == 0.0
        sx, sy, _ = map(float, model.findtext("link/collision/geometry/box/size").split())
        boxes.append([x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2])
    world.append(ET.fromstring("""
      <model name="floor"><static>true</static><link name="floor_link">
        <collision name="surface"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry></collision>
        <visual name="surface"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry></visual>
      </link></model>"""))
    mobile = ET.parse(HERE / "mobile_base.sdf").find("model")
    world.append(mobile)
    scene = output / "navigation_room.sdf"
    source.write(scene, encoding="utf-8", xml_declaration=True)
    start = tuple(map(float, mobile.findtext("pose").split()))
    mount = tuple(map(float, mobile.findtext("link/sensor/pose").split()))
    # 安装 TF 在 ROS 发布。这个模型的传感器方向与基座一致。
    assert start[3:5] == (0.0, 0.0) and mount[3:] == (0.0, 0.0, 0.0)
    return scene, boxes, (start[0], start[1], start[5]), mount[:3]


def map_input(path):
    """将输入限制为本地 PGM/YAML。可选原始栅格用于逐格比对。"""
    import yaml

    info = yaml.safe_load(path.read_text())
    image = (path.parent / info["image"]).resolve(strict=True)
    if image.parent != path.parent or image.suffix.lower() != ".pgm" or info["mode"] != "trinary":
        raise ValueError("本实验需要同一目录中的 Trinary 地图 YAML 和 PGM。")
    if len(info["origin"]) != 3 or info["origin"][2] != 0:
        raise ValueError("本实验使用与房间轴向对齐的地图。")
    raw = path.with_suffix(".occupancy")
    files = {file.name: sha(file) for file in (path, image)}
    if raw.is_file():
        files[raw.name] = sha(raw)
    return info, files, raw.read_bytes() if raw.is_file() else None


def clearance(point, boxes):
    """返回机器人参考点到最近轴对齐碰撞盒的平面距离，单位 m。"""
    x, y = point
    return min(math.hypot(max(x0 - x, x - x1, 0.0), max(y0 - y, y - y1, 0.0))
               for x0, x1, y0, y1 in boxes)


def xy(row):
    return row["xM"], row["yM"]


def length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def command_is_zero(row):
    return abs(row["linearMps"]) <= 1e-7 and abs(row["angularRadps"]) <= 1e-7


def still(row):
    return math.hypot(row["vxMps"], row["vyMps"]) <= STILL_LINEAR_MPS and abs(row["wRadps"]) <= STILL_ANGULAR_RADPS


class ExecutionLab(NavigationLab):
    def __init__(self, output, report):
        super().__init__(output, report)
        self.namespace = report["namespace"]
        self.deadline = time.monotonic() + 125.0
        self.trace = {name: [] for name in (
            "scans", "truth", "odometry", "wheels", "controller", "smoothed", "plans", "status", "bt", "feedback", "tf",
        )}
        self.wall_start = time.monotonic_ns()
        self.last_status = {}
        self.costmaps = {}
        self.active = []

    def now(self):
        return self.node.get_clock().now().nanoseconds

    def state(self, name):
        """发现后仍可能错过首个回执。仅在读取状态超时时再读一次。"""
        try:
            return super().state(name)
        except TimeoutError as error:
            self.report.setdefault("stateReadRetries", []).append(dict(node=name, reason=str(error)))
            return super().state(name)

    def activate_node(self, package, name, *extra):
        from ament_index_python.packages import get_package_prefix
        from lifecycle_msgs.msg import Transition

        binary = Path(get_package_prefix(package)) / "lib" / package / name
        self.start(name, [str(binary), "--ros-args", "-r", "__ns:=" + self.namespace,
                          "--params-file", str(HERE / "navigation.yaml"), *extra])
        assert self.state(name) == "unconfigured"
        self.transition(name, Transition.TRANSITION_CONFIGURE, "inactive")
        self.transition(name, Transition.TRANSITION_ACTIVATE, "active")
        self.active.append(name)

    def stop_nodes(self):
        from lifecycle_msgs.msg import Transition

        for name in reversed(self.active):
            self.transition(name, Transition.TRANSITION_DEACTIVATE, "inactive")
            self.transition(name, Transition.TRANSITION_CLEANUP, "unconfigured")

    def watch(self):
        """订阅旁路观测。速度消息没有 Header，另记接收时的 ROS 钟与单调墙钟。"""
        from action_msgs.msg import GoalStatusArray
        from geometry_msgs.msg import Twist
        from nav2_msgs.msg import BehaviorTreeLog, Costmap
        from nav_msgs.msg import Odometry, Path as RosPath
        from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
        from sensor_msgs.msg import JointState, LaserScan
        from tf2_msgs.msg import TFMessage

        def odom(name, msg):
            pose, twist = msg.pose.pose, msg.twist.twist
            values = [pose.position.x, pose.position.y, pose.position.z, yaw(pose.orientation),
                      twist.linear.x, twist.linear.y, twist.angular.z]
            assert all(map(math.isfinite, values)), name
            self.trace[name].append(dict(zip(
                ("xM", "yM", "zM", "yawRad", "vxMps", "vyMps", "wRadps"), values,
            ), stampNs=stamp(msg), frame=msg.header.frame_id, childFrame=msg.child_frame_id))

        def wheel(msg):
            rows = self.trace["wheels"]
            when = stamp(msg)
            # Gazebo 物理步频为 200 Hz。原始观测按 20 ms 采样，保持测量时戳。
            if rows and when < rows[-1]["stampNs"] + 20_000_000:
                return
            names = [name.rsplit("::", 1)[-1] for name in msg.name]
            rates = [msg.velocity[names.index(name)] for name in WHEEL_NAMES]
            assert all(map(math.isfinite, rates))
            rows.append(dict(stampNs=when, leftRadps=rates[0], rightRadps=rates[1]))

        def scan(msg):
            center = float(msg.ranges[len(msg.ranges) // 2])
            self.trace["scans"].append(dict(stampNs=stamp(msg), frame=msg.header.frame_id,
                beams=len(msg.ranges), centerRangeM=center if math.isfinite(center) else None))

        def command(name, msg):
            assert math.isfinite(msg.linear.x) and math.isfinite(msg.angular.z)
            self.trace[name].append(dict(receivedRosNs=self.now(), receivedWallNs=time.monotonic_ns() - self.wall_start,
                                          linearMps=msg.linear.x, angularRadps=msg.angular.z))

        def plan(msg):
            points = [[item.pose.position.x, item.pose.position.y] for item in msg.poses]
            if points:
                self.trace["plans"].append(dict(stampNs=stamp(msg), receivedRosNs=self.now(),
                                                 frame=msg.header.frame_id, pointsM=points))

        def status(action, msg):
            for item in msg.status_list:
                identifier = bytes(item.goal_info.goal_id.uuid).hex()
                key = (action, identifier)
                if self.last_status.get(key) != item.status:
                    self.last_status[key] = item.status
                    self.trace["status"].append(dict(action=action, uuid=identifier, status=item.status,
                        goalStampNs=ns(item.goal_info.stamp), receivedRosNs=self.now()))

        def bt(msg):
            for event in msg.event_log:
                self.trace["bt"].append(dict(publishedRosNs=ns(msg.timestamp), eventInternalNs=ns(event.timestamp),
                    name=event.node_name, uid=event.uid, previous=event.previous_status, current=event.current_status))

        def transforms(msg):
            for tf in msg.transforms:
                edge = (tf.header.frame_id, tf.child_frame_id)
                if edge in (("map", "odom"), ("odom", "base_link")):
                    self.trace["tf"].append(dict(parent=edge[0], child=edge[1], stampNs=stamp(tf), receivedRosNs=self.now()))

        self.node.create_subscription(LaserScan, "scan", scan, qos_profile_sensor_data)
        self.node.create_subscription(Odometry, "odom", lambda msg: odom("odometry", msg), qos_profile_sensor_data)
        self.node.create_subscription(Odometry, "world_pose", lambda msg: odom("truth", msg), qos_profile_sensor_data)
        self.node.create_subscription(JointState, "wheel_joints", wheel, qos_profile_sensor_data)
        self.node.create_subscription(Twist, "cmd_vel", lambda msg: command("controller", msg), 20)
        self.node.create_subscription(Twist, "cmd_vel_smoothed", lambda msg: command("smoothed", msg), 20)
        self.node.create_subscription(RosPath, "plan", plan, 10)
        self.node.create_subscription(BehaviorTreeLog, "behavior_tree_log", bt, 30)
        self.node.create_subscription(TFMessage, "/tf", transforms, 50)
        for name in ("global_costmap", "local_costmap"):
            self.node.create_subscription(Costmap, name + "/costmap_raw",
                lambda msg, name=name: self.costmaps.update({name: msg}), 10)
        history = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        for action in ("navigate_to_pose", "compute_path_to_pose", "follow_path"):
            self.node.create_subscription(GoalStatusArray, action + "/_action/status",
                lambda msg, action=action: status(action, msg), history)

    def pose(self, target, covariance=None):
        from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped

        msg = PoseWithCovarianceStamped() if covariance is not None else PoseStamped()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        p = msg.pose.pose if covariance is not None else msg.pose
        p.position.x, p.position.y = target[:2]
        p.orientation.z, p.orientation.w = math.sin(target[2] / 2.0), math.cos(target[2] / 2.0)
        if covariance is not None:
            for index in (0, 7, 35):
                msg.pose.covariance[index] = covariance
        return msg

    def start_location(self, yaml_path, start):
        from nav2_msgs.srv import SetInitialPose
        from nav_msgs.srv import GetMap
        from rclpy.time import Time

        info, files, expected = map_input(yaml_path)
        self.activate_node("nav2_map_server", "map_server", "-p", "yaml_filename:=" + str(yaml_path))
        current = self.call(GetMap, "map_server/map").map
        width, height = current.info.width, current.info.height
        position = current.info.origin.position
        raw = bytes(value & 0xff for value in current.data)
        self.grid = Grid(width, height, current.info.resolution, position.x, position.y)
        assert width > 0 and height > 0 and current.header.frame_id == "map"
        assert math.isclose(self.grid.resolution, info["resolution"], abs_tol=1e-7)
        assert math.dist((position.x, position.y), info["origin"][:2]) < 1e-8
        assert len(raw) == width * height and (expected is None or expected == raw)
        assert raw[self.grid.index(*start[:2])] == 0
        observed = self.output / "map.occupancy"
        observed.write_bytes(raw)
        self.report["map"] = dict(files=files, size=[width, height], resolutionM=self.grid.resolution,
            originM=[position.x, position.y], receivedBytes=len(raw), dataSha256=sha(observed), comparedRaw=expected is not None)

        self.activate_node("nav2_amcl", "amcl")
        # 近参考位姿供初始化，方差 0.0025 m² / rad²。AMCL 独自发布 map → odom。
        self.call(SetInitialPose, "set_initial_pose", SetInitialPose.Request(pose=self.pose(start, 0.0025)))
        self.wait(lambda: self.buffer.can_transform("map", "base_link", Time()), "AMCL 未产生全局 TF", seconds=12.0)
        t = self.buffer.lookup_transform("map", "base_link", Time()).transform.translation
        error = math.dist((t.x, t.y), start[:2])
        assert error < 0.17, error
        self.report["initialPose"] = dict(expectedM=list(start[:2]), tfM=[t.x,t.y], positionErrorM=error)

    def await_navigation_frames(self):
        """晚启动导航器时，等两条动态边在采样时戳上形成可查询的共同区间。"""
        from rclpy.time import Time

        self.wait(lambda: any(e.node_name == "bt_navigator" and e.node_namespace == self.namespace
            for e in self.node.get_subscriptions_info_by_topic("/tf")), "导航器的 TF 监听端尚未发现")
        offset = len(self.trace["tf"])

        def overlapping():
            current = self.trace["tf"][offset:]
            stamps = {parent: sorted({row["stampNs"] for row in current if row["parent"] == parent})
                      for parent in ("map", "odom")}
            if any(len(values) < 4 for values in stamps.values()):
                return None
            start = max(values[0] for values in stamps.values())
            end = min(values[-1] for values in stamps.values())
            if end - start < 100_000_000 or not self.buffer.can_transform("map", "base_link", Time(nanoseconds=end)):
                return None
            return dict(mapToOdomNs=[stamps["map"][0], stamps["map"][-1]],
                odomToBaseNs=[stamps["odom"][0], stamps["odom"][-1]], sharedRangeNs=[start, end])

        self.wait(overlapping, "导航器启动后的两条 TF 未形成共同时间窗", seconds=8.0)
        self.report["navigationTfWarmup"] = overlapping()

    def ready_motion(self, before_ns, start):
        """只有独立世界位姿显示已有平移才取消，排除原地旋转。"""
        row = self.trace["truth"][-1]
        return (row["stampNs"] > before_ns and math.dist(xy(row), xy(start)) >= 0.42
                and math.hypot(row["vxMps"], row["vyMps"]) > 0.12)

    def quiet_tail(self, after_ns):
        """选取结束之后连续符合阈值的世界位姿。返回按测量时间排序的后缀。"""
        tail = []
        for row in reversed(self.trace["truth"]):
            if row["stampNs"] < after_ns or not still(row):
                break
            tail.append(row)
        return list(reversed(tail))

    def nested(self, statuses):
        """从最近的终态 UUID 查询下级动作缓存的实际业务结果，只读且不发送目标。"""
        from nav2_msgs.action import ComputePathToPose, FollowPath
        from unique_identifier_msgs.msg import UUID

        types = {"compute_path_to_pose": ComputePathToPose, "follow_path": FollowPath}
        terminals = {}
        for event in statuses:
            if event["action"] in types and event["status"] in (4, 5, 6):
                terminals[event["action"]] = event
        results = []
        for action, event in terminals.items():
            identifier = event["uuid"]
            srv = types[action].Impl.GetResultService
            reply = self.call(srv, action + "/_action/get_result",
                srv.Request(goal_id=UUID(uuid=list(bytes.fromhex(identifier)))), seconds=3.0)
            assert reply.status == event["status"]
            results.append(dict(action=action, uuid=identifier, status=reply.status,
                                errorCode=reply.result.error_code, errorMessage=reply.result.error_msg))
        return results

    def drive_goal(self, label, target, *, cancel=False):
        from nav2_msgs.action import NavigateToPose

        stage = dict(goalM=list(target[:2]), goalYawRad=target[2], sentRosNs=self.now(), accepted=False)
        self.report["scenarios"][label] = stage
        starts = {name: len(rows) for name, rows in self.trace.items()}
        origin = self.trace["truth"][-1]

        def feedback(message):
            f = message.feedback
            position = f.current_pose.pose.position
            self.trace["feedback"].append(dict(scenario=label, uuid=bytes(message.goal_id.uuid).hex(),
                receivedRosNs=self.now(), poseStampNs=stamp(f.current_pose), frame=f.current_pose.header.frame_id,
                xM=position.x, yM=position.y, yawRad=yaw(f.current_pose.pose.orientation),
                distanceRemainingM=f.distance_remaining, navigationNs=ns(f.navigation_time),
                estimatedRemainingNs=ns(f.estimated_time_remaining), recoveries=f.number_of_recoveries))

        request = NavigateToPose.Goal(pose=self.pose(target))
        future = self.action.send_goal_async(request, feedback_callback=feedback)
        self.wait(future.done, label + " 无目标响应")
        handle = future.result()
        stage.update(accepted=handle.accepted, uuid=bytes(handle.goal_id.uuid).hex())
        assert handle.accepted, label
        result_future = handle.get_result_async()
        if cancel:
            self.wait(lambda: result_future.done() or self.ready_motion(stage["sentRosNs"], origin),
                      "取消前没有可辨认的真实平移", seconds=20.0)
            assert not result_future.done()
            stage["cancelRequestedRosNs"] = self.now()
            stage["cancelPoseM"] = list(xy(self.trace["truth"][-1]))
            reply = handle.cancel_goal_async()
            self.wait(reply.done, "无取消服务响应")
            value = reply.result()
            uuids = [bytes(info.goal_id.uuid).hex() for info in value.goals_canceling]
            stage.update(cancelAckRosNs=self.now(), cancelCode=value.return_code, cancelingIds=uuids)
            assert value.return_code == 0 and uuids == [stage["uuid"]]
        self.wait(result_future.done, label + " 无动作终态", seconds=42.0)
        result = result_future.result()
        stage.update(resultRosNs=self.now(), status=result.status, errorCode=result.result.error_code,
                     errorMessage=result.result.error_msg)
        print(label, result.status, result.result.error_code, flush=True)

        def physically_settled():
            tail = self.quiet_tail(stage["resultRosNs"])
            return len(tail) > 2 and tail[-1]["stampNs"] - tail[0]["stampNs"] >= STILL_WINDOW_NS

        self.wait(physically_settled, label + " 未在有限观测窗内停稳", seconds=5.0)
        window = self.quiet_tail(stage["resultRosNs"])
        last = window[-1]
        stage["windowEndRosNs"] = last["stampNs"]
        stage["truthStop"] = dict(stillFromNs=window[0]["stampNs"], stillUntilNs=last["stampNs"],
            samples=len(window), maxLinearMps=max(math.hypot(p["vxMps"], p["vyMps"]) for p in window),
            maxAngularRadps=max(abs(p["wRadps"]) for p in window))
        stage["endM"], stage["endYawRad"] = list(xy(last)), last["yawRad"]
        stage["positionErrorM"], stage["yawErrorRad"] = math.dist(xy(last), target[:2]), yaw_error(last["yawRad"], target[2])
        path = [xy(origin), *(xy(row) for row in self.trace["truth"][starts["truth"]:])]
        stage.update(worldTravelM=length(path), displacementM=math.dist(xy(origin), xy(last)),
                     minimumCenterClearanceM=min(clearance(p, self.boxes) for p in path))

        for stream in ("controller", "smoothed"):
            rows = self.trace[stream][starts[stream]:]
            moving = [index for index, row in enumerate(rows) if not command_is_zero(row)]
            last_active = moving[-1] if moving else -1
            zero = next((row["receivedRosNs"] for row in rows[last_active + 1:] if command_is_zero(row)), None)
            stage[stream] = dict(samples=len(rows), nonzero=len(moving), firstZeroAfterMotionNs=zero,
                maxLinearMps=max((abs(row["linearMps"]) for row in rows), default=0.0),
                maxAngularRadps=max((abs(row["angularRadps"]) for row in rows), default=0.0))

        wheel_rows = [row for row in self.trace["wheels"][starts["wheels"]:] if row["stampNs"] >= window[0]["stampNs"]]
        assert wheel_rows, label
        stage["wheelStopMaxRadps"] = max(max(abs(row["leftRadps"]), abs(row["rightRadps"])) for row in wheel_rows)
        assert stage["wheelStopMaxRadps"] < 0.20, stage["wheelStopMaxRadps"]
        stage["feedbackSamples"] = len(self.trace["feedback"][starts["feedback"]:])
        stage["recoveries"] = max((row["recoveries"] for row in self.trace["feedback"][starts["feedback"]:]), default=0)
        stage["btTransitions"] = len(self.trace["bt"][starts["bt"]:])
        stage["plans"] = len(self.trace["plans"][starts["plans"]:])
        stage["nestedResults"] = self.nested(self.trace["status"][starts["status"]:])
        if cancel:
            stage["travelAfterCancelM"] = length([tuple(stage["cancelPoseM"]), *(xy(row) for row in
                self.trace["truth"][starts["truth"]:] if row["stampNs"] >= stage["cancelRequestedRosNs"])])
        return stage

    def run(self, args):
        from ament_index_python.packages import get_package_prefix, get_package_share_directory
        from geometry_msgs.msg import TransformStamped
        from nav2_msgs.action import NavigateToPose
        import rclpy
        from rclpy.action import ActionClient
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.parameter import Parameter
        from rclpy.qos import DurabilityPolicy, QoSProfile
        from rclpy.signals import SignalHandlerOptions
        from rclpy.time import Time
        from std_msgs.msg import String
        from tf2_ros import Buffer, StaticTransformBroadcaster, TransformListener

        scene, self.boxes, start, mount = prepare_scene(self.output)
        self.report["scene"] = dict(file=scene.name, sha256=sha(scene), boxBoundsM=self.boxes, sensorOffsetM=mount)
        packages = ("ros_gz_bridge", "nav2_map_server", "nav2_amcl", "nav2_planner", "nav2_navfn_planner",
                    "nav2_controller", "nav2_regulated_pure_pursuit_controller", "nav2_velocity_smoother",
                    "nav2_behaviors", "nav2_bt_navigator", "nav2_msgs", "rclpy")
        versions = self.report["versions"]
        versions["gazebo"] = subprocess.check_output(["gz", "sim", "--version"], text=True, timeout=5).splitlines()[0]
        for package in packages:
            versions[package] = ET.parse(Path(get_package_share_directory(package)) / "package.xml").findtext("version")
        tree = Path(get_package_share_directory("nav2_bt_navigator")) / "behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml"
        self.report["behaviorTree"] = dict(file=tree.name, installedSha256=sha(tree), usesDefaultGoalField=True)

        render_env = dict(os.environ)
        if args.egl_vendor_json:
            render_env["__EGL_VENDOR_LIBRARY_FILENAMES"] = str(args.egl_vendor_json.resolve())
            render_env.pop("LIBGL_ALWAYS_SOFTWARE", None)
        self.start("gazebo", ["gz", "sim", "-s", "-r", "--headless-rendering", "-v", "3", str(scene)], render_env)
        bridge = Path(get_package_prefix("ros_gz_bridge")) / "lib/ros_gz_bridge/parameter_bridge"
        self.start("bridge", [str(bridge), "--ros-args", "-r", "__ns:=" + self.namespace, "-r", "__node:=execution_bridge",
                              "-p", "config_file:=" + str(HERE / "bridge.yaml"), "-p", "override_timestamps_with_wall_time:=false"])

        self.context = Context()
        rclpy.init(context=self.context, signal_handler_options=SignalHandlerOptions.NO)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.node = Node("execution_probe", namespace=self.namespace, context=self.context,
                         parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.executor.add_node(self.node)
        self.watch()
        self.buffer = Buffer()
        listener = TransformListener(self.buffer, self.node, spin_thread=False)
        mount_tf = TransformStamped()
        mount_tf.header.frame_id, mount_tf.child_frame_id = "base_link", "laser_link"
        mount_tf.transform.translation.x, mount_tf.transform.translation.y, mount_tf.transform.translation.z = mount
        mount_tf.transform.rotation.w = 1.0
        broadcaster = StaticTransformBroadcaster(self.node)
        broadcaster.sendTransform(mount_tf)
        self.wait(lambda: self.now() > 0 and all(len(self.trace[k]) >= 3 for k in ("scans", "truth", "wheels", "odometry"))
                  and self.buffer.can_transform("odom", "laser_link", Time()),
                  "Gazebo 时钟、扫描、世界位姿、轮速或动态 TF 未就绪", seconds=18.0)
        origin = self.trace["truth"][-1]
        assert origin["frame"] == "gazebo_world" and math.dist(xy(origin), start[:2]) < 0.03
        assert self.trace["odometry"][-1]["frame"] == "odom" and self.trace["odometry"][-1]["childFrame"] == "base_link"
        assert self.trace["scans"][-1]["frame"] == "laser_link" and self.trace["scans"][-1]["beams"] == 361
        clock = self.node.get_publishers_info_by_topic("/clock")
        assert [endpoint.node_name for endpoint in clock] == ["execution_bridge"]

        self.start_location(args.map_yaml, start)
        # 两个代价地图在各自子命名空间。覆盖相对话题时，将它们明确接到父空间的实际输入。
        self.activate_node("nav2_planner", "planner_server", "-r", f"global_costmap:map:={self.namespace}/map")
        # 让平滑器先就绪，关闭时则让它晚于控制器停用，保留速度传播通道。
        self.activate_node("nav2_velocity_smoother", "velocity_smoother")
        self.activate_node("nav2_controller", "controller_server", "-r", f"local_costmap:scan:={self.namespace}/scan")
        self.activate_node("nav2_behaviors", "behavior_server")
        self.activate_node("nav2_bt_navigator", "bt_navigator", "-p", "default_nav_to_pose_bt_xml:=" + str(tree))
        self.action = ActionClient(self.node, NavigateToPose, "navigate_to_pose")
        self.wait(self.action.server_is_ready, "NavigateToPose 服务不可用")
        # 行为树可接受目标不表示代价地图已得到输入。等待实际新样本后才下发任务。
        def costmaps_ready():
            global_map = self.costmaps.get("global_costmap")
            local_map = self.costmaps.get("local_costmap")
            return (global_map is not None and local_map is not None
                    and len(global_map.data) == self.grid.width * self.grid.height
                    and any(value == 254 for value in local_map.data))

        self.wait(costmaps_ready, "尚未收到有效的全局图与扫描标记的局部图", seconds=10.0)
        self.await_navigation_frames()
        smooth_topic = self.namespace + "/cmd_vel_smoothed"
        self.wait(lambda: self.node.count_subscribers(smooth_topic) == 2, "仿真桥未匹配平滑器输出")
        self.report["endpointRoles"] = dict(clock=["execution_bridge"],
            controllerTopicPublishers=sorted(e.node_name for e in self.node.get_publishers_info_by_topic(self.namespace + "/cmd_vel")),
            smootherPublishers=[e.node_name for e in self.node.get_publishers_info_by_topic(smooth_topic)],
            simulatorCommandSubscribers=sorted(e.node_name for e in self.node.get_subscriptions_info_by_topic(smooth_topic)))
        for name, topic in (("global_costmap", "map"), ("local_costmap", "scan")):
            matches = sorted((e.node_name, e.node_namespace) for e in
                self.node.get_subscriptions_info_by_topic(self.namespace + "/" + topic))
            assert (name, self.namespace + "/" + name) in matches, matches
            self.report["endpointRoles"][name] = dict(topic=self.namespace + "/" + topic,
                receivedCells=len(self.costmaps[name].data), frame=self.costmaps[name].header.frame_id)
        assert self.report["endpointRoles"]["smootherPublishers"] == ["velocity_smoother"]
        assert self.report["endpointRoles"]["simulatorCommandSubscribers"] == ["execution_bridge", "execution_probe"]

        successful = self.drive_goal("arrival", (2.20, 0.70, 0.0))
        assert (successful["status"], successful["errorCode"]) == (4, 0), successful
        assert successful["positionErrorM"] < POSITION_TOLERANCE_M and successful["yawErrorRad"] < 0.28, successful
        assert successful["worldTravelM"] > 4.0 and successful["plans"] >= 2 and successful["feedbackSamples"] >= 10
        assert successful["minimumCenterClearanceM"] > 0.24, successful
        assert any(row["action"] == "follow_path" and row["status"] == 4 for row in successful["nestedResults"])

        canceled = self.drive_goal("cancel", (-2.15, -1.15, math.pi), cancel=True)
        assert canceled["status"] == 5 and canceled["positionErrorM"] > 0.70, canceled
        assert canceled["displacementM"] > 0.32 and canceled["travelAfterCancelM"] < 0.42, canceled
        assert any(row["action"] == "follow_path" and row["status"] == 5 for row in canceled["nestedResults"]), canceled
        for stage in (successful, canceled):
            for name in ("controller", "smoothed"):
                assert stage[name]["nonzero"] >= 5 and stage[name]["firstZeroAfterMotionNs"] is not None, (name, stage)

        outside = self.drive_goal("outside_map", (5.0, 0.0, 0.0))
        assert (outside["status"], outside["errorCode"]) == (6, 204), outside
        assert [(row["action"], row["errorCode"]) for row in outside["nestedResults"]] == [("compute_path_to_pose", 204)]
        assert outside["smoothed"]["nonzero"] == 0 and outside["displacementM"] < 0.035, outside

        # 用实际 ControllerSelector 话题注入一个不存在的 ID。默认行为树保持原样。
        selector = self.node.create_publisher(String, "controller_selector",
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.wait(lambda: selector.get_subscription_count() > 0, "未匹配行为树的 ControllerSelector")
        selector.publish(String(data="unknown_controller_for_lab"))
        self.observe(0.2)
        recovered_goal = (1.85, -1.35, 0.0)
        invalid = self.drive_goal("invalid_controller", recovered_goal)
        assert (invalid["status"], invalid["errorCode"]) == (6, 101), invalid
        assert any(row["action"] == "follow_path" and row["errorCode"] == 101 for row in invalid["nestedResults"])
        assert invalid["smoothed"]["nonzero"] == 0 and invalid["displacementM"] < 0.035, invalid

        selector.publish(String(data="FollowPath"))
        self.observe(0.2)
        recovered = self.drive_goal("restored_controller", recovered_goal)
        assert (recovered["status"], recovered["errorCode"]) == (4, 0), recovered
        assert recovered["positionErrorM"] < POSITION_TOLERANCE_M and recovered["worldTravelM"] > 0.45, recovered

        self.report["limits"] = dict(positionToleranceM=POSITION_TOLERANCE_M,
            stillLinearMps=STILL_LINEAR_MPS, stillAngularRadps=STILL_ANGULAR_RADPS, stillWindowNs=STILL_WINDOW_NS)
        self.report["traceCounts"] = {name: len(rows) for name, rows in self.trace.items()}
        self.stop_nodes()
        listener.unregister()
        self.action.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--map-yaml", required=True, type=Path, help="同一房间的 learned.yaml，旁边保留 learned.pgm")
    parser.add_argument("--domain-id", type=int, default=218, help="未使用的本机 DDS 域，1..232")
    parser.add_argument("--egl-vendor-json", type=Path, help="Gazebo Ogre2 EGL 驱动文件")
    parser.add_argument("--report", type=Path, help="将报告另写到尚不存在的文件")
    args = parser.parse_args()
    args.map_yaml = args.map_yaml.resolve()
    if (not args.map_yaml.is_file() or not 1 <= args.domain_id <= 232
            or args.egl_vendor_json and not args.egl_vendor_json.is_file()
            or args.report and args.report.exists()):
        parser.error("请检查地图文件、DDS 域、EGL 驱动和报告路径。")
    if os.environ.get("ROS_DISTRO") != "jazzy":
        raise SystemExit("请先加载本机 ROS 2 Jazzy。")

    output = Path(tempfile.mkdtemp(prefix="ros2-nav-execution-"))
    print(f"实验记录目录 {output}", flush=True)
    suffix = output.name.rsplit("-", 1)[-1]
    for key in ("ROS_LOCALHOST_ONLY", "ROS_STATIC_PEERS", "ROS_DISCOVERY_SERVER", "FASTDDS_DEFAULT_PROFILES_FILE",
                "FASTRTPS_DEFAULT_PROFILES_FILE", "GZ_RELAY"):
        os.environ.pop(key, None)
    os.environ.update(ROS_DOMAIN_ID=str(args.domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
                      RMW_IMPLEMENTATION="rmw_fastrtps_cpp", SKIP_DEFAULT_XML="1",
                      ROS_LOG_DIR=str(output / "ros-log"), ROS_HOME=str(output / "ros-home"),
                      GZ_PARTITION="hub_execute_" + suffix, GZ_IP="127.0.0.1",
                      GZ_FUEL_CACHE_PATH=str(output / "fuel"), MESA_SHADER_CACHE_DISABLE="true")
    (output / "fuel").mkdir()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    files = [*(HERE / name for name in ("validate_execution.py", "mobile_base.sdf", "bridge.yaml", "navigation.yaml")),
             *(EXAMPLES / name for name in ("nav2_labs/nav_room.sdf", "nav2_labs/validate_nav2.py", "gazebo_labs/validate_sensors.py"))]
    report = dict(passed=False, output=str(output), domainId=args.domain_id, discovery="LOCALHOST",
        namespace="/navexec_" + suffix, gazeboPartition=os.environ["GZ_PARTITION"], versions={}, scenarios={}, lifecycle=[],
        processes=[], sourceHashes={path.relative_to(EXAMPLES).as_posix(): sha(path) for path in files})
    lab = ExecutionLab(output, report)
    try:
        lab.run(args)
    except (Exception, KeyboardInterrupt):
        report["error"] = traceback.format_exc()
        print(report["error"], end="")
    finally:
        lab.close()
    trace = output / "telemetry.json"
    trace.write_text(json.dumps(lab.trace, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
    report["telemetry"] = dict(file=trace.name, sha256=sha(trace))
    report["passed"] = ("error" not in report and len(report["processes"]) == 9 and len(report["lifecycle"]) == 28
        and all(p["returnCode"] == 0 and p["pidGone"] and p["signals"] == ["SIGINT"] for p in report["processes"]))
    data = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    (output / "report.json").write_text(data)
    if args.report:
        with args.report.open("x") as file:
            file.write(data)
    print(json.dumps(dict(passed=report["passed"], report=str(output / "report.json")), ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
