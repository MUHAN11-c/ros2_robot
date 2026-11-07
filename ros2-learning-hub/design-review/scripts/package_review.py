#!/usr/bin/env python3
"""制作自足的设计审查ZIP：审查版与只读教材dist并排保存，不含原始第三方参考仓库。

先核对当前验收与原图，再打包、CRC检查并输出SHA256。deliverables不打入自身，避免递归。
"""
import hashlib
import json
from pathlib import Path
import zipfile
from prepare_review import load_mascot_manifest, sha256 as sha

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT.parent


def main() -> None:
    reports = {}
    report_names = ["browser-report.json", "logic-report.json", "viewport-report.json", "file-save-report.json"]
    for name in report_names:
        report = json.loads((ROOT / "validation" / name).read_text())
        assert report["passed"], name
        reports[name] = report
    baseline = json.loads((ROOT / "source/formal-baseline.json").read_text())["files"]
    for name, digest in baseline.items():
        assert sha(HUB / "dist" / name) == digest, name
    assets = load_mascot_manifest()["assets"]
    evidence = json.loads((ROOT / "validation/preparation.json").read_text())
    assert evidence["assets"] == len(assets)
    screenshot_count = len(reports["browser-report.json"]["screenshots"])
    assert evidence["screenshots"] == screenshot_count >= 15
    output = ROOT / "deliverables"
    output.mkdir(exist_ok=True)
    archive = output / "narukami-design-review.zip"
    initial = json.loads((HUB / "source/local-edits.json").read_text())
    assert not initial["chapters"], "样稿包只保存初始教材；现有本地修订请单独备份。"
    prefix = "ros2-narukami-review/"
    fingerprints = {}
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for folder, label in [(ROOT, "design-review"), (HUB / "dist", "dist")]:
            for file in sorted(folder.rglob("*")):
                relative = file.relative_to(folder)
                if not file.is_file() or not file.resolve().is_relative_to(folder):
                    continue
                if any(part in {"deliverables", "__pycache__", ".git"} for part in relative.parts):
                    continue
                if file.suffix == ".pyc" or file.name in {"reader-preview.html", "initial-home.png"}:
                    continue
                name = label + "/" + relative.as_posix()
                if name == "dist/environment.js":
                    # 便携包独立阅读，保留元数据并禁用依赖完整工作区的原文入口。
                    data = b"/* Portable review package. */\nwindow.ROS2Environment = {workspace:false};\n"
                    z.writestr(prefix + name, data)
                    fingerprints[name] = hashlib.sha256(data).hexdigest()
                else:
                    z.write(file, prefix + name)
                    fingerprints[name] = sha(file)
        for name in ["scripts/serve_local.py", "scripts/local_editions.py", "source/local-edits.json"]:
            z.write(HUB / name, prefix + name)
            fingerprints[name] = sha(HUB / name)
        z.writestr(prefix + "SOURCE_SHA256.json", json.dumps(fingerprints, ensure_ascii=False, indent=2) + "\n")
        z.writestr(prefix + "START_HERE.html", '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>鸣神设计审查版</title><h1>鸣神 · ROS 2 学习手册</h1><p><a href="design-review/index.html#/review">打开设计审查台 →</a></p><p>design-review 与 dist 两个目录须一同保留。紫樱吉祥物与来源说明位于审查目录。</p></html>')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name, digest in fingerprints.items():
            assert hashlib.sha256(z.read(prefix + name)).hexdigest() == digest
    digest = sha(archive)
    (output / "SHA256SUMS").write_text(digest + "  " + archive.name + "\n")
    report = {"passed": True, "archive": archive.name, "bytes": archive.stat().st_size, "sha256": digest, "files": len(fingerprints) + 2, "assets": len(assets), "screenshots": screenshot_count, "formalBaselineFilesUnchanged": len(baseline), "validationHashes": {n: sha(ROOT / "validation" / n) for n in report_names}, "scope": "便携审查站与本机编辑服务；初始修订为空，不含第三方参考仓库、ROS安装、个人草稿或备份。"}
    (output / "delivery.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
