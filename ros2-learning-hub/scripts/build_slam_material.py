#!/usr/bin/env python3
"""把运动扫描、SLAM 位姿图恢复和滚动定位的实测写入教材。

输入为本机及解压复跑报告、主试验的扫描和地图文件、固定版本上游源码。
先核指纹和实测判据，再生成正文及 SVG。坐标和误差以 m、rad 记录，SVG 布局以像素计。
"""
from collections import Counter
from html import escape
from itertools import groupby
import json
import math
from pathlib import Path

from build_drive_material import exercise, section, sha, vector, verified_sources
from build_theory_figures import text

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "validation-evidence"
REPORT = EVIDENCE / "slam-mapping-current-validation.json"
PORTABLE = EVIDENCE / "slam-mapping-portable-current-validation.json"
FINDING = EVIDENCE / "slam-localization-raster-finding.json"
CAPTURES = EVIDENCE / "slam-mapping-captures"
FILES = {"validate_slam.py": "python", "scan_run.py": "python", "slam.yaml": "yaml", "bridge.yaml": "yaml"}
SLAM = "SteveMacenski--slam_toolbox"
GZ = "gazebosim--ros_gz"
NAV = "ros-navigation--navigation2"
MESSAGES = "ros2--common_interfaces"

REFERENCES = {
    "slam-lab-gz-bridge": (GZ, "jazzy", "Gazebo 世界控制、移位与里程计桥接",
        "桥接的实体位姿和世界步进走服务通道，激光和参考位姿走独立消息通道。里程计演示提供 OdometryPublisher 配置。",
        ("ros_gz_bridge/src/service_factories/ros_gz_interfaces.cpp", "ros_gz_interfaces/srv/SetEntityPose.srv",
         "ros_gz_interfaces/msg/WorldControl.msg", "ros_gz_sim_demos/worlds/vehicle.sdf",
         "ros_gz_sim_demos/README.md", "ros_gz_bridge/package.xml")),
    "slam-lab-laserscan": (MESSAGES, "jazzy", "激光扫描与里程计的坐标和时间字段",
        "LaserScan 的角度使用 rad、距离使用 m。Odometry 的 pose 和 twist 分别依照 header.frame_id 与 child_frame_id。",
        ("sensor_msgs/msg/LaserScan.msg", "nav_msgs/msg/Odometry.msg")),
    "slam-lab-message-filter": ("ros2--geometry2", "jazzy", "TF 消息过滤器的等待与目标帧",
        "消息过滤使用消息帧及采集时戳等待目标坐标系，过滤成功之后才进入算法回调。",
        ("tf2_ros/include/tf2_ros/message_filter.hpp",)),
    "slam-lab-input-pipeline": (SLAM, "jazzy", "SLAM Toolbox 的输入过滤、地图发布和 TF 时戳",
        "扫描订阅使用 Sensor Data QoS。消息过滤、基座位姿查询、门限、栅格缓存与 map 到 odom 的发布时间分别处理。",
        ("src/slam_toolbox_common.cpp", "include/slam_toolbox/get_pose_helper.hpp", "package.xml")),
    "slam-lab-sync": (SLAM, "jazzy", "同步建图队列、异步入口与启动生命周期",
        "同步节点在通过输入检查后入队，由工作线程逐帧处理。对照异步回调和同步启动文件的生命周期选项。",
        ("src/slam_toolbox_sync.cpp", "src/slam_toolbox_async.cpp", "launch/online_sync_launch.py")),
    "slam-lab-saver": (SLAM, "jazzy", "栅格保存服务和真实回执",
        "SLAM Toolbox 等待已发布地图，再转交 Nav2 的地图保存命令。业务 result 与服务可见性分开。",
        ("src/map_saver.cpp", "srv/SaveMap.srv")),
    "slam-lab-map-writer": (NAV, "jazzy", "Nav2 MapSaver 的命令、阈值与地图原点",
        "保存器按图像模式生成像素，并在 YAML 中写分辨率与三位小数的平移原点。地图重载仍要核对原点。",
        ("nav2_map_server/src/map_saver/main_cli.cpp", "nav2_map_server/src/map_saver/map_saver.cpp",
         "nav2_map_server/src/map_io.cpp", "nav2_map_server/package.xml")),
    "slam-lab-serialization": (SLAM, "jazzy", "位姿图与扫描数据的二进制保存",
        "序列化使用同一文件前缀写图和数据两份二进制文件，加载时分别读取。服务类型区分保存结果和空的恢复响应。",
        ("include/slam_toolbox/serialization.hpp", "srv/SerializePoseGraph.srv", "srv/DeserializePoseGraph.srv")),
    "slam-lab-localization": (SLAM, "jazzy", "图定位节点的加载模式和清理服务",
        "定位节点检查匹配模式，按地图坐标中的初始位姿启动。定位缓冲可通过空服务清理。",
        ("src/slam_toolbox_localization.cpp", "config/mapper_params_localization.yaml")),
    "slam-lab-rolling-buffer": (SLAM, "jazzy", "Karto 的短期定位扫描与栅格重建",
        "短期扫描进入 Karto 定位缓冲与活动图，清理时移除相应扫描和约束。占据图由当前已处理扫描集合栅格化。",
        ("lib/karto_sdk/src/Mapper.cpp", "src/slam_mapper.cpp")),
    "slam-lab-graph-markers": (SLAM, "jazzy", "位姿图节点与线列表标记",
        "普通和短期定位节点有不同标记，边以两个端点表示。可用 MarkerArray 统计本次可见节点和约束。",
        ("src/loop_closure_assistant.cpp",)),
    "slam-lab-ceres": (SLAM, "jazzy", "Ceres 的二维位姿图残差与锚点",
        "用约束协方差的逆形成信息矩阵，对角误差做角度归一化，固定首节点的 x、y 和偏航。",
        ("solvers/ceres_solver.cpp", "solvers/ceres_utils.h")),
    "slam-lab-theory-course": ("existing--Robotics_Tutorial", "main", "机器人教程的 SLAM 前端与后端",
        "结合教程对观测、数据关联、残差和优化的划分，区分视觉里程计概念与本章的二维激光实现。",
        ("03_SLAM/10_SLAM理论/10_SLAM理论基础.md",)),
    "slam-lab-ros2-course": ("existing--ros2_tutorial", "main", "ROS2 教程的建图、地图管理与导航串联",
        "保留课程组织与图约束示意。工程中的图文件和 ROS 服务以固定版本的二进制序列化与接口定义为准。",
        ("chapter11.md",)),
    "slam-lab-linorobot-launch": ("existing--linorobot2", "jazzy", "Linorobot2 异步建图的启动与参数",
        "建图入口包含 SLAM Toolbox 异步启动和 Nav2 navigation_launch。用实际包含文件和参数核时钟、帧与模式。",
        ("linorobot2_navigation/launch/slam.launch.py", "linorobot2_navigation/config/slam.yaml")),
}


