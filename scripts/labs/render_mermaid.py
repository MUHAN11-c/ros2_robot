#!/usr/bin/env python3
"""把 md 中的 ```mermaid 块用 mermaid-cli 预渲染为 SVG 并替换为图片引用。

- 幂等：以「源码内容哈希」为缓存键，重复运行不重复渲染；
- 产物：assets/labs/diagrams/<slug>.svg（提交进仓库，CI 无需浏览器）；
- 替换后的图片引用按文档深度生成相对路径。

用法：.venv/Scripts/python scripts/labs/render_mermaid.py
前置：scripts/labs 下已 npm i @mermaid-js/mermaid-cli
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABS = Path(__file__).resolve().parent
DIAGRAMS = ROOT / "assets" / "labs" / "diagrams"
SOURCES = LABS / "sources"
CACHE = LABS / "mermaid_cache.json"
PPCFG = LABS / "pp.json"
MMDC = LABS / "node_modules" / ".bin" / "mmdc.cmd"

TARGETS = [
    "08_可视化实验室/README.md",
    "08_可视化实验室/lab01_微积分实验室.md",
    "08_可视化实验室/lab02_线性代数实验室.md",
    "08_可视化实验室/lab03_概率与滤波实验室.md",
    "08_可视化实验室/lab04_数值方法实验室.md",
    "08_可视化实验室/lab05_控制实验室.md",
    "08_可视化实验室/lab06_运动学实验室.md",
    "08_可视化实验室/lab07_规划实验室.md",
    "08_可视化实验室/lab08_强化学习实验室.md",
    "08_可视化实验室/lab09_坐标变换实验室.md",
    "08_可视化实验室/lab10_卡尔曼滤波实验室.md",
    "00_项目导航/从零开始学习路线总图.md",
    "01_数学/数学方向_学习路径与教材映射.md",
    "02_C++基础与进阶/C++方向_学习路径与教材映射.md",
    "03_SLAM/SLAM方向_学习路径与教材映射.md",
    "04_移动机器人规控/移动规控方向_学习路径与教材映射.md",
    "05_运动控制/运动控制方向_学习路径与教材映射.md",
    "06_具身智能/具身智能方向_学习路径与教材映射.md",
]


def render_mmd(src: str, out_svg: Path) -> None:
    tmp = LABS / "_tmp.mmd"
    tmp.write_text(src, encoding="utf-8")
    subprocess.run(
        [str(MMDC), "-i", str(tmp), "-o", str(out_svg), "-p", str(PPCFG),
         "-b", "white"],
        check=True, capture_output=True, text=True,
    )
    # 后处理：mermaid 默认 width="100%" + 内联 max-width，作为 <img> 加载时
    # 会被拉伸到列宽导致窄高流程图文字巨大化。改为固有尺寸（取自 viewBox）。
    import re as _re
    svg = out_svg.read_text(encoding="utf-8")
    m = _re.search(r'viewBox="[\d.eE+-]+ [\d.eE+-]+ ([\d.eE+-]+) ([\d.eE+-]+)"', svg)
    if m:
        w, h = float(m.group(1)), float(m.group(2))
        svg = _re.sub(r'<svg ([^>]*?)width="100%"',
                      rf'<svg \1width="{w:.0f}" height="{h:.0f}"', svg, count=1)
        svg = _re.sub(r'(<svg [^>]*?)style="[^"]*"', r"\1", svg, count=1)
        out_svg.write_text(svg, encoding="utf-8")


def main() -> None:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    DIAGRAMS.mkdir(parents=True, exist_ok=True)
    SOURCES.mkdir(parents=True, exist_ok=True)
    # 源码归档：hash → 源码。缺失的归档项若 SVG 也不存在则无法再生（需 md 中还有块）
    for mmd in SOURCES.glob("*.mmd"):
        key = mmd.stem
        if key not in cache:
            body = mmd.read_text(encoding="utf-8")
            fname = f"diag_{key}.svg"
            render_mmd(body, DIAGRAMS / fname)
            cache[key] = fname
            print(f"  依据归档重渲染 {fname}")
    counter = {}
    for rel in TARGETS:
        p = ROOT / rel
        text = p.read_text(encoding="utf-8")
        if "```mermaid" not in text:
            continue
        depth = "../" * (len(rel.split("/")) - 1)
        parts = text.split("```mermaid")
        rebuilt = [parts[0]]
        for chunk in parts[1:]:
            body, _, rest = chunk.partition("```")
            key = hashlib.sha1(body.encode("utf-8")).hexdigest()[:10]
            fname = f"diag_{Path(rel).stem}_{key}.svg"
            (SOURCES / f"{Path(rel).stem}_{key}.mmd").write_text(body, encoding="utf-8")
            if key not in cache:
                render_mmd(body, DIAGRAMS / fname)
                cache[key] = fname
                print(f"  渲染 {fname}")
            else:
                fname = cache[key]
            rebuilt.append(f"\n\n![图示]({depth}assets/labs/diagrams/{fname})\n\n{rest}")
        p.write_text("".join(rebuilt), encoding="utf-8")
    CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    print(f"完成，缓存 {len(cache)} 张图。")


if __name__ == "__main__":
    sys.exit(main())
