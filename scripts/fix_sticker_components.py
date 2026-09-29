# -*- coding: utf-8 -*-
"""贴纸组件修复：
1. mkdocs 只重写 markdown 图片路径（raw HTML img 的 src 不改写且深度全错）——
   章节头/完成卡全部改用 markdown 图片 + attr_list class。
2. glightbox 会给内容区所有图片套 <a> 包装（成为 grid 直接子元素）——
   CSS 由 img 改为盯 a:first-child（另一脚本改 CSS）。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGED = []

# ---------- A. 章节头（9 页）：markdown attr + markdown 图片 ----------
MODULES = [
    ("00_项目导航/从零开始学习路线总图.md", "mod-route"),
    ("01_数学/数学方向_学习路径与教材映射.md", "mod-math"),
    ("02_C++基础与进阶/C++方向_学习路径与教材映射.md", "mod-cpp"),
    ("03_SLAM/SLAM方向_学习路径与教材映射.md", "mod-slam"),
    ("04_移动机器人规控/移动规控方向_学习路径与教材映射.md", "mod-plan"),
    ("05_运动控制/运动控制方向_学习路径与教材映射.md", "mod-ctrl"),
    ("06_具身智能/具身智能方向_学习路径与教材映射.md", "mod-emb"),
    ("07_机器人学导论/00_机器人学导论_学习地图.md", "mod-intro"),
    ("08_可视化实验室/README.md", "mod-lab"),
]

RAW_IMG = re.compile(
    r'<img class="rt-chapter-header__avatar" src="[^"]*" alt="">\n')

for path, mod in MODULES:
    p = ROOT / path
    t = p.read_text(encoding="utf-8")
    orig = t
    # 1) div 加 markdown attr
    if '<div class="rt-chapter-header">' in t:
        t = t.replace('<div class="rt-chapter-header">',
                      '<div class="rt-chapter-header" markdown>')
    # 2) raw img → markdown img（源文件相对路径，mkdocs 自动按输出深度改写）
    t2 = RAW_IMG.sub(f"![紫樱](../assets/mascots/{mod}.webp){{.rt-chapter-header__avatar}}\n", t)
    if t2 == t and "rt-chapter-header__avatar" in t and "![紫樱]" not in t:
        raise AssertionError(f"{path}: raw img 未匹配")
    t = t2
    if t != orig:
        p.write_text(t, encoding="utf-8")
        CHANGED.append(path)
        print("  ✔", path)

# ---------- B. 完成卡（8 页）：纯 markdown 结构 + attr_list ----------
COMPLETE_RE = re.compile(
    r'<div class="rt-complete" markdown>\n\n'
    r'<img class="rt-complete__sticker" src="(?P<src>[^"]*)" alt="紫樱">\n\n'
    r'<p class="rt-complete__title"><span class="rt-complete__badge">✓</span>(?P<title>[^<]*)</p>\n\n'
    r'<p class="rt-complete__body">(?P<body>.*)</p>\n\n'
    r'</div>', re.S)

def fix_complete(m):
    body = m.group("body")
    # 提取链接目标并保持 markdown 链接（mkdocs 会改写为正确深度）
    return (
        '<div class="rt-complete" markdown>\n\n'
        f'![紫樱]({m.group("src")}){{.rt-complete__sticker}}\n\n'
        f'✓ 本章完成 · {m.group("title")}\n'
        '{: .rt-complete__title}\n\n'
        f'{body}\n'
        '{: .rt-complete__body}\n\n'
        '</div>'
    )

COMPLETES = [
    "01_数学/00_大学基础筑基/10_微积分I_极限与一元微分.md",
    "01_数学/00_大学基础筑基/20_微积分II_积分_级数与多元入门.md",
    "01_数学/00_大学基础筑基/30_线性代数I_矩阵与线性方程组.md",
    "01_数学/00_大学基础筑基/40_线性代数II_特征值_二次型与正定性.md",
    "01_数学/00_大学基础筑基/50_概率与统计基础.md",
    "01_数学/00_大学基础筑基/60_数值方法与复变速成.md",
    "07_机器人学导论/20_空间描述与坐标变换.md",
    "07_机器人学导论/30_机械臂正运动学入门.md",
]
for path in COMPLETES:
    p = ROOT / path
    t = p.read_text(encoding="utf-8")
    if '{: .rt-complete__title}' in t:
        print("  =", path, "已修复")
        continue
    t2, n = COMPLETE_RE.subn(fix_complete, t)
    assert n == 1, f"{path}: 完成卡匹配 {n} 处"
    p.write_text(t2, encoding="utf-8")
    CHANGED.append(path)
    print("  ✔", path)

print(f"完成：{len(CHANGED)} 个文件")
