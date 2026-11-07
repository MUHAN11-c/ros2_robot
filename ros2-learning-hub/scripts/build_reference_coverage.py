#!/usr/bin/env python3
"""只读清点原始资料，生成章末溯源和站内附录所需的两个 JSON。

输入：工作区三套教程、references/catalog.json、references/manifest.json。
输出：source/reference-coverage.json 与 source/local-library.json。
路径统一相对工作区根目录；字节数、字符数均是文件统计，不代表教学完成度。
顺序：读取原文结构 → 按人工审定的主题范围映射 → 核对导航目标 → 汇总下载版本。
边界：不联网，不运行第三方脚本，不改原文，不把目录映射标成逐段内容整合。
只在已抽样比较的很窄主题上使用“详细讲解”，其余保守标为概览或延伸。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote
from zoneinfo import ZoneInfo

from catalog_mapping import map_entry


HUB = Path(__file__).resolve().parents[1]
WORKSPACE = HUB.parent
SOURCE = HUB / "source"
LIBRARY = HUB / "references"
NEW_LESSONS = ["math-linear", "math-rigid", "math-probability", "math-estimation",
               "math-optimization", "math-kinematics", "math-dynamics", "math-control",
               "cpp-engineering", "theory-slam", "theory-planning", "theory-optimal-control",
               "theory-legged", "theory-aerial", "project-navigation", "project-manipulation"]
TUTORIALS = [
    {"id": "zsc", "title": "ROS 2 完全教程", "repository": "zsc/ros2_tutorial",
     "path": "ros2_tutorial", "license": "未发现根许可证文件，原文授权需单独核对"},
    {"id": "rzl6", "title": "ROS 2 理论与实践", "repository": "Rzl6/ROS2_Tuition",
     "path": "ROS2_Tuition", "license": "根目录 LICENSE 声明 MIT"},
    {"id": "robotics", "title": "Robotics Tutorial", "repository": "Michael-Jetson/Robotics_Tutorial",
     "path": "Robotics_Tutorial", "license": "根 LICENSE 为 CC BY-NC 4.0；部分页眉另写 CC BY 4.0，存在声明差异"},
]
# 以下代表页确实由研究代理读取过正文片段；其他页只作结构和目录范围扫描。
# 它不是“所有原文结论已核实”的名单，更不代表相应 ROS 工程已运行。
SAMPLE_READ = {
    "ros2_tutorial/chapter8.md",
    "ROS2_Tuition/_book/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/22-hua-ti-tong-xin/223-hua-ti-tong-xin-python-shi-73b028-yuan-sheng-xiao-606f29.md",
    "Robotics_Tutorial/01_数学/60_概率与估计/30_流形滤波族.md",
    "Robotics_Tutorial/03_SLAM/10_SLAM理论/10_SLAM理论基础.md",
    "Robotics_Tutorial/04_移动机器人规控/10_时空规划/20_Frenet坐标系与ST图.md",
    "Robotics_Tutorial/04_移动机器人规控/40_博弈规划/10_博弈规划总论.md",
    "Robotics_Tutorial/05_运动控制/10_足式/70_腿足简化模型理论.md",
    "Robotics_Tutorial/05_运动控制/20_机械臂/F04_笛卡尔阻抗控制.md",
    "Robotics_Tutorial/05_运动控制/30_复合/220_经典人形全身控制.md",
    "Robotics_Tutorial/06_具身智能/RL运控/Ch23_Sim2Real部署全链路.md",
}
TOPIC_COMPARED = {
    "ROS2_Tuition/_book/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/22-hua-ti-tong-xin/223-hua-ti-tong-xin-python-shi-73b028-yuan-sheng-xiao-606f29.md":
        {"lessons": ["pubsub"], "reason": "抽样比较了 Python 定时发布、订阅回调、spin 与退出顺序；本站 pubsub 已有同一最小通信任务的原理、完整文件和操作说明。仅限此主题，不表示原页每行代码已逐句吸收。"},
}
REVIEW_WARNINGS = {
    "Robotics_Tutorial/01_数学/60_概率与估计/30_流形滤波族.md":
        "原页对 InEKF 一致性、四元数协方差等有较强结论；本站不能照搬为无条件保证，需回到具体系统、误差定义和可观性假设。",
    "Robotics_Tutorial/05_运动控制/10_足式/70_腿足简化模型理论.md":
        "原页包含“全身动力学不能实时 MPC”“ZMP 在支撑多边形内即稳定”等强表述；后续教材需补充求解器、硬件、接触和模型假设。",
}


def load(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value) -> None:
    """只替换本工具负责的生成数据，避免改动主代理并行编辑的文件。"""
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def relative(path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(WORKSPACE):
        raise ValueError(f"资料路径越过工作区：{path}")
    return resolved.relative_to(WORKSPACE).as_posix()


class ArticleHTML(HTMLParser):
    """仅提取 HTML 标题与可见文本；绝不执行脚本、外链或原站模板。"""
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.heading = None
        self.headings = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
        if tag in {"h1", "h2", "h3"}:
            self.heading = []

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        if tag in {"h1", "h2", "h3"} and self.heading is not None:
            self.headings.append("".join(self.heading).strip())
            self.heading = None

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.heading is not None:
                self.heading.append(data)


def scan_document(path: Path) -> dict:
    """读取全文以计算结构证据，不把自动扫描叙述为人工逐段核读。"""
    raw = path.read_text(errors="replace")
    if path.suffix.lower() == ".html":
        parser = ArticleHTML()
        parser.feed(raw)
        headings, prose = parser.headings, " ".join(parser.parts)
    else:
        prose_lines, headings, fenced = [], [], False
        for line in raw.splitlines():
            if re.match(r"^\s*(```|~~~)", line):
                fenced = not fenced
                continue
            if not fenced:
                prose_lines.append(line)
                match = re.match(r"^\s*#{1,4}\s+(.+)", line)
                if match:
                    headings.append(re.sub(r"\s*\{#[^}]+\}", "", match.group(1)).strip())
        prose = "\n".join(prose_lines)
    return {"raw": raw, "prose": prose, "headings": headings,
            "bytes": path.stat().st_size, "proseCharacters": len(prose.strip()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def doc_kind(path: Path, scan: dict) -> str:
    """把导航、维护资料、空白占位与正文分开；统计不合并这些性质不同的文件。"""
    name, text = path.name, path.as_posix()
    if name.upper() in {"AGENTS.MD", "CLAUDE.MD", "CONTRIBUTING.MD"}:
        return "项目规则"
    if any(term in text for term in ("_调研_2026Q2", "修复记录", "审计报告", "待人工裁定", "建设计划", "运控文档问题")):
        return "维护记录"
    if (name.lower() in {"readme.md", "summary.md", "index.md", "index.html"}
            or "/00_项目导航/" in text or path.suffix == ".html"
            or re.search(r"(总大纲|综合教学大纲|路线图|导读|方向分类|扩展方案|合并路线图|合并章节列表|技能矩阵|依赖图)", name)):
        return "导航导读"
    # Rzl6 部分文件只有标题，另有章节目录页以一个短句介绍下级文件。
    if scan["proseCharacters"] < 80:
        return "导航导读" if path.with_suffix("").is_dir() else "空白占位"
    if any(term in text for term in ("调研报告", "/调研/", "全景调研", "项目调研", "课程规划")):
        return "研究资料"
    return "教学附录" if "附录" in name or "Appendix_" in name else "教学正文"


def robotics_topic(path: str) -> tuple[str, list[str], str, str]:
    """按已核读代表页和目录学科范围映射；高级专门内容保守列为延伸。

    返回（分类、相关章节、深度、理由）。这不是关键词覆盖率评分器。
    文件名用于区分同目录中明显超出教材所述范围的专题，实际证据另存。
    """
    if "/01_数学/" in path:
        if "/10_纯数学基础/" in path:
            extended = any(x in path for x in ("集合论", "Jordan", "多线性", "拓扑", "抽象代数", "实分析", "测度", "泛函"))
            return "数学／线性代数", ["math-linear"], "延伸范围" if extended else "主题概览", "教材建立机器人所需线性代数基础；原页的完整高等代数/分析内容不据此视为已收录。"
        if "/20_微分几何与李群/" in path:
            return "数学／几何与李群", ["math-rigid", "math-kinematics", "tf2"], "延伸范围" if any(x in path for x in ("流形一般", "BCH", "等变", "不确定性", "Retraction")) else "主题概览", "关联刚体变换与局部线性化；不声明覆盖全部流形、BCH 或等变理论。"
        if "/30_优化理论/" in path:
            return "数学／优化", ["math-optimization", "theory-optimal-control"], "延伸范围" if any(x in path for x in ("共轭", "proximal", "自动微分", "对偶")) else "主题概览", "关联最小二乘和约束优化入门；专门的凸分析与算法证明属于进一步阅读。"
        if "/40_控制理论/" in path:
            return "数学／控制理论", ["math-control", "theory-optimal-control"], "主题概览" if any(x in path for x in ("Lyapunov", "LQR", "辨识")) else "延伸范围", "教材涉及反馈、稳定性、LQR/MPC 基础；不据此声称完整推导 HJB、PMP、DDP、鲁棒/随机控制。"
        if "/50_刚体动力学/" in path:
            return "数学／动力学", ["math-dynamics", "math-kinematics"], "延伸范围" if any(x in path for x in ("辛结构", "解析微分", "SE3几何")) else "主题概览", "关联机器人动力学与能量建模；高级几何力学和算法实现仍需原资料。"
        if "/60_概率与估计/" in path:
            return "数学／概率与估计", ["math-probability", "math-estimation", "theory-slam", "eco-state-estimation"], "延伸范围" if any(x in path for x in ("流形滤波", "iSAM2", "Barrau", "Certifiable", "Kalman族全景")) else "主题概览", "关联贝叶斯更新、滤波和因子图基础；不宣称已穷尽滤波族、一致性理论或可认证估计。"
        if "/70_强化学习数学/" in path:
            return "数学／强化学习", ["learning-rl", "theory-optimal-control"], "主题概览" if "MDP" in path else "延伸范围", "与决策过程和策略学习主题对应；不将专题数学证明算入概念性实验。"
        if "/80_接触力学/" in path:
            return "数学／接触力学", ["math-dynamics", "theory-legged"], "延伸范围", "教材只使用有限接触假设和约束模型，未覆盖完整互补、非光滑或可微接触理论。"
        if "/90_深度学习数学/" in path:
            return "数学／学习模型", ["learning-policy", "learning-embodied"], "延伸范围", "教材说明机器人策略接口与部署边界，不替代神经网络数学专题。"
        return "数学／随机分析", ["math-probability", "math-estimation"], "延伸范围", "随机微分方程等内容超出基础概率与估计章节的当前范围。"
    if "/02_C++基础与进阶/" in path:
        lessons = ["cpp-engineering"]
        if any(x in path for x in ("实时", "无锁", "线程", "缓存")):
            lessons += ["executors", "performance"]
        if any(x in path for x in ("ROS2", "CMake", "构建", "测试")):
            lessons += ["workspace", "composition", "testing"]
        if any(x in path for x in ("Eigen", "Ceres", "manif")):
            lessons += ["math-linear", "math-optimization"]
        if any(x in path for x in ("PCL", "OpenCV", "CUDA", "GPU")):
            lessons += ["eco-perception-pipeline", "eco-accelerated-robotics"]
        depth = "延伸范围" if any(x in path for x in ("SFINAE", "CRTP", "Concepts", "CUDA", "GPU", "深入", "剖析", "代码生成")) else "主题概览"
        return "C++ 与工程", lessons, depth, "教材选择资源管理、构建、并发和 ROS 集成重点；不将完整 C++ 语言/库课程算作已整合。"
    if "/03_SLAM/" in path:
        lessons = ["theory-slam", "eco-slam-mapping", "math-estimation"]
        return "SLAM", lessons, "延伸范围" if any(x in path for x in ("精读", "GTSAM", "g2o", "Mini-LIO", "PCL_OpenCV")) else "主题概览", "提供 SLAM 系统和估计基础的主题入口；特定开源系统的逐行实现与精读内容未全面编入。"
    if "/04_移动机器人规控/" in path:
        if "/70_无人机/" in path:
            return "无人机", ["theory-aerial", "theory-planning", "math-control"], "延伸范围", "教材建立飞行器坐标、控制接口和环境边界，不替代全部轨迹生成及敏捷飞行专题。"
        if "/50_多机器人协作/" in path:
            return "多机器人规划", ["eco-multi-robot", "project-navigation", "theory-planning"], "延伸范围", "关联协调与任务分配；原页专门的多机控制、博弈或 MARL 算法未被视为全部整合。"
        if "/60_任务运动规划/" in path:
            return "任务与运动规划", ["theory-planning", "project-manipulation", "learning-embodied", "eco-nav2-task-programming"], "主题概览" if "行为树" in path else "延伸范围", "关联任务契约、规划和执行监控；PDDLStream、LGP 与信念空间算法仍列为延伸。"
        if "/20_采样式MPC/" in path:
            return "采样控制与 MPC", ["theory-optimal-control", "theory-planning", "eco-nav2-stack"], "延伸范围", "教材介绍滚动优化原则，未把 MPPI/CEM 各变体的完整推导和 GPU 实现算作已收录。"
        if "/40_博弈规划/" in path:
            return "博弈规划", ["theory-planning", "eco-multi-robot"], "延伸范围", "多决策者均衡与博弈求解超出基础单机器人规划的已讲解范围。"
        return "移动机器人规划", ["theory-planning", "project-navigation", "theory-optimal-control"], "延伸范围", "关联搜索、优化和不确定性规划；原资料的 Frenet/ST、风险约束及自动驾驶专用实现尚非完整正文范围。"
    if "/05_运动控制/" in path:
        if "/10_足式/" in path:
            return "腿足控制", ["theory-legged", "math-dynamics", "theory-optimal-control"], "主题概览" if any(x in path for x in ("简化模型", "浮动基座动力学", "接触力学")) else "延伸范围", "教材说明接触、简化模型与反馈链路；不声明覆盖 OCS2/Pinocchio/WBC/RL 的全部系统精读。"
        if "/20_机械臂/" in path:
            lessons = ["project-manipulation", "eco-moveit-planning", "eco-manipulation-tasks", "math-kinematics"]
            return "机械臂与操作", lessons, "主题概览" if any(x in path for x in ("URDF_Xacro", "MoveIt2_MTC", "碰撞检测", "时间参数化", "ros2_control")) else "延伸范围", "关联建模、规划场景和轨迹执行；阻抗、遥操作、双臂或特定动力学库的细节仍需另行深读。"
        if "/30_复合/" in path:
            return "复合机器人", ["project-manipulation", "theory-legged", "learning-policy"], "延伸范围", "移动操作、轮足和人形全身控制的统一系统实现不由现有入门章节替代。"
        return "仿真与运动控制", ["eco-gazebo-simulation", "eco-accelerated-robotics", "learning-rl"], "延伸范围", "Gazebo/训练管线概念与此相关，但 MuJoCo、mjlab、可微仿真的具体教程未完整编入。"
    if "/06_具身智能/" in path:
        lessons = ["learning-rl", "learning-policy", "learning-embodied"]
        if any(x in path for x in ("数据", "训练管线", "性能", "诊断")):
            lessons += ["cloud-mlops"]
        return "具身智能与训练", lessons, "主题概览" if any(x in path for x in ("生态系统", "观测与动作", "奖励课程", "域随机化", "Sim2Real部署")) else "延伸范围", "教材以数据、接口、训练与部署边界为主；具体学习算法、平台训练或网球任务等实现不视为已全部吸收。"
    return "项目导航", [], "未纳入", "非教学正文或暂无对应正文主题。"


def coverage_data() -> dict:
    legacy = load(SOURCE / "catalog.json")
    legacy_by_file = {entry["file"]: entry for entry in legacy}
    entries, tutorials = [], []
    for tutorial in TUTORIALS:
        root = WORKSPACE / tutorial["path"]
        paths = sorted(root.rglob("*.md"))
        # HTML 是 Markdown 的生成副本时不重复统计；仅独有的顶层 HTML 导航仍登记。
        paths += sorted(path for path in root.rglob("*.html") if not path.with_suffix(".md").exists()
                        and tutorial["id"] == "rzl6")
        for path in paths:
            file = relative(path)
            scan = scan_document(path)
            kind = doc_kind(path, scan)
            old = legacy_by_file.get(file) or legacy_by_file.get(str(path.with_suffix(".html").relative_to(WORKSPACE)))
            title = (old or {}).get("title") or next(iter(scan["headings"]), path.stem)
            if tutorial["id"] == "robotics":
                category, lessons, depth, reason = robotics_topic(file)
            elif tutorial["id"] == "zsc" and re.fullmatch(r"chapter\d+\.md", path.name):
                category, lessons, depth, reason = "ROS 2 综合", map_entry(old or {"site": "zsc", "url": "chapter" + re.search(r"\d+", path.stem).group()}), "主题概览", "源章横跨多个知识点；本地章节提供主题对应，不代表源章所有细节逐项整合。"
            elif tutorial["id"] == "rzl6" and old:
                category, lessons, depth, reason = "ROS 2 基础", map_entry(old), "主题概览", "依据原页标题、正文结构与既有教程映射建立联系；未逐段完成吸收核验。"
            elif tutorial["id"] == "rzl6":
                # 原有 HTML 目录未登记的 Markdown 文件不凭空视为完整章节。
                title_low = title.lower()
                if "话题" in title or "topic" in file:
                    lessons = ["pubsub"]
                elif "服务" in title:
                    lessons = ["services"]
                elif "动作" in title:
                    lessons = ["actions"]
                elif "参数" in title:
                    lessons = ["parameters"]
                elif any(term in title_low for term in ("坐标", "tf")):
                    lessons = ["tf2"]
                else:
                    lessons = ["architecture"]
                category, depth, reason = "ROS 2 基础", "主题概览", "原 Markdown 文件存在；依据结构辨认相关主题，尚未进行逐段正文对照。"
            else:
                category, lessons, depth, reason = "项目导航", [], "未纳入", "索引或辅助文档不计作教学正文覆盖。"
            if kind not in {"教学正文", "教学附录"}:
                depth, reason = "未纳入", f"此文件属于{kind}，单独保留以追溯来源，不计作教学正文吸收。"
            review_level = "结构扫描"
            if file in SAMPLE_READ:
                review_level = "代表页正文片段核读"
            if file in TOPIC_COMPARED and kind in {"教学正文", "教学附录"}:
                depth = "详细讲解"
                lessons = TOPIC_COMPARED[file]["lessons"]
                reason = TOPIC_COMPARED[file]["reason"]
                review_level = "代表页具体主题对照"
            source_relative = path.relative_to(root).as_posix()
            url = (old or {}).get("url") or f"https://github.com/{tutorial['repository']}/blob/main/{quote(source_relative, safe='/')}"
            entry = {"id": "coverage-" + hashlib.sha256(file.encode()).hexdigest()[:14],
                     "site": tutorial["id"], "title": title, "file": file, "localPath": file,
                     "url": url, "category": category, "kind": kind,
                     "relatedLessons": list(dict.fromkeys(lessons)), "depth": depth,
                     "depthReason": reason, "reviewLevel": review_level,
                     "proseCharacters": scan["proseCharacters"], "bytes": scan["bytes"],
                     "sha256": scan["sha256"],
                     "evidence": {"headings": scan["headings"][:3], "topicBasis": "目录学科范围、文件标题和自动提取的非代码正文结构；人工抽样另有 reviewLevel 标记"},
                     "runtimeValidation": "原文示例本轮未构建、未运行"}
            if file in REVIEW_WARNINGS:
                entry["reviewNote"] = REVIEW_WARNINGS[file]
            entries.append(entry)
        subset = [entry for entry in entries if entry["site"] == tutorial["id"]]
        tutorials.append({**tutorial, "counts": {"indexedDocuments": len(subset),
                          "kinds": dict(Counter(entry["kind"] for entry in subset)),
                          "depths": dict(Counter(entry["depth"] for entry in subset))}})
    summary = WORKSPACE / "Robotics_Tutorial" / "SUMMARY.md"
    summary_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", summary.read_text())
    missing = []
    for label, target in summary_links:
        if "://" in target or target.startswith("#"):
            continue
        destination = summary.parent / unquote(target.split("#")[0])
        if not destination.exists():
            missing.append({"site": "robotics", "summaryFile": relative(summary),
                            "label": label, "target": target, "localPath": relative(destination),
                            "status": "原参考仓库导航目标不存在；未伪造正文或可用链接"})
    return {"meta": {"schemaVersion": 1, "checkedAt": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
                     "purpose": "站内附录和章末溯源；不替代自足教材正文",
                     "pathBase": "workspace-root", "scopeClaim": "这是主题对应与资料结构索引，不是原教程逐段穷尽吸收证明。",
                     "verification": "扫描全部规范正文文件的存在性、标题、非代码结构、摘要值；仅对明示代表页核读正文片段。",
                     "newChapterTargets": NEW_LESSONS,
                     "navigationPolicy": "辅助页、研究记录、导航导读、空白占位分开登记；生成HTML与同名Markdown不重复算正文。",
                     "reusePolicy": "只发布元数据、标题与路径；原文/代码按各自许可保留，不从索引推导转载授权。"},
            "depthLevels": [
                {"id": "详细讲解", "description": "对明示的窄主题有本地原理、实现和实践解释，并做代表页具体主题对照；不是原文逐句覆盖。"},
                {"id": "主题概览", "description": "教材讨论同一主题，但没有逐项核对全部原文细节。"},
                {"id": "延伸范围", "description": "列出相关本地入口，原资料的专门推导或系统实现超出当前自足正文范围。"},
                {"id": "未纳入", "description": "辅助/空白资料或尚无对应正文，不算教学内容覆盖。"}],
            "tutorials": tutorials, "entries": entries, "missingTargets": missing,
            "statistics": {"indexedDocuments": len(entries),
                           "teachingDocuments": sum(entry["kind"] in {"教学正文", "教学附录"} for entry in entries),
                           "kinds": dict(Counter(entry["kind"] for entry in entries)),
                           "depths": dict(Counter(entry["depth"] for entry in entries)),
                           "reviewLevels": dict(Counter(entry["reviewLevel"] for entry in entries)),
                           "roboticsSummaryLinks": len(summary_links), "missingSummaryTargets": len(missing)}}


def repository_lessons(repository: str, title: str) -> list[str]:
    """下载元数据采用用途分类，不将仓库名命中写成正文吸收完成。"""
    exact = {
        "ros2/ros2": ["installation", "deployment", "migration"],
        "ros2/rclc": ["eco-microcontrollers"],
        "ros2/rclcpp": ["pubsub", "services", "executors", "cpp-engineering"],
        "ros2/rclpy": ["pubsub", "services", "executors"],
        "ros2/ros2cli": ["graph-cli"],
        "ros2/ros2_tracing": ["performance", "eco-data-observability"],
        "ros2/examples": ["pubsub", "services", "actions", "qos", "testing"],
        "ros2/demos": ["pubsub", "actions", "lifecycle", "composition", "qos", "performance"],
        "ros-swg/turtlebot3_demo": ["security", "eco-network-security"],
    }
    if repository in exact:
        return exact[repository]
    text = (repository + " " + title).lower()
    rules = [
        (("ros2_documentation",), ["architecture", "workspace", "pubsub", "launch", "testing"]),
        (("ros2/design",), ["architecture", "executors", "lifecycle", "network"]),
        (("nav2", "navigation2", "rosmaster", "linorobot"), ["project-navigation", "eco-nav2-stack", "eco-nav2-task-programming"]),
        (("moveit", "mycobot"), ["project-manipulation", "eco-moveit-planning", "eco-manipulation-tasks"]),
        (("micro-ros", "platformio"), ["eco-microcontrollers"]),
        (("ros2_control", "ros2_controllers", "control.ros.org", "roscon2022_workshop", "diffdrive_arduino"), ["eco-control-framework", "eco-hardware-integration", "eco-diff-drive-tracks"]),
        (("gazebo", "ros_gz", "webots"), ["eco-gazebo-simulation", "eco-model-rviz"]),
        (("geometry", "tf2"), ["tf2", "eco-tf-frames", "math-rigid"]),
        (("urdf", "xacro", "robot_state_publisher"), ["eco-model-rviz", "math-kinematics"]),
        (("image_", "opencv", "perception_pcl"), ["eco-perception-pipeline"]),
        (("slam_toolbox", "cartographer"), ["theory-slam", "eco-slam-mapping"]),
        (("robot_localization",), ["math-estimation", "eco-state-estimation"]),
        (("turtlebot3", "ros_tutorials"), ["graph-cli", "project-navigation", "eco-gazebo-simulation"]),
        (("open-rmf", "multirobot"), ["eco-multi-robot"]),
        (("px4",), ["theory-aerial"]),
        (("isaac",), ["eco-accelerated-robotics"]),
        (("canopen", "bunker", "ugv_sdk", "agrosense"), ["eco-hardware-integration", "eco-diff-drive-tracks"]),
        (("rosbag", "rqt_bag"), ["time-bag", "eco-data-observability"]),
        (("tracing", "tracetools"), ["performance", "eco-data-observability"]),
        (("rviz", "visualization", "interactive_markers"), ["eco-model-rviz"]),
        (("rclcpp", "rclpy"), ["pubsub", "services", "executors", "cpp-engineering"]),
        (("launch",), ["launch", "testing"]),
        (("interfaces", "rosidl"), ["interfaces", "parameters"]),
        (("pluginlib",), ["composition", "eco-control-framework"]),
        (("sros2", "ros-swg"), ["security", "eco-network-security"]),
        (("rmw_zenoh",), ["network", "eco-network-security"]),
        (("ros2cli",), ["graph-cli"]),
        (("realtime_support", "rttest"), ["performance", "math-control", "cpp-engineering"]),
        (("ros1_bridge",), ["migration"]),
        (("ros2/examples", "ros2/demos", "ros2-examples", "fundamentals_examples", "ros2_town"), ["pubsub", "services", "actions", "qos", "testing"]),
        (("fishbot", "articubot", "my_bot"), ["project-navigation", "eco-model-rviz", "eco-diff-drive-tracks"]),
        (("ros2_cookbook",), ["workspace", "pubsub", "qos", "deployment"]),
        (("robotics_tutorial",), NEW_LESSONS),
        (("ros2_tutorial", "ros2_tuition", "ros2_course", "ros2-guides", "ros2bookcode", "d2l-ros2", "ros2_21_tutorials", "robotics_academy", "ros2_limo", "ros2-tutorials-ws"), ["architecture", "workspace", "pubsub", "launch", "project-navigation"]),
    ]
    for patterns, lessons in rules:
        if any(pattern in text for pattern in patterns):
            return lessons
    return ["architecture"]


def license_label(root: Path, license_files: list[dict]) -> tuple[str, str]:
    """仅识别原文件里的显式文字，保留独立许可路径，不作重新授权判断。"""
    labels = set()
    for item in sorted(license_files, key=lambda item: len(item["path"]))[:8]:
        path = root / item["path"]
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")[:14000]
        if re.search(r"CC BY-NC-ND|Attribution-NonCommercial-NoDerivatives", text, re.I):
            labels.add("CC BY-NC-ND")
        elif re.search(r"CC BY-NC|Attribution-NonCommercial", text, re.I):
            labels.add("CC BY-NC")
        elif re.search(r"CC BY-ND|Attribution-NoDerivatives", text, re.I):
            labels.add("CC BY-ND")
        elif re.search(r"CC BY 4|Attribution 4.0", text, re.I):
            labels.add("CC BY 4.0")
        if "Apache License" in text or "Apache-2.0" in text:
            labels.add("Apache-2.0")
        if "MIT License" in text or "Permission is hereby granted, free of charge" in text:
            labels.add("MIT")
        if "BSD" in text or "Redistribution and use in source and binary forms" in text:
            labels.add("BSD 类声明")
        if "GNU GENERAL PUBLIC LICENSE" in text:
            labels.add("GPL")
        if "GNU LESSER GENERAL PUBLIC LICENSE" in text:
            labels.add("LGPL")
    if not license_files:
        return "未发现独立许可文件", "仓库公开可访问不等于已授予自由转载许可；源文件头或包声明仍须另行核对。"
    label = " / ".join(sorted(labels)) or "见独立许可文件"
    note = "这里只标记原始许可文件中识别出的文字；不同文档、代码和嵌套依赖可能使用不同条款。"
    if root.name == "Robotics_Tutorial":
        note += "根许可证为 CC BY-NC 4.0，部分正文页眉另写 CC BY 4.0；不能据页眉将整个快照重新许可。"
    return label, note


def choose_entries(root: Path, repository: str) -> list[dict]:
    """优先真正教程入口；排除代理规则、编辑器配置、测试数据 README。"""
    preferred = {
        "ros2/ros2_documentation": ["source/Tutorials.rst", "source/First-Steps.rst", "source/index.rst"],
        "ros2/design": ["articles/010_why_ros2.md", "index.md"],
        "MetroRobots/rqt_bag_diagnostics_demo": ["rqt_bag_diagnostics_demo/the_plugin.py", "generate_data.py"],
        "ros2/ros2": ["README.md", "ros2.repos"],
        "ros-navigation/docs.nav2.org": ["docs/getting_started/index.md", "docs/tutorials/index.md", "docs/configuration_and_development/first_time_robot_setup_guide/index.md"],
        "moveit/moveit2_tutorials": ["index.rst", "doc/tutorials/getting_started/getting_started.rst", "README.md"],
        "ros-controls/control.ros.org": ["index.rst", "README.md"],
        "gazebosim/docs": ["harmonic/install.md", "harmonic/ros_installation.md", "harmonic/building_robot.md", "README.md"],
        "micro-ROS/micro-ROS.github.io": ["_docs/tutorials/core/first_application_linux/index.md", "_docs/tutorials/core/first_application_rtos/index.md", "README.md"],
        "mmmarinho/ROS2_Tutorial": ["docs/source/index.rst", "README.md"],
        "zeeshanhaider1007/ROS2_Limo_Cobot_Training": ["day1-ros2-concepts.pdf", "README.md"],
        "zsc/ros2_tutorial": ["index.md", "chapter1.md"],
        "Rzl6/ROS2_Tuition": ["_book/index.html", "README.md"],
        "Michael-Jetson/Robotics_Tutorial": ["00_项目导航/项目总导航.md", "SUMMARY.md", "README.md"],
    }
    candidates = list(preferred.get(repository, []))
    candidates += ["README.md", "README.rst", "README", "Readme.md", "readme.md", "index.rst", "index.md", "doc/index.rst", "docs/index.rst"]
    # 实时仓库没有根 README，其真正说明位于 rttest 子包。
    if repository in {"ros2/rttest", "ros2/realtime_support"}:
        candidates = ["rttest/README.md"] + candidates
    result, seen = [], set()
    for candidate in candidates:
        path = root / candidate
        if path.is_file() and candidate not in seen:
            seen.add(candidate)
            result.append({"path": relative(path), "format": path.suffix.lstrip(".") or "text", "label": candidate})
            if len(result) == 3:
                return result
    if not result:
        fallbacks = sorted(path for path in root.rglob("*")
                           if path.is_file() and path.suffix.lower() in {".md", ".rst", ".pdf"}
                           and not any(part.startswith(".") or part in {"test", "tests"} for part in path.relative_to(root).parts)
                           and path.name.upper() not in {"AGENTS.MD", "CLAUDE.MD", "CONTRIBUTING.MD"})
        for path in fallbacks[:3]:
            result.append({"path": relative(path), "format": path.suffix.lstrip("."), "label": path.relative_to(root).as_posix()})
    if not result:
        # 少数官方配套插件仓库没有 README，直接以实际插件源文件作为阅读入口。
        # 不把 setup.py、包配置或代理规则当作教程正文。
        code = sorted(path for path in root.rglob("*") if path.is_file()
                      and path.suffix in {".py", ".cpp", ".hpp", ".c"}
                      and path.name not in {"setup.py", "__init__.py", "conf.py"}
                      and not any(part.startswith(".") or part in {"test", "tests"} for part in path.relative_to(root).parts))
        for path in code[:3]:
            result.append({"path": relative(path), "format": path.suffix.lstrip("."), "label": path.relative_to(root).as_posix()})
    return result


def library_data() -> dict:
    manifest, catalog = load(LIBRARY / "manifest.json"), load(LIBRARY / "catalog.json")
    configured = {item["id"]: item for item in catalog["sources"]}
    snapshots = []
    for original in manifest["snapshots"]:
        root = (LIBRARY / original["localPath"]).resolve()
        if not root.is_dir():
            raise FileNotFoundError(root)
        entries = choose_entries(root, original["repository"])
        licenses = original["licenseFiles"]
        label, note = license_label(root, licenses)
        category = original["category"]
        content_type = {"official-docs": "文档正文与版本资料", "official-examples": "示例源码与说明",
                        "official-core": "库源码与 API 说明", "ecosystem": "生态项目源码与教程",
                        "community-zh": "中文课程原文或配套源码", "community-en": "英文课程原文或配套源码",
                        "existing": "原有教程或参考工程"}[category]
        source = configured.get(original["sourceId"], {})
        record = {"id": original["id"], "sourceId": original["sourceId"], "title": original["title"],
                  "repository": original["repository"], "sourceUrl": original["sourceUrl"],
                  "category": category, "ref": original["ref"], "commit": original["commit"],
                  "localPath": relative(root), "available": True,
                  "entryPath": entries[0]["path"] if entries else "",
                  "entryFormat": entries[0]["format"] if entries else "",
                  "entries": entries, "contentType": content_type,
                  "licenseLabel": label, "licenseNote": note,
                  "licenseFiles": [{"path": relative(root / item["path"]), "sha256": item["sha256"]}
                                   for item in licenses],
                  "inventory": original["inventory"],
                  "description": source.get("title", original["title"]),
                  "relatedLessons": repository_lessons(original["repository"], original["title"]),
                  "mappingStatus": "用途关联；不表示仓库细节已全部进入正文",
                  "reviewLevel": "下载回执、许可文件与本地入口核对；未逐文件精读所有源码",
                  "runtimeValidation": original["runtimeValidation"],
                  "storageStatus": original["status"],
                  "portableArchiveIncluded": False,
                  "portableNote": "便携教材仅内置此索引；本机原始资料目录需另行复制，缺失时不能显示为正文已包含。"}
        if "archivePath" in original:
            record.update(archivePath=relative(LIBRARY / original["archivePath"]),
                          archiveSha256=original["archiveSha256"], archiveBytes=original["archiveBytes"])
        snapshots.append(record)
    # 使用实际归档 SHA 分组，只把跨来源相同归档标为重复；不同发行版不随意合并。
    hashes = defaultdict(list)
    for item in snapshots:
        if item.get("archiveSha256"):
            hashes[item["archiveSha256"]].append(item)
    duplicate_groups = []
    for digest, items in hashes.items():
        if len({item["sourceId"] for item in items}) < 2:
            continue
        canonical = next((item for item in items if item["repository"] == "ros2/realtime_support"), items[0])
        duplicate_groups.append({"archiveSha256": digest, "canonicalSnapshotId": canonical["id"],
                                 "canonicalSourceId": canonical["sourceId"],
                                 "snapshotIds": [item["id"] for item in items],
                                 "sourceIds": list(dict.fromkeys(item["sourceId"] for item in items)),
                                 "explanation": "实际原始归档字节相同；两个来源地址不能被当作两套独立资料。"})
        for item in items:
            if item["id"] != canonical["id"]:
                item["duplicateOf"] = canonical["id"]
                item["duplicateNote"] = "与标明的快照具有相同归档 SHA256；保留来源追溯，不重复计算独立内容。"
    repositories = []
    grouped = defaultdict(list)
    for item in snapshots:
        grouped[item["sourceId"]].append(item)
    for identifier, items in grouped.items():
        first = items[0]
        entry = {"id": identifier, "title": first["title"], "repository": first["repository"],
                 "category": first["category"], "description": first["description"],
                 "sourceUrl": first["sourceUrl"], "relatedLessons": first["relatedLessons"],
                 "versions": [{"id": item["id"], "ref": item["ref"], "commit": item["commit"],
                               "localPath": item["localPath"], "entryPath": item["entryPath"],
                               "entryFormat": item["entryFormat"], "licenseLabel": item["licenseLabel"],
                               "contentType": item["contentType"], "runtimeValidation": item["runtimeValidation"]}
                              for item in items]}
        group = next((group for group in duplicate_groups if identifier in group["sourceIds"] and identifier != group["canonicalSourceId"]), None)
        if group:
            entry["duplicateOf"] = group["canonicalSourceId"]
        repositories.append(entry)
    return {"meta": {"schemaVersion": 1, "checkedAt": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
                     "pathBase": "workspace-root", "purpose": "章末溯源与站内资料附录，不能替代自足教材正文",
                     "verification": "读取下载 manifest 与实际本地目录、许可文件、阅读入口；运行状态沿用实际回执。",
                     "sourceCountNote": "99 是新增下载来源条目数，包含一组相同归档；版本数、文件数、仓库数均不能冒充独立课程或内容吸收量。",
                     "contentReuse": "这里只复制元数据；源正文保留在独立目录，许可证不随教材统一改变。",
                     "localAvailability": "available=true 仅表示构建时本机存在，浏览器访问时仍须检查本机服务/目录是否可用。"},
            "counts": {"downloadedSourceEntries": manifest["downloadedRepositories"],
                       "downloadedSnapshots": manifest["downloadedSnapshots"],
                       "existingSnapshots": manifest["existingSnapshots"],
                       "sourceEntries": len(repositories), "snapshots": len(snapshots),
                       "duplicateArchiveGroupsAcrossSources": len(duplicate_groups),
                       "distinctDownloadedArchiveContents": len(hashes),
                       "submodules": len(manifest["submodules"]), "lfsFiles": len(manifest["lfsFiles"])},
            "categories": [{"id": key, "sourceEntries": len({item["sourceId"] for item in snapshots if item["category"] == key}),
                            "snapshots": sum(item["category"] == key for item in snapshots)}
                           for key in dict.fromkeys(item["category"] for item in snapshots)],
            "repositories": repositories, "snapshots": snapshots, "duplicateGroups": duplicate_groups,
            "submodules": [{"id": item["id"], "parentId": item["parentId"], "repository": item["repository"],
                            "commit": item["commit"], "localPath": relative(LIBRARY / item["localPath"]),
                            "runtimeValidation": item["runtimeValidation"]} for item in manifest["submodules"]],
            "websiteEntrypoints": manifest["websiteEntrypoints"]}


def main() -> None:
    coverage, library = coverage_data(), library_data()
    known = set(NEW_LESSONS)
    for name in ("core", "ecosystem", "extra", "frontier"):
        known.update(chapter["id"] for chapter in load(SOURCE / f"{name}.json")["chapters"])
    for entry in coverage["entries"]:
        assert set(entry["relatedLessons"]) <= known, entry["file"]
        assert (WORKSPACE / entry["localPath"]).is_file(), entry["file"]
    for entry in library["snapshots"]:
        assert set(entry["relatedLessons"]) <= known, entry["id"]
        assert (WORKSPACE / entry["localPath"]).is_dir(), entry["id"]
        assert entry["entryPath"] and (WORKSPACE / entry["entryPath"]).is_file(), entry["id"]
    assert len({entry["id"] for entry in coverage["entries"]}) == len(coverage["entries"])
    write(SOURCE / "reference-coverage.json", coverage)
    write(SOURCE / "local-library.json", library)
    print(json.dumps({"coverage": coverage["statistics"], "library": library["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
