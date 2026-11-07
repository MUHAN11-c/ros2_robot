"""教材文件修订层：校验正文、备份原文和旧版本，再提交章节文件与网页读取缓存。

输入来自本机编辑器；路径固定在教材目录，章节 ID 必须属于现有教材。
保存单位为整章；最大正文 2 MiB，原文备份只建立一次，历史版本按 SHA256 命名。
失败时回滚已写入的教材文件；备份失败时不写教材，不修改第三方资料或 ROS 工程。
"""
from __future__ import annotations

import base64
import copy
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from datetime import datetime, timezone

FORMAT = "ros2-local-editions-v1"
EMPTY = {"format": FORMAT, "revision": 0, "chapters": {}}
LOCK = threading.Lock()
TAGS = set("article section header footer div span p h1 h2 h3 h4 h5 h6 ul ol li strong b em i code pre table thead tbody tr th td caption figure figcaption details summary a img br hr blockquote small math mrow mi mo mn mtext mspace mstyle msub msup msubsup mfrac msqrt mroot mover munder munderover mtable mtr mtd mpadded menclose mfenced semantics annotation".split())
ATTRS = set("class id href src alt title width height open colspan rowspan display xmlns mathvariant mathsize mathcolor stretchy fence separator form accent accentunder columnalign rowalign columnspacing rowspacing encoding aria-label data-section-number".split())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("教材文件路径无效")
    for parent in [path, *path.parents]:
        if parent == root.parent:
            break
        if parent.is_symlink():
            raise ValueError("保存路径包含符号链接，请使用实际教材目录")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("保存路径越出教材目录")
    return path


def read_data(root: Path):
    text = safe_path(root, "dist/content.js").read_text()
    return json.loads(text.split("window.ROS2Hub = ", 1)[1].strip().removesuffix(";"))


class DocumentCheck(HTMLParser):
    def __init__(self, figures):
        super().__init__(convert_charrefs=True)
        self.images = {"../dist/" + item["file"] for item in figures}

    def handle_starttag(self, tag, attrs):
        if tag not in TAGS:
            raise ValueError("正文包含不允许的标签：" + tag)
        for key, value in attrs:
            if key not in ATTRS or key.startswith("on"):
                raise ValueError("正文包含不允许的属性：" + key)
            if key == "href" and not re.match(r"^(https?://|#/|\.\./dist/|#[a-z0-9_-]+$)", value or "", re.I):
                raise ValueError("正文链接地址无效")
            if key == "data-section-number" and not re.fullmatch(r"\d+(?:\.\d+)+", value or ""):
                raise ValueError("正文节号无效")
            if key == "src" and value not in self.images:
                raise ValueError("正文图解不在本地教材清单内")

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag not in TAGS:
            raise ValueError("正文包含不允许的标签：" + tag)


def validate_document(document, data):
    if not isinstance(document, dict):
        raise ValueError("章节保存数据无效")
    for field in ("html", "markdown", "title"):
        if not isinstance(document.get(field), str) or len(document[field].encode()) > 2 * 1024**2:
            raise ValueError("章节正文无效或超过 2 MiB")
    if len(document["title"]) > 1000:
        raise ValueError("章节标题过长")
    DocumentCheck(data.get("figures", [])).feed(document["html"])
    return document


def load_editions(root: Path, data):
    file = safe_path(root, "source/local-edits.json")
    registry = json.loads(file.read_text()) if file.exists() else copy.deepcopy(EMPTY)
    if registry.get("format") != FORMAT or not isinstance(registry.get("chapters"), dict):
        raise ValueError("教材修订文件格式无效")
    valid = {chapter["id"] for chapter in data["lessons"]}
    for key, record in registry["chapters"].items():
        if key not in valid or record.get("chapterId") != key:
            raise ValueError("修订引用了不存在的章节")
        validate_document(record["document"], data)
    return registry


def runtime_script(registry):
    return ("/* 本地教材文件修订；原文与历史见 backups/local-edits/。 */\nwindow.ROS2LocalEditions = "
            + json.dumps(registry, ensure_ascii=False, indent=2).replace("<", "\\u003c") + ";\n").encode()


def chapter_page(document, backup=False):
    prefix = "../../../../dist/" if backup else "../"
    style = "../../../../design-review/styles.css" if backup else "../../design-review/styles.css"
    body = re.sub(r"<(?:a|img)\b[^>]*>", lambda m: m[0].replace('="../dist/', '="' + prefix), document["html"])
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + escape(document["title"]) + '</title><link rel="stylesheet" href="' + style + '"></head>'
            '<body><main id="reading"><p><a href="' + prefix + 'index.html">返回教材</a></p>' + body + '</main></body></html>\n').encode()


