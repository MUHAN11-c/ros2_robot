# -*- coding: utf-8 -*-
"""贴纸包拆解 v2：连通域分析（降采样 + 腐蚀断桥 + BFS 标记）。

思路：贴纸为不透明连通块；相邻贴纸间的细桥接像素用腐蚀打断。
在 1/4 分辨率上做 BFS 连通域（快），取包围盒回原分辨率后再按 alpha 精修边界。
输出：.generated/mascot_check/stickers2/<sheet>_<idx>.png + 带尺寸标注总览。
"""
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets" / "mascots" / "src"
OUT = ROOT / ".generated" / "mascot_check" / "stickers2"

SCALE = 4          # 降采样倍数
ERODE = 2          # 腐蚀半径（降采样坐标系）
MIN_AREA = 900     # 降采样坐标最小面积（≈ 原图 14400px）
MIN_SIDE = 60      # 原图最小边长


def erode(mask: np.ndarray, r: int) -> np.ndarray:
    """方形最小滤波（腐蚀），r 为半径。"""
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


def components(mask: np.ndarray):
    """BFS 连通域 → [(bbox x0,y0,x1,y1), ...]（降采样坐标）。"""
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
                    if cx < x0: x0 = cx
                    if cx > x1: x1 = cx
                    if cy < y0: y0 = cy
                    if cy > y1: y1 = cy
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                q.append((ny, nx))
                comps.append(((x0, y0, x1 + 1, y1 + 1), area))
    return comps


def refine_box(alpha_full: np.ndarray, box):
    """在原分辨率上按 alpha 精修边界（留 6px 余量）。"""
    x0, y0, x1, y1 = box
    sub = alpha_full[y0:y1, x0:x1]
    ys, xs = np.where(sub > 16)
    if len(ys) == 0:
        return None
    return (
        max(0, x0 + int(xs.min()) - 6),
        max(0, y0 + int(ys.min()) - 6),
        min(alpha_full.shape[1], x0 + int(xs.max()) + 7),
        min(alpha_full.shape[0], y0 + int(ys.max()) + 7),
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    all_items = []
    for sheet in sorted(SRC.glob("sakura-*.png")):
        im = Image.open(sheet).convert("RGBA")
        arr = np.array(im)
        alpha = arr[:, :, 3]
        if (alpha < 250).mean() < 0.05:
            # 白底图：以「非近白」为内容
            lum = arr[:, :, :3].astype(int).mean(axis=2)
            content = (lum < 240) | (alpha > 16)
        else:
            content = alpha > 60
        # 降采样
        small = content[::SCALE, ::SCALE]
        solid = erode(small.astype(bool), ERODE)
        comps = components(solid)
        picked = []
        for (bbox, area) in comps:
            if area < MIN_AREA:
                continue
            x0, y0, x1, y1 = [v * SCALE for v in bbox]
            fb = refine_box(alpha if (alpha < 250).mean() >= 0.05 else (arr[:, :, :3].astype(int).mean(axis=2) < 240).astype(int) * 255, (x0, y0, x1, y1))
            if fb is None:
                continue
            w, h = fb[2] - fb[0], fb[3] - fb[1]
            if w < MIN_SIDE or h < MIN_SIDE:
                continue
            if w / h > 3.0 or h / w > 3.0:
                continue  # 文字条
            picked.append(fb)
        # 按面积从大到小排序
        picked.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
        print(f"{sheet.stem}: {len(picked)} 个贴纸")
        for i, box in enumerate(picked):
            crop = im.crop(box)
            p = OUT / f"{sheet.stem}_{i:02d}.png"
            crop.save(p)
            all_items.append((f"{sheet.stem}_{i:02d}", crop))
    # 总览
    cols, tw = 8, 150
    rows_n = (len(all_items) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * (tw + 6), rows_n * (tw + 20)), (246, 244, 250))
    d = ImageDraw.Draw(canvas)
    for i, (name, crop) in enumerate(all_items):
        r, c = divmod(i, cols)
        x0, y0 = c * (tw + 6) + 3, r * (tw + 20) + 3
        th = crop.copy()
        th.thumbnail((tw, tw))
        canvas.paste(th, (x0 + (tw - th.width) // 2, y0 + (tw - th.height) // 2), th)
        d.text((x0, y0 + tw + 4), f"{i}:{name[-2:]}", fill=(120, 60, 120))
    canvas.save(OUT / "_contact.png")
    print(f"共 {len(all_items)} → {OUT}/_contact.png")


if __name__ == "__main__":
    main()
