#!/usr/bin/env python3
"""给原有 44 章的全部代码位置生成中文教学注释覆盖层。

输入：core/ecosystem/extra/frontier 与三份 expanded 内容，按原构建器顺序合并。
输出：source/code-annotations.json；只有 --update-files 才为原创 atlas/foundation 文件加注释。
注释记录每例实际目的、输入输出、物理单位、参数语义、执行顺序及生命周期边界。
除meta明示的后端切换/看门狗输入验证修复外，只加注释和解释；其余Python AST保持一致。
XML/YAML/CMake/INI 使用各自合法注释；CSV、JSON、普通示意文本保留内容并扩展解释。
不运行 ROS 节点或用户硬件；脚本的检查仅为语法、AST/解析结构及注释覆盖检查。
"""

from __future__ import annotations

import argparse
import ast
import configparser
import hashlib
import io
import json
import re
import shlex
import subprocess
import tempfile
import tokenize
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


HUB = Path(__file__).resolve().parents[1]
SOURCE = HUB / "source"
MARKER = "【中文教学注释】"

# 每章注释上下文来自该章实际实验，不用同一条“输入ROS输出日志”代替不同任务。
# 元组分别说明输入输出和关键边界；单位在具体 API/字段旁进一步解释。
CONTEXT = {
    "architecture": ("输入是已启动节点及当前终端的 ROS 环境；输出是节点、话题、接口类型的发现结果。", "先启动相容的发布/订阅端，再查询计算图；发现端点不能证明业务处理完成，图中数量也不是发送频率。"),
    "installation": ("输入是 Ubuntu 版本、区域设置和 apt 源；输出是软件包安装结果及跨语言通信日志。", "平台检查先于安装；安装需联网和相应系统权限，source 只影响当前终端，不代表其他终端已加载环境。"),
    "workspace": ("输入是 src 中的包清单、源码和构建配置；输出先是 install 产物，随后才是节点进程的日志。", "先加载 Jazzy underlay，再构建并 source overlay；包名、安装目标与 console_scripts 必须一致，单个源码文件不能替代整个包。"),
    "graph-cli": ("输入是运行中的 turtlesim/演示节点；输出为图结构、消息、参数值或一次请求的响应。", "查询命令与持续发布/echo 分别运行；速度字段采用 m/s、rad/s，背景颜色是 0..255 的无量纲整数，节点重命名不自动改变所有绝对话题。"),
    "pubsub": ("输入为定时触发或收到的 String 消息；输出为带序号的消息及接收日志，序号无量纲。", "初始化→创建并持有节点/端点→spin 分发回调→清理；历史深度 10 不是 10 Hz，定时周期以秒或毫秒单独指定。"),
    "interfaces": ("输入为 msg/srv/action 定义及生成配置；输出为两种语言可使用的类型和 wheel_feedback 测量。", "接口必须先生成并加载再导入；轮速单位 rad/s，Header 指定采样时刻与坐标系，gain 无量纲，valid 不能被缺省数值替代。"),
    "services": ("输入为 AddTwoInts 请求中的两个小整数；输出为 sum 响应和成功/失败退出码，无物理单位。", "先发现服务再发请求；Future 返回不等于响应已完成，等待超时不会撤销服务端已经发生的业务副作用。"),
    "actions": ("输入为 Count 目标 target 或取消请求；输出为 current 反馈、completed 结果及终态，计数无量纲。", "服务端接受 1..20 且同一时刻只运行一个目标；每步约 0.5 秒。取消请求被接受与任务已取消是两个事件，共享 busy 状态按线程模型保护。"),
    "parameters": ("输入为启动覆盖值或动态参数请求；输出为 gain/enabled 的验证结果和 configured_value。", "gain 为有限无量纲 double，范围 [0,2]；先验证启动值，再注册动态验证器。回调通过后才应提交配置，参数回调不能阻塞执行器。"),
    "launch": ("输入为 launch 参数、包内文件路径和 YAML 配置；输出为具有指定命名空间、重映射和参数的节点进程。", "launch 描述在启动阶段解释，动作书写顺序不等于应用已就绪；相对话题继承命名空间，参数文件顶层节点名必须匹配实际节点。"),
    "qos": ("输入为发布/订阅 QoS 策略和消息；输出为端点匹配结果或晚加入者收到的缓存状态。", "depth 是历史条数；reliable/best_effort 与 transient_local/volatile 有请求-提供兼容约束。发布一次后仍须保留端点，缓存并不等于磁盘永久保存。"),
    "executors": ("输入为定时事件、异步服务 Future 和单调时钟；输出为轮询得到的响应或超时日志。", "0.2 秒回调只推进状态，不同步阻塞等待服务；2 秒超时用单调时钟，移除待处理请求不取消远端业务，多线程仍受回调组与 Python GIL 约束。"),
    "lifecycle": ("输入为 configure/activate 等状态转换请求；输出为生命周期状态和激活后发布的数据。", "状态应逐步核对；节点存在不代表已激活，转换成功不等于其他依赖已准备就绪，失败转移必须按当前状态处理。"),
    "composition": ("输入为已安装组件插件、容器和 NodeOptions；输出为已装入同一进程的节点与话题。", "C++ 组件由容器持有，无独立 main；注册插件、导出库、安装、加载缺一不可。进程内通信要求相应选项，组件故障仍可影响同一容器。"),
    "tf2": ("输入是带 source frame 和采样时间的 PointStamped 及 TF 缓存；输出为 base_link 中的点。", "平移单位 m、旋转 rad；按输入消息时刻查变换，缺失/外推失败时丢弃并记录。Time(0) 与消息时间不是同一语义，不在单线程回调中长期阻塞等 TF。"),
    "time-bag": ("输入为话题数据、Header 时间戳与选定时钟；输出为 bag 文件、回放消息和时间观测值。", "先录制再停止检查，回放前停掉同话题实时发布者；use_sim_time 需 /clock，暂停/跳转可能使 ROS 时间停住或倒退，QoS 覆盖不修复原始坏数据。"),
    "testing": ("输入为速度、纳秒时间戳和超时阈值，或受控启动的 talker；输出为断言、消息观测及测试退出状态。", "边界含 age==timeout、负年龄、NaN 和缺失输入；集成测试用单调时间设上限，测试节点和订阅者最后销毁，不将单元通过冒充实机安全。"),
    "network": ("输入为各终端的 Domain ID、RMW、发现范围和对端地址；输出为发现/组播诊断结果。", "设置后重启节点与 CLI daemon；Domain ID 无量纲且不是访问控制。静态对端地址必须替换为实际学习机，网络连通不保证 QoS/类型相容。"),
    "security": ("输入为实验密钥库、enclave 与 DDS 权限规则；输出为签名权限文件和受限通信结果。", "先创建身份和签名材料，再显式选 DDS 后端并启用 Enforce；示例仅用于独立实验目录，修改 XML 后必须重签，私钥不能随学习包发布。"),
    "performance": ("输入为合成 CSV 或真实追踪事件；输出为等待/回调时延、分位数和样本缺失等统计。", "CSV 时间均为 ns，除以 1,000,000 才是 ms；端到端时延不能与回调执行时间混淆，合成数据和一次追踪都不能证明实时性上界。"),
    "eco-tf-frames": ("输入为 map/odom/base_link/sensor 的父子关系、时间戳与静态安装参数；输出为可查询的变换链。", "平移 m、角度 rad；每个 child 应只有一个有效父关系，静态外参不能代替动态里程计，查询成功还需核对方向和时间。"),
    "eco-model-rviz": ("输入为 URDF/Xacro、关节状态和 RViz 固定坐标系；输出为展开后的模型与可视化。", "几何尺寸 m、rpy 为 rad；先展开宏再检查 URDF，visual/collision/inertial 职责不同，此最小显示模型没有完整动力学和控制能力。"),
    "eco-gazebo-simulation": ("输入为 SDF 世界与桥配置；输出为仿真进程及 ROS /clock。", "物理步长单位 s，实时因子无量纲；先运行世界再运行单向时钟桥，算法 use_sim_time 须一致，ROS 与 Gazebo 类型名不能直接互换。"),
    "eco-control-framework": ("输入为 URDF 控制接口、硬件插件和控制器配置；输出为状态接口、命令接口和控制器状态。", "加载硬件并导出接口后才能配置/激活控制器；mock 反馈不是真实编码器，控制标签片段不包含完整机器人或启动工程。"),
    "eco-diff-drive-tracks": ("输入为底盘线速度/偏航角速度和轮几何；输出为左右轮命令、反馈及里程计。", "车速 m/s、偏航 rad/s、轮半径/轮距 m、关节速度 rad/s；先确认 Twist 或 TwistStamped，超时停车依赖控制器与硬件实现。"),
    "eco-hardware-integration": ("输入为教学协议的速度/字节串或已配置设备的观测数据；输出为编码字节和解码后的状态。", "速度 m/s 乘 1000 编成 mm/s int16，小端且溢出拒绝；示例没有厂商协议兼容承诺，CAN/串口命令需对应实际配置，不在此处发硬件运动命令。"),
    "eco-slam-mapping": ("输入为 LaserScan、TF、时钟与建图参数；输出为合成扫描、地图和保存文件。", "距离 m、角度 rad、栅格分辨率 m/cell；合成方房间只是数据契约实验，没有真实运动或 SLAM 精度证明。保存前检查 TF 和扫描时间。"),
    "eco-state-estimation": ("输入为轮速 Odometry 和协方差、滤波配置；输出为融合里程计及选定 TF。", "线速度 m/s，姿态/角速度分别 rad、rad/s；15维配置向量顺序固定。示例只融合 x 速度，TF 只保留一个发布者，协方差不是任意置信百分比。"),
    "eco-nav2-stack": ("输入为地图、定位、TF、传感器与导航目标；输出为 Nav2 状态、规划和控制行为。", "先验证环境和定位，再送目标；生命周期激活不等于定位已可信。集成仿真依赖单独准备，本文检查不会自动完成真实机器人验收。"),
    "eco-nav2-task-programming": ("输入 --start/--goal 为 map 中 x、y、yaw；输出为导航任务结果或取消状态。", "位置 m、yaw rad、timeout s；先设初始位姿并等待 Nav2 激活，再发目标。激活等待本身不受任务 deadline 约束，取消发出后仍等终态。"),
    "eco-moveit-planning": ("输入为机器人状态、规划场景和目标；输出为规划轨迹及执行端点信息。", "转动关节位置 rad、移动关节 m，time_from_start 为相对轨迹起点的时长；mock 轨迹可视化不能证明真实碰撞、力矩或急停功能已验证。"),
    "eco-manipulation-tasks": ("输入为任务状态或 requested_velocity；输出为受限位置增量和任务成功/失败分支。", "离线积分中位置 rad、速度 rad/s、dt s；先限速再积分，只验证数值接口，不具备完整碰撞、抓持力或失效安全保证。"),
    "eco-perception-pipeline": ("输入为合成像素图像或 ROS Image；输出为原图和边缘图话题。", "图像尺寸以像素计，颜色 bgr8/mono8 为编码；生成周期 0.1 s。处理保留原采样 Header，转换不等于相机已标定或图像已同步。"),
    "eco-data-observability": ("输入为已知话题数据和录制配置；输出为 bag/MCAP 元数据、回放与诊断信息。", "先保留完整最小实验再对比；回放用原时钟须显式发布 /clock，端到端链路、存储和可视化各自可能丢失信息。"),
    "eco-microcontrollers": ("输入为匹配版本的 Agent/MCU 传输以及离线看门狗请求；输出为 ROS 端点或受限目标。", "UDP 端口为整数，串口波特率为 bit/s；看门狗时间 s、限速 m/s。Agent 连接不代表 MCU 控制循环安全，失联处理应在设备端独立实现。"),
    "eco-multi-robot": ("输入为命名空间/域配置或资源占用请求；输出为隔离后的图和占用许可。", "资源名/机器人名为离散标识；示例字典只有单进程顺序语义，没有分布式原子性、租约或故障恢复，命名空间也不是网络隔离或权限控制。"),
    "eco-network-security": ("输入为 RMW、路由器和 DDS 身份权限配置；输出为连接、发现与受限通信证据。", "Zenoh 与 DDS-Security 是不同机制；做本章 SROS2 实验前必须显式切回受支持 DDS 后端，不能沿用 rmw_zenoh_cpp 后只设置 ROS_SECURITY_*。"),
    "eco-accelerated-robotics": ("输入为假设的 CPU/GPU 各环节时延或 ROS 感知数据；输出为中位数和尾部分位数。", "合成时延单位 ms，q 无量纲且应在 [0,1]；数组必须非空。GPU 计算快不保证端到端尾延迟低，结果不是硬件测速。"),
    "deployment": ("输入为已验证源码、依赖和镜像构建上下文；输出为安装产物、容器镜像及归档摘要。", "先固定版本再构建验证；容器仍共享主机内核和网络条件。entrypoint 应 exec 传递信号，镜像可加载不代表架构、设备与实时能力相容。"),
    "migration": ("输入为旧 Twist 或待迁移接口/参数；输出为新消息结构和兼容性检查结果。", "速度值仍是 m/s、rad/s；适配器用接收时刻补 stamp，并不能恢复旧消息真实采样时间或完成坐标变换，两个输出发布者会产生竞争。"),
    "learning-rl": ("输入为候选增益、随机种子和教学动力学参数；输出为训练收益、选定增益和留出条件结果。", "模型约定位置 m、速度 m/s、质量 kg、积分步长 0.05 s；力限制 ±1 N。奖励是选定标度的教学目标，不是物理能量，也未连接机器人。"),
    "learning-embodied": ("输入为 JSON 任务提案和地点/技能白名单；输出为 DRY_RUN 或拒绝原因。", "计划限 1..8 步，timeout 为有限秒值且 0<值≤120；先做结构和字段验证，再演示计划，不执行 shell、ROS 或真实动作。"),
    "learning-policy": ("输入为6关节位置候选、上一目标、数据年龄和控制周期；输出为限幅/限速位置或 None。", "关节位置 rad、年龄/dt s、limit rad/s；拒绝非有限数，数据年龄上限0.1s。None 需调用者选择已验证停止/保持策略，限幅并不保证无碰撞。"),
    "cloud-mlops": ("输入为只读数据目录；输出为相对路径、字节数与 SHA256 的确定性 JSON 清单。", "按路径排序并分块哈希，不修改原数据；软链接必须有独立策略。摘要证明字节一致性，不证明标签、校准或训练划分正确。"),
}


