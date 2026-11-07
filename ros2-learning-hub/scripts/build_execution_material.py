#!/usr/bin/env python3
"""从 Nav2 实跑、解压复跑和固定参考生成导航执行教材。

速度命令的时间是旁路接收时的 ROS 时钟，世界位姿使用 Gazebo 的采样时戳。
两条序列只在已知同一仿真时基下并列绘制，不将差值解释为传输延迟。
"""
from html import escape
from itertools import groupby
import json
import math
from pathlib import Path

from build_drive_material import exercise, section, sha, verified_sources
from build_theory_figures import text

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "validation-evidence"
REPORT = EVIDENCE / "nav2-execution-current-validation.json"
PORTABLE = EVIDENCE / "nav2-execution-portable-current-validation.json"
READINESS = EVIDENCE / "nav2-execution-readiness-finding.json"
STOP_FINDING = EVIDENCE / "nav2-execution-stop-finding.json"
CAPTURES = EVIDENCE / "nav2-execution-captures"
SLAM_INPUT = EVIDENCE / "slam-mapping-captures"
FILES = {"validate_execution.py": "python", "mobile_base.sdf": "xml", "navigation.yaml": "yaml", "bridge.yaml": "yaml"}
NAV = "ros-navigation--navigation2"
GZ = "gazebosim--ros_gz"

REFERENCES = {
    "navexec-default-tree": (NAV, "jazzy", "默认导航行为树的重规划与分级恢复",
        "安装树与固定源码的 XML 指纹相同。树中分开运行规划、跟踪、局部恢复和通用恢复，动作节点通过黑板传递路径及错误码。",
        ("nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml",
         "nav2_behavior_tree/plugins/control/pipeline_sequence.cpp", "nav2_behavior_tree/plugins/decorator/rate_controller.cpp")),
    "navexec-bt-runtime": (NAV, "jazzy", "行为树执行、终态与事件时间",
        "导航器使用自身 TF 缓存初始化，树结束后汇总黑板错误码。行为树批次时间和内部事件时间由不同层提供。",
        ("nav2_behavior_tree/include/nav2_behavior_tree/bt_action_server_impl.hpp",
         "nav2_bt_navigator/src/bt_navigator.cpp", "nav2_bt_navigator/src/navigators/navigate_to_pose.cpp",
         "nav2_behavior_tree/include/nav2_behavior_tree/ros_topic_logger.hpp", "nav2_util/src/robot_utils.cpp")),
    "navexec-bt-actions": (NAV, "jazzy", "规划与跟踪 Action 节点及取消路径",
        "跟踪节点可以在上游更新路径时更新子目标。行为树停下动作节点时使用相应子目标的取消路径。",
        ("nav2_behavior_tree/include/nav2_behavior_tree/bt_action_node.hpp",
         "nav2_behavior_tree/plugins/action/compute_path_to_pose_action.cpp", "nav2_behavior_tree/plugins/action/follow_path_action.cpp")),
    "navexec-action-fields": (NAV, "jazzy", "NavigateToPose、子动作与事件消息字段",
        "上层结果、下级业务码、当前位姿反馈和事件批次分属不同消息。跟踪反馈中的 speed 由控制命令计算。",
        ("nav2_msgs/action/NavigateToPose.action", "nav2_msgs/action/ComputePathToPose.action",
         "nav2_msgs/action/FollowPath.action", "nav2_msgs/msg/BehaviorTreeLog.msg", "nav2_msgs/msg/BehaviorTreeStatusChange.msg")),
    "navexec-status": ("ros2--rcl_interfaces", "jazzy", "动作状态与按 UUID 取消",
        "状态列表可观察终态和目标 ID。CancelGoal 的应答确认哪些目标已进入取消流程。",
        ("action_msgs/msg/GoalStatus.msg", "action_msgs/msg/GoalStatusArray.msg", "action_msgs/srv/CancelGoal.srv")),
    "navexec-selector": (NAV, "jazzy", "控制器选择与恢复条件",
        "ControllerSelector 的输入可靠且瞬态本地。无效控制器 ID 与规划越界分别可通过下级回执确认，默认树按错误码决定恢复。",
        ("nav2_behavior_tree/plugins/action/controller_selector_node.cpp",
         "nav2_behavior_tree/plugins/condition/would_a_controller_recovery_help_condition.cpp",
         "nav2_behavior_tree/plugins/condition/would_a_planner_recovery_help_condition.cpp")),
    "navexec-controller": (NAV, "jazzy", "控制器循环、进度与到达检查",
        "ControllerServer 负责选插件、更新路径、计算反馈、终态和置零。进度与目标容差由不同插件处理。",
        ("nav2_controller/src/controller_server.cpp", "nav2_controller/plugins/simple_goal_checker.cpp",
         "nav2_controller/plugins/simple_progress_checker.cpp")),
    "navexec-rpp": (NAV, "jazzy", "调节型纯追踪的前视、曲率和碰撞投影",
        "截取并变换路径，按前视点计算曲率，再按曲率、代价、趋近阶段和局部代价图限制速度。",
        ("nav2_regulated_pure_pursuit_controller/src/regulated_pure_pursuit_controller.cpp",
         "nav2_regulated_pure_pursuit_controller/src/parameter_handler.cpp",
         "nav2_regulated_pure_pursuit_controller/src/path_handler.cpp",
         "nav2_regulated_pure_pursuit_controller/src/collision_checker.cpp")),
    "navexec-smoother": (NAV, "jazzy", "速度平滑器的闭环反馈与限速",
        "输入为控制器或恢复行为的速度，闭环读取里程计，按加减速限制生成下游速度。超时基于节点时钟。",
        ("nav2_velocity_smoother/src/velocity_smoother.cpp", "nav2_util/src/odometry_utils.cpp",
         "nav2_util/include/nav2_util/twist_publisher.hpp")),
    "navexec-bringup": (NAV, "jazzy", "导航启动文件、命名空间与生命周期",
        "标准启动文件包含速度重映射及生命周期管理。内嵌地图节点在各自子空间，需要核对实际输入和就绪状态。",
        ("nav2_bringup/launch/navigation_launch.py", "nav2_lifecycle_manager/src/lifecycle_manager.cpp",
         "nav2_costmap_2d/src/costmap_2d_ros.cpp", "nav2_costmap_2d/plugins/static_layer.cpp",
         "nav2_costmap_2d/plugins/obstacle_layer.cpp")),
    "navexec-gazebo-model": ("gazebosim--ros_gz_project_template", "main", "官方模板的差速模型与世界结构",
        "参考模型的轮轴、差速插件和世界装配。本文小车为独立 SDF，只使用本地几何和已有系统插件。",
        ("ros_gz_example_description/models/diff_drive/model.sdf", "ros_gz_example_gazebo/worlds/diff_drive.sdf")),
    "navexec-bridge": (GZ, "jazzy", "速度、里程计、关节与 TF 的桥接",
        "Twist、Odometry、Model 关节数据和 Pose_V 通过各自类型转换。轮积分数据与仿真世界参考按不同话题采集。",
        ("ros_gz_bridge/src/convert/nav_msgs.cpp", "ros_gz_bridge/src/convert/sensor_msgs.cpp",
         "ros_gz_bridge/src/convert/geometry_msgs.cpp", "ros_gz_bridge/src/convert/tf2_msgs.cpp")),
    "navexec-linorobot": ("existing--linorobot2", "jazzy", "Linorobot2 的旋转包装器与速度配置",
        "导航工程用 RotationShimController 包装 RPP。参数与本台架不同，移植时核查基座帧、速度链及目标容差。",
        ("linorobot2_navigation/config/navigation.yaml",)),
    "navexec-agro": ("existing--AgroSenseBot", "jazzy", "AgroSenseBot 对前视和碰撞检查的工程实现",
        "农业工程有自己的路径处理与碰撞检查，可与本次原生 Nav2 RPP 对照阅读。运行范围各自记录。",
        ("asb_regulated_pure_pursuit_controller/src/path_handler.cpp",
         "asb_regulated_pure_pursuit_controller/src/collision_checker.cpp",
         "asb_regulated_pure_pursuit_controller/README.md", "asb_nav/config/nav2_params/nav2_params.yaml")),
    "navexec-community": ("existing--ros2_tutorial", "main", "ROS2 教程的导航树、纯追踪与恢复",
        "教程用车式转向角说明纯追踪，并分类讲解恢复。本实验对照差速车的曲率与角速度关系和 Jazzy 安装树。",
        ("chapter12.md",)),
}


