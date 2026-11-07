#!/usr/bin/env python3
"""准备审查版的离线数据。

依次核对吉祥物清单和文件哈希、教材基线与现有截图，再生成浏览器可直接读取的 JS 数据。
素材尺寸以像素计。文件缺失、哈希冲突或目录混入旧素材时，在生成前终止。
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT.parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_mascot_manifest() -> dict:
    manifest = json.loads((ROOT / "source/mascot-assets.json").read_text())
    assets = manifest["assets"]
    assert manifest["mascot"] == "紫樱" and assets
    assert not (ROOT / "assets/characters").exists(), "旧角色图片仍在审查版目录"
    assert not (ROOT / "source/character-assets.json").exists(), "旧角色清单仍在审查版目录"
    assert len({item["id"] for item in assets}) == len(assets), "素材 ID 重复"
    assert len({item["sha256"] for item in assets}) == len(assets), "素材文件重复"
    directory = ROOT / "assets/mascots"
    files = set()
    for item in assets:
        target = (ROOT / item["file"]).resolve()
        assert target.parent == directory and target.suffix == ".webp", item["file"]
        assert sha256(target) == item["sha256"], item["id"]
        files.add(target)
    assert files == set(directory.iterdir()), "吉祥物目录与清单不一致"
    return manifest


def main() -> None:
    manifest = load_mascot_manifest()
    baseline = json.loads((ROOT / "source/formal-baseline.json").read_text())
    for name, digest in baseline["files"].items():
        assert sha256(HUB / "dist" / name) == digest, "正式教材发生变更：" + name
    (ROOT / "assets-data.js").write_text(
        "/* 紫樱吉祥物的仓库原文件。来源记录见 source/mascot-assets.json 与 ASSET_SOURCES.md。 */\n"
        + "window.NarukamiAssets = " + json.dumps(manifest, ensure_ascii=False, indent=2) + ";\n"
    )
    labels = {
        "desktop-light.png": "桌面1440px · 樱粉浅色首页",
        "desktop-dark.png": "桌面1440px · 夜紫深色首页",
        "chapter-light.png": "控制章 · 小节编号与长标题换行",
        "chapter-workspace-outline.png": "第 3 章 · 工作空间的实现对照与代码",
        "chapter-estimation-outline.png": "第 8 章 · 状态估计的小节编号与公式",
        "chapter-model-outline.png": "第 33 章 · 深色模型章的 33.10 与实测表 33.10.1",
        "chapter-action-mobile-outline.png": "390px · 第 16 章动作目录的 API 子条目",
        "chapter-action-mobile-reading.png": "320px · 第 16 章从目录定位到 API 正文",
        "chapter-nav2-planning.png": "第 45 章 · 实测代价地图与同目标绕行",
        "chapter-slam-mapping.png": "第 41 章 · 同一圈扫描的占据图、轨迹与误差",
        "editor-desktop.png": "章节编辑 · 原排版直接修改",
        "editor-mobile.png": "手机390px · 深色原排版编辑",
        "note-drawer.png": "章节笔记 · 编辑抽屉",
        "search-results.png": "全文搜索 · 命中与定位",
        "search-empty.png": "全文搜索 · 空态",
        "lab-wide.png": "坐标变换 · 宽屏实验",
        "model-lab.png": "机器人几何模型 · 交互",
        "gallery.png": "紫樱素材 · 来源审查画廊",
        "mobile-390.png": "手机390px · 樱粉浅色",
        "mobile-320.png": "手机320px · 樱粉浅色",
        "mobile-dark.png": "手机390px · 夜紫深色",
        "mobile-note.png": "手机390px · 章节笔记",
    }
    screenshots = [
        {"file": "screenshots/" + name, "title": title, "sha256": sha256(ROOT / "screenshots" / name)}
        for name, title in labels.items() if (ROOT / "screenshots" / name).exists()
    ]
    (ROOT / "review-evidence.js").write_text(
        "/* 仅列实际存在的浏览器截图；测试结论另见validation/browser-report.json。 */\n"
        + "window.NarukamiReviewEvidence = " + json.dumps({"screenshots": screenshots}, ensure_ascii=False, indent=2) + ";\n"
    )
    report = {"assets": len(manifest["assets"]), "formalBaselineFilesUnchanged": len(baseline["files"]), "screenshots": len(screenshots)}
    (ROOT / "validation/preparation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
