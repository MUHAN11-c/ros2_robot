from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from html import escape
from pathlib import Path, PurePosixPath

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / ".generated" / "docs"
DEFAULT_SOURCE = ROOT

INCLUDE_ROOT_FILES = {"README.md", "LICENSE"}
INCLUDE_TOP_DIRS = {
    "00_项目导航",
    "01_数学",
    "02_C++基础与进阶",
    "02_基础",
    "03_SLAM",
    "04_移动机器人规控",
    "05_运动控制",
    "06_具身智能",
    "media",
    "media_足式RL",
    "media_足式控制",
}
EXCLUDE_PARTS = {
    ".git",
    ".github",
    ".agents",
    ".claude",
    ".codex",
    "_archive",
    "__pycache__",
}
COPY_EXTENSIONS = {
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".pdf",
}
SITE_ASSET_DIRS = ("stylesheets", "javascripts", "assets")


def source_dir() -> Path:
    configured = os.environ.get("DOCS_SOURCE_PATH")
    if configured:
        path = Path(configured).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"DOCS_SOURCE_PATH does not exist: {path}")
        return path

    return DEFAULT_SOURCE


def should_copy(relative_path: Path) -> bool:
    parts = set(relative_path.parts)
    if parts & EXCLUDE_PARTS:
        return False

    if relative_path.name.endswith(".bak"):
        return False

    if "复制版本" in relative_path.name:
        return False

    if relative_path.parent == Path("."):
        return relative_path.name in INCLUDE_ROOT_FILES

    if relative_path.parts[0] not in INCLUDE_TOP_DIRS:
        return False

    return relative_path.suffix.lower() in COPY_EXTENSIONS


def copy_docs(source: Path) -> tuple[int, int]:
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)

    markdown_count = 0
    asset_count = 0

    for item in source.rglob("*"):
        if not item.is_file():
            continue

        relative = item.relative_to(source)
        if not should_copy(relative):
            continue

        target = DOCS_DIR / ("project.md" if relative == Path("README.md") else relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)

        if relative.suffix.lower() == ".md":
            markdown_count += 1
        else:
            asset_count += 1

    return markdown_count, asset_count


def copy_site_assets() -> None:
    for dirname in SITE_ASSET_DIRS:
        source = ROOT / dirname
        if not source.exists():
            continue

        target = DOCS_DIR / dirname
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)


def write_home(markdown_count: int, asset_count: int) -> None:
    def module_link(*targets: str) -> str:
        return public_page_url(first_existing(*targets))

    module_links = {
        "math": module_link(
            "01_数学/数学方向_总大纲.md",
            "01_数学/数学方向总大纲.md",
        ),
        "foundation": module_link(
            "02_C++基础与进阶/C++基础与进阶方向_总大纲.md",
            "02_基础/基础方向_总大纲.md",
            "02_基础/C++基础方向_总大纲.md",
        ),
        "slam": module_link(
            "03_SLAM/SLAM方向_总大纲.md",
            "03_SLAM/slam理论.md",
        ),
        "mobile": module_link(
            "04_移动机器人规控/移动规控方向_总大纲.md",
            "04_移动机器人规控/移动机器人规控方向_总大纲.md",
            "04_移动机器人规控/README.md",
        ),
        "control": module_link(
            "05_运动控制/运动控制方向_总大纲.md",
        ),
        "embodied": module_link(
            "06_具身智能/具身智能方向_总大纲.md",
        ),
    }

    (DOCS_DIR / "index.md").write_text(
        f"""---
template: home.html
hide:
  - navigation
  - toc
---

# 学习模块

<div class="grid cards" markdown>

-   **数学基础**

    流形、李群、凸优化、最优控制、状态估计、强化学习理论。

    [进入模块]({module_links["math"]})

-   **C++基础与进阶**

    C++ 进阶、并发、ROS2、CMake、工程化与机器人软件栈。

    [进入模块]({module_links["foundation"]})

-   **SLAM**

    SLAM 理论、核心库、系统精读、架构与工程化实践。

    [进入模块]({module_links["slam"]})

-   **移动机器人规控**

    规划、控制、TAMP、不确定性、多机器人与横切专题。

    [进入模块]({module_links["mobile"]})

-   **运动控制**

    足式、机械臂、复合机器人、仿真与实时控制工程。

    [进入模块]({module_links["control"]})

-   **具身智能**

    大模型、世界模型、VLA、动作模仿与强化学习。

    [进入模块]({module_links["embodied"]})

</div>

## 构建统计

- 文档页：{markdown_count}
- 媒体资源：{asset_count}

""",
        encoding="utf-8",
    )


