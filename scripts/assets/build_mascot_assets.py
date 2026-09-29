# -*- coding: utf-8 -*-
"""樱机实验室 · 吉祥物素材库构建 v2（贴纸包版）。

素材源 assets/mascots/src/sakura-01..04.png 为贴纸包（网格布局、约 12 贴/包），
先连通域提取单个贴纸，再装配命名素材：

  hero.webp      首页 hero 大图（sakura-02_00，原生 ~360px）
  tip.webp       提示卡贴纸（sakura-03_00）
  404.webp       404 页贴纸（sakura-04_00）
  avatar-512/128/64.webp + favicon + apple-touch-icon   头像（hero 贴纸上部脸区裁剪）

体积门禁：hero/404 ≤200KB，tip ≤120KB，avatar 按档 ≤80/20/8KB。
"""
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets" / "mascots" / "src"
OUT = ROOT / "assets" / "mascots"

# 装配配置：命名素材 ← 提取贴纸名
CONFIG = {
    "hero": "sakura-02_01",
    "tip": "sakura-02_04",
    "404": "sakura-02_03",
    "complete": "sakura-02_00",
    # 模块入口页章节头贴纸（44px 方形 cover 裁剪）——四张贴纸包全部在用：
    # 01 号（白底）经 MANUAL_CROPS 手动标定；02/03/04 号走连通域提取
    "mod-route": "sakura-02_02",   # 00 学习路线总图（02 号包）
    "mod-math": "sakura-02_07",    # 01 数学（02 号包）
    "mod-cpp": "sakura-02_08",     # 02 C++（02 号包）
    "mod-slam": "sakura-03_03",    # 03 SLAM（03 号包）
    "mod-plan": "manual-01-11",    # 04 规控（01 号包手动裁剪）
    "mod-ctrl": "sakura-02_11",    # 05 运控（02 号包）
    "mod-emb": "sakura-04_07",     # 06 具身（04 号包）
    "mod-intro": "sakura-02_06",   # 07 导论（02 号包）
    "mod-lab": "sakura-02_05",     # 08 可视化实验室（02 号包）
}
AVATAR_FROM = "sakura-02_01"

# 01 号包为白底无沟槽版式，连通域失效——按下述网格手框（据 12 格对照图标定）
MANUAL_CROPS = {
    "manual-01-11": ("sakura-01.png", (390, 410, 710, 730)),
}

MOD_PREFIX = "mod-"  # 模块贴纸导出为 96px 方形 cover 裁剪

SCALE = 4
ERODE = 2
MIN_AREA = 900
MIN_SIDE = 60


def erode(mask, r):
    if r <= 0:
        return mask
    h, w = mask.shape
    m = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy == 0 and dx == 0:
                continue
            shifted = np.zeros_like(mask)
            ys0, ys1 = max(0, dy), h + min(0, dy)
            xs0, xs1 = max(0, dx), w + min(0, dx)
            shifted[ys0:ys1, xs0:xs1] = mask[max(0, -dy):h - max(0, dy) or h,
                                             max(0, -dx):w - max(0, dx) or w]
            m &= shifted
    return m


def components(mask):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps = []
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                q = deque([(y, x)])
                seen[y, x] = True
                x0, y0, x1, y1 = x, y, x, y
                area = 0
                while q:
                    cy, cx = q.popleft()
                    area += 1
                    x0, y0, x1, y1 = min(x0, cx), min(y0, cy), max(x1, cx), max(y1, cy)
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                q.append((ny, nx))
                comps.append(((x0, y0, x1 + 1, y1 + 1), area))
    return comps


def extract_stickers(im: Image.Image):
    """返回按面积降序的贴纸 PIL 图列表。"""
    arr = np.array(im)
    alpha = arr[:, :, 3]
    if (alpha < 250).mean() >= 0.05:
        content = alpha > 60
        ref = alpha
    else:
        lum = arr[:, :, :3].astype(int).mean(axis=2)
        content = lum < 240
        ref = (lum < 240).astype(int) * 255
    small = content[::SCALE, ::SCALE]
    solid = erode(small.astype(bool), ERODE)
    picked = []
    for bbox, area in components(solid):
        if area < MIN_AREA:
            continue
        x0, y0, x1, y1 = [v * SCALE for v in bbox]
        sub = ref[y0:y1, x0:x1]
        ys, xs = np.where(sub > 16)
        if len(ys) == 0:
            continue
        fb = (
            max(0, x0 + int(xs.min()) - 6),
            max(0, y0 + int(ys.min()) - 6),
            min(arr.shape[1], x0 + int(xs.max()) + 7),
            min(arr.shape[0], y0 + int(ys.max()) + 7),
        )
        w, h = fb[2] - fb[0], fb[3] - fb[1]
        if w < MIN_SIDE or h < MIN_SIDE or w / h > 3.0 or h / w > 3.0:
            continue
        picked.append(im.crop(fb))
    picked.sort(key=lambda c: c.width * c.height, reverse=True)
    return picked


