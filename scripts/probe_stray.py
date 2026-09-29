#!/usr/bin/env python3
"""探查构建页中剩余的游离 $ 上下文。"""
import re
import sys

html = open(sys.argv[1], encoding="utf-8").read()
pats = [r".{90}\$<span", r".{90}</span>\$</p>", r".{60}\$\$"]
for pat in pats:
    for m in list(re.finditer(pat, html))[:6]:
        seg = re.sub(r'<span class="arithmatex">', "AX", m.group(0))
        seg = re.sub(r"<div[^>]*>", "DIV", seg)
        seg = re.sub(r"</div>", "/DIV", seg)
        print(seg.replace("\n", "⏎")[-150:])
        print("---")
