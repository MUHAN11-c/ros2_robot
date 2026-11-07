#!/usr/bin/env python3
"""用标准库审计显式安装前缀；不source脚本、不运行产物或Docker。

输入：--prefix、额外只读--allow-root、--underlay、逐个--source-file/--package。
输出：文件/链接SHA、链接外部目标、指定包版本、有限环境变量与ELF直接依赖JSON。
--copy-demo只把已清点条目复制到自建/tmp，保留链接，再检查外部依赖仍存在。
所有大小单位为字节，时间上限为monotonic秒；默认报告/tmp/deployment-audit.json。
不遍历HOME、凭据目录，不跟随目录链接递归，不执行ldd、安装器或容器。
文件完整性和依赖清点不证明跨机可运行；无外部链接也不能推出自包含。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import stat
import struct
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
HUB = HERE.parents[1]
ENV_ALLOWLIST = ("ROS_DISTRO", "ROS_DOMAIN_ID", "RMW_IMPLEMENTATION",
                 "ROS_AUTOMATIC_DISCOVERY_RANGE", "AMENT_PREFIX_PATH",
                 "CMAKE_PREFIX_PATH", "COLCON_PREFIX_PATH", "LD_LIBRARY_PATH", "PYTHONPATH")
DENIED_PARTS = {".ssh", ".aws", ".azure", ".gnupg", ".kube", ".docker", ".git", ".config",
                ".netrc", ".npmrc", ".pypirc", "credentials", "keyrings", "secrets", "id_rsa", "id_ed25519"}
MAX_LINK_HOPS = 24


class AuditLimit(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sensitive(path):
    """按名字排除凭据；不是内容扫描，也不读取被排除文件来判断是否真的含密钥。"""
    return any(part in DENIED_PARTS or part.startswith(".env") or
               part.lower().endswith((".pem", ".key")) for part in Path(path).parts)


def inside(path, root):
    return path == root or path.is_relative_to(root)


def scope_root(value):
    """显式路径可位于用户工作区；禁止把整个HOME、根目录或其上级当扫描范围。"""
    path = Path(value).expanduser().absolute()
    if sensitive(path):
        raise ValueError("不允许凭据名称作为审计范围")
    path = path.resolve(strict=True)
    home = Path.home().resolve()
    if (not path.is_dir() or path in {Path("/"), Path("/home"), Path("/tmp"), Path("/opt"), home}
            or path.parts[1:2] in [("etc",), ("proc",), ("sys",), ("dev",), ("run",), ("root",)]
            or sensitive(path)):
        raise ValueError("范围必须是具体项目/安装目录，不能是根、HOME或凭据目录")
    return path


class Budget:
    def __init__(self, entries=1000, per_file=16 * 1024 * 1024,
                 total=96 * 1024 * 1024, seconds=10.0):
        self.max_entries, self.per_file, self.max_total = entries, per_file, total
        self.entries = self.bytes = 0
        self.started = time.monotonic()
        self.deadline = self.started + seconds

    def check(self):
        if time.monotonic() > self.deadline:
            raise AuditLimit("到达单调扫描软期限；本次不能标为完整清点")

    def entry(self):
        self.check()
        self.entries += 1
        if self.entries > self.max_entries:
            raise AuditLimit("目录条目超过上限；没有继续扫描")

    def read(self, path):
        """只打开最终普通文件且不跟随最终symlink；前后fstat发现变化即停止。

        路径来自显式可信工作区；allowlist是防误读范围，不是抵御恶意并发改路径的沙箱。
        原生文件系统调用不可被软期限抢占，读者可再用外层timeout保护。
        """
        self.check()
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode), "只读取普通文件，拒绝设备/FIFO/socket")
            if before.st_size > self.per_file or self.bytes + before.st_size > self.max_total:
                raise AuditLimit("文件或累计读取字节超限")
            chunks, amount = [], 0
            while True:
                self.check()
                chunk = stream.read(min(65536, self.per_file + 1 - amount))
                if not chunk:
                    break
                chunks.append(chunk)
                amount += len(chunk)
                if amount > self.per_file:
                    raise AuditLimit("读取期间文件超过单文件上限")
            after = os.fstat(stream.fileno())
            require((before.st_ino, before.st_size, before.st_mtime_ns) ==
                    (after.st_ino, after.st_size, after.st_mtime_ns), "文件读取期间发生变化")
            result = b"".join(chunks)
            require(len(result) == before.st_size, "文件长度与读取快照不一致")
            self.bytes += len(result)
            return result


def resolve_allowed(path, roots, budget):
    """逐个路径分量解析，最多24次链接；越出allowlist的目标不读取内容。

    只对给定路径做lstat/readlink，不枚举外部目录。已允许根的祖先只用于解析该路径。
    """
    candidate = Path(os.path.normpath(str(Path(path).absolute())))
    if sensitive(candidate) or not any(inside(candidate, root) for root in roots):
        return None, "outside_allowlist_or_sensitive", []
    pending, current, hops, chain = list(candidate.parts[1:]), Path("/"), 0, []
    steps = 0
    while pending:
        budget.check()
        steps += 1
        if steps > 256:
            return None, "path_component_budget", chain
        current /= pending.pop(0)
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return None, "missing_target", chain
        if stat.S_ISLNK(mode):
            hops += 1
            if hops > MAX_LINK_HOPS:
                return None, "link_hop_limit", chain
            raw = os.readlink(current)
            if len(raw) > 4096:
                return None, "link_text_too_long", chain
            target = Path(raw) if os.path.isabs(raw) else current.parent / raw
            target = Path(os.path.normpath(str(target.joinpath(*pending))))
            chain.append({"link": str(current), "text": raw, "nextPath": str(target)})
            if sensitive(target) or not any(inside(target, root) for root in roots):
                return None, "outside_allowlist_or_sensitive", chain
            pending, current = list(target.parts[1:]), Path("/")
    return current, "resolved", chain


def elf_summary(data):
    """只解析有界ELF64小端section信息；不是动态装载器，不递归解析共享库。

    DT_NEEDED是直接soname，不能由此断言依赖均存在。无section或其他格式返回未覆盖。
    """
    if not data.startswith(b"\x7fELF"):
        return None
    result = {"format": "ELF", "needed": [], "runpath": [], "rpath": [],
              "transitiveResolutionPerformed": False}
    if len(data) < 64 or data[4:6] != b"\x02\x01":
        return {**result, "scan": "unsupported_or_truncated_elf_not_dependency_free"}
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", data)
    machine, offset, entry_size, count = header[2], header[6], header[11], header[12]
    result["machine"] = {62: "x86_64", 183: "aarch64"}.get(machine, str(machine))
    if not count or count > 4096 or entry_size < 64 or offset + entry_size * count > len(data):
        return {**result, "scan": "no_supported_section_table_not_dependency_free"}
    sections = [struct.unpack_from("<IIQQQQIIQQ", data, offset + i * entry_size)
                for i in range(count)]
    dynamic_found = False
    for section in sections:
        if section[1] != 6:
            continue
        dynamic_found = True
        location, size, linked = section[4], section[5], section[6]
        if linked >= count or location + size > len(data) or size // 16 > 4096:
            return {**result, "scan": "invalid_dynamic_section"}
        strings = sections[linked]
        start, string_size = strings[4], strings[5]
        if start + string_size > len(data):
            return {**result, "scan": "invalid_dynamic_strings"}
        for position in range(location, location + size - 15, 16):
            tag, value = struct.unpack_from("<qQ", data, position)
            if tag not in (1, 15, 29):
                continue
            if value >= string_size:
                return {**result, "scan": "invalid_dynamic_string_offset"}
            end = data.find(b"\0", start + value, min(start + string_size, start + value + 4096))
            if end < 0:
                return {**result, "scan": "unterminated_dynamic_string"}
            text = data[start + value:end].decode("utf-8", errors="replace")
            result[{1: "needed", 15: "rpath", 29: "runpath"}[tag]].append(text)
    return {**result, "scan": "dynamic_sections_read" if dynamic_found else "no_dynamic_section"}


def file_evidence(path, roots, budget):
    resolved, status, chain = resolve_allowed(path, roots, budget)
    result = {"path": str(path), "resolutionStatus": status, "linkChain": chain}
    if resolved is None:
        return result
    result["resolvedPath"] = str(resolved)
    if not stat.S_ISREG(resolved.lstat().st_mode):
        result["resolutionStatus"] = "not_regular_file"
        return result
    data = budget.read(resolved)
    result.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    elf = elf_summary(data)
    if elf:
        result["elf"] = elf
    return result


def inventory(prefix, roots, budget):
    """深度遍历普通目录；目录链接仅记录，绝不递归到链接目标。"""
    stack, rows, skipped = [prefix], [], []
    while stack:
        directory = stack.pop()
        entries = []
        with os.scandir(directory) as scan:
            for entry in scan:
                budget.entry()
                entries.append(entry)
        for entry in sorted(entries, key=lambda item: item.name):
            path = Path(entry.path)
            relative = path.relative_to(prefix).as_posix()
            if sensitive(path):
                skipped.append({"relativePath": relative, "reason": "excluded_sensitive_name"})
                continue
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                text = os.readlink(path)
                info = file_evidence(path, roots, budget)
                target = info.get("resolvedPath")
                rows.append({"relativePath": relative, "kind": "symlink", "linkText": text,
                             "linkTextSha256": hashlib.sha256(text.encode()).hexdigest(),
                             "targetOutsidePrefix": None if target is None else not inside(Path(target), prefix),
                             "targetEvidence": info})
            elif stat.S_ISDIR(mode):
                rows.append({"relativePath": relative, "kind": "directory"})
                stack.append(path)
            elif stat.S_ISREG(mode):
                info = file_evidence(path, roots, budget)
                rows.append({"relativePath": relative, "kind": "file", "evidence": info})
            else:
                skipped.append({"relativePath": relative, "reason": "not_regular_file_or_directory"})
    return {"prefix": str(prefix), "entries": rows, "skipped": skipped,
            "counts": {"files": sum(x["kind"] == "file" for x in rows),
                       "links": sum(x["kind"] == "symlink" for x in rows),
                       "externalLinks": sum(x.get("targetOutsidePrefix") is True for x in rows),
                       "unresolvedLinks": sum(x["kind"] == "symlink" and x.get("targetOutsidePrefix") is None for x in rows)}}


def setup_literals(prefix, roots, budget):
    """只读这几个已知环境入口，提取字面prefix；不eval或source任何内容。"""
    records = []
    pattern = re.compile(r"(?:COLCON_CURRENT_PREFIX)=['\"]?(/[^\s'\"]+)")
    for name in ("setup.bash", "setup.sh", "local_setup.bash", "local_setup.sh"):
        path = prefix / name
        resolved, _, _ = resolve_allowed(path, roots, budget)
        if resolved is None:
            continue
        data = budget.read(resolved)
        if len(data) > 65536:
            raise AuditLimit("环境入口超出64KiB文本读取范围")
        for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            for match in pattern.finditer(line):
                records.append({"file": name, "line": number, "literalPrefix": match.group(1)})
    return records


def copy_evidence(original, roots, settings):
    """只复制有限清单中的条目，保留链接文本；不移动/删除原source、build或underlay。"""
    require(not original["skipped"], "副本实验要求原始清点无排除项；否则不冒充完整install复制")
    with tempfile.TemporaryDirectory(prefix="ros2-deployment-copy-") as temporary:
        destination = Path(temporary) / "install"
        destination.mkdir()
        origin = Path(original["prefix"])
        copy_budget = Budget(**settings)
        for entry in sorted(original["entries"], key=lambda row: (len(Path(row["relativePath"]).parts), row["relativePath"])):
            copy_budget.check()
            source, target = origin / entry["relativePath"], destination / entry["relativePath"]
            if entry["kind"] == "directory":
                target.mkdir(exist_ok=True)
            elif entry["kind"] == "symlink":
                target.symlink_to(entry["linkText"])
            else:
                data = copy_budget.read(source)
                require(hashlib.sha256(data).hexdigest() == entry["evidence"]["sha256"],
                        "原文件在复制前变化")
                target.write_bytes(data)
                target.chmod(stat.S_IMODE(source.lstat().st_mode))
        audit = inventory(destination, [destination, *roots], Budget(**settings))
        before = {e["relativePath"]: e for e in original["entries"]}
        for entry in audit["entries"]:
            old = before[entry["relativePath"]]
            if entry["kind"] == "symlink":
                require(entry["linkText"] == old["linkText"], "保留链接文本失败")
                require(entry["targetEvidence"].get("sha256") == old["targetEvidence"].get("sha256"),
                        "链接目标在副本实验期间发生变化")
            if entry["kind"] == "file":
                require(entry["evidence"]["sha256"] == old["evidence"]["sha256"], "副本文件SHA不同")
        require(set(before) == {e["relativePath"] for e in audit["entries"]}, "复制条目集合不同")
        return {"temporaryCopyPath": str(destination), "linkTextsAndFilesMatched": True,
                "originalSourceBuildUnderlayUntouched": True, "copyAudit": audit,
                "conclusion": "副本仍可指向原source/build；同机目标存在不证明换机时也存在。",
                "copiedProgramsExecuted": False, "crossMachineExecutionPerformed": False,
                "temporaryCopyRemovedAfterReturn": True}


def self_test():
    """用自建/tmp小夹具检查链接/范围/上限；不读取真实凭据或启动ROS。"""
    rows = []
    with tempfile.TemporaryDirectory(prefix="deployment-audit-selftest-") as temporary:
        base = Path(temporary); root = base / "prefix"; root.mkdir()
        outside = base / "outside"; outside.mkdir()
        (root / "data.txt").write_text("样本", encoding="utf-8")
        (outside / "source.txt").write_text("fixture", encoding="utf-8")
        (root / "inside").symlink_to("data.txt")
        (root / "external").symlink_to(outside / "source.txt")
        (root / ".env").write_text("synthetic-excluded-fixture")
        result = inventory(root, [root, outside], Budget())
        require(result["counts"]["links"] == 2 and result["counts"]["externalLinks"] == 1,
                "内/外部链接分类失败")
        require(len(result["skipped"]) == 1 and result["skipped"][0]["reason"] == "excluded_sensitive_name",
                "敏感名字排除失败")
        rows.append({"case": "internal_external_and_sensitive_exclusion", "passed": True})
        resolved, status, _ = resolve_allowed(root / "external", [root], Budget())
        require(resolved is None and status == "outside_allowlist_or_sensitive", "越界目标不应打开")
        rows.append({"case": "unallowed_target_not_read", "passed": True})
        (root / "loop_a").symlink_to("loop_b"); (root / "loop_b").symlink_to("loop_a")
        require(resolve_allowed(root / "loop_a", [root], Budget())[1] == "link_hop_limit", "链接环未有界停止")
        rows.append({"case": "link_loop_hop_budget", "passed": True})
        for name, action in [("entry_budget", lambda: inventory(root, [root], Budget(entries=1))),
                             ("file_byte_budget", lambda: Budget(per_file=1).read(root / "data.txt"))]:
            try:
                action()
            except AuditLimit:
                rows.append({"case": name, "passed": True})
            else:
                raise AssertionError(name + "没有拒绝超限")
        require(elf_summary(b"plain") is None and "unsupported" in elf_summary(b"\x7fELF")["scan"],
                "截断ELF不应伪装无依赖")
        rows.append({"case": "truncated_elf_not_dependency_free", "passed": True})
        for name in (Path.home(), Path("/"), Path("/etc")):
            try:
                scope_root(name)
            except ValueError:
                rows.append({"case": "reject_broad_scope_" + (name.name or "root"), "passed": True})
            else:
                raise AssertionError("不应允许HOME/系统范围")
    return rows


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prefix", type=Path)
    parser.add_argument("--allow-root", type=Path, action="append", default=[])
    parser.add_argument("--underlay", type=Path, action="append", default=[])
    parser.add_argument("--source-file", type=Path, action="append", default=[])
    parser.add_argument("--package", action="append", default=[])
    parser.add_argument("--copy-demo", action="store_true")
    parser.add_argument("--host-signal-report", type=Path, help="可选/tmp实际宿主信号检查报告，只读合并")
    parser.add_argument("--max-entries", type=int, default=1000)
    parser.add_argument("--max-file-mib", type=float, default=16.0)
    parser.add_argument("--max-total-mib", type=float, default=96.0)
    parser.add_argument("--timeout-s", type=float, default=10.0)
    parser.add_argument("--report", type=Path, default=Path("/tmp/deployment-audit.json"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test and args.prefix is None:
        parser.error("需要显式--prefix；没有自动工作空间或HOME搜索")
    if not 1 <= args.max_entries <= 5000:
        parser.error("max-entries须为1..5000")
    for value, low, high in [(args.max_file_mib, 0.001, 64), (args.max_total_mib, 0.001, 256),
                             (args.timeout_s, 0.1, 60)]:
        if not math.isfinite(value) or not low <= value <= high:
            parser.error("大小/期限须为帮助范围内的有限正数")
    if len(args.package) > 32 or len(args.source_file) > 32 or len(args.allow_root) > 16 or len(args.underlay) > 8:
        parser.error("包/源码/范围数量超过教学上限")
    if any(not re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in args.package):
        parser.error("package须为普通ROS包名，不接受路径")
    return args


def teaching_summary(result):
    """把本次原始清点转换为教材表；数值均取当前结果，不写死实验计数。

    输入为内存中的实际报告，输出为附加字段；不新增文件读取或运行产物。
    表中的“外部”仅相对于各自install根，不是对依赖是否已安装的判定。
    """
    original = result.get("originalAudit")
    if original is None:
        return
    copy = result.get("copyDemo")
    copy_audit = copy.get("copyAudit") if copy else None
    rows = []
    for name, audit in (("原安装前缀", original), ("保留链接的临时副本", copy_audit)):
        if audit is None:
            continue
        counts = audit["counts"]
        rows.append([name, counts["files"], counts["links"], counts["externalLinks"],
                     counts["unresolvedLinks"], "未运行副本" if name.startswith("保留") else "仅文件清点"])
    tables = [{"id": "prefix-copy", "title": "实际安装前缀与保留链接的副本",
               "columns": ["范围", "普通文件", "符号链接", "前缀外链接", "未解析链接", "验证层次"],
               "rows": rows,
               "caption": "条数来自有限清点；SHA/链接文本一致不证明独立部署或跨机可运行。"}]
    target_rows = []
    roots = result.get("parameters", {}).get("allowRoots", [])[1:]
    for root in roots:
        matches = [entry for entry in original["entries"] if entry["kind"] == "symlink"
                   and entry.get("targetOutsidePrefix") is True
                   and entry["targetEvidence"].get("resolvedPath")
                   and inside(Path(entry["targetEvidence"]["resolvedPath"]), Path(root))]
        if matches:
            target_rows.append([root, len(matches), ", ".join(row["relativePath"] for row in matches[:3])])
    tables.append({"id": "external-targets", "title": "外部链接实际解析到的显式允许根",
                   "columns": ["目标根", "链接数", "相对安装入口举例（最多3项）"], "rows": target_rows,
                   "caption": "仅归类已解析的直接清点条目；不递归展开underlay，也不证明全部传递依赖。"})
    checks = [
        {"id": "ordinary-file-sha", "passed": all(entry["evidence"].get("sha256") for entry in original["entries"]
         if entry["kind"] == "file"), "meaning": "原前缀所有已清点普通文件均有实际字节SHA。"},
        {"id": "copy-not-executed", "passed": copy is None or copy["copiedProgramsExecuted"] is False,
         "meaning": "副本没有运行；这项为实验边界记录，不是运行成功断言。"}]
    if copy:
        removed = not Path(copy["temporaryCopyPath"]).exists()
        require(removed, "自建临时副本返回后仍存在")
        checks.extend([
            {"id": "copy-files-links-targets-match", "passed": copy["linkTextsAndFilesMatched"],
             "meaning": "副本普通文件SHA、链接文本和本机可解析目标SHA匹配。"},
            {"id": "temporary-copy-removed", "passed": removed,
             "meaning": "只删除自建临时副本，没有移除原source/build/underlay。"}])
    host = result.get("hostSignal")
    if host:
        # 这里引用独立宿主实测；没有再次启动ROS节点，也不等同Docker PID1验证。
        checks.append({"id": "host-direct-exec-term", "passed": host["passed"] and
                       host["samePidBecameNode"] and host["childrenBeforeSignal"] == [] and
                       host["signalsSent"] == ["SIGTERM"] and host["exitCode"] == 0 and host["pidAbsentAfterReap"],
                       "meaning": "原安装合成节点同PID直接exec，一次TERM后exit0并回收。"})
        tables.append({"id": "host-signal", "title": "原安装节点的宿主直接exec信号正例",
                       "columns": ["PID", "同PID成为节点", "信号前孩子数", "发送信号", "退出码", "回收耗时（秒）"],
                       "rows": [[host["pid"], host["samePidBecameNode"], len(host["childrenBeforeSignal"]),
                                 ", ".join(host["signalsSent"]), host["exitCode"], host["signalToExitS"]]],
                       "caption": "耗时为该次宿主观测；未运行Docker或副本，不构成设备停车验证。"})
    require(all(check["passed"] for check in checks), "教学汇总的精确一致性断言失败")
    command = list(result["invocation"])
    if "--report" in command:
        command[command.index("--report") + 1] = "/tmp/deployment-local-audit.json"
    result.update(assertions=checks, teachingTables=tables,
                  teachingValidation="已实际清点显式安装前缀，复制并核对保留链接的临时副本；另引用原节点宿主exec/TERM实测。Docker、复制产物及跨机运行未执行。",
                  teachingCommand=shlex.join(command),
                  teachingCommandNote="路径是本机原构建记录；换机须先构建组件实验并替换明确前缀。报告另存/tmp；若没有宿主报告，去掉--host-signal-report，不能补称信号已验证。")


def main():
    args = arguments()
    if args.self_test:
        print(json.dumps({"passed": True, "checks": self_test()}, ensure_ascii=False)); return 0
    # 只允许默认/tmp或本任务专用证据文件，防止读者误覆盖已有绑定报告。
    report_path = args.report.absolute()
    report_parent = report_path.parent.resolve(strict=True)
    report_path = report_parent / report_path.name
    require(inside(report_path, Path("/tmp")) or report_path == HUB / "validation-evidence/deployment-current-validation.json",
            "报告只能写/tmp或本任务专用deployment证据，不覆盖其他绑定报告")
    result = {"schemaVersion": 1, "checkedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
              "passed": False, "invocation": [sys.executable, *sys.argv],
              "environmentAllowlist": {key: os.environ.get(key, "")[:4096] for key in ENV_ALLOWLIST},
              "environmentKeysCollected": list(ENV_ALLOWLIST), "python": sys.version,
              "platform": platform.platform(), "selfTests": self_test(),
              "docker": {"commandAvailable": shutil.which("docker") is not None,
                         "imageBuilt": False, "containerRun": False}}
    try:
        prefix = scope_root(args.prefix)
        roots = [prefix, *[scope_root(value) for value in args.allow_root]]
        underlays = [scope_root(value) for value in args.underlay]
        require(all(any(inside(value, root) for root in roots) for value in underlays),
                "underlay必须同时位于显式allow-root内")
        settings = dict(entries=args.max_entries, per_file=round(args.max_file_mib * 1024 * 1024),
                        total=round(args.max_total_mib * 1024 * 1024), seconds=args.timeout_s)
        budget = Budget(**settings)
        result.update(parameters={"prefix": str(prefix), "allowRoots": [str(x) for x in roots],
                                  "underlays": [str(x) for x in underlays], "budget": settings})
        result["originalAudit"] = inventory(prefix, roots, budget)
        result["setupLiteralPrefixes"] = setup_literals(prefix, roots, budget)
        result["requestedSourceFiles"] = [file_evidence(value.absolute(), roots, budget) for value in args.source_file]
        require(all(x.get("sha256") for x in result["requestedSourceFiles"]),
                "显式请求的源码没有全部在allowlist内完成SHA读取")
        versions = []
        for name in args.package:
            for location in (prefix, *underlays):
                path = location / "share" / name / "package.xml"
                resolved, _, _ = resolve_allowed(path, roots, budget)
                if resolved is not None:
                    data = budget.read(resolved)
                    require(len(data) <= 262144, "package.xml超过256KiB")
                    xml = ET.fromstring(data)
                    versions.append({"name": name, "version": xml.findtext("version"),
                                     "path": str(path), "resolvedPath": str(resolved),
                                     "sha256": hashlib.sha256(data).hexdigest()})
                    break
            else:
                versions.append({"name": name, "status": "not_found_in_explicit_prefixes"})
        result["packageVersions"] = versions
        if args.copy_demo:
            result["copyDemo"] = copy_evidence(result["originalAudit"], roots, settings)
        if args.host_signal_report:
            host_path = args.host_signal_report.resolve(strict=True)
            require(inside(host_path, Path("/tmp")), "宿主信号报告应显式另存/tmp")
            data = budget.read(host_path)
            host = json.loads(data)
            require(host.get("passed") is True, "宿主信号检查未通过，不能混成通过证据")
            result["hostSignal"] = host
            result["hostSignalInputSha256"] = hashlib.sha256(data).hexdigest()
        result["readBudgetUsed"] = {"entries": budget.entries, "bytes": budget.bytes,
                                     "elapsedS": time.monotonic() - budget.started}
        teaching_summary(result)
        result["passed"] = True
    except BaseException:
        result["error"] = traceback.format_exc(limit=10)[-8000:]
    result["sourceHashes"] = [{"path": str(path.relative_to(HUB)),
                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                               for path in sorted(HERE.iterdir()) if path.is_file() and path.suffix in (".py", ".sh", ".md")]
    result["limits"] = [
        "审计/副本只读取显式范围，未移除原source/build/underlay，未运行复制产物。",
        "保留链接的副本仍指向原位置；同机可解引用不证明换机可运行。",
        "环境脚本只提取有限字面prefix，未执行；ELF只读直接DT_NEEDED/RUNPATH，不解析全部传递依赖。",
        "默认不采集完整环境，不扫描HOME或凭据；排除项、未知格式或超限均不构成自包含证明。",
        "哈希只证明本次读取/复制一致；没有Docker构建、容器停止或跨架构/跨机验证。",
        "可选宿主SIGTERM检查仅针对原安装前缀的合成节点，不是Docker PID1或设备停车验收。"]
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"passed": result["passed"], "report": str(report_path),
                      "counts": result.get("originalAudit", {}).get("counts")}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
