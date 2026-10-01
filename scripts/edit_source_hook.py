# -*- coding: utf-8 -*-
"""mkdocs 构建钩子：编辑按钮回链源文件 + H1 下注入「最后更新于」。

背景：站点从 .generated/docs 构建，该目录不入库。mkdocs 默认按 docs_dir 相对路径
拼接 edit_uri，编辑链接会指向仓库中不存在的生成文件（GitHub 上 404）。本钩子：

1. on_page_context 改写 page.edit_url：
   - 普通内容页：生成路径与源目录 1:1（sync_docs.copy_docs 原样拷贝），直接映射；
   - project.md → README.md（sync_docs 的改名规则）；
   - 纯生成页（首页 index.md / 目录索引 catalog.md / 404.md）：置 None 隐藏按钮。
   - `mkdocs serve`（本地预览）时改为 EDITOR_SCHEME://file/ 直开本地源文件，
     方便「本地改完 → git push → CI 发布」；正式构建（mkdocs build）仍指向
     GitHub 网页编辑器，访客提交后 push 到 main 触发 deploy-docs.yml 自动重建发布。

2. on_page_markdown 在章节 H1 下方注入「最后更新于 <日期>」（Stripe/GitBook 式
   活文档元信息）。日期来自一次 `git log --name-only` 扫描建立的
   {源文件路径: 最近提交日期} 映射（git 不可用或文件未提交过则静默跳过），
   全站 400+ 页只起一个子进程，构建耗时影响可忽略。
"""
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

GENERATED_PAGES = {"index.md", "catalog.md", "404.md"}
RENAME = {"project.md": "README.md"}

# 本地预览点「编辑此页」时用哪个编辑器协议拉起：VS Code 用 vscode，Cursor 改 cursor
EDITOR_SCHEME = "vscode"
# `mkdocs serve` 子命令在 sys.argv 里（CI 走 build_site.sh → `mkdocs build`，不含 serve）
SERVING = "serve" in sys.argv

ROOT = Path(__file__).resolve().parents[1]
_updated_cache = None  # {posix 相对路径: "YYYY-MM-DD"}


def _last_commit_map():
    """一次 git log 建立 {路径: 最近提交日期}；失败返回空表（静默降级）。"""
    global _updated_cache
    if _updated_cache is not None:
        return _updated_cache
    _updated_cache = {}
    try:
        out = subprocess.run(
            ["git", "-c", "core.quotepath=false", "log", "--name-only",
             "--diff-filter=AM", "--pretty=format:@%as", "--", "*.md"],
            cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace",
            timeout=30, check=True,
        ).stdout
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("@"):
                _date = line[1:]
            elif line and line.endswith(".md"):
                # log 从新到旧：首次出现的路径即最近提交日期
                _updated_cache.setdefault(line.replace("\\", "/"), _date)
    except Exception:
        pass
    return _updated_cache


def on_page_markdown(markdown, *, page, **kwargs):
    src_path = page.file.src_path.replace("\\", "/")
    if src_path in GENERATED_PAGES or not src_path.endswith(".md"):
        return markdown
    date = _last_commit_map().get(RENAME.get(src_path, src_path))
    if not date:
        return markdown
    lines = markdown.split("\n")
    date_line = f'\n<p class="rt-updated">最后更新于 {date}</p>\n'
    for i, line in enumerate(lines[:3]):  # H1 允许前面有空行
        if line.startswith("# ") and i + 1 <= len(lines):
            lines.insert(i + 1, date_line)
            return "\n".join(lines)
    return markdown


def on_page_context(context, *, page, config, **kwargs):
    # Windows 构建时 src_path 可能带反斜杠，统一转 posix 再拼 URL
    src_path = page.file.src_path.replace("\\", "/")

    if src_path in GENERATED_PAGES:
        page.edit_url = None
    elif src_path.endswith(".md"):
        source = RENAME.get(src_path, src_path)
        if SERVING:
            # 本地预览：直接在编辑器里打开源文件（盘符冒号不编码，中文路径走 quote）
            page.edit_url = f"{EDITOR_SCHEME}://file/{quote((ROOT / source).as_posix(), safe='/:')}"
        else:
            repo_url = (config.get("repo_url") or "").rstrip("/")
            edit_uri = (config.get("edit_uri") or "").strip("/")
            if repo_url and edit_uri:
                page.edit_url = f"{repo_url}/{edit_uri}/{quote(source)}"

    context["page"] = page
    return context
