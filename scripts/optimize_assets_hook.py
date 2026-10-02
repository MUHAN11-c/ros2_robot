# -*- coding: utf-8 -*-
"""mkdocs 构建钩子：构建期资源优化。源目录零改动，只处理 site 产物。

1. on_page_content（每页 HTML）：给 <img> 注入懒加载——首图保持 eager
   （常为首屏 LCP，labs 页顶部就是插图），其余 loading="lazy"
   decoding="async"。此前懒加载完全靠 app.js 运行时兜底，无 JS 视图/
   爬虫会整页急加载。首页 hero / 吉祥物等模板图不经 markdown 渲染，
   不受影响。

2. on_post_build（整站产物，单次遍历 HTML）：
   - glightbox 条件加载：mkdocs-glightbox 在全部页面注入 css+js+初始化
     （~70KB），但实测仅 38/466 页含图片锚点。对无 class="glightbox"
     锚点的页面剥离其 <link>/<script src>/<style id="glightbox-style">/
     <script id="init-glightbox"> 四段；含图页原样保留。
   - 图片尺寸注入：为缺尺寸的 <img> 写入构建期 width/height（浏览器在
     图片加载前预留宽高比，消除长页 CLS）。raster 走 Pillow
     （mkdocs-material 自带依赖），SVG 解析根元素的 width/height 或
     viewBox；外部图/data URI/已手写尺寸的跳过。放在 post_build 是因为
     mkdocs 1.6 先渲染全部页面后拷贝静态资源，渲染期读不到 site 图片。
   - 压缩自研样式与脚本（site/stylesheets/*.css、site/javascripts/*.js，
     rcssmin/rjsmin 纯 Python 实现）。仓库源文件保持可读可维护，压缩只
     发生在 site 产物上；Material/glightbox/MathJax 的第三方已压缩文件
     （site/assets/）一概不动。
   - 删除 site 下全部 *.map（Material bundle 等 4 个 source map 约
     1.3MB，线上无人消费）。

注意：mkdocs serve 同样会触发本钩子（调试时看到的是压缩版产物）。
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

import rcssmin
import rjsmin

try:
    from PIL import Image
except ImportError:  # 尺寸注入为增强项，Pillow 缺失时静默降级
    Image = None

_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_ATTR = re.compile(r'\bsrc="([^"]+)"')
_DIMS_ATTR = re.compile(r'\b(?:width|height)=')
_SVG_HEAD = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
_SVG_W_H = re.compile(r'\bwidth="([\d.]+)(?:pt|px)?"[^>]*?\bheight="([\d.]+)(?:pt|px)?"')
_SVG_VIEWBOX = re.compile(r'\bviewBox="[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)"')

# glightbox 在每页注入的四段（无图片锚点的页面上整体移除）
_GLB_LINK = re.compile(r"<link[^>]*glightbox\.min\.css[^>]*>\s*")
_GLB_SCRIPT = re.compile(r"<script[^>]*glightbox\.min\.js[^>]*></script>\s*")
_GLB_STYLE = re.compile(r'<style id="glightbox-style">.*?</style>\s*', re.DOTALL)
_GLB_INIT = re.compile(r'<script id="init-glightbox">.*?</script>\s*', re.DOTALL)

# {解析过的图片绝对路径: (w, h)}——同一插图被几十页引用，跨页缓存
_dims_cache: dict[str, tuple[int, int] | None] = {}


def _svg_dims(path: Path) -> tuple[int, int] | None:
    try:
        head = path.open(encoding="utf-8", errors="replace").read(4096)
    except OSError:
        return None
    tag = _SVG_HEAD.search(head)
    if not tag:
        return None
    m = _SVG_W_H.search(tag.group(0)) or _SVG_VIEWBOX.search(tag.group(0))
    if not m:
        return None
    w, h = int(float(m.group(1))), int(float(m.group(2)))
    return (w, h) if w > 0 and h > 0 else None


def _local_dims(path: Path) -> tuple[int, int] | None:
    """本地图片的像素尺寸；解析失败返回 None（不注入，保持原行为）。"""
    cached = _dims_cache.get(str(path))
    if str(path) in _dims_cache:
        return cached
    dims = None
    if path.is_file():
        if path.suffix.lower() == ".svg":
            dims = _svg_dims(path)
        elif Image is not None:
            try:
                with Image.open(path) as im:
                    dims = (im.width, im.height)
            except Exception:
                dims = None
    _dims_cache[str(path)] = dims
    return dims


def on_page_content(html: str, *, page, **kwargs) -> str:
    """懒加载注入。注意：此时 site/ 静态资源尚未拷贝（mkdocs 先渲染全部
    页面再 copy_static_files），尺寸解析做不了，故拆到 on_page_html。"""
    first_seen = False

    def _inject(match: re.Match) -> str:
        nonlocal first_seen
        tag = match.group(0)
        if "loading=" in tag:
            return tag
        additions = ""
        # 首图 eager：labs 等页顶部即插图，懒加载会推迟首屏 LCP
        if first_seen:
            additions += ' loading="lazy"'
        first_seen = True
        additions += ' decoding="async"'
        if tag.rstrip().endswith("/>"):  # XHTML 风格自闭合（python-markdown 输出）
            return tag[:-2].rstrip() + additions + " />"
        return tag[:-1].rstrip() + additions + ">"

    if "<img" not in html:
        return html
    return _IMG_TAG.sub(_inject, html)


def _inject_dims(html: str, page_dir: Path) -> tuple[str, int]:
    """为缺尺寸的 <img> 注入 width/height，返回 (新 HTML, 注入数)。
    在 on_post_build 阶段对 site 产物执行：此时静态资源已全部拷贝，
    可读取真实尺寸（mkdocs 1.6 无 on_page_html 事件，页面渲染期
    site/ 还是空的，尺寸读不到）。"""
    if Image is None or "<img" not in html:
        return html, 0
    count = 0

    def _inject(match: re.Match) -> str:
        nonlocal count
        tag = match.group(0)
        if _DIMS_ATTR.search(tag):
            return tag  # 已手写尺寸（attr_list/模板），尊重作者意图
        src_m = _SRC_ATTR.search(tag)
        # 绝对路径（404 根副本被改写为部署前缀）解析不到 site 内文件，跳过
        if not src_m or "://" in src_m.group(1) or src_m.group(1).startswith(("/", "data:")):
            return tag
        dims = _local_dims(page_dir / unquote(src_m.group(1)))
        if not dims:
            return tag
        count += 1
        addition = f' width="{dims[0]}" height="{dims[1]}"'
        if tag.rstrip().endswith("/>"):
            return tag[:-2].rstrip() + addition + " />"
        return tag[:-1].rstrip() + addition + ">"

    return _IMG_TAG.sub(_inject, html), count


def _minify_dir(directory: Path, suffix: str, minifier) -> tuple[int, int]:
    """压缩目录下全部 *suffix 文件，返回 (处理数, 节省字节数)。"""
    saved = 0
    count = 0
    if not directory.is_dir():
        return 0, 0
    for path in sorted(directory.glob("*" + suffix)):
        try:
            source = path.read_text(encoding="utf-8")
            compressed = minifier(source)
        except Exception as exc:  # 压缩失败不影响构建，保留原文件
            print(f"[optimize] 跳过 {path.name}: {exc}")
            continue
        if compressed and len(compressed) < len(source):
            saved += len(source) - len(compressed)
            count += 1
            path.write_text(compressed, encoding="utf-8")
    return count, saved


def on_post_build(*, config, **kwargs) -> None:
    site_dir = Path(config["site_dir"])

    # 单次遍历整站 HTML：glightbox 条件剥离 + 图片尺寸注入
    glb_files = 0
    glb_bytes = 0
    dim_tags = 0
    for html_path in site_dir.rglob("*.html"):
        text = html_path.read_text(encoding="utf-8")
        new = text
        glb_stripped = False
        if 'class="glightbox"' not in new:  # 无图片锚点的页面剥离四段注入
            stripped = _GLB_INIT.sub("", _GLB_STYLE.sub("", _GLB_SCRIPT.sub("", _GLB_LINK.sub("", new))))
            if stripped != new:
                glb_stripped = True
                new = stripped
        new, n = _inject_dims(new, html_path.parent)
        dim_tags += n
        if glb_stripped:
            glb_files += 1
        if new != text:
            glb_bytes += len(text) - len(new)
            html_path.write_text(new, encoding="utf-8")

    css_n, css_saved = _minify_dir(site_dir / "stylesheets", ".css", rcssmin.cssmin)
    js_n, js_saved = _minify_dir(site_dir / "javascripts", ".js", rjsmin.jsmin)

    map_bytes = 0
    for map_file in site_dir.rglob("*.map"):
        map_bytes += map_file.stat().st_size
        map_file.unlink()

    parts = []
    if glb_files:
        parts.append(f"glightbox 剥离 {glb_files} 页 -{glb_bytes // 1024}KB")
    if dim_tags:
        parts.append(f"尺寸注入 {dim_tags} 处")
    if css_n:
        parts.append(f"css -{css_saved // 1024}KB/{css_n} 文件")
    if js_n:
        parts.append(f"js -{js_saved // 1024}KB/{js_n} 文件")
    if map_bytes:
        parts.append(f"map -{map_bytes // 1024}KB")
    if parts:
        print(f"[optimize] {'，'.join(parts)}")
