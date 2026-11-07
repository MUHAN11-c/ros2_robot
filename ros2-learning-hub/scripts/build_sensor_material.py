#!/usr/bin/env python3
"""把 Harmonic 实测、原始采样图与固定参考写入教材。正常构建不启动仿真。"""
import base64
import json
from pathlib import Path

from build_drive_material import exercise, section, sha, vector, verified_sources
from build_theory_figures import text

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "validation-evidence"
REPORT = EVIDENCE / "gazebo-sensors-current-validation.json"
FILES = {"sensors.sdf": "xml", "bridge.yaml": "yaml", "validate_sensors.py": "python"}

REFERENCES = {
    "sensor-gz-world": ("gazebosim--docs", "master", "Harmonic 世界与传感器系统",
        "依据 Harmonic 文档分开加载物理与渲染系统，SDF 单位和更新率明确。EGL 选择记录随本机报告保留。",
        ("harmonic/sensors.md", "harmonic/sdf_worlds.md", "harmonic/troubleshooting.md")),
    "sensor-bridge-config": ("gazebosim--ros_gz", "jazzy", "ros_gz_bridge 映射和 Header 覆盖",
        "核对映射方向、QoS、每条 frame_id 与 wall-time 开关，保留 Gazebo 采集时戳。",
        ("ros_gz_bridge/README.md", "ros_gz_bridge/src/bridge_config.cpp", "ros_gz_bridge/src/bridge_handle_gz_to_ros.cpp")),
    "sensor-control": ("gazebosim--ros_gz", "jazzy", "世界控制请求与仿真时钟转换",
        "控制服务的 pause 字段进入 Gazebo WorldControl，ROS Clock 传递仿真时间。",
        ("ros_gz_interfaces/srv/ControlWorld.srv", "ros_gz_bridge/src/convert/ros_gz_interfaces.cpp",
         "ros_gz_bridge/src/convert/rosgraph_msgs.cpp")),
    "sensor-converters": ("gazebosim--ros_gz", "jazzy", "图像、LaserScan 和点云的桥转换",
        "扫描时间字段在这版转换中设为零，点云仍携带字段表和二进制布局。安装与快照版本分别记录。",
        ("ros_gz_bridge/src/convert/sensor_msgs.cpp",)),
    "sensor-template": ("gazebosim--ros_gz_project_template", "main", "Gazebo 工程模板的方向划分",
        "模板中控制命令走 ROS 到 Gazebo，时钟与扫描走反向。这里只迁移方向划分，实测使用独立静止世界。",
        ("ros_gz_example_bringup/config/ros_gz_example_bridge.yaml",)),
    "sensor-image-contract": ("ros2--common_interfaces", "jazzy", "Image 与 CameraInfo 采样合同",
        "图像按 encoding 和 step 解码。图像与内参的 Header 应对应同一相机光学 frame。",
        ("sensor_msgs/msg/Image.msg", "sensor_msgs/msg/CameraInfo.msg")),
    "sensor-scan-contract": ("ros2--common_interfaces", "jazzy", "LaserScan 与 PointCloud2 二进制合同",
        "LaserScan 按 X 前、Z 上的轴向解释，点云按字段、端序与步长解释。",
        ("sensor_msgs/msg/LaserScan.msg", "sensor_msgs/msg/PointCloud2.msg", "sensor_msgs/msg/PointField.msg")),
    "sensor-image-calibration": ("ros-perception--image_pipeline", "jazzy", "内参、畸变与校正流程",
        "用 K、D、R、P 理解图像标定与校正，教材把这个流程和单通道边缘处理分开。",
        ("image_pipeline/doc/camera_info.rst", "image_proc/src/rectify.cpp")),
    "sensor-opencv": ("ros-perception--vision_opencv", "humble", "cv_bridge 解码与编码接口",
        "核读本地 Humble Python 源码的行跨度、端序和显式编码。实测使用已安装 Jazzy cv_bridge，版本分列。",
        ("cv_bridge/python/cv_bridge/core.py",)),
    "sensor-pcl-layout": ("existing--Robotics_Tutorial", "main", "点云字段、偏移与点类型",
        "借助专题讲义对照结构化点与字段描述。是否复制按实际转换函数单独核查。",
        ("02_C++基础与进阶/40_通用库剖析/50_PCL点云库.md",)),
    "sensor-pcl-convert": ("ros-perception--perception_pcl", "jazzy", "PCL 转换的拷贝与移动入口",
        "当前快照的 toPCL 复制 data，moveToPCL 交换 data 缓冲，应用应按具体重载推断所有权。",
        ("pcl_conversions/include/pcl_conversions/pcl_conversions.h",)),
    "sensor-clock-client": ("ros2--rclpy", "jazzy", "Python TimeSource 与传感器 QoS",
        "TimeSource 为时钟建立深度 1 的尽力而为订阅。传感器与控制端点按实际 QoS 分开核对。",
        ("rclpy/rclpy/time_source.py", "rclpy/rclpy/qos.py")),
    "sensor-nav2-filter": ("ros-navigation--navigation2", "jazzy", "Nav2 障碍层的消息与 TF 门控",
        "LaserScan 和 PointCloud2 分别进入 TF 消息过滤器。清除、标记和无穷距离处理各有参数边界。",
        ("nav2_costmap_2d/plugins/obstacle_layer.cpp",)),
    "sensor-slam-input": ("SteveMacenski--slam_toolbox", "jazzy", "SLAM Toolbox 的输入与帧",
        "配置把扫描入口、地图帧、里程计帧、机器人基座分别列出。静止台架只检查测量入口。",
        ("config/mapper_params_online_async.yaml",)),
}


