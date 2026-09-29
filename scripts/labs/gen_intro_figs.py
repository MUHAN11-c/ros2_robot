#!/usr/bin/env python3
"""生成《机器人学导论》正文几何插图 → assets/labs/intro_*.svg

统一风格与 gen_all.py 一致（品牌色板 / Microsoft YaHei / 白底）。
运行：.venv/Scripts/python scripts/labs/gen_intro_figs.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "labs"
OUT.mkdir(parents=True, exist_ok=True)

SAKURA = "#D98FAF"
VIOLET = "#8166B1"
GOLD = "#C9A96E"
DEEP = "#292530"
TEAL = "#2fb2a8"

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "sans-serif"],
    "axes.unicode_minus": False,
    "figure.dpi": 110,
    "svg.fonttype": "none",
})


def arrow(ax, x0, y0, x1, y1, color=DEEP, lw=2.4, ms=14):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=ms, color=color, lw=lw,
                                 shrinkA=0, shrinkB=0))


def right_hand():
    fig = plt.figure(figsize=(5.6, 4.6))
    ax = fig.add_subplot(projection="3d")
    L = 1.0
    for dx, dy, dz, c, label in [
        (1, 0, 0, DEEP, "x"),
        (0, 1, 0, VIOLET, "y"),
        (0, 0, 1, SAKURA, "z"),
    ]:
        ax.quiver(0, 0, 0, dx * L, dy * L, dz * L, color=c, linewidth=2.6,
                  arrow_length_ratio=0.08)
        ax.text(dx * L * 1.18, dy * L * 1.18, dz * L * 1.18, label,
                color=c, fontsize=15, fontweight="bold")
    ax.scatter([0], [0], [0], color=DEEP, s=36)
    ax.text(0.06, -0.1, 0.02, "原点 O", color=DEEP, fontsize=11)
    ax.view_init(elev=18, azim=-58)
    ax.set_box_aspect([1, 1, 1])
    ax.set_xlim(-0.4, 1.25); ax.set_ylim(-0.4, 1.25); ax.set_zlim(-0.1, 1.25)
    ax.set_axis_off()
    ax.set_title("右手坐标系：四指从 x 弯向 y，大拇指指向 z", fontsize=11, color=DEEP, pad=0)
    fig.tight_layout()
    fig.savefig(OUT / "intro_right_hand.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def dh_params():
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    # 两根 z 轴（竖直）
    for x, top, label in [(1.0, 2.6, "$z_{i-2}$"), (5.4, 2.6, "$z_{i-1}$")]:
        arrow(ax, x, 0.3, x, top, color=VIOLET)
        ax.text(x + 0.08, top, label, color=VIOLET, fontsize=13)
    # 公垂线 a_i
    arrow(ax, 1.0, 1.75, 5.4, 1.75, color=GOLD, lw=3.0)
    ax.text(3.1, 1.9, "公垂线 = $a_i$", color=GOLD, fontsize=12, ha="center")
    # 夹角 α_i（第二根轴倾斜表示）
    arrow(ax, 5.4, 0.3, 6.9, 1.7, color=SAKURA, lw=2.0)
    ax.add_patch(Arc((5.4, 1.75), 2.2, 2.2, angle=0, theta1=-38, theta2=0,
                     color=SAKURA, lw=1.8))
    ax.text(6.5, 1.15, "$\\alpha_i$（两根 z 轴的夹角）", color=SAKURA, fontsize=11)
    # x_i 方向
    arrow(ax, 1.0, 1.75, 2.4, 1.75, color=DEEP)
    ax.text(2.0, 1.45, "$x_i$ 方向", color=DEEP, fontsize=11)
    # 关节
    for x, name in [(1.0, "关节 $i{-}1$"), (5.4, "关节 $i$")]:
        ax.plot([x], [0.35], "o", color=DEEP, ms=9)
        ax.text(x, -0.05, name, color=DEEP, fontsize=11, ha="center")
    # d_i 沿 z_{i-1}
    arrow(ax, 0.55, 0.3, 0.55, 1.75, color=TEAL, lw=2.0)
    ax.text(0.1, 1.0, "$d_i$", color=TEAL, fontsize=12)
    ax.annotate("", xy=(1.0, 0.3), xytext=(0.62, 0.3),
                arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.2))
    ax.text(1.3, 2.15, "$\\theta_i$ 绕 $z_{i-1}$ 转，$d_i$ 沿 $z_{i-1}$ 量",
            color=DEEP, fontsize=11)
    ax.set_xlim(-0.4, 8.2); ax.set_ylim(-0.4, 3.1)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("D-H 参数：相邻两根关节轴之间的四件套（$a_i,\\ \\alpha_i,\\ d_i,\\ \\theta_i$）",
                 fontsize=11, color=DEEP)
    fig.tight_layout()
    fig.savefig(OUT / "intro_dh_params.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def two_r_geometry():
    fig, ax = plt.subplots(figsize=(6.0, 4.6))
    l1, l2 = 2.0, 1.4
    th1, th2 = np.deg2rad(50), np.deg2rad(40)
    elbow = np.array([l1 * np.cos(th1), l1 * np.sin(th1)])
    end = elbow + np.array([l2 * np.cos(th1 + th2), l2 * np.sin(th1 + th2)])
    # 连杆
    ax.plot([0, elbow[0]], [0, elbow[1]], color=VIOLET, lw=4, solid_capstyle="round")
    ax.plot([elbow[0], end[0]], [elbow[1], end[1]], color=SAKURA, lw=4,
            solid_capstyle="round")
    ax.text(elbow[0] / 2 - 0.35, elbow[1] / 2 + 0.12, "$l_1$", color=VIOLET, fontsize=13)
    ax.text(*(elbow + end) / 2 + np.array([0.08, 0.14]), "$l_2$", color=SAKURA, fontsize=13)
    # 关节
    ax.plot(0, 0, "o", color=DEEP, ms=10)
    ax.plot(*elbow, "o", color=DEEP, ms=8)
    ax.plot(*end, "o", color=GOLD, ms=10)
    ax.text(-0.15, -0.42, "基座 · 关节 1", color=DEEP, fontsize=11, ha="center")
    ax.text(elbow[0] + 0.12, elbow[1] - 0.4, "肘关节（关节 2）", color=DEEP, fontsize=11)
    ax.text(end[0] + 0.12, end[1] + 0.1, "末端 $(x,\\ y)$", color=GOLD, fontsize=12)
    # 坐标轴
    arrow(ax, 0, 0, 3.4, 0, color=DEEP, lw=1.6)
    arrow(ax, 0, 0, 0, 2.6, color=DEEP, lw=1.6)
    ax.text(3.5, -0.05, "x", color=DEEP, fontsize=12)
    ax.text(-0.28, 2.62, "y", color=DEEP, fontsize=12)
    # 角度弧
    ax.add_patch(Arc((0, 0), 2.4, 2.4, theta1=0, theta2=np.rad2deg(th1), color=VIOLET, lw=1.8))
    ax.text(1.45, 0.62, "$\\theta_1$", color=VIOLET, fontsize=13)
    ax.add_patch(Arc(tuple(elbow), 1.3, 1.3, angle=np.rad2deg(th1),
                     theta1=0, theta2=np.rad2deg(th2), color=SAKURA, lw=1.8))
    ax.text(elbow[0] + 0.78, elbow[1] + 0.5, "$\\theta_2$", color=SAKURA, fontsize=13)
    ax.set_xlim(-0.7, 3.8); ax.set_ylim(-0.7, 3.0)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("平面 2R 机械臂：两个转角 $(\\theta_1,\\ \\theta_2)$ 决定末端位置",
                 fontsize=11, color=DEEP)
    fig.tight_layout()
    fig.savefig(OUT / "intro_2r_geometry.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    right_hand()
    dh_params()
    two_r_geometry()
    print("3 张导论几何图已生成 →", OUT)