def load_final_originals():
    """只解析 JSON，不 import 会写生成物的原构建器，也不读取新增16章。"""
    data = {name: json.loads((SOURCE / f"{name}.json").read_text())
            for name in ("core", "ecosystem", "extra", "frontier")}
    chapters = {chapter["id"]: dict(chapter) for name in data for chapter in data[name]["chapters"]}
    for name in ("foundation-expanded", "engineering-expanded", "ecosystem-expanded"):
        for chapter in json.loads((SOURCE / f"{name}.json").read_text())["chapters"]:
            chapters[chapter["id"]].update(chapter)
    comparisons = data["core"]["comparisons"] + data["extra"]["comparisons"]
    assert len(chapters) == 44
    return chapters, comparisons


def brief(value: str, length: int = 220) -> str:
    return re.sub(r"\s+", " ", value).strip()[:length]


def context_lines(chapter: str, label: str, explanation: str, mode: str = "", code: str = "") -> list[str]:
    inputs, boundary = CONTEXT[chapter]
    if mode == "cmake":
        inputs = "输入是本包源码、已安装依赖及目标配置；输出为构建目标、安装文件和ament导出元数据。"
        boundary = "先find_package再建立/连接目标并install，最后ament_package；VERSION是工具/语言版本而非物理单位，源码存在不等于已安装入口。"
    elif mode == "ini":
        inputs = "输入为setuptools安装配置；输出是开发/普通安装时的脚本目标目录，供ROS按包名发现入口。"
        boundary = "script_dir/install_scripts均与console_scripts配套；$base是安装基路径，目录配置没有物理单位，不负责创建ROS节点。"
    elif mode == "xml" and "package.xml" in label:
        inputs = "输入为包名、版本、许可和依赖元数据；输出是ament/rosdep/发布工具可读取的包清单。"
        boundary = "包名须与构建/安装配置一致，buildtool、depend、exec_depend作用不同；元数据本身不执行安装，版本字段不是物理量。"
    elif mode == "python" and label.endswith("setup.py"):
        inputs = "输入为包名、Python模块、资源文件及入口映射；输出为可安装Python包和console_scripts可执行入口。"
        boundary = "resource索引/package.xml需安装到正确share目录；入口名=模块:function，setup.cfg将脚本装入lib/包名；此配置没有物理单位或ROS回调循环。"
    purpose = brief(explanation)
    if purpose.startswith("随离线教材保存的原创教学文件；"):
        # 文件来源由路径、许可证和manifest保存，不能再把同一输入输出重复当作用途。
        purpose = ""
    else:
        normalize = lambda value: re.sub(r"[\s，。；：、,. ;:]+", "", value)
        comparable = re.sub(r"^(?:本例作用|输入输出)：", "", purpose)
        if normalize(comparable) == normalize(inputs):
            purpose = ""
        elif inputs in purpose:
            purpose = purpose.replace(inputs, "").strip(" ，。；：,.;:")
        if re.fullmatch(r"完整\s*(?:(?:C\+\+|Python)\s*)?(?:文件|模块|脚本|示例)[。.]?", purpose):
            purpose = ""  # 完整/片段属性已由代码块元数据与文件标签明确表达。
    result = [f"{MARKER} {label}"]
    if purpose:
        result.append("本例作用：" + purpose)
    result.extend(["输入输出：" + inputs, "执行顺序与边界：" + boundary])
    return result


def protected_python_lines(code: str) -> set[int]:
    """多行字符串中不能插入 #，否则会改变 docstring 或发送的文本。"""
    protected = set()
    try:
        for token in tokenize.generate_tokens(io.StringIO(code).readline):
            if token.type == tokenize.STRING and token.end[0] > token.start[0]:
                protected.update(range(token.start[0], token.end[0] + 1))
    except (tokenize.TokenError, IndentationError):
        pass  # 局部片段最终以原有代码的解析能力为基准，不强行补成完整文件。
    return protected


