# -*- coding: utf-8 -*-
"""贴纸包拆解：从 4 张贴纸素材图中自动提取单个贴纸。

原理：贴纸网格的行/列之间存在透明（RGBA）或近白（RGB）沟槽，
对 alpha / 亮度做行列投影即可定位网格线；每格再按内容 bbox 收紧。
输出：.generated/mascot_check/stickers/<sheet>_<idx>.png + 总览拼图。
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets" / "mascots" / "src"
OUT = ROOT / ".generated" / "mascot_check" / "stickers"


def find_bands(profile: np.ndarray, min_block=80):
    """自适应阈值：低于 内容行不透明度中位数 30%（且 <15% 绝对值）视为沟槽。"""
    n = len(profile)
    prof = np.asarray(profile, dtype=float)
    prof = prof / (prof.max() + 1e-9)
    nz = prof[prof > 0.05]
    if len(nz) == 0:
        return []
    thr = min(0.32 * float(np.median(nz)), 0.15)
    mask = prof > thr
    # 平滑：3px 均值卷积去毛刺
    kernel = np.ones(5) / 5
    sm = np.convolve(prof, kernel, mode="same") > thr
    mask = mask | sm
    bands = []
    start = None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            if i - start >= min_block:
                bands.append((start, i))
            start = None
    if start is not None and n - start >= min_block:
        bands.append((start, n))
    return bands


def extract(sheet: Path):
    im = Image.open(sheet)
    has_alpha = im.mode == "RGBA"
    arr = np.array(im.convert("RGBA"))
    alpha = arr[:, :, 3].astype(int)
    if has_alpha and (alpha < 250).mean() > 0.05:
        # 透明背景：用 alpha 投影
        rows = (alpha > 16).sum(axis=1)
        cols = (alpha > 16).sum(axis=0)
        row_bands = find_bands(rows)
        col_bands = find_bands(cols)
    else:
        # 白背景：用亮度投影（近白为沟槽）
        rgb = arr[:, :, :3].astype(int)
        lum = rgb.mean(axis=2)
        # 白底：内容 = 非近白占比
        content_rows = 1.0 - (lum > 244).mean(axis=1)
        content_cols = 1.0 - (lum > 244).mean(axis=0)
        row_bands = find_bands(content_rows)
        col_bands = find_bands(content_cols)

    stickers = []
    for ri, (y0, y1) in enumerate(row_bands):
        for ci, (x0, x1) in enumerate(col_bands):
            cell = arr[y0:y1, x0:x1]
            a = cell[:, :, 3]
            if (a > 16).sum() < 2000:  # 空格
                continue
            # 内容 bbox（alpha 收紧）
            ys, xs = np.where(a > 16)
            if len(ys) == 0:
                continue
            cy0, cy1 = ys.min(), ys.max() + 1
            cx0, cx1 = xs.min(), xs.max() + 1
            w, h = cx1 - cx0, cy1 - cy0
            # 过滤文字碎片/过小格
            if w < 80 or h < 80 or w * h < 12000:
                continue
            # 宽高比过扁的通常是文字条
            if w / h > 2.6 or h / w > 2.6:
                continue
            stickers.append({
                "name": f"{sheet.stem}_{ri}{ci}",
                "box": (x0 + int(cx0), y0 + int(cy0), x0 + int(cx1), y0 + int(cy1)),
                "size": (w, h),
            })
    return im.convert("RGBA"), stickers


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    all_crops = []
    for sheet in sorted(SRC.glob("sakura-*.png")):
        im, stickers = extract(sheet)
        print(f"{sheet.stem}: 网格提取 {len(stickers)} 个贴纸")
        for s in stickers:
            crop = im.crop(s["box"])
            p = OUT / f"{s['name']}.png"
            crop.save(p)
            all_crops.append((s["name"], crop, s["size"]))
    # 总览拼图（160px 缩略，带编号）
    cols = 8
    tile, label_h = 160, 18
    rows_n = (len(all_crops) + cols - 1) // cols
    sheet_img = Image.new("RGB", (cols * (tile + 6), rows_n * (tile + label_h + 6)), (250, 248, 253))
    d = ImageDraw.Draw(sheet_img)
    for i, (name, crop, size) in enumerate(all_crops):
        r, c = divmod(i, cols)
        x0, y0 = c * (tile + 6) + 3, r * (tile + label_h + 6) + 3
        th = crop.copy()
        th.thumbnail((tile, tile))
        sheet_img.paste(th, (x0 + (tile - th.width) // 2, y0 + (tile - th.height) // 2), th)
        d.text((x0, y0 + tile + 2), f"{i}:{name.split('_')[-1]}", fill=(120, 60, 120))
    sheet_img.save(OUT / "_contact.png")
    print(f"共 {len(all_crops)} 个贴纸 → {OUT}/_contact.png")


if __name__ == "__main__":
    main()
