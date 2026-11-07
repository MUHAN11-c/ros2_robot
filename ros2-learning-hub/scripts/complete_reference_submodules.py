#!/usr/bin/env python3
"""按父仓库固定提交补齐教程中的 Git 子模块，不运行子模块代码。

输入：下载回执和源码根目录的 .gitmodules。
输出：子模块源码、独立原始归档和 state/submodules 中的固定提交回执。
执行顺序：读取 .gitmodules → 查询父提交 Git 树 → 取 gitlink 的准确 SHA → 下载。
边界：只访问公开 GitHub HTTPS；递归最多四层；不把分支最新提交冒充 gitlink。
容量限制单位为 MiB，沿用主下载器的安全解包与 SHA256 计算。
"""

from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

from download_ros2_references import LIBRARY, atomic_json, download, extract, now, sha256


USE_GIT_TREE = False


def git_tree_without_api(repository: str, commit: str) -> dict:
    """API 限流时只取 Git 对象元数据，不检出或运行第三方文件。

    blob:none 省去源文件内容；临时裸仓库只用于 ls-tree 读取 gitlink 的 SHA。
    仍以父回执中的固定提交为准，不能用分支头替代。
    """
    temporary = Path(tempfile.mkdtemp(prefix="ros2-git-tree-"))
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    base = ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null"]
    try:
        subprocess.run(base + ["init", "--bare", str(temporary)], check=True,
                       capture_output=True, env=environment, timeout=20)
        subprocess.run(base + ["-C", str(temporary), "fetch", "--no-tags", "--depth=1",
                               "--filter=blob:none", f"https://github.com/{repository}.git", commit],
                       check=True, capture_output=True, env=environment, timeout=180)
        result = subprocess.run(base + ["-C", str(temporary), "ls-tree", "-r", "-z", "FETCH_HEAD"],
                                check=True, capture_output=True, env=environment, timeout=30)
        tree = []
        for entry in result.stdout.split(b"\0"):
            if not entry:
                continue
            metadata, path = entry.split(b"\t", 1)
            mode, kind, object_id = metadata.decode().split()
            if mode == "160000":
                tree.append({"path": path.decode(), "mode": mode,
                             "type": kind, "sha": object_id})
        return {"sha": commit, "tree": tree, "truncated": False,
                "retrieval": "git fetch --filter=blob:none + git ls-tree"}
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def git_tree(repository: str, commit: str) -> dict:
    """GitHub 公共 Git 树仅提供对象元数据；不读取本机账户或登录令牌。"""
    global USE_GIT_TREE
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("不允许的仓库名称")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("必须使用完整的固定提交哈希")
    cache = LIBRARY / "state" / "trees" / f"{repository.replace('/', '--')}--{commit}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    url = f"https://api.github.com/repos/{repository}/git/trees/{commit}?recursive=1"
    request = urllib.request.Request(url, headers={"User-Agent": "ROS2-Offline-Reference-Download/1.0"})
    if USE_GIT_TREE:
        data = git_tree_without_api(repository, commit)
    else:
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in {403, 429}:
                raise
            USE_GIT_TREE = True
            print("公共 API 限流，改用 Git 对象元数据核对固定提交。", flush=True)
            data = git_tree_without_api(repository, commit)
    if data.get("truncated"):
        raise ValueError("GitHub 返回了截断的 Git 树，不能据此声明子模块完整")
    atomic_json(cache, data)
    return data