def python_note(line: str, chapter: str) -> str | None:
    """按实际 API 调用、字段和单位写注释，不按行号机械重复套话。"""
    s = line.strip()
    if chapter in {"launch", "composition", "testing"} and (s.startswith("Node(") or "launch_ros.actions.Node(" in s):
        return "这是launch的Node启动动作：package/executable定位已安装入口，name/namespace决定ROS名称，parameters与remappings在启动阶段配置；不等于rclpy运行期Node对象。"
    rules = [
        (r"\brclpy\.init\(", "初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。"),
        (r"\brclpy\.shutdown\(", "关闭本进程 ROS 上下文；先停止执行器、销毁端点/节点，再在上下文仍有效时调用。"),
        (r"\brclpy\.ok\(", "检查 ROS 上下文仍有效，避免退出流程重复 shutdown；它不表示节点业务健康。"),
        (r"spin_until_future_complete\(", "在一次性 main 流程中分发回调直到 Future 完成或 timeout_sec 秒到期；不能原样嵌套到已 spin 的同一节点回调中。"),
        (r"spin_once\(", "最多等待 timeout_sec 秒并执行一次可用回调；返回后仍须检查消息/期限，不能当成固定周期睡眠。"),
        (r"(?:rclpy|executor)\.spin\(", "进入执行器事件循环，定时器、订阅、服务和 Future 回调在这里才被推进；通常阻塞到中断或上下文关闭。"),
        (r"super\(\)\.__init__\(", "构造 Node 基类并确定节点名；后续相对话题/服务名由命名空间解析，重命名需与参数文件选择器对应。"),
        (r"(?:=\s*Node|rclpy\.create_node)\(", "创建并持有节点对象；本进程退出前应显式 destroy_node，创建节点本身不会自动处理回调。"),
        (r"create_publisher\(", "创建指定消息类型和话题的发布端并持久保存；整数 QoS 是 KeepLast 历史深度，不是 Hz，真正发送由 publish 调用决定。"),
        (r"create_subscription\(", "绑定消息类型、话题、回调和 QoS，并持有订阅对象；/开头的名称是绝对话题，回调由执行器调度。"),
        (r"create_timer\(", "定时周期单位为秒，回调由执行器调度而非自动新建独占线程；使用节点时钟，仿真时间暂停可能影响触发。"),
        (r"create_service\(", "创建服务端并保存句柄；收到请求后执行回调，需返回填好的 Response，服务发现与请求执行是不同阶段。"),
        (r"create_client\(", "创建服务客户端，接口类型和服务名须与服务端一致；此调用不保证服务已经发现。"),
        (r"wait_for_service\(", "只等待服务发现，timeout_sec 单位为秒；返回 False 应走失败分支，发现成功不保证随后请求一定成功。"),
        (r"service_is_ready\(", "非阻塞检查服务是否已发现；未就绪时让当前回调尽快返回，避免阻塞其他事件。"),
        (r"call_async\(", "提交请求并立即返回 Future；仍需执行器处理响应，保存 Future 才能关联完成、异常与超时。"),
        (r"add_done_callback\(", "注册 Future 完成回调；这不保证开启新线程，完成回调应检查异常且尽快返回。"),
        (r"remove_pending_request\(", "从客户端本地待响应表移除此 Future；只回收本地跟踪，不撤销服务端可能正在执行的工作。"),
        (r"\.done\(\)", "先检查 Future 是否已经结束；完成仍可能包含异常，需要与 result()/exception() 的错误处理配合。"),
        (r"\.exception\(\)", "读取已完成 Future 的异常状态；None 表示未携带异常，不等于业务结果天然正确。"),
        (r"\.result\(\)", "提取已经完成的异步结果；可能抛出传输/服务异常，不能把未完成 Future 的结果当作有效 Response。"),
        (r"destroy_subscription\(", "取消订阅并释放该订阅者的 ROS 资源；测试结束后不继续占用端点。"),
        (r"destroy_node\(", "显式释放节点所属端点与定时器；应在相关执行器不再访问节点后执行。"),
        (r"executor\.shutdown\(", "先停止执行器并等待其工作回调结束，再销毁节点；避免回调继续访问已释放对象。"),
        (r"MultiThreadedExecutor\(", "创建给定 num_threads 的执行器工作线程；并发还受回调组、共享状态锁以及 Python GIL 影响。"),
        (r"ReentrantCallbackGroup\(", "允许该组回调重入/并发；它不自动保护 busy 等共享变量，必须另用锁或状态机。"),
        (r"threading\.Lock\(", "为目标接纳与任务完成共享的状态建立互斥锁；锁内只做短操作，不在持锁时长时间执行任务。"),
        (r"with self\.lock", "原子检查并更新忙闲标志，防止并发目标同时被接受；离开 with 后自动释放锁。"),
        (r"ActionServer\(", "建立动作服务端，分别接线目标接纳、执行和取消回调；这些阶段不能混作一次普通服务调用。"),
        (r"ActionClient\(", "建立 Count 动作客户端，名称和 Action 类型须匹配服务端；对象保留至取消/结果处理结束。"),
        (r"wait_for_server\(", "等待动作服务端发现，timeout_sec 以秒计；True 只说明发现条件满足，不代表目标已被接受。"),
        (r"send_goal_async\(", "异步发送目标并接入反馈回调；此 Future 返回目标接纳句柄，最终任务结果要另用 get_result_async。"),
        (r"get_result_async\(", "在目标已接受后申请结果 Future；结果包装中同时包含终态 status 和业务 result。"),
        (r"cancel_goal_async\(", "异步请求取消；取消响应只说明是否进入取消流程，仍要等待最终 CANCELED/其他终态。"),
        (r"is_cancel_requested", "检查任务取消标志，并在任务自身的可中断边界主动退出；仅接收请求不会自动终止耗时业务。"),
        (r"\.canceled\(", "将目标置为已取消终态；执行回调还须返回当前 Result，不能随后再调用 succeed。"),
        (r"\.succeed\(", "只在业务达到成功条件后设置 SUCCEEDED；Python 动作回调仍须返回 Result 对象。"),
        (r"publish_feedback\(", "发布中间进度而不结束目标；current 是无量纲计数，反馈不等于最终结果。"),
        (r"declare_parameter\(", "声明参数的名称、类型/默认值，并接收启动覆盖值；默认值不等于最终生效值，启动值仍需检查范围。"),
        (r"add_on_set_parameters_callback\(", "注册参数提交前验证器；只判断本次请求是否合法，不在这里产生不可回滚的业务副作用。"),
        (r"get_parameter\(", "读取当前已提交参数；value 的 Python 类型必须与声明一致，动态更新后的值在后续业务回调生效。"),
        (r"SetParametersResult\(", "返回本次参数验证是否接受以及原因；successful=False 会拒绝相应更新，而非悄悄限幅改值。"),
        (r"QoSProfile\(", "构造 QoS：depth 是样本条数；可靠性和持久性须与对端兼容，缓存深度不决定发布频率。"),
        (r"TRANSIENT_LOCAL", "保留发布者存活期间的历史样本供相容晚加入订阅者接收；仍受深度/资源约束，不是永久存储。"),
        (r"BEST_EFFORT", "允许丢样而不要求可靠重传，常用于实时传感器；reliable 请求端不能依赖仅 best_effort 提供端满足其要求。"),
        (r"qos_profile_sensor_data", "使用传感器 QoS 预设；关键是低积压和 best-effort 语义，双方仍需检查具体策略。"),
        (r"get_clock\(\)\.now\(\)\.to_msg\(\)", "取得节点当前 ROS 时刻并转换为 sec/nanosec 消息；use_sim_time 时来自 /clock，采样时刻应尽量靠近数据生成。"),
        (r"Buffer\(", "创建按时间缓存的 TF 查询器；缓存内容由 TransformListener 接收，创建 Buffer 不会凭空生成变换。"),
        (r"TransformListener\(", "订阅 /tf 与 /tf_static 并填充 Buffer，监听器及节点必须保持存活，接收仍需要执行器。"),
        (r"lookup_transform\(", "按目标坐标系、源坐标系和输入消息时刻查变换；方向不能反用，找不到或外推失败会抛 TransformException。"),
        (r"Time\.from_msg\(", "把消息采样时间转换为查询所需 Time；这是测量时刻，不能任意改成回调接收时刻。"),
        (r"do_transform_point\(", "对点应用查询到的旋转与平移，坐标单位 m；先保证 transform 对应正确源/目标和采样时刻。"),
        (r"time\.monotonic\(", "读取只用于测量经过时长的单调时钟，单位 s；不会随 ROS 仿真时间暂停或回拨。"),
        (r"time\.sleep\(", "按秒阻塞当前工作线程；本例只模拟耗时，不保证实时周期，动作服务器需要其他可运行线程处理取消。"),
        (r"LaunchConfiguration\(", "建立延后求值的 launch 参数替换对象；它不是普通 Python 字符串，执行启动动作时才解析。"),
        (r"DeclareLaunchArgument\(", "声明启动参数和默认值；外部 name:=value 可覆盖，参数名需与 LaunchConfiguration 相同。"),
        (r"ComposableNodeContainer\(", "描述持有多个 C++ 组件的进程；容器可选多线程，但插件内部仍需正确回调组和共享状态设计。"),
        (r"ComposableNode\(", "用包名和已注册 plugin 类型创建组件描述；不是直接运行普通可执行文件。"),
        (r"use_intra_process_comms", "显式请求进程内通信；两个组件须在同一进程及相容接口下工作，选项不保证所有路径零复制。"),
        (r"LaunchDescription\(", "返回 launch 动作集合，由启动系统执行；列表顺序不能作为节点发现/生命周期就绪屏障。"),
        (r"ReadyToTest\(", "通知 launch_testing 可以开始测试代码；只表示测试阶段就绪，不替代应用消息/状态的实际等待。"),
        (r"assertExitCodes\(", "在进程退出后核对被测进程退出状态；与运行期间是否收到有效消息是两项独立断言。"),
        (r"get_package_share_directory\(", "通过 ament 索引定位已安装包 share 目录；需要正确 source 环境，不能直接假设源码目录就是安装目录。"),
        (r"\bsetup\(", "setuptools读取包元数据、安装资源和入口；name应匹配package.xml，源码模块存在仍须console_scripts和setup.cfg才能由ros2 run找到。"),
        (r"\bfind_packages\(", "发现Python包目录，排除测试目录；包内__init__.py、实际模块名和入口映射需保持一致。"),
        (r"entry_points\s*=", "把可执行入口名映射到Python模块:function；ros2 run查找的是安装入口，不是任意.py文件名。"),
        (r"data_files\s*=", "安装ament资源索引、package.xml及需要的share文件；缺失索引时包可能已被pip装入却无法被ROS工具发现。"),
        (r"remappings\s*=", "在启动时改名连接端点；元组是(原名,新名)，相对名称受namespace影响，不改变类型/单位。"),
        (r"struct\.pack\(", "按 <h 编成小端有符号 int16；先将 m/s 放大为 mm/s 并检查 [-32768,32767]，不能静默溢出。"),
        (r"struct\.unpack\(", "按 <hb 读取小端 int16 速度和有符号 int8 温度；输入必须恰为3字节，速度随后除1000还原 m/s。"),
        (r"np\.zeros\(", "创建 height×width×channels 的 uint8 图像，尺寸是像素；本例全零黑底，不来自实际相机。"),
        (r"cv2\.rectangle\(", "按像素坐标绘制白色矩形，颜色顺序是 BGR，最后一个数是线宽像素。"),
        (r"cv2_to_imgmsg\(", "将 OpenCV 数组按指定 bgr8/mono8 编码转为 ROS Image；随后须正确设置或保留采样 Header。"),
        (r"imgmsg_to_cv2\(", "按 desired_encoding 解释图像字节，编码不匹配可能转换或报错；不能只依据数组形状猜测颜色顺序。"),
        (r"cv2\.cvtColor\(", "按明确的 BGR→灰度规则转换像素，避免将 RGB/BGR 顺序混淆；这不进行相机几何校准。"),
        (r"cv2\.Canny\(", "Canny 的50/150是梯度阈值，不是距离或置信概率；输出为单通道8位边缘图。"),
        (r"BasicNavigator\(", "创建 Nav2 Simple Commander 客户端节点；它依赖外部导航系统，不在此脚本中自动启动 Nav2。"),
        (r"setInitialPose\(", "发布 map 中的初始定位假设；位置 m、yaw rad，必须结合真实地图和实际初始位置选择。"),
        (r"waitUntilNav2Active\(", "等待导航和定位相关生命周期节点就绪；本调用在任务 deadline 建立之前，当前示例未给其单独设置总等待上限。"),
        (r"goToPose\(", "发送单个 map 位姿导航目标；先检查接纳结果，后续以 isTaskComplete/getResult 跟踪，不视作同步到达。"),
        (r"isTaskComplete\(", "推进并查询当前导航任务是否结束；False 不能单独解释为正在正常前进，仍需监测进度/失败和超时。"),
        (r"cancelTask\(", "请求取消当前导航任务；不把取消请求发出当作机器人已经停稳，仍等待任务终态。"),
        (r"getResult\(", "任务结束后读取 SUCCEEDED/CANCELED/FAILED 等结果，再决定下一步；不能仅依靠目标发送成功。"),
        (r"hashlib\.sha256\(", "建立 SHA256 摘要器，随后逐块更新；摘要只验证字节内容一致，不提供数据语义或标注正确性证明。"),
        (r"digest\.update\(", "按读取顺序累计原始字节摘要；不把路径或文本编码替代文件实际字节。"),
        (r"path\.is_symlink\(", "本实验拒绝软链接，以免扫描越过数据集边界；需要链接时必须先定义明确的数据归属策略。"),
        (r"json\.loads\(", "把 JSON 文本解析为数据，不执行其中内容；解析成功后仍必须校验类型、字段、白名单和数值范围。"),
        (r"subprocess\.run\(", "以参数列表调用 openssl 重签权限文件，check=True 使失败显式抛出；不使用 shell 拼接，不输出私钥内容。"),
        (r"ET\.parse\(", "读取实验权限 XML；后续只修改本实验授权规则，修改后旧签名失效，必须重新签名。"),
    ]
    for pattern, note in rules:
        if re.search(pattern, s):
            return note
    # 以下字段说明绑定到实际出现的行，补充单位、维度和范围。
    fields = [
        (r"\.left_velocity_rad_s|\.right_velocity_rad_s", "轮关节角速度单位 rad/s；正方向按本接口定义，不能直接当作底盘线速度 m/s。"),
        (r"\.frame_id\s*=", "坐标系名称是离散标识；它必须与数值实际表达的坐标系相符，改字符串不会完成坐标变换。"),
        (r"\.child_frame_id\s*=", "标明子坐标系；Odometry 中 pose 与 twist 的参考语义不同，不因字段填名就自动广播 TF。"),
        (r"\.angle_(?:min|max|increment)\s*=", "扫描角度单位 rad；angle_max 必须与角度起点、增量和实际样本数相符，360个点只有359个相邻间隔。"),
        (r"\.range_(?:min|max)\s*=", "有效距离上下界单位 m；真实无返回/越界样本还需遵循 LaserScan 的约定，不可随意当作零距离。"),
        (r"\.scan_time\s*=", "整次扫描时长单位 s；此合成实验不模拟每束激光在该时长内的真实运动畸变。"),
        (r"\.twist\.twist\.linear\.x\s*=", "Odometry 的前向速度单位 m/s；本例是合成测量，未同时积分位置或读取硬件编码器。"),
        (r"\.twist\.covariance\[", "6×6协方差按行展平，对角下标0/7/14/21/28/35；不同分量单位分别是速度/角速度单位的平方。"),
        (r"\.pose\.position\.[xy]\s*=", "map 中位置单位 m；赋值前必须确认输入坐标系和地图原点，而不是直接复制机器人局部坐标。"),
        (r"\.pose\.orientation\.[zw]\s*=", "平面 yaw 用 z=sin(yaw/2)、w=cos(yaw/2) 构造单位四元数；yaw 单位 rad，x/y分量保持0。"),
        (r"time_from_start|nanosec", "时间字段中的 sec 为秒、nanosec 为纳秒，1秒=10^9纳秒；二者不是相互独立的任意整数。"),
        (r"/\s*1_000_000", "把纳秒差转换为毫秒：1 ms = 1,000,000 ns；先确保两个时间戳来自可比较的时钟。"),
        (r"\.header\s*=\s*msg\.header", "处理结果沿用原始采样时刻与坐标系，不能把回调完成时刻冒充相机曝光时刻。"),
        (r"\.publish\(", "提交已填好的消息给 ROS 发布端；这不是业务处理完成确认，端到端接收仍取决于发现、类型、QoS 和执行器。"),
        (r"\.cancel\(\)", "取消当前定时器/Future的本地后续触发；取消本地对象不必然撤销已经发给远端的业务。"),
        (r"\.get_logger\(\)\.(?:info|warning|error)", "输出可观测日志用于核对状态；日志成功写出不等于对端收到消息或任务执行成功。"),
        (r"\bassert\b", "断言检验本例明确的数值/边界性质；失败立即暴露问题，不能用这里的合成样本证明所有输入或实机安全。"),
    ]
    for pattern, note in fields:
        if re.search(pattern, s):
            return note
    domain = {
        "learning-rl": [
            ("force =", "PD型教学策略按位置/速度反馈产生力，限幅±1N；gain对应位置反馈，0.8为所选速度反馈系数，未包含真实执行器与接触约束。"),
            ("velocity +=", "按显式离散更新速度：force/mass为m/s²，加上所选线性阻尼后乘0.05s；mass必须为正，当前实验使用预设正质量。"),
            ("position +=", "用更新后的速度积分位置，步长0.05s；这是所选离散教学模型，不能当作连续动力学的精确解。"),
            ("reward -=", "累积位置误差与控制幅度的加权惩罚；权重含人为尺度选择，不把两项当作同一物理能量。"),
            ("random.Random(", "使用本次rollout独立随机种子，避免候选之间不受控地共享随机状态；训练种子与留出种子分开。"),
        ],
        "learning-embodied": [
            ("allowed =", "白名单明确每种技能的完整允许字段集合，不能把自然语言或额外shell字段直接转换为可执行动作。"),
            ("type(timeout)", "显式拒绝bool、NaN、Inf及越界时长；Python中bool是int子类，因此这里检查具体type而非宽泛isinstance。"),
            ("PLACES =", "地点ID映射到预先认可的map位姿；x/y为m、yaw为rad，模型生成的任意坐标不直接获得执行授权。"),
        ],
        "learning-policy": [
            ("bounded =", "先把候选位置限制到[-1,1]rad；这是教学位置范围，不能替代实际每个关节的硬限位或碰撞检查。"),
            ("output.append(", "把单步位置变化限制为±limit×dt(rad)，保持输出维度和既定关节顺序；限速不保证轨迹连续加速度或安全避障。"),
            ("return None", "明确向调用者表示数据过期；调用者应进入已验证的停止/保持流程，不能把None当成零力矩。"),
        ],
        "performance": [
            ("math.ceil(", "nearest-rank分位数使用ceil(q×N)-1并夹住下界；这是经验样本统计定义，有限样本p99不是时延上界。"),
            ("unique =", "按序号集合区分重复和观测范围内缺号；没有观测范围外的期望总数，不能推算完整丢包率。"),
        ],
        "eco-manipulation-tasks": [
            ("velocity =", "把请求角速度限于±velocity_limit(rad/s)，再用于位置积分；只做运动学限幅，没有力矩、加速度或碰撞约束。"),
            ("return position +", "前向离散积分q_next=q+v×dt，q单位rad、dt单位s；本示例要求正周期与正速率上限。"),
        ],
        "eco-hardware-integration": [
            ("raw = round(", "速度m/s放大1000成为mm/s整数；round引入量化，发送前还须检查有符号int16的可表示范围。"),
            ("len(payload)", "先检查精确报文长度再按协议字段解包；不能把截断或额外字节默默解释成有效状态。"),
        ],
        "eco-slam-mapping": [
            ("distance = min(", "对边长4m、中心在传感器原点的合成方房间求射线到墙距离；1e-9只避免除零，不模拟真实噪声/遮挡。"),
            ("msg.ranges.append", "按角度从angle_min递增的相同顺序追加米制距离；数组长度与angle_increment/angle_max约定一致。"),
        ],
        "security": [
            ("own_services =", "为本实验角色生成服务内部通道匹配范围；通配规则需按目标RMW实际名称展开核对，不能无条件沿用到其他机器人。"),
            (".text = 'DENY'", "未由allow_rule明确授权的行为默认拒绝；签名后的权限文件才会被DDS安全插件采信。"),
        ],
        "eco-nav2-task-programming": [
            ("args.timeout <=", "当前代码仅检查timeout>0；真实部署还应拒绝NaN/Inf等非有限浮点值，并为激活等待设置独立上限。"),
            ("math.sin(yaw /", "将yaw(rad)的一半代入sin设置四元数z分量；配对的cos给w，平面旋转x/y保持0。"),
        ],
    }
    for token, note in domain.get(chapter, []):
        if token in s:
            return note
    if s.startswith("def "):
        name = s[4:].split("(")[0]
        functions = {
            "main": "程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。",
            "generate_launch_description": "launch 系统调用此工厂获取动作描述；函数本身不是节点的执行回调，参数替换可延后求值。",
            "encode_speed": "输入 speed_m_s 为 m/s；先缩放、取整并检查int16范围，输出两个小端字节。",
            "decode_status": "输入恰为3字节；输出 (速度m/s, 教学协议温度整数)，不是某厂商报文的通用解码器。",
            "pose": "输入 values=(x米,y米,yaw弧度)，输出带map坐标和当前ROS时刻的PoseStamped。",
            "select_output": "输入 speed 与纳秒时间戳，输出原速度或0；age==timeout仍接受，负年龄/超时/缺失或NaN返回0。",
            "accepted_target": "输入now/received_at为同一单调时基的非负秒值，请求/限速为m/s；先验证所有数值有限、timeout/限速为正，再拒绝缺失、未来或过期时间，最后限幅（默认±0.2m/s）。返回0仅是离线拒绝值。",
            "gate": "输入6关节位置(rad)、上一目标(rad)、年龄(s)、dt(s)和速率上限(rad/s)；返回位置列表或陈旧数据标记None。",
            "rollout": "按seed建立独立随机初值，以0.05s步长积分给定增益/质量的教学模型，返回累计收益与终态绝对位置误差。",
            "evaluate": "对给定seed集合复用相同增益评估；seed集合必须非空，留出种子和质量改变用于检查过拟合。",
            "manifest": "只读扫描真实数据目录，输出按路径排序的文件条目；大小单位为字节，遇软链接按本示例策略拒绝。",
            "acquire": "单进程内检查离散资源归属；同一所有者重复请求可成功，不同机器人不能同时持有同一资源。",
            "release": "只允许当前所有者释放资源；此字典没有分布式锁、租约或进程崩溃恢复功能。",
            "percentile": ("非空样本的nearest-rank分位数：索引ceil(q×N)-1；与GPU教学数组中的线性插值定义不同。" if chapter == "performance" else "分位数输入需非空，q在[0,1]；本例使用线性插值，不能与另一段nearest-rank实现混为同一统计定义。"),
            "validate": "先校验类型、字段集合与数值边界，再返回计划/参数验证结果；通过校验不表示环境或动作执行一定成功。",
            "on_response": "这是响应完成回调；结果读取仍需异常处理，不在此回调再次同步spin等待同一执行器。",
        }
        if name in functions:
            return functions[name]
    return None


