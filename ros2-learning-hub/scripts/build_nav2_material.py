#!/usr/bin/env python3
"""把实际 Nav2 回执、代价值与固定版本源码融合到章节。

输入为两次通过的报告和主试验的栅格捕获。核对文件指纹后生成正文、表格及 SVG。
原始代价值每格一字节，路径在 map 系以 m 表示。生成教材时不启动 Gazebo 或 ROS。
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
REPORT = EVIDENCE / "nav2-planning-current-validation.json"
PORTABLE = EVIDENCE / "nav2-planning-portable-current-validation.json"
CAPTURES = EVIDENCE / "nav2-grid-captures"
FILES = {"validate_nav2.py": "python", "nav2.yaml": "yaml", "bridge.yaml": "yaml", "nav_room.sdf": "xml"}
NAV = "ros-navigation--navigation2"
SLAM = "SteveMacenski--slam_toolbox"

REFERENCES = {
    "nav-lab-grid": ("ros2--common_interfaces", "jazzy", "占据栅格的布局、元数据与读取服务",
        "占据数组按行主序铺开，分辨率和原点随消息传输。PGM 行方向由 MapServer 的图像读取实现转换。",
        ("nav_msgs/msg/OccupancyGrid.msg", "nav_msgs/msg/MapMetaData.msg", "nav_msgs/srv/GetMap.srv")),
    "nav-lab-map-io": (NAV, "jazzy", "MapServer 的图像装载与错误分类",
        "Trinary 将灰度和阈值转为占据、自由、未知。空路径、YAML 解析失败与图像读取失败分别映射回执码。",
        ("nav2_map_server/src/map_io.cpp", "nav2_msgs/srv/LoadMap.srv")),
    "nav-lab-map-server": (NAV, "jazzy", "地图生命周期与保留发布",
        "配置文件在 configure 阶段加载，active 阶段才提供地图。主题使用可靠、瞬态本地 QoS。运行期重新加载成功才发布新地图。",
        ("nav2_map_server/src/map_server/map_server.cpp", "nav2_map_server/include/nav2_map_server/map_server.hpp")),
    "nav-lab-amcl": (NAV, "jazzy", "AMCL 的初始位姿、扫描更新和 TF",
        "初值需在全局帧。服务回执无业务布尔字段。无运动请求标记下一次更新，AMCL 的 map 到 odom 时戳来自扫描与有效余量。",
        ("nav2_amcl/src/amcl_node.cpp", "nav2_msgs/srv/SetInitialPose.srv")),
    "nav-lab-static-layer": (NAV, "jazzy", "静态层、父命名空间和全局代价地图",
        "PlannerServer 内部创建代价地图节点。它的默认地图入口与父命名空间有关，覆盖相对话题后需核实际全名。",
        ("nav2_costmap_2d/plugins/static_layer.cpp", "nav2_costmap_2d/src/costmap_2d_ros.cpp",
         "nav2_bringup/params/nav2_params.yaml")),
    "nav-lab-marking": (NAV, "jazzy", "扫描标记和膨胀的不同职责",
        "障碍层按扫描与目标帧 TF 标记可见表面。膨胀层将周边格赋为距离相关代价，与先验 OccupancyGrid 数值不同。",
        ("nav2_costmap_2d/plugins/obstacle_layer.cpp", "nav2_costmap_2d/plugins/inflation_layer.cpp")),
    "nav-lab-raw-costs": (NAV, "jazzy", "主代价图字节和 GetCostmap 回执",
        "服务返回 master 图的逐格字节。可视化 OccupancyGrid 会把代价值换算为另一套标度。",
        ("nav2_costmap_2d/src/costmap_2d_publisher.cpp", "nav2_msgs/srv/GetCostmap.srv",
         "nav2_msgs/msg/CostmapMetaData.msg", "nav2_costmap_2d/include/nav2_costmap_2d/cost_values.hpp")),
    "nav-lab-planner": (NAV, "jazzy", "规划服务器的起点、异常和路径检查",
        "use_start 控制取 TF 或指定起点。失败路径与 Action 接受分开。半径模式下 IsPathValid 检查剩余路径的离散点。",
        ("nav2_planner/src/planner_server.cpp", "nav2_msgs/action/ComputePathToPose.action", "nav2_msgs/srv/IsPathValid.srv")),
    "nav-lab-navfn": (NAV, "jazzy", "NavFn 的势场传播与路径提取",
        "先转代价值，按开关选择 Dijkstra 或 A* 传播，再沿势场提取路径。允许未知和目标容差由插件参数决定。",
        ("nav2_navfn_planner/src/navfn_planner.cpp", "nav2_navfn_planner/src/navfn.cpp", "nav2_planner/package.xml")),
    "nav-lab-commander": (NAV, "jazzy", "BasicNavigator 的规划快捷入口",
        "getPath 提供 Path 或 None，内部才取完整动作结果。需要保留 error_code 时可直接使用动作消息。",
        ("nav2_simple_commander/nav2_simple_commander/robot_navigator.py",)),
    "nav-lab-straightline": ("ros-navigation--navigation2_tutorials", "jazzy", "直线规划插件教学与注册",
        "示例展示 GlobalPlanner 的生命周期与 pluginlib 注册，createPlan 按起终点插值，未用占据代价做绕行。",
        ("nav2_straightline_planner/src/straight_line_planner.cpp", "nav2_straightline_planner/global_planner_plugin.xml")),
    "nav-lab-slam-artifacts": (SLAM, "jazzy", "SLAM Toolbox 的栅格保存与图序列化",
        "图像地图供地图服务器加载。位姿图序列化另带扫描和约束语义，反序列化请求区分启动匹配方式。",
        ("README.md", "srv/SaveMap.srv", "srv/SerializePoseGraph.srv", "srv/DeserializePoseGraph.srv",
         "config/mapper_params_localization.yaml")),
    "nav-lab-bringup": (NAV, "jazzy", "Nav2 Jazzy 的启动与定位配置入口",
        "bringup 将定位与导航分开包含，定位启动把 map 路径交给 yaml_filename。参数按实际包含文件核对。",
        ("nav2_bringup/launch/bringup_launch.py", "nav2_bringup/launch/localization_launch.py")),
    "nav-lab-linorobot": ("existing--linorobot2", "jazzy", "Linorobot2 的建图与导航配置",
        "建图包含 SLAM Toolbox，导航包含 Nav2。AMCL 和规划使用不同基座帧时，要从模型查二者之间的 TF。",
        ("linorobot2_navigation/launch/navigation.launch.py", "linorobot2_navigation/config/navigation.yaml",
         "linorobot2_navigation/launch/slam.launch.py", "linorobot2_navigation/config/slam.yaml")),
    "nav-lab-reference-chain": ("existing--Robotics_Tutorial", "main", "导航生态的分层排错路线",
        "沿传感器、TF、代价地图、全局规划、控制、底盘逐段核对。教材的固定台架提供其中前四段的实测。",
        ("02_C++基础与进阶/50_ROS2工程化/30_SLAM导航与仿真生态.md",)),
}


def verified_evidence():
    """报告、安装范围、复现源码及图像输入必须指向同一组实验。"""
    primary, portable = (json.loads(path.read_text()) for path in (REPORT, PORTABLE))
    paths = {"nav2_labs/" + name for name in FILES} | {"gazebo_labs/validate_sensors.py"}
    if not primary["passed"] or not portable["passed"] or primary["domainId"] == portable["domainId"]:
        raise ValueError("需要本机和实际解压源码的两份隔离报告")
    if set(primary["sourceHashes"]) != paths or portable["sourceHashes"] != primary["sourceHashes"]:
        raise ValueError("两次运行的源码集合或指纹不一致")
    for name, digest in primary["sourceHashes"].items():
        if sha(ROOT / "examples" / name) != digest:
            raise ValueError("实验文件已变化，须重新实测：" + name)
    captures = {**primary["map"]["files"], **{row["file"]: row["sha256"] for row in primary["costmap"]["snapshots"].values()}}
    for name, digest in captures.items():
        if sha(CAPTURES / name) != digest:
            raise ValueError("原始栅格文件指纹不一致：" + name)
    expected_codes = dict(static=0, marked=0, occupied=206, outside=204, unknown=208,
                          **{"from-tf": 0, "bad-planner": 201, "bad-frame": 202})
    for report in (primary, portable):
        if ({key: row["code"] for key, row in report["actions"].items()} != expected_codes or
                report["costmap"]["isPathValid"] != dict(static=True, oldAfterMarking=False, detour=True) or
                report["amcl"]["wrongFramePoseSamples"] != 0 or report["amcl"]["wrongFrameMapToBase"] or
                not report["costmap"]["oldPathNewLethalCellIndices"] or report["costmap"]["detourRejectedCells"]):
            raise ValueError("规划或 AMCL 的关键对照缺失")
    return primary, portable


def measured(title, columns, rows, caption):
    return dict(title=title, columns=columns, rows=rows, caption=caption,
                evidenceFile=REPORT.relative_to(ROOT).as_posix(), evidenceSha256=sha(REPORT))


def save_figure(report):
    """以两份实际 master 图绘制等比例栅格，叠加原样读取的 Path 坐标。"""
    costmap = report["costmap"]
    width, height = costmap["size"]
    resolution = costmap["resolutionM"]
    ox, oy = costmap["originM"]
    scale = 4.75
    colors = {0: "#fcfbfe", 1: "#e7dcf2", 253: "#ad8cbe", 254: "#384358", 255: "#c9d1db", 256: "#b73948"}
    title = "同一目标在障碍标记前后的 NavFn 路径"
    description = "左侧的静态代价图上原路径横穿箱体所在区域。右侧的障碍层由实际激光标记箱体前缘，新路径从其侧面绕行。"
    body = text(40, 46, title, 27, "#27273d", 650)
    body += text(40, 76, f"实际 master 栅格 · {width} × {height} 格 · {resolution:.2f} m/格 · 地图系", 16, "#525568")
    added = set(costmap["addedLethalCellIndices"])
    rect_center, rect_size = costmap["obstacleCenterM"], costmap["obstacleSizeM"]

    def panel(left, key, label, route_color):
        top = 133
        run = report["actions"][key]
        capture = (CAPTURES / costmap["snapshots"][key]["file"]).read_bytes()
        assert len(capture) == width * height
        assert {str(k): v for k, v in Counter(capture).items()} == costmap["snapshots"][key]["valueCounts"]
        patches = {kind: [] for kind in colors}
        for row in range(height):
            idx = row * width
            values = [256 if key == "marked" and i in added else 1 if 0 < capture[i] < 253 else capture[i]
                      for i in range(idx, idx + width)]
            x = 0
            for kind, group in groupby(values):
                run_width = sum(1 for _ in group)
                patches[kind].append(f"M{x} {height - row - 1}h{run_width}v1h-{run_width}z")
                x += run_width
        cells = "".join(f'<path fill="{colors[k]}" d="{"".join(v)}"/>' for k, v in patches.items() if v)
        out = text(left, 111, label, 20, route_color, 650)
        out += f'<g transform="translate({left} {top}) scale({scale})" shape-rendering="crispEdges">{cells}</g>'
        out += f'<rect x="{left}" y="{top}" width="{width * scale}" height="{height * scale}" fill="none" stroke="#9499a8"/>'

        def pixel(x, y):
            return left + scale * (x - ox) / resolution, top + scale * (height - (y - oy) / resolution)

        box_x, box_y = pixel(rect_center[0] - rect_size[0] / 2, rect_center[1] + rect_size[1] / 2)
        out += (f'<rect x="{box_x:.2f}" y="{box_y:.2f}" width="{rect_size[0] / resolution * scale:.2f}" '
                f'height="{rect_size[1] / resolution * scale:.2f}" fill="none" stroke="#b73948" stroke-dasharray="4 3" stroke-width="2"/>')
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in (pixel(*point) for point in run["pointsM"]))
        out += f'<polyline points="{points}" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round"/>'
        out += f'<polyline points="{points}" fill="none" stroke="{route_color}" stroke-width="3.5" stroke-linecap="round"/>'
        for xy, marker in ((costmap["frozenStartM"], "S"), (costmap["goalM"], "G")):
            x, y = pixel(*xy)
            out += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{route_color}" stroke="#fff" stroke-width="2"/>'
            out += text(round(x - 4), round(y - 9), marker, 14, route_color, 650)
        for x in (-4, -2, 0, 2, 4):
            display_x, _ = pixel(x, oy)
            out += text(round(display_x - 6), 437, x, 13, "#54596a")
        out += text(left, 465, f"{run['poseCount']} 个位姿 · 折线长 {run['lengthM']:.2f} m", 16, route_color, 650)
        return out

    body += panel(45, "static", "A　仅静态层与膨胀层", "#364b8a")
    body += panel(505, "marked", "B　开启激光障碍标记", "#036c57")
    legend = [(0, "自由"), (1, "一般代价"), (253, "内切膨胀"), (254, "致命"), (255, "未知"), (256, "箱体新增致命格")]
    for i, (value, name) in enumerate(legend):
        x = 45 + i * 124
        body += f'<rect x="{x}" y="486" width="15" height="15" rx="2" fill="{colors[value]}" stroke="#8490a3"/>'
        body += text(x + 22, 499, name, 14, "#46485b")
    body += text(45, 532, "S / G 为相同起终点。横轴为 x（m），图中向上为 +y。虚线框为 SDF 中的箱体尺寸。", 15, "#54596a")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 930 556" role="img" aria-labelledby="title desc">'
           f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>'
           '<rect width="930" height="556" fill="#f8f5fc"/><g font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif">'
           + body + '</g></svg>\n')
    identifier = "nav2-costmap-planning"
    file = f"preview/figures/{identifier}.svg"
    target = ROOT / "dist" / file
    target.write_text(svg)
    manifest = ROOT / "source/design-figures.json"
    data = json.loads(manifest.read_text())
    data["figures"] = [item for item in data["figures"] if item["id"] != identifier]
    data["figures"].append(dict(id=identifier, title=title, alt=description, file=file, kind="实测图",
        caption="两幅底图来自真实 GetCostmap 主图，路径来自两个实际 ComputePathToPose 回执。箱体虚线是 SDF 几何，红格是扫描新增的可见面。两图比例相同。",
        evidenceFile=REPORT.relative_to(ROOT).as_posix(), evidenceSha256=sha(REPORT), assetSha256=sha(target),
        placements=[dict(chapter="eco-nav2-stack", afterSection=8), dict(chapter="theory-planning", afterSection=6)]))
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    report, portable = verified_evidence()
    resources, reads = verified_sources(REFERENCES, category="地图与规划 · 固定源码")
    map_data, amcl, scan, costmap, actions = (report[key] for key in ("map", "amcl", "scan", "costmap", "actions"))
    versions = report["versions"]
    runtime = (f"在本机 Jazzy Nav2 {versions['nav2_planner']}、Harmonic {versions['gzSim'].split()[-1]}、"
               f"ros_gz_bridge {versions['ros_gz_bridge']} 的固定激光台架实测。")
    scope = "运行 MapServer、AMCL、全局代价地图和 NavFn。SLAM 建图、完整 NavigateToPose 行为树、控制器、运动底盘和硬件待分别验证。"

    failures = {row["case"]: row for row in map_data["failedLoads"]}
    map_table = measured("地图节点状态、晚加入订阅和加载回执", ["操作", "本次实际输出", "判断"], [
        ["配置后查 GetMap", f"{map_data['inactiveCells']} 格", "等到 active 再读取有效图"],
        ["激活后晚加入", f"瞬态本地收到 {map_data['checkedCells']} 格，易失订阅收到 0 条", "提供端与请求端匹配仍需区分历史样本"],
        ["空路径 / 缺 YAML / 缺图像", " / ".join(str(failures[case]["code"]) for case in ("empty-url", "missing-yaml", "missing-image")), "三次均再次查到旧地图"],
        ["重新加载同一 YAML", f"结果 {map_data['reloadCode']}，易失订阅收到 {map_data['volatileAfterReload']} 条", "同一栅格，新发布时戳"],
    ], "占据图逐格核对，障碍、空闲和未知均在地图帧下验证。回执失败时以另一次 GetMap 判断旧图状态。")
    pose_table = measured("从初始位姿回执到 AMCL 与 TF 输出", ["阶段", "输入", "实际结果"], [
        ["错误初值", f"frame={amcl['wrongFrame']}，坐标与后面的正确初值相同",
         f"服务有回应，{amcl['wrongFrameScanWindowS']:.2f} s 扫描窗内无新位姿，map 到基座不可查"],
        ["正确初值", f"frame=map，x / y 为 {vector(amcl['initialM'], 2)} m",
         f"AMCL 输出 {vector(amcl['positionM'])} m，位置误差 {amcl['errorM']:.4f} m，偏航 {amcl['yawRad']:.4f} rad"],
        ["无运动更新", "request_nomotion_update 后继续接收扫描",
         f"位姿时戳从 {amcl['initialUpdateStampNs']/1e9:.3f} s 推进到 {amcl['noMotionUpdateStampNs']/1e9:.3f} s"],
        ["按扫描查 TF", f"采样时刻 {amcl['scanLookupStampNs']/1e9:.3f} s",
         f"激光原点在 map 中为 {vector(amcl['laserOriginAtScanM'])} m"],
    ], "位置与偏航为无运动更新后的实测输出。台架提供固定里程计边，AMCL 提供全局校正边。")
    before, after = actions["static"], actions["marked"]
    crossings = len(costmap["oldPathNewLethalCellIndices"])
    marks = len(costmap["addedLethalCellIndices"])
    path_table = measured("同一起终点与两份实际全局代价图", ["代价地图", "路径", "采样与服务结果"], [
        ["静态层与膨胀层", f"{before['poseCount']} 点，{before['lengthM']:.2f} m", "原路径 IsPathValid 为真"],
        ["启用激光标记", "用同一条旧路径检查", f"中心线采到 {crossings} 个箱体新增致命格，IsPathValid 为假"],
        ["启用激光标记", f"重算 {after['poseCount']} 点，{after['lengthM']:.2f} m", "IsPathValid 为真，中心线采样无 253/254/255 格"],
    ], f"实际从同一 TF 样本固定起点，目标 x / y 为 {vector(costmap['goalM'], 2)} m。折线每最多 {costmap['sampledStepM']:.3f} m 采一格。")
    error_labels = {
        "from-tf": ("真实 TF 起点", "NONE"), "occupied": ("柱内目标", "GOAL_OCCUPIED"),
        "outside": ("地图外目标", "GOAL_OUTSIDE_MAP"), "unknown": ("墙外未知格", "NO_VALID_PATH"),
        "bad-planner": ("不存在的插件 ID", "INVALID_PLANNER"), "bad-frame": ("不存在的目标坐标系", "TF_ERROR"),
    }
    action_table = measured("实际规划动作的接受与业务终态", ["请求", "接受回执", "终态", "结果码", "位姿数"], [
        [label, "接受" if actions[key]["accepted"] else "拒绝", "SUCCEEDED" if actions[key]["status"] == 4 else "ABORTED",
         f"{actions[key]['code']} · {code}", str(actions[key]["poseCount"])] for key, (label, code) in error_labels.items()
    ], "动作协议接受与规划可行性分开。五类故障记录错误码和日志。本机该版回执的 error_msg 为空。")
    command = dict(label="运行本地 Nav2 固定激光台架", language="bash", type="commands", code=(
        "# 从 ros2-learning-hub 运行。先加载 Jazzy 与本机已安装的 Nav2、Harmonic 和桥。\n"
        "source /opt/ros/jazzy/setup.bash\n"
        "# 229 是示例的本机 DDS 域，改为当前空闲的 1..232。输入是同目录 SDF 和 YAML。\n"
        "# 输出为 /tmp 中的新地图、原始代价值、路径和报告。脚本不发送速度。\n"
        "python3 examples/nav2_labs/validate_nav2.py --domain-id 229\n"
        "# 解压源码 ZIP 后从 atlas_examples 运行时去掉 examples/。\n"
        "# 本机使用 NVIDIA EGL 时，加 --egl-vendor-json /usr/share/glvnd/egl_vendor.d/10_nvidia.json。"))
    code_files = [dict(label=name, language=language, type="complete", sourceFile=f"examples/nav2_labs/{name}", explanation=note)
        for (name, language), note in zip(FILES.items(), (
            "完整驱动依次等待真实扫描、地图、定位与规划。复用同包 gazebo_labs 的进程管理辅助，退出时回收自身节点。",
            "三个生命周期节点与内部全局代价地图。距离用米、频率用 Hz。仅改障碍层 enabled 做两次路径对照。",
            "将专属世界时钟与激光单向转入独立 DDS 域。Header 保持模拟时钟，TF 单独提供。",
            "固定几何，单位米和弧度。map_ 模型组成先验图，observation_box 仅供运行期激光看到。",
        ))]
    chapters = {
        "eco-nav2-stack": dict(validation=runtime + scope, appendSourceIds=["nav-lab-grid", "nav-lab-map-io", "nav-lab-map-server",
            "nav-lab-static-layer", "nav-lab-marking", "nav-lab-raw-costs", "nav-lab-planner", "nav-lab-reference-chain"],
            appendSections=[
                section("从先验图像到可逐格核对的占据地图", [
                    f"脚本将四面墙和一根非对称柱投到 {map_data['size'][0]} × {map_data['size'][1]} 格，分辨率 {map_data['resolutionM']:.2f} m/格，原点为 ({vector(map_data['originM'], 1)}) m。箱体只存在于 Gazebo 场景。PGM 首行对应最高 y，OccupancyGrid 首行对应最低 y，发布后以柱的位置核对行翻转。",
                    f"MapServer 实际输出 {map_data['cells']['0']} 个空闲格、{map_data['cells']['100']} 个占据格和 {map_data['cells']['-1']} 个未知格。trinary 模式按 YAML 的分辨率、原点、阈值和 negate 解释像素，图像灰度与 ROS 占据值需要分别读。",
                    "先查生命周期状态，再查 GetMap 与话题。配置成功时服务已发现，未激活的回应仍是空图。激活后发布端可靠且瞬态本地，两种晚加入订阅都与提供端匹配，但只有请求瞬态本地的订阅得到历史地图。",
                ], [map_table]),
                section("让同一个规划目标绕过新增障碍", [
                    f"用固定激光收到 {scan['beams']} 束，中心距离 {scan['centerRangeM']:.4f} m。全局代价地图的静态层接地图，障碍层按扫描采样时戳查 TF。此处关闭射线清除，仅对比标记。全局图用 0.10 m/格、0.18 m 圆半径和 0.38 m 膨胀范围。",
                    "GetCostmap 返回 master 原始字节。0 为空闲，253 为内切膨胀格，254 为致命，255 为未知。可视化 OccupancyGrid 把这些值重新编码。Jazzy 固定实现的服务把地图时刻字段填为响应时钟读数，用扫描 Header 查真正的采集时刻。",
                    f"将内部节点的 obstacle_layer.enabled 从 false 改为 true。除参数回执外，还要从主图读出箱体附近 {marks} 个新增致命格。激光只看见箱体的可见面，图中的完整虚线框来自世界几何。然后用同一起终点验旧路径和重算路径。",
                ], [path_table]),
            ], appendExercises=[
                exercise("两个晚加入订阅都已匹配，为何只有一个收到旧地图？", "瞬态本地允许取活动发布者保留的旧样本。易失订阅匹配后只等后续发布。本例重载同一地图验证了易失订阅可以收到新数据。"),
                exercise("加载路径为空、YAML 缺失、图像缺失时怎样定位？", "这次分别得到 1、3、2。按错误对应检查输入、YAML 和图像，再独立查询 GetMap 核实旧图状态。"),
                exercise("收到障碍层开关的成功回执后，还要怎样确认可规划？", "先查同一场景主图是否出现新代价值，再比较相同起终点的旧路径检查和新规划回执。"),
            ]),
        "eco-state-estimation": dict(validation="软件差速与局部 EKF 按独立域225的报告实测。" + runtime + "另核近真值初值、无运动更新和扫描时刻 TF。IMU、GNSS、全局重定位与运动中的定位精度待单独测量。",
            appendSourceIds=["nav-lab-amcl", "nav-lab-map-server"],
            appendSections=[section("用扫描和 TF 确认 AMCL 的初始位姿", [
                "AMCL 使用带协方差的地图系初值与扫描更新粒子分布。这里知道固定台架位置，因此使用较小的对角协方差。x、y 方差为 0.0025 m²，偏航方差为 0.0025 rad²。定位输出的协方差随估计变化，不能把输入先验当成传感器精度。",
                "SetInitialPose 的响应体为空。把相同数字先标成 odom，再标成 map。观察窗口里都有新激光，只有通过全局帧检查的请求产生地图位姿与 TF。无运动更新服务标记下一次扫描更新，本次收到一个更新后的位姿时戳。",
                "软件底盘章的局部 EKF 负责 odom 到基座。此台架的同一边为静态，AMCL 独自发布 map 到 odom，基座到激光另加 0.30 m 高度。部署时为两类边分别指定发布者，并以实际扫描时戳检查能否串接。",
            ], [pose_table])], appendExercises=[
                exercise("SetInitialPose 有回应，却一直没有 map 到 odom，要查什么？", "分别查初值的 frame、地图可用、AMCL 活动状态、激光时间与到 odom 的 TF。用实际位姿和 TF 作为业务验收。"),
            ]),
        "eco-nav2-task-programming": dict(validation="独立域217的假服务端验证十二类 NavigateToPose 客户端协议，包括超时、取消和迟到接受。" + runtime + "另实测 ComputePathToPose 的五类规划失败。完整 NavigateToPose 导航执行仍待验证。",
            appendSourceIds=["nav-lab-planner", "nav-lab-commander", "nav-lab-navfn"],
            appendSections=[section("从 ComputePathToPose 定位规划失败阶段", [
                "路径规划动作返回 Path、规划时长和错误码。use_start=false 时从全局代价地图的 TF 取当前基座，true 时用请求的 start。起终点须能变到全局帧。实测同时保留目标接受与最后状态，空路径按对应错误码解释。",
                "Jazzy 快照的 BasicNavigator.getPath 给调用者 Path 或 None。需要把 TF 失败、规划器未配置、目标越界和无可行路径分开记录时，直接调用动作并保留完整结果以及规划服务器日志。",
                "本轮成功规划的 planning_time 为 0 仿真纳秒。规划器用节点时钟计算，两个读数可能落在同一个仿真时刻。等待期限仍用单调时间，耗时基准需另行测量。",
            ], [action_table])], appendExercises=[
                exercise("同样是零个路径点，目标在柱内和目标在未知区有何区别？", "本机严格容差配置下，柱内是 206，禁止走未知区时该目标为 208。结合代价图和动作错误码区分判据。"),
            ]),
        "theory-planning": dict(validation="Python 标准库网格实验已实测。" + runtime + scope,
            appendSourceIds=["nav-lab-navfn", "nav-lab-straightline", "nav-lab-raw-costs"],
            appendSections=[section("从网格最短路过渡到 NavFn 势场路径", [
                "教学四邻域实验按离散步数检查最短路。NavFn 先把 ROS 代价值映射为内部成本，使用 Dijkstra 或 A* 传播势场，再由梯度提取折线路径。位姿点数受到提取步长和插值影响，不能直接当作格数或势场成本。",
                "官方直线插件教学示例展示了 pluginlib 注册和统一 createPlan 入口，具体实现只插值。相同接口可以返回不同质量的路径，检查要依据插件实现、代价值和失败合同。本台架实际加载 GridBased 对应 NavFn，关闭 A* 与未知区通行，目标容差设为 0 m。",
                f"同样的起点和目标，实测路径由 {before['lengthM']:.2f} m 变为 {after['lengthM']:.2f} m。沿每段最多 0.025 m 采中心线，另调用 IsPathValid 检查剩余离散位姿。两项证据均用于当前静态图，车辆动力学、连续扫掠和安全间距要由后续验证负责。",
            ])], appendExercises=[
                exercise("为什么路径点数增加不能直接证明全局规划代价增加？", "点数取决于输出采样、插值和路径提取。应分别计算折线长度、对照代价地图并理解插件内部的势场成本。"),
            ]),
        "eco-slam-mapping": dict(validation="SLAM Toolbox 的节点启动、走行建图、回环与图恢复为读者练习。固定激光实验另实测先验 PGM/YAML 读取和重载。",
            appendSourceIds=["nav-lab-slam-artifacts", "nav-lab-map-io", "nav-lab-linorobot"],
            appendSections=[section("把占据图与可继续建图的位姿图区分保存", [
                "占据图交给 Nav2 MapServer 时，需要 PGM 与 YAML 配对保存。台架从已知几何生成这对文件，重载能核对分辨率、原点与占据结果。使用地图时应另记录地图数据来源、生成时刻和尺寸。",
                "SLAM Toolbox 的 SaveMap 和 SerializePoseGraph 对应不同产物。序列化位姿图供继续建图或图定位使用，反序列化时还要选择首节点、指定姿态或定位匹配方式。只有栅格文件时，图中的扫描、位姿节点和约束无法从像素完整恢复。",
                "本地 Jazzy 快照的 mapper_params_localization.yaml 中仍写着 mode: mapping 并带 localization 注释。准备图定位时，检查实际启动的节点、有效模式和图文件入口。Linorobot2 将建图与导航放在独立启动文件，这些参数也要按实际运行分支核对。",
            ])], appendExercises=[
                exercise("若要隔天在旧地图基础上继续做图优化，除了 PGM 与 YAML 应保存什么？", "同时序列化 SLAM Toolbox 的位姿图及数据，记录建图参数、文件名、初始匹配策略和版本。"),
            ]),
        "project-navigation": dict(validation="局部轮反馈、Odometry 与 EKF 按独立域225验证。NavigateToPose 客户端在域217对假服务端完成十二类协议验证。" + runtime + scope,
            appendSourceIds=["nav-lab-linorobot", "nav-lab-bringup", "nav-lab-map-server", "nav-lab-amcl", "nav-lab-planner"],
            appendSections=[section("可解压复跑的分段导航台架", [
                "先在隔离台架完成地图、定位与全局规划。启动顺序由实际服务、消息和 TF 判定。地图配置后激活，再激活 AMCL 并给出 map 系初值，最后激活 PlannerServer。关闭时逐个停用和清理，保留各状态回执。",
                "Linorobot2 的工程配置中 AMCL 用 base_footprint，导航器与全局代价地图用 base_link。复用工程配置前先查两个基座之间的 TF。外层启动把 map 路径传入 Nav2，固定版定位启动将其赋给 yaml_filename。外层的 initial_pose_* 参数仍需对照被包含文件及 AMCL 实际生效参数。",
                f"台架把实际地图、扫描和命名空间内的规划器连在一起，主试验用域 {report['domainId']}，从原创示例包解压后用域 {portable['domainId']} 重跑。两次分别记录 12 次生命周期切换、实际规划终态和五个直接进程的退出。运行源码和配置按报告指纹核对。",
            ], code=[command, *code_files])], appendExercises=[
                exercise("先确定地图、扫描、TF 都有输出，为何还需检查代价地图订阅全名？", "PlannerServer 内的代价地图另有命名空间。相对名可能解析到它内部，实验用限定节点 remap 后再从 ROS 图检查订阅。"),
            ]),
        "eco-tf-frames": dict(appendSourceIds=["nav-lab-amcl"], sections={"2": dict(appendParagraphs=[
            "在导航台架中，AMCL 用扫描时戳加 transform_tolerance 发布 map 到 odom。查看最新 TF 与按激光采集时刻查询是两项检查。台架通过当时的 map 到 laser_link 查询，验证固定安装平移仍为 0.30 m。",
        ])}),
        "eco-gazebo-simulation": dict(appendSourceIds=["nav-lab-marking"], sections={"7": dict(appendParagraphs=[
            "导航章另有一个固定房间，它的真实扫描从同样的桥进入 AMCL 和 Nav2 障碍层。场景的运行期箱体与先验地图分开，用来比较标记前后的路径。当前相机实验的 ControlWorld 暂停回执继续独立解释。",
        ])}),
        "qos": dict(appendSourceIds=["nav-lab-map-server"], sections={"4": dict(appendParagraphs=[
            "MapServer 的实际对照把两个订阅者都放在激活之后。请求瞬态本地的订阅收到旧地图，易失订阅虽匹配但起初为空。成功重载同一 YAML 后它收到新发布，证明历史可用性与当前匹配可以分别验证。",
        ])}),
    }
    api = dict(id="api-nav2-map-planning", title="Nav2 地图、定位与规划接口", lessons=["eco-nav2-stack", "eco-nav2-task-programming", "project-navigation"],
        columns=["接口", "输入", "回执与检查", "边界"], rows=[
            ["GetMap / LoadMap", "活动 MapServer 与地图 YAML", "GetMap 的 OccupancyGrid，LoadMap 的 result 及后续地图消息", "检查分辨率、原点和实际栅格。失败回执里的 map 不用作新地图"],
            ["SetInitialPose", "map 系 PoseWithCovarianceStamped", "响应体为空，以 AMCL 位姿和 TF 验收", "坐标、时间与协方差含义分别核对"],
            ["GetCostmap", "全局代价地图服务", "master 图的尺寸、原点、分辨率与 uint8 字节", "不要用占据图 0 到 100 的标度解释 253 到 255"],
            ["ComputePathToPose", "起点策略、目标帧、planner_id", "接受、终态、error_code 和 Path 分开读取", "规划成功后另验控制与执行"],
            ["IsPathValid", "同一全局帧的 Path", "看当前代价图上的剩余路径", "半径模式以离散位姿检查，连续足印与运动约束需另查"],
        ])
    assert math.isfinite(after["lengthM"]) and after["lengthM"] > before["lengthM"]
    save_figure(report)
    patch = dict(meta=dict(report=REPORT.relative_to(ROOT).as_posix(), reportSha256=sha(REPORT),
                           portableReport=PORTABLE.relative_to(ROOT).as_posix(), portableReportSha256=sha(PORTABLE),
                           sourceReads=reads), chapters=chapters, resources=resources, apiReferences=[api])
    (ROOT / "source/nav2-planning-revision.json").write_text(json.dumps(patch, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(chapters=len(chapters), sources=len(resources), checkedSourceFiles=len(reads), tables=4, figures=1)))


if __name__ == "__main__":
    main()
