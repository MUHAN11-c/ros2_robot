#!/usr/bin/env python3
"""将公开 ROS 2 教程与示例按固定提交下载到本地，不执行第三方代码。

输入：references/catalog.json；可用 --only 指定仓库标识。
输出：原始 tar.gz、独立源码目录、下载回执和失败记录。
单位：容量限制使用 MiB（1 MiB = 1024**2 字节），网络超时使用秒。
顺序：读取分支 → 锁定提交 → 流式下载并计算 SHA256 → 安全解包 → 写回执。
边界：不存在的发行版分支单独登记；网络失败可重试；已有目录不被覆盖。
下载源码保留上游原貌，中文教学注释应在后续教材副本中添加。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo


HUB = Path(__file__).resolve().parents[1]
LIBRARY = HUB / "references"
# 只探测已发布的 ROS 2 发行版与 Rolling；不下载开发者临时分支。
DISTROS = ["jazzy", "humble", "lyrical", "kilted", "rolling", "iron",
           "galactic", "foxy", "eloquent", "dashing", "crystal", "bouncy", "ardent"]


def now() -> str:
    """所有回执明确采用用户所在的北京时间，避免主机时区混淆。"""
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def atomic_json(path: Path, value: object) -> None:
    """先写临时文件再替换；中断时不会留下半份 JSON 清单。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def sha256(path: Path) -> str:
    """分块计算压缩包摘要；不把大文件一次性读入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover(source: dict, refresh: bool) -> dict:
    """读取公开 Git 分支；只使用显式 URL，不读取凭据或运行仓库脚本。"""
    repository = source["repository"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError(f"非法公开仓库标识：{repository}")
    cache = LIBRARY / "state" / "refs" / (source["id"] + ".json")
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    # 禁用交互凭据助手；公开仓库不存在时直接失败，不弹出登录对话框。
    command = ["git", "-c", "credential.helper=", "ls-remote", "--symref",
               f"https://github.com/{repository}.git", "HEAD", "refs/heads/*"]
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=90, env=environment, check=True)
    branches, default = {}, None
    for line in result.stdout.splitlines():
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            default = line.split("\t")[0].removeprefix("ref: refs/heads/")
        else:
            fields = line.split("\t")
            if len(fields) == 2 and fields[1].startswith("refs/heads/"):
                branches[fields[1].removeprefix("refs/heads/")] = fields[0]
    if not branches:
        raise ValueError("未发现可用的公开分支")
    value = {"repository": repository, "queriedAt": now(),
             "defaultBranch": default, "branches": branches}
    atomic_json(cache, value)
    return value


def choose_refs(source: dict, remote: dict) -> tuple[list[str], list[str]]:
    """返回实际分支和缺失分支；回退分支始终以真实名称保存。"""
    available = remote["branches"]
    if source.get("mode") == "all_ros_distros":
        return ([ref for ref in DISTROS if ref in available],
                [ref for ref in DISTROS if ref not in available])
    for ref in source.get("prefer", []):
        if ref in available:
            return [ref], []
    if source.get("allowDefault", True) and remote.get("defaultBranch") in available:
        return [remote["defaultBranch"]], []
    raise ValueError("指定分支不存在，且未允许使用默认分支")


def download(url: str, target: Path, limit: int) -> tuple[str, int]:
    """按字节数限制下载，失败重试三次；仅完整文件可成为最终压缩包。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "ROS2-Offline-Reference-Download/1.0",
                "Accept": "application/octet-stream"})
            digest, size = hashlib.sha256(), 0
            with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    size += len(block)
                    if size > limit:
                        raise ValueError(f"压缩包超过容量上限 {limit // 1024**2} MiB")
                    digest.update(block)
                    output.write(block)
            partial.replace(target)
            return digest.hexdigest(), size
        except (OSError, urllib.error.URLError, TimeoutError):
            partial.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("下载重试异常结束")