def cpp_note(line: str, chapter: str) -> str | None:
    s = line.strip()
    rules = [
        (r"rclcpp::init\(", "初始化进程 ROS 上下文、解析 ROS 参数；必须先于 Node 和通信对象创建。"),
        (r"rclcpp::shutdown\(", "关闭当前上下文，让执行器退出；确保异步回调不再访问已销毁对象，不能替代业务层故障处理。"),
        (r"spin_until_future_complete\(", "分发回调直到Future完成、给定chrono期限到达或中断；只适用于此处一次性main流程，不能嵌套spin已被执行器持有的同一节点。"),
        (r"rclcpp::spin\(", "持有节点并进入默认单线程执行器，回调在这里得到执行；返回后才能按退出顺序关闭上下文。"),
        (r"create_publisher", "创建指定模板消息类型和话题的发布端；整数10是KeepLast历史条数，不是频率。发布者必须作为成员或其他长寿命对象保留。"),
        (r"create_subscription", "将消息类型、话题、QoS和回调绑定，保存订阅句柄；回调运行线程由执行器/回调组决定，不由lambda写法决定。"),
        (r"create_wall_timer", "创建墙钟/稳态周期定时器，chrono时长明确单位；回调由执行器调度，不随/clock仿真时钟暂停而自然暂停。"),
        (r"create_service", "创建AddTwoInts服务并持有服务句柄；回调填入本次Response，在响应返回前应完成短计算而不长期阻塞执行器。"),
        (r"create_client", "建立请求接口类型与服务名的客户端；创建成功不等于服务端已发现，仍需wait_for_service。"),
        (r"wait_for_service", "等待服务发现，chrono时长限定本地等待期限；返回false走失败分支，不把发现成功当作响应成功。"),
        (r"async_send_request", "异步发送请求并返回Future或注册完成回调；执行器必须继续推进，超时仅影响本地等待，不撤销远端副作用。"),
        (r"create_server<", "创建动作服务端并分别注册目标接纳、取消、已接受目标处理；三个阶段构成状态机而非一次同步服务。"),
        (r"GoalResponse::REJECT", "拒绝忙碌或target超出1..20的目标；拒绝后不能继续把该目标当作已接受任务执行。"),
        (r"ACCEPT_AND_EXECUTE", "确认目标被接受并可进入执行；本例先置busy防止另一个目标同时占用单任务状态。"),
        (r"CancelResponse::ACCEPT", "同意进入取消流程；最终还必须由任务循环检查is_canceling并设置canceled终态。"),
        (r"is_canceling\(", "在短执行步之间检查取消；需要继续spin以接收取消请求，不能靠接受请求自动打断长阻塞调用。"),
        (r"publish_feedback\(", "发布无量纲进度current，不结束任务；对象仅描述本步反馈，不表示任务最终成功。"),
        (r"->canceled\(", "把目标置为CANCELED并附上已完成步数；随后释放活动目标，不能再将其succeed。"),
        (r"->succeed\(", "只有计数达到目标才进入SUCCEEDED并返回Result；此后释放目标句柄并恢复接纳状态。"),
        (r"active_\.reset\(", "释放本节点持有的活动目标引用；必须先写入终态，reset本身不会替代动作协议的成功/取消通知。"),
        (r"busy_\s*=", "更新本例单任务占用标记；当前默认单线程串行访问，换多线程/可重入组后需额外同步。"),
        (r"declare_parameter", "声明参数类型与默认值，并取得启动覆盖值；gain是无量纲double，仍须检查有限性与[0,2]范围。"),
        (r"add_on_set_parameters_callback", "保存动态参数验证回调句柄；句柄销毁会移除注册。验证器只返回是否接受，不做不可回滚的业务修改。"),
        (r"get_parameter\(", "读取已提交参数并按声明类型取值；enabled选择是否输出，gain决定教学值的无量纲比例。"),
        (r"std::isfinite", "拒绝NaN和正负无穷，再检查闭区间[0,2]；只比较大小不足以构成完整的数值输入验证。"),
        (r"MultiThreadedExecutor", "多线程执行器提供工作线程；两个线程不保证默认互斥回调组并行，不能因此忽略共享对象生命周期和锁。"),
        (r"SingleThreadedExecutor", "单线程执行器一次执行一个回调；长时间阻塞会同时延迟本节点的其他事件。"),
        (r"executor\.add_node", "将已创建且尚未被其他执行器持有的节点加入执行器；执行器随后才可调度它的回调。"),
        (r"executor\.spin", "进入事件循环，直到上下文关闭/取消；此调用阻塞，不会自动执行写在它后面的清理代码。"),
        (r"RCLCPP_COMPONENTS_REGISTER_NODE", "导出可被class_loader发现的组件工厂；还需CMake注册/安装，组件NodeOptions构造与容器共同管理生命周期。"),
        (r"NodeOptions", "组件从容器接收NodeOptions，包括参数覆盖和进程内通信配置；不能将其当作已经启动的节点。"),
        (r"std::bind", "将this与成员回调绑定，_1映射到收到的消息；this捕获不延长节点寿命，需保证回调不会在析构后运行。"),
        (r"response->sum\s*=", "对本例小整数相加并写入Response；AddTwoInts字段为有符号64位数，生产输入还需独立处理溢出。"),
        (r"future\.get\(|result\.get\(", "只在Future已完成时读取响应；get可能抛出异常，不能把其视为无错误、无阻塞的任意时刻查询。"),
        (r"->publish\(", "提交当前消息给发布端；日志/返回不提供订阅者业务处理确认，端到端行为还取决于QoS、网络和对端执行器。"),
        (r"RCLCPP_(?:INFO|ERROR|WARN)", "记录当前状态/错误供实验核对；printf格式必须匹配传入类型，日志不等于对端已收到数据。"),
        (r"SharedPtr|std::shared_ptr", "持久共享句柄维持ROS对象/目标的寿命；智能指针只管理生存期，不自动解决多线程数据竞争。"),
    ]
    for pattern, note in rules:
        if re.search(pattern, s):
            return note
    return None


