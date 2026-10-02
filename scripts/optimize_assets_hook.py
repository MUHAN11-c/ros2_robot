# -*- coding: utf-8 -*-
"""mkdocs 构建钩子：构建期资源优化。源目录零改动，只处理 site 产物。

1. on_page_content：给正文 <img> 注入 loading="lazy" decoding="async"。
   此前懒加载完全靠 app.js 运行时兜底（无 JS 视图/爬虫会整页急加载，
   instant 导航前也先急取图）；构建期写入属性后 HTML 天生按需取图。
   首页 hero / 吉祥物等模板图不经 markdown 渲染，不受影响（hero 是
   LCP，本就应立即加载）。已手写 loading 属性的 img（attr_list）不覆盖。

2. on_post_build：
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

import rcssmin
import rjsmin

_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def _inject_lazy(match: re.Match) -> str:
    tag = match.group(0)
    if "loading=" in tag:  # 尊重 attr_list 手写的加载策略
        return tag
    if tag.rstrip().endswith("/>"):  # XHTML 风格自闭合（python-markdown 输出）
        return tag[:-2].rstrip() + ' loading="lazy" decoding="async" />'
    return tag[:-1].rstrip() + ' loading="lazy" decoding="async">'


def on_page_content(html: str, *, page, **kwargs) -> str:
    if "<img" not in html:
        return html
    return _IMG_TAG.sub(_inject_lazy, html)


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

    css_n, css_saved = _minify_dir(site_dir / "stylesheets", ".css", rcssmin.cssmin)
    js_n, js_saved = _minify_dir(site_dir / "javascripts", ".js", rjsmin.jsmin)

    map_bytes = 0
    for map_file in site_dir.rglob("*.map"):
        map_bytes += map_file.stat().st_size
        map_file.unlink()

    parts = []
    if css_n:
        parts.append(f"css -{css_saved // 1024}KB/{css_n} 文件")
    if js_n:
        parts.append(f"js -{js_saved // 1024}KB/{js_n} 文件")
    if map_bytes:
        parts.append(f"map -{map_bytes // 1024}KB")
    if parts:
        print(f"[optimize] {'，'.join(parts)}")
