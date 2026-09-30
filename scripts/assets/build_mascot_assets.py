# -*- coding: utf-8 -*-
"""樱机实验室 · 吉祥物素材库构建 v3（贴纸包全量版）。

素材源 assets/mascots/src/sakura-01..04.png 为贴纸包（3×4 网格、12 贴/包）。
三层提取策略：
  1) 连通域自动提取（透明沟槽版式的 02/03 号包效果好，04 号部分粘连）
  2) 3×4 网格整包裁剪 GRID_CROPS（g{包}-r{格}）：01 号白底包全量 + 04 号粘连格的干净版
  3) 旧版手工标定 MANUAL_CROPS 兼容保留

装配命名素材（CONFIG）：
  hero/tip/404/complete   首页 hero / 提示卡 / 404 / 章末完成卡
  mod-* ×9                模块入口页章节头（96px 方形 cover 裁剪）
  step-* ×3               首页「开始学习」三步骤卡图标
  panel-* / thanks / sleep / kmap-guide   助手面板 / 页脚 / 目录 / 知识主线
  avatar-512/128/64.webp + favicon + apple-touch-icon   头像（hero 贴纸脸区裁剪）

体积门禁：hero/404 ≤200KB，tip ≤120KB，avatar 按档 ≤80/20/8KB，池内单贴 ≤10KB。
"""
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets" / "mascots" / "src"
OUT = ROOT / "assets" / "mascots"

# 装配配置：命名素材 ← 提取贴纸名（gXX-rN 为网格裁剪名，见 GRID_CROPS）
CONFIG = {
    "hero": "sakura-02_01",
    "tip": "sakura-02_04",
    "404": "sakura-02_03",
    "complete": "sakura-02_00",
    # 模块入口页章节头贴纸（44px 方形 cover 裁剪）——四张贴纸包全部在用：
    # 01 号（白底）与 04 号粘连格经网格裁剪标定；其余走连通域提取
    "mod-route": "sakura-02_02",   # 00 学习路线总图（02 号包 · 指点教学）
    "mod-math": "sakura-02_07",    # 01 数学（02 号包 · 认真讲授）
    "mod-cpp": "sakura-02_08",     # 02 C++（02 号包 · 敬礼）
    "mod-slam": "sakura-03_03",    # 03 SLAM（03 号包 · 竖大拇指）
    "mod-plan": "manual-01-11",    # 04 规控（01 号包 · 竖大拇指，旧标定）
    "mod-ctrl": "sakura-02_11",    # 05 运控（02 号包）
    "mod-emb": "g04-r6",           # 06 具身（04 号包 · 白板讲解，旧 04_07 为粘连块）
    "mod-intro": "sakura-02_06",   # 07 导论（02 号包 · 比心）
    "mod-lab": "sakura-02_05",     # 08 可视化实验室（02 号包）
    # —— 全站图标化落位（首页三步 / 助手面板 / 页脚 / 目录 / 知识主线）——
    "step-start": "g04-r3",        # 敬礼「跟我来」→ 首页·第一步 打地基
    "step-lab": "g04-r7",          # 竖大拇指 → 首页·第二步 边学边练
    "step-adv": "g04-r2",          # 持地图指路 → 首页·第三步 冲进深水区
    "panel-hero": "g01-r10",       # 咨询讲解 → 助手面板头部
    "panel-coffee": "sakura-03_01",# 端咖啡 → 助手面板底部
    "thanks": "g04-r9",            # 深鞠躬 → 页脚感谢条
    "sleep": "g04-r0",             # 躺机器人腿上睡 → 目录「静待绽放」
    "kmap-guide": "sakura-02_06",  # 比心讲解 → 首页·知识主线点缀
}
AVATAR_FROM = "sakura-02_01"

# 旧版手工标定（01 号包，坐标据 12 格对照图标定）
MANUAL_CROPS = {
    "manual-01-11": ("sakura-01.png", (390, 410, 710, 730)),
}


