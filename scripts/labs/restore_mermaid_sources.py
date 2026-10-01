#!/usr/bin/env python3
"""恢复被 render_mermaid 替换掉的 mermaid 源码块（把图片引用换回 ```mermaid 块）。

源码从开发记录精确恢复；恢复后重跑 render_mermaid.py 重新渲染。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

INIT = ('%%{init: {"theme":"base","themeVariables":'
        '{"primaryColor":"#f0e8ff","primaryBorderColor":"#7c4dff",'
        '"primaryTextColor":"#3a2b57","lineColor":"#7c4dff","fontSize":"14px"}}}%%')

LAB_INIT = INIT  # 同一头


def block(body: str) -> str:
    return f"```mermaid\n{INIT}\n{body}```"


BASE0 = ("⛩ 第〇阶 · 入门筑基（从这里开始，全部在本站）<br>"
         "数学筑基 7 章 · C++ 入门 7 章 · Python 工具链 2 章 · 机器人学导论 5 章")


def ladder(s0, s1, s2, s3):
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


RECOVER = {
    "08_可视化实验室/README.md": block(
        'flowchart LR\n'
        '    A(["读理论章节"]) --> B[/"抄跑实验代码"/]\n'
        '    B --> C{"图和预期<br>一致吗？"}\n'
        '    C -- 是 --> D["改参数再跑"]\n'
        '    C -- 否 --> E["回到理论章节<br>查那一节"]\n'
        '    D --> F(["写出你自己的版本"])\n'
        '    E --> B\n'),
    "08_可视化实验室/lab01_微积分实验室.md": block(
        'flowchart TD\n'
        '    A(["选定函数 f"]) --> B[/"在 x₀ 处取割线，缩小 h"/]\n'
        '    B --> C{"割线斜率 → 什么值？"}\n'
        '    C -- "h → 0" --> D["切线 = 导数 f\'(x₀)"]\n'
        '    D --> E[/"用多项式逐阶逼近 f：泰勒"/]\n'
        '    E --> F[/"沿负梯度迭代：梯度下降"/]\n'
        '    F --> G(["观察：小球滚向谷底"])\n'),
    "08_可视化实验室/lab02_线性代数实验室.md": block(
        'flowchart TD\n'
        '    A(["取单位方格与基向量 e₁ e₂"]) --> B[/"左乘矩阵 M"/]\n'
        '    B --> C{"变换后哪些方向<br>没被掰弯？"}\n'
        '    C -- "方向不变" --> D["那是不动方向 = 特征向量<br>缩放倍数 = 特征值 λ"]\n'
        '    C -- "方向被掰弯" --> E["普通方向：长度与角度都变"]\n'
        '    D --> F(["椭圆主轴 = 特征向量方向"])\n'),
    "08_可视化实验室/lab03_概率与滤波实验室.md": block(
        'flowchart TD\n'
        '    A(["机器人在 1D 走廊，位置未知"]) --> B[/"撒 700 个粒子：假设位置"/]\n'
        '    B --> C["机器人走一步<br>粒子们也跟着走一步+抖动"]\n'
        '    C --> D["读一次距离传感器 z<br>离观测越近的粒子权重越高"]\n'
        '    D --> E{"全部重采样"}\n'
        '    E --> F["粒子云收拢到真值附近"]\n'
        '    F -- "循环每一步" --> C\n'),
    "08_可视化实验室/lab04_数值方法实验室.md": block(
        'flowchart TD\n'
        '    A(["要解 f x = 0"]) --> B[/"从初值 x₀ 出发"/]\n'
        '    B --> C["作切线，滑到 x 轴<br>得到更好的 x₁"]\n'
        '    C --> D{"|f x₁| 够小吗？"}\n'
        '    D -- "否" --> C\n'
        '    D -- "是" --> E(["收敛：得到近似根"])\n'
        '    F(["要算定积分"]) --> G[/"切成 n 个梯形求和"/]\n'
        '    G --> H{"n 翻倍，误差够小吗？"}\n'
        '    H -- "否" --> G\n'
        '    H -- "是" --> I(["得到积分近似值"])\n'),
    "08_可视化实验室/lab05_控制实验室.md": block(
        'flowchart LR\n'
        '    r(["目标 r"]) --> s(("Σ<br>e=r−y"))\n'
        '    s -->|"误差 e"| C["控制器<br>PID / LQR"]\n'
        '    C -->|"控制量 u"| P["被控对象<br>（小车/电机）"]\n'
        '    P -->|"实际输出 y"| s\n'
        '    P --> y2(["位置 y"])\n'
        '    style s fill:#ffe9f1,stroke:#e75480\n'),
    "08_可视化实验室/lab06_运动学实验室.md": block(
        'flowchart LR\n'
        '    A[/"输入：关节角 θ₁ θ₂"/] --> B["正运动学 FK<br>x = l₁cosθ₁ + l₂cos(θ₁+θ₂)"]\n'
        '    B --> C{"θ 扫遍所有取值"}\n'
        '    C --> D[/"输出：末端点云 =<br>工作空间（甜甜圈）"/]\n'
        '    D --> E(["逆运动学的舞台就绪<br>——目标点必须落在甜甜圈里"])\n'),
    "08_可视化实验室/lab07_规划实验室.md": block(
        'flowchart TD\n'
        '    A(["起点入开放列表"]) --> B[/"取出 f = g + h 最小的节点"/]\n'
        '    B --> C{"是终点吗？"}\n'
        '    C -- "是" --> Z(["回溯得到最短路径"])\n'
        '    C -- "否" --> D[/"把四邻中可行走且更优的<br>节点入列表（记下父节点）"/]\n'
        '    D --> B\n'
        '    E[/"障碍：永远不入列"/] -.-> D\n'),
    "08_可视化实验室/lab08_强化学习实验室.md": block(
        'flowchart TD\n'
        '    A(["初始化 Q 表 = 全 0"]) --> B[/"观察当前状态 s"/]\n'
        '    B --> C{"ε-贪婪：探索 or 利用？"}\n'
        '    C -- "概率 ε：探索" --> D["随机选动作 a"]\n'
        '    C -- "概率 1−ε：利用" --> E["选 Q 最大的动作 a"]\n'
        '    D --> F["执行 a → 得奖励 r 与新状态 s\']"]\n'
        '    E --> F\n'
        '    F --> G[/"更新：Q(s,a) ← Q(s,a) + α(r + γ·maxQ(s\') − Q(s,a))"/]\n'
        '    G --> H{"到终点了？"}\n'
        '    H -- "否" --> B\n'
        '    H -- "是" --> I(["下一回合；ε 逐渐减小"])\n'),
    "00_项目导航/从零开始学习路线总图.md": None,  # 三个子图块，单独处理
    "01_数学/数学方向_学习路径与教材映射.md": ladder(
        "⛩ 第〇阶 · 入门筑基（从这里开始）<br>"
        "微积分 I/II · 线代 I/II · 概率统计 · 数值方法<br>"
        "教材：同济《高数》《线代》· 浙大《概率》· 李庆扬《数值分析》",
        "⚡ 第一阶 · 本科核心<br>常微分方程 · 多元微积分深入 · 线代加深<br>"
        "教材：同济《高数》下册 · 王高雄《常微分方程》",
        "❖ 第二阶 · 研究生进阶<br>凸优化 · 状态估计 · 微分几何<br>"
        "教材：Boyd《凸优化》· Barfoot · do Carmo",
        "✦ 第三阶 · 前沿/博士<br>10_纯数学基础 ~ 95_随机分析 共 10 个子方向<br>教材：专题专著 + 论文",
    ),
    "02_C++基础与进阶/C++方向_学习路径与教材映射.md": ladder(
        "⛩ 第〇阶 · 入门筑基（从这里开始）<br>"
        "00_入门 7 章 + 15_Python与工具链 2 章<br>教材：《C++ Primer 第5版》",
        "⚡ 第一阶 · 本科核心（语言功底）<br>现代类设计 · RAII · 移动语义 · STL 深入<br>"
        "教材：《Effective C++》· 《STL源码剖析》",
        "❖ 第二阶 · 进阶工程<br>并发编程 · 模板进阶 · CMake 工程<br>"
        "教材：《C++ Concurrency in Action》· 《C++ Templates》",
        "✦ 第三阶 · 前沿/专家：工程化深耕<br>"
        "40_通用库剖析 · 50_ROS2工程化 · 60_规控公共工程基础<br>教材：官方文档与源码为主",
    ),
    "03_SLAM/SLAM方向_学习路径与教材映射.md": ladder(
        "⛩ 第〇阶 · 入门筑基（跨方向拼图）<br>"
        "机器人学导论 5 章 + 数学筑基 + C++ 入门<br>"
        "教材：同济《高数》《线代》· 浙大《概率》· 《C++ Primer》",
        "⚡ 第一阶 · 本科核心<br>视觉 SLAM 框架全貌 + 动手复现<br>教材：高翔《视觉SLAM十四讲》第2版",
        "❖ 第二阶 · 研究生进阶<br>概率机器人 · 状态估计 · SLAM 库<br>"
        "教材：Thrun《概率机器人》· Barfoot · GTSAM/g2o 文档",
        "✦ 第三阶 · 前沿/博士：系统精读与综合项目<br>"
        "30_系统精读（入门级 → 前沿）· 40_综合项目 Mini-LIO<br>教材：经典系统论文 + 开源源码",
    ),
    "04_移动机器人规控/移动规控方向_学习路径与教材映射.md": ladder(
        BASE0,
        "⚡ 第一阶 · 本科核心：控制入门 + 车辆规控入门<br>"
        "胡寿松《自动控制原理》第七版 · 龚建伟《无人驾驶车辆模型预测控制》第2版",
        "❖ 第二阶 · 研究生进阶：教材 + 经典专著<br>"
        "LaValle《Planning Algorithms》· Boyd《凸优化》· Thrun《概率机器人》相关章",
        "✦ 第三阶 · 前沿/博士：本站子方向深潜 + 论文<br>"
        "10_时空规划 · 20_采样式MPC · 30_不确定性规划 · 40_博弈规划<br>"
        "50_多机器人协作 · 60_任务运动规划 · 70_无人机 · 80_综述",
    ),
    "05_运动控制/运动控制方向_学习路径与教材映射.md": ladder(
        BASE0,
        "⚡ 第一阶 · 本科核心：控制入门 + 机器人动力学入门<br>"
        "胡寿松《自动控制原理》第七版 · Craig《机器人学导论》",
        "❖ 第二阶 · 研究生进阶：教材 + 经典专著<br>"
        "郑大钟《线性系统理论》· Lynch 与 Park《Modern Robotics》· Siciliano · Featherstone",
        "✦ 第三阶 · 前沿/博士：本站子方向深潜 + 论文<br>"
        "10_足式 WBC/OCS2/Perceptive MPC · 20_机械臂 力控/双臂/MoveIt2<br>"
        "30_复合 轮足/人形/LocoManipulation · 40_仿真 MuJoCo/可微仿真",
    ),
    "06_具身智能/具身智能方向_学习路径与教材映射.md": ladder(
        BASE0.replace("C++ 入门 7 章", "C++ 入门 7 章（重点概率统计）"),
        "⚡ 第一阶 · 本科核心：强化学习入门 + 机器学习选学<br>"
        "Sutton 与 Barto《强化学习》第2版（免费在线）· 周志华《机器学习》选学",
        "❖ 第二阶 · 研究生进阶：深度学习 + RL 实战课<br>"
        "Goodfellow《Deep Learning》（花书，免费在线）· OpenAI Spinning Up（免费）",
        "✦ 第三阶 · 前沿/博士：本站 RL运控 28 章 + 前沿综述<br>"
        "RL运控 Ch01-Ch28（Isaac Lab/mjlab 全链路）· 05_运动控制/40_仿真",
    ),
}

ROADMAP_BLOCKS = [
    block(
        'flowchart TD\n'
        '    subgraph M["数学线 · 预计 3-4 个月"]\n'
        '        direction LR\n'
        '        M0["00 学习地图"] --> M1["10 微积分 I"] --> M2["20 微积分 II"] --> M7["60 数值方法与复变"]\n'
        '        M0 --> M3["30 线代 I"] --> M4["40 线代 II"] --> M5["50 概率与统计"]\n'
        '    end\n'),
    block(
        'flowchart TD\n'
        '    subgraph P["编程线 · 预计 3 个月"]\n'
        '        direction LR\n'
        '        P0["00 环境搭建"] --> P1["10 程序与类型"] --> P2["20 控制流"] --> P3["30 容器"] --> P4["40 指针内存"] --> P5["50 类与对象"] --> P6["60 STL 项目"]\n'
        '        P6 --> PY1["Python 与 NumPy"] --> PY2["Linux 与 Git"]\n'
        '    end\n'),
    block(
        'flowchart TD\n'
        '    subgraph R["通识线 · 建议与编程线并行 · 预计 1 个月"]\n'
        '        direction LR\n'
        '        R0["00 学习地图"] --> R1["10 什么是机器人"] --> R2["20 坐标变换"] --> R3["30 正运动学"] --> R4["40 ROS2 初体验"]\n'
        '    end\n'),
]


def restore(rel: str, mermaid_block: str) -> None:
    p = ROOT / rel
    text = p.read_text(encoding="utf-8")
    if "```mermaid" in text:
        print(f"跳过（已是 mermaid 源码）: {rel}")
        return
    lines = text.splitlines(keepends=True)
    out = []
    i = 0
    count = 0
    while i < len(lines):
        line = lines[i]
        if "![图示]" in line and "labs/diagrams" in line:
            if rel.endswith("从零开始学习路线总图.md"):
                out.append(ROADMAP_BLOCKS[count] if count < len(ROADMAP_BLOCKS) else line)
                count += 1
            else:
                out.append(mermaid_block)
            i += 1
        else:
            out.append(line)
            i += 1
    p.write_text("".join(out), encoding="utf-8")
    print(f"已恢复: {rel}（{count} 块）")


for rel, blk in RECOVER.items():
    restore(rel, blk)
print("恢复完成。")