def load(path):
    return json.loads(path.read_text())


def verify():
    """核实双份运行、源码、前一轮地图和原始采样的一致性。"""
    primary, portable = load(REPORT), load(PORTABLE)
    expected_sources = {"nav2_execution/" + name for name in FILES} | {
        "nav2_labs/nav_room.sdf", "nav2_labs/validate_nav2.py", "gazebo_labs/validate_sensors.py"}
    assert primary["passed"] and portable["passed"] and primary["domainId"] != portable["domainId"]
    assert set(primary["sourceHashes"]) == expected_sources and primary["sourceHashes"] == portable["sourceHashes"]
    assert portable["sourceArchive"]["verifiedSourceFiles"] == len(expected_sources)
    for name, digest in primary["sourceHashes"].items():
        assert sha(ROOT / "examples" / name) == digest, name
    for run in (primary, portable):
        assert run["map"]["comparedRaw"] and run["map"]["receivedBytes"] == 13426
        assert set(run["map"]["files"]) == {"learned.yaml", "learned.pgm", "learned.occupancy"}
        for name, digest in run["map"]["files"].items():
            assert sha(SLAM_INPUT / name) == digest, name
        assert len(run["lifecycle"]) == 28 and all(row["success"] for row in run["lifecycle"])
        assert len(run["processes"]) == 9 and all(row["pidGone"] and row["returnCode"] == 0
            and row["signals"] == ["SIGINT"] for row in run["processes"])
        cases = run["scenarios"]
        assert {key: (row["status"], row["errorCode"]) for key, row in cases.items()} == {
            "arrival": (4, 0), "cancel": (5, 0), "outside_map": (6, 204),
            "invalid_controller": (6, 101), "restored_controller": (4, 0),
        }
        cancel = cases["cancel"]
        assert cancel["cancelCode"] == 0 and cancel["cancelingIds"] == [cancel["uuid"]]
        assert any(row["action"] == "follow_path" and row["status"] == 5 for row in cancel["nestedResults"])
        assert all(row["accepted"] and row["truthStop"]["stillUntilNs"] - row["truthStop"]["stillFromNs"] >= 500_000_000
                   for row in cases.values())
    artifacts = {
        primary["scene"]["file"]: primary["scene"]["sha256"],
        primary["telemetry"]["file"]: primary["telemetry"]["sha256"],
        "map.occupancy": primary["map"]["dataSha256"],
    }
    for name, digest in artifacts.items():
        assert sha(CAPTURES / name) == digest, name
    traces = load(CAPTURES / primary["telemetry"]["file"])
    return primary, portable, traces, artifacts