def shell_note(line: str) -> str:
    """解释当前真正命令、子命令或环境变量；不执行任何终端代码。"""
    s = line.strip()
    try:
        words = shlex.split(s, comments=True)
    except ValueError:
        words = s.split()
    if not words:
        return "此行为当前逻辑命令的组成部分，变量展开与引号沿用原示例。"
    if words[0] in {"source", "."}:
        return "在当前shell加载" + brief(" ".join(words[1:]), 100) + "；它影响本终端的包索引/库路径，另一个终端必须单独加载。"
    if words[0] == "export":
        variable = words[1].split("=")[0] if len(words) > 1 else "环境变量"
        meanings = {
            "ROS_DOMAIN_ID": "Domain ID是无量纲发现域编号；相关端点需一致，它不是认证或网络加密。",
            "RMW_IMPLEMENTATION": "指定本进程使用的通信后端；设置后需重启相关节点/daemon，DDS-Security实验须明确选受支持DDS实现。",
            "ROS_SECURITY_KEYSTORE": "选择本实验密钥库目录；路径应在每个实际运行终端解析正确，私钥不应复制到公共学习包。",
            "ROS_SECURITY_ENABLE": "请求启用对应后端支持的ROS安全机制；只设置变量不代表身份/签名/权限已配齐。",
            "ROS_SECURITY_STRATEGY": "Enforce使缺少安全材料时显式失败；不能用空身份悄悄回退未保护通信来证明实验成功。",
            "ROS_AUTOMATIC_DISCOVERY_RANGE": "限制自动发现范围；LOCALHOST通常只自动发现本机，对端还需按所用RMW配置静态发现。",
            "ROS_STATIC_PEERS": "配置静态对端地址；示例IP必须替换为实际可达学习机，作用和防火墙策略不同。",
            "ROS_LOCALHOST_ONLY": "旧的本机发现限制；需按目标发行版支持情况使用，避免与新的发现范围设置混淆。",
        }
        return f"设置{variable}。" + meanings.get(variable, "仅影响当前终端及其后启动子进程；必须核对实际展开值后再运行依赖命令。")
    if words[0] == "unset":
        return "清除当前终端的指定覆盖变量，避免上一轮实验设置影响本次身份/配置；已运行进程不会因此自动重配。"
    if len(words) >= 3 and words[0] == "ros2":
        family, action = words[1:3]
        operations = {
            ("node", "list"): "列出本发现域中可见节点；节点存在不证明其回调、生命周期或业务状态正常。",
            ("node", "info"): "查询指定节点的发布、订阅、服务和动作端点，由端点证据核对实际接口。",
            ("topic", "list"): "列出可见话题；-t附带类型，不能从名字推断消息结构或物理单位。",
            ("topic", "info"): "查询实际消息类型与发布/订阅端点；--verbose显示QoS等证据，先查类型再选择发送消息结构。",
            ("topic", "type"): "读取指定话题的实际接口类型；同名话题类型冲突不能靠强制发送另一类型修复。",
            ("topic", "echo"): "临时创建订阅者观察消息；--once收到一条后退出，持续模式用Ctrl+C结束，其QoS也须匹配。",
            ("topic", "hz"): "用观察者的到达间隔估算接收频率Hz；它不是发布端硬实时周期或网络全部负载的证明。",
            ("topic", "bw"): "估算此观察端接收的序列化流量；结果受采样、编码、丢包与观察者性能影响。",
            ("topic", "pub"): "按指定接口序列化消息并发布；--once只发一条，--rate单位Hz。Twist线速度m/s、角速度rad/s，不能把不同类型强行互发。",
            ("interface", "show"): "展开消息/服务/Action字段定义；字段类型不自动表达坐标系、单位和语义约定。",
            ("service", "list"): "检查可见服务及其类型；发现服务不代表请求必然在期限内完成。",
            ("service", "type"): "核对指定服务请求/响应接口类型，后续call的YAML字段必须与其一致。",
            ("service", "call"): "发送一次类型匹配的请求并等待响应；无响应要区分未发现、回调阻塞和业务失败，重试可能重复远端副作用。",
            ("action", "list"): "查询可见Action接口，-t附上类型；不要把动作目标接纳与最终完成混作同一状态。",
            ("action", "info"): "查看动作服务/客户端端点，先验证类型与名称再发送目标。",
            ("action", "send_goal"): "发送动作目标，--feedback额外显示中间反馈；收到接纳响应后仍需等待最终结果/取消终态。",
            ("param", "list"): "列出指定节点已声明的参数；节点名需与实际命名空间和重命名后的名称对应。",
            ("param", "get"): "读取当前已提交参数的类型和值；与源文件默认值或launch中预期值分别核对。",
            ("param", "set"): "发起动态参数更新，值必须满足声明类型和验证器范围；检查返回是否成功，不能只看CLI命令已发出。",
            ("param", "dump"): "导出当前生效参数作为实验快照；保存文件并不自动保证下一次节点名匹配或版本兼容。",
            ("pkg", "create"): "在当前目录创建包骨架；--build-type决定ament构建类型，--dependencies只登记依赖，仍需写源码与安装规则。",
            ("pkg", "prefix"): "查询当前叠加环境实际选中的包安装前缀，用于识别overlay覆盖或包未找到。",
            ("pkg", "executables"): "列出已安装可执行入口；源码文件存在不代表入口已按CMake/console_scripts安装。",
            ("lifecycle", "get"): "读取节点当前生命周期状态；后续转换必须从合法前置状态执行。",
            ("lifecycle", "set"): "请求明确状态转换并检查结果；configure、activate等顺序不能跳过，active也不等于全系统就绪。",
            ("lifecycle", "nodes"): "查找支持生命周期服务的节点，普通节点不会因此获得受控启动语义。",
            ("component", "types"): "查询已注册组件插件类型；注册/安装正确后才能由容器装载。",
            ("component", "load"): "把指定包/插件装入已有容器，返回运行时组件ID；同进程共享故障边界，类型名须与注册名相同。",
            ("component", "list"): "列出容器中已加载组件与ID，用于验证实际进程组织，不推导所有回调已经并行。",
            ("component", "unload"): "按先前返回的组件ID卸载并释放对象；先确认没有业务仍依赖该组件的持续输出。",
            ("control", "list_controllers"): "观察控制器是否unconfigured/inactive/active及其类型；加载成功不等于已激活并持有接口。",
            ("control", "list_hardware_components"): "只读查看硬件组件生命周期状态；mock和真实硬件的状态不能混为实机验证。",
            ("control", "list_hardware_interfaces"): "核对硬件导出的state/command接口及占用情况，关节名与类型须与控制器需求一致。",
            ("bag", "record"): "录制指定话题到新目录；先确保消息/TF/QoS完整，-o目录应尚不存在，Ctrl+C后再检查关闭后的元数据。",
            ("bag", "info"): "只读检查bag话题、类型、时长和数量；有文件不代表数据覆盖完整或时钟可比。",
            ("bag", "play"): "重放记录的数据；--clock发布回放时钟，依赖节点需use_sim_time。先停同话题实时发布者，防止双来源混入。",
            ("daemon", "stop"): "停止CLI后台发现缓存，后续查询会按当前环境重建；这不会关闭正在运行的业务节点。",
            ("doctor", "--report"): "输出当前ROS环境和中间件诊断基线，保留版本信息以便复现实验。",
            ("multicast", "receive"): "在接收机监听组播测试数据；只诊断网络通路，不验证ROS接口、发现或QoS。",
            ("multicast", "send"): "在另一台经授权的学习机发送组播测试数据，与receive共同检查网络限制。",
            ("security", "create_keystore"): "仅在独立实验目录创建密钥库和CA材料；不要覆盖既有生产密钥库或把私钥上传。",
            ("security", "create_enclave"): "在指定密钥库为给定enclave生成身份材料；运行时路径与权限签名必须匹配。",
        }
        if (family, action) in operations:
            return operations[(family, action)]
        if family == "run":
            package = action
            executable = words[3] if len(words) > 3 else "指定入口"
            extra = ""
            if package == "tf2_ros":
                extra = " 静态平移为m、roll/pitch/yaw为rad；父/子方向必须与后续查询一致。"
            elif package == "micro_ros_agent":
                extra = " 传输端口/设备和波特率需与MCU固件一致；成功连接不是设备端控制安全证明。"
            elif package == "ros_gz_bridge":
                extra = " 配置明确ROS/Gazebo类型及桥接方向；/clock只应有清楚的主时钟来源。"
            elif package == "rmw_zenoh_cpp":
                extra = " Zenoh路由器独立存活，配置与DDS-Security身份机制分别验证。"
            return f"从已安装包{package}启动{executable}；此进程通常持续运行，另用新终端执行观察命令，Ctrl+C结束。" + extra
        if family == "launch":
            return "解析指定launch描述并启动其动作；key:=value为启动参数覆盖。节点发现、TF、控制器和生命周期就绪仍需另行检查。"
        if family == "trace":
            return "创建指定会话的追踪采集；需预先验证LTTng/权限和实际启用事件，追踪开销与本机采样条件要记录。"
    if "apt" in words or "apt-get" in words:
        if "update" in words:
            return "更新已配置软件源的软件包索引，不等于升级全部软件；该准备步骤需要联网。"
        return "安装本段明确列出的系统/ROS依赖；-y自动接受软件包确认，发行版前缀须与目标环境一致。"
    if "rosdep" in words:
        return "按package.xml解析目标发行版依赖；--ignore-src跳过src已提供包，源码已下载不等于系统依赖已离线备齐。"
    if words[0] == "colcon":
        if len(words) > 1 and words[1] == "build":
            return "从工作空间根按依赖拓扑构建；--packages-select只选指定包，--packages-up-to连同所需上游包，构建后必须source安装环境。"
        return "运行/汇总所选包的测试结果；先完成构建，检查失败和跳过项，不把命令退出或部分通过当作全部运行验证。"
    if words[0] == "git":
        return "取得或核对本段明确的上游来源/分支/提交；分支会移动，记录commit才可追溯，clone本身不会安装依赖或运行示例。"
    if words[0] in {"curl", "wget"}:
        return "从本段URL下载明确文件；curl -f使HTTP错误失败、-L跟随重定向，先核对版本变量及目标路径再安装。"
    if words[0] in {"python3", "python"}:
        return "用当前Python解释器运行指定本地脚本；脚本参数/输出路径按本段约定，ROS脚本还需source与包依赖，标准库实验不连接硬件。"
    if words[0] == "docker":
        return "执行本段容器镜像/进程操作；镜像标签、主机架构、网络和设备映射须核对，镜像可启动不证明ROS发现或硬件实时能力。"
    if words[0] == "xacro":
        return "展开Xacro参数/宏为URDF文本；重定向会写目标文件，展开成功后仍需检查链接、关节、单位和惯性。"
    if words[0] == "check_urdf":
        return "检查展开后的URDF语法和树结构；通过不代表惯性、碰撞、控制配置或实机几何准确。"
    if words[0] == "gz":
        return "启动Gazebo仿真世界；-r使仿真开始推进，仿真物理时间与墙钟的比例由世界配置和运行负载决定。"
    if words[0] in {"candump", "ip", "lsusb", "lsmod"}:
        return "只读观测已配置的设备/接口状态；本段没有替代波特率、驱动和厂商协议配置，也不向电机发送运动指令。"
    if words[0] == "mkdir":
        return "创建本段所需目录；相对路径以当前工作目录为基准，-p只容忍目录已存在，不验证其已有内容是否适合覆盖。"
    if words[0] == "cd":
        return "切换到紧随其后的路径，后续相对文件操作由此解析；目录不存在应停止并修正，不继续在错误目录操作。"
    if words[0] in {"cp", "mv"}:
        return "按本段源/目标路径复制或移动已有文件；先确认目标没有需要保留的不同版本，复制源码不等于完成编译安装。"
    if words[0] in {"cat", "head", "file", "sha256sum", "printenv", "locale", "ls", "find", "which", "uname", "lsb_release", "env"}:
        return "读取当前文件、摘要或环境证据，不改变ROS业务状态；核对实际路径和输出，不把示例占位值当成本机事实。"
    if words[0] in {"printf", "echo"}:
        return "输出本段明确文本；若带>则写入/覆盖目标文件，字符串中的转义和引号必须按原样保留。"
    if words[0] == "exec":
        return "用目标命令替换shell进程而非再包一层，使容器退出信号和退出码传给实际ROS进程。"
    if words[0] == "set":
        return "设置shell失败/未定义变量/管道错误策略；具体选项沿用本脚本，不保证任意子命令错误都会被业务层正确恢复。"
    if words[0] == "test":
        return "先检查本地前提是否成立，失败分支显式退出；不要在源码缺失时继续把空路径当作可运行工程。"
    if words[0] in {"sudo", "chmod"}:
        return "执行本段明确的系统准备操作；目标文件和权限需核对，不能把该步骤的成功当作ROS节点运行验证。"
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", s):
        return "为当前实验保存本行明确的路径/版本变量；使用前检查展开值，后续命令只引用该实验变量，不修改用户HOME等系统变量。"
    return "按本行的实际参数执行本段验证步骤；保持引号和变量引用，检查返回状态后再继续依赖它的下一步。"