def complete(parent: dict, root: Path, errors: list, depth: int = 0) -> int:
    """递归补齐一个父快照的子模块；已保存的数据只校验，不覆盖。"""
    module_file = root / ".gitmodules"
    if not module_file.is_file() or not module_file.read_text().strip():
        return 0
    if depth >= 4:
        errors.append({"parentId": parent["id"], "error": "超过四层子模块递归上限"})
        return 0
    configuration = configparser.ConfigParser(interpolation=None)
    configuration.read(module_file)
    tree = git_tree(parent["repository"], parent["commit"])
    gitlinks = {item["path"]: item["sha"] for item in tree["tree"] if item["mode"] == "160000"}
    count = 0
    for section in configuration.sections():
        try:
            relative = configuration[section]["path"]
            parts = PurePosixPath(relative)
            if parts.is_absolute() or ".." in parts.parts:
                raise ValueError("子模块路径越界")
            url = configuration[section]["url"]
            if url.startswith("."):
                url = urllib.parse.urljoin(f"https://github.com/{parent['repository']}/", url)
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme != "https" or parsed.netloc != "github.com":
                raise ValueError(f"仅支持公开 GitHub HTTPS 子模块：{url}")
            repository = parsed.path.strip("/").removesuffix(".git")
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
                raise ValueError("子模块仓库地址格式不正确")
            commit = gitlinks.get(relative)
            if not commit:
                raise ValueError(".gitmodules 中的路径没有对应的 gitlink，不猜测分支提交")
            key = hashlib.sha256(f"{parent['id']}:{relative}".encode()).hexdigest()[:16]
            identifier = f"submodule--{key}"
            receipt_path = LIBRARY / "state" / "submodules" / (identifier + ".json")
            archive = LIBRARY / "archives" / f"{identifier}--{commit[:12]}.tar.gz"
            destination = root / relative
            if receipt_path.exists():
                record = json.loads(receipt_path.read_text())
                if record["commit"] != commit or sha256(archive) != record["archiveSha256"]:
                    raise ValueError("已有子模块回执与固定提交或压缩包校验不符")
                if not destination.is_dir():
                    raise ValueError("已有回执对应的子模块目录缺失")
            else:
                archive_url = f"https://codeload.github.com/{repository}/tar.gz/{commit}"
                if archive.exists():
                    digest, size = sha256(archive), archive.stat().st_size
                else:
                    digest, size = download(archive_url, archive, 2048 * 1024**2)
                # GitHub 归档有时留下空的子模块占位目录，只移除确认为空的占位目录。
                if destination.is_dir() and not any(destination.iterdir()):
                    destination.rmdir()
                extract(archive, destination, 8192 * 1024**2)
                record = {"id": identifier, "parentId": parent["id"],
                          "submodulePath": relative, "repository": repository, "commit": commit,
                          "sourceUrl": f"https://github.com/{repository}", "downloadedAt": now(),
                          "localPath": destination.relative_to(LIBRARY).as_posix(),
                          "archiveUrl": archive_url, "archivePath": archive.relative_to(LIBRARY).as_posix(),
                          "archiveSha256": digest, "archiveBytes": size,
                          "status": "downloaded_submodule", "runtimeValidation": "未构建、未运行"}
                atomic_json(receipt_path, record)
            count += 1
            print(f"已补齐 {parent['id']} / {relative} @ {commit[:12]}", flush=True)
            count += complete(record, destination, errors, depth + 1)
        except Exception as error:
            errors.append({"parentId": parent["id"], "section": section, "error": str(error)})
            print(f"子模块失败 {parent['id']} / {section}：{error}", flush=True)
    return count


