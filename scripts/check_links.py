#!/usr/bin/env python3
"""校验 SUMMARY.md 全部条目 + 指定范围（新写章节/方向映射/导航）内相对链接的真实性。

范围外（各方向深层旧章）由 mkdocs 构建时的相对链接告警兜底；旧章里形如
`$x_k-x^*$` 的 LaTeX 括号会被朴素链接正则误报，不纳入本门禁。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def md_links(text):
    for m in re.finditer(r"\]\(([^)#\s]+\.md)\)", text):
        yield m.group(1)

def main():
    errors = []

    # 1) SUMMARY.md 条目
    summary = ROOT / "SUMMARY.md"
    for target in re.findall(r"\]\(([^)]+\.md)\)", summary.read_text(encoding="utf-8")):
        if not (ROOT / target).is_file():
            errors.append(f"SUMMARY 死链: {target}")

    # 2) 新写章节内部的相对 .md 链接与图片引用（范围：新目录 + 方向映射 + 导航）
    check_files = []
    for pat in [
        "01_数学/00_大学基础筑基/*.md",
        "02_C++基础与进阶/00_零基础入门/*.md",
        "02_C++基础与进阶/15_Python与工具链/*.md",
        "03_SLAM/00_零基础入门/*.md",
        "07_机器人学导论/*.md",
        "08_可视化实验室/*.md",
        "*/*方向_学习路径与教材映射.md",
        "00_项目导航/*.md",
        "README.md",
    ]:
        check_files.extend(ROOT.glob(pat))
    # 具身智能映射在 06 下，上面通配已覆盖（*/*方向…）
    seen = set()
    for f in check_files:
        if f in seen:
            continue
        seen.add(f)
        text = f.read_text(encoding="utf-8")
        links = [m.group(1) for m in re.finditer(r"\]\(([^)#\s]+)\)", text)]
        links += re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
        for link in links:
            if link.startswith("http"):
                continue
            resolved = (f.parent / link).resolve()
            if not resolved.is_file():
                errors.append(f"{f.relative_to(ROOT)} -> 死链: {link}")

    if errors:
        print(f"发现 {len(errors)} 个死链：")
        for e in errors:
            print("  " + e)
        sys.exit(1)
    print(f"校验通过：SUMMARY 条目 + {len(seen)} 个新文件的相对链接全部真实存在。")

if __name__ == "__main__":
    main()