def extract(archive: Path, destination: Path, expanded_limit: int) -> list[str]:
    """在暂存区安全解包，校验路径、链接与解压后容量，再原子移动。

    不执行安装器；拒绝设备文件和越界链接。归档内的相对软链接交由
    Python 的 data 过滤器校验，保留合法链接以保持上游源码结构。
    Git 子模块不在 GitHub 源码归档中，另由索引明确记录，不能算作已下载。
    """
    # 暂存区与目标放在同一文件系统，保证最后的 rename 是原子操作。
    # /tmp 可能是独立挂载，不能假定它与工作区之间可直接 rename。
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".extract-", dir=destination.parent))
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            roots = set()
            total = 0
            for member in members:
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or not path.parts:
                    raise ValueError(f"不安全的归档路径：{member.name}")
                roots.add(path.parts[0])
                total += max(member.size, 0)
            if len(roots) != 1 or total > expanded_limit:
                raise ValueError("归档根目录数量或解压容量不符合限制")
            bundle.extractall(staging, filter="data")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"目标目录已存在，拒绝覆盖：{destination}")
        (staging / roots.pop()).rename(destination)
        return []
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def fetch_snapshot(source: dict, ref: str, commit: str, args: argparse.Namespace) -> dict:
    """下载一个仓库的一个发行版快照，回执中保留源码与压缩包校验信息。"""
    identifier = f"{source['id']}--{ref.replace('/', '__')}"
    receipt = LIBRARY / "state" / "receipts" / (identifier + ".json")
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        if (previous.get("commit") == commit
                and (LIBRARY / previous["localPath"]).is_dir()
                and (LIBRARY / previous["archivePath"]).is_file()
                and sha256(LIBRARY / previous["archivePath"]) == previous["archiveSha256"]):
            return previous
    # 提交哈希加入目录名；后续上游变更不会覆盖用户已保存的旧版本。
    suffix = f"{identifier}--{commit[:12]}"
    archive = LIBRARY / "archives" / (suffix + ".tar.gz")
    destination = LIBRARY / "sources" / source["category"] / source["id"] / f"{ref.replace('/', '__')}--{commit[:12]}"
    url = f"https://codeload.github.com/{source['repository']}/tar.gz/{commit}"
    if archive.exists():
        digest, size = sha256(archive), archive.stat().st_size
    else:
        digest, size = download(url, archive, args.max_archive_mib * 1024**2)
    if not destination.exists():
        extract(archive, destination, args.max_expanded_mib * 1024**2)
    record = {"id": identifier, "sourceId": source["id"], "title": source["title"],
              "repository": source["repository"], "sourceUrl": f"https://github.com/{source['repository']}",
              "category": source["category"], "ref": ref, "commit": commit,
              "downloadedAt": now(), "archiveUrl": url,
              "archivePath": archive.relative_to(LIBRARY).as_posix(),
              "archiveSha256": digest, "archiveBytes": size,
              "localPath": destination.relative_to(LIBRARY).as_posix(),
              "status": "downloaded", "runtimeValidation": "未构建、未运行"}
    atomic_json(receipt, record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", help="仅处理这些 catalog 标识；省略则处理全部")
    parser.add_argument("--jobs", type=int, default=4, help="同时联网任务数，默认 4，上限 8")
    parser.add_argument("--refresh", action="store_true", help="重新查询上游分支；默认复用本次锁定结果")
    parser.add_argument("--max-archive-mib", type=int, default=2048)
    parser.add_argument("--max-expanded-mib", type=int, default=8192)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 8 or min(args.max_archive_mib, args.max_expanded_mib) <= 0:
        parser.error("并发数须为 1–8，容量限制须为正数")
    catalog = json.loads((LIBRARY / "catalog.json").read_text())
    sources = [item for item in catalog["sources"]
               if not args.only or item["id"] in args.only]
    if args.only and set(args.only) - {source["id"] for source in sources}:
        parser.error("--only 包含未知的 catalog 标识")
    errors, missing, tasks = [], {}, []
    print(f"开始：{len(sources)} 个仓库；并发 {args.jobs}；时间 {now()}", flush=True)
    # 分支查询是独立只读操作，可并行；每个快照的下载和解包仍顺序执行。
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(discover, source, args.refresh): source for source in sources}
        for future in concurrent.futures.as_completed(futures):
            source = futures[future]
            try:
                remote = future.result()
                refs, absent = choose_refs(source, remote)
                missing[source["id"]] = absent
                tasks.extend((source, ref, remote["branches"][ref]) for ref in refs)
                print(f"已锁定 {source['id']}：{', '.join(refs)}", flush=True)
            except Exception as error:
                detail = getattr(error, "stderr", None) or str(error)
                errors.append({"sourceId": source["id"], "stage": "discover", "error": detail[:1000]})
                print(f"查询失败 {source['id']}：{detail[:200]}", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(fetch_snapshot, source, ref, commit, args): (source, ref)
                   for source, ref, commit in tasks}
        for future in concurrent.futures.as_completed(futures):
            source, ref = futures[future]
            try:
                record = future.result()
                print(f"已下载 {record['id']}：{record['archiveBytes'] / 1024**2:.1f} MiB", flush=True)
            except Exception as error:
                errors.append({"sourceId": source["id"], "ref": ref,
                               "stage": "download", "error": str(error)[:1000]})
                print(f"下载失败 {source['id']} [{ref}]：{error}", flush=True)
    report = {"finishedAt": now(), "selectedSources": [item["id"] for item in sources],
              "requestedSnapshots": len(tasks), "missingDistroBranches": missing, "errors": errors}
    atomic_json(LIBRARY / "state" / "last-run.json", report)
    # 分次补下载时保留所有探测的缺失分支证据，便于汇总与明确覆盖边界。
    for identifier, absent in missing.items():
        atomic_json(LIBRARY / "state" / "coverage" / (identifier + ".json"),
                    {"sourceId": identifier, "checkedAt": now(), "absentBranches": absent})
    print(f"结束：{len(tasks)} 个快照任务，失败 {len(errors)} 项。", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