def complete_lfs_snapshots(parents: list[dict], errors: list) -> int:
    """补齐 Git LFS 指针所代表的原始资源，验证对象 SHA256 与字节数。

    只扫描小于 1 KiB 的指针候选，不将大二进制文件整体读入内存。
    真实图片/视频由 GitHub 原始媒体接口提供；先校验再替换本地指针。
    保留指针全文和下载回执，原始仓库压缩包也仍包含原始指针。
    """
    submodules = [json.loads(path.read_text())
                  for path in (LIBRARY / "state" / "submodules").glob("*.json")]
    owners = sorted(parents + submodules, key=lambda item: len(item["localPath"]), reverse=True)
    count = 0
    for parent in parents:
        root = LIBRARY / parent["localPath"]
        for path in root.rglob("*"):
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024:
                continue
            pointer = path.read_text(errors="replace")
            if not pointer.startswith("version https://git-lfs.github.com/spec/v1\n"):
                continue
            try:
                digest_match = re.search(r"^oid sha256:([0-9a-f]{64})$", pointer, re.MULTILINE)
                size_match = re.search(r"^size ([0-9]+)$", pointer, re.MULTILINE)
                if not digest_match or not size_match:
                    raise ValueError("LFS 指针缺少有效的 SHA256 或字节数")
                digest, expected_size = digest_match.group(1), int(size_match.group(1))
                if expected_size > 2048 * 1024**2:
                    raise ValueError("LFS 对象超过 2048 MiB 上限")
                owner = next(item for item in owners if path.is_relative_to(LIBRARY / item["localPath"]))
                relative = path.relative_to(LIBRARY / owner["localPath"]).as_posix()
                encoded = urllib.parse.quote(relative, safe="/")
                url = f"https://media.githubusercontent.com/media/{owner['repository']}/{owner['commit']}/{encoded}"
                temporary = path.with_name(path.name + ".lfs-download")
                try:
                    actual_digest, actual_size = download(url, temporary, max(expected_size, 1024))
                    if actual_digest != digest or actual_size != expected_size:
                        raise ValueError("LFS 对象与 Git 指针中的 SHA256 或字节数不符")
                    temporary.replace(path)
                finally:
                    temporary.unlink(missing_ok=True)
                identifier = hashlib.sha256(path.relative_to(LIBRARY).as_posix().encode()).hexdigest()[:20]
                record = {"id": "lfs--" + identifier, "ownerId": owner["id"],
                          "sourceUrl": url, "repository": owner["repository"], "commit": owner["commit"],
                          "localPath": path.relative_to(LIBRARY).as_posix(), "sha256": digest,
                          "bytes": expected_size, "originalPointer": pointer, "downloadedAt": now()}
                atomic_json(LIBRARY / "state" / "lfs" / (identifier + ".json"), record)
                count += 1
                print(f"已补齐 LFS {owner['id']} / {relative}：{expected_size} 字节", flush=True)
            except Exception as error:
                errors.append({"localPath": path.relative_to(LIBRARY).as_posix(), "error": str(error)})
    # 再运行时无需重复联网，仍会复算以前补齐对象的 SHA256。
    receipts = list((LIBRARY / "state" / "lfs").glob("*.json"))
    for receipt in receipts:
        record = json.loads(receipt.read_text())
        path = LIBRARY / record["localPath"]
        if (not path.is_file() or path.stat().st_size != record["bytes"]
                or sha256(path) != record["sha256"]):
            errors.append({"localPath": record["localPath"], "error": "LFS 资源复核失败"})
    atomic_json(LIBRARY / "state" / "lfs-last-run.json",
                {"checkedAt": now(), "downloadedLfsFiles": len(receipts), "errors": errors})
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--include-lfs", action="store_true", help="同时补齐 Git LFS 图片、视频等资源")
    args = parser.parse_args()
    errors, count = [], 0
    parents = []
    for path in sorted((LIBRARY / "state" / "receipts").glob("*.json")):
        parent = json.loads(path.read_text())
        if args.only and parent["sourceId"] not in args.only:
            continue
        parents.append(parent)
        try:
            count += complete(parent, LIBRARY / parent["localPath"], errors)
        except Exception as error:
            errors.append({"parentId": parent["id"], "error": str(error)})
    report = {"checkedAt": now(), "completedSubmodules": count, "errors": errors}
    atomic_json(LIBRARY / "state" / "submodules-last-run.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.include_lfs:
        lfs_errors = []
        lfs_count = complete_lfs_snapshots(parents, lfs_errors)
        print(f"本轮补充 LFS 资源 {lfs_count} 个，失败 {len(lfs_errors)} 项。", flush=True)
        errors.extend(lfs_errors)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
