# -*- coding: utf-8 -*-
"""mkdocs 构建钩子：搜索索引瘦身（不影响渲染 HTML 与站内搜索功能）。

背景：463 页中文教程的 search_index.json 曾达 126MB——打开搜索框要下载
约 25MB（gzip 后）并做多秒的 JSON 解析，移动端基本不可用。两个膨胀源：

1. 代码块全文进索引：6k+ 个 <pre> 里的 import/赋值/模板代码 token 量大、
   检索价值低（中文教学站的正文/标题才是主要检索目标）；
2. json.dumps 默认 ensure_ascii=True：每个 CJK 字符写成 \\uXXXX 6 字节，
   比 UTF-8 原文（3 字节）翻倍。

做法（全部构建期，渲染产物零变化）：
- on_config：包装 material/search 插件 SearchIndex.add_entry_from_context，
  仅在索引读取 page.content 的瞬间换成剥离 <pre> 后的副本，函数返回即恢复
  原文。Material 插件先于 hooks 迭代，其 on_config 已建好 search_index；
  serve 重建时 SearchIndex 会被重建，故每次 on_config 都对新实例包装
  （以实例上的标记防重复包装）。
- on_post_build：把 search_index.json 以 ensure_ascii=False 重新序列化。
  JSON 转义只是序列化细节，JSON.parse 后的字符串与 worker 侧 new RegExp
  的语义完全一致；lunr 分词依赖的 \\u200b 分隔符字符本身原样保留。

已知取舍：代码块内部文本不再可搜（标题、正文、行内代码、公式容器
.arithmatex 均不受影响）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# <pre> 不可能嵌套，非贪婪 + DOTALL 即可整块移除（含 pymdownx.highlight
# 的 <div class="highlight"> 内层）；pre 内部不会出现 "</pre>" 字面量
# （markdown 渲染时已转义为 &lt;/pre&gt;）
_PRE_RE = re.compile(r"<pre\b[^>]*>.*?</pre>", re.DOTALL | re.IGNORECASE)


def on_config(config, **kwargs):
    plugins = config.get("plugins") or {}
    search = plugins.get("material/search")
    if search is None:
        # 非 Material 9.7+ 的搜索实现（如退回 mkdocs 自带 search），不动
        return
    indexer = getattr(search, "search_index", None)
    if indexer is None or getattr(indexer, "_rt_diet_wrapped", False):
        return

    original = indexer.add_entry_from_context

    def wrapped(page, **kw):
        full = page.content
        page.content = _PRE_RE.sub("", full or "")
        try:
            return original(page, **kw)
        finally:
            page.content = full

    indexer.add_entry_from_context = wrapped
    indexer._rt_diet_wrapped = True


def on_post_build(*, config, **kwargs):
    path = Path(config["site_dir"]) / "search" / "search_index.json"
    if not path.is_file():
        return
    before = path.stat().st_size
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
    except Exception as exc:  # 解析失败则保留原索引，不影响构建
        print(f"[search-diet] 跳过索引重编码: {exc}")
        return
    path.write_text(text, encoding="utf-8")
    after = path.stat().st_size
    print(f"[search-diet] 索引 {before >> 20}MB -> {after >> 20}MB")