def atomic_write(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".edition-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def backup_once(root: Path, relative: str, content: bytes):
    path = safe_path(root, relative)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("已有原文备份与当前基线不同，已停止保存：" + relative)
        return
    atomic_write(path, content)


def save_edition(root: Path, payload):
    if not isinstance(payload, dict):
        raise ValueError("章节保存请求无效")
    root = root.resolve()
    with LOCK:
        data = read_data(root)
        chapter_id = payload.get("chapterId")
        chapter = next((c for c in data["lessons"] if c["id"] == chapter_id), None)
        if chapter is None:
            raise ValueError("请选择有效教材章节")
        if payload.get("baseChapter") != chapter:
            raise ValueError("教材基线已变化，请刷新后重新核对修改")
        document = validate_document(payload.get("document"), data)
        original = validate_document(payload.get("original"), data)
        registry = load_editions(root, data)
        previous = registry["chapters"].get(chapter_id)
        if payload.get("expectedRevision") != (previous or {}).get("revision"):
            raise ValueError("此章已被其他页面修改，请刷新后重新保存；现有文件已保留")
        revision = digest(encoded(document))
        if previous and previous["revision"] == revision:
            return {"saved": True, "unchanged": True, "record": previous}
        prefix = "backups/local-edits/original/" + chapter_id
        backup_once(root, prefix + "/source.json", encoded(chapter))
        backup_once(root, prefix + "/chapter.md", original["markdown"].encode())
        backup_once(root, prefix + "/chapter.html", chapter_page(original, backup=True))
        # 原始内容数据从磁盘读取，避免仅依赖浏览器提交的原文声明。
        baseline = safe_path(root, "backups/local-edits/original/content.js")
        if not baseline.exists():
            backup_once(root, "backups/local-edits/original/content.js", safe_path(root, "dist/content.js").read_bytes())
        if previous:
            backup_once(root, f"backups/local-edits/history/{chapter_id}/{previous['revision']}.json", encoded(previous))
        record = {"chapterId": chapter_id, "revision": revision,
                  "savedAt": datetime.now(timezone.utc).isoformat(), "document": document}
        registry["chapters"][chapter_id] = record
        registry["revision"] += 1
        outputs = {f"dist/chapters/{chapter_id}.md": document["markdown"].encode(),
                   f"dist/chapters/{chapter_id}.html": chapter_page(document),
                   "source/local-edits.json": encoded(registry), "dist/local-edits.js": runtime_script(registry)}
        old = {}; touched = []
        try:
            for name, content in outputs.items():
                path = safe_path(root, name)
                old[name] = path.read_bytes() if path.exists() else None
                touched.append(name)
                atomic_write(path, content)
        except Exception:
            failures = []
            for name in reversed(touched):
                path = safe_path(root, name)
                try:
                    if old[name] is None:
                        path.unlink(missing_ok=True)
                    else:
                        atomic_write(path, old[name])
                except OSError:
                    failures.append(name)
            if failures:
                raise OSError("保存失败且部分文件未能回滚，原文备份已保留：" + ", ".join(failures))
            raise
        return {"saved": True, "record": record, "files": list(outputs), "backup": prefix}


def inline_local_figures(html: str, root: Path, data):
    for item in data.get("figures", []):
        if 'src="../dist/' + item["file"] + '"' not in html:
            continue
        file = safe_path(root, "dist/" + item["file"])
        image = "data:image/svg+xml;base64," + base64.b64encode(file.read_bytes()).decode()
        html = html.replace('src="../dist/' + item["file"] + '"', 'src="' + image + '"')
    return html


def edition_markdown(document, chapter_number):
    """将单章标题降级到全书层级，围栏内的代码注释不改变。"""
    lines = document["markdown"].splitlines()
    if lines and lines[0].startswith("# "):
        lines.pop(0)
    out = [f"## {chapter_number}. {document['title']}"]
    fence = None
    for line in lines:
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match[1]
            if fence and marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            elif fence is None:
                fence = marker
        elif fence is None and re.match(r"^#{1,6} ", line):
            line = "#" + line if not line.startswith("###### ") else line
        if fence is None and line.startswith("!["):
            line = line.replace("](../dist/", "](../", 1)
        out.append(line)
    return "\n".join(out)