def measured(title, columns, rows, caption):
    return dict(title=title, columns=columns, rows=rows, caption=caption,
                evidenceFile=REPORT.relative_to(ROOT).as_posix(), evidenceSha256=sha(REPORT))


def save_figure(report, perception_index):
    """保留真实 RGB/mono8 PNG 字节，图内只叠加说明，连续版离线可见。"""
    camera = report["camera"]
    image_dir = EVIDENCE / "gazebo-sensor-captures"
    pairs = []
    for name in ("camera.png", "edges.png"):
        path = image_dir / name
        if sha(path) != camera["imageSha256"][name]:
            raise ValueError("相机样本与实测记录不一致：" + name)
        pairs.append(base64.b64encode(path.read_bytes()).decode("ascii"))
    sample = f"{camera['stampNs']/1e9:.3f} s"
    title = "Gazebo 红板的真实相机帧与红通道边缘"
    alt = "同一采集时戳的96乘64像素红板图像和黑底白边Canny结果。两个结果并排，可看清红板的竖边。"
    body = text(38, 50, title, 25, "#294b32", 650)
    body += text(38, 93, "原始 RGB · 96 × 64 px", 19, "#345b3b", 600)
    body += text(462, 93, "红通道 Canny · mono8", 19, "#345b3b", 600)
    for left, data in zip((38, 462), pairs):
        body += f'<image x="{left}" y="112" width="390" height="260" style="image-rendering:pixelated" href="data:image/png;base64,{data}"/>'
    body += text(38, 410, f"采样时戳 {sample} · {camera['frame']}", 16)
    body += text(462, 410, f"红通道 {camera['redEdgePixels']} 像素 · 同阈值灰度 {camera['grayEdgePixelsSameThreshold']}", 16)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 440" role="img" '
           'aria-labelledby="title desc"><title id="title">' + title + '</title><desc id="desc">' + alt +
           '</desc><rect width="900" height="440" fill="#fbfdf9"/><g font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif">'
           + body + '</g></svg>\n')
    file = "preview/figures/gazebo-sensor-captures.svg"
    target = ROOT / "dist" / file
    target.write_text(svg)
    manifest = ROOT / "source/design-figures.json"
    figures = json.loads(manifest.read_text())
    figures["figures"] = [item for item in figures["figures"] if item["id"] != "gazebo-sensor-captures"]
    figures["figures"].append(dict(id="gazebo-sensor-captures", title=title, alt=alt, file=file, kind="实测图",
        caption="左侧 RGB、右侧红通道 Canny 来自同一台架的实际软件仿真采样。阈值固定为 40/120，像素以最近邻放大。图像处理保留原 Header。",
        evidenceFile=REPORT.relative_to(ROOT).as_posix(), evidenceSha256=sha(REPORT), assetSha256=sha(target),
        placements=[dict(chapter="eco-gazebo-simulation", afterSection=7),
                    dict(chapter="eco-perception-pipeline", afterSection=perception_index)]))
    manifest.write_text(json.dumps(figures, ensure_ascii=False, indent=2) + "\n")


