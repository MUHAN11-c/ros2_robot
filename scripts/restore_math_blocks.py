#!/usr/bin/env python3
"""修复多行 $$ 公式块内部被误插入的空行（把块重新合为一个连续段落）。

状态机：
- 代码围栏内不动；
- 引用块行（> 前缀）的 body 剥去前缀后参与判定，内部空引用行（>）同样剔除；
- body 以 $$ 开头且非单行块 → 进入公式块，块内所有空行剔除，直到以 $$ 结尾的行。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRS = [
    "00_项目导航",
    "01_数学",
    "02_C++基础与进阶",
    "03_SLAM",
    "04_移动机器人规控",
    "05_运动控制",
    "06_具身智能",
    "07_机器人学导论",
]


def split_line(line: str) -> tuple[bool, str]:
    s = line.strip()
    if not s.startswith(">"):
        return False, s
    return True, s.lstrip("> \t")


def is_fence_body(body: str) -> bool:
    return body.startswith("```") or body.startswith("~~~")


def fix_lines(lines: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    dropped = 0
    in_fence = False
    in_math = False

    for line in lines:
        in_quote, body = split_line(line)

        if in_fence:
            out.append(line)
            if is_fence_body(body):
                in_fence = False
            continue
        if is_fence_body(body):
            in_fence = True
            out.append(line)
            continue

        if in_math:
            if body == "":
                dropped += 1  # 剔除公式块内部的空行/空引用行
                continue
            out.append(line)
            if body.endswith("$$"):
                in_math = False
            continue

        out.append(line)
        if body.startswith("$$"):
            inner = body[2:]
            single = inner.endswith("$$") and "$$" not in inner[:-2]
            if not single:
                in_math = True

    return out, dropped


def main() -> None:
    total_files = 0
    total_dropped = 0
    for d in DIRS:
        for md in (ROOT / d).rglob("*.md"):
            text = md.read_text(encoding="utf-8")
            if "$$" not in text:
                continue
            lines = [ln if ln.endswith("\n") else ln + "\n" for ln in text.splitlines(keepends=True)]
            fixed, dropped = fix_lines(lines)
            if dropped:
                md.write_text("".join(fixed), encoding="utf-8")
                total_files += 1
                total_dropped += dropped
    print(f"修复 {total_files} 个文件，剔除公式块内部空行 {total_dropped} 处")


if __name__ == "__main__":
    sys.exit(main())