def table(title, columns, rows, caption):
    return dict(title=title, columns=columns, rows=rows, caption=caption,
                evidenceFile=REPORT.relative_to(ROOT).as_posix(), evidenceSha256=sha(REPORT))


def stage_rows(traces, key, stage, time_key):
    return [row for row in traces[key] if stage["sentRosNs"] <= row[time_key] <= stage["windowEndRosNs"]]


def xy(row):
    return row["xM"], row["yM"]


def figure(report, traces):
    """从实际占据字节、Path、Gazebo 位姿和取消后的两级速度生成图解。"""
    arrived, canceled = (report["scenarios"][key] for key in ("arrival", "cancel"))
    width, height = report["map"]["size"]
    resolution = report["map"]["resolutionM"]
    origin_x, origin_y = report["map"]["originM"]
    cells = (CAPTURES / "map.occupancy").read_bytes()
    assert len(cells) == width * height and set(cells) <= {0, 100, 255}
    title = "真实行为树执行：到达、取消与停稳"
    desc = "左图叠加实际规划和 Gazebo 参考轨迹。右图比较同一取消场景的控制器、平滑器和世界速度。"
    purple, teal, orange, navy = "#6159a5", "#087b73", "#ae531e", "#252942"
    colors = {0: "#fbfcfa", 100: "#41475b", 255: "#d5d4e4"}
    left, top, pixel = 54, 127, 3.12
    map_height = pixel * height

    def map_point(x, y):
        return (left + (x - origin_x) / resolution * pixel, top + map_height - (y - origin_y) / resolution * pixel)

    def polyline(points, project, color, size=2.4, dash="none"):
        p = " ".join(f"{x:.2f},{y:.2f}" for x, y in (project(*pair) for pair in points))
        return f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{size}" stroke-dasharray="{dash}" stroke-linejoin="round"/>'

    def line(x1, y1, x2, y2, color="#b7b6c8", dash="none"):
        return f'<line x1="{x1:.2f}" x2="{x2:.2f}" y1="{y1:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-dasharray="{dash}"/>'

    def dot(x, y, color):
        return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{color}" stroke="#fff" stroke-width="1.2"/>'

    body = text(28, 42, title, 26, navy, 650)
    body += text(28, 70, "Jazzy Nav2 · 同一张 SLAM 栅格 · Harmonic 差速车", 15, "#555a72")
    body += text(54, 105, "A　首条路径和世界位姿", 20, navy, 650)
    body += text(540, 105, "B　行驶中取消后的速度", 20, navy, 650)
    for row in range(height):
        first = 0
        for value, run in groupby(cells[row*width:(row+1)*width]):
            count = sum(1 for _ in run)
            body += (f'<rect x="{left+first*pixel:.3f}" y="{top+(height-1-row)*pixel:.3f}" '
                     f'width="{count*pixel+0.02:.3f}" height="{pixel+0.02:.3f}" fill="{colors[value]}"/>')
            first += count
    plan = stage_rows(traces, "plans", arrived, "receivedRosNs")[0]
    paths = {key: stage_rows(traces, "truth", stage, "stampNs") for key, stage in (("arrival", arrived), ("cancel", canceled))}
    body += polyline(plan["pointsM"], map_point, purple, 2.0, "6 4")
    body += polyline((xy(row) for row in paths["arrival"]), map_point, teal, 3.0)
    body += polyline((xy(row) for row in paths["cancel"]), map_point, orange, 3.0)
    for x, y, label, color, dx, dy in (
        (*xy(paths["arrival"][0]), "起点", teal, -12, 24),
        (*arrived["goalM"], "目标", purple, 10, -8),
        (*canceled["cancelPoseM"], "发出取消", orange, -102, -8),
        (*canceled["endM"], "停稳位置", orange, -102, 20),
    ):
        u, v = map_point(x, y)
        body += dot(u, v, color) + text(u + dx, v + dy, label, 13, navy, 600)
    for x in range(-3, 4):
        u, v = map_point(x, origin_y)
        body += line(u, v, u, v+5) + text(u-5, v+20, x, 12)
    for y in range(-2, 3):
        u, v = map_point(origin_x, y)
        body += line(u-5, v, u, v) + text(u-22, v+5, y, 12)
    body += text(444, 468, "x (m)", 12) + text(29, 120, "y (m)", 12)

    t0 = canceled["cancelRequestedRosNs"]
    still_begin = (canceled["truthStop"]["stillFromNs"] - t0) / 1e9
    result_time = (canceled["resultRosNs"] - t0) / 1e9
    t_max = max(1.2, math.ceil((canceled["windowEndRosNs"] - t0) / 4e8) * 0.4)
    chart_left, chart_top, chart_w, chart_h = 582, 151, 351, 227

    def chart_point(t, v):
        return chart_left + (t + 0.4) / (t_max + 0.4) * chart_w, chart_top + chart_h * (1.0 - v / 0.55)

    body += f'<rect x="{chart_left}" y="{chart_top}" width="{chart_w}" height="{chart_h}" fill="#fff" stroke="#d7d9e4"/>'
    for speed in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]:
        x, y = chart_point(0, speed)
        body += line(chart_left, y, chart_left+chart_w, y, "#e2e1eb") + text(chart_left-30, y+4, f"{speed:.1f}", 12)
    for i in range(-1, round(t_max / 0.4) + 1):
        t = i * 0.4
        x, y = chart_point(t, 0)
        body += line(x, y, x, y+5) + text(x-9, y+20, f"{t:.1f}", 12)
    body += text(540, 138, "线速度幅值 (m/s)", 12) + text(797, 421, "距取消请求的时间 (s)", 13)
    for t, color, label, offset, y in (
        (0, navy, "请求", -30, 145), (result_time, purple, "终态", 7, 145),
        (still_begin, teal, "停稳窗开始", -33, 406),
    ):
        x, _ = chart_point(t, 0)
        body += line(x, chart_top, x, chart_top+chart_h, color, "4 3") + text(x+offset, y, label, 12, color, 600)
    for key, stamp_key, value, color in (
        ("controller", "receivedRosNs", lambda r: abs(r["linearMps"]), purple),
        ("smoothed", "receivedRosNs", lambda r: abs(r["linearMps"]), orange),
        ("truth", "stampNs", lambda r: math.hypot(r["vxMps"],r["vyMps"]), teal),
    ):
        points = [((r[stamp_key]-t0)/1e9, value(r)) for r in traces[key]
                  if -0.40 <= (r[stamp_key]-t0)/1e9 <= t_max]
        body += polyline(points, chart_point, color, 2.5)
    identity = lambda x,y: (x,y)
    for x, y, color, label, dash in (
        (54, 495, purple, "首条 NavFn 路径", "6 4"), (220, 495, teal, "到达轨迹", "none"),
        (359, 495, orange, "取消轨迹", "none"), (546, 456, purple, "控制器", "none"),
        (666, 456, orange, "平滑器", "none"), (789, 456, teal, "Gazebo 实测", "none"),
    ):
        body += polyline(((x,y),(x+23,y)), identity, color, 3, dash) + text(x+29,y+4,label,13,navy)
    body += text(54, 529, f"到达位置误差 {arrived['positionErrorM']:.3f} m · 行驶 {arrived['worldTravelM']:.2f} m", 14, navy)
    body += text(546, 504, f"取消请求后实测仍行驶 {canceled['travelAfterCancelM']:.3f} m", 14, navy)
    body += text(546, 529, "命令取旁路接收时刻，世界速度取采样时刻", 12, "#555a72")

    identifier = "nav2-execution-stop"
    relative = f"preview/figures/{identifier}.svg"
    target = ROOT / "dist" / relative
    target.write_text(('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 972 550" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>'
        '<rect width="972" height="550" fill="#f8f6fb"/><g font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif">'
        + body + '</g></svg>\n'))
    manifest = ROOT / "source/design-figures.json"
    data = load(manifest)
    data["figures"] = [item for item in data["figures"] if item["id"] != identifier]
    data["figures"].append(dict(id=identifier, title=title, alt=desc, kind="实测图", file=relative,
        caption="左图底图为实际重载的 SLAM 栅格，线段来自首条 NavFn Path 与 Gazebo 世界位姿。右图用同一仿真时基对照控制器、平滑器和世界速度，停稳按连续采样判据。",
        evidenceFile=REPORT.relative_to(ROOT).as_posix(), evidenceSha256=sha(REPORT), assetSha256=sha(target),
        placements=[dict(chapter="eco-nav2-stack", afterSection=9), dict(chapter="eco-nav2-task-programming", afterSection=8)]))
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def localization_pairs(traces, label):
    """按采样时戳配对，同一位姿反馈可能重复，按时戳去重后计算平面误差。"""
    truth = {row["stampNs"]: row for row in traces["truth"]}
    feedback = {row["poseStampNs"]: row for row in traces["feedback"]
                if row["scenario"] == label and row["frame"] == "map"}
    errors = [math.dist(xy(row), xy(truth[when])) for when, row in feedback.items() if when in truth]
    assert errors, label
    return len(feedback), len(errors), max(errors)