def _grid_sheet(sheet: str):
    """3×4 网格（行主序 r0..r11），格内四边各缩 6px 防相邻串色。"""
    im = Image.open(SRC / sheet).convert("RGBA")
    W, H = im.size
    cw, ch = W / 3, H / 4
    pad = 6
    return {
        f"g{sheet[7:9]}-r{i}": im.crop((
            round(cw * (i % 3)) + pad,
            round(ch * (i // 3)) + pad,
            round(cw * (i % 3 + 1)) - pad,
            round(ch * (i // 3 + 1)) - pad,
        ))
        for i in range(12)
    }


# 网格整包裁剪：01 号包（白底，连通域失效，全 12 格）+ 04 号包（含粘连格的干净版）。
# 白底在导出贴纸池时经 strip_white_bg 转透明。
GRID_CROPS = {**_grid_sheet("sakura-01.png"), **_grid_sheet("sakura-04.png")}

MOD_PREFIX = "mod-"  # 模块贴纸导出为 96px 方形 cover 裁剪

# 贴纸池排除名单：连通域提取中粘连成块或带暗边残缺的（对应干净版已由网格裁剪提供）
POOL_DENY = {
    "sakura-03_00",  # 腿部特写 + 站立全身 两贴粘连
    "sakura-03_02",  # 带粗暗边的残块
    "sakura-03_11",  # 带粗暗边的残块
    "sakura-04_01",  # 白板讲解 + 比心 两贴粘连
    "sakura-04_02",  # 敬礼 + 竖大拇指 两贴粘连
    "sakura-02_09",  # 两人粘连块
    "sakura-04_04",  # 与相邻元素粘连（干净版 g04-r3）
    "sakura-04_05",  # 与相邻元素粘连（干净版 g04-r2）
    "sakura-04_06",  # 与相邻元素粘连（干净版 g04-r7）
    "g01-r11",       # 网格裁剪右缘白条残留
}

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


def strip_white_bg(im: Image.Image) -> Image.Image:
    """白底贴纸包（01 号）专用：把与裁剪边缘连通的近白像素转为透明。

    只泛洪"从边缘可达"的白色，贴纸内部被线条包住的白色高光不受影响；
    在降采样图上做 BFS，掩码放大回原尺寸。
    """
    small = im.copy()
    small.thumbnail((448, 448), Image.LANCZOS)
    arr = np.array(small)
    if arr[:, :, 3].min() < 250:  # 已带透明通道（透明沟槽版式），无需处理
        return im
    lum = arr[:, :, :3].astype(int).mean(axis=2)
    near_white = lum > 238
    h, w = near_white.shape
    seen = np.zeros_like(near_white, dtype=bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if near_white[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if near_white[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    while q:
        cy, cx = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and near_white[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    mask = Image.fromarray((seen * 255).astype(np.uint8), "L").resize(im.size, Image.BILINEAR)
    out = np.array(im.convert("RGBA"))
    out[:, :, 3] = np.where(np.array(mask) > 127, 0, out[:, :, 3])
    return Image.fromarray(out, "RGBA")


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
    # 2a) 网格整包裁剪（01 白底包全量 + 04 号包），并按非白内容收紧 bbox
    for gname, gcrop in GRID_CROPS.items():
        arr = np.array(gcrop)
        lum = arr[:, :, :3].astype(int).mean(axis=2)
        ys, xs = np.where(lum < 235)
        if len(ys) > 500:
            gcrop = gcrop.crop((
                max(0, int(xs.min()) - 6), max(0, int(ys.min()) - 6),
                min(gcrop.width, int(xs.max()) + 7), min(gcrop.height, int(ys.max()) + 7),
            ))
        stickers[gname] = gcrop
    print(f"grid: 01/04 号包网格裁剪 {len(GRID_CROPS)} 格")
    # 2b) 旧版手动裁剪（非白 bbox 收紧）
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
        if src_name.startswith("g01"):  # 白底包命名导出同样去白底
            im = strip_white_bg(im)
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
    # 只收干净单贴：宽松长宽比（0.45-2.2，纳入鞠躬/敬礼等长条姿态）、排除小杂质；
    # 已知粘连块/带暗边残块（连通域提取的合并对）显式排除
    clean = [
        (name, crop) for name, crop in stickers.items()
        if name not in POOL_DENY
        and 0.45 <= crop.width / crop.height <= 2.2
        and min(crop.size) >= 120
    ]
    keep = set()
    for name, crop in clean:
        th = strip_white_bg(crop) if name.startswith(("g01", "sakura-01")) else crop.copy()
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

    # 5) 未利用清单：既没被命名引用、也没进贴纸池的提取结果
    pool_names = {Path(f).stem for f in keep}
    named = set(CONFIG.values()) | {AVATAR_FROM}
    leftovers = sorted(set(stickers) - pool_names - named)
    print(f"  未利用贴纸 {len(leftovers)} 枚：{', '.join(leftovers) or '无'}")


if __name__ == "__main__":
    main()
