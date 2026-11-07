#!/usr/bin/env python3
"""离线清点已下载的 ROS 2 资料，生成可追溯清单与逐文件校验表。

输入：下载回执、catalog.json、已有工作区快照；不联网，不执行上游代码。
输出：manifest.json、README.md、文档索引、ROS 包索引和 SHA256 校验表。
数量仅代表仓库快照、文件与 package.xml，不能解释为已讲解的知识点数量。
容量统一使用字节记录、GiB 展示；任何源码运行验证都保持“本轮未运行”。
"""

from __future__ import annotations

import csv
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from download_ros2_references import HUB, LIBRARY, atomic_json, now, sha256


WORKSPACE = HUB.parent
DOC_SUFFIXES = {".md", ".rst", ".mdx", ".ipynb", ".pdf"}
CODE_SUFFIXES = {".py", ".cpp", ".hpp", ".h", ".c", ".cc", ".cxx", ".ino"}
CATEGORY_NAMES = {"official-docs": "官方文档", "official-examples": "官方及官方教程配套示例",
                  "official-core": "官方工具与配套库", "ecosystem": "主要生态教程与示例",
                  "community-zh": "中文社区课程", "community-en": "英文社区课程",
                  "existing": "原有教程与参考工程"}


def document_title(path: Path) -> str:
    """只读取文本开头提取标题；PDF 和 Notebook 仅登记文件名，不伪造解析结果。"""
    if path.suffix.lower() in {".pdf", ".ipynb"}:
        return path.stem
    with path.open(encoding="utf-8", errors="replace") as stream:
        lines = stream.read(12000).splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            return line[2:].strip()
        if (index + 1 < len(lines) and line.strip()
                and re.fullmatch(r"[=~^\-]{3,}", lines[index + 1].strip())):
            return line.strip()
    return path.stem


def local_link(path: str) -> str:
    """URL 编码空格与中文，保证 Markdown 文件链接可直接使用。"""
    return quote(path, safe="/.-_")


def scan(record: dict, root: Path, checksums, documents, packages) -> dict:
    """逐文件核查并清点；不沿目录软链接递归，防止越过资料边界。"""
    if not root.is_dir():
        raise FileNotFoundError(f"回执指向的源码目录不存在：{root}")
    counts = Counter()
    licenses, submodule_configs, lfs, links, malformed_packages = [], [], [], [], []
    for directory, subdirectories, filenames in os.walk(root, followlinks=False):
        # 下载的上游代码不作为当前工作区的代理规则，也不扫描本机缓存或凭据。
        subdirectories[:] = sorted(name for name in subdirectories
                                   if name not in {".git", "__pycache__", "node_modules", ".venv"})
        for filename in sorted(filenames):
            path = Path(directory) / filename
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                links.append({"path": relative, "target": os.readlink(path)})
                continue
            if not path.is_file():
                continue
            size = path.stat().st_size
            counts["files"] += 1
            counts["bytes"] += size
            counts["codeFiles"] += path.suffix.lower() in CODE_SUFFIXES
            library_relative = os.path.relpath(path, LIBRARY)
            digest = sha256(path)
            checksums.write(f"{digest}  {library_relative}\n")
            if re.match(r"(?i)^(licen[cs]e|copying|copyright|notice)([._-]|$)", filename):
                licenses.append({"path": relative, "sha256": digest})
            if filename == ".gitmodules" and size:
                submodule_configs.append(relative)
            if size < 1024:
                prefix = path.read_bytes()
                if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
                    lfs.append(relative)
            if path.suffix.lower() in DOC_SUFFIXES:
                counts["documentFiles"] += 1
                documents.writerow([record["id"], record["ref"], path.suffix.lower(),
                                    document_title(path), library_relative])
            if filename == "package.xml":
                counts["packageXmlFiles"] += 1
                try:
                    package = ET.parse(path).getroot()
                    tags = [element.text or "" for element in package.findall("license")]
                    packages.writerow([record["id"], record["ref"], package.findtext("name", ""),
                                       package.findtext("version", ""), "; ".join(tags), library_relative])
                except ET.ParseError as error:
                    malformed_packages.append({"path": relative, "error": str(error)})
    return {**record, "inventory": dict(counts), "licenseFiles": licenses,
            "submoduleConfigFiles": submodule_configs, "unfetchedLfsPointers": lfs,
            "symbolicLinks": links, "unparsedPackageXml": malformed_packages}