def contents(report, portable, traces):
    cases = report["scenarios"]
    arrived, canceled, outside, invalid, restored = (
        cases[key] for key in ("arrival", "cancel", "outside_map", "invalid_controller", "restored_controller"))
    edges = report["navigationTfWarmup"]
    t0 = canceled["cancelRequestedRosNs"]
    old_stop = load(STOP_FINDING)["earlier"]
    old_ready = load(READINESS)["observed"]
    cell_count = report["map"]["receivedBytes"]
    checked = ["arrival", "cancel", "restored_controller"]
    pairing = [localization_pairs(traces, key) for key in checked]

    def delta(value, anchor=t0):
        return f"{(value-anchor)/1e9:+.3f} s"

    def steady(stage):
        window = stage["truthStop"]
        return f"{(window['stillUntilNs']-window['stillFromNs'])/1e9:.3f} s"

    startup_table = table("启动检查与实际连接的代价图输入", ["阶段", "观测", "通过条件"], [
        ["MapServer", f"{cell_count} 格", "重载前一轮 PGM/YAML，与原始占据数组逐格一致"],
        ["全局代价图", f"{report['endpointRoles']['global_costmap']['receivedCells']} 格，map 系", "内嵌节点订阅本实验的 map"],
        ["局部代价图", f"{report['endpointRoles']['local_costmap']['receivedCells']} 格，odom 系", "内嵌节点订阅本实验的 scan，已有扫描标记"],
        ["导航器的 TF 启动窗", f"{(edges['sharedRangeNs'][1]-edges['sharedRangeNs'][0])/1e9:.3f} s 重叠",
         "实际监听端已发现，启动后的 map → odom 与 odom → base_link 在相同时刻可查"],
        ["速度链", "cmd_vel → velocity_smoother → cmd_vel_smoothed", "单一平滑器发布，桥与旁路监听分别接收"],
    ], "Action 服务发现只是启动的一步。通过话题、坐标系与时间窗后才送入实际目标。")

    motion_table = table("成功回执与停稳后的世界坐标", ["场景", "成功规划路径条数", "实际行驶（m）", "停稳位置误差（m）", "停稳偏航误差（rad）"], [
        [label, str(stage["plans"]), f"{stage['worldTravelM']:.3f}", f"{stage['positionErrorM']:.3f}", f"{stage['yawErrorRad']:.3f}"]
        for label, stage in (("正常到达", arrived), ("切回有效控制器后到达", restored))
    ], f"正常到达路线采样点的最小基座中心净距为 {arrived['minimumCenterClearanceM']:.3f} m。误差来自世界位姿，净距按房间盒形几何计算。")

    terminal_names = {4: "SUCCEEDED", 5: "CANCELED", 6: "ABORTED"}
    status_rows = []
    for title, case in (("正常到达", arrived), ("途中取消", canceled), ("越界目标", outside),
                        ("无效控制器", invalid), ("恢复控制器后到达", restored)):
        nested = "；".join(f"{item['action']} {terminal_names[item['status']]} / {item['errorCode']}"
                           for item in case["nestedResults"])
        status_rows.append([title, "接受", terminal_names[case["status"]], str(case["errorCode"]), nested])
    status_table = table("上层动作与下级动作的实测终态", ["场景", "目标响应", "上层终态", "上层业务码", "下级终态与业务码"],
        status_rows, "下级最近终态按状态消息中的 UUID 读取结果。两次失败先接受目标，随后在不同阶段中止。")

    stop_table = table("一次真实行驶中的取消与停稳时间线",
        ["事件", "相对请求的仿真时间", "证据"], [
        ["发送取消", "+0.000 s", "独立世界位姿已记录可辨认的平移，取消使用同一目标 UUID"],
        ["取消服务回执", delta(canceled["cancelAckRosNs"]), "return_code=0，返回同一 UUID"],
        ["上层取消终态", delta(canceled["resultRosNs"]), "NavigateToPose 为 CANCELED，FollowPath 也已取消"],
        ["控制器最近一次运动后首次零速", delta(canceled["controller"]["firstZeroAfterMotionNs"]), "旁路收到 Twist"],
        ["平滑器最近一次运动后首次零速", delta(canceled["smoothed"]["firstZeroAfterMotionNs"]), "旁路收到送往 Gazebo 桥的 Twist"],
        ["停稳采样窗开始", delta(canceled["truthStop"]["stillFromNs"]), f"持续 {steady(canceled)}，并检查实际两轮速度"],
    ], f"从发出请求到停稳观测结束，世界坐标累计行驶 {canceled['travelAfterCancelM']:.3f} m。命令使用旁路接收时刻，世界位姿使用采样时刻。")

    localization_table = table("移动中用同戳的世界位姿对照导航反馈",
        ["阶段", "去重后的地图位姿", "同戳配对", "最大平面误差（m）"], [
        [label, str(total), str(matches), f"{maximum:.4f}"]
        for label, (total, matches, maximum) in zip(("到达", "取消前后任务反馈", "恢复后到达"), pairing)
    ], "反馈为导航器的 map 系基座位姿，Gazebo 世界参考另由实体系统输出。只比较相同测量时戳。")

    scope = (f"本机 Jazzy Nav2 {report['versions']['nav2_bt_navigator']}、Harmonic 8.15.0、"
             f"ros_gz_bridge {report['versions']['ros_gz_bridge']} 实测。主试验域 {report['domainId']}，"
             f"实际解压示例和地图后在域 {portable['domainId']} 重跑。范围为静态房间的单机器人仿真。")
    chapters = {
        "eco-nav2-stack": dict(validation="先前固定激光台架独立核对 MapServer、AMCL、主代价图和 NavFn。" + scope
            + "本轮安装树实际执行到达、取消、两种失败和恢复到达。动态障碍、实机与跨版本待验。",
            appendSourceIds=["navexec-default-tree", "navexec-bringup", "navexec-bt-runtime", "navexec-smoother"],
            appendSections=[
                section("把已保存的 SLAM 地图接入真实导航执行", [
                    "前面的固定台架将地图、扫描与规划分段验收。本次从同一房间的 learned.yaml 加载已保存地图，接入具有关节、地面接触和实时激光的 Gazebo 差速车。AMCL 使用地图系近参考初值，发布 map 到 odom，轮速积分另供 odom 到 base_link。",
                    "地图和定位就绪后再激活规划、平滑、控制、恢复行为与导航器。全局代价图用先验栅格，局部滚动图从实时扫描标记障碍。此固定版本在嵌套代价地图中解析明确指定的相对话题，驱动按实际节点名重映射到父命名空间，并从图上核对订阅。",
                    f"首轮误将全局地图入口留在子命名空间。导航器仍接受目标，最后报规划超时 207，收到 {old_ready['recoveries']} 次恢复计数和约 {old_ready['worldTravelM']:.2f} m 的世界位移，期间没有实际规划路径。修复后先等完整栅格、局部障碍标记和导航器的共同 TF 时间窗再发目标。",
                    "安装版默认树把规划和跟踪放进可流水推进的序列，规划由 1 Hz 装饰器节流。上游产生的新路径可更新正在执行的 FollowPath。恢复分支按错误类型选择清图、旋转、等待和后退等动作。",
                ], [startup_table]),
                section("同时验收动作成功、终点误差与停稳", [
                    f"首条规划绕开中心箱体。到达阶段实际观察 {arrived['plans']} 条规划和 {arrived['feedbackSamples']} 条上层反馈，独立世界位姿测得路线 {arrived['worldTravelM']:.2f} m。规划路径、车辆轨迹和停车位置分别记录。",
                    "目标检查器根据局部坐标中的估计位姿和配置容差判定到达。行为树终态、控制器置零和车轮稳定有不同触发点。验收先等实际终态，再分别比对两级速度与世界位姿。",
                    "世界坐标的中心净距只在观测到的参考点上计算。局部控制器自身使用代价图足迹检查。若更改机器人外形、地图或采样频率，需重新评估运动几何与停稳。",
                ], [motion_table]),
            ], appendExercises=[
                exercise("动作服务已可调用，为什么还要验证代价地图和 TF 后再发目标？",
                    "服务就绪证明目标通道已发现。用有效栅格、实际订阅和两条动态边的共同时间窗检查执行输入，才能排除本实验的规划超时与初始位姿失败。"),
                exercise("全局图和局部图为什么使用不同帧？",
                    "全局图对齐已保存地图并服务整段路径。局部滚动图在 odom 中保持短程运动连续，由扫描更新附近障碍。通过带时戳的 map 到 odom 将两者接起来。"),
            ]),
        "eco-nav2-task-programming": dict(validation="有界客户端仍有独立假服务端验证。实际行为树与下级动作：" + scope
            + "本轮验证五个任务分支和停稳。多目标调度、抢占及硬件待验。",
            appendSourceIds=["navexec-action-fields", "navexec-status", "navexec-selector", "navexec-bt-actions", "navexec-community"],
            appendSections=[
                section("按目标 UUID 核对上层、下级和取消回执", [
                    "发送标准 NavigateToPose 目标，behavior_tree 字段留空以使用安装版默认树。记录目标响应、持续反馈、取消响应和最终业务结果。上层有自己的目标 UUID，规划器和控制器的子目标也各自有独立 UUID。",
                    f"取消试验先通过世界位姿确认车辆平移，再按当前目标 UUID 发送取消。上层终态在请求后约 {(canceled['resultRosNs']-t0)/1e9:.3f} s 收到。下级 FollowPath 的最后终态也是 CANCELED。停止证据来自后续轮反馈与世界位姿。",
                    "越界目标在规划阶段返回 204，无效控制器在成功规划后由 FollowPath 返回 101。恢复有效控制器 ID 后，同一地图系目标可重新到达。目标是否被接受、动作状态和业务码需要分别记录。",
                    "本章的通用有界客户端只依赖公开动作协议。台架为诊断订阅子动作状态主题，从真实 UUID 读取最近一次终态的详细结果。行为树事件的发布批次和内部时间分别保留。",
                ], [status_table]),
                section("结合恢复条件解释同为 ABORTED 的结果", [
                    "ROS2 教程第 12 章先用规划、跟踪和恢复把流程分层。固定 Jazzy 默认树中的条件会按黑板错误码判断是否值得恢复。越界目标和无效控制器在本次直接中止，未产生非零底盘命令。",
                    "另一次启动反例中，两张代价图已收到，导航器自己的 TF 历史尚缺共同时间。目标先被接受，随后因初始位姿不可用而中止，业务码为 0，行为树尚未进入规划与跟踪。此时查看顶层状态、节点日志和事件数。",
                    "向可靠、瞬态本地的 controller_selector 发布错误 ID 可以受控复现实验。再发布有效的 FollowPath 后新目标恢复。此路径只操作隔离仿真内的选择器。实际部署将选择权限与业务取消权限分开。",
                ]),
            ], appendExercises=[
                exercise("取消服务返回 0 后，哪几项证据分别对应协议和车辆？",
                    "核对 goals_canceling 的 UUID、上层 CANCELED、对应下级终态。然后核对平滑后速度、轮速和世界位姿在停稳窗口的变化。"),
                exercise("业务码为 0 时，怎样区分成功、取消和初始化失败？",
                    "读动作状态，再看业务码、最早执行事件与日志。实测成功与取消都可报 0，启动 TF 不可用也出现过 ABORTED 与 0。"),
                exercise("越界与无效控制器如何从子动作诊断？",
                    "越界的 ComputePathToPose 为 ABORTED / 204。无效 ID 已取得路径，FollowPath 为 ABORTED / 101。分别核对地图边界和已配置控制器名称。"),
            ]),
        "eco-control-framework": dict(validation="GenericSystem 差速和局部 EKF 仍按软件台架独立验证。" + scope
            + "本轮测 Gazebo 关节、轮速里程计及独立世界参考，实机停机和故障制动待验。",
            appendSourceIds=["navexec-controller", "navexec-rpp", "navexec-smoother"],
            appendSections=[
                section("从速度置零追到仿真车实际停稳", [
                    "ControllerServer 用 RPP 计算 Twist，恢复行为有同一个原始速度入口。平滑器闭环读取轮积分里程计，根据加减速参数和速度上限发布下游命令。桥只把平滑后的速度送给 Gazebo DiffDrive，旁路同时记录前后两路。",
                    f"最早的 0.85 rad/s 终点转向使动作已成功时车辆仍在减速，最终偏航误差 {old_stop['yawErrorRad']:.3f} rad，超过 0.28 rad 的台架判据。调整为 0.45 rad/s 后重新实测，并为较慢的原地转向保留进度时间。当前主试验停稳偏航误差 {arrived['yawErrorRad']:.3f} rad。",
                    f"行驶中取消后，按世界参考取平移速度不超过 0.018 m/s、偏航速度不超过 0.055 rad/s 的连续窗口。本次取消后的停稳窗口采到 {canceled['truthStop']['samples']} 帧，并独立核对两个关节速度。",
                    "取消终态、零速度消息、车体速度下降与停止距离应使用各自的测量量。无 Header 的速度消息只记录接收时钟。里程计和世界位姿保留发布端采样时戳，端到端通讯延迟需要另设同步测量。",
                ], [stop_table]),
            ], appendExercises=[
                exercise("如果导航已经返回成功，但停稳偏航超差，优先对照哪些曲线？",
                    "在同一仿真时基对照终点转向命令、平滑器角速度、世界偏航与轮速。检查目标容差、转向速度和减速余量后复验停稳角度。"),
            ]),
        "eco-state-estimation": dict(validation="软件 EKF、固定激光 AMCL 与 SLAM 图定位分别有原报告。" + scope
            + "本轮移动 AMCL 从近参考初值启动。远处重定位、IMU/GNSS 与实机精度另验。",
            appendSourceIds=["navexec-bt-runtime", "navexec-bridge"],
            appendSections=[
                section("用世界采样对照移动时的 AMCL 导航反馈", [
                    "仿真车轮关节生成里程计和 odom 到基座，AMCL 结合地图与实际扫描发布 map 到 odom。世界位姿只作旁路参考。导航器反馈的地图位姿来自它自己的 TF 缓存，记录时保留采样时戳。",
                    "把重复反馈按位姿时戳去重，再与 Gazebo 世界位姿配对。相同帧名的坐标值可能由多个模块获得，比较前须核实采样时基、参考原点和相同的基座点。",
                    f"初始 TF 误差约 {report['initialPose']['positionErrorM']:.4f} m。导航器晚启动时再核两条动态边的重叠窗口。在这套静态房间和近参考初值下测得的误差，和上一节加载原图后用短期扫描定位的配置各自记录。",
                ], [localization_table]),
            ], appendExercises=[
                exercise("为什么要按位姿 Header 去重，不能直接用反馈消息数量代表定位更新频率？",
                    "行为树反馈循环可以重复使用最近一次 TF 位姿。按位姿采样时戳去重，配对同戳世界参考，再统计定位误差与有效样本数。"),
            ]),
        "theory-planning": dict(appendSourceIds=["navexec-rpp", "navexec-community", "navexec-agro"],
            appendSections=[
                section("把全局路径转成差速车前视控制量", [
                    "ROS2 教程的车式纯追踪用轴距和转向角描述同一转弯几何。对平面差速车，把前视点转到基座坐标系，设其坐标为 x、y，曲率 `κ = 2y / (x² + y²)`，单位为 1/m。分母趋近零时实际实现使用边界检查。",
                    "差速运动用 `ω = vκ`，角速度为 rad/s，线速度为 m/s。RPP 会按配置裁剪前视距离并用曲率、障碍代价和趋近目标的速度限制重新决定 v，还根据局部代价图检查有限投影轨迹。",
                    "固定版 RPP 的路径处理与 AgroSenseBot 自带的前视和碰撞实现都可以在章末打开。实际导航测试使用 Nav2 安装版的 RPP，农业工程另按其路径、外形和插件配置检验。",
                    f"本次 Gazebo 到达路线实测 {arrived['worldTravelM']:.2f} m，期间发布了 {arrived['plans']} 条规划。全局几何提供跟踪参考，控制器和平滑器通过反馈决定每次速度，最终路线应以世界采样复核。",
                ]),
            ], appendExercises=[
                exercise("前视点位于基座 (0.4, 0.2) m，若 v=0.30 m/s，差速车该有多大角速度？",
                    "曲率为 2×0.2/(0.4²+0.2²)=2 1/m，角速度为 0.60 rad/s。实际控制还会按速度和碰撞检查调整。"),
            ]),
        "project-navigation": dict(validation="固定图、SLAM 与假服务端协议均保留独立记录。" + scope
            + "已跑从地图与定位到导航器、控制器、平滑器和差速车反馈的完整链路。实物与跨版本执行待验。",
            appendSourceIds=["navexec-bringup", "navexec-gazebo-model", "navexec-linorobot", "navexec-agro"],
            appendSections=[
                section("复跑已保存地图上的导航与停车", [
                    "在教材目录加载 Jazzy，运行 `python3 examples/nav2_execution/validate_execution.py --map-yaml validation-evidence/slam-mapping-captures/learned.yaml --domain-id 223`。从下载区分别解压原创示例和验证记录时，脚本路径改为 nav2_execution/validate_execution.py，地图指向实际解压目录。环境和 EGL 参数见工程说明。",
                    "启动时先通过真实消息确认时钟、激光、关节与里程计，再配置导航。两次运行分别核对七份运行源码和三个地图输入。报告带已安装的默认行为树指纹，XML 与固定源码一致。",
                    "Linorobot2 的控制器配置使用旋转包装器组合 RPP。本实验直接加载 RPP，并观察原始速度与闭环平滑后的速度。移植到项目时逐项核对包装层、坐标基座、Twist 类型、滤波和停稳验收。",
                    "所有等待都以单调墙钟设置上界，取仿真时戳做行为对照。停用顺序让控制器先于平滑器退出。读取生命周期状态超时时可再读一次，修改状态及发送目标不自动重复。",
                ], code=[dict(label="nav2_execution/" + name, language=language, type="complete",
                              sourceFile="examples/nav2_execution/" + name) for name, language in FILES.items()]),
            ], appendExercises=[
                exercise("怎样在换机后确认实跑仍使用同一地图和同一棵行为树？",
                    "对照输入 PGM/YAML/占据数组、安装版 XML 和运行源码指纹。然后在本机独立域重新采样，核实地图、动作终态、坐标误差与停车边界。"),
            ]),
        "eco-diff-drive-tracks": dict(appendSourceIds=["navexec-gazebo-model", "navexec-bridge", "navexec-smoother"],
            sections={"6": dict(appendParagraphs=[
                "导航执行台架的两轮半径为 0.09 m、间距 0.32 m。真实仿真轮关节随平滑后 Twist 转动，DiffDrive 用两轮积分发布 odom，独立 Gazebo 系统发布世界参考。前者可与差速方程对照，后者包含轮地接触后的实际仿真运动。",
                "本节软件控制器的命令过期机制有独立试验。导航执行里的停稳来自控制器置零、平滑器减速与仿真反馈，验收分别看两路 Twist 与轮速。正式底盘的制动和急停仍按其驱动协议测试。",
            ])}),
        "eco-gazebo-simulation": dict(validation="固定相机、激光桥接和 SLAM 离散扫描各有独立报告。" + scope
            + "本轮加入仿真差速关节与地面。GUI、硬件和动态人车环境另验。",
            appendSourceIds=["navexec-gazebo-model", "navexec-bridge"],
            sections={"7": dict(appendParagraphs=[
                "导航运行台架保留六个房间障碍的碰撞和视觉尺寸，给车辆加入地面、驱动轮、随动球与 GPU 激光。桥从 Gazebo 单向传时钟、扫描、两类里程计与关节，从 ROS 单向传平滑速度。控制运行阶段靠轮关节驱动车体。",
            ])}),
        "eco-slam-mapping": dict(appendSourceIds=["navexec-bringup"], sections={"10": dict(appendParagraphs=[
            f"完整导航台架沿用这一对 PGM/YAML，在同一房间里让实际差速车执行任务。启动后再按原 OccupancyGrid 核 {cell_count} 格，并用地图系初值启动 AMCL。导航运行使用栅格，留存的位姿图仍供本章的继续建图与图定位。",
        ])}),
        "actions": dict(appendSourceIds=["navexec-status", "navexec-action-fields"], sections={"6": dict(appendParagraphs=[
            "真实 NavigateToPose 台架中，按当前目标 UUID 取消后收到取消应答和上层终态，随后还能测到平滑指令与车辆继续移动。取消响应说明协议状态推进，停稳需另等世界位姿或实际反馈。机器人任务章节给出三个时刻与额外位移的原始对照。",
        ])}),
        "lifecycle": dict(appendSourceIds=["navexec-bringup"], sections={"8": dict(appendParagraphs=[
            "导航台架按依赖手动配置和激活七个生命周期节点，按相反顺序停用清理。活跃状态之后再核实际传感器、代价图和 TF。官方启动文件的生命周期管理器还涉及绑定与故障处理，这部分由固定源码说明，台架记录的是本次手动切换。",
        ])}),
    }
    api = dict(id="api-nav2-execution", title="真实导航执行中的回执、路径与反馈", lessons=[
        "eco-nav2-stack","eco-nav2-task-programming","project-navigation"],
        columns=["接口", "数据与单位", "观察结果", "边界"],
        rows=[
            ["NavigateToPose", "地图 PoseStamped，位置 m、偏航 rad", "目标响应、反馈、动作状态、error_code", "默认树由空 behavior_tree 字段选用"],
            ["ComputePathToPose", "起终点和 planner_id", "实际 Path，例中越界码 204", "路径本身无法表达已行驶或已停"],
            ["FollowPath", "Path、controller_id 与检查器 ID", "控制终态，例中无效控制器码 101", "反馈 speed 源自计算的速度指令"],
            ["取消目标", "当前目标 UUID", "CancelGoal 响应与对应终态", "用车体和关节观测验收停车"],
            ["BehaviorTreeLog", "发布批次与内部事件各有时钟字段", "节点 ID、旧状态与新状态", "两层时钟分别解释"],
            ["控制与平滑速度", "Twist，线 m/s、角 rad/s", "原始命令、平滑输出", "实际车体与轮速另用同一仿真时基对照"],
        ], notes=["本台架控制与桥接都显式选择 Twist，迁移其他版本时以各端实际消息类型为准。"])
    return chapters, api