def main():
    report = json.loads(REPORT.read_text())
    if not report["passed"] or set(report["sourceHashes"]) != FILES.keys():
        raise ValueError("需要完整通过的真实仿真报告")
    for name, digest in report["sourceHashes"].items():
        if sha(ROOT / "examples/gazebo_labs" / name) != digest:
            raise ValueError("仿真实验源码变化，须重新运行：" + name)
    camera, scan, cloud, clock, qos = (report[k] for k in ("camera", "scan", "cloud", "clock", "qos"))
    assert clock["initialNs"] == 0 and clock["resumedNs"] > clock["pausedNs"] > 0
    assert qos["bestEffortSamples"] > 0 and qos["reliableSamples"] == 0
    sources, reads = verified_sources(REFERENCES, category="仿真与感知 · 固定源码")
    active = f"{clock['runningNs']/1e9:.3f}"
    paused = f"{clock['pausedNs']/1e9:.3f}"
    resumed = f"{clock['resumedNs']/1e9:.3f}"
    clock_table = measured("同一真实仿真世界的时钟和采样", ["阶段", "ROS 时间（s）", "采样与控制回执"], [
        ["初始暂停", "0", "桥已发现，时间尚未推进"],
        ["运行", active, "ControlWorld 恢复成功，收到图像与激光"],
        ["暂停", paused, "排空队列后观察 0.40 单调秒，五类采样时戳不变"],
        ["再恢复", resumed, "服务回执成功，时钟与五类采样时戳推进"],
    ], "三处非零值取自这一轮采样。暂停窗口以单调时钟测量，不能用冻结的仿真时间限时。")
    image_table = measured("同戳 RGB、CameraInfo 与边缘检查", ["观测量", "实测值", "读法"], [
        ["原图", f"{camera['sizePx'][0]}×{camera['sizePx'][1]}，{camera['encoding']}",
         f"每行 {camera['rowBytes']} 字节，整帧 {camera['dataBytes']} 字节"],
        ["K 内参", vector([camera["k"][0], camera["k"][4], camera["k"][2], camera["k"][5]], 2),
         "依次为 fx、fy、cx、cy，单位 px"],
        ["同戳样本组", str(camera["matchingTriplets"]), "按 Header.stamp 配对原图、内参与输出，三者同光学 frame"],
        ["边缘", f"{camera['edgeEncoding']}，每行 {camera['edgeRowBytes']} 字节",
         f"阈值 40/120 下灰度 {camera['grayEdgePixelsSameThreshold']}，红通道 {camera['redEdgePixels']} 个非零像素"],
    ], "96×64 图像来自固定红板与相机。内参核对的是本例视场和像素尺寸，实机标定需要另外的数据与验证。")
    intervals = sorted(set(scan["successiveHeaderIntervalsS"]))
    intervals_text = f"{intervals[0]:.2f}" if len(intervals) == 1 else f"{intervals[0]:.2f} 至 {intervals[-1]:.2f}"
    scan_table = measured("同戳 LaserScan 与 PointCloud2", ["消息", "实测结构", "几何与时间"], [
        ["LaserScan", f"{scan['beams']} 束，{scan['finiteRanges']} 束有有限距离",
         f"中心 {scan['centerRangeM']:.4f} m，angle_increment {scan['angleStepRad']:.3f} rad"],
        ["PointCloud2", f"{cloud['width']}×{cloud['height']}，每点 {cloud['pointStep']} B，每行 {cloud['rowStep']} B",
         f"x/y/z 偏移 {vector(cloud['xyzOffsets'], 0)} B，中心点 {vector(cloud['centerM'])} m"],
        ["时间字段", "scan_time = time_increment = 0 s",
         f"桥没有填逐束时差。此轮相邻扫描 Header 间隔为 {intervals_text} s"],
    ], "板面理论中心为 2.20 m。两端射线越过板边，样本含非有限回波。读取点云时按消息字段、行步长、点步长和端序解码。")
    args = dict(label="运行 Gazebo 传感器实验", language="bash", type="commands", code=(
        "# 在 ros2-learning-hub 目录执行，需已安装 Jazzy、Harmonic、ros_gz_bridge 与 cv_bridge。\n"
        "source /opt/ros/jazzy/setup.bash\n"
        "# 输入是本地小世界和桥映射。227 为隔离本机 DDS 域。结果写到新建 /tmp 目录。\n"
        "python3 examples/gazebo_labs/validate_sensors.py --domain-id 227\n"
        "# Ogre2 若无法创建 EGL 上下文，可用 --egl-vendor-json 指向本机有效的 vendor JSON。"),
        explanation="先在暂停世界发现服务和端点，再让真实世界运行并核对时钟、相机、点云与 ROS 消费端。")
    configs = [dict(label="gazebo_labs/" + name, language=language, type="complete",
                    sourceFile="examples/gazebo_labs/" + name, explanation=description)
               for (name, language), description in zip(FILES.items(), (
                   "独立 SDF 文件。世界只包含本地红板和静止传感器台架，固定安装和无噪声设定只用于检查接口。",
                   "五条单向数据映射，世界控制作为单独服务桥。frame_id 字符串和实际 TF 分开设置。",
                   "执行与回收进程，按时戳对齐消息，验证数据字段、图像与点云并留存报告和原始采样。",
               ))]
    versions = report["versions"]
    runtime = (f"在本机 {versions['gzSim']} 与 Jazzy ros_gz_bridge {versions['ros_gz_bridge']}，"
               f"域 {report['domainId']}/LOCALHOST、独立 Gazebo Transport 分区实际运行。")
    scope = "范围为固定模拟相机、激光和实际桥接，GUI、实机、SLAM、Nav2 和底盘仿真由其他实验验收。"
    chapters = {
        "eco-gazebo-simulation": dict(appendSourceIds=["sensor-gz-world", "sensor-bridge-config", "sensor-control", "sensor-template"],
            validation=runtime + "通过无窗口 EGL Ogre2 实测时钟、传感器、世界控制和暂停恢复。" + scope,
            appendSections=[section("在本地小世界实测单向桥与暂停恢复", [
                "把 SDF 中的物理系统和 Sensors 系统分开观察。步长为 0.005 s，传感器配置 10 Hz。模型只由本地几何构成，ROS 端取得图像、内参、激光和点云之后再谈算法。",
                "官方工程模板把速度命令放在 ROS 到 Gazebo 的方向，并把时钟、里程计和扫描放在反向。本例从世界专属 /world/hub_perception/clock 转发到 ROS /clock，五条数据映射实际查到桥发布端和单向图结构。ControlWorld 走单独服务路径，响应成功后还要检查时钟是否推进。",
                "SDF 只描述仿真中的数据。桥的 ROS 类型、QoS 和命名空间由 YAML 显式给出，传感器 frame_id 与下游提供的 TF 逐一配对。原始 Header 保持仿真采集时间。本机无窗口运行选择了可用的 EGL vendor，先前的软件 EGL 路径在驱动初始化阶段失败。",
            ], [clock_table], [args, *configs])],
            appendExercises=[
                exercise("世界控制回执成功后还需要看什么？", "等待相应窗口内的 /clock 和传感器采集时戳按预期冻结或推进。用单调秒限制等待。"),
                exercise("多个 Gazebo 世界时，应怎样给同一 ROS 域提供 /clock？", "选择一个世界的限定时钟主题作为 ROS /clock 的唯一提供者。其他世界需要另设隔离域或时钟命名方案，避免同时驱动消费者。"),
            ]),
        "eco-perception-pipeline": dict(appendSourceIds=["sensor-image-contract", "sensor-image-calibration", "sensor-opencv",
                "sensor-scan-contract", "sensor-converters", "sensor-pcl-layout", "sensor-pcl-convert"],
            validation=runtime + f"真实桥接图像并使用 cv_bridge {versions['cv_bridge']}、OpenCV {versions['opencv']} 处理，按二进制结构解码点云。" + scope,
            appendSections=[section("从模拟传感器核对采集、编码、内参与点字段", [
                "把 Image、CameraInfo 和处理后的边缘图按 Header.stamp 精确配对，再核对光学 frame。96 像素宽、水平视场 π/3 rad 时，fx=96/(2·tan(π/6))≈83.14 px。读 CameraInfo 的 K 与本次采样配置交叉核对，K、D、R、P 的校正过程在相机资料中分别说明。",
                "RGB 输入经 cv_bridge 按显式编码转换成 BGR 数组。对这块红板，灰度换算压低了边界对比度；同一 Canny 阈值应用到红通道后检出竖边。输出 mono8 时保留原时戳和 frame，改像素颜色不需要重写采样位置或时间。阈值和选色结果仅限这个场景。",
                "扫描中心束和点云中心点应对应同一板面。点云解析必须先看 fields、point_step、row_step 与端序，再用偏移读坐标，过滤非有限点。PointCloud2 与 PCL 结构的转换也有实际复制边界。本地 pcl_conversions 的 toPCL 给数据数组赋值，moveToPCL 则交换数组，应用要根据调用的重载判断开销与输入所有权。",
                f"本例 LiDAR 的 scan_time 和 time_increment 均为零，同时实测相邻采样 Header 间隔为 {intervals_text} s。源码的桥转换没有从模拟器消息填入两个时长字段。对运动平台做去畸变前，应先确认驱动是否提供逐束时序及完整时间源。",
            ], [image_table, scan_table])],
            appendExercises=[
                exercise("为何同阈值的灰度图和红通道会有不同边缘结果？", "灰度对通道加权，颜色边界可能只有很小的亮度梯度。先核 RGB/BGR 顺序，再按所需目标选择通道或改阈值。"),
                exercise("点云有三个 FLOAT32 坐标，为何每点 32 B？", "点还可能有附加字段及对齐填充。字段的 offset 描述 x/y/z，每点和每行长度按 point_step、row_step 读取。"),
            ]),
        "eco-tf-frames": dict(appendSourceIds=["sensor-image-contract", "sensor-scan-contract", "sensor-bridge-config"],
            sections={"6": dict(appendParagraphs=[
                "仿真章另以真实桥接相机 Header 时戳查询 rig_base ← camera_optical_frame。光学单位点 (0, 0, 1) m 和同原点激光的 (1, 0, 0) m 都变到台架 (1, 0, 0) m。桥的 frame_id 覆盖只改标签，轴向关系由独立静态 TF 提供。模型章带安装平移的光学试验仍单独记录。",
            ])}, appendExercises=[
                exercise("只把 Gazebo 图像的 frame_id 改成 camera_optical_frame，会发生轴变换吗？",
                         "改名不改变像素或三维轴。应为相机安装位置与光学旋转发布相应 TF，并用采样时戳查变换。"),
            ]),
        "qos": dict(appendSourceIds=["sensor-bridge-config", "sensor-clock-client"],
            appendSections=[section("发现扫描话题后，分别核对匹配和接收", [
                f"在真实 Gazebo 桥的扫描话题上同时放两个订阅者。图上有 {qos['scanGraphPublishers']} 个 BEST_EFFORT 发布者；BEST_EFFORT 订阅匹配并收到 {qos['bestEffortSamples']} 条，RELIABLE 订阅匹配数为 {qos['reliableMatched']} 且零接收。报告记录了同一时间窗下的端点和接收计数。",
                "排查时分开记录话题名与类型、端点提供与请求 QoS、实际收到的采样数。把订阅策略对齐到模拟传感器只能解决传输匹配，Header、坐标系和数据质量仍要分别验证。",
            ])], appendExercises=[
                exercise("topic list 能看到 scan，但 RELIABLE 消费者一直空，先看什么？",
                         "查实际提供端的可靠性和消费端请求值。若提供 BEST_EFFORT，可对照同窗 BEST_EFFORT 订阅的匹配和接收。"),
            ]),
        "time-bag": dict(appendSourceIds=["sensor-control", "sensor-clock-client"],
            sections={"0": dict(appendParagraphs=[
                "仿真章用真实 Harmonic 观察到暂停后 ROS 时间与五类采样时戳冻结，恢复后同步继续。软件定时器、录放与真实世界控制分别有证据。重放接入同一域前，先划清现场桥和回放的 /clock 发布职责；监测暂停或服务无响应时采用单调超时。",
            ])}, appendExercises=[
                exercise("Gazebo 暂停后，为何检查程序仍能在 0.40 秒结束？",
                         "0.40 秒来自本机单调时钟。订阅的仿真时间保持不变，程序超时仍能继续计算。"),
            ]),
        "eco-slam-mapping": dict(appendSourceIds=["sensor-slam-input", "sensor-scan-contract", "sensor-converters"],
            sections={"1": dict(appendParagraphs=[
                "先用仿真章的实际扫描核第 20 束距离约 2.20 m、激光 frame 和采样时戳。SLAM Toolbox 配置还需独立指定 scan_topic、odom_frame、base_frame 与 map_frame。静止台架只检查入口；走廊、转弯和回环的建图效果需要有运动和里程计的不同数据。",
            ])}, appendExercises=[
                exercise("只有连续重复的静止墙面扫描，能否验收建图的回环？",
                         "回环需要实际重访与时序观测。静止采样只适用于验收扫描结构、坐标与输入链路。"),
            ]),
        "eco-nav2-stack": dict(appendSourceIds=["sensor-nav2-filter", "sensor-scan-contract"],
            sections={"2": dict(appendParagraphs=[
                "Nav2 障碍层对 LaserScan 和 PointCloud2 分别使用 TF 消息过滤。先在仿真章验证实际 scan 的 QoS、采样时戳和 laser_link 到基座的变换，再核对代价地图实际配置的目标帧。远处无回波可能为无穷值，标记、清除、inf_is_valid 与距离参数分别检查。这里的传感器实测范围止于消费合同，代价地图输出与导航任务另验。",
            ])}, appendExercises=[
                exercise("激光 echo 有数据，代价地图仍无障碍，如何沿链路排查？",
                         "查障碍层订阅的实际话题与数据类型，再按 Header.stamp 检查目标帧 TF，最后检查标记范围、清除和无穷距离规则。"),
            ]),
    }
    api = dict(id="api-gz-sensor-contract", title="仿真桥接与传感器消费合同",
        lessons=["eco-gazebo-simulation", "eco-perception-pipeline"],
        columns=["接口", "输入", "实际检查", "边界"], rows=[
            ["Clock", "Gazebo 世界时间", "单向发布到 ROS /clock", "消费者显式 use_sim_time，监控采用单调软期限"],
            ["ControlWorld", "pause 布尔请求", "服务回执与实际时钟推进", "服务发现和世界执行是不同证据"],
            ["Image / CameraInfo", "编码、行字节、内参、采集 Header", "同帧同戳、颜色与尺寸", "重标 frame 后另有正确 TF，校正另用相机模型"],
            ["LaserScan", "角度 rad，距离 m，采样时戳", "41 束与中心 2.20 m", "零扫描时间字段按桥版本解释，非有限回波保留语义"],
            ["PointCloud2", "字段、字节偏移、端序、行/点步长", "解码中心三维坐标", "先筛非有限点，别把数组直接当连续 XYZ"],
        ])
    # 旧章编号保持稳定，原有七节之后是新增实测。
    save_figure(report, perception_index=7)
    patch = dict(meta=dict(report=REPORT.relative_to(ROOT).as_posix(), reportSha256=sha(REPORT), sourceReads=reads),
                 chapters=chapters, resources=sources, apiReferences=[api])
    (ROOT / "source/gazebo-sensor-revision.json").write_text(json.dumps(patch, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(chapters=len(chapters), sources=len(sources), checkedSourceFiles=len(reads), tables=3, figures=1)))


if __name__ == "__main__":
    main()
