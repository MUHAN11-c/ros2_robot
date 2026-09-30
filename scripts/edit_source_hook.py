# -*- coding: utf-8 -*-
"""mkdocs 构建钩子：把页面右上角「编辑此页」按钮指回 GitHub 仓库的源文件。

背景：站点从 .generated/docs 构建，该目录不入库。mkdocs 默认按 docs_dir 相对路径
拼接 edit_uri，编辑链接会指向仓库中不存在的生成文件（GitHub 上 404）。本钩子在
on_page_context 中改写 page.edit_url：
  - 普通内容页：生成路径与源目录 1:1（sync_docs.copy_docs 原样拷贝），直接映射；
  - project.md → README.md（sync_docs 的改名规则）；
  - 纯生成页（首页 index.md / 目录索引 catalog.md / 404.md）：置 None 隐藏按钮。
访客在 GitHub 网页编辑器里提交后，push 到 main 触发 deploy-docs.yml 自动重建发布。
"""
from urllib.parse import quote

GENERATED_PAGES = {"index.md", "catalog.md", "404.md"}
RENAME = {"project.md": "README.md"}


def on_page_context(context, *, page, config, **kwargs):
    # Windows 构建时 src_path 可能带反斜杠，统一转 posix 再拼 URL
    src_path = page.file.src_path.replace("\\", "/")

    if src_path in GENERATED_PAGES:
        page.edit_url = None
    elif src_path.endswith(".md"):
        repo_url = (config.get("repo_url") or "").rstrip("/")
        edit_uri = (config.get("edit_uri") or "").strip("/")
        if repo_url and edit_uri:
            source = RENAME.get(src_path, src_path)
            page.edit_url = f"{repo_url}/{edit_uri}/{quote(source)}"

    context["page"] = page
    return context
