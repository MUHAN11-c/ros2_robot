#!/usr/bin/env python3
"""把 6 个方向映射文档的第一个 fenced 块（ASCII 阶梯）替换为 mermaid 阶梯图。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INIT = ('%%{init: {"theme":"base","themeVariables":'
        '{"primaryColor":"#f0e8ff","primaryBorderColor":"#7c4dff",'
        '"primaryTextColor":"#3a2b57","lineColor":"#7c4dff","fontSize":"14px"}}}%%')


def mermaid(s0, s1, s2, s3):
    return (
        "```mermaid\n" + INIT + "\n"
        "flowchart BT\n"
        f'    S0["{s0}"] --> S1["{s1}"] --> S2["{s2}"] --> S3["{s3}"]\n'
        '    style S0 fill:#ffe9f1,stroke:#e75480\n'
        '    style S1 fill:#f0e8ff,stroke:#7c4dff\n'
        '    style S2 fill:#f3ecff,stroke:#8a5cf6\n'
        '    style S3 fill:#fff7e6,stroke:#e3b341\n'
        "```\n"
    )


BASE0 = ("⛩ 第〇阶 · 零基础筑基（从这里开始，全部在本站）<br>"
         "数学筑基 7 章 · C++ 零基础 7 章 · Python 工具链 2 章 · 机器人学导论 5 章")

DOCS = {
    "01_数学/数学方向_学习路径与教材映射.md": mermaid(
        "⛩ 第〇阶 · 零基础筑基（从这里开始）<br>"
        "微积分 I/II · 线代 I/II · 概率统计 · 数值方法<br>"
        "教材：同济《高数》《线代》· 浙大《概率》· 李庆扬《数值分析》",
        "⚡ 第一阶 · 本科核心<br>常微分方程 · 多元微积分深入 · 线代加深<br>"
        "教材：同济《高数》下册 · 王高雄《常微分方程》",
        "❖ 第二阶 · 研究生进阶<br>凸优化 · 状态估计 · 微分几何<br>"
        "教材：Boyd《凸优化》· Barfoot · do Carmo",
        "✦ 第三阶 · 前沿/博士<br>10_纯数学基础 ~ 95_随机分析 共 10 个子方向<br>"
        "教材：专题专著 + 论文",
    ),
    "02_C++基础与进阶/C++方向_学习路径与教材映射.md": mermaid(
        "⛩ 第〇阶 · 零基础筑基（从这里开始）<br>"
        "00_零基础入门 7 章 + 15_Python与工具链 2 章<br>教材：《C++ Primer 第5版》",
        "⚡ 第一阶 · 本科核心（语言功底）<br>现代类设计 · RAII · 移动语义 · STL 深入<br>"
        "教材：《Effective C++》· 《STL源码剖析》",
        "❖ 第二阶 · 进阶工程<br>并发编程 · 模板进阶 · CMake 工程<br>"
        "教材：《C++ Concurrency in Action》· 《C++ Templates》",
        "✦ 第三阶 · 前沿/专家：工程化深耕<br>"
        "40_通用库剖析 · 50_ROS2工程化 · 60_规控公共工程基础<br>教材：官方文档与源码为主",
    ),
    "03_SLAM/SLAM方向_学习路径与教材映射.md": mermaid(
        "⛩ 第〇阶 · 零基础筑基（跨方向拼图）<br>"
        "机器人学导论 5 章 + 数学筑基 + C++ 零基础<br>"
        "教材：同济《高数》《线代》· 浙大《概率》· 《C++ Primer》",
        "⚡ 第一阶 · 本科核心<br>视觉 SLAM 框架全貌 + 动手复现<br>"
        "教材：高翔《视觉SLAM十四讲》第2版",
        "❖ 第二阶 · 研究生进阶<br>概率机器人 · 状态估计 · SLAM 库<br>"
        "教材：Thrun《概率机器人》· Barfoot · GTSAM/g2o 文档",
        "✦ 第三阶 · 前沿/博士：系统精读与综合项目<br>"
        "30_系统精读（入门级 → 前沿）· 40_综合项目 Mini-LIO<br>教材：经典系统论文 + 开源源码",
    ),
    "04_移动机器人规控/移动规控方向_学习路径与教材映射.md": mermaid(
        BASE0,
        "⚡ 第一阶 · 本科核心：控制入门 + 车辆规控入门<br>"
        "胡寿松《自动控制原理》第七版 · 龚建伟《无人驾驶车辆模型预测控制》第2版",
        "❖ 第二阶 · 研究生进阶：教材 + 经典专著<br>"
        "LaValle《Planning Algorithms》· Boyd《凸优化》· Thrun《概率机器人》相关章",
        "✦ 第三阶 · 前沿/博士：本站子方向深潜 + 论文<br>"
        "10_时空规划 · 20_采样式MPC · 30_不确定性规划 · 40_博弈规划<br>"
        "50_多机器人协作 · 60_任务运动规划 · 70_无人机 · 80_综述",
    ),
    "05_运动控制/运动控制方向_学习路径与教材映射.md": mermaid(
        BASE0,
        "⚡ 第一阶 · 本科核心：控制入门 + 机器人动力学入门<br>"
        "胡寿松《自动控制原理》第七版 · Craig《机器人学导论》",
        "❖ 第二阶 · 研究生进阶：教材 + 经典专著<br>"
        "郑大钟《线性系统理论》· Lynch 与 Park《Modern Robotics》· Siciliano · Featherstone",
        "✦ 第三阶 · 前沿/博士：本站子方向深潜 + 论文<br>"
        "10_足式 WBC/OCS2/Perceptive MPC · 20_机械臂 力控/双臂/MoveIt2<br>"
        "30_复合 轮足/人形/LocoManipulation · 40_仿真 MuJoCo/可微仿真",
    ),
    "06_具身智能/具身智能方向_学习路径与教材映射.md": mermaid(
        BASE0.replace("C++ 零基础 7 章", "C++ 零基础 7 章（重点概率统计）"),
        "⚡ 第一阶 · 本科核心：强化学习入门 + 机器学习选学<br>"
        "Sutton 与 Barto《强化学习》第2版（免费在线）· 周志华《机器学习》选学",
        "❖ 第二阶 · 研究生进阶：深度学习 + RL 实战课<br>"
        "Goodfellow《Deep Learning》（花书，免费在线）· OpenAI Spinning Up（免费）",
        "✦ 第三阶 · 前沿/博士：本站 RL运控 28 章 + 前沿综述<br>"
        "RL运控 Ch01-Ch28（Isaac Lab/mjlab 全链路）· 05_运动控制/40_仿真",
    ),
}

for rel, new_block in DOCS.items():
    p = ROOT / rel
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, ln in enumerate(lines) if ln.strip().startswith("```"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("```"))
    replaced = "".join(lines[:start]) + new_block + "".join(lines[end + 1:])
    p.write_text(replaced, encoding="utf-8")
    print(f"已替换 {rel}（原块 {start+1}-{end+1} 行）")

print("完成。")