def save_webp(im: Image.Image, path: Path, limit: int, start_q: int = 90) -> None:
    q = start_q
    while True:
        im.save(path, "WEBP", quality=q, method=6)
        if path.stat().st_size <= limit or q <= 62:
            break
        q -= 6
    print(f"  {path.name:<22} {im.width}x{im.height}  q={q}  {path.stat().st_size / 1024:.0f}KB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # 1) 提取
    stickers = {}
    for sheet in sorted(SRC.glob("sakura-*.png")):
        im = Image.open(sheet).convert("RGBA")
        crops = extract_stickers(im)
        for i, crop in enumerate(crops):
            stickers[f"{sheet.stem}_{i:02d}"] = crop
        print(f"{sheet.stem}: 提取 {len(crops)} 贴")
    # 2) 装配命名素材
    print("[装配]")
    # 01 号包手动裁剪（非白 bbox 收紧）
    for mname, (sheet_name, box) in MANUAL_CROPS.items():
        im = Image.open(SRC / sheet_name).convert("RGBA")
        crop = im.crop(box)
        lum = np.array(crop)[:, :, :3].astype(int).mean(axis=2)
        ys, xs = np.where(lum < 235)
        if len(ys) > 500:
            crop = crop.crop((
                max(0, int(xs.min()) - 6), max(0, int(ys.min()) - 6),
                min(crop.width, int(xs.max()) + 7), min(crop.height, int(ys.max()) + 7),
            ))
        stickers[mname] = crop
        print(f"manual: {mname} ← {sheet_name}{box} → {crop.size}")

    for name, src_name in CONFIG.items():
        assert src_name in stickers, f"{src_name} 不在提取结果中"
        im = stickers[src_name]
        if name.startswith(MOD_PREFIX):
            # 模块贴纸：96px 方形 cover 裁剪（章节头 44px 显示，2x 余量）
            w, h = im.size
            side = min(w, h)
            sq = im.crop(((w - side) // 2, (h - side) // 2,
                          (w + side) // 2, (h + side) // 2))
            sq = sq.resize((96, 96), Image.LANCZOS)
            save_webp(sq, OUT / f"{name}.webp", 30 * 1024)
        else:
            save_webp(im, OUT / f"{name}.webp",
                      200 * 1024 if name != "tip" else 120 * 1024)
    # 3) 头像：hero 贴纸上部中心脸区
    hero = stickers[AVATAR_FROM]
    w, h = hero.size
    side = int(min(w, h * 0.66))
    cx = w // 2
    face = hero.crop((cx - side // 2, int(h * 0.05), cx - side // 2 + side, int(h * 0.05) + side))
    for size, limit in ((512, 80 * 1024), (128, 20 * 1024), (64, 8 * 1024)):
        a = face.resize((size, size), Image.LANCZOS)
        save_webp(a, OUT / f"avatar-{size}.webp", limit, start_q=92)
    # 4) 贴纸池（干净单贴导出，供点击反应随机调用）
    pool = OUT / "pool"
    pool.mkdir(exist_ok=True)
    # 只收干净单贴：近方形（0.62-1.5）、足够大（排除整包合并块/文字条/合并对）
    clean = [
        (name, crop) for name, crop in stickers.items()
        if not name.startswith("manual")
        and 0.62 <= crop.width / crop.height <= 1.5
        and min(crop.size) >= 140
    ]
    keep = set()
    for name, crop in clean:
        th = crop.copy()
        th.thumbnail((112, 112), Image.LANCZOS)
        save_webp(th, pool / f"{name}.webp", 10 * 1024)
        keep.add(f"{name}.webp")
    # 清理陈旧文件（过滤规则变化后不再入选的）
    for old_file in pool.glob("*.webp"):
        if old_file.name not in keep:
            old_file.unlink()
    (pool / "manifest.json").write_text(json.dumps(sorted(keep)), encoding="utf-8")
    print(f"  贴纸池 {len(keep)} 张 → assets/mascots/pool/")

    fav = Image.new("RGBA", (64, 64), (25, 22, 30, 255))
    fav.alpha_composite(face.resize((64, 64), Image.LANCZOS))
    fav.convert("RGB").save(OUT / "favicon.png")
    apple = Image.new("RGBA", (180, 180), (25, 22, 30, 255))
    apple.alpha_composite(face.resize((180, 180), Image.LANCZOS))
    apple.convert("RGB").save(OUT / "apple-touch-icon.png")
    print("  favicon.png / apple-touch-icon.png 已派生")


if __name__ == "__main__":
    main()