def main() -> int:
    catalog = json.loads((LIBRARY / "catalog.json").read_text())
    downloaded = [json.loads(path.read_text())
                  for path in sorted((LIBRARY / "state" / "receipts").glob("*.json"))]
    submodules = [json.loads(path.read_text())
                  for path in sorted((LIBRARY / "state" / "submodules").glob("*.json"))]
    lfs_files = [json.loads(path.read_text())
                 for path in sorted((LIBRARY / "state" / "lfs").glob("*.json"))]
    by_source = {source["id"]: source for source in catalog["sources"]}
    present_ids = {record["sourceId"] for record in downloaded}
    unresolved = [source["id"] for source in catalog["sources"] if source["id"] not in present_ids]
    records, archive_failures = [], []
    with ((LIBRARY / "SOURCE_FILES.sha256").open("w") as checksums,
          (LIBRARY / "documents.csv").open("w", newline="") as doc_file,
          (LIBRARY / "packages.csv").open("w", newline="") as package_file,
          (LIBRARY / "ARCHIVES.sha256").open("w") as archives):
        documents, packages = csv.writer(doc_file), csv.writer(package_file)
        documents.writerow(["snapshot", "branch", "format", "title", "local_path"])
        packages.writerow(["snapshot", "branch", "package", "version", "declared_license", "local_path"])
        for record in downloaded:
            archive = LIBRARY / record["archivePath"]
            if not archive.is_file() or sha256(archive) != record["archiveSha256"]:
                archive_failures.append(record["id"])
            archives.write(f"{record['archiveSha256']}  {record['archivePath']}\n")
            records.append(scan(record, LIBRARY / record["localPath"], checksums, documents, packages))
            print(f"已清点 {record['id']}", flush=True)
        for existing in catalog["existingSnapshots"]:
            record = {"id": "existing--" + existing["path"], "sourceId": "existing--" + existing["path"],
                      "title": existing["path"], "sourceUrl": existing["url"],
                      "repository": existing["url"].removeprefix("https://github.com/").removesuffix(".git"),
                      "ref": existing["branch"], "commit": existing["commit"], "category": "existing",
                      "localPath": os.path.relpath(WORKSPACE / existing["path"], LIBRARY),
                      "status": "existing_snapshot", "runtimeValidation": "本轮未构建、未运行；历史记录见 CONTINUE.md"}
            records.append(scan(record, WORKSPACE / existing["path"], checksums, documents, packages))
        # 子模块文件已随父快照逐文件扫描；此处只补充独立压缩包摘要，避免重复计数。
        for record in submodules:
            archive = LIBRARY / record["archivePath"]
            if not archive.is_file() or sha256(archive) != record["archiveSha256"]:
                archive_failures.append(record["id"])
            archives.write(f"{record['archiveSha256']}  {record['archivePath']}\n")
    absent = [json.loads(path.read_text())
              for path in sorted((LIBRARY / "state" / "coverage").glob("*.json"))]
    totals = Counter()
    for record in records:
        totals.update(record["inventory"])
    categories = Counter(record["category"] for record in records)
    lfs_failures = []
    for item in lfs_files:
        asset = LIBRARY / item["localPath"]
        if (not asset.is_file() or asset.stat().st_size != item["bytes"]
                or sha256(asset) != item["sha256"]):
            lfs_failures.append(item["id"])
    lfs_pointer_count = sum(len(item["unfetchedLfsPointers"]) for item in records)
    submodule_report_path = LIBRARY / "state" / "submodules-last-run.json"
    submodule_report = (json.loads(submodule_report_path.read_text())
                        if submodule_report_path.exists() else {"errors": ["尚未检查子模块"]})
    manifest = {"indexedAt": now(), "timezone": "Asia/Shanghai", "scope": catalog["scope"],
                "downloadedRepositories": len(present_ids), "downloadedSnapshots": len(downloaded),
                "existingSnapshots": len(catalog["existingSnapshots"]), "submoduleSnapshots": len(submodules),
                "downloadedLfsFiles": len(lfs_files),
                "totals": dict(totals), "snapshotsByCategory": dict(categories),
                "archiveVerificationFailures": archive_failures, "unresolvedSources": unresolved,
                "lfsVerificationFailures": lfs_failures, "unfetchedLfsPointerCount": lfs_pointer_count,
                "missingDistroBranches": [item for item in absent if item["absentBranches"]],
                "websiteEntrypoints": catalog["websiteEntrypoints"],
                "snapshots": records, "submodules": submodules, "lfsFiles": lfs_files,
                "submoduleReport": submodule_report,
                "validation": {"archives": "SHA256 已复算", "sourceFiles": "逐文件 SHA256 已生成",
                               "rosBuild": "本轮未执行", "simulation": "本轮未执行", "hardware": "本轮未执行"}}
    atomic_json(LIBRARY / "manifest.json", manifest)
    lines = ["# ROS 2 本地教程与官方示例资料库", "", f"清点时间：{manifest['indexedAt']}。",
             "", f"本轮下载 **{len(present_ids)} 个来源条目、{len(downloaded)} 份分支快照**，另复用原有 **{len(catalog['existingSnapshots'])} 份快照**；已补充子模块 **{len(submodules)} 份**、LFS 资源 **{len(lfs_files)} 个**。",
             f"资料文件合计约 **{totals['bytes'] / 1024**3:.2f} GiB**，保留的原始压缩包另外占用空间。",
             "", "这份记录只说明原始资料下载、清点与完整性核查；原始第三方工程未批量构建或运行。当前中文教材及原创示例的独立整合/实测范围见 ../VALIDATION.md；不宣称这些资料已经逐段全部编入教材。",
             "文件数量包含导航、配置、图片与测试，文档文件数量也包含 README 等辅助文档，均不代表教学细节已穷尽。",
             "来源条目可能包含相同归档的别名，不能按条目数推断独立课程数；重复关系见 ../source/local-library.json。",
             "", "## 查阅入口", "",
             "- [完整来源、分支、提交、许可与缺项清单](manifest.json)",
             "- [文档文件索引：Markdown、RST、PDF、Notebook](documents.csv)",
             "- [ROS 包与其声明许可证索引](packages.csv)",
             "- [原始压缩包 SHA256](ARCHIVES.sha256)；[源码逐文件 SHA256](SOURCE_FILES.sha256)",
             "- [下载来源配置](catalog.json)", "- [本轮核查记录与验证边界](VALIDATION.md)",
             "", "## 官方版本范围", "",
             "`ros2/examples`、`ros2/demos` 和 `ros2/ros2` 按实际存在的发行版分支保存；官方文档库保存当前能取到的发行版分支。",
             "`ros2/ros2_documentation` 没有独立的 Ardent、Bouncy 分支，未把其他分支冒充这两个版本的完整历史文档。",
             "其余项目以 Jazzy 分支优先；无 Jazzy 分支时使用清单中明确记录的其他分支。main、master、rolling、ros2 分支不等于已验证兼容 Jazzy。",
             "", "## 来源与许可", "",
             "每个目录保留上游许可证与原注释，不对第三方源码重新许可。许可证未明确的资料只登记实际情况，不能因公开可访问就视为自由转载。",
             "带 NC/ND 等条件的正文与代码可能适用不同许可，后续整合需逐项查看原始条款；下载资料尚未统一添加中文教学注释。",
             "`sources/` 和 `archives/` 已从 Git 跟踪中排除，也不自动打入现有教材 ZIP；迁移这些本地资料需要额外复制整个 references 目录。",
             "", "## 下载与校验", "", "从工作区根目录执行：", "", "```bash",
             "# 下载：并发单位为独立公开仓库或快照；复用本轮锁定的提交。",
             "python3 ros2-learning-hub/scripts/download_ros2_references.py --jobs 6",
             "# 补齐源码归档未包含的子模块，严格使用父仓库记录的提交。",
             "python3 ros2-learning-hub/scripts/complete_reference_submodules.py --include-lfs",
             "# 清点：完全离线，逐文件计算 SHA256；不会运行第三方工程。",
             "python3 ros2-learning-hub/scripts/index_ros2_references.py",
             "# 验证压缩包：需要从 references 目录运行，路径均相对该目录。",
             "cd ros2-learning-hub/references",
             "sha256sum --check --quiet ARCHIVES.sha256",
             "# 原有参考快照也在校验范围；正常完成不应有 FAILED。",
             "sha256sum --check --quiet SOURCE_FILES.sha256", "```", "", "## 本地快照目录", ""]
    for category in CATEGORY_NAMES:
        subset = [record for record in records if record["category"] == category]
        if not subset:
            continue
        lines += [f"### {CATEGORY_NAMES[category]}", "", "| 资料 | 实际分支 | 本地目录 |", "| --- | --- | --- |"]
        for record in subset:
            title = by_source.get(record["sourceId"], {}).get("title", record["title"])
            lines.append(f"| [{title}]({record['sourceUrl']}) | `{record['ref']}` | [打开]({local_link(record['localPath'])}) |")
        lines.append("")
    lines += ["## 尚未纳入的范围", "",
              "互联网教程持续增加，本次清单不代表全网无遗漏；付费课程、视频流、登录后资料、完整 ROS 二进制镜像和所有传递依赖未自动下载。",
              "官方文档和大部分社区课程保存的是源码（RST/Markdown 等），没有统一构建成原站 HTML；可直接用编辑器离线阅读正文和代码。",
              "下列独立网站需与代码仓库的下载情况分别理解：", ""]
    for website in catalog["websiteEntrypoints"]:
        lines.append(f"- [{website['title']}]({website['url']})：{website['status']}。")
    lines += ["", f"当前未下载的清单仓库：{len(unresolved)}；压缩包校验失败：{len(archive_failures)}；子模块处理失败：{len(submodule_report['errors'])}；未补齐的 LFS 指针：{lfs_pointer_count}；LFS 校验失败：{len(lfs_failures)}。", ""]
    (LIBRARY / "README.md").write_text("\n".join(lines))
    print(json.dumps({key: manifest[key] for key in ("downloadedRepositories", "downloadedSnapshots",
                     "existingSnapshots", "submoduleSnapshots", "totals", "unresolvedSources",
                     "archiveVerificationFailures")}, ensure_ascii=False, indent=2))
    return 1 if unresolved or archive_failures or submodule_report["errors"] or lfs_pointer_count or lfs_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
