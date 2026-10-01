# -*- coding: utf-8 -*-
"""吉祥物组件系统落地脚本：
1. 9 个模块首页插入 rt-chapter-header
2. 实验室 README / 路线图页插入 rt-mascot-tip（替换旧吉祥物卡）
3. 8 个筑基章末尾追加 rt-complete
4. 文案换名：小樱丸 → 紫樱
5. 内容层 IP 名称清扫（原神/雷电将军/八重神子/稻妻/神瞳/七天神像/提瓦特 → 原创或中性表述）
每处替换断言命中次数，防止误伤。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGED = []


def patch(path: str, replacements, expect_each=1):
    """replacements: list of (old, new) 或 (old, new, count)；幂等：已应用则跳过"""
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    applied = False
    for item in replacements:
        old, new = item[0], item[1]
        want = item[2] if len(item) > 2 else expect_each
        got = text.count(old)
        if got == 0 and new in text:
            continue  # 已应用，幂等跳过
        assert got == want, f"{path}: 「{old[:40]}…」期望 {want} 处，实际 {got} 处"
        text = text.replace(old, new)
        applied = True
    if applied:
        p.write_text(text, encoding="utf-8")
        CHANGED.append(path)


def insert_after_h1(path: str, block: str):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if "rt-chapter-header" in text:
        print(f"  = {path}: 已有章节头，跳过")
        return
    lines = text.splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            # H1 后插入（保持一个空行分隔）
            if i + 1 < len(lines) and lines[i + 1].strip():
                lines.insert(i + 1, "\n")
            lines.insert(i + 1, block.rstrip("\n") + "\n\n")
            p.write_text("".join(lines), encoding="utf-8")
            CHANGED.append(path)
            return
    raise AssertionError(f"{path}: 未找到 H1")


def append_block(path: str, block: str, marker: str = "rt-complete"):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if marker in text:
        print(f"  = {path}: 已有完成卡，跳过")
        return
    if not text.endswith("\n"):
        text += "\n"
    text += "\n" + block.rstrip("\n") + "\n"
    p.write_text(text, encoding="utf-8")
    CHANGED.append(path)


# ============================================================
# 1. rt-chapter-header（9 个模块首页，H1 之后）
# ============================================================

def chapter_header(code: str, tagline: str, chips: list) -> str:
    chip_html = "".join(f"<span>◆ {c}</span>" for c in chips)
    return (
        '<div class="rt-chapter-header">\n'
        '<div class="rt-chapter-header__top">\n'
        f'<span class="rt-chapter-header__code">{code}</span>\n'
        f'<span class="rt-chapter-header__tagline">{tagline}</span>\n'
        "</div>\n"
        '<div class="rt-chapter-header__meta">\n'
        f"{chip_html}\n"
        "</div>\n"
        "</div>"
    )


insert_after_h1(
    "00_项目导航/从零开始学习路线总图.md",
    chapter_header("ROUTE MAP · 全站总览", "从零到前沿的四阶段学习路线",
                   ["四阶段阶梯", "8 大方向", "每章学时与毕业自测"]),
)
insert_after_h1(
    "01_数学/数学方向_学习路径与教材映射.md",
    chapter_header("MODULE 01 · 数学", "从零起步到研究生的完整阶梯",
                   ["筑基 7 章", "配套实验 ×7", "教材映射：同济 · 浙大 · Boyd"]),
)
insert_after_h1(
    "02_C++基础与进阶/C++方向_学习路径与教材映射.md",
    chapter_header("MODULE 02 · C++ 与编程", "从第一行代码到工程化开发",
                   ["入门起步", "Python 工具链", "通往 ROS2 工程"]),
)
insert_after_h1(
    "07_机器人学导论/00_机器人学导论_学习地图.md",
    chapter_header("MODULE 07 · 机器人学导论", "把数学与代码第一次真正用在机器人上",
                   ["坐标变换", "正运动学", "ROS2 初体验", "配套实验 ×2"]),
)
insert_after_h1(
    "03_SLAM/SLAM方向_学习路径与教材映射.md",
    chapter_header("MODULE 03 · SLAM", "从零理解定位与建图",
                   ["十四讲路线", "概率机器人", "配套实验 ×1"]),
)
insert_after_h1(
    "04_移动机器人规控/移动规控方向_学习路径与教材映射.md",
    chapter_header("MODULE 04 · 移动机器人规控", "从时空规划到采样 MPC 与博弈",
                   ["采样式 MPC 深水区", "时空联合规划", "配套实验 ×1"]),
)
insert_after_h1(
    "05_运动控制/运动控制方向_学习路径与教材映射.md",
    chapter_header("MODULE 05 · 运动控制", "足式、机械臂与实时控制工程",
                   ["足式与机械臂", "仿真与实机", "配套实验 ×2"]),
)
insert_after_h1(
    "06_具身智能/具身智能方向_学习路径与教材映射.md",
    chapter_header("MODULE 06 · 具身智能", "从 RL 运控到 Isaac Lab 全链路",
                   ["RL 运控 28 章", "Isaac Lab", "配套实验 ×1"]),
)
insert_after_h1(
    "08_可视化实验室/README.md",
    chapter_header("VIS LAB · 可视化实验室", "每条公式都能亲手运行、亲手修改",
                   ["11 个实验", "纯 numpy 可复现", "固定种子出图"]),
)

# ============================================================
# 2. rt-mascot-tip：实验室 README 旧卡替换 + 路线图页新增
# ============================================================

patch(
    "08_可视化实验室/README.md",
    [
        # 旧身份行 → 紫樱
        ("> **樱雷工程狐 · 小樱丸 的实验室**——理论书上每一条公式，在这里都变成一段你能亲手运行、亲手修改的代码和一张你能看懂的图。",
         "> **紫樱的可视化实验室**——理论书上每一条公式，在这里都变成一段你能亲手运行、亲手修改的代码和一张你能看懂的图。"),
        # 旧吉祥物独立图片 + 守则段 → rt-mascot-tip 组件
        ("![樱雷工程狐·小樱丸](../assets/images/mascot.svg)\n\n"
         "**小樱丸**：实验守则只有三条——抄一遍再跑、每次只改一个参数、看到意外的形状别慌，意外就是理解的开端。",
         '<div class="rt-mascot-tip" markdown>\n\n'
         "![紫樱](../assets/images/mascot.svg)\n\n"
         "**紫樱的实验守则**只有三条——抄一遍再跑、每次只改一个参数、看到意外的形状别慌，"
         "意外就是理解的开端。\n\n"
         "</div>"),
        ("## 使用守则（小樱丸的三条叮嘱）", "## 使用守则（紫樱的三条叮嘱）"),
    ],
)

# 路线图页：在第一个 --- 前插入紫樱路线建议（幂等）
p = ROOT / "00_项目导航/从零开始学习路线总图.md"
text = p.read_text(encoding="utf-8")
if "rt-mascot-tip" in text:
    print("  = 00_项目导航/从零开始学习路线总图.md: 已有提示卡，跳过")
else:
    tip_block = (
        '<div class="rt-mascot-tip" markdown>\n\n'
        "![紫樱](../assets/images/mascot.svg)\n\n"
        '**紫樱的路线建议**：别在第一页找「最优路径」。先用「一句话路线」定位自己所在的阶段，'
        "直接跳进对应章节；缺什么回筑基补什么——自学的正确姿势是按需补课，而不是从第一页抄到最后一页。\n\n"
        "</div>\n\n"
    )
    anchor = "\n---\n"
    idx = text.find(anchor)
    assert idx > 0, "路线图页未找到第一个 ---"
    text = text[:idx] + "\n" + tip_block + text[idx + 1:]
    p.write_text(text, encoding="utf-8")
    CHANGED.append("00_项目导航/从零开始学习路线总图.md")

# ============================================================
# 3. rt-complete：8 个筑基章末尾
# ============================================================

COMPLETES = [
    ("01_数学/00_大学基础筑基/10_微积分I_极限与一元微分.md",
     "极限与一元微分",
     "[20 · 微积分 II](./20_微积分II_积分_级数与多元入门.md)",
     "[lab01 · 微积分实验室](../../08_可视化实验室/lab01_微积分实验室.md)"),
    ("01_数学/00_大学基础筑基/20_微积分II_积分_级数与多元入门.md",
     "积分、级数与多元入门",
     "[30 · 线性代数 I](./30_线性代数I_矩阵与线性方程组.md)",
     "[lab01 · 微积分实验室](../../08_可视化实验室/lab01_微积分实验室.md)"),
    ("01_数学/00_大学基础筑基/30_线性代数I_矩阵与线性方程组.md",
     "矩阵与线性方程组",
     "[40 · 线性代数 II](./40_线性代数II_特征值_二次型与正定性.md)",
     "[lab02 · 线性代数实验室](../../08_可视化实验室/lab02_线性代数实验室.md)"),
    ("01_数学/00_大学基础筑基/40_线性代数II_特征值_二次型与正定性.md",
     "特征值、二次型与正定性",
     "[50 · 概率与统计基础](./50_概率与统计基础.md)",
     "[lab02 · 线性代数实验室](../../08_可视化实验室/lab02_线性代数实验室.md)"),
    ("01_数学/00_大学基础筑基/50_概率与统计基础.md",
     "概率与统计基础",
     "[60 · 数值方法与复变速成](./60_数值方法与复变速成.md)",
     "[lab03 · 概率与滤波实验室](../../08_可视化实验室/lab03_概率与滤波实验室.md)"),
    ("01_数学/00_大学基础筑基/60_数值方法与复变速成.md",
     "数值方法与复数",
     "[00 · C++ 入门学习地图](../../02_C++基础与进阶/00_入门/00_C++学习地图与环境搭建.md)",
     "[lab04 · 数值方法实验室](../../08_可视化实验室/lab04_数值方法实验室.md)"),
    ("07_机器人学导论/20_空间描述与坐标变换.md",
     "空间描述与坐标变换",
     "[30 · 机械臂正运动学入门](./30_机械臂正运动学入门.md)",
     "[lab09 · 坐标变换实验室](../08_可视化实验室/lab09_坐标变换实验室.md)"),
    ("07_机器人学导论/30_机械臂正运动学入门.md",
     "机械臂正运动学入门",
     "[40 · ROS2 初体验](./40_ROS2初体验_小海龟仿真.md)",
     "[lab06 · 运动学实验室](../08_可视化实验室/lab06_运动学实验室.md)"),
]

for path, label, nxt, lab in COMPLETES:
    append_block(
        path,
        '<div class="rt-complete" markdown>\n\n'
        f'<p class="rt-complete__title"><span class="rt-complete__badge">✓</span>本章完成 · {label}</p>\n\n'
        f'<p class="rt-complete__body">下一站：{nxt} ｜ 动手验证：{lab}</p>\n\n'
        "</div>",
    )

# ============================================================
# 4. 文案换名：小樱丸 → 紫樱（实验室三章备注）
# ============================================================

patch("08_可视化实验室/lab02_线性代数实验室.md",
      [("> 小樱丸备注：", "> 紫樱备注：")])
patch("08_可视化实验室/lab07_规划实验室.md",
      [("> 小樱丸备注：", "> 紫樱备注：")])
patch("08_可视化实验室/lab10_卡尔曼滤波实验室.md",
      [("> 小樱丸备注：", "> 紫樱备注：")])

# ============================================================
# 5. 内容层 IP 清扫 → 已拆分至 apply_ip_sweep.py
# ============================================================

print(f"完成：{len(CHANGED)} 个文件")
for c in CHANGED:
    print("  ✔", c)
