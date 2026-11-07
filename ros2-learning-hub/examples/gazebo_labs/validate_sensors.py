#!/usr/bin/env python3
"""运行 Harmonic 的本地几何世界，验证 ROS 时钟、传感器、QoS 和 TF。

输入：同目录 SDF 与单向桥映射；长度 m、角度 rad、图像尺寸 px。
输出：新的临时目录，保存图像、边缘图、服务回执、消息字段、日志和 JSON。
顺序：先发现暂停的世界，再桥接控制与数据，最后检查暂停/恢复与采样。
范围：固定模拟相机和激光，不连接硬件、不运行 SLAM 或导航控制。
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import struct
import subprocess
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
WORLD_CONTROL = "/world/hub_perception/control"
OPTICAL = "camera_optical_frame"
LASER = "laser_link"
BASE = "rig_base"


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-id", type=int, default=227, help="空闲的本机 DDS 域，范围 1..232")
    parser.add_argument("--egl-vendor-json", type=Path, help="仅为本次 Gazebo 进程选择可用的 EGL vendor")
    parser.add_argument("--report", type=Path, help="将报告另写到尚不存在的文件")
    args = parser.parse_args()
    if not 1 <= args.domain_id <= 232:
        parser.error("domain-id 须在 1..232")
    if args.report and args.report.exists():
        parser.error("报告文件已存在，请指定新路径")
    if args.egl_vendor_json and not args.egl_vendor_json.is_file():
        parser.error("EGL vendor JSON 不存在")
    return args


def ns(stamp):
    return stamp.sec * 10**9 + stamp.nanosec


def stamp(message):
    return ns(message.header.stamp)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cloud_fields(message, float32):
    """按 ROS fields 中的偏移读 FLOAT32 坐标，逐行尊重 row_step，排除非有限点。"""
    fields = {field.name: field for field in message.fields}
    offsets = [fields[name].offset for name in ("x", "y", "z")]
    assert all(fields[name].datatype == float32 and fields[name].count == 1 for name in ("x", "y", "z"))
    assert max(offsets) + 4 <= message.point_step
    assert message.row_step >= message.width * message.point_step
    assert len(message.data) == message.height * message.row_step
    data = memoryview(message.data)
    fmt = ">f" if message.is_bigendian else "<f"
    points = []
    for row in range(message.height):
        for column in range(message.width):
            base = row * message.row_step + column * message.point_step
            point = tuple(struct.unpack_from(fmt, data, base + offset)[0] for offset in offsets)
            if all(map(math.isfinite, point)):
                points.append(point)
    assert points, "点云没有有限点"
    center = min(points, key=lambda point: abs(point[1]) + abs(point[2]))
    return dict(width=message.width, height=message.height, pointStep=message.point_step, rowStep=message.row_step,
                xyzOffsets=offsets, bigEndian=bool(message.is_bigendian), finitePoints=len(points),
                centerM=list(center), stampNs=stamp(message), frame=message.header.frame_id)


class Lab:
    def __init__(self, output, report):
        self.output, self.report = output, report
        self.namespace = "/gzlab_" + output.name.rsplit("-", 1)[-1].replace("-", "_")
        self.processes = []
        self.context = self.executor = self.node = None
        self.deadline = time.monotonic() + 45

    def start(self, label, argv, env=None):
        log = self.output / (label + ".log")
        with log.open("wb") as stream:
            process = subprocess.Popen(argv, cwd=self.output, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        record = dict(label=label, argv=argv, pid=process.pid, logFile=str(log), signals=[])
        self.report["processes"].append(record)
        self.processes.append((process, record))

    def assert_live(self):
        for process, record in self.processes:
            if process.poll() is not None:
                raise RuntimeError(f"{record['label']} 提前退出 {process.returncode}，见 {record['logFile']}")

    def wait(self, predicate, label, seconds=5.0):
        # 等待窗口与超时都用单调墙钟，暂停模拟不会让验证本身挂起。
        end = min(self.deadline, time.monotonic() + seconds)
        while not predicate():
            self.assert_live()
            if time.monotonic() >= end:
                raise TimeoutError(label)
            self.executor.spin_once(timeout_sec=min(0.02, max(0.0, end - time.monotonic())))

    def observe(self, seconds):
        end = time.monotonic() + seconds
        self.wait(lambda: time.monotonic() >= end, "有限观测窗口", seconds + 0.15)

    def run(self, egl_vendor):
        import cv2
        from ament_index_python.packages import get_package_prefix
        from cv_bridge import CvBridge
        from geometry_msgs.msg import PointStamped, TransformStamped
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.parameter import Parameter
        from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
        from rclpy.signals import SignalHandlerOptions
        from rclpy.time import Time
        from ros_gz_interfaces.srv import ControlWorld
        from rosgraph_msgs.msg import Clock
        from sensor_msgs.msg import CameraInfo, Image, LaserScan, PointCloud2, PointField
        from tf2_geometry_msgs import do_transform_point
        from tf2_ros import Buffer, StaticTransformBroadcaster, TransformListener

        versions = self.report["versions"]
        versions["gzSim"] = subprocess.check_output(["gz", "sim", "--version"], text=True, timeout=5).splitlines()[0]
        versions["opencv"] = cv2.__version__
        for name in ("ros_gz_bridge", "ros_gz_interfaces", "gz_sensors_vendor", "cv_bridge", "rclpy"):
            versions[name] = ET.parse(Path(get_package_prefix(name)) / "share" / name / "package.xml").findtext("version")
        cv2.setNumThreads(1)
        render_env = dict(os.environ)
        if egl_vendor:
            render_env["__EGL_VENDOR_LIBRARY_FILENAMES"] = str(egl_vendor.resolve())
            render_env.pop("LIBGL_ALWAYS_SOFTWARE", None)
        self.report.update(namespace=self.namespace, eglVendor=render_env.get("__EGL_VENDOR_LIBRARY_FILENAMES"),
                           renderMode="server-only EGL Ogre2")
        # 不带 -r：先以暂停世界启动。控制指令必须从下方的 ROS 服务桥成功送达。
        self.start("gazebo", ["gz", "sim", "-s", "--headless-rendering", "-v", "4", str(HERE / "sensors.sdf")], render_env)
        # ROS 服务端出现只表示桥就绪。先确认同一 Gazebo 分区实际公开世界控制服务。
        for _ in range(8):
            self.assert_live()
            services = subprocess.check_output(["gz", "service", "-l"], text=True, timeout=3).splitlines()
            if WORLD_CONTROL in services:
                break
        else:
            raise RuntimeError("Gazebo Transport 未发现世界控制服务")
        self.report["gazeboWorldControlDiscovered"] = True
        bridge_exe = Path(get_package_prefix("ros_gz_bridge")) / "lib/ros_gz_bridge/parameter_bridge"
        bridge_args = WORLD_CONTROL + "@ros_gz_interfaces/srv/ControlWorld@gz.msgs.WorldControl@gz.msgs.Boolean"
        self.start("bridge", [str(bridge_exe), bridge_args, "--ros-args", "-r", "__ns:=" + self.namespace,
                              "-r", "__node:=sensor_bridge", "-p", "config_file:=" + str(HERE / "bridge.yaml"),
                              "-p", "override_timestamps_with_wall_time:=false"])

        self.context = Context()
        rclpy.init(context=self.context, signal_handler_options=SignalHandlerOptions.NO)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.node = Node("sensor_probe", namespace=self.namespace, context=self.context,
                         parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.executor.add_node(self.node)
        node = self.node
        queues = {key: deque(maxlen=512) for key in ("clock", "image", "info", "scan", "cloud", "edges", "reliable")}
        image_bridge = CvBridge()
        edge_pub = node.create_publisher(Image, "camera/edges", qos_profile_sensor_data)

        def handle_image(message):
            # 红板的颜色对比在红通道更明显。请求 BGR 后第 2 索引是红色，再输出 mono8 边缘。
            # 处理像素不替换采集时戳或光学 frame。固定阈值只用于这个几何与材质。
            bgr = image_bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
            edges = cv2.Canny(bgr[:, :, 2], 40, 120)
            edge_pub.publish(image_bridge.cv2_to_imgmsg(edges, encoding="mono8", header=message.header))
            queues["image"].append(message)

        def subscribe(key, msg_type, topic, qos=qos_profile_sensor_data):
            return node.create_subscription(msg_type, topic, lambda message: queues[key].append(message), qos)

        # 与 Jazzy Python TimeSource 一样显式请求深度 1、尽力而为。
        subscribe("clock", Clock, "/clock", QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
        node.create_subscription(Image, "camera/image_raw", handle_image, qos_profile_sensor_data)
        subscribe("info", CameraInfo, "camera/camera_info")
        scan = subscribe("scan", LaserScan, "scan")
        # 同一真发布端上的负例：RELIABLE 请求与 BEST_EFFORT 提供不匹配。
        reliable_scan = subscribe("reliable", LaserScan, "scan", 10)
        subscribe("cloud", PointCloud2, "scan_points")
        subscribe("edges", Image, "camera/edges")
        service = node.create_client(ControlWorld, WORLD_CONTROL)
        self.wait(service.service_is_ready, "ROS 侧世界控制服务未就绪")

        # 台架、相机与激光共原点；只有光学基轴旋转。重标 Header 不会替代这些变换。
        tf_buffer = Buffer()
        listener = TransformListener(tf_buffer, node, spin_thread=False)
        broadcaster = StaticTransformBroadcaster(node)
        transforms = []
        for parent, child, xyzw in ((BASE, "camera_link", (0.0, 0.0, 0.0, 1.0)),
                                    ("camera_link", OPTICAL, (-0.5, 0.5, -0.5, 0.5)),
                                    (BASE, LASER, (0.0, 0.0, 0.0, 1.0))):
            transform = TransformStamped()
            transform.header.frame_id = parent
            transform.child_frame_id = child
            q = transform.transform.rotation
            q.x, q.y, q.z, q.w = xyzw
            transforms.append(transform)
        broadcaster.sendTransform(transforms)

        self.wait(lambda: len(node.get_publishers_info_by_topic("/clock")) == 1, "未发现唯一 ROS 时钟提供者")
        self.observe(0.25)
        initially = node.get_clock().now().nanoseconds
        assert initially == 0, initially
        bridged_topics = ("/clock", *(self.namespace + "/" + topic for topic in
                                      ("camera/image_raw", "camera/camera_info", "scan", "scan_points")))
        for topic in bridged_topics:
            publishers = node.get_publishers_info_by_topic(topic)
            assert len(publishers) == 1 and publishers[0].node_name == "sensor_bridge"
            assert all(endpoint.node_name != "sensor_bridge" for endpoint in node.get_subscriptions_info_by_topic(topic))
        self.report["oneWayRosTopics"] = list(bridged_topics)

        def control(pause):
            request = ControlWorld.Request()
            request.world_control.pause = pause
            future = service.call_async(request)
            self.wait(future.done, "世界控制无回应")
            success = future.result().success
            self.report["controlReplies"].append(dict(pause=pause, success=success))
            assert success, "Gazebo 拒绝暂停控制"

        def same_frame_triplets():
            # 桥有三条不同 ROS 话题，按 Header 精确配对，禁止拿各队列的最后一条盲配。
            images, infos, edges = ({stamp(msg): msg for msg in queues[key]} for key in ("image", "info", "edges"))
            return [(images[t], infos[t], edges[t]) for t in sorted(images.keys() & infos.keys() & edges.keys())]

        control(False)
        self.wait(lambda: queues["clock"] and ns(queues["clock"][-1].clock) > 0 and
                  node.get_clock().now().nanoseconds > 0 and len(same_frame_triplets()) >= 3 and
                  len(queues["scan"]) >= 3 and len(queues["cloud"]) >= 3, "活动期未收到完整仿真观测", 15.0)
        self.observe(0.35)
        running = node.get_clock().now().nanoseconds
        actual_endpoints = node.get_publishers_info_by_topic(self.namespace + "/scan")
        assert len(actual_endpoints) == 1 and actual_endpoints[0].qos_profile.reliability.name == "BEST_EFFORT"
        assert scan.get_publisher_count() == 1 and reliable_scan.get_publisher_count() == 0 and not queues["reliable"]
        self.report["qos"] = dict(scanGraphPublishers=len(actual_endpoints), offered="BEST_EFFORT",
                                  bestEffortMatched=scan.get_publisher_count(), reliableMatched=0,
                                  bestEffortSamples=len(queues["scan"]), reliableSamples=0)

        # 给跨进程队列一个短暂排空窗口。测的是已暂停后的采集时戳和 ROS 时钟，不只相信回执。
        control(True)
        self.observe(0.22)
        frozen = node.get_clock().now().nanoseconds
        tracked = ("image", "info", "scan", "cloud", "edges")
        stopped_stamps = {key: stamp(queues[key][-1]) for key in tracked}
        self.observe(0.40)
        assert frozen >= running > initially and node.get_clock().now().nanoseconds == frozen
        assert ns(queues["clock"][-1].clock) == frozen
        assert all(stamp(queues[key][-1]) == value for key, value in stopped_stamps.items())
        control(False)
        self.wait(lambda: node.get_clock().now().nanoseconds > frozen and
                  all(stamp(queues[key][-1]) > value for key, value in stopped_stamps.items()), "恢复后采样未推进")
        self.report["clock"] = dict(initialNs=initially, runningNs=running, pausedNs=frozen, pausedWindowSteadyS=0.40,
                                    resumedNs=node.get_clock().now().nanoseconds, pausedSensorStampsNs=stopped_stamps)
        self.report["clock"]["resumedSensorStampsNs"] = {key: stamp(queues[key][-1]) for key in tracked}

        pairs = same_frame_triplets()
        raw, info, edge = pairs[-1]
        assert raw.header.frame_id == info.header.frame_id == edge.header.frame_id == OPTICAL
        assert raw.width == info.width == edge.width == 96 and raw.height == info.height == edge.height == 64
        assert raw.encoding == "rgb8" and raw.step == 96 * 3 and len(raw.data) == raw.step * raw.height
        assert edge.encoding == "mono8" and edge.step == 96 and len(edge.data) == edge.step * edge.height
        focal_px = 96 / (2 * math.tan(math.pi / 6))
        assert math.isclose(info.k[0], focal_px, abs_tol=0.02) and math.isclose(info.k[4], focal_px, abs_tol=0.02), list(info.k)
        bgr = image_bridge.imgmsg_to_cv2(raw, "bgr8")
        outline = image_bridge.imgmsg_to_cv2(edge, "mono8")
        blue, green, red = map(int, bgr[32, 48])
        nonzero = int(cv2.countNonZero(outline))
        assert red > max(blue, green) + 30 and nonzero > 0, ([blue, green, red], nonzero)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gray_count = int(cv2.countNonZero(cv2.Canny(gray, 40, 120)))
        for name, image in (("camera.png", bgr), ("edges.png", outline)):
            assert cv2.imwrite(str(self.output / name), image)
        self.report["camera"] = dict(sizePx=[raw.width, raw.height], encoding=raw.encoding, rowBytes=raw.step,
                                     dataBytes=len(raw.data), matchingTriplets=len(pairs), stampNs=stamp(raw), frame=OPTICAL,
                                     k=list(info.k), centerRgb=[red, green, blue], edgeEncoding=edge.encoding,
                                     edgeRowBytes=edge.step, redEdgePixels=nonzero, grayEdgePixelsSameThreshold=gray_count,
                                     imageSha256={name: sha(self.output / name) for name in ("camera.png", "edges.png")})

        scans, clouds = ({stamp(msg): msg for msg in queues[key]} for key in ("scan", "cloud"))
        lidar, cloud = (samples[max(scans.keys() & clouds.keys())] for samples in (scans, clouds))
        assert lidar.header.frame_id == cloud.header.frame_id == LASER
        assert len(lidar.ranges) == 41 and math.isclose(lidar.angle_min + 20 * lidar.angle_increment, 0.0, abs_tol=1e-5)
        assert lidar.range_min <= lidar.ranges[20] <= lidar.range_max
        assert math.isclose(lidar.ranges[20], 2.20, abs_tol=0.03)
        assert all(not math.isfinite(lidar.ranges[i]) for i in (0, 40))
        # 桥不会凭 SDF 更新率填入 LaserScan 的逐束和逐圈时长。
        assert lidar.scan_time == lidar.time_increment == 0.0
        scan_times = sorted(scans)
        self.report["scan"] = dict(stampNs=stamp(lidar), frame=LASER, beams=len(lidar.ranges),
                                  angleMinRad=lidar.angle_min, angleStepRad=lidar.angle_increment,
                                  centerRangeM=lidar.ranges[20], finiteRanges=sum(map(math.isfinite, lidar.ranges)),
                                  scanTimeS=lidar.scan_time, beamTimeIncrementS=lidar.time_increment,
                                  successiveHeaderIntervalsS=[(b - a) / 1e9 for a, b in zip(scan_times, scan_times[1:])])
        self.report["cloud"] = cloud_fields(cloud, PointField.FLOAT32)
        assert math.dist(self.report["cloud"]["centerM"], [2.20, 0.0, 0.0]) < 0.03

        frame_probes = []
        for frame, header, unit in ((OPTICAL, raw.header, (0.0, 0.0, 1.0)), (LASER, lidar.header, (1.0, 0.0, 0.0))):
            when = Time.from_msg(header.stamp)
            self.wait(lambda: tf_buffer.can_transform(BASE, frame, when), "按采集时戳查询静态 TF")
            probe = PointStamped()
            probe.header = header
            probe.point.x, probe.point.y, probe.point.z = unit
            projected = do_transform_point(probe, tf_buffer.lookup_transform(BASE, frame, when)).point
            result = [projected.x, projected.y, projected.z]
            assert math.dist(result, [1.0, 0.0, 0.0]) < 1e-9
            frame_probes.append(dict(source=frame, target=BASE, headerStampNs=ns(header.stamp), inputM=unit, outputM=result))
        self.report["tf"] = frame_probes
        control(True)
        listener.unregister()

    def close(self):
        try:
            if self.executor is not None:
                self.executor.shutdown(timeout_sec=2.0)
            if self.node is not None:
                self.node.destroy_node()
            if self.context is not None and self.context.ok():
                self.context.shutdown()
        finally:
            for process, record in reversed(self.processes):
                # -s 只启动 Gazebo 服务端。先给自建进程一次 INT；异常才升级其专用进程组。
                for sig, seconds in ((signal.SIGINT, 5), (signal.SIGTERM, 2), (signal.SIGKILL, 2)):
                    if process.poll() is not None:
                        break
                    try:
                        if sig == signal.SIGINT:
                            process.send_signal(sig)
                        else:
                            os.killpg(process.pid, sig)
                        record["signals"].append(sig.name)
                        process.wait(timeout=seconds)
                    except (subprocess.TimeoutExpired, ProcessLookupError):
                        continue
                path = Path(record["logFile"])
                record.update(returnCode=process.poll(), pidGone=not Path("/proc", str(process.pid)).exists(),
                              logSha256=sha(path), logTail=path.read_bytes()[-5000:].decode(errors="replace"))


def main():
    args = arguments()
    if os.environ.get("ROS_DISTRO") != "jazzy":
        raise SystemExit("请先加载 ROS 2 Jazzy。")
    output = Path(tempfile.mkdtemp(prefix="ros2-gz-sensor-"))
    (output / "fuel").mkdir()
    # 设各自的发现边界，去除继承的跨机发现配置。只使用本例几何，不下载 Fuel 模型。
    for key in ("ROS_LOCALHOST_ONLY", "ROS_STATIC_PEERS", "ROS_DISCOVERY_SERVER", "FASTDDS_DEFAULT_PROFILES_FILE",
                "FASTRTPS_DEFAULT_PROFILES_FILE", "GZ_RELAY"):
        os.environ.pop(key, None)
    os.environ.update(ROS_DOMAIN_ID=str(args.domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
                      RMW_IMPLEMENTATION="rmw_fastrtps_cpp", SKIP_DEFAULT_XML="1",
                      ROS_LOG_DIR=str(output / "ros-log"), ROS_HOME=str(output / "ros-home"),
                      GZ_PARTITION="hub_" + output.name.rsplit("-", 1)[-1], GZ_IP="127.0.0.1",
                      GZ_FUEL_CACHE_PATH=str(output / "fuel"), MESA_SHADER_CACHE_DISABLE="true")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    report = dict(passed=False, domainId=args.domain_id, discovery="LOCALHOST", output=str(output),
                  gazeboPartition=os.environ["GZ_PARTITION"], gazeboIp=os.environ["GZ_IP"], versions={},
                  sourceHashes={name: sha(HERE / name) for name in ("validate_sensors.py", "sensors.sdf", "bridge.yaml")},
                  controlReplies=[], processes=[])
    lab = Lab(output, report)
    try:
        lab.run(args.egl_vendor_json)
    except (Exception, KeyboardInterrupt):
        report["error"] = traceback.format_exc()
        print(report["error"], end="")
    finally:
        lab.close()
    report["passed"] = ("error" not in report and len(report["processes"]) == 2 and
                        all(p["returnCode"] == 0 and p["pidGone"] and p["signals"] == ["SIGINT"]
                            for p in report["processes"]))
    data = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    (output / "report.json").write_text(data)
    if args.report:
        with args.report.open("x") as target:
            target.write(data)
    print(json.dumps(dict(passed=report["passed"], report=str(output / "report.json")), ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
