#!/usr/bin/env python3
"""按 sources/*.mmd（已换新色板）重渲染全部 mermaid 图，输出文件名沿用 mermaid_cache.json 记录。"""
import json
import subprocess
from pathlib import Path

LABS = Path(__file__).resolve().parent
ROOT = LABS.parents[1]
DIAGRAMS = ROOT / "assets" / "labs" / "diagrams"
PPCFG = LABS / "pp.json"
MMDC = LABS / "node_modules" / ".bin" / "mmdc.cmd"
CACHE = LABS / "mermaid_cache.json"


def render(src: str, out_svg: Path) -> None:
    tmp = LABS / "_tmp.mmd"
    tmp.write_text(src, encoding="utf-8")
    subprocess.run(
        [str(MMDC), "-i", str(tmp), "-o", str(out_svg), "-p", str(PPCFG), "-b", "white"],
        check=True, capture_output=True, text=True,
    )
    import re
    svg = out_svg.read_text(encoding="utf-8")
    m = re.search(r'viewBox="[\d.eE+-]+ [\d.eE+-]+ ([\d.eE+-]+) ([\d.eE+-]+)"', svg)
    if m:
        w, h = float(m.group(1)), float(m.group(2))
        svg = re.sub(r'<svg ([^>]*?)width="100%"', rf'<svg \1width="{w:.0f}" height="{h:.0f}"', svg, count=1)
        svg = re.sub(r'(<svg [^>]*?)style="[^"]*"', r"\1", svg, count=1)
        svg = re.sub(r"max-width:\s*[\d.]+px", "max-width:100%", svg, count=1)
        out_svg.write_text(svg, encoding="utf-8")


def main() -> None:
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    for mmd in sorted(LABS.glob("sources/*.mmd")):
        key = mmd.stem.split("_")[-1]
        fname = cache.get(key)
        if not fname:
            print(f"  跳过（缓存无记录）: {mmd.name}")
            continue
        render(mmd.read_text(encoding="utf-8"), DIAGRAMS / fname)
        print(f"  ✓ {fname}")
    print("全部完成。")


if __name__ == "__main__":
    main()