def config_note(line: str, language: str, label: str, context: dict | None = None) -> str | None:
    s = line.strip()
    if language == "cmake":
        rules = [
            ("cmake_minimum_required", "声明配置所需最低CMake版本；它不是C++语言标准，也不会自动安装构建工具。"),
            ("project(", "工程名应与package.xml包名一致，PROJECT_NAME供安装和接口生成目标引用。"),
            ("find_package(", "在已source的安装前缀查找此依赖并加载导出配置；REQUIRED使缺失时配置失败，不自动从网络获取依赖。"),
            ("add_executable(", "把本行源码编成命名可执行目标；还需声明依赖和install规则，才能通过ros2 run找到。"),
            ("add_library(", "构建组件共享库而非独立进程；SHARED目标须导出插件并被容器加载。"),
            ("ament_target_dependencies(", "为指定目标连接ROS依赖及其包含目录；与package.xml的声明互补，不能只写其中一处。"),
            ("target_compile_features(", "为此目标明确C++语言特性要求；PUBLIC会传递给依赖该目标的使用者。"),
            ("rosidl_generate_interfaces(", "从本包msg/srv/action生成各语言接口；DEPENDENCIES必须列出引用的外部接口包。"),
            ("ament_export_dependencies(", "把运行期/构建使用者需要的依赖导出，接口包通常需要rosidl_default_runtime。"),
            ("rclcpp_components_register_node", "登记组件库、插件类和可选独立入口；类名须与C++注册宏一致，供运行时class_loader发现。"),
            ("install(TARGETS", "安装已构建目标到ROS约定位置；普通节点运行入口通常放lib/${PROJECT_NAME}，库与组件的安装规则分别核对。"),
            ("install(DIRECTORY", "将launch/config等运行所需目录复制到包share目录；未安装时源码中存在文件也可能无法按包名启动。"),
            ("add_launch_test(", "注册launch集成测试并设置TIMEOUT秒上限；测试还需自行等待实际消息/退出状态。"),
            ("if(BUILD_TESTING)", "只在启用测试的构建中寻找并注册测试依赖，避免把测试工具当作运行期必需。"),
            ("ament_package()", "完成ament包元数据导出，应在目标、依赖和安装规则之后调用。"),
        ]
        return next((note for token, note in rules if token in s), None)
    if language == "ini":
        if s.startswith("["):
            return "此段名对应setuptools开发安装或普通安装设置；保持与包内入口安装约定一致。"
        if "script_dir" in s or "install_scripts" in s:
            return "把console_scripts入口安装到lib/包名供ros2 run发现；$base由setuptools展开，不是要手工填入的用户HOME。"
        return None
    if language == "yaml":
        key = s.removeprefix("- ").split(":", 1)[0]
        notes = {
            "ros__parameters": "ROS参数文件的固定层级名；其父节点名/通配选择器必须匹配实际启动名称。",
            "use_sim_time": "布尔开关：true使节点采用ROS仿真时间，必须有正确/clock；false使用正常节点时钟路径。",
            "frequency": "滤波器输出频率，单位Hz；30.0不是传感器一定达到的采样率。",
            "sensor_timeout": "传感器超时时长，单位s；过期测量的处置仍由滤波器逻辑决定。",
            "two_d_mode": "二维运动假设开关；用于地面平面模型，不能照搬到有明显俯仰/垂向运动的系统。",
            "publish_tf": "选择是否由此滤波器广播TF；同一odom→base_link关系只保留一个权威发布者。",
            "world_frame": "决定融合状态在哪个世界坐标系输出；设为odom适于连续局部估计，与map的跳变语义不同。",
            "odom0": "第一路里程计输入的实际话题名；消息类型、参考坐标系、时间和协方差须预先核对。",
            "odom0_config": "固定15维顺序为x,y,z,roll,pitch,yaw,vx,vy,vz,vroll,vpitch,vyaw,ax,ay,az；本例仅索引6(vx)为true。",
            "odom0_differential": "是否把相邻位姿差分为速度；本例直接使用速度测量，false避免再次差分。",
            "odom0_relative": "是否相对首帧位姿解释测量；不等于坐标变换或传感器外参标定。",
            "wheel_separation": "左右轮接地点的有效轮距，单位m；误差会影响偏航里程计，履带滑移不能仅靠几何参数完全消除。",
            "wheel_radius": "有效滚动半径，单位m；与轮角速度rad/s共同决定底盘线速度m/s。",
            "left_wheel_names": "实际URDF/硬件导出的左轮关节名列表；名称必须逐字匹配接口。",
            "right_wheel_names": "实际URDF/硬件导出的右轮关节名列表；左右对应错误会改变运动方向。",
            "open_loop": "false要求从反馈估计里程计；true的命令积分不等于实际轮子已达到该速度。",
            "position_feedback": "true从position反馈求速度/里程计；轮关节位置为rad，硬件接口种类须与此设置一致。",
            "enable_odom_tf": "是否广播里程计TF；与robot_localization等同时使用时避免重复发布同一关系。",
            "cmd_vel_timeout": "速度命令过期阈值，单位s；这是控制器策略，还需设备端独立失联/制动设计。",
            "publish_rate": "状态发布频率，单位Hz；与控制循环频率、命令输入频率分开理解。",
            "linear.x.max_velocity": "底盘前向速度上限，单位m/s；具体控制器版本是否另需启用对应限制开关，应查目标版本配置。",
            "angular.z.max_velocity": "底盘偏航角速度上限，单位rad/s；不要与轮关节速度上限混淆。",
            "resolution": "二维地图栅格分辨率，单位m/cell；越细通常越耗内存和计算，不直接保证定位精度。",
            "map_update_interval": "地图更新间隔，单位s；不是激光扫描周期或控制器周期。",
            "scan_topic": "实际LaserScan输入话题；需要相容QoS、有效Header和可查TF。",
            "ros_topic_name": "桥接后ROS侧话题名；与Gazebo内部话题名是两套命名空间。",
            "gz_topic_name": "Gazebo侧源话题名；桥配置必须与实际世界发布者一致。",
            "ros_type_name": "ROS消息的包/msg/类型路径，不能直接填写Gazebo类型名。",
            "gz_type_name": "Gazebo消息类型名；桥需支持与ROS类型的明确转换。",
            "direction": "GZ_TO_ROS为单向Gazebo→ROS；时钟桥不应形成双向回路或多个互相竞争的主时钟。",
            "depth": "KeepLast历史样本条数，无量纲；不表示采样频率，也不是磁盘保留时长。",
            "reliability": "reliable或best_effort决定可靠传输请求/提供约束，和消息是否已经被业务处理无关。",
            "durability": "transient_local保留存活发布者的有限历史；volatile晚加入者通常只能接收后续样本。",
            "time_from_start": "轨迹起点之后的相对时长：sec秒、nanosec纳秒；点时间必须按执行接口要求递增。",
            "positions": "按joint_names相同顺序填写位置；转动关节rad、移动关节m，此数据片段不代表可直接执行的安全轨迹。",
            "joint_names": "轨迹位置数组的关节顺序契约；不能只检查数组长度而忽略名称对应。",
            "background_r": "turtlesim颜色分量是0..255整数、无量纲；本参数不控制机器人速度。",
            "background_g": "绿色通道0..255、无量纲；参数选择器应匹配重命名后的sim节点。",
            "background_b": "蓝色通道0..255、无量纲；颜色与实际控制接口分别验证。",
            "gain": "无量纲增益，必须是有限浮点数并处于[0,2]；1.0与整数1在参数类型层面不同。",
            "enabled": "布尔开关，决定是否输出教学值；禁用时输出0不等于真实硬件制动。",
            "namespace": "相对节点/话题名称在此命名空间下解析；绝对话题名不会因此自动加前缀。",
            "remap": "启动前重映射名称；只改变连接名称，不转换消息类型、单位或坐标系。",
            "node": "创建节点启动动作；pkg/exec/name等为前端语法，不是任意ROS参数。",
        }
        if key in notes:
            return notes[key]
        if key.endswith("frame") or key.endswith("frame_id"):
            return "坐标系名称必须与TF树及消息Header一致；名称配置不自动生成所需TF或完成外参标定。"
        return None
    if language == "xml":
        if "<joint " in s and (context or {}).get("insideRos2Control"):
            return "这里引用URDF中已经存在的同名关节，并声明控制器可用的state/command接口；不在ros2_control标签内定义父子link或运动学关节。"
        rules = [
            ("<package ", "ROS包清单说明依赖和构建类型；包名、安装目录和实际源码工程需一致，不会自行编译/安装。"),
            ("<buildtool_depend>", "构建工具依赖，用于选择ament构建流程；不同于运行时消息/客户端库依赖。"),
            ("<depend>", "同时声明本包对该ROS依赖的构建/运行需要；CMake目标仍须显式连接对应依赖。"),
            ("<exec_depend>", "声明安装后运行所需依赖，确保发布二进制包时能够解析；不会在打开XML时自动安装。"),
            ("<member_of_group>", "接口包声明所属rosidl_interface_packages组，配合接口生成与导出配置。"),
            ("<node ", "声明待启动节点的包、可执行入口和名称；属性可分多行，启动动作顺序不是应用就绪屏障。"),
            ("<arg ", "声明launch参数及默认值；使用时通过$(var ...)引用，外部可按参数名覆盖。"),
            ("<remap ", "重映射ROS名称，不改变消息类型、物理单位或坐标系。"),
            ("<param ", "为节点设置参数值或参数文件；类型、最终节点名和覆盖顺序需核对。"),
            ("<robot ", "URDF机器人根元素；此最小模型用于显示，不能由此推断已配齐惯性、控制器和真实硬件。"),
            ("<joint ", "定义父/子link间关节；fixed表示固定安装关系，不从joint_states读取自由度。"),
            ("<parent ", "声明此关节的父link；整个URDF应形成无环树，不能让同一子link有多个父关系。"),
            ("<child ", "声明关节的子link；其位姿由父link及origin/关节变量共同确定。"),
            ("<origin ", "xyz平移单位m，rpy旋转单位rad；这是相对父元素的姿态，不是世界坐标的任意标注。"),
            ("<geometry>", "几何尺寸采用m；visual用于显示、collision用于碰撞，二者不能替代inertial动力学参数。"),
            ("<collision>", "声明碰撞几何，仅描述碰撞检查形状；实际接触材质/动力学仍由仿真配置决定。"),
            ("<xacro:property ", "定义Xacro宏参数供后续表达式替换；必须声明xmlns:xacro并先展开，再作为URDF读取。"),
            ("<max_step_size>", "仿真最大积分步长，单位s；0.001s=1ms，不等于所有ROS回调以1kHz实时运行。"),
            ("<real_time_factor>", "仿真时间/墙钟时间的目标比例，无量纲；1.0只是目标，实际值受计算资源影响。"),
            ("<plugin ", "加载本行指定插件实现；名称/库必须与目标Gazebo版本相容，源码标签存在不代表插件已安装。"),
            ("<ros2_control ", "描述供controller_manager使用的硬件与关节接口；它不是完整机器人URDF或自动启动控制循环的脚本。"),
            ("<hardware>", "选择硬件组件插件；mock_components/GenericSystem只模拟状态，不连接电机/读取真实编码器。"),
            ("<command_interface ", "声明可被控制器占用的命令接口；轮关节velocity单位rad/s，与底盘Twist线速度m/s不同。"),
            ("<state_interface ", "声明只读反馈接口；转动关节position为rad、velocity为rad/s，需由硬件read步骤正确填充。"),
        ]
        return next((note for token, note in rules if token in s), None)
    return None


