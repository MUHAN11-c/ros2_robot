# -*- coding: utf-8 -*-
"""mkdocs 构建钩子：编辑按钮直开本地源文件 + H1 下注入「最后更新于」。

背景：站点从 .generated/docs 构建，该目录不入库，mkdocs 默认按 docs_dir 相对路径
拼接 edit_uri 的链接指向仓库中不存在的生成文件（GitHub 上 404）；GitHub 托管侧
暂不可改，故本地/构建统一一套：编辑按钮一律用编辑器协议直开仓库里的源文件
（「本地改完 → git push」的工作流）。本钩子：

1. on_page_context 改写 page.edit_url：
   - 普通内容页：生成路径与源目录 1:1（sync_docs.copy_docs 原样拷贝），直接映射；
   - project.md → README.md（sync_docs 的改名规则）；
   - 纯生成页（首页 index.md / 目录索引 catalog.md / 404.md）：置 None 隐藏按钮。
   注意：链接含本机绝对路径，仅对持有仓库的工作机有意义；若日后恢复线上
   「GitHub 在线编辑」，把 on_page_context 换回 repo_url/edit_uri 拼接即可。

2. on_page_markdown 在章节 H1 下方注入「最后更新于 <日期>」（Stripe/GitBook 式
   活文档元信息）。日期来自一次 `git log --name-only` 扫描建立的
   {源文件路径: 最近提交日期} 映射（git 不可用或文件未提交过则静默跳过），
   全站 400+ 页只起一个子进程，构建耗时影响可忽略。
"""
import subprocess
from pathlib import Path
from urllib.parse import quote

GENERATED_PAGES = {"index.md", "catalog.md", "404.md"}
RENAME = {"project.md": "README.md"}

# 「编辑此页」用哪个编辑器协议拉起：VS Code 用 vscode，Cursor 改 cursor
EDITOR_SCHEME = "vscode"

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
        # 直开本地源文件（盘符冒号不编码，中文路径走 quote）
        page.edit_url = f"{EDITOR_SCHEME}://file/{quote((ROOT / source).as_posix(), safe='/:')}"

    context["page"] = page
    return context
