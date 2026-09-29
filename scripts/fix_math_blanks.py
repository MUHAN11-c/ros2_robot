#!/usr/bin/env python3
"""给 $$ 显示公式块前后补空行，避免 arithmatex 行内规则错误处理产生游离 $。

处理三种上下文：
- 代码围栏（``` / ~~~）：内部一律不动；
- 引用块（> 前缀，含嵌套）：分隔行插入 ">" 保持引用语义；
- 多行公式块： opening $$ 行之后与 closing 行之前的行不改动。

判定均基于剥去引用前缀后的 body。
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
    """返回 (是否引用块行, 剥去引用前缀后的 body)。"""
    s = line.strip()
    if not s.startswith(">"):
        return False, line.strip()
    return True, s.lstrip("> \t")


def is_fence_body(body: str) -> bool:
    return body.startswith("```") or body.startswith("~~~")


def fix_lines(lines: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    changed = 0
    in_fence = False
    in_math = False  # 多行 $$ 块内部
    n = len(lines)

    for i, line in enumerate(lines):
        in_quote, body = split_line(line)
        sep = "> \n" if in_quote else "\n"

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
            out.append(line)
            if body.endswith("$$"):
                in_math = False
                nxt = split_line(lines[i + 1])[1] if i + 1 < n else ""
                if nxt:
                    out.append(sep)
                    changed += 1
            continue

        if body.startswith("$$"):
            prev = out[-1] if out else ""
            if prev.strip() and prev not in ("\n", "> \n"):
                out.append(sep)
                changed += 1
            out.append(line)
            single = len(body) > 4 and body.endswith("$$") and body.count("$$") >= 2
            if single:
                nxt = split_line(lines[i + 1])[1] if i + 1 < n else ""
                if nxt:
                    out.append(sep)
                    changed += 1
            else:
                in_math = True
            continue

        if body.endswith("$$"):
            # 非 $$ 开头却以 $$ 结尾：多行块的 closing（或行内写法），补后空行
            out.append(line)
            nxt = split_line(lines[i + 1])[1] if i + 1 < n else ""
            if nxt:
                out.append(sep)
                changed += 1
            continue

        out.append(line)

    return out, changed


def main() -> None:
    total_files = 0
    total_changes = 0
    for d in DIRS:
        for md in (ROOT / d).rglob("*.md"):
            text = md.read_text(encoding="utf-8")
            if "$$" not in text:
                continue
            lines = [ln if ln.endswith("\n") else ln + "\n" for ln in text.splitlines(keepends=True)]
            fixed, changed = fix_lines(lines)
            if changed:
                md.write_text("".join(fixed), encoding="utf-8")
                total_files += 1
                total_changes += changed
    print(f"修复 {total_files} 个文件，共插入 {total_changes} 处分隔行")


if __name__ == "__main__":
    sys.exit(main())