def message_note(line: str, label: str, section: int) -> str | None:
    s = line.strip()
    if s == "---":
        return "分隔请求与响应。" if label.endswith(".srv") else "分隔目标/结果/反馈三个部分，顺序是Action接口协议的一部分。"
    if "Header header" in s:
        return "采样时间以sec/nanosec表示，frame_id声明本测量坐标约定；接收方不能只看速度数值而忽略时间与坐标。"
    if "velocity_rad_s" in s:
        return "轮关节角速度rad/s；正方向按本接口约定，不是底盘线速度m/s。"
    if s.startswith("bool valid"):
        return "显式标注测量是否有效；false时接收方不能把默认0速度当作可信停车反馈。"
    if s.startswith("float64 gain"):
        return "无量纲缩放系数；接口类型自身不约束有限性或范围，业务层需验证NaN/Inf等输入。"
    if s.startswith("float64 value"):
        return "待缩放输入；物理单位由业务约定，scaled与value应保持相同单位。"
    if s.startswith("float64 scaled"):
        return "响应scaled=value×gain；需明确错误、溢出或非有限输入的业务策略。"
    if s.startswith("uint32 target"):
        return "目标计数，无量纲uint32；本章服务端额外限制1..20，字段类型本身不表达该业务范围。"
    if s.startswith("uint32 completed"):
        return "最终结果中的已完成步数，无量纲；取消或失败时可能小于目标。"
    if s.startswith("uint32 current"):
        return "中间反馈计数，无量纲；反馈不是最终状态，客户端还需检查结果终态。"
    return None


def effective_language(language: str, label: str, code: str) -> str:
    if language != "text":
        return language
    if label.endswith((".msg", ".srv", ".action")):
        return "ros-interface"
    if "CMakeLists" in label or "ament_cmake" in label:
        return "cmake"
    if "Dockerfile" in label:
        return "dockerfile"
    return "data"


def shell_quote_state(line: str, state: str | None) -> str | None:
    """跟踪原始shell跨行引号；不能在printf的多行字符串内部插入注释。"""
    escaped = False
    for char in line:
        if escaped:
            escaped = False
            continue
        if char == "\\" and state != "'":
            escaped = True
        elif state:
            if char == state:
                state = None
        elif char in {"'", '"'}:
            state = char
        elif char == "#":
            break
    return state


def annotate(code: str, language: str, label: str, chapter: str, explanation: str) -> tuple[str, str]:
    """生成合法注释；不改原始代码的任何非注释字符。"""
    mode = effective_language(language, label, code)
    header = context_lines(chapter, label, explanation, mode, code)
    detail = explanation.strip()
    context_detail = [line for line in header if line.startswith(("输入输出：", "执行顺序与边界："))]
    detail += ("\n\n" if detail else "") + "\n".join(context_detail)
    if mode in {"data", "json", "csv"}:
        if "csv" in label.lower():
            detail += "\n数据字段：seq为无量纲序号；send_ns/start_ns/end_ns为同一时基下的纳秒时间戳，必须send≤start≤end。合成样本不能视为实际测速。"
        elif "动作" in label or "rclpy.action" in label or "rclcpp_action" in label:
            detail += "\nAPI顺序：创建端点→接纳目标→执行并发反馈→成功/取消/失败终态→获取结果。目标响应Future和最终结果Future分别处理；取消还需服务端主动协作。此表是API索引，不可直接作为源文件执行。"
        else:
            detail += "\n这是概念/数据表达，保留原文以避免插入非法语法；请结合正文解释，不能直接当成完整可执行工程。"
        return code, detail
    lines = code.splitlines()
    output = []
    start = 0
    if mode == "xml":
        if lines and lines[0].lstrip().startswith("<?xml"):
            output.append(lines[0]); start = 1
        output.extend("<!-- " + comment.replace("--", "—") + " -->" for comment in header)
    else:
        prefix = "// " if mode == "cpp" else "# "
        # 保持shell/Python shebang和编码声明优先位置；SPDX亦保留在原有文件开头。
        while start < len(lines) and (lines[start].startswith("#!") or "coding:" in lines[start] or "SPDX-License-Identifier" in lines[start]):
            output.append(lines[start]); start += 1
        output.extend(prefix + comment for comment in header)
    protected = protected_python_lines(code) if mode == "python" else set()
    continuation, xml_open, shell_quote, xml_in_control = False, False, None, False
    seen_notes = set()
    for index in range(start, len(lines)):
        line = lines[index]
        stripped = line.strip()
        indent = line[:len(line) - len(line.lstrip())]
        note = None
        if mode == "xml" and re.search(r"<ros2_control(?:\s|>)", line):
            xml_in_control = True
        if stripped and not stripped.startswith(("#", "//", "<!--")):
            if mode == "python" and index + 1 not in protected:
                note = python_note(line, chapter)
            elif mode == "cpp":
                note = cpp_note(line, chapter)
            elif mode == "bash" and not continuation and shell_quote is None:
                note = shell_note(line)
            elif mode in {"cmake", "ini", "yaml"}:
                note = config_note(line, mode, label)
            elif mode == "ros-interface":
                note = message_note(line, label, 0)
            elif mode == "xml" and not xml_open:
                note = config_note(line, mode, label, {"insideRos2Control": xml_in_control})
            elif mode == "dockerfile" and not continuation:
                first = stripped.split()[0]
                note = {
                    "ARG": "声明构建时可覆盖的镜像参数；为复现应记录实际镜像摘要，标签本身可移动。",
                    "FROM": "选择目标ROS/Jazzy基础镜像及架构；基础镜像不包含所有应用依赖。",
                    "SHELL": "后续RUN使用bash并启用pipefail；只是构建shell策略，不是运行时节点执行器。",
                    "WORKDIR": "建立后续COPY/RUN的工作目录，所有相对路径在此解析。",
                    "COPY": "仅复制构建上下文内本行指定文件；源码、安装产物和运行数据的职责分别核对。",
                    "RUN": "构建阶段准备依赖并编译，&&保证前一步成功才继续；反斜杠连接属于同一逻辑指令，不能插入破坏续行的内容。",
                    "ENTRYPOINT": "运行时入口负责source安装环境并exec目标程序，让退出信号/退出码传给ROS进程。",
                    "CMD": "提供默认运行命令，可由docker run参数替换；镜像构建成功并不等于此节点已通过运行验证。",
                }.get(first)
        # 同一完整块/文件内，一个API规则解释一次即可；不同单位、参数或异步边界
        # 使用不同文本，仍保留在各自首次出现的位置，不按API名字粗暴合并。
        if note and note not in seen_notes:
            seen_notes.add(note)
            if mode == "xml":
                output.append(indent + "<!-- " + note.replace("--", "—") + " -->")
            else:
                output.append(indent + ("// " if mode == "cpp" else "# ") + note)
        output.append(line)
        if mode in {"bash", "dockerfile"}:
            if stripped and not stripped.startswith("#"):
                continuation = line.rstrip().endswith("\\")
            if mode == "bash":
                shell_quote = shell_quote_state(line, shell_quote)
        if mode == "xml" and not stripped.startswith("<!--"):
            # 属性跨行时不能把注释插进尚未结束的开始标签中。
            opens, closes = line.count("<"), line.count(">")
            if opens > closes:
                xml_open = True
            elif closes > opens:
                xml_open = False
            if "</ros2_control>" in line:
                xml_in_control = False
    result = "\n".join(output)
    if code.endswith("\n"):
        result += "\n"
    return result, detail


def semantic_cpp_tokens(code: str) -> list[str]:
    """跳过注释/空白，保留字符串和全部C++词法字符，检查没有改动代码语义字符。"""
    pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/|[^\s]'
    return [match.group() for match in re.finditer(pattern, code)
            if not match.group().startswith(("//", "/*"))]


def validate_pair(original: str, annotated: str, language: str, label: str, statistics: Counter) -> None:
    """只做不会启动进程业务的静态验证；片段按原始可解析性处理。"""
    mode = effective_language(language, label, original)
    if mode == "python":
        try:
            before = ast.parse(original)
        except SyntaxError:
            statistics["pythonFragments"] += 1
            # 局部片段不能靠补缩进/补导入伪装完整文件；依旧保证去注释token不变。
            return
        after = ast.parse(annotated)
        assert ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False), label
        compile(annotated, label, "exec")  # 仅编译字节码对象，不执行模块顶层语句。
        statistics["pythonAstEquivalent"] += 1
    elif mode == "cpp":
        assert semantic_cpp_tokens(original) == semantic_cpp_tokens(annotated), label
        statistics["cppTokensEquivalent"] += 1
    elif mode == "bash":
        assert shlex.split(original, comments=True) == shlex.split(annotated, comments=True), label
        result = subprocess.run(["bash", "-n"], input=annotated, text=True, capture_output=True)
        assert result.returncode == 0, (label, result.stderr)
        statistics["bashSyntaxAndTokensEquivalent"] += 1
    elif mode == "xml":
        try:
            before = ET.fromstring(original)
        except ET.ParseError:
            statistics["xmlFragments"] += 1
            return
        after = ET.fromstring(annotated)
        for tree in (before, after):
            for element in tree.iter():
                if element.text is not None and not element.text.strip():
                    element.text = None
                if element.tail is not None and not element.tail.strip():
                    element.tail = None
        assert ET.tostring(before) == ET.tostring(after), label
        statistics["xmlStructureEquivalent"] += 1
    elif mode == "yaml":
        import yaml
        assert yaml.safe_load(original) == yaml.safe_load(annotated), label
        statistics["yamlStructureEquivalent"] += 1
    elif mode == "ini":
        before, after = configparser.ConfigParser(interpolation=None), configparser.ConfigParser(interpolation=None)
        before.read_string(original); after.read_string(annotated)
        assert dict(before) == dict(after), label
        statistics["iniStructureEquivalent"] += 1
    elif mode in {"data", "json", "csv"}:
        assert original == annotated, label
        statistics["dataUnchanged"] += 1
    else:
        # CMake、ROS接口和Dockerfile都是逐行新增合法#注释，非注释行保持完全一致。
        def uncommented(text):
            return [line for line in text.splitlines() if not line.lstrip().startswith("#")]
        assert uncommented(original) == uncommented(annotated), label
        statistics[mode + "NoncommentLinesEquivalent"] += 1


def annotation_patch(code: str, language: str, label: str, chapter: str, explanation: str, statistics: Counter) -> dict:
    corrected = code
    correction = None
    if chapter == "eco-network-security" and "export ROS_SECURITY_KEYSTORE" in code:
        corrected = ("# 退出上一段Zenoh应用；先确认已安装所选DDS后端，再重启本段节点。\n"
                     "export RMW_IMPLEMENTATION=rmw_fastrtps_cpp\n"
                     "ros2 daemon stop\n" + code)
        correction = "修复后端混用：SROS2/DDS-Security实验前显式切回Fast DDS并重启发现daemon；此前Zenoh路由/会话的安全性需按Zenoh配置单独验证。"
        statistics["explicitSemanticCorrections"] += 1
    if chapter == "eco-microcontrollers" and "def accepted_target(" in code:
        # 审查确认的真实缺陷：NaN与min/max组合可能漏检并生成正限速值。
        # 修正实现由单独可运行文件提供，保证正文代码与实际边界测试用的是同一逻辑。
        corrected = (HUB / "examples/offline_labs/watchdog_model.py").read_text()
        correction = "修复看门狗非有限输入漏检：now/received_at/requested/timeout/velocity_limit先做数值类型与有限性验证，拒绝负时间、非正阈值、缺失/未来/过期戳；合法输入仍按默认±0.2m/s限幅。0只表示模型拒绝，不证明硬件已停车。"
        explanation = ("完整标准库离线看门狗文件，包含正常限幅、NaN/Inf、未来戳及严格超时边界断言。"
                       "本轮实际运行对应实验及tests/test_watchdog_model.py；未连接ROS、MCU或硬件。"
                       "可选velocity_limit采用m/s，timeout采用s，两个上限必须为有限正数。")
        statistics["explicitSemanticCorrections"] += 1
        statistics["watchdogFiniteInputCorrections"] += 1
    annotated, detail = annotate(corrected, language, label, chapter, explanation)
    validate_pair(corrected, annotated, language, label, statistics)
    statistics["annotatedPositions"] += 1
    patch = {"code": annotated, "explanation": detail,
             "originalSha256": hashlib.sha256(code.encode()).hexdigest()}
    if correction:
        patch["semanticCorrection"] = correction
        patch["explanation"] += "\n" + correction
    return patch


