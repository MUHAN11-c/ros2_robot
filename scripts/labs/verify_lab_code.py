# -*- coding: utf-8 -*-
"""实验室代码本地测试门禁：提取 11 个实验室页的全部 ```python 代码块，
逐块在 MPLBACKEND=Agg 子进程中运行（超时 60s）。

规范要求：写在教程里的代码必须先本地跑通（「抄一遍再跑」承诺）。
任何块失败即退出码 1。用法：
  .venv/Scripts/python scripts/labs/verify_lab_code.py [lab名…]
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABS = ROOT / "08_可视化实验室"
PY = sys.executable

BLOCK_RE = re.compile(r"```python\n(.*?)```", re.S)
# 允许跳过显式标注为片段的块（块内首行注释含「片段」或「示意」）
FRAGMENT_HINTS = ("片段", "示意", "伪代码")


def lab_files(only=None):
    files = sorted(LABS.glob("lab*.md"))
    if only:
        files = [f for f in files if any(o in f.name for o in only)]
    return files


def run_block(idx: int, code: str):
    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8", dir=tempfile.gettempdir()
    ) as fp:
        fp.write(code)
        path = fp.name
    env = dict(os.environ)
    env["MPLBACKEND"] = "Agg"
    env["MPLCONFIGDIR"] = tempfile.gettempdir()
    try:
        r = subprocess.run(
            [PY, path],
            capture_output=True,
            timeout=60,
            env=env,
            cwd=str(ROOT),
        )
        out = ((r.stderr or b"") + b"\n" + (r.stdout or b"")).decode("utf-8", "replace")
        return r.returncode, out.strip()[-600:]
    except subprocess.TimeoutExpired:
        return -1, "超时（>60s）"
    finally:
        Path(path).unlink(missing_ok=True)


def main():
    only = sys.argv[1:] or None
    total = failed = 0
    for f in lab_files(only):
        code_blocks = BLOCK_RE.findall(f.read_text(encoding="utf-8"))
        lab_failed = []
        for bi, code in enumerate(code_blocks, 1):
            first = code.strip().splitlines()[0] if code.strip() else ""
            if any(h in first for h in FRAGMENT_HINTS):
                continue
            total += 1
            rc, err = run_block(bi, code)
            if rc != 0:
                failed += 1
                lab_failed.append((bi, rc, err))
        status = "PASS" if not lab_failed else f"FAIL({len(lab_failed)})"
        print(f"{f.name:<36} {len(code_blocks):>2} 块  {status}")
        for bi, rc, err in lab_failed:
            print(f"  ── 块 {bi} (rc={rc}): {err[:300]}")
    print(f"\n合计：{total} 块，失败 {failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