SUMMARY_HEADING = re.compile(r"^##\s+(.+?)\s*$")
SUMMARY_ITEM = re.compile(r"^(\s*)\*\s+(?:\[([^\]]+)\]\(([^)]+)\)|(.+?))\s*$")
NUMERIC_PREFIX = re.compile(r"^\d+[_\-\s]+")
CODE_PREFIX = re.compile(
    r"^(?:"
    r"B\d+(?:_[A-Z]+\d*[a-z]?|_[A-Z]+|_T\d+[a-z]?|_TR)?"
    r"|Ch\d+"
    r"|P\d+(?:-\d+)?"
    r"|M\d+"
    r"|D\d+"
    r"|F\d+"
    r"|S\d+[A-Z]?"
    r"|Deep_D\d+[a-z]?"
    r"|Survey_D\d+"
    r")[_\-\s]+",
    re.IGNORECASE,
)
GENERIC_PLACEHOLDER_KEYS = {
    "readme",
    "概览",
    "目录",
    "导读",
    "导读与目录",
    "整合导读",
    "总大纲",
}


@dataclass
class SummaryNode:
    title: str
    target: str | None = None
    missing: bool = False
    children: list["SummaryNode"] = field(default_factory=list)


def link_target(target: str) -> str:
    if target == "README.md":
        return "project.md"
    return target


def first_existing(*targets: str) -> str:
    for target in targets:
        if (DOCS_DIR / target).exists():
            return target
    return targets[0]


def public_page_url(target: str) -> str:
    target = link_target(target)
    path = PurePosixPath(target)

    if path.suffix.lower() != ".md":
        return target

    if path.name in {"README.md", "index.md"}:
        page = path.parent.as_posix()
    else:
        page = path.with_suffix("").as_posix()

    if page in {"", "."}:
        return "./"

    return f"{page}/"


def display_title(name: str) -> str:
    if name == "README":
        return "概览"

    title = NUMERIC_PREFIX.sub("", name)
    title = title.replace("_", " ").strip()
    return title or name


def comparable_title(name: str) -> str:
    title = Path(name).stem
    if title == "README":
        return "概览"

    for _ in range(4):
        title = NUMERIC_PREFIX.sub("", title)
        title = CODE_PREFIX.sub("", title)

    title = re.sub(r"[_\-\s·:：/（）(),，、]+", "", title)
    return title.lower()


def sort_key(path: Path) -> tuple[int, int, str]:
    stem = path.stem if path.is_file() else path.name

    if path.name == "README.md":
        priority = 0
    elif "总大纲" in stem or "导读" in stem or "目录" in stem:
        priority = 1
    else:
        priority = 2

    number = 10_000
    match = re.match(r"^(\d+)[_\-\s]+", stem)
    if match:
        number = int(match.group(1))

    return priority, number, display_title(stem)


def has_markdown(path: Path) -> bool:
    return any(path.rglob("*.md"))


def parse_summary(source: Path) -> list[SummaryNode]:
    summary = source / "SUMMARY.md"
    if not summary.exists():
        return []

    catalog: list[SummaryNode] = []
    stack: list[tuple[int, list[SummaryNode]]] = []
    missing: list[str] = []

    for line in summary.read_text(encoding="utf-8").splitlines():
        heading = SUMMARY_HEADING.match(line)
        if heading:
            node = SummaryNode(heading.group(1).strip())
            catalog.append(node)
            children = node.children
            stack = [(-1, children)]
            continue

        item = SUMMARY_ITEM.match(line)
        if not item or not stack:
            continue

        indent = len(item.group(1).replace("\t", "  "))
        title = item.group(2) or item.group(4) or ""
        target = item.group(3)

        if target == "README.md" and indent == 0:
            continue

        while stack and indent <= stack[-1][0]:
            stack.pop()

        is_missing = bool(target and not (DOCS_DIR / link_target(target)).exists())
        if target and is_missing:
            missing.append(target)

        parent = stack[-1][1] if stack else catalog
        node = SummaryNode(title=title.strip(), target=target.strip() if target else None, missing=is_missing)
        parent.append(node)

        if target is None:
            stack.append((indent, node.children))

    if missing:
        print("Missing SUMMARY.md targets shown as unfinished in catalog:")
        for target in missing[:50]:
            print(f"  - {target}")
        if len(missing) > 50:
            print(f"  ... {len(missing) - 50} more")

    return catalog


