# -*- coding: utf-8 -*-
"""导论 4 章的 ASCII 示意图 → mermaid / matplotlib 图 / markdown 表。

按「文件中第 N 个含 ≥3 行盒绘字符的代码块」定位替换；幂等：marker 已在文中则跳过。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = re.compile(r"[┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣]")
INIT = ('%%{init: {"theme":"base","themeVariables":{"primaryColor":"#FFFFFF",'
        '"primaryBorderColor":"#8166B1","primaryTextColor":"#292530",'
        '"lineColor":"#8166B1","fontSize":"14px"}}}%%')

CHANGED = []


def find_blocks(lines):
    blocks = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            if j < len(lines):
                body = lines[i + 1:j]
                if sum(1 for l in body if BOX.search(l)) >= 3:
                    blocks.append((i, j))
            i = j + 1
        else:
            i += 1
    return blocks


def replace_block(path: str, index: int, new_text: str, marker: str):
    p = ROOT / path
    full = p.read_text(encoding="utf-8")
    if marker in full:
        print(f"  = {path}#{index} 已应用（marker 命中），跳过")
        return
    lines = full.splitlines()
    blocks = find_blocks(lines)
    assert index < len(blocks), f"{path}: 只有 {len(blocks)} 个块，找不到第 {index} 个"
    s, e = blocks[index]
    lines[s:e + 1] = new_text.splitlines()
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    CHANGED.append(f"{path}#{index}")


def MM(body: str) -> str:
    return f"```mermaid\n{INIT}\n{body}\n```"


P = "07_机器人学导论/"

# 00 学习地图（两块均已在早前步骤完成，marker 直接跳过）
replace_block(
    P + "00_机器人学导论_学习地图.md", 0,
    MM('flowchart TD\n    Z["占位-已应用"]'),
    marker="diag_00_机器人学导论_学习地图",
)
replace_block(
    P + "00_机器人学导论_学习地图.md", 0,
    MM('flowchart LR\n    Z["占位-已应用"]'),
    marker="diag_00_机器人学导论_学习地图",
)

# 10 什么是机器人
replace_block(
    P + "10_什么是机器人_组成分类与发展.md", 0,
    MM('''flowchart LR
    S(["① 感知 · 传感器<br/>相机 / 雷达 / IMU / 编码器"]) -- "原始数据" --> E["② 状态估计<br/>我在哪？"]
    E -- "位姿 / 地图" --> P2["③ 决策规划<br/>该怎么走？"]
    P2 -- "轨迹" --> C["④ 控制<br/>怎么跟上"]
    C -- "力矩 / 转速" --> A(["执行器<br/>电机 / 液压 / 舵机"])
    A -. "⑤ 闭环反馈：机器人真的动了，世界变了，重新感知（物理世界）" .-> S'''),
    marker="感知 · 传感器",
)
replace_block(
    P + "10_什么是机器人_组成分类与发展.md", 1,
    """| 层 | 硬件部件（至少 3 个） | 行为举例（至少 3 条） |
|---|---|---|
| 感知 | ？ | 碰到墙了？桌子底下是黑的？ |
| 决策 | ？ | 下一步往哪走？该回充了吗？ |
| 执行 | ？ | 左右轮差速转弯、滚刷吸尘 |""",
    marker="| 感知 | ？ |",
)

# 20 空间描述：右手坐标系
replace_block(
    P + "20_空间描述与坐标变换.md", 0,
    "![右手坐标系](../assets/labs/intro_right_hand.svg)",
    marker="intro_right_hand.svg",
)

# 30 机械臂：D-H / 2R 几何 / 工作空间（倒序防索引漂移）
replace_block(
    P + "30_机械臂正运动学入门.md", 2,
    """![2R 机械臂工作空间圆环](../assets/labs/lab06_workspace.svg)

外半径 $R = l_1 + l_2$（伸直可达），内半径 $r = |l_1 - l_2|$（对折够不着）：圆环里每一处末端都能到，中间的"洞"与圆环之外到不了。想亲手扫描这个甜甜圈：[lab06 · 运动学实验室](../08_可视化实验室/lab06_运动学实验室.md)。""",
    marker="lab06_workspace.svg",
)
replace_block(
    P + "30_机械臂正运动学入门.md", 1,
    "![平面 2R 机械臂几何](../assets/labs/intro_2r_geometry.svg)",
    marker="intro_2r_geometry.svg",
)
replace_block(
    P + "30_机械臂正运动学入门.md", 0,
    "![D-H 参数几何](../assets/labs/intro_dh_params.svg)",
    marker="intro_dh_params.svg",
)

# 40 ROS2：发布/订阅
replace_block(
    P + "40_ROS2初体验_小海龟仿真.md", 0,
    MM('''flowchart LR
    PUB["发布者 Publisher<br/>turtle_teleop_key<br/>（键盘遥控节点）"] -- "话题 /turtle1/cmd_vel<br/>消息 Twist：线速度 + 角速度" --> SUB["订阅者 Subscriber<br/>turtlesim_node<br/>（小海龟仿真器）"]
    DDS["ROS2 / DDS 负责递送与发现<br/>谁在发、谁在收都不重要"] -.- PUB
    DDS -.- SUB'''),
    marker="ROS2 / DDS",
)

print(f"替换完成：{len(CHANGED)} 处")
for c in CHANGED:
    print("  ✔", c)
