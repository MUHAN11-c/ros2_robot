#!/usr/bin/env python3
"""把行中（非行首的缩进/列表标记之后）的 $$...$$ 对改为 $...$。

行内上下文中 arithmatex 对两种写法都用 \(...\) 渲染，但 $$ 配对在含 \\| 等
内容时会被行内规则错误切分产生游离 $；单 $ 配对则稳健。
"""
import re
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

PAIR = re.compile(r"\$\$([^$\n]+?)\$\$")


def split_line(line: str) -> tuple[bool, str]:
    s = line.strip()
    if not s.startswith(">"):
        return False, s
    return True, s.lstrip("> \t")


def convert_line(line: str) -> str:
    in_quote, body = split_line(line)
    if "$$" not in body:
        return line

    # 计算缩进+引用前缀长度；有前缀（列表/引用内）时 $$ 块规则不生效，一律按行内处理
    indent_len = len(line) - len(line.lstrip())
    stripped = line.lstrip()
    quote_len = len(stripped) - len(stripped.lstrip("> \t")) if in_quote else 0
    prefix_len = indent_len + quote_len
    at_block_level = prefix_len == 0

    body_part = line[prefix_len:]

    def repl(m: re.Match) -> str:
        # 仅当成对 $$ 独占整行（块级上下文）时保留块定界符，否则按行内处理
        if at_block_level and m.start() == 0 and body_part[m.end():].strip() == "":
            return m.group(0)
        return f"${m.group(1)}$"

    new_body = PAIR.sub(repl, body_part)
    return line[:prefix_len] + new_body


def fix_lines(lines: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    changed = 0
    in_fence = False
    in_math = False
    for line in lines:
        in_quote, body = split_line(line)
        if in_fence:
            out.append(line)
            if body.startswith("```") or body.startswith("~~~"):
                in_fence = False
            continue
        if body.startswith("```") or body.startswith("~~~"):
            in_fence = True
            out.append(line)
            continue
        if in_math:
            out.append(line)
            if body.endswith("$$"):
                in_math = False
            continue
        new_line = convert_line(line)
        if new_line != line:
            out.append(new_line)
            changed += 1
            # 转换后若行首仍是 $$ 且未闭合（罕见），保持原逻辑：按块处理
            _, new_body = split_line(new_line)
            if new_body.startswith("$$") and not (
                len(new_body) > 4 and new_body.endswith("$$") and "$$" not in new_body[2:-2]
            ):
                in_math = True
            continue
        out.append(line)
        if body.startswith("$$") and not (
            len(body) > 4 and body.endswith("$$") and "$$" not in body[2:-2]
        ):
            in_math = True
    return out, changed


def main() -> None:
    total_files = 0
    total = 0
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
                total += changed
    print(f"修改 {total_files} 个文件，转换 {total} 行的行中 $$ 对")


if __name__ == "__main__":
    sys.exit(main())