def main():
    primary, portable, traces, artifacts = verify()
    resources, reads = verified_sources(REFERENCES, category="导航执行 · 固定参考")
    tree = next(item for item in reads if item["path"].endswith("/navigate_to_pose_w_replanning_and_recovery.xml"))
    for report in (primary, portable):
        assert report["behaviorTree"]["installedSha256"] == tree["sha256"]
    for path in (READINESS, STOP_FINDING):
        assert load(path)["currentReportSha256"] == sha(REPORT)
    chapters, api = contents(primary, portable, traces)
    figure(primary, traces)
    material = dict(meta=dict(checkedAt="2026-11-07", report=REPORT.relative_to(ROOT).as_posix(),
        reportSha256=sha(REPORT), portableReport=PORTABLE.relative_to(ROOT).as_posix(), portableReportSha256=sha(PORTABLE),
        findingHashes={path.relative_to(ROOT).as_posix():sha(path) for path in (READINESS, STOP_FINDING)},
        captureHashes=artifacts, sourceReads=reads), chapters=chapters, resources=resources, apiReferences=[api])
    (ROOT / "source/nav2-execution-revision.json").write_text(json.dumps(material,ensure_ascii=False,indent=2) + "\n")
    print(json.dumps(dict(chapters=len(chapters), sections=sum(len(c.get("appendSections",[])) for c in chapters.values()),
        checkedSourceFiles=len(reads), resources=len(resources), tables=5, figures=1)))


if __name__ == "__main__":
    main()
