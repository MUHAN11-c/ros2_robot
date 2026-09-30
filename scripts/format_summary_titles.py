# -*- coding: utf-8 -*-
"""SUMMARY.md 目录标题格式化（目录清晰化维护工具）。

规则（只改显示标题，不动文件名与链接目标）：
  1. 条目标题去掉纯数字排序前缀：`10_微积分I_...` → `微积分I_...`
  2. 子课程系列号保留但加分隔：`P01_URDF...` → `P01 · URDF...`（Ch/M/F/D/S/B/Deep/Survey 同）
  3. `README` 标题 → `导读`
  4. 分组标题去掉 `00_` 等前缀与「（原版）」维护标记，保留有用注记（如“27 章全序列”）
  5. 英文复合词按词典规范化（`Actor_Critic`→`Actor-Critic`、`MPC_WBC`→`MPC/WBC` 等），
     其余下划线统一替换为「 · 」：`指针_引用与内存模型` → `指针 · 引用与内存模型`

用法：
  python scripts/format_summary_titles.py --check   # 只报告需要改的行
  python scripts/format_summary_titles.py           # 写回 SUMMARY.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "SUMMARY.md"

ITEM_RE = re.compile(r"^(\s*)\*\s+\[([^\]]+)\]\(([^)]+)\)\s*$")
# 分组行：`* 组名`（无链接方括号）
GROUP_ITEM_RE = re.compile(r"^(\s*)\*\s+([^*\[]+?)\s*$")

# 纯数字排序前缀（条目与分组通用）
NUMERIC_PREFIX = re.compile(r"^\d+[_\-\s]+")
# 子课程系列号：P01 / M03 / F04 / D05 / S01 / S99 / B02 / Ch01 / Deep_D1 / Survey_D2 / P3-00
SERIES_PREFIX = re.compile(
    r"^(?P<tag>(?:Ch|P|M|F|D|S|B)\d+(?:-\d+)?|Deep_D\d+[a-z]?|Survey_D\d+[a-z]?|P3-\d+)"
    r"[_.\- ]+(?P<rest>.+)$"
)
# 幂等保护：已是「TAG · …」形态的不再重切（否则 P3-00 会被回溯切成 P3 · 00）
SERIES_ALREADY_SPLIT = re.compile(
    r"^(?:(?:Ch|P|M|F|D|S|B)\d+(?:-\d+)?|Deep_D\d+[a-z]?|Survey_D\d+[a-z]?|P3-\d+) · "
)

# 英文复合词：下划线处的规范写法各不相同（连字符/空格/斜杠），逐一给定；
# 其余下划线一律替换为「 · 」（列表内条目彼此无前缀包含关系）
COMPOUNDS = [
    ("Actor_Critic", "Actor-Critic"),
    ("Diffusion_Models", "Diffusion Models"),
    ("Certifiable_Perception", "Certifiable Perception"),
    ("Ceres_Solver", "Ceres Solver"),
    ("Barrau_Bonnabel", "Barrau-Bonnabel"),
    ("Privileged_Learning", "Privileged Learning"),
    ("Motion_Imitation", "Motion Imitation"),
    ("Mobile_ALOHA", "Mobile ALOHA"),
    ("UMI_on_Legs", "UMI on Legs"),
    ("Perceptive_MPC", "Perceptive MPC"),
    ("Deep_WBC", "Deep WBC"),
    ("Visual_WBC", "Visual WBC"),
    ("ASAP_SimToReal", "ASAP SimToReal"),
    ("VLA_Foundation_Model", "VLA Foundation Model"),
    ("OCS2_mobile_manipulator", "OCS2 mobile manipulator"),
    ("Wheel_Legged_Gym_RL", "Wheel-Legged-Gym · RL"),
    ("Swiss_Mile", "Swiss-Mile"),
    ("SO3_SE3", "SO3/SE3"),
    ("PCL_OpenCV", "PCL/OpenCV"),
    ("Apollo_Autoware", "Apollo/Autoware"),
    ("QP_NLP", "QP/NLP"),
    ("MPC_WBC", "MPC/WBC"),
    ("MPC_RL", "MPC/RL"),
    ("URDF_Xacro", "URDF/Xacro"),
    ("MoveIt2_MTC", "MoveIt2/MTC"),
    ("MJCF_USD", "MJCF/USD"),
    ("Appendix_A3", "Appendix A3"),
    ("Appendix_B3", "Appendix B3"),
    ("Appendix_C3", "Appendix C3"),
    ("Appendix_A", "Appendix A"),
    ("Appendix_B", "Appendix B"),
    ("Appendix_C", "Appendix C"),
    ("Deep_D", "Deep D"),
    ("Survey_D", "Survey D"),
]


def clean_title(title: str) -> str:
    if title == "README":
        return "导读"
    title = NUMERIC_PREFIX.sub("", title)
    if not SERIES_ALREADY_SPLIT.match(title):
        m = SERIES_PREFIX.match(title)
        if m:
            title = f"{m.group('tag')} · {m.group('rest')}"
    # 「（原版…）」维护标记：去掉“原版”，保留其余注记
    title = re.sub(r"（原版，\s*([^）]*)）", r"（\1）", title)
    title = title.replace("（原版）", "").strip()
    # 复合词按词典规范化，剩余下划线统一为「 · 」
    for old, new in COMPOUNDS:
        title = title.replace(old, new)
    title = title.replace("_", " · ").strip()
    return title or title


def main() -> None:
    check_only = "--check" in sys.argv
    lines = SUMMARY.read_text(encoding="utf-8").splitlines()
    changed = 0
    for i, line in enumerate(lines):
        m = ITEM_RE.match(line)
        gm = GROUP_ITEM_RE.match(line) if not m else None
        if m:
            new = clean_title(m.group(2))
        elif gm:
            new = clean_title(gm.group(2))
        else:
            continue
        old = m.group(2) if m else gm.group(2)  # type: ignore[union-attr]
        if new != old:
            changed += 1
            prefix = "  DRY " if check_only else "  FIX "
            print(f"{prefix}L{i + 1}: {old}  →  {new}")
            if not check_only and m:
                lines[i] = f"{m.group(1)}* [{new}]({m.group(3)})"
            elif not check_only and gm:
                lines[i] = f"{gm.group(1)}* {new}"
    if not check_only and changed:
        SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"共 {changed} 处标题调整" + ("（未写入）" if check_only else ""))


if __name__ == "__main__":
    main()
