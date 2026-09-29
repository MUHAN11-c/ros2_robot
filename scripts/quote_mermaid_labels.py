#!/usr/bin/env python3
"""把 08_可视化实验室 下所有 mermaid 块的节点标签统一加双引号（幂等）。"""
import re
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "08_可视化实验室"


def normalize_line(line: str) -> str:
    if line.strip().startswith(("%%", "flowchart", "style", "subgraph", "end")) or "--" not in line and "-->" not in line:
        # 无节点定义的行原样保留
        if not re.search(r"\w+(\(\[|\[\/|\[|\{)", line):
            return line

    def requ(m):
        head, inner, tail = m.group(1), m.group(2), m.group(3)
        inner = inner.strip()
        if inner.startswith('"') and inner.endswith('"'):
            return m.group(0)
        return f'{head}"{inner}"{tail}'

    # 平行四边形 [/ ... /]
    line = re.sub(r"(\w+\[\/)(.*?)(\/\])", requ, line)
    # stadium ([ ... ])
    line = re.sub(r"(\w+\(\[)(.*?)(\]\))", requ, line)
    # 菱形 { ... }（不含已引用）
    line = re.sub(r"(\w+\{)([^\"{}].*?)(\})", requ, line)
    # 普通矩形 [ ... ]（非 [/，非已引用）
    line = re.sub(r"(\w+\[)(?!\/)([^\"\[].*?)(\])", requ, line)
    return line


def fix_text(text: str) -> str:
    def block_repl(m):
        body = m.group(1)
        lines = []
        for ln in body.splitlines(keepends=True):
            if ln.strip().startswith(("%%", "flowchart", "style")):
                lines.append(ln)
            else:
                lines.append(normalize_line(ln))
        return "```mermaid\n" + "".join(lines) + "```"
    return re.sub(r"```mermaid\n(.*?)```", block_repl, text, flags=re.S)


changed = 0
for p in sorted(DIR.glob("*.md")):
    text = p.read_text(encoding="utf-8")
    new = fix_text(text)
    if new != text:
        p.write_text(new, encoding="utf-8")
        changed += 1
        print(f"已规范化: {p.name}")
print(f"共修改 {changed} 个文件")
