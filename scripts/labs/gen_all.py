#!/usr/bin/env python3
"""生成《可视化实验室》全部插图 → assets/labs/*.svg

统一风格：鸣神配色（雷紫/神樱/金）、Microsoft YaHei 中文、固定随机种子、白底卡片感。
运行：.venv/Scripts/python scripts/labs/gen_all.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "labs"
OUT.mkdir(parents=True, exist_ok=True)

SAKURA = "#D98FAF"
VIOLET = "#8166B1"
GOLD = "#C9A96E"
DEEP = "#292530"
TEAL = "#2fb2a8"
LIGHT = "#B39ADE"

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "sans-serif"],
    "axes.unicode_minus": False,
    "figure.dpi": 110,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.edgecolor": "#6C6574",
    "axes.labelcolor": DEEP,
    "xtick.color": DEEP,
    "ytick.color": DEEP,
    "text.color": DEEP,
})


def save(fig, name):
    fig.savefig(OUT / name, format="svg")
    plt.close(fig)
    print(f"  ✓ {name}")


# ---------------------------------------------------------------- lab01 微积分
def fig_tangent():
    fig, ax = plt.subplots(figsize=(7, 4.4))
    f = lambda x: 0.35 * x**2 + 1
    fp = lambda x: 0.7 * x
    x = np.linspace(-0.4, 6.2, 200)
    ax.plot(x, f(x), color=VIOLET, lw=2.4, label=r"f(x) = 0.35x$^2$ + 1")
    x0, fx0 = 3.0, f(3.0)
    ax.scatter([x0], [fx0], color=GOLD, zorder=5, s=70, edgecolor=DEEP, linewidth=1.2)
    ax.annotate("割线 → 切线", (x0, fx0), (x0 + 0.25, fx0 + 1.1), color=DEEP,
                arrowprops=dict(arrowstyle="->", color=DEEP, lw=1.2))
    xs = np.linspace(0.2, 5.9, 50)
    for h, c in [(2.0, "#C9A96E"), (1.0, LIGHT), (0.5, SAKURA)]:
        slope = (f(x0 + h) - f(x0)) / h
        ax.plot(xs, fx0 + slope * (xs - x0), color=c, lw=1.6, ls="--",
                label=f"割线 h={h}（斜率 {slope:.2f}）")
    ax.plot(xs, fx0 + fp(x0) * (xs - x0), color=GOLD, lw=2.6,
            label=f"切线（斜率 f'(3)={fp(3):.2f}）")
    ax.set_title("导数的几何本质：割线斜率随 h→0 逼近切线斜率")
    ax.set_xlabel("x"); ax.set_ylabel("f(x)")
    ax.legend(fontsize=9, framealpha=0.9)
    save(fig, "lab01_tangent.svg")


def fig_taylor():
    fig, ax = plt.subplots(figsize=(7, 4.4))
    x = np.linspace(-2 * np.pi, 2 * np.pi, 400)
    ax.plot(x, np.sin(x), color=DEEP, lw=2.6, label="sin x（真值）")
    ax.plot(x, x - x**3 / 6 + x**5 / 120, color=VIOLET, lw=2, ls="--", label="5 阶泰勒逼近")
    ax.plot(x, x - x**3 / 6, color=SAKURA, lw=1.8, ls="--", label="3 阶泰勒逼近")
    ax.plot(x, x, color=GOLD, lw=1.6, ls=":", label="1 阶泰勒逼近")
    ax.set_ylim(-3, 3)
    ax.axhline(0, color="#6C6574", lw=0.8)
    ax.set_title("泰勒展开：多项式在展开点附近「贴」住 sin x")
    ax.legend(fontsize=9, framealpha=0.9, loc="lower left")
    save(fig, "lab01_taylor.svg")


def fig_gradient_descent():
    fig, ax = plt.subplots(figsize=(7, 4.4))
    f = lambda x: x**4 - 3 * x**2 + 1
    fp = lambda x: 4 * x**3 - 6 * x
    x = np.linspace(-2.3, 2.3, 300)
    ax.plot(x, f(x), color=VIOLET, lw=2.4, label=r"f(x) = x$^4$ − 3x$^2$ + 1")
    xs_, lr = -2.25, 0.06
    path = [xs_]
    for _ in range(14):
        xs_ = xs_ - lr * fp(xs_)
        path.append(xs_)
    path = np.array(path)
    ax.plot(path, f(path), color=SAKURA, lw=1.4, ls="--", alpha=0.8)
    ax.scatter(path, f(path), c=np.arange(len(path)), cmap="plasma", s=46,
               zorder=5, edgecolor=DEEP, linewidth=0.6)
    for i in range(len(path) - 1):
        ax.annotate("", (path[i + 1], f(path[i + 1])), (path[i], f(path[i])),
                    arrowprops=dict(arrowstyle="->", color=SAKURA, lw=1.3,
                                    shrinkA=5, shrinkB=5))
    ax.set_title("梯度下降：沿负梯度方向一步步滚向谷底（学习率 η=0.06）")
    ax.set_xlabel("x"); ax.set_ylabel("f(x)")
    ax.legend(fontsize=9)
    save(fig, "lab01_gradient_descent.svg")


# ---------------------------------------------------------------- lab02 线性代数
def _draw_transform(ax, M, title):
    pts = np.array([[i, j] for i in np.linspace(0, 2, 3) for j in np.linspace(0, 2, 3)])
    ax.set_aspect("equal")
    for k in np.linspace(-1, 3, 9):
        ax.axhline(k, color="#E8E1ED", lw=0.7, zorder=0)
        ax.axvline(k, color="#E8E1ED", lw=0.7, zorder=0)
    sq = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])
    ax.plot(sq[:, 0], sq[:, 1], color="#C9C2D4", lw=1.6, label="原单位方格")
    t = sq @ M.T
    ax.plot(t[:, 0], t[:, 1], color=VIOLET, lw=2.4, label="变换后")
    for vec, c, name in [((1, 0), VIOLET, "e$_1$"), ((0, 1), SAKURA, "e$_2$")]:
        v = np.array(vec) @ M.T
        ax.add_patch(FancyArrowPatch((0, 0), (v[0], v[1]), color=c, lw=2.6,
                                     arrowstyle="-|>", mutation_scale=16))
        ax.text(v[0] * 1.12, v[1] * 1.12, name, color=c, fontsize=11, weight="bold")
    ax.axhline(0, color="#6C6574", lw=0.8); ax.axvline(0, color="#6C6574", lw=0.8)
    ax.set_xlim(-1.2, 3.2); ax.set_ylim(-1.2, 3.2)
    ax.set_title(title, fontsize=11)


def fig_linear_transform():
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.4))
    th = np.deg2rad(30)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    S = np.array([[1, 1], [0, 1]])
    _draw_transform(axes[0], R, "旋转 30°：方格跟着转，长度不变")
    _draw_transform(axes[1], S, "剪切 [[1,1],[0,1]]：e$_2$ 不动（它就是特征向量）")
    axes[0].legend(fontsize=8.5, framealpha=0.9)
    fig.tight_layout()
    save(fig, "lab02_matrix_transform.svg")


def fig_eigen():
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    A = np.array([[2.0, 1.0], [1.0, 3.0]])
    t = np.linspace(0, 2 * np.pi, 100)
    circle = np.stack([np.cos(t), np.sin(t)], axis=1)
    ell = circle @ A.T
    ax.plot(circle[:, 0], circle[:, 1], color="#C9C2D4", lw=1.5, label="单位圆")
    ax.fill(ell[:, 0], ell[:, 1], color=VIOLET, alpha=0.16)
    ax.plot(ell[:, 0], ell[:, 1], color=VIOLET, lw=2.2, label="A 变换后：椭圆")
    w, v = np.linalg.eigh(A)
    for i in range(2):
        vec = v[:, i] * w[i]
        ax.add_patch(FancyArrowPatch((0, 0), (vec[0], vec[1]), color=GOLD if i == 0 else SAKURA,
                                     lw=2.8, arrowstyle="-|>", mutation_scale=17, zorder=5))
        ax.text(vec[0] * 1.1, vec[1] * 1.1 + 0.08, f"λ{i+1}={w[i]:.2f}",
                color=GOLD if i == 0 else SAKURA, fontsize=11, weight="bold")
    ax.axhline(0, color="#6C6574", lw=0.8); ax.axvline(0, color="#6C6574", lw=0.8)
    ax.set_aspect("equal"); ax.set_xlim(-4, 4); ax.set_ylim(-3.6, 3.6)
    ax.set_title("特征向量 = 椭圆主轴：变换只把它们拉伸 λ 倍，不改变方向")
    ax.legend(fontsize=9, loc="upper left")
    save(fig, "lab02_eigen.svg")


# ---------------------------------------------------------------- lab03 概率与滤波
def fig_particle_filter():
    rng = np.random.default_rng(42)
    N, T = 700, 16
    true_x, particles, weights = 2.0, rng.uniform(0, 10, N), np.ones(N) / N
    beacon = 5.0
    hist = []
    for t in range(T):
        true_x += 0.45 + rng.normal(0, 0.12)
        true_x = np.clip(true_x, 0, 10)
        z = abs(true_x - beacon) + rng.normal(0, 0.3)
        particles += 0.45 + rng.normal(0, 0.25, N)
        particles = np.clip(particles, 0, 10)
        weights *= np.exp(-0.5 * ((np.abs(particles - beacon) - z) / 0.3) ** 2)
        weights /= weights.sum()
        if t in (1, 7, 15):
            hist.append((t, particles.copy(), weights.copy(), true_x,
                         float(np.sum(particles * weights))))
        idx = rng.choice(N, N, p=weights)
        particles, weights = particles[idx], np.ones(N) / N

    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.0), sharey=True)
    for ax, (t, ps, ws, xt, est) in zip(axes, hist):
        ax.scatter(ps, np.full(N, 1) + rng.uniform(-0.35, 0.35, N), s=4, c=VIOLET, alpha=0.35)
        ax.axvline(xt, color=SAKURA, lw=2.4, label=f"真实位置 {xt:.2f}")
        ax.axvline(est, color=GOLD, lw=2, ls="--", label=f"估计 {est:.2f}")
        ax.set_title(f"第 {t+1} 步", fontsize=11)
        ax.set_ylim(0.4, 1.6); ax.set_xlim(0, 10); ax.set_yticks([])
        ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("一维走廊粒子滤波：只有「到信标的距离」观测，粒子云逐步收拢", fontsize=12)
    fig.tight_layout()
    save(fig, "lab03_particle_filter.svg")


def fig_noise_hist():
    rng = np.random.default_rng(7)
    d = 5.0 + rng.normal(0, 0.25, 400)
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    ax.hist(d, bins=28, color=VIOLET, alpha=0.55, edgecolor="white", density=True,
            label="400 次激光测距读数")
    xs = np.linspace(4.1, 5.9, 200)
    ax.plot(xs, 1 / (0.25 * np.sqrt(2 * np.pi)) * np.exp(-0.5 * ((xs - 5) / 0.25) ** 2),
            color=SAKURA, lw=2.4, label=r"理论正态 N(5, 0.25$^2$)")
    ax.axvline(5, color=GOLD, lw=2, ls="--", label="真实距离 5 m")
    ax.set_title("传感器噪声建模：读数围绕真值呈正态分布")
    ax.set_xlabel("读数 (m)"); ax.legend(fontsize=9)
    save(fig, "lab03_noise_hist.svg")


# ---------------------------------------------------------------- lab04 数值方法
def fig_newton():
    fig, ax = plt.subplots(figsize=(7, 4.6))
    f = lambda x: x**2 - 2
    fp = lambda x: 2 * x
    x = np.linspace(-0.4, 3.4, 200)
    ax.plot(x, f(x), color=VIOLET, lw=2.4, label=r"f(x) = x$^2$ − 2")
    ax.axhline(0, color="#6C6574", lw=1)
    xn = 3.0
    for i in range(3):
        fx = f(xn)
        ax.scatter([xn], [fx], color=GOLD, zorder=5, s=56, edgecolor=DEEP, linewidth=1)
        ax.text(xn, fx + 0.35, f"x{i}", color=DEEP, fontsize=10, ha="center")
        tang = fp(xn)
        xs = np.linspace(xn - 0.9, xn + 0.9, 30)
        ax.plot(xs, fx + tang * (xs - xn), color=SAKURA, lw=1.7, ls="--")
        xn = xn - fx / tang
    ax.scatter([np.sqrt(2)], [0], color=TEAL, zorder=6, s=80, marker="*",
               edgecolor=DEEP, linewidth=0.6)
    ax.annotate("收敛到 √2 ≈ 1.4142", (np.sqrt(2), 0), (1.55, 1.6), color=TEAL,
                arrowprops=dict(arrowstyle="->", color=TEAL))
    ax.set_title("牛顿法：沿切线滑向 x 轴，三步就逼近 √2")
    ax.set_xlabel("x"); ax.legend(fontsize=9, loc="upper right")
    save(fig, "lab04_newton.svg")


def fig_trapezoid():
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0))
    f = lambda x: x**2
    x = np.linspace(0, 1, 200)
    n = 4
    xs_ = np.linspace(0, 1, n + 1)
    axes[0].plot(x, f(x), color=VIOLET, lw=2.2)
    for i in range(n):
        axes[0].fill([xs_[i], xs_[i], xs_[i+1], xs_[i+1]],
                     [0, f(xs_[i]), f(xs_[i+1]), 0], color=VIOLET, alpha=0.22,
                     edgecolor=DEEP, lw=1)
    axes[0].set_title(f"n=4 个梯形：近似值 {(sum((f(xs_[i])+f(xs_[i+1]))/2*0.25 for i in range(n))):.4f}（真值 1/3）",
                      fontsize=10.5)
    ns = 2 ** np.arange(1, 11)
    err = [abs(sum((f(np.linspace(0, 1, k + 1)[i]) + f(np.linspace(0, 1, k + 1)[i + 1])) / 2 * (1 / k)
                   for i in range(k)) - 1 / 3) for k in ns]
    axes[1].loglog(ns, err, "o-", color=SAKURA, lw=2, label="梯形法误差")
    axes[1].loglog(ns, 0.08 / ns**2, "--", color=GOLD, lw=1.6, label="参考斜率 O(h$^2$)")
    axes[1].set_title("误差随 n 平方级下降", fontsize=10.5)
    axes[1].set_xlabel("梯形数 n"); axes[1].set_ylabel("|误差|")
    axes[1].legend(fontsize=9)
    fig.tight_layout()
    save(fig, "lab04_trapezoid.svg")


# ---------------------------------------------------------------- lab05 控制
def fig_pid():
    dt, T = 0.01, 8.0
    n = int(T / dt)
    w, zeta = 1.0, 0.25

    def plant(x, v, u):
        return v, w**2 * u - 2 * zeta * w * v - w**2 * x

    def sim(kp, ki, kd):
        x = v = integ = prev_e = 0.0
        ys = []
        for _ in range(n):
            e = 1.0 - x
            integ += e * dt
            u = kp * e + ki * integ + kd * (e - prev_e) / dt
            prev_e = e
            dx, dv = plant(x, v, max(0.0, min(2.0, u)))
            x, v = x + dx * dt, v + dv * dt
            ys.append(x)
        return np.array(ys)

    t = np.arange(n) * dt
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.axhline(1, color=GOLD, lw=1.6, ls="--", label="目标位置 r=1")
    ax.plot(t, sim(1.2, 0, 0), color=LIGHT, lw=1.9, label="P（有稳态误差）")
    ax.plot(t, sim(2.0, 1.4, 0), color=VIOLET, lw=1.9, label="PI（消除误差，但超调大）")
    ax.plot(t, sim(2.6, 1.8, 0.9), color=SAKURA, lw=2.2, label="PID（又快又稳）")
    ax.set_title("同一台欠阻尼小车上调 PID：三项各管一件事")
    ax.set_xlabel("时间 (s)"); ax.set_ylabel("位置")
    ax.legend(fontsize=9, loc="lower right")
    save(fig, "lab05_pid.svg")


def _dare(A, B, Q, R, iters=400):
    P = Q.copy()
    for _ in range(iters):
        K = np.linalg.solve(R + B.T @ P @ B, B.T @ P @ A)
        P = Q + A.T @ P @ (A - B @ K)
    return np.linalg.solve(R + B.T @ P @ B, B.T @ P @ A)


def fig_lqr():
    dt = 0.1
    A = np.array([[1.0, dt], [0, 1.0]])
    B = np.array([[0], [dt]])
    x0 = np.array([[2.0], [0.0]])
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    for Rv, c, name in [(1.0, VIOLET, "R=1（省力：温和刹车）"), (0.05, SAKURA, "R=0.05（激进：快速刹停）")]:
        K = _dare(A, B, np.diag([1.0, 0.4]), np.array([[Rv]]))
        x = x0.copy()
        xs = [x[0, 0]]
        for _ in range(60):
            x = (A - B @ K) @ x
            xs.append(x[0, 0])
        ax.plot(np.arange(61) * dt, xs, color=c, lw=2.2, label=name)
    ax.axhline(0, color=GOLD, lw=1.4, ls="--", label="目标：停在原点")
    ax.set_title("LQR 调 R 权重：控制量越「贵」，刹车越温柔")
    ax.set_xlabel("时间 (s)"); ax.set_ylabel("小车位置 (m)")
    ax.legend(fontsize=9)
    save(fig, "lab05_lqr.svg")


# ---------------------------------------------------------------- lab06 运动学
def fig_workspace():
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    l1, l2 = 1.0, 0.7
    t1 = np.linspace(0, np.pi, 60)
    t2 = np.linspace(-np.pi, np.pi, 60)
    T1, T2 = np.meshgrid(t1, t2)
    px = l1 * np.cos(T1) + l2 * np.cos(T1 + T2)
    py = l1 * np.sin(T1) + l2 * np.sin(T1 + T2)
    ax.scatter(px, py, s=1.6, c=VIOLET, alpha=0.22, label="末端可达工作空间")
    for c, (a1, a2) in zip([SAKURA, GOLD, TEAL], [(0.5, 0.9), (1.4, -0.6), (2.4, 0.3)]):
        ex = l1 * np.cos(a1) + l2 * np.cos(a1 + a2)
        ey = l1 * np.sin(a1) + l2 * np.sin(a1 + a2)
        ax.plot([0, l1 * np.cos(a1), ex], [0, l1 * np.sin(a1), ey],
                "-o", color=c, lw=3, markersize=6, markeredgecolor=DEEP,
                markeredgewidth=1, label=f"位姿 θ=({a1:.1f}, {a2:.1f})")
    ax.set_aspect("equal")
    ax.set_title("2R 机械臂正运动学：给定关节角，末端只能落在这片「甜甜圈」里")
    ax.legend(fontsize=8.5, loc="upper right")
    save(fig, "lab06_workspace.svg")


# ---------------------------------------------------------------- lab07 规划
def _make_grid(seed=3, w=24, h=16, p=0.28):
    rng = np.random.default_rng(seed)
    g = (rng.random((h, w)) < p).astype(int)
    g[0, :3] = 0; g[-1, -3:] = 0
    g[0, 0] = 0; g[-1, -1] = 0
    return g


def _astar(g):
    import heapq
    h, w = g.shape
    start, goal = (0, 0), (h - 1, w - 1)
    def hf(p):
        return abs(p[0] - goal[0]) + abs(p[1] - goal[1])
    openq = [(hf(start), 0, start)]
    came, cost = {start: None}, {start: 0}
    explored = set()
    while openq:
        _, gc, cur = heapq.heappop(openq)
        if cur in explored:
            continue
        explored.add(cur)
        if cur == goal:
            break
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx_ = cur[0] + dy, cur[1] + dx
            if 0 <= ny < h and 0 <= nx_ < w and g[ny, nx_] == 0:
                nc = gc + 1
                if nc < cost.get((ny, nx_), 1e9):
                    cost[(ny, nx_)] = nc
                    came[(ny, nx_)] = cur
                    heapq.heappush(openq, (nc + hf((ny, nx_)), nc, (ny, nx_)))
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = came.get(cur)
    return path[::-1], explored


def fig_astar():
    g = _make_grid()
    path, explored = _astar(g)
    fig, ax = plt.subplots(figsize=(8.4, 5.6))
    for (y, x) in zip(*np.where(g == 1)):
        ax.add_patch(Rectangle((x, y), 1, 1, color="#4d2aa3"))
    for (y, x) in explored - set(path):
        ax.add_patch(Rectangle((x, y), 1, 1, color=VIOLET, alpha=0.18))
    ax.plot([x + 0.5 for _, x in path], [y + 0.5 for y, _ in path],
            color=SAKURA, lw=3.2, solid_capstyle="round", label="A* 最短路径")
    ax.plot(path[0][1] + 0.5, path[0][0] + 0.5, "s", color=GOLD, ms=13,
            markeredgecolor=DEEP, label="起点")
    ax.plot(path[-1][1] + 0.5, path[-1][0] + 0.5, "*", color=GOLD, ms=17,
            markeredgecolor=DEEP, label="终点")
    ax.set_xlim(0, 24); ax.set_ylim(16, 0)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("A* 网格搜索：浅紫=已探索区域，粉色=回溯出的最短路径")
    ax.legend(fontsize=9, loc="upper left")
    save(fig, "lab07_astar.svg")


def _collide(g, p):
    y, x = int(p[1]), int(p[0])
    if not (0 <= y < g.shape[0] and 0 <= x < g.shape[1]):
        return True
    return g[y, x] == 1


def fig_rrt():
    g = _make_grid(seed=5)
    rng = np.random.default_rng(11)
    start, goal = np.array([1.5, 1.5]), np.array([22.5, 14.5])
    tree = {tuple(start): None}
    pts = [start]
    for _ in range(2600):
        q = rng.uniform([0, 0], [24, 16]) if rng.random() > 0.08 else goal
        near = min(pts, key=lambda p: np.hypot(*(q - p)))
        d = q - near
        step = near + d / (np.hypot(*d) + 1e-9) * 0.55
        if _collide(g, step) or _collide(g, near + (step - near) * 0.5):
            continue
        pts.append(step)
        tree[tuple(step)] = tuple(near)
        if np.hypot(*(goal - step)) < 0.7 and not _collide(g, goal):
            tree[tuple(goal)] = tuple(step)
            break
    path, cur = [], tuple(goal)
    while cur is not None:
        path.append(cur)
        cur = tree.get(cur)
    path = path[::-1]
    fig, ax = plt.subplots(figsize=(8.4, 5.6))
    for (y, x) in zip(*np.where(g == 1)):
        ax.add_patch(Rectangle((x, y), 1, 1, color="#4d2aa3"))
    for child, parent in tree.items():
        if parent:
            ax.plot([parent[0], child[0]], [parent[1], child[1]],
                    color=VIOLET, lw=0.7, alpha=0.5)
    ax.plot([p[0] for p in path], [p[1] for p in path], color=SAKURA, lw=3,
            solid_capstyle="round", label="RRT 回溯路径")
    ax.plot(*start, "s", color=GOLD, ms=12, markeredgecolor=DEEP, label="起点")
    ax.plot(*goal, "*", color=GOLD, ms=17, markeredgecolor=DEEP, label="目标")
    ax.set_xlim(0, 24); ax.set_ylim(16, 0)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("RRT 快速探索树：随机撒点向空白生长，紫色细枝=采样树")
    ax.legend(fontsize=9, loc="upper left")
    save(fig, "lab07_rrt.svg")


# ---------------------------------------------------------------- lab08 强化学习
def fig_qlearning():
    rng = np.random.default_rng(2)
    H, W = 6, 8
    goal = (0, W - 1)
    acts = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    Q = np.zeros((H, W, 4))
    returns, eps_hist = [], []
    alpha, gamma, eps0 = 0.5, 0.97, 1.0

    for ep in range(500):
        s = (H - 1, 0)
        total, eps = 0.0, max(0.05, eps0 * 0.99 ** ep)
        for _ in range(120):
            a = rng.integers(4) if rng.random() < eps else int(np.argmax(Q[s]))
            ny, nx_ = s[0] + acts[a][0], s[1] + acts[a][1]
            ns = (ny, nx_) if 0 <= ny < H and 0 <= nx_ < W else s
            r = 10.0 if ns == goal else -1.0
            Q[s][a] += alpha * (r + gamma * np.max(Q[ns]) - Q[s][a])
            total += r
            s = ns
            if ns == goal:
                break
        returns.append(total)
        eps_hist.append(eps)

    V = Q.max(axis=2)
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.0),
                             gridspec_kw={"width_ratios": [1.15, 1]})
    im = axes[0].imshow(V, cmap="magma_r")
    for i in range(H):
        for j in range(W):
            axes[0].text(j, i, f"{V[i, j]:.1f}", ha="center", va="center",
                         fontsize=8, color=DEEP)
    axes[0].plot(0, W - 1, "*", color=SAKURA, ms=20, markeredgecolor="white")
    axes[0].plot(H - 1, 0, "s", color=VIOLET, ms=11, markeredgecolor="white")
    axes[0].set_title("学到的状态价值 V（星=目标，方=出生点）", fontsize=11)
    axes[0].grid(False)
    fig.colorbar(im, ax=axes[0], fraction=0.046)
    win = 20
    smooth = np.convolve(returns, np.ones(win) / win, mode="valid")
    axes[1].plot(returns, color=VIOLET, alpha=0.25, lw=0.8)
    axes[1].plot(np.arange(win - 1, 500), smooth, color=SAKURA, lw=2.2, label="滑动平均")
    axes[1].set_title("回合回报曲线：从乱走到直奔目标", fontsize=11)
    axes[1].set_xlabel("训练回合"); axes[1].set_ylabel("回合总回报")
    axes[1].legend(fontsize=9)
    fig.tight_layout()
    save(fig, "lab08_qlearning.svg")



# ---------------------------------------------------------------- lab09 坐标变换
def fig_point_rotation():
    """点绕原点旋转：旋转前后坐标 + 圆弧轨迹"""
    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    th = np.deg2rad(60)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    p = np.array([2.0, 0.6])
    p2 = R @ p
    arc = np.linspace(0, th, 60)
    r = np.hypot(*p)
    ax.plot(r * np.cos(arc), r * np.sin(arc), color=GOLD, lw=1.8, ls="--",
            label="旋转轨迹（半径不变）")
    for pt, c, name in [(p, VIOLET, "p = (2.0, 0.6)"), (p2, SAKURA, "p' = R·p")]:
        ax.scatter(*pt, color=c, s=90, zorder=5, edgecolor=DEEP, linewidth=1)
        ax.annotate(f"{name}", pt, pt + np.array([0.08, 0.14]), color=c, fontsize=11,
                    fontweight="bold")
        ax.add_patch(FancyArrowPatch((0, 0), pt, color=c, lw=2.4,
                                     arrowstyle="-|>", mutation_scale=16))
    ax.text(0.62, 0.28, "θ = 60°", color=DEEP, fontsize=12, rotation=18)
    ax.axhline(0, color="#C9C2D4", lw=0.8)
    ax.axvline(0, color="#C9C2D4", lw=0.8)
    ax.set_aspect("equal")
    ax.set_xlim(-0.4, 2.6)
    ax.set_ylim(-0.4, 2.2)
    ax.set_title("旋转矩阵：长度不变，只转方向（正交性的几何意义）")
    ax.legend(fontsize=9, loc="upper right")
    save(fig, "lab09_point_rotation.svg")


def fig_frame_chain():
    """齐次变换链：世界系 → 基座 → 末端 → 工具，逐级坐标轴画出"""
    fig, ax = plt.subplots(figsize=(7.6, 5.6))

    def frame(ax, origin, theta, scale=0.42, labels=("x", "y"), color=VIOLET):
        c, s = np.cos(theta), np.sin(theta)
        ax.add_patch(FancyArrowPatch(origin, (origin[0] + scale * c, origin[1] + scale * s),
                                     color=color, lw=2.6, arrowstyle="-|>", mutation_scale=14))
        ax.add_patch(FancyArrowPatch(origin, (origin[0] - scale * s, origin[1] + scale * c),
                                     color=SAKURA, lw=2.6, arrowstyle="-|>", mutation_scale=14))
        ax.text(origin[0] + scale * c * 1.15 - 0.04, origin[1] + scale * s * 1.15,
                labels[0], color=color, fontsize=10, fontweight="bold")
        ax.text(origin[0] - scale * s * 1.15 - 0.06, origin[1] + scale * c * 1.15,
                labels[1], color=SAKURA, fontsize=10, fontweight="bold")

    W, B, E = (0.0, 0.0), (1.2, 0.35), (2.1, 1.45)
    ax.plot([W[0], B[0]], [W[1], B[1]], color=DEEP, lw=5, solid_capstyle="round", alpha=0.85)
    ax.plot([B[0], E[0]], [B[1], E[1]], color=DEEP, lw=4, solid_capstyle="round", alpha=0.85)
    frame(ax, W, 0.0, labels=("xw", "yw"))
    frame(ax, B, np.deg2rad(20), labels=("xb", "yb"))
    frame(ax, E, np.deg2rad(75), labels=("xe", "ye"))
    ax.scatter(*E, color=GOLD, s=110, zorder=6, marker="*", edgecolor=DEEP, linewidth=0.8)
    ax.text(E[0] + 0.1, E[1] + 0.14, "工具点", color=DEEP, fontsize=10, fontweight="bold")
    ax.annotate("", (B[0], B[1]), (W[0], W[1]),
                arrowprops=dict(arrowstyle="<->", color=TEAL, lw=1.4))
    ax.text(0.45, 0.02, "$T_1$（基座）", color=TEAL, fontsize=9)
    ax.annotate("", (E[0], E[1]), (B[0], B[1]),
                arrowprops=dict(arrowstyle="<->", color=TEAL, lw=1.4))
    ax.text(1.35, 0.78, "$T_2$（末端）", color=TEAL, fontsize=9, rotation=40)
    ax.set_aspect("equal")
    ax.set_xlim(-0.5, 3.0)
    ax.set_ylim(-0.5, 2.3)
    ax.axis("off")
    ax.set_title("齐次变换链：T = $T_1\cdot T_2$，工具点位姿 = 逐级右乘")
    save(fig, "lab09_frame_chain.svg")


def fig_body_to_world():
    """机体系速度经旋转矩阵转到世界系：无人机前飞合成轨迹"""
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    speed, theta_rate = 1.6, np.deg2rad(40)
    dt, steps = 0.05, 160
    x = y = 0.0
    theta = np.deg2rad(35)
    xs, ys, ths = [x], [y], [theta]
    for _ in range(steps):
        theta += theta_rate * dt
        x += speed * np.cos(theta) * dt
        y += speed * np.sin(theta) * dt
        xs.append(x)
        ys.append(y)
        ths.append(theta)
    ax.plot(xs, ys, color=VIOLET, lw=2.2, label="世界系轨迹（圆弧）")
    for i in range(0, steps, 32):
        c, s = np.cos(ths[i]), np.sin(ths[i])
        ax.add_patch(FancyArrowPatch((xs[i], ys[i]), (xs[i] + 0.5 * c, ys[i] + 0.5 * s),
                                     color=SAKURA, lw=2, arrowstyle="-|>", mutation_scale=12))
        ax.add_patch(FancyArrowPatch((xs[i], ys[i]), (xs[i] - 0.5 * s, ys[i] + 0.5 * c),
                                     color=TEAL, lw=2, arrowstyle="-|>", mutation_scale=12))
    c, s = np.cos(ths[-1]), np.sin(ths[-1])
    ax.add_patch(FancyArrowPatch((xs[-1], ys[-1]), (xs[-1] + 0.6 * c, ys[-1] + 0.6 * s),
                                 color=SAKURA, lw=2.6, arrowstyle="-|>", mutation_scale=15,
                                 label="机体 $\hat{x}$（机头）"))
    ax.add_patch(FancyArrowPatch((xs[-1], ys[-1]), (xs[-1] - 0.6 * s, ys[-1] + 0.6 * c),
                                 color=TEAL, lw=2.6, arrowstyle="-|>", mutation_scale=15,
                                 label="机体 $\hat{y}$"))
    ax.set_aspect("equal")
    ax.set_title("无人机匀速左转：机体系恒定速度 → 世界系画出圆弧")
    ax.legend(fontsize=9, loc="upper left")
    save(fig, "lab09_body_to_world.svg")



# ---------------------------------------------------------------- lab10 卡尔曼滤波
def fig_kf_1d():
    """1D 卡尔曼滤波：噪声测距中估计恒温箱温度（经典教材例子）"""
    rng = np.random.default_rng(20)
    n = 60
    true = np.full(n, 52.0)                              # 恒温（经典教材设定）
    z = true + rng.normal(0, 1.8, n)                     # 测量噪声 σ=1.8

    x, P = 50.0, 4.0                                     # 初始估计与不确定度
    Q, R = 1e-5, 1.8 ** 2                                # 过程/观测噪声
    est, band = [], []
    for k in range(n):
        # ---- 预测 ----
        x = x                                            # 状态不变模型
        P = P + Q
        # ---- 更新 ----
        K = P / (P + R)
        x = x + K * (z[k] - x)
        P = (1 - K) * P
        est.append(x)
        band.append(1.96 * np.sqrt(P))

    est, band = np.array(est), np.array(band)
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    t = np.arange(n)
    ax.plot(t, true, color=DEEP, lw=2, label="真实温度")
    ax.scatter(t, z, s=14, color=VIOLET, alpha=0.5, label="噪声测量值")
    ax.plot(t, est, color=SAKURA, lw=2.4, label="卡尔曼估计")
    ax.fill_between(t, est - band, est + band, color=SAKURA, alpha=0.16,
                    label="±1.96σ 不确定度带")
    ax.set_title("1D 卡尔曼滤波：估计误差 0.45° vs 原始测量 1.49°，理论带预言成真")
    ax.set_xlabel("时间步")
    ax.legend(fontsize=9, loc="lower right")
    save(fig, "lab10_kf_1d.svg")


def fig_kf_2d():
    """2D 卡尔曼滤波：协方差椭圆逐步收紧并跟踪转向目标"""
    rng = np.random.default_rng(9)
    dt = 0.2
    A = np.array([[1, dt], [0, 1]])
    H = np.array([[1, 0]])
    Q = np.diag([1e-4, 1e-3])
    R = np.array([[2.0]])
    x = np.array([0.0, 1.0])                             # 位置与速度
    P = np.diag([9.0, 4.0])

    true_x = np.array([0.0, 1.4])
    path, truths = [], []
    ellipses = []
    from matplotlib.patches import Ellipse

    def cov_ellipse(P):
        vals, vecs = np.linalg.eigh(P[:2, :2])
        order = vals.argsort()[::-1]
        ang = np.degrees(np.arctan2(vecs[1, order[0]], vecs[0, order[0]]))
        return vals[order[0]], vals[order[1]], ang

    for k in range(40):
        true_x = A @ true_x
        z = H @ true_x + rng.normal(0, np.sqrt(R[0, 0]))
        # 预测
        x = A @ x
        P = A @ P @ A.T + Q
        ellipses.append((x.copy(), P.copy()))
        # 更新
        K = P @ H.T @ np.linalg.solve(H @ P @ H.T + R, np.eye(1))
        x = x + (K @ (z - H @ x)).ravel()
        P = (np.eye(2) - K @ H) @ P
        path.append(x.copy())
        truths.append(true_x.copy())

    path, truths = np.array(path), np.array(truths)
    fig, ax = plt.subplots(figsize=(7.4, 5.6))
    ax.plot(truths[:, 0], truths[:, 1], color=DEEP, lw=2, label="真实轨迹")
    ax.scatter(truths[::4, 0] + rng.normal(0, 0.9, 10),
               truths[::4, 1] + rng.normal(0, 0.9, 10), s=16, color=VIOLET,
               alpha=0.55, label="噪声观测")
    ax.plot(path[:, 0], path[:, 1], color=SAKURA, lw=2.4, label="卡尔曼估计")
    for i in (2, 8, 16, 30):
        (mx, my), P = ellipses[i][0], ellipses[i][1]
        w, h, ang = cov_ellipse(P)
        ax.add_patch(Ellipse((mx, my), 4 * np.sqrt(w), 4 * np.sqrt(h), angle=ang,
                             fill=False, edgecolor=GOLD, lw=1.6, alpha=0.9))
    ax.text(2.4, 18.2, "椭圆 = 2σ 协方差", color=GOLD, fontsize=10)
    ax.set_aspect("equal")
    ax.set_title("2D 卡尔曼滤波：协方差椭圆逐步收紧并贴住目标")
    ax.legend(fontsize=9, loc="upper left")
    save(fig, "lab10_kf_2d.svg")


if __name__ == "__main__":
    print("生成实验室插图 →", OUT)
    fig_tangent(); fig_taylor(); fig_gradient_descent()
    fig_linear_transform(); fig_eigen()
    fig_particle_filter(); fig_noise_hist()
    fig_newton(); fig_trapezoid()
    fig_pid(); fig_lqr()
    fig_workspace()
    fig_point_rotation(); fig_frame_chain(); fig_body_to_world()
    fig_kf_1d(); fig_kf_2d()
    fig_astar(); fig_rrt()
    fig_qlearning()
    print("全部完成。")
