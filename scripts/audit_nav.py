#!/usr/bin/env python3
"""内容完整性巡检：导航 ↔ 页面双向覆盖 + 子目录章节编号连续性。

在 scripts/sync_docs.py 之后运行（读取 mkdocs.generated.yml 与 .generated/docs/）：
1. 孤儿页——已构建但未进入导航的页面（应为 0，否则 SUMMARY.md 缺条目或混入内部文档）；
2. 编号间隔/重复——子目录内章节序号跳档（10 步留白属惯例，仅示警不作死链门禁）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / ".generated" / "docs"
GEN = ROOT / "mkdocs.generated.yml"


def walk_nav(node, out: list[str]) -> None:
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for item in node:
            walk_nav(item, out)
    elif isinstance(node, dict):
        for v in node.values():
            walk_nav(v, out)


def main() -> int:
    if not GEN.exists() or not DOCS.exists():
        print("请先运行 scripts/sync_docs.py 生成 mkdocs.generated.yml 与 .generated/docs/")
        return 1

    cfg = yaml.load(GEN.read_text(encoding="utf-8"), Loader=yaml.Loader)
    nav_targets: list[str] = []
    walk_nav(cfg.get("nav", []), nav_targets)
    nav_set = set(nav_targets)

    skip = {"index.md", "catalog.md", "project.md", "404.md"}
    pages = [
        md.relative_to(DOCS).as_posix()
        for md in sorted(DOCS.rglob("*.md"))
        if md.relative_to(DOCS).as_posix() not in skip
    ]
    orphans = [rel for rel in pages if rel not in nav_set]

    print(f"nav entries: {len(nav_targets)}")
    print(f"docs pages (excl. home/catalog/project/404): {len(pages)}")
    print(f"orphan pages (built but NOT in nav): {len(orphans)}")
    for rel in orphans:
        print(f"  - {rel}")

    print("\n=== chapter numbering gaps per directory (10-step spacing is normal) ===")
    for top in sorted(p for p in ROOT.iterdir() if p.is_dir() and re.match(r"^\d\d_", p.name)):
        for sub in sorted(top.rglob("*")):
            if not sub.is_dir():
                continue
            nums = []
            for f in sub.glob("*.md"):
                m = re.match(r"^(\d+)[_\-]", f.name)
                if m:
                    nums.append(int(m.group(1)))
            if len(nums) < 2:
                continue
            nums.sort()
            gaps = []
            prev = nums[0]
            for n in nums[1:]:
                if n > prev + 1:
                    gaps.append(f"{prev}->{n}")
                prev = n
            dups = sorted({n for n in nums if nums.count(n) > 1})
            if gaps or dups:
                print(f"{top.name}/{sub.name}: gaps={gaps or '-'} dups={dups or '-'}")

    return 1 if orphans else 0


if __name__ == "__main__":
    sys.exit(main())
