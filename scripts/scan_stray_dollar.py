#!/usr/bin/env python3
"""统计构建产物中「游离 $ 紧贴 arithmatex span」的伪影分布。"""
import re
from pathlib import Path

site = Path(__file__).resolve().parent.parent / "site"
pat_open = re.compile(r'(?:^|：|。|\n)\$<span class="arithmatex">', re.MULTILINE)
pat_close = re.compile(r'</span>\$</p>')

hits = {}
for p in site.rglob("index.html"):
    html = p.read_text(encoding="utf-8")
    n = len(pat_open.findall(html)) + len(pat_close.findall(html))
    if n:
        hits[str(p.relative_to(site))] = n

total = sum(hits.values())
print(f"受影响页面数: {len(hits)}, 游离$总数: {total}")
for k, v in sorted(hits.items(), key=lambda x: -x[1])[:15]:
    print(f"  {v:3d}  {k}")
