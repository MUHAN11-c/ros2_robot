# -*- coding: utf-8 -*-
"""mkdocs 构建钩子：on_post_build 用自定义渲染覆盖根级 404.html。

背景：mkdocs 对 404.md 会同时输出两份——
  1) site/404.html：Material 默认 404 模板（忽略页面内容，硬编码 "404 - Not found"）；
  2) site/404/index.html：常规渲染（我们的自定义内容）。
GitHub Pages 只服务根级 404.html，且任何裸 `mkdocs build`（定时校验、本地直跑）
都会把默认版写回。本钩子挂在 on_post_build，所有构建路径统一覆盖并断言校验。

路径修正：GitHub Pages 对未命中路径返回 404.html 时，文档地址停留在**访问者请求
的 URL**（如 /ros2_robot/不存在的页/），而非 /ros2_robot/404.html。文档相对引用
（剥掉 ../ 后的 assets/…）会以该不存在目录为基准解析，导致样式与素材全部失联。
因此根级副本统一把 ../ 前缀改写为站点绝对路径（site_url 的路径部分，如
/ros2_robot/），任意触发 URL 下均可正确解析；site/404/index.html 保持 ../ 相对
引用不变。
"""
import re
from pathlib import Path
from urllib.parse import urlparse

# 裸父级引用（href=".."）→ 站点根；带路径的 ../ 前缀 → 站点绝对路径
_BARE_PARENT = re.compile(r'((?:src|href)=")\.\.(")')
_PARENT_PREFIX = re.compile(r'((?:src|href)=")\.\./')


def site_base_path(config) -> str:
    """site_url 的路径部分，规范为以 / 开头、以 / 结尾（如 /ros2_robot/）。"""
    path = urlparse((config.get("site_url") or "").strip()).path or "/"
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path += "/"
    return path


def absolutize_refs(text: str, base: str) -> str:
    text = _BARE_PARENT.sub(lambda m: m.group(1) + base + m.group(2), text)
    return _PARENT_PREFIX.sub(lambda m: m.group(1) + base, text)


def on_post_build(config, **kwargs):
    site = Path(config["site_dir"])
    custom = site / "404" / "index.html"
    target = site / "404.html"
    if not custom.exists():
        print("WARNING - override_404 钩子：未找到 site/404/index.html，跳过覆盖")
        return
    text = custom.read_text(encoding="utf-8")
    assert "rt-404" in text, "override_404 钩子：自定义 404 渲染缺少 rt-404 内容"
    base = site_base_path(config)
    target.write_text(absolutize_refs(text, base), encoding="utf-8")
    print(f"INFO    - 404.html 已由自定义渲染覆盖（override_404 钩子，相对引用已改写为绝对路径 {base}）")