def catalog_stats(items: list[SummaryNode]) -> tuple[int, int]:
    target_count = 0
    missing_count = 0

    for item in items:
        if item.target:
            target_count += 1
            if item.missing:
                missing_count += 1

        child_targets, child_missing = catalog_stats(item.children)
        target_count += child_targets
        missing_count += child_missing

    return target_count, missing_count


def build_filesystem_children(directory: Path) -> list[SummaryNode]:
    children: list[SummaryNode] = []

    files = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".md"
    ]
    directories = [
        path
        for path in directory.iterdir()
        if path.is_dir()
        and path.name not in SITE_ASSET_DIRS
        and has_markdown(path)
    ]

    for path in sorted(files, key=sort_key):
        relative = path.relative_to(DOCS_DIR).as_posix()
        if relative in {"index.md", "catalog.md", "project.md"}:
            continue

        children.append(
            SummaryNode(
                title=display_title(path.stem),
                target=relative,
            )
        )

    for path in sorted(directories, key=sort_key):
        directory_children = build_filesystem_children(path)
        if not directory_children:
            continue

        children.append(
            SummaryNode(
                title=display_title(path.name),
                children=directory_children,
            )
        )

    return children


def build_filesystem_catalog() -> list[SummaryNode]:
    catalog: list[SummaryNode] = []

    for path in sorted(DOCS_DIR.iterdir(), key=sort_key):
        if not path.is_dir() or path.name in SITE_ASSET_DIRS or not has_markdown(path):
            continue

        children = build_filesystem_children(path)
        if not children:
            continue

        catalog.append(
            SummaryNode(
                title=display_title(path.name),
                children=children,
            )
        )

    return catalog


def collect_existing_keys(items: list[SummaryNode]) -> set[str]:
    keys: set[str] = set()

    for item in items:
        if item.target and not item.missing:
            keys.add(comparable_title(item.title))
            keys.add(comparable_title(Path(item.target).stem))

        keys.update(collect_existing_keys(item.children))

    return keys


def is_known_existing(key: str, existing_keys: set[str]) -> bool:
    if key in existing_keys:
        return True

    if len(key) < 6:
        return False

    for existing in existing_keys:
        if len(existing) < 6:
            continue

        if key in existing or existing in key:
            return True

        if SequenceMatcher(None, key, existing).ratio() >= 0.6:
            return True

    return False


def module_key(title: str) -> str:
    if "项目导航" in title:
        return "project"
    if "数学" in title:
        return "math"
    if "SLAM" in title.upper():
        return "slam"
    if "移动机器人" in title or "移动规控" in title:
        return "mobile"
    if "运动控制" in title:
        return "control"
    if "具身智能" in title:
        return "embodied"
    if "编程" in title or "基础" in title:
        return "foundation"
    return comparable_title(title)


def filter_missing_placeholders(
    items: list[SummaryNode],
    existing_keys: set[str],
) -> list[SummaryNode]:
    placeholders: list[SummaryNode] = []

    for item in items:
        if item.children:
            children = filter_missing_placeholders(item.children, existing_keys)
            if children:
                placeholders.append(
                    SummaryNode(
                        title=item.title,
                        children=children,
                    )
                )
            continue

        if not item.target or not item.missing:
            continue

        key = comparable_title(item.title)
        if key in GENERIC_PLACEHOLDER_KEYS or is_known_existing(key, existing_keys):
            continue

        placeholders.append(
            SummaryNode(
                title=item.title,
                target=item.target,
                missing=True,
            )
        )

    return placeholders