def same_raster(comparison):
    return comparison["cells"] > 0 and comparison["changedCells"] == 0


def accepted(poses):
    return [row for row in poses if row["acceptedPose"]]


def odom_error(pose):
    return math.dist(pose["truth"][:2], pose["odom"][:2])


def verified_evidence():
    """先核报告、源码和原始采样的同源性，再允许正文引用测量值。"""
    report, portable, finding = (json.loads(path.read_text()) for path in (REPORT, PORTABLE, FINDING))
    expected = {"slam_labs/" + name for name in FILES} | {
        "nav2_labs/nav_room.sdf", "nav2_labs/validate_nav2.py", "gazebo_labs/validate_sensors.py",
    }
    if not report["passed"] or not portable["passed"] or report["domainId"] == portable["domainId"]:
        raise ValueError("需要两个不同域的通过报告")
    if set(report["sourceHashes"]) != expected or report["sourceHashes"] != portable["sourceHashes"]:
        raise ValueError("两次运行的源文件集合或指纹不一致")
    if portable["sourceArchive"]["verifiedSourceFiles"] != len(expected):
        raise ValueError("解压工程的运行文件未逐个核对")
    for name, digest in report["sourceHashes"].items():
        if sha(ROOT / "examples" / name) != digest:
            raise ValueError("运行文件已变化：" + name)
    captures = {name: item["sha256"] for name, item in report["artifacts"]["files"].items()}
    capture = report["capture"]
    captures.update({capture["sampleFile"]: capture["sampleSha256"], "mapping_room.sdf": capture["sceneSha256"]})
    for name, digest in captures.items():
        if sha(CAPTURES / name) != digest:
            raise ValueError("原始采样指纹不一致：" + name)
    trajectory = json.loads((CAPTURES / capture["sampleFile"]).read_text())
    samples = trajectory["samples"]
    if (len(samples) != capture["samples"] or trajectory["mappingSamples"] != capture["mappingSamples"]
            or any(row["stampNs"] != row["poseStampNs"] or len(row["ranges"]) != capture["raysPerSample"]
                   for row in samples)):
        raise ValueError("采集帧与参考位姿不能逐个配对")
    if (finding["currentReportSha256"] != sha(REPORT)
            or finding["observedAgain"] != report["localization"]["rollingMapCompared"]
            or finding["afterClearing"] != report["localization"]["clearedMapCompared"]):
        raise ValueError("定位反例与当前报告不一致")

    for run in (report, portable):
        capture, mapping, artifacts, restore, loc = (
            run[key] for key in ("capture", "mapping", "artifacts", "restore", "localization"))
        if (capture["exactPosePairs"] != capture["samples"] or capture["maxPairDeltaNs"] != 0
                or capture["samples"] != capture["mappingSamples"] + capture["heldOutSamples"]
                or mapping["captureClockStayedNs"] != capture["captureEndNs"] or mapping["saveBeforeMapCode"] != 1
                or mapping["badFrame"]["acceptedPose"] or mapping["acceptedPoses"] != len(accepted(mapping["poses"]))):
            raise ValueError("采集或 SLAM 输入边界未复现")
        last = accepted(mapping["poses"])[-1]
        if (last["positionErrorM"] >= odom_error(last) or last["captureNs"] != mapping["lookupStampNs"]
                or mapping["transformStampNs"] - mapping["lookupStampNs"] != 200_000_000):
            raise ValueError("建图估计或 TF 时戳对照缺失")
        if (artifacts["rasterServiceCode"] != 0 or artifacts["graphServiceCode"] != 0
                or not same_raster(artifacts["rasterCompared"]) or not same_raster(restore["compared"])
                or restore["matchType"] != 1 or restore["missingPrefixMapCells"] or restore["wrongModeMapCells"]
                or restore["missingPrefixResponseFields"] or restore["wrongModeResponseFields"] or restore["responseFields"]
                or restore["beforeReplayMap"]["stampNs"] != 0 or restore["continuationSaveCode"] != 0
                or restore["continuedGraph"]["mappingNodes"] != restore["graph"]["mappingNodes"] + len(accepted(restore["continuation"]))):
            raise ValueError("栅格、位姿图恢复或继续建图对照缺失")
        if (loc["matchType"] != 3 or not loc["originalGraphFilesIntact"]
                or not same_raster(loc["loadedMapCompared"]) or not same_raster(loc["clearedMapCompared"])
                or loc["rollingMapCompared"]["changedCells"] <= 0
                or sum(loc["rollingCellTransitions"].values()) != loc["rollingMapCompared"]["changedCells"]
                or loc["rollingGraph"]["localizationNodes"] != len(accepted(loc["poseResults"]))
                or loc["rollingGraph"]["mappingNodes"] != restore["graph"]["mappingNodes"]
                or loc["clearedGraph"]["localizationNodes"] or loc["clearedGraph"]["localizationEdges"]):
            raise ValueError("定位缓冲变化和清空对照缺失")
        if (len(run["lifecycle"]) != 16 or not all(row["success"] for row in run["lifecycle"])
                or len(run["processes"]) != 6 or any(row["returnCode"] != 0 or not row["pidGone"]
                or row["signals"] != ["SIGINT"] for row in run["processes"])):
            raise ValueError("节点或进程回收证据缺失")
    return report, portable, trajectory, captures