COMPARE_CHAPTER = {
    "compare-publisher": "pubsub", "compare-callback": "pubsub", "compare-service": "services",
    "compare-actions": "actions", "compare-params": "parameters", "compare-launch": "launch",
    "compare-executor": "executors", "compare-composition": "composition", "compare-build": "workspace",
    "compare-qos": "qos", "compare-velocity": "eco-diff-drive-tracks", "compare-description": "eco-model-rviz",
}
COMPARE_NOTES = {
    "compare-publisher": "队列10是历史深度（条），不是10Hz。C++ create_wall_timer按墙钟/稳态时长，rclpy create_timer默认用节点时钟；use_sim_time启用后两者计时行为不必等价，均需要执行器调度。",
    "compare-callback": "lambda捕获this和绑定成员方法都不延长节点寿命，也不自动提供线程安全；Python绑定方法持有self的引用，但仍须显式销毁ROS资源。",
    "compare-service": "两者Future都是异步完成对象，执行器须持续运行；响应回调需要处理异常、超时和请求并发上限，超时不会自动撤销远端副作用。",
    "compare-actions": "目标接纳、反馈、取消响应、最终结果是不同阶段；最终CANCELED由服务端协作设置，不能把cancel请求已发送当成任务已停。",
    "compare-params": "CLI值推断、YAML原生类型、launch显式值需与声明类型一致；参数选择器匹配实际节点名，后续覆盖顺序和动态校验也需要核对。",
    "compare-launch": "三种写法建立相同节点/名称映射的意图；Python可编程性和前端替换能力并非完全等价，动作顺序不表示应用已就绪。",
    "compare-executor": "线程数只是可用工作线程数；默认互斥回调组可能仍串行，Python GIL限制CPU密集回调并行，不能仅换执行器就解决死锁或数据竞争。",
    "compare-composition": "组件共享进程地址空间和故障边界；进程内通信需显式选项与相容类型，容器名称/组件ID是运行时证据而非永久固定值。",
    "compare-build": "两种包仍共同依赖package.xml、依赖解析、安装规则和source环境；CMake目标与Python console_scripts入口必须与ros2 run使用的名称一致。",
    "compare-qos": "SensorDataQoS与Python预设强调相同策略意图，具体默认字段仍应按所用版本核对；BestEffort不能满足Reliable请求，深度不是频率。",
    "compare-velocity": "Twist和TwistStamped是不同接口契约；线速度m/s、角速度rad/s，增加header不会自动校准时钟或转换坐标，零速度消息也不能替代设备端急停验收。",
    "compare-description": "xyz使用m，rpy使用rad；Xacro只做建模文本生成，展开成功仍需检查TF树、碰撞与惯性，不将宏参数化当成运动学或物理验证。",
}


def file_chapter(path: Path) -> str:
    """只用于原创atlas/foundation文件，按包/目录的实际教学任务确定上下文。"""
    text = path.as_posix()
    if "learning_count_interfaces" in text or "/actions/" in text or "learning_action_cpp" in text:
        return "actions"
    if "learning_interfaces" in text or "/interfaces/" in text:
        return "interfaces"
    if "learning_bringup" in text or "/launch/" in text or "/config/" in text:
        return "launch"
    if "learning_params" in text or "/parameters/" in text:
        return "parameters"
    if "learning_service" in text or "/services/" in text or "add_client" in text or "add_server" in text:
        return "services"
    if "learning_topic" in text or "/atlas_" in text:
        return "pubsub"
    return "workspace"


def update_original_examples(statistics: Counter, previous_files: dict) -> list[dict]:
    """为随包下载的原创工程加相同注释；绝不遍历references或第三方仓库。"""
    changed = []
    roots = [HUB / "examples" / "src", HUB / "foundation-examples"]
    languages = {".py": "python", ".cpp": "cpp", ".hpp": "cpp", ".h": "cpp", ".xml": "xml",
                 ".yaml": "yaml", ".cfg": "ini", ".msg": "text", ".srv": "text", ".action": "text"}
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name == "__init__.py" or any(part in {"__pycache__", "build", "install", "log"} for part in path.parts):
                continue
            language = "cmake" if path.name == "CMakeLists.txt" else languages.get(path.suffix)
            if language is None:
                continue
            code = path.read_text()
            if not code.strip():
                continue
            chapter = file_chapter(path)
            label = path.relative_to(HUB).as_posix()
            detail = "随离线教材保存的原创教学文件；" + CONTEXT[chapter][0]
            baseline = code
            record = previous_files.get(label, {})
            original_revision = record.get("originalRevision")
            if MARKER in code:
                # 不按字符串猜测并删除作者原注释。仅从经beforeSha验证的原始Git文件
                # 重新生成本工具的教学注释，再检查与当前文件非注释语义完全一致。
                if not record:
                    raise ValueError(f"已有教学注释但缺少原文件摘要，拒绝猜测重写：{label}")
                git_path = path.relative_to(HUB.parent).as_posix()
                if not original_revision:
                    original_revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HUB.parent,
                                                       capture_output=True, text=True, check=True, timeout=20).stdout.strip()
                original = subprocess.run(["git", "show", original_revision + ":" + git_path], cwd=HUB.parent,
                                          capture_output=True, check=True, timeout=20)
                if hashlib.sha256(original.stdout).hexdigest() != record["beforeSha256"]:
                    raise ValueError(f"Git原文件与已记录beforeSha不一致，拒绝覆盖：{label}")
                baseline = original.stdout.decode("utf-8")
            annotated, _ = annotate(baseline, language, label, chapter, detail)
            # 每次重跑均校验全部64文件，让统计和产物都具有幂等性。
            validate_pair(baseline, annotated, language, label, statistics)
            validate_pair(code, annotated, language, label, Counter())
            statistics["originalFilesStaticallyChecked"] += 1
            if annotated == code and original_revision == record.get("originalRevision"):
                continue
            if annotated != code:
                path.write_text(annotated)
            item = {"path": label, "chapter": chapter,
                    "beforeSha256": hashlib.sha256(code.encode()).hexdigest(),
                    "afterSha256": hashlib.sha256(annotated.encode()).hexdigest()}
            if original_revision:
                item["originalRevision"] = original_revision
            changed.append(item)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-files", action="store_true", help="同时给原创atlas/foundation代码文件添加中文注释")
    args = parser.parse_args()
    chapters, comparisons = load_final_originals()
    overlay, statistics = {"chapters": {}, "comparisons": {}}, Counter()
    for identifier, chapter in chapters.items():
        chapter_patch = {"sections": {}, "steps": {}, "commands": {}}
        for si, section in enumerate(chapter.get("sections", [])):
            for bi, block in enumerate(section.get("codeBlocks", [])):
                chapter_patch["sections"][f"{si}:{bi}"] = annotation_patch(
                    block["code"], block.get("language", "text"), block.get("label", section["title"]), identifier,
                    block.get("explanation", "") or section["title"], statistics)
                statistics["sectionPositions"] += 1
        for index, step in enumerate(chapter.get("steps", [])):
            if isinstance(step, dict) and step.get("code"):
                patch = annotation_patch(step["code"], step.get("language", "bash"), step["title"], identifier,
                                         step.get("body", "") or step["title"], statistics)
                patch["body"] = patch.pop("explanation")
                chapter_patch["steps"][str(index)] = patch
                statistics["stepPositions"] += 1
        for index, block in enumerate(chapter.get("commands", [])):
            chapter_patch["commands"][str(index)] = annotation_patch(
                block["code"], block.get("language", "bash"), block.get("label", chapter["title"]), identifier,
                block.get("explanation", "") or block.get("label", "基础验证命令"), statistics)
            statistics["commandPositions"] += 1
        overlay["chapters"][identifier] = chapter_patch
    for comparison in comparisons:
        identifier = comparison["id"]
        chapter = COMPARE_CHAPTER[identifier]
        patch = {"variants": {}, "notes": list(comparison["notes"]) + [COMPARE_NOTES[identifier]]}
        for index, variant in enumerate(comparison["variants"]):
            item = annotation_patch(variant["code"], variant["language"], variant["label"], chapter,
                                    variant.get("scope", ""), statistics)
            item["scope"] = item.pop("explanation") + "\n" + COMPARE_NOTES[identifier]
            patch["variants"][str(index)] = item
            statistics["comparisonPositions"] += 1
        overlay["comparisons"][identifier] = patch
    target = SOURCE / "code-annotations.json"
    previous_files = {}
    if target.exists():
        previous_files = {item["path"]: item for item in json.loads(target.read_text()).get("meta", {}).get("updatedOriginalFiles", [])}
    changed = update_original_examples(statistics, previous_files) if args.update_files else []
    for item in changed:
        if item["path"] in previous_files:
            item["beforeSha256"] = previous_files[item["path"]]["beforeSha256"]
        previous_files[item["path"]] = item
    # 331个位置是现有44章+12组写法对照，不包括新增16章，也不代表331个独立工程。
    assert statistics["annotatedPositions"] == 331, statistics
    overlay["meta"] = {"schemaVersion": 1, "scope": "原有44章全部代码位置及12组对照；不包含新增16章或第三方源码",
                       "checkedAt": "2026-11-07", "statistics": dict(statistics),
                       "annotationPolicy": "注释说明真实API、参数、单位、输入输出、顺序与生命周期；除semanticCorrections明示修复外，不改变原始非注释代码。",
                       "validationScope": "Python AST/编译、Bash语法和词法、XML/YAML/INI解析等价、C++词法等价；未运行ROS或硬件。",
                       "updatedOriginalFiles": list(previous_files.values()),
                       "apiTimeSemantics": "rclcpp create_wall_timer使用墙钟/稳态计时；rclpy create_timer默认用节点时钟，use_sim_time下两者不保证相同。",
                       "formatPolicy": "CSV/JSON/普通示意文本保留原数据，在explanation/scope补充说明；XML注释置于声明之后。"}
    overlay["meta"]["repetitionPolicy"] = "同一代码块/完整文件内完全相同的教学API说明仅保留首次；不同参数、单位、生命周期或异步边界说明分别保留。头注释不重复用途与输入输出。"
    overlay["meta"]["semanticCorrections"] = [
        {"id": "dds-security-backend-transition", "chapter": "eco-network-security", "location": "sections:4:1",
         "description": "SROS2实验前切回Fast DDS并重启CLI daemon，避免沿用Zenoh后端解释DDS-Security。",
         "runtimeValidation": "只做Bash语法与明确命令顺序检查；未运行ROS安全实验。"},
        {"id": "watchdog-finite-input-validation", "chapter": "eco-microcontrollers", "location": "sections:5:0",
         "description": "非有限数、非法时间、无效上限均先拒绝，随后检查新鲜性，合法速度保持对称限幅。",
         "implementation": "examples/offline_labs/watchdog_model.py", "tests": "tests/test_watchdog_model.py",
         "validationCommands": ["python3 tests/test_watchdog_model.py", "python3 examples/offline_labs/watchdog_model.py"],
         "runtimeValidation": "纯标准库离线模型；不是设备端执行、制动或停车保证。"},
    ]
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(target)
    print(json.dumps({"statistics": dict(statistics), "updatedOriginalFiles": len(changed),
                      "outputBytes": (SOURCE / "code-annotations.json").stat().st_size}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