def merge_summary_placeholders(
    catalog: list[SummaryNode],
    summary_catalog: list[SummaryNode],
) -> list[SummaryNode]:
    existing_keys = collect_existing_keys(catalog)
    sections = {module_key(item.title): item for item in catalog}

    for summary_section in summary_catalog:
        placeholders = filter_missing_placeholders(summary_section.children, existing_keys)
        if not placeholders:
            continue

        key = module_key(summary_section.title)
        target_section = sections.get(key)
        placeholder_group = SummaryNode(title="敬请期待", children=placeholders)

        if target_section:
            target_section.children.append(placeholder_group)
        else:
            catalog.append(
                SummaryNode(
                    title=summary_section.title,
                    children=[placeholder_group],
                )
            )

    return catalog


def select_catalog(source: Path) -> list[SummaryNode]:
    summary_catalog = parse_summary(source)
    target_count, missing_count = catalog_stats(summary_catalog)

    if target_count == 0:
        print("No usable SUMMARY.md targets found. Building catalog from local files.")
        return build_filesystem_catalog()

    missing_ratio = missing_count / target_count
    if missing_ratio > 0.35:
        print(
            "SUMMARY.md appears stale "
            f"({missing_count}/{target_count} targets missing). "
            "Preserving SUMMARY.md order and marking missing pages as unfinished."
        )
        return summary_catalog

    return summary_catalog


def build_navigation(items: list[SummaryNode]) -> list[dict[str, object]]:
    nav: list[dict[str, object]] = []

    for item in items:
        if item.children:
            children = build_navigation(item.children)
            if children:
                nav.append({item.title: children})
            continue

        if item.target and not item.missing:
            nav.append({item.title: link_target(item.target)})

    return nav


def missing_leaf_totals(item: SummaryNode) -> tuple[int, int]:
    if item.target:
        return 1, 1 if item.missing else 0

    total = 0
    missing = 0
    for child in item.children:
        child_total, child_missing = missing_leaf_totals(child)
        total += child_total
        missing += child_missing

    return total, missing


def all_leaf_pages_missing(item: SummaryNode) -> bool:
    total, missing = missing_leaf_totals(item)
    return total > 0 and total == missing


def catalog_missing_label(title: str) -> str:
    return (
        f'<span class="robotics-catalog-missing">{escape(title)}'
        ' <span class="robotics-catalog-badge">敬请期待</span></span>'
    )


def render_catalog_items(items: list[SummaryNode], level: int = 0) -> list[str]:
    lines: list[str] = []
    details_class = "robotics-catalog-section" if level == 0 else "robotics-catalog-group"

    for item in items:
        if item.children:
            summary_title = (
                catalog_missing_label(item.title)
                if level > 0 and item.title != "敬请期待" and all_leaf_pages_missing(item)
                else escape(item.title)
            )
            details_attrs = f'class="{details_class}" markdown'
            if level == 0:
                details_attrs += " open"
            lines.extend(
                [
                    f"<details {details_attrs}>",
                    f"<summary>{summary_title}</summary>",
                    "",
                ]
            )
            lines.extend(render_catalog_items(item.children, level + 1))
            lines.extend(["", "</details>", ""])
            continue

        if item.target and item.missing:
            lines.append(f"- {catalog_missing_label(item.title)}")
            continue

        if item.target:
            lines.append(f"- [{item.title}]({link_target(item.target)})")

    return lines


def write_catalog(catalog: list[SummaryNode]) -> None:
    lines = [
        "# 目录索引",
        "",
        "按课程模块折叠展示，展开模块后进入对应章节。",
        "",
        *render_catalog_items(catalog),
    ]
    (DOCS_DIR / "catalog.md").write_text("\n".join(lines), encoding="utf-8")


def generate_config(nav: list[dict[str, object]]) -> None:
    base = yaml.load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=yaml.Loader)
    base["nav"] = [{"首页": "index.md"}, {"项目说明": "project.md"}, {"目录索引": "catalog.md"}, *nav]
    (ROOT / "mkdocs.generated.yml").write_text(
        yaml.dump(base, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def main() -> None:
    source = source_dir()
    markdown_count, asset_count = copy_docs(source)
    copy_site_assets()
    write_home(markdown_count, asset_count)
    catalog = select_catalog(source)
    nav = build_navigation(catalog)
    write_catalog(catalog)
    generate_config(nav)
    print(f"Synced {markdown_count} markdown files and {asset_count} assets from {source}")


if __name__ == "__main__":
    main()