def measured(title, columns, rows, caption):
    return dict(title=title, columns=columns, rows=rows, caption=caption,
                evidenceFile=REPORT.relative_to(ROOT).as_posix(), evidenceSha256=sha(REPORT))


def save_figure(report, trajectory):
    """从真实栅格和逐帧位姿绘图，距离沿采集参考轨迹累加。"""
    mapping = report["mapping"]
    grid = mapping["learnedMap"]
    width, height = grid["size"]
    resolution = grid["resolutionM"]
    origin_x, origin_y = grid["originM"]
    raster = (CAPTURES / "learned.occupancy").read_bytes()
    unknown_counts = {0: "0", 100: "100", 255: "-1"}
    cells = Counter(unknown_counts[value] for value in raster)
    if len(raster) != width * height or cells != grid["cells"]:
        raise ValueError("图解底图必须是实际发布的完整占据栅格")

    title = "同一圈扫描的占据图、轨迹与误差"
    description = "左侧为实测占据图叠加 Gazebo 参考路线、注入偏差的里程计和 SLAM 位姿。右侧比较每次接受扫描时的平面位置误差。"
    blue, green, orange, ink = "#565caa", "#08796b", "#ad521e", "#23283b"
    palette = {0: "#f8faf7", 100: "#303749", 255: "#c8c9dd"}
    left, top, pixel = 60, 133, 3.17
    plot_width, plot_height = width * pixel, height * pixel

    def map_xy(x, y):
        return left + (x - origin_x) / resolution * pixel, top + plot_height - (y - origin_y) / resolution * pixel

    def stroke(x1, y1, x2, y2, color, line_width=1):
        return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{line_width}"/>'

    def route(points, project, color, line_width, dash=""):
        coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in (project(*point) for point in points))
        return (f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{line_width}" '
                f'stroke-dasharray="{dash or "none"}" stroke-linecap="round" stroke-linejoin="round"/>')

    def dot(x, y, color, radius=4):
        return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="{color}" stroke="#fff" stroke-width="1.4"/>'

    body = text(30, 42, title, 27, ink, 680)
    body += text(30, 70, "Gazebo Harmonic 采集 · Jazzy SLAM Toolbox 2.8.5 · 同一基座位置参考", 15, "#52576c")
    body += text(60, 109, "A　实际发布的占据地图", 21, ink, 650)
    body += text(550, 109, "B　平面位置误差", 21, ink, 650)
    for row in range(height):
        start = 0
        for value, group in groupby(raster[row * width:(row + 1) * width]):
            length = sum(1 for _ in group)
            body += (f'<rect x="{left + start * pixel:.3f}" y="{top + (height - row - 1) * pixel:.3f}" '
                     f'width="{length * pixel + 0.015:.3f}" height="{pixel + 0.015:.3f}" fill="{palette[value]}"/>')
            start += length
    body += (f'<rect x="{left}" y="{top}" width="{plot_width:.2f}" height="{plot_height:.2f}" '
             'fill="none" stroke="#949aab"/>')
    for x in range(-3, 4):
        u, y = map_xy(x, origin_y)
        body += stroke(u, y, u, y + 5, "#949aab") + text(u - 6, y + 19, x, 12)
    for y in range(-2, 3):
        x, v = map_xy(origin_x, y)
        body += stroke(x - 5, v, x, v, "#949aab") + text(x - 24, v + 4, y, 12)
    body += text(463, 471, "x (m)", 12) + text(32, 122, "y (m)", 12)

    kept = accepted(mapping["poses"])
    positions = [row["truth"] for row in trajectory["samples"][:trajectory["mappingSamples"]]]
    distance = [0.0]
    for a, b in zip(positions, positions[1:]):
        distance.append(distance[-1] + math.dist(a[:2], b[:2]))
    if not math.isclose(distance[-1], report["capture"]["traveledM"], abs_tol=1e-7):
        raise ValueError("误差图的路程与报告不一致")
    body += route((p[:2] for p in positions), map_xy, blue, 5)
    body += route((row["odom"][:2] for row in kept), map_xy, orange, 2.4, "6 5")
    body += route((row["estimated"][:2] for row in kept), map_xy, green, 2.1)
    x, y = map_xy(*positions[0][:2])
    body += dot(x, y, blue, 6) + text(x + 9, y + 22, "起终点同一位置", 12, ink, 600)

    graph_left, graph_top, graph_width, graph_height = 590, 154, 351, 246
    errors = [row["positionErrorM"] for row in kept]
    odom = [odom_error(row) for row in kept]
    max_error = math.ceil(max(*errors, *odom) / 0.05) * 0.05

    def chart_xy(path_m, error_m):
        return (graph_left + path_m / distance[-1] * graph_width,
                graph_top + graph_height - error_m / max_error * graph_height)

    body += (f'<rect x="{graph_left}" y="{graph_top}" width="{graph_width}" height="{graph_height}" '
             'fill="#fff" stroke="#d7d9e4"/>')
    for i in range(round(max_error / 0.05) + 1):
        error = 0.05 * i
        x, y = chart_xy(0, error)
        body += stroke(x, y, x + graph_width, y, "#e3e4eb") + text(x - 34, y + 4, f"{error:.2f}", 12)
    for path_m in range(0, int(distance[-1]) + 1, 3):
        x, y = chart_xy(path_m, 0)
        body += stroke(x, y, x, y + 5, "#949aab") + text(x - 5, y + 21, path_m, 12)
    body += text(858, 437, "累计路程 (m)", 13) + text(552, 142, "误差 (m)", 12)
    for values, color, dash in ((odom, orange, "6 5"), (errors, green, "")):
        points = [(distance[row["sample"]], value) for row, value in zip(kept, values)]
        body += route(points, chart_xy, color, 2.8, dash)
        x, y = chart_xy(*points[-1])
        body += dot(x, y, color) + text(x - 78, y - 11, f"{values[-1]:.4f} m", 14, color, 680)

    for x, color, label, dash in ((60, blue, "Gazebo 参考", ""), (210, orange, "注入偏差的里程计", "6 5"),
                                  (400, green, "SLAM 输出", "")):
        body += route(((x, 498), (x + 25, 498)), lambda u, v: (u, v), color, 3, dash)
        body += text(x + 34, 503, label, 14, ink)
    for x, value, label in ((590, 0, "空闲"), (698, 100, "占据"), (810, 255, "未知")):
        body += f'<rect x="{x}" y="490" width="15" height="15" rx="2" fill="{palette[value]}" stroke="#949aab"/>'
        body += text(x + 21, 503, label, 14, ink)
    body += text(60, 535, f"{width} × {height} 格 · {resolution:.2f} m/格 · {len(kept)} 个位姿回执", 15, "#52576c")
    body += text(590, 535, "x 偏差每走 1 m 加 0.014 m", 15, "#52576c")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 980 556" role="img" aria-labelledby="title desc">'
           f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>'
           '<rect width="980" height="556" fill="#f8f6fb"/><g font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif">'
           + body + '</g></svg>\n')
    identifier = "slam-mapping-trajectory"
    file = f"preview/figures/{identifier}.svg"
    target = ROOT / "dist" / file
    target.write_text(svg)
    manifest = ROOT / "source/design-figures.json"
    data = json.loads(manifest.read_text())
    data["figures"] = [item for item in data["figures"] if item["id"] != identifier]
    data["figures"].append(dict(id=identifier, title=title, alt=description, file=file, kind="实测图",
        caption="底图是 SLAM Toolbox 实际发布的占据栅格。路线取采集参考、注入偏差的里程计和接受扫描后的位姿回执。估计误差按采集参考位姿计算。",
        evidenceFile=REPORT.relative_to(ROOT).as_posix(), evidenceSha256=sha(REPORT), assetSha256=sha(target),
        placements=[dict(chapter="eco-slam-mapping", afterSection=9), dict(chapter="theory-slam", afterSection=6)]))
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def chapter_material(report, portable):
    capture, mapping, artifacts, restore, local = (
        report[key] for key in ("capture", "mapping", "artifacts", "restore", "localization"))
    accepted_poses = accepted(mapping["poses"])
    last = accepted_poses[-1]
    maximum_error = max(pose["positionErrorM"] for pose in accepted_poses)
    odom_heading_error = abs((last["odom"][2] - last["truth"][2] + math.pi) % (2 * math.pi) - math.pi)
    occupied_error = max(row[3] for row in mapping["geometryChecks"]["nearestOccupiedM"])
    distance = capture["traveledM"]
    compared_cells = artifacts["rasterCompared"]["cells"]
    old_graph, new_graph = restore["graph"], restore["continuedGraph"]
    early, learned = mapping["initialMap"], mapping["learnedMap"]
    raster_delta = artifacts["rasterCompared"]["originDeltaM"]
    bad_stamp = mapping["badFrame"]["replayNs"] / 1e9
    scan_stamp, tf_stamp = (mapping[key] / 1e9 for key in ("lookupStampNs", "transformStampNs"))
    local_graph = local["rollingGraph"]
    changed = local["rollingMapCompared"]["changedCells"]

    capture_table = measured("离散移位、采集时戳与扫描准入", ["检查", "本次观测", "解释"], [
        ["激光与参考位姿", f"{capture['exactPosePairs']}/{capture['samples']} 对同戳",
         f"每对含 {capture['raysPerSample']} 束距离，采集窗 0.40 s，激光高 {capture['lidarHeightM']:.2f} m"],
        ["盒形场景对照", f"各帧绝对距离误差的 P95 最大为 {capture['maxRangeP95ErrorM']:.5f} m",
         "解析射线与 GPU 激光比对，用于核对几何、角度和单位"],
        ["错误扫描帧", f"{bad_stamp:.2f} s 的 unlinked_laser 无位姿",
         "时钟和基座里程计已提供，扫描帧到目标 odom 仍缺变换"],
        ["修正后的建图回放", f"{len(accepted_poses)}/{capture['mappingSamples']} 条扫描有位姿",
         "首帧通过，接下来的三条静止预热帧无新位姿，随后依次接收路线扫描"],
        ["采集时钟隔离", f"{mapping['captureClockStayedNs'] / 1e9:.2f} s",
         "采集结束后 Gazebo 保持暂停，SLAM 使用单独重映射的回放时钟"],
    ], f"路线按离散位置采集，每个采样窗内台架静止。保留的 {capture['heldOutSamples']} 帧用于后续恢复和定位。")

    def map_row(label, grid):
        width, height = grid["size"]
        cells = grid["cells"]
        return [label, f"{width} × {height}", str(cells["0"]), str(cells["100"]), str(cells["-1"]),
                vector(grid["originM"], 5)]
    map_table = measured("首帧与整圈之后的实测占据图", ["阶段", "尺寸（格）", "空闲", "占据", "未知", "原点 x / y（m）"], [
        map_row("首个有效扫描", early), map_row("最后一个建图扫描", learned),
    ], f"分辨率约 {learned['resolutionM']:.2f} m/格。两张图的尺寸与原点发生变化，面积比较要先对齐到同一空间范围。")
    restore_table = measured("同一张图的栅格重载与位姿图恢复", ["操作", "回执与产物", "后验检查"], [
        ["首图产生前 SaveMap", f"result={mapping['saveBeforeMapCode']}", "报告没有新文件"],
        ["有图后 SaveMap", f"result={artifacts['rasterServiceCode']} · learned.pgm + learned.yaml",
         f"新 MapServer 的 {compared_cells} 格逐格一致，平移原点差 {raster_delta:.6f} m"],
        ["SerializePoseGraph", f"result={artifacts['graphServiceCode']} · learned.posegraph + learned.data",
         f"{old_graph['mappingNodes']} 个建图节点，{old_graph['mappingEdges']} 条建图约束"],
        ["恢复缺失前缀或匹配类型不符", "两次响应都没有字段", "新同步节点的地图仍为空"],
        ["同步节点 START_AT_FIRST_NODE", "响应没有字段", f"回放前已复原全部 {compared_cells} 格和原位姿图"],
        ["恢复后继续提供留存扫描", f"{len(accepted(restore['continuation']))} 条新增位姿",
         f"新前缀保存 {new_graph['mappingNodes']} 个建图节点和 {new_graph['mappingEdges']} 条约束"],
    ], "用有效地图、位姿图标记与文件指纹验收。恢复前的空回执和成功后的空回执具有相同的消息结构。")

    pose_table = measured("沿采集路线对照输入偏差与估计误差", ["观测", "里程计输入", "SLAM 输出"], [
        ["第一帧平面误差", f"{odom_error(accepted_poses[0]):.4f} m", f"{accepted_poses[0]['positionErrorM']:.4f} m"],
        ["终点平面误差", f"{odom_error(last):.4f} m", f"{last['positionErrorM']:.4f} m"],
        ["终点绝对偏航误差", f"{odom_heading_error:.5f} rad",
         f"{last['yawErrorRad']:.5f} rad"],
        ["已接收帧中最大平面误差", f"{max(odom_error(row) for row in accepted_poses):.4f} m",
         f"{maximum_error:.4f} m"],
    ], "各误差均以同帧 Gazebo 参考位姿计算。位姿回执是每帧在线输出，图标记记录的是相应阶段发布的图节点。")

    local_table = measured("图定位加入短期扫描后再清空缓冲",
        ["阶段", "建图节点", "短期定位节点", "短期约束", "相对原图的差异格"], [
        ["以原图加载且还未回放", str(old_graph["mappingNodes"]), "0", "0",
         str(local["loadedMapCompared"]["changedCells"])],
        ["定位扫描已接受", str(local_graph["mappingNodes"]), str(local_graph["localizationNodes"]),
         str(local_graph["localizationEdges"]), str(changed)],
        ["清空定位缓冲后重读", str(local["clearedGraph"]["mappingNodes"]), "0", "0",
         str(local["clearedMapCompared"]["changedCells"])],
    ], "比较覆盖原点和尺寸相同的整张图。两份原位姿图文件的 SHA 在定位过程前后相同。")

    versions = report["versions"]
    runtime = (f"在本机 Jazzy SLAM Toolbox {versions['slam_toolbox']}、Nav2 MapServer {versions['nav2_map_server']}、"
               f"Harmonic 8.15.0 和 ros_gz_bridge {versions['ros_gz_bridge']} 实测。"
               f"主试验域 {report['domainId']}，解压原创示例包后在域 {portable['domainId']} 重跑。")
    scope = "采集使用离散移位和静止采样窗。轮地运动、扫描运动畸变、强制回环、远处重定位和跨版本图文件兼容性待测。"
    transitions = local["rollingCellTransitions"]

    chapters = {
        "eco-slam-mapping": dict(validation=runtime + scope, appendSourceIds=[
            "slam-lab-input-pipeline", "slam-lab-sync", "slam-lab-saver", "slam-lab-map-writer",
            "slam-lab-serialization", "slam-lab-ros2-course", "slam-lab-graph-markers",
        ], appendSections=[
            section("用真实仿真回波检验采集与回放合同", [
                f"台架按长方形路线设置多处位姿，总路程 {distance:.2f} m。每处先用世界服务移位，再推进 80 个 0.005 s 步长，在稳定窗口里配对激光与 Gazebo 位姿。俯视盒形场景另算射线交点，用相同角度和基座位姿核对距离。",
                "原始位姿流只作测量参考。回放驱动先供独立时钟和 TF，再送原始 LaserScan 距离。每走 1 m 给里程计 x 加 0.014 m、给偏航加 0.002 rad，得到可单独核算的偏差。首轮保留采集时戳，ROS 的处理次序通过回执检查。",
                "固定源码中，LaserScan 先经 Sensor Data QoS 与朝 odom 的 TF 消息过滤，回调再查询扫描时刻的基座位姿和传感器安装。同步实现把通过门限的帧排入队列，异步实现从回调走自己的处理路径。",
                "首次测量允许通过。后续需同时看暂停、节流、最小时间间隔和预热逻辑。测试启用了精确距离与转角判定，距离与转角都低于各自阈值时跳过。错误帧和故意留出的静止预热用于核对这两类边界。",
            ], [capture_table]),
            section("从有效位姿跟到实际发布的地图", [
                f"首帧后记录占据图，完成整圈后再记录地图和位姿图。整圈有 {len(accepted_poses)} 个位姿回执，图标记给出 {old_graph['mappingNodes']} 个节点和 {old_graph['mappingEdges']} 条建图约束。四个路线拐角都可在最终图上查到空闲格，四处已知墙面或障碍探针到最近占据格的最大距离约 {occupied_error:.4f} m。",
                "固定同步节点在完成建图前已更新扫描 Header。驱动先等同戳位姿，再清空旧接收缓存并等一次地图发布，最后核对 dynamic_map 的数据和话题一致。固定实现要求地图发布端已激活且有订阅者，动态地图服务读取缓存。",
                f"最后一个扫描时刻是 {scan_stamp:.2f} s。restamp_tf 关闭时，map 到 odom 的发布时戳为 {tf_stamp:.2f} s，即扫描加 0.20 s。验收使用扫描时刻查询 map 到 laser_link，实际保留约 {mapping['mapToLaserZ']:.2f} m 的激光安装高度。",
            ], [map_table]),
            section("新进程分别重载栅格、恢复图并继续建图", [
                "先用 SLAM Toolbox 的 SaveMap 保存 PGM/YAML。然后用 SerializePoseGraph 按一个路径前缀保存图和扫描数据。两份二进制文件来自固定版的 Boost 归档，复跑时保留原配对和生成版本。ROS2 教程第 11 章的 YAML 节点和边适合说明数据结构，工程运行依赖实际接口定义与二进制文件。",
                f"将 learned.yaml 单独交给新 MapServer。它重载的 {compared_cells} 个占据值与原图逐格相等。YAML 保存平移原点时保留三位小数，本次 xy 差约 {raster_delta * 1000:.3f} mm。下游复用时仍要检查分辨率、帧、原点和格值。",
                "关闭原建图节点，启动新的同步建图节点。请求字段包含前缀、匹配类型与可选初始位姿。缺失前缀和误用图定位模式都给出空响应，只有首节点模式实际恢复地图。还未重放扫描时，恢复栅格的 Header 时间为零，其格值、原点和节点数已能独立检查。",
                f"继续提供 {capture['heldOutSamples']} 帧留存数据，{len(accepted(restore['continuation']))} 帧产生新位姿。使用不同的 continued 前缀保存新图，保留旧图以复现初始条件。两种前缀各保留成对文件，回执之外再检查图标记与文件指纹。",
            ], [restore_table]),
        ], appendExercises=[
            exercise("第一帧之前 SaveMap 已能调用，怎样确定有可发布的文件？",
                     "看 result。实测首图前返回 1 且没有新文件。收到有效 OccupancyGrid 后重试，核对 PGM/YAML 是否成对、再让新 MapServer 实际读取。"),
            exercise("同步建图节点收到了空的 DeserializePoseGraph 响应，该如何验收？",
                     "空响应是接口结构。确认生命周期与匹配类型，再等待有效栅格，核对图节点和格值。缺前缀、匹配类型不符、成功恢复三种情况都要分别观察。"),
            exercise("首帧和最后一帧图的未知格相差很多，能直接换算成新探索的面积吗？",
                     "先在共同坐标系与网格边界上对齐地图。原点和尺寸发生变化时，两次数组索引的空间含义不同。用重采样或同一范围的索引再比较。"),
        ]),
        "theory-slam": dict(validation="Python 标准库数值实验及断言已执行。" + runtime + scope,
            appendSourceIds=["slam-lab-ceres", "slam-lab-graph-markers", "slam-lab-theory-course"],
            appendSections=[
                section("在实际二维位姿图里区分约束、锚点与误差", [
                    "Robotics_Tutorial 用视觉里程计、关联、优化和回环来拆分 SLAM。放到二维激光案例，扫描匹配和里程计给相对状态估计，后端用约束联合调整位姿。固定版 Ceres 求解器取约束协方差的逆并作 Cholesky 分解，用上三角因子对白化残差；偏航误差先归一化。首个节点的 x、y 和偏航参数被固定以选定参考。",
                    f"本次轨迹的首末 xy 接近重合，末帧偏航改变约 {abs(last['truth'][2] - accepted_poses[0]['truth'][2]):.3f} rad。MarkerArray 给出 {old_graph['mappingNodes']} 个节点和 {old_graph['mappingEdges']} 条建图约束。边数表示当前连接，若要把一条边归因为回环，还需记录约束类型或回环事件。",
                    "将每个接受帧的估计与独立采集位姿逐帧配对，再报告平面和偏航误差。图中的橙线输入是已知的注入偏差，青线是 ROS 位姿回执。结果反映这套几何和同一配置下的改正程度，初值、场景和走法会影响误差。",
                ], [pose_table]),
            ], appendExercises=[
                exercise("每走 1 m 在 x 方向注入 0.014 m 偏差。用本次路线计算末端平面误差，再比较实际估计。",
                         f"{distance:.2f} × 0.014 = {odom_error(last):.4f} m。其余平移分量未加偏差，所以是本例平面误差。终点估计误差为 {last['positionErrorM']:.4f} m。"),
                exercise("图里有 37 个节点和 38 条约束，怎样确认回环？",
                         "先记录优化前后的位姿和新增边的两端。结合求解器或 SLAM 节点的约束类型、匹配事件与接受条件，区分邻接匹配和跨段回环。"),
            ]),
        "eco-state-estimation": dict(validation="软件差速与局部 EKF 在域 225 实测。固定激光 AMCL 在域 229 及 230 实测，另核近真值初值、无运动更新和扫描时刻 TF。"
            + runtime + "图定位从已知初值启动。IMU、GNSS、运动底盘和全局重定位精度各需独立验收。",
            appendSourceIds=["slam-lab-localization", "slam-lab-rolling-buffer", "slam-lab-graph-markers"],
            appendSections=[
                section("图定位的短期扫描会进入实时栅格", [
                    "使用另一个定位进程，选择 LOCALIZE_AT_POSE，输入地图中的基座 x、y 和偏航。此例用接近已知的参考位姿启动。AMCL 的先验栅格与粒子分布另有上一节实测，局部 EKF 则继续负责局部状态。部署时为同一 map 到 odom 边选一个发布者。",
                    f"定位进程先恢复原栅格，再回放留存帧。回放时钟、动态 TF 和扫描统一加 {local['replayShiftNs'] / 1e9:.0f} s，保留时间顺序。得到 {len(accepted(local['poseResults']))} 个定位位姿，最大平面误差约 {local['maxPositionErrorM']:.5f} m。",
                    f"最初的夹具预期实时栅格始终和载入时一致，两轮均实际观察到 {changed} 个差异格。由空闲到占据 {transitions['0→100']} 格，由未知到占据 {transitions['-1→100']} 格，由未知到空闲 {transitions['-1→0']} 格。固定实现的短期扫描进入 Karto 的定位缓冲，栅格化使用当前处理过的扫描集合。",
                    f"调用 clear_localization_buffer，再读取新图与 MarkerArray。定位节点与短期约束消失，{compared_cells} 格恢复到载入时的数据，原始 .posegraph 和 .data 文件的 SHA 一致。地图时戳仍沿用上一帧扫描，清理结果要看栅格和图结构。",
                ], [local_table]),
            ], appendExercises=[
                exercise("定位过程中发布的地图变了 8 格，哪些结果能说明发生了什么？",
                         "比较短期节点和边、三类格值转移、清空后的栅格以及原始文件 SHA。此实验定位缓冲可复原，持久图文件仍是原配对。"),
            ]),
        "project-navigation": dict(validation="局部轮反馈与 EKF 在域 225、226 实测。NavigateToPose 客户端另有十二类假服务端协议验证。"
            "固定台架实测 MapServer、AMCL、全局代价地图和 NavFn。" + runtime
            + "此建图台架按位姿采集并回放。完整行为树、控制器、车轮驱动与硬件待分别验收。",
            appendSourceIds=["slam-lab-linorobot-launch", "slam-lab-sync", "slam-lab-serialization"],
            appendSections=[
                section("复跑采集、建图和图恢复，再接导航层", [
                    "在完整教材目录加载本机 Jazzy 环境，运行 `python3 examples/slam_labs/validate_slam.py --domain-id 231`。解压原创工程后从 atlas_examples 运行 `python3 slam_labs/validate_slam.py --domain-id 232`。域号是隔离示例，执行时选本机未使用的域。需要无窗口 Ogre2 EGL、SLAM Toolbox 与 Nav2 MapServer。",
                    "脚本复用同包 nav2_labs 的房间和服务辅助以及 gazebo_labs 的有界等待。它生成临时目录保存原始扫描、图和报告。Gazebo 默认时钟用于采集，回放时钟和实际算法节点同属隔离空间。回放提供 odom 到 base_link，静态发布安装边，SLAM 提供 map 到 odom。",
                    "Linorobot2 建图入口包含 online_async_launch.py 和 Nav2 navigation_launch.py。此台架使用同步节点和明确的分段生命周期。迁移时核对 sim 对 use_sim_time 的传递、基座与激光帧、scan 的实际话题、局部 TF 发布者和互斥的全局定位入口。",
                    "分开备份原始轨迹、PGM/YAML 与位姿图对。前两类便于重放与导航地图，位姿图供继续建图和图定位。先证明重载后地图坐标和格值，再以同一地图合同接入规划、控制和行为树。",
                ], code=[dict(label="slam_labs/" + name, language=language, type="complete",
                              sourceFile="examples/slam_labs/" + name) for name, language in FILES.items()]),
            ], appendExercises=[
                exercise("如何让接手工程的同学分别重载地图、继续建图和回放原始观测？",
                         "交接 PGM/YAML、成对位姿图和扫描轨迹三组文件。附 ROS 包版本、命名空间、帧、时钟和校验值。分别让 MapServer、新同步节点和回放脚本验证各自输入。"),
            ]),
        "eco-gazebo-simulation": dict(validation="固定相机与激光在 Harmonic 8.15.0 和 Jazzy ros_gz_bridge 1.0.24、域 227/228 实测。"
            + runtime + "移动路径采用离散移位，GUI、轮地动力学与物理传感器待验收。",
            appendSourceIds=["slam-lab-gz-bridge", "slam-lab-laserscan"], sections={"7": dict(appendParagraphs=[
                "SLAM 实验另使用 UserCommands 的实体位姿服务与世界步进，验证服务应答后读取同戳激光和位姿。OdometryPublisher 的世界参考位姿经独立话题进入 ROS，桥只改激光帧标签，回放另提供实际安装 TF。每处先移位再在稳定窗口采样，采集期间保留仿真 Header。",
            ])}),
        "eco-tf-frames": dict(appendSourceIds=["slam-lab-message-filter", "slam-lab-input-pipeline"],
            sections={"2": dict(appendParagraphs=[
                f"SLAM 台架把错误激光帧放在有效回放时间窗内，缺少该帧到 odom 的可用链时无位姿回执。随后以 laser_link 和真实安装关系恢复，最终用 {scan_stamp:.2f} s 的采集时刻查询到 map 到 laser_link。TF 消息过滤器按消息帧和时戳等待目标帧，算法还会另查基座运动边。",
            ])}),
        "time-bag": dict(appendSourceIds=["slam-lab-laserscan", "slam-lab-input-pipeline"],
            sections={"8": dict(appendParagraphs=[
                "SLAM 台架的 trajectory.json 是已记录扫描及参考位姿的实验输入。这里由驱动自行重放，时钟和 TF 与扫描明确配对，Gazebo 采集钟仍停在独立话题。本章前面的 SQLite/MCAP 实验提供 rosbag2 的存储和 CLI 证据，两条回放路线各有自己的格式与验证记录。",
            ])}),
        "eco-nav2-stack": dict(validation="固定激光台架在 Jazzy Nav2 1.3.13 实测 MapServer、AMCL、全局代价地图和 NavFn。"
            + runtime + "两个分段台架使用各自的地图与运行时序。完整 NavigateToPose 行为树、控制器、运动底盘和硬件待分别验收。",
            appendSourceIds=["slam-lab-saver", "slam-lab-map-writer", "slam-lab-serialization"],
            sections={"7": dict(appendParagraphs=[
                f"SLAM 章另把实际建图生成的 PGM/YAML 交给新 MapServer，验证 {compared_cells} 格一致。此节 80 × 60 图来自固定房间的先验几何，后续 NavFn 对照仍使用该输入。迁移到实测地图时重新核对地图边界、初始位姿与代价地图各层。",
            ])}),
        "qos": dict(appendSourceIds=["slam-lab-input-pipeline"],
            sections={"4": dict(appendParagraphs=[
                "SLAM Toolbox 固定版的 map 与 map_metadata 使用深度一的可靠、瞬态本地发布端。有效地图仍由已激活的发布端与扫描处理产生。重启后通过文件恢复地图是独立过程，可用新的进程、实际格值和原点检查。",
            ])}, appendExercises=[
                exercise("为什么位姿图恢复前后都有服务回执，而地图主题的行为不同？",
                         "服务发现、端点 QoS、地图是否已生成是三个检查。用相同的订阅策略，再看有效地图尺寸、内容与实际发布者。"),
            ]),
    }
    api = dict(id="api-slam-map-lifecycle", title="SLAM Toolbox 的扫描、地图与位姿图接口",
        lessons=["eco-slam-mapping", "eco-state-estimation", "project-navigation"],
        columns=["接口", "输入与单位", "实际输出或检查", "边界"],
        rows=[
            ["LaserScan 与 TF", "距离 m，角度 rad，Header 为采集时刻", "按扫描帧等目标 odom，再查基座运动", "到达话题后仍可因缺 TF 或门限跳过"],
            ["map / dynamic_map", "订阅可靠瞬态本地地图，GetMap 为空请求", "OccupancyGrid 和地图元数据", "固定实现读取缓存，空图与未发布要分开"],
            ["SaveMap", "name 为栅格输出前缀", "PGM/YAML，result 0 为成功", "首图前本次 result=1"],
            ["SerializePoseGraph", "filename 为图文件前缀", ".posegraph + .data，result 0 为成功", "两份文件一起备份，版本和来源随图记录"],
            ["DeserializePoseGraph", "match_type 为 1、2 或 3，地图初值用 m、rad", "固定版响应无字段", "本次同步恢复用 1，图定位用 3。2 由接口定义列出"],
            ["clear_localization_buffer", "std_srvs/Empty", "短期图节点、边和栅格可重新观察", "定位进程提供，回执无业务字段"],
        ], notes=["命名空间用于 ROS 名称隔离。TF frame 字符串仍须按同一棵树规划。"])
    return chapters, api


def main():
    report, portable, trajectory, captures = verified_evidence()
    resources, reads = verified_sources(REFERENCES, category="SLAM 与图定位 · 固定参考")
    chapters, api = chapter_material(report, portable)
    save_figure(report, trajectory)
    material = dict(meta=dict(checkedAt="2026-11-07",
        report=REPORT.relative_to(ROOT).as_posix(), reportSha256=sha(REPORT),
        portableReport=PORTABLE.relative_to(ROOT).as_posix(), portableReportSha256=sha(PORTABLE),
        finding=FINDING.relative_to(ROOT).as_posix(), findingSha256=sha(FINDING),
        captureHashes=captures, sourceReads=reads), chapters=chapters, resources=resources, apiReferences=[api])
    output = ROOT / "source/slam-mapping-revision.json"
    output.write_text(json.dumps(material, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(chapters=len(chapters), sources=len(resources), checkedSourceFiles=len(reads),
        sections=sum(len(c.get("appendSections", [])) for c in chapters.values()), tables=5, figures=1)))


if __name__ == "__main__":
    main()
