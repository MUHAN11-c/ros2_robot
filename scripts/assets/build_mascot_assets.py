# -*- coding: utf-8 -*-
"""樱机实验室 · 吉祥物素材库构建脚本。

输入：assets/mascots/src/sakura-01..04.png（1122x1402 原始档）
输出（assets/mascots/）：
  - sakura-01..04.webp   全图（长边 ≤1200，质量迭代压至 ≤300KB）
  - avatar-512/128/64.webp 头像裁剪（AVATAR_SRC 指定源图与裁剪框，视觉校准）
  - favicon.png / apple-touch-icon.png（由 avatar 派生）
可重复运行；crop 参数据预览结果手工微调。
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets" / "mascots" / "src"
OUT = ROOT / "assets" / "mascots"

# 头像源图与裁剪框（原图坐标，方形）：据网格图目测校准，可微调
AVATAR_SRC = "sakura-01.png"
AVATAR_BOX = (310, 90, 830, 610)  # 左、上、右、下

MAX_EDGE = 1200
SIZE_LIMIT_FULL = 420 * 1024
SIZE_LIMIT_AVATAR = {512: 80 * 1024, 128: 20 * 1024, 64: 8 * 1024}


def save_webp(im: Image.Image, path: Path, limit: int, start_q: int = 88) -> None:
    """质量迭代压缩直至满足体积门禁。"""
    q = start_q
    while True:
        im.save(path, "WEBP", quality=q, method=6)
        if path.stat().st_size <= limit or q <= 68:
            break
        q -= 6
    kb = path.stat().st_size / 1024
    print(f"  {path.name:<28} {im.size[0]}x{im.size[1]}  q={q}  {kb:.0f}KB")


def build_full() -> None:
    print("[全图 WebP]")
    for src in sorted(SRC.glob("sakura-*.png")):
        im = Image.open(src)
        if max(im.size) > MAX_EDGE:
            im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
        save_webp(im, OUT / (src.stem + ".webp"), SIZE_LIMIT_FULL)


def build_avatar() -> None:
    print("[头像裁剪]")
    im = Image.open(SRC / AVATAR_SRC).convert("RGBA")
    box = AVATAR_BOX
    assert box[2] - box[0] == box[3] - box[1], "裁剪框必须为正方形"
    face = im.crop(box)
    for size in (512, 128, 64):
        a = face.resize((size, size), Image.LANCZOS)
        save_webp(a, OUT / f"avatar-{size}.webp", SIZE_LIMIT_AVATAR[size], start_q=92)
    # favicon（不透明底，避免深色标签页发灰）
    fav = Image.new("RGBA", (64, 64), (25, 22, 30, 255))
    fav.alpha_composite(face.resize((64, 64), Image.LANCZOS))
    fav.convert("RGB").save(OUT / "favicon.png")
    apple = Image.new("RGBA", (180, 180), (25, 22, 30, 255))
    apple.alpha_composite(face.resize((180, 180), Image.LANCZOS))
    apple.convert("RGB").save(OUT / "apple-touch-icon.png")
    print("  favicon.png / apple-touch-icon.png 已派生")


def build_candidates() -> None:
    """四张图各出一版头像候选，用于视觉挑选（不进入正式素材）。"""
    print("[头像候选（校准用）]")
    cand = ROOT / ".generated" / "mascot_check"
    cand.mkdir(parents=True, exist_ok=True)
    boxes = {
        "sakura-01": (310, 90, 830, 610),
        "sakura-02": (310, 130, 830, 650),
        "sakura-03": (310, 110, 830, 630),
        "sakura-04": (310, 130, 830, 650),
    }
    for name, box in boxes.items():
        im = Image.open(SRC / f"{name}.png").convert("RGBA")
        face = im.crop(box).resize((240, 240), Image.LANCZOS)
        canvas = Image.new("RGBA", (250, 250), (245, 243, 248, 255))
        canvas.alpha_composite(face, (5, 5))
        canvas.convert("RGB").save(cand / f"cand_{name}.jpg", quality=90)
        print(f"  cand_{name}.jpg")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_full()
    build_avatar()
    print("完成")
