# -*- coding: utf-8 -*-
"""mkdocs 构建钩子：on_post_build 用自定义渲染覆盖根级 404.html。

背景：mkdocs 对 404.md 会同时输出两份——
  1) site/404.html：Material 默认 404 模板（忽略页面内容，硬编码 "404 - Not found"）；
  2) site/404/index.html：常规渲染（我们的自定义内容）。
GitHub Pages 只服务根级 404.html，且任何裸 `mkdocs build`（定时校验、本地直跑）
都会把默认版写回。本钩子挂在 on_post_build，所有构建路径统一覆盖并断言校验。
"""
from pathlib import Path


def on_post_build(config, **kwargs):
    site = Path(config["site_dir"])
    custom = site / "404" / "index.html"
    target = site / "404.html"
    if not custom.exists():
        print("WARNING - override_404 钩子：未找到 site/404/index.html，跳过覆盖")
        return
    text = custom.read_text(encoding="utf-8")
    assert "rt-404" in text, "override_404 钩子：自定义 404 渲染缺少 rt-404 内容"
    target.write_text(text, encoding="utf-8")
    print("INFO    - 404.html 已由自定义渲染覆盖（override_404 钩子）")
