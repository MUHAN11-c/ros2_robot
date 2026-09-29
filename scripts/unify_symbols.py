#!/usr/bin/env python3
"""全站符号统一（樱雷符号表）：⭐→★、📋→◆。

- 跳过代码围栏（``` / ~~~）内的内容，避免误伤代码示例
- 幂等：重复运行无副作用
- 替换后打印统计，供 git diff 抽查
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = [
    "00_项目导航", "01_数学", "02_C++基础与进阶", "03_SLAM",
    "04_移动机器人规控", "05_运动控制", "06_具身智能",
    "07_机器人学导论", "08_可视化实验室",
]
EXTRA = ["SUMMARY.md", "README.md"]

REPLACEMENTS = {
    "⭐": "★",
    "📋": "◆",
}


def is_fence(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("```") or s.startswith("~~~")


def fix_text(text: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    out = []
    changed = 0
    in_fence = False
    for line in lines:
        if is_fence(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        new = line
        for old, repl in REPLACEMENTS.items():
            if old in new:
                changed += new.count(old)
                new = new.replace(old, repl)
        out.append(new)
    return "".join(out), changed


def main() -> None:
    files_changed = 0
    total = 0
    targets = [ROOT / f for f in EXTRA]
    for d in DIRS:
        targets.extend((ROOT / d).rglob("*.md"))
    for p in targets:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        if not any(sym in text for sym in REPLACEMENTS):
            continue
        new, changed = fix_text(text)
        if changed:
            p.write_text(new, encoding="utf-8")
            files_changed += 1
            total += changed
    print(f"符号统一：{files_changed} 个文件，共 {total} 处（⭐→★ / 📋→◆，已跳过代码围栏）")


if __name__ == "__main__":
    sys.exit(main())
