#!/usr/bin/env python3
"""用 Jazzy 真实节点检查软件差速底盘、局部 EKF 和 TF。

输入：同包 YAML、原学习模型和固定合成 TwistStamped。轮尺寸 m，命令 m/s 与 rad/s。
输出：/tmp 运行目录中的实际服务回执、传感器样本、进程日志和 JSON。
顺序：模型→接口→资源竞争→反馈→滤波→超时→恢复→双 TF 来源反例。
边界：仅 GenericSystem，无 Gazebo、IMU、GNSS、电机或实时性测试。
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE.parent
MODEL = EXAMPLES / "model_labs/learning_description/urdf/robot.urdf.xacro"
JOINTS = ("left_wheel_joint", "right_wheel_joint")
ODOM_EDGE = ("odom", "base_footprint")
WHEEL_EDGES = {("base_link", name.removesuffix("_joint")) for name in JOINTS}
COMMAND_NAMES = {name + "/velocity" for name in JOINTS}
TIMEOUT_S = 0.30


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-id", default=225, type=int, help="用于实验的独立本机 DDS 域，默认 225")
    parser.add_argument("--report", type=Path, help="额外写入这个新路径，省略时只写 /tmp 运行目录")
    args = parser.parse_args()
    if not 1 <= args.domain_id <= 232:
        parser.error("domain-id 须在 1..232")
    if args.report and args.report.exists():
        parser.error("报告路径已存在，请使用新路径")
    return args


def stamp_ns(stamp):
    return stamp.sec * 10**9 + stamp.nanosec


def near(actual, expected, tolerance):
    return len(actual) == len(expected) and all(
        math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance) for a, b in zip(actual, expected)
    )


def joints(message):
    # JointState 数组顺序由发布者决定。按名字关联值，不能直接假设第一个一定是左轮。
    return {
        "stampNs": stamp_ns(message.header.stamp),
        "positionRad": [message.position[message.name.index(name)] for name in JOINTS],
        "velocityRadS": [message.velocity[message.name.index(name)] for name in JOINTS],
    }


def odometry(message):
    return {
        "stampNs": stamp_ns(message.header.stamp),
        "frames": [message.header.frame_id, message.child_frame_id],
        "xyM": [message.pose.pose.position.x, message.pose.pose.position.y],
        "twist": [message.twist.twist.linear.x, message.twist.twist.angular.z],
        "twistVariance": [message.twist.covariance[0], message.twist.covariance[35]],
    }


class DriveLab:
    def __init__(self, output, report):
        self.output, self.report = output, report
        self.namespace = "/drive_" + output.name.rsplit("-", 1)[-1].replace("-", "_")
        self.processes = []
        self.context = self.node = self.executor = None
        self.deadline = time.monotonic() + 55.0
        self.samples = defaultdict(lambda: deque(maxlen=512))

    def start(self, label, argv, *, persistent=False):
        log = self.output / (label + ".log")
        with log.open("wb") as stream:
            process = subprocess.Popen(argv, cwd=self.output, stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        record = dict(label=label, argv=argv, logFile=str(log), pid=process.pid, signals=[])
        self.report["processes"].append(record)
        self.processes.append((process, record, persistent))
        return process

    def command(self, label, argv):
        process = self.start(label, argv)
        status = process.wait(timeout=12.0)
        assert status == 0, (label, status, Path(self.report["processes"][-1]["logFile"]).read_text()[-4000:])

    def wait(self, condition, label, seconds=5.0):
        # 发现与消息等待采用单调时钟软期限，和消息中的 ROS 时钟相互独立。
        end = min(self.deadline, time.monotonic() + seconds)
        while not condition():
            if time.monotonic() >= end:
                raise TimeoutError(label)
            for process, record, persistent in self.processes:
                if persistent and process.poll() is not None:
                    raise RuntimeError(f'{record["label"]} 提前退出 {process.returncode}，见 {record["logFile"]}')
            self.executor.spin_once(timeout_sec=min(0.02, max(0.0, end - time.monotonic())))

    def observe(self, seconds):
        end = time.monotonic() + seconds
        self.wait(lambda: time.monotonic() >= end, "有限观测窗口", seconds + 0.1)

    def call(self, srv, suffix, request=None):
        name = self.namespace + "/controller_manager/" + suffix
        client = self.node.create_client(srv, name)
        try:
            self.wait(client.service_is_ready, "未发现 " + name)
            future = client.call_async(request if request is not None else srv.Request())
            self.wait(future.done, "无服务应答 " + name)
            return future.result()
        finally:
            self.node.destroy_client(client)

    def watch(self, key, message_type, topic, qos=10):
        def record(message):
            self.samples[key].append((time.monotonic(), message))
        self.node.create_subscription(message_type, self.namespace + "/" + topic, record, qos)

    def latest(self, key):
        return self.samples[key][-1][1]

    def window(self, key, since):
        return [message for at, message in self.samples[key] if at >= since]

    def edges(self, key, since=0.0):
        return {(t.header.frame_id, t.child_frame_id)
                for message in self.window(key, since) for t in message.transforms}

    def run(self):
        import yaml
        from ament_index_python.packages import get_package_prefix
        from builtin_interfaces.msg import Duration as DurationMsg
        from controller_manager_msgs.srv import ListControllers, ListHardwareComponents, ListHardwareInterfaces, SwitchController
        from geometry_msgs.msg import TwistStamped
        from nav_msgs.msg import Odometry
        import rclpy
        from rclpy.context import Context
        from rclpy.duration import Duration
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.qos import DurabilityPolicy, QoSProfile
        from rclpy.signals import SignalHandlerOptions
        from sensor_msgs.msg import JointState
        from tf2_msgs.msg import TFMessage

        def exe(package, executable):
            return str(Path(get_package_prefix(package)) / "lib" / package / executable)

        packages = ("xacro", "robot_state_publisher", "controller_manager", "hardware_interface",
                    "joint_state_broadcaster", "diff_drive_controller", "robot_localization", "rclpy")
        self.report["versions"] = {
            p: ET.parse(Path(get_package_prefix(p)) / "share" / p / "package.xml").findtext("version")
            for p in packages
        }
        self.report["namespace"] = self.namespace
        ros_args = ["--ros-args", "-r", "__ns:=" + self.namespace]
        tf_args = ["-r", "/tf:=" + self.namespace + "/tf", "-r", "/tf_static:=" + self.namespace + "/tf_static"]

        # 复用既有几何，检查轮径、轮距及两端接口，再把唯一的内存后端追加到 URDF。
        config = yaml.safe_load((HERE / "diff_drive.yaml").read_text())
        drive_params = config["/**"]["ros__parameters"]
        radius, separation = drive_params["wheel_radius"], drive_params["wheel_separation"]
        assert drive_params["cmd_vel_timeout"] == TIMEOUT_S and not drive_params["enable_odom_tf"]
        assert tuple(drive_params[side + "_wheel_names"][0] for side in ("left", "right")) == JOINTS
        expanded = self.output / "expanded.urdf"
        self.command("xacro", [exe("xacro", "xacro"), str(MODEL), "-o", str(expanded)])
        robot = ET.parse(expanded).getroot()
        assert not robot.findall("ros2_control") and not robot.findall(".//plugin")
        wheel_y = [float(robot.find(f"joint[@name='{name}']/origin").attrib["xyz"].split()[1]) for name in JOINTS]
        assert near(wheel_y, [separation / 2.0, -separation / 2.0], 1e-10), wheel_y
        for name in JOINTS:
            cylinder = robot.find(f"link[@name='{name.removesuffix('_joint')}']/visual/geometry/cylinder")
            assert math.isclose(float(cylinder.attrib["radius"]), radius)
        hardware = ET.parse(HERE / "mock_system.xml").getroot()
        assert hardware.tag == "ros2_control"
        assert [plugin.text for plugin in hardware.findall(".//plugin")] == ["mock_components/GenericSystem"]
        assert [joint.attrib["name"] for joint in hardware.findall("joint")] == list(JOINTS)
        robot.append(hardware)
        self.report["geometry"] = dict(wheelRadiusM=radius, wheelSeparationM=separation, jointY_M=wheel_y)
        description = self.output / "description.yaml"
        description.write_text(yaml.safe_dump({
            self.namespace + "/robot_state_publisher": {"ros__parameters": {
                "robot_description": ET.tostring(robot, encoding="unicode"), "publish_frequency": 40.0,
            }},
        }))
        # reserve 的 TF 单独接到 controller_tf。对照时能直接认出哪个发布源产生了同名边。
        reserve_file = self.output / "reserve.yaml"
        drive_params["enable_odom_tf"] = True
        reserve_file.write_text(yaml.safe_dump(config))

        self.context = Context()
        rclpy.init(context=self.context, signal_handler_options=SignalHandlerOptions.NO)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.node = Node("contract_probe", namespace=self.namespace, context=self.context)
        self.executor.add_node(self.node)
        self.watch("joint", JointState, "state_broadcaster/joint_states")
        self.watch("raw", Odometry, "drive/odom")
        self.watch("ekf", Odometry, "odometry/filtered")
        self.watch("tf", TFMessage, "tf")
        self.watch("controller_tf", TFMessage, "controller_tf")
        publisher = self.node.create_publisher(TwistStamped, self.namespace + "/drive/cmd_vel", 10)
        self.start("rsp", [exe("robot_state_publisher", "robot_state_publisher"), *ros_args, *tf_args,
                          "-r", "joint_states:=state_broadcaster/joint_states", "--params-file", str(description)],
                   persistent=True)
        manager_file = HERE / "manager.yaml"
        self.start("manager", [exe("controller_manager", "ros2_control_node"), *ros_args,
                              "--params-file", str(manager_file)], persistent=True)
        component, = self.call(ListHardwareComponents, "list_hardware_components").component
        assert component.plugin_name == "mock_components/GenericSystem" and component.state.label == "active"
        self.report["hardware"] = dict(name=component.name, plugin=component.plugin_name,
                                       state=component.state.label, rwRateHz=component.rw_rate)
        self.watch("static", TFMessage, "tf_static", QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL))

        for name, config_file in (("state_broadcaster", manager_file), ("drive", HERE / "diff_drive.yaml"), ("reserve", reserve_file)):
            options = [] if name == "state_broadcaster" else [
                "--inactive", "--controller-ros-args", "-r /tf:=" + self.namespace + "/controller_tf",
            ]
            self.command("spawn_" + name, [exe("controller_manager", "spawner"), name,
                         "-c", self.namespace + "/controller_manager", "-p", str(config_file),
                         "--controller-manager-timeout", "5", "--service-call-timeout", "3",
                         "--switch-timeout", "2", *options, *ros_args])

        def inspect():
            controllers = self.call(ListControllers, "list_controllers").controller
            interfaces = self.call(ListHardwareInterfaces, "list_hardware_interfaces")
            states = {c.name: {"state": c.state, "claimed": sorted(c.claimed_interfaces),
                               "requiredState": sorted(c.required_state_interfaces)} for c in controllers}
            all_commands = {i.name: [i.is_available, i.is_claimed] for i in interfaces.command_interfaces}
            # 资源表还可能包含控制器导出的上游 reference，并不都是物理轮速接口。
            commands = {name: state for name, state in all_commands.items() if name in COMMAND_NAMES}
            references = sorted(all_commands.keys() - commands.keys())
            feedback = {i.name for i in interfaces.state_interfaces if i.is_available}
            assert set(commands) == COMMAND_NAMES
            assert feedback == {name + "/" + key for name in JOINTS for key in ("position", "velocity")}
            assert states["state_broadcaster"]["state"] == "active"
            return dict(controllers=states, commands=commands, stateInterfaces=sorted(feedback),
                        otherCommandNames=references)

        def switch(activate, deactivate=()):
            request = SwitchController.Request(activate_controllers=list(activate),
                                               deactivate_controllers=list(deactivate),
                                               strictness=SwitchController.Request.STRICT, activate_asap=False,
                                               timeout=DurationMsg(sec=2))
            response = self.call(SwitchController, "switch_controller", request)
            return dict(activate=list(activate), deactivate=list(deactivate), ok=response.ok, message=response.message)

        before = inspect()
        assert all(state == [True, False] for state in before["commands"].values())
        activation = switch(["drive"])
        active = inspect()
        assert activation["ok"] and active["controllers"]["drive"]["state"] == "active"
        assert set(active["controllers"]["drive"]["claimed"]) == COMMAND_NAMES
        assert set(active["controllers"]["drive"]["requiredState"]) == {name + "/position" for name in JOINTS}
        assert all(state == [True, True] for state in active["commands"].values())
        rejection = switch(["reserve"])
        after_rejection = inspect()
        assert not rejection["ok"] and after_rejection == active
        assert after_rejection["controllers"]["reserve"]["state"] == "inactive"
        self.report["resources"] = dict(before=before, activation=activation, active=active,
                                        rejection=rejection, afterRejection=after_rejection)

        self.wait(lambda: self.samples["joint"] and self.samples["raw"] and
                  WHEEL_EDGES <= self.edges("tf") and ("base_footprint", "base_link") in self.edges("static"),
                  "未观察到原始里程计、固定边和轮子活动边")
        start = time.monotonic()
        self.observe(0.35)
        before_ekf = self.edges("tf", start)
        assert WHEEL_EDGES <= before_ekf and ODOM_EDGE not in before_ekf and not self.edges("controller_tf", start)
        self.start("ekf", [exe("robot_localization", "ekf_node"), *ros_args, *tf_args,
                          "-r", "__node:=ekf_filter_node", "--params-file", str(HERE / "ekf.yaml")], persistent=True)
        self.wait(lambda: self.samples["ekf"] and ODOM_EDGE in self.edges("tf"), "EKF 未发布融合输出和局部 TF")
        self.wait(lambda: publisher.get_subscription_count() == 1, "命令端点未匹配或数量异常")
        self.report["frames"] = dict(staticEdges=sorted(self.edges("static")), beforeEkf=sorted(before_ekf),
                                     withEkf=sorted(self.edges("tf")), controlTfDisabled=not self.edges("controller_tf"))
        assert ("map", "odom") not in self.edges("tf")

        def send(vx, wz, age_s=0.0):
            msg = TwistStamped()
            msg.header.stamp = (self.node.get_clock().now() - Duration(seconds=age_s)).to_msg()
            msg.header.frame_id = "base_footprint"
            msg.twist.linear.x, msg.twist.angular.z = vx, wz
            publisher.publish(msg)
            return time.monotonic()

        def motion(label, vx, wz):
            # 以约 20 Hz 刷新系统时间戳。检查有限稳态窗口中的反馈，避开开始时的离散周期。
            start = time.monotonic()
            for _ in range(20):
                last = send(vx, wz)
                self.observe(0.05)
            wheels = [(vx - wz * separation / 2.0) / radius, (vx + wz * separation / 2.0) / radius]
            observed = {name: self.window(name, start + 0.75) for name in ("joint", "raw", "ekf")}
            assert all(len(messages) >= 3 for messages in observed.values()), label
            joint, raw, fused = joints(observed["joint"][-1]), odometry(observed["raw"][-1]), odometry(observed["ekf"][-1])
            assert near(joint["velocityRadS"], wheels, 1e-4), joint
            assert raw["frames"] == fused["frames"] == list(ODOM_EDGE), (raw, fused)
            assert near(raw["twist"], [vx, wz], 0.015), raw
            assert near(fused["twist"], [vx, wz], 0.03), fused
            assert all(math.isfinite(n) for n in joint["positionRad"] + raw["xyM"] + fused["xyM"])
            self.report["motion"][label] = dict(command=[vx, wz], expectedWheelRadS=wheels, joint=joint, raw=raw, fused=fused,
                                               windowSamples={k: len(v) for k, v in observed.items()})
            return last

        motion("straight", 0.16, 0.0)
        last_command = motion("turn", 0.16, 0.4)
        self.wait(lambda: near(joints(self.latest("joint"))["velocityRadS"], [0.0, 0.0], 1e-4) and
                  near(odometry(self.latest("raw"))["twist"], [0.0, 0.0], 0.015),
                  "停止刷新命令后反馈未归零", 2.0)
        elapsed = time.monotonic() - last_command
        assert 0.25 <= elapsed <= 1.5, elapsed
        self.report["timeout"] = dict(configuredRosSeconds=TIMEOUT_S, observedSteadySeconds=elapsed,
                                      joint=joints(self.latest("joint")), raw=odometry(self.latest("raw")))

        start = time.monotonic()
        send(0.16, 0.4, age_s=1.0)
        self.observe(0.35)
        stale_joints = [joints(message) for message in self.window("joint", start)]
        assert len(stale_joints) >= 3 and all(near(s["velocityRadS"], [0.0, 0.0], 1e-4) for s in stale_joints)
        self.report["stale"] = dict(stampAgeSeconds=1.0, windowSeconds=0.35, jointSamples=len(stale_joints),
                                    joint=stale_joints[-1])
        motion("recovered", 0.16, 0.0)
        motion("explicitZero", 0.0, 0.0)

        handoff = switch(["reserve"], ["drive"])
        switch_stamp = self.node.get_clock().now().nanoseconds
        after_handoff = inspect()
        assert handoff["ok"] and after_handoff["controllers"]["drive"]["state"] == "inactive"
        assert after_handoff["controllers"]["reserve"]["state"] == "active"
        assert set(after_handoff["controllers"]["reserve"]["claimed"]) == COMMAND_NAMES
        self.wait(lambda: ODOM_EDGE in self.edges("controller_tf"), "reserve 未广播同名里程计边")
        start = time.monotonic()
        # 结束新测量后，EKF 按 sensor_timeout 预测，输出不能继续按活跃输入的 30 Hz 来断言。
        self.observe(0.75)
        fusion_edges = self.edges("tf", start)
        controller_edges = self.edges("controller_tf", start)
        raw_stamps = [stamp_ns(message.header.stamp) for message in self.window("raw", start)]
        fused_stamps = [stamp_ns(message.header.stamp) for message in self.window("ekf", start)]
        new_raw = sum(stamp > switch_stamp for stamp in raw_stamps)
        new_fused = sum(stamp > switch_stamp for stamp in fused_stamps)
        self.report["handoff"] = dict(switch=handoff, resources=after_handoff, fusionEdges=sorted(fusion_edges),
                                      controllerEdges=sorted(controller_edges), windowSeconds=0.75,
                                      switchStampNs=switch_stamp, rawStampsNs=raw_stamps, fusedStampsNs=fused_stamps,
                                      newRawMessages=new_raw, newFusedMessages=new_fused)
        assert ODOM_EDGE in (fusion_edges & controller_edges), (fusion_edges, controller_edges)
        assert new_raw == 0 and new_fused >= 2, (raw_stamps, fused_stamps)

    def close(self):
        if self.executor is not None:
            self.executor.shutdown(timeout_sec=2.0)
        if self.node is not None:
            self.node.destroy_node()
        if self.context is not None and self.context.ok():
            self.context.shutdown()
        for process, record, _ in reversed(self.processes):
            # 只处理本脚本创建的独立进程。正常退出只给直接 PID 一次 INT，超时才升级到进程组。
            for sig, grace in ((signal.SIGINT, 4.0), (signal.SIGTERM, 2.0), (signal.SIGKILL, 2.0)):
                if process.poll() is not None:
                    break
                try:
                    if sig == signal.SIGINT:
                        process.send_signal(sig)
                    else:
                        os.killpg(process.pid, sig)
                    record["signals"].append(sig.name)
                    process.wait(timeout=grace)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    continue
            raw = Path(record["logFile"]).read_bytes()
            record.update(returnCode=process.poll(), pidGone=not Path("/proc", str(process.pid)).exists(),
                          logSha256=hashlib.sha256(raw).hexdigest(), logTail=raw[-4500:].decode(errors="replace"))


def main():
    args = arguments()
    if os.environ.get("ROS_DISTRO") != "jazzy":
        raise SystemExit("请先加载 ROS 2 Jazzy 环境。")
    # 保留本机域通信，清除外部 DDS 发现配置。实验没有发布到工作机器人话题。
    for key in ("ROS_LOCALHOST_ONLY", "ROS_STATIC_PEERS", "ROS_DISCOVERY_SERVER",
                "FASTDDS_DEFAULT_PROFILES_FILE", "FASTRTPS_DEFAULT_PROFILES_FILE"):
        os.environ.pop(key, None)
    os.environ.update(ROS_DOMAIN_ID=str(args.domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
                      RMW_IMPLEMENTATION="rmw_fastrtps_cpp", SKIP_DEFAULT_XML="1")
    output = Path(tempfile.mkdtemp(prefix="ros2-learning-drive-"))
    os.environ.update(ROS_HOME=str(output / "ros-home"), ROS_LOG_DIR=str(output / "ros-log"))
    source = [Path(__file__).resolve(), MODEL, *(HERE / name for name in ("mock_system.xml", "manager.yaml", "diff_drive.yaml", "ekf.yaml"))]
    report = dict(passed=False, checkedAt=datetime.now(timezone.utc).isoformat(), scope=__doc__.splitlines()[-2],
                  domainId=args.domain_id, discovery="LOCALHOST", rmw="rmw_fastrtps_cpp", output=str(output),
                  sourceHashes={p.relative_to(EXAMPLES).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source},
                  processes=[], motion={})
    lab = DriveLab(output, report)
    try:
        lab.run()
    except (Exception, KeyboardInterrupt):
        report["error"] = traceback.format_exc()
        print(report["error"], end="")
    finally:
        lab.close()
    # 旧时间戳不触发软件运动，并且日志明确拒收。正常运行的七个直接进程必须全部退出。
    drive_log = (output / "manager.log").read_text(errors="replace") if (output / "manager.log").is_file() else ""
    report["staleLogged"] = "Ignoring the received message" in drive_log
    report["passed"] = ("error" not in report and report["staleLogged"] and len(report["processes"]) == 7 and
                        all(p["returnCode"] == 0 and p["pidGone"] and set(p["signals"]) <= {"SIGINT"}
                            for p in report["processes"]))
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    (output / "report.json").write_text(encoded)
    if args.report:
        with args.report.open("x") as stream:
            stream.write(encoded)
    print(json.dumps({"passed": report["passed"], "report": str(output / "report.json")}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
