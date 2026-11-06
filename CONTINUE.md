# 换机续作说明

保存日期：2026-11-06（Asia/Shanghai）。目的：迁移全部工作资料和未完成改动，继续完成用户要求的中文 ROS 2 离线教材网站。

## 给新会话的任务说明

> 请先阅读本文件、`docs/superpowers/specs/2026-11-06-ros2-learning-hub-design.md` 和 `docs/superpowers/plans/2026-11-06-ros2-textbook-integration.md`，然后从未完成项继续，不要重做已完成的教材和样稿。始终使用中文。用户要求综合官方文档、官方示例、主流教学项目以及 zsc/ros2_tutorial、Rzl6/ROS2_Tuition、Michael-Jetson/Robotics_Tutorial，形成完整离线教材，而非外链目录。原理清楚，公式有符号、单位、前提和逐步推导，图文结合，理论与实践对应；**涉及代码必须有详细中文注释，下载源码保留同样注释**。
>
> 采用已认可的 GitBook 式双栏：左章节树、右宽正文；正文内语言标签切换，另可并排对照。用户先要求审查设计，已收到带 6 张 SVG 和 2 种交互图的样稿；随后在审查回复中要求继续综合资料完善内容。因此沿用样稿推进，不需重复询问展现形式。最后用户为更换电脑要求保存和推送，本次暂停内容实施、完成迁移。

## 已完成、可直接使用

- 两套早期教程已克隆；新增 `Robotics_Tutorial/` 已克隆。控制与底盘参考工程共 8 个也在工作区内。各提交以 `TRANSFER_MANIFEST.json` 为准。
- `ros2-learning-hub/dist/content.js`：44 章、12 组写法对照、132 条来源，早期两套教程的 169 页主题对应；每章包含深入正文、案例、练习答案和代码。
- `dist/index.html`：上一版完整交互网站（搜索、进度、收藏、资料、项目、下载等）。因换机时新版整合尚未完成，已从现有离线包恢复可用入口。
- `dist/book.html`：独立 HTML 全文，不依赖 JavaScript 或外部资产；`dist/downloads/ros2-learning-guide.md` 为 Markdown 正文。
- `dist/layout-preview.html/css/js`：已获方向认可的双栏设计样稿，复用同一内容数据；代码标签与并排比较、搜索、手机侧栏可用。
- `dist/preview/`：6 张原创 SVG（架构、Pub/Sub、Action、生命周期、控制循环、Nav2）共 14 处上下文位置；二维刚体变换和三维关节模型交互。静态图有放大；二维滑块改变真实坐标计算；三维相机视角与关节姿态分离。
- `examples/`：`atlas_cpp`/`atlas_py` 通信工程及 4 个标准库离线实验。ROS 编译与跨语言发布订阅/服务、三种 launch 解析的既有验证见 `examples/VALIDATION.md`。
- `foundation-examples/`：从本机临时验证工作区抢救保存的 10 个基础 ROS 包及 Python 示例，源文件 52 个；不含 build/install。此前构建和部分运行记录在 `validation-evidence/foundation/`。不要把已有记录当成本次换机后已重新验证。
- `deliverables/ros2-learning-hub-offline.zip`：上一次完成的离线阅读包，带 SHA256。**这个包不包含所有最新设计和未完成改动；完整开发状态请以 Git 仓库目录为准。**

## 本次被换机打断的工作

1. `work-in-progress/reader-integration.html`、`reader.js` 保存了开始替换正式入口时的草稿。HTML 引用了尚未写出的 `reader-library.js` 和 `reader.css`，当前不可作为正式入口。应继续实现、测试后再放回 `dist/index.html`，不要直接覆盖已恢复的可用入口。
2. `scripts/math_render.py` 已实现 TeX → 原生 MathML、公式符号表和 Markdown 输出；构建依赖 `latex2mathml==3.81.1` 已完整保存于 `scripts/vendor/`。无需重新联网安装。`tests/test_math_export.py` 的两个检查已通过。
3. `scripts/book_export.py` 已开始接入 equations，但 `book_figure()` 尚未实现。在构建器添加 `data['figures']` 前必须实现该函数并处理 SVG ID 唯一性。现有构建数据没有 figures，所以旧内容流程尚不触发此分支。
4. `tests/reader-checks.cjs` 是新版整合的目标验收，已经见到预期失败（旧正式入口没有新的双栏章节树）。**它不是目前可宣称通过的测试**。检查覆盖进度保存、新旧路由、所有章节、公式、图解、资料过滤、手机布局、断网与无脚本连续版。
5. 三个研究任务被暂停，**尚未生成** `source/math-foundations.json`、`applied-robotics.json`、`reference-coverage.json`。任务接口在 `source/RESEARCH-CONTRACT.md`，不能把计划的 16 新章算作已完成内容。
6. 之前 `source/ecosystem.json` 中的本机绝对路径已改为可移植的环境变量/下载步骤，但尚未完整重新生成教材和离线包。恢复时比较内容源与生成物，统一重建。

## 下一步，按顺序

1. 完成内容研究与详细注释。数学 8 章 ID：`math-linear`、`math-rigid`、`math-probability`、`math-estimation`、`math-optimization`、`math-kinematics`、`math-dynamics`、`math-control`。应用 8 章：`cpp-engineering`、`theory-slam`、`theory-planning`、`theory-optimal-control`、`theory-legged`、`theory-aerial`、`project-navigation`、`project-manipulation`。逐章写原创自足正文、公式推导、数值例子、可执行实验、排错与带答案练习；补充旧代码注释。不要为凑数量机械扩写。
2. 清点第三套教程并建立真实覆盖索引。区分详解、概览、延伸范围，不能用“标题映射”冒充所有细节已编入。然后修改 `scripts/build_content.py` 接入新章/公式/图解/覆盖数据，完成双栏阅读器。保留原搜索、进度、收藏、代码比较、下载和 `#/lesson/id` 等旧路由。
3. 完成连续 HTML 的内嵌 SVG/MathML 与 Markdown 导出，保存带详细注释的源码包；运行合适的内容、数值、ROS 示例和浏览器验证，再重建离线 ZIP、SHA256 与说明。当前任务优先本地离线，不要擅自发布或重新注册 Sites 项目。

## 核查中发现的具体问题

- Robotics_Tutorial 当前清点为 437 个 tracked 文件、430 个 Markdown；SUMMARY 中有 395 个链接，其中 10 个目标缺失（需复核并记录路径）。README 的旧文件计数不是本轮准确教学页数量。导航、审核记录与项目规则不能混作教学正文。
- `eco-network-security` 中 Zenoh 示例设置 `RMW_IMPLEMENTATION=rmw_zenoh_cpp` 后，后续 SROS2 示例若只设置 `ROS_SECURITY_*` 与 `--enclave`，会混淆安全后端。应明确切回 DDS（如 Fast DDS）再讲 DDS-Security，或完整讲解 Zenoh 自己的 session/router 配置。参考官方 Jazzy `zenoh_security_tools` 文档。
- 社区资料中“ZMP 在支撑多边形内即可保证稳定”“全身动力学 MPC 不能实时”“固定 GPU 加速倍数”等说法需要附加假设或修正。KF 的高斯条件、ESKF/InEKF 的能力、四元数协方差也需核对原始文献，不照抄强结论。
- PX4 相关教材需要明确文档版本及 ROS 配套环境，不把官方 Humble 示例标成已在 Jazzy 验证。

## 在新电脑运行和检查

从 `ros2_robot` 开始：

```bash
# 只阅读教材：Python 3 即可；也可直接双击 HTML。
python3 -m http.server 8766 --bind 127.0.0.1 --directory ros2-learning-hub/dist
```

另一个终端：

```bash
cd ros2-learning-hub
node --test tests/logic.test.cjs tests/textbook.test.cjs tests/preview-geometry.test.cjs
python3 tests/test_math_export.py
python3 tests/test_offline_labs.py
python3 tests/check_content.py
```

浏览器检查需要本机 Playwright 与 Chromium。测试里的默认 Playwright 路径来自旧电脑，应在新电脑设置 `PLAYWRIGHT_MODULE` 指向可用 Node 包，再运行 `node tests/design-preview-checks.cjs`。`tests/browser-checks.cjs` 是旧正式网站验证；`tests/reader-checks.cjs` 留待新版实现后运行。不要把浏览器通过当作 ROS 或实机通过。

基础工程重建见 `foundation-examples/README.md`。旧电脑 `/tmp/ros2-atlas-build`、`/tmp/ros2-foundation-validation-b3pfmcge` 等编译目录不随迁移；所有必要源文件已保留。终端会话、浏览器 LocalStorage 的个人阅读进度、登录态和代理会话不能从 Git 恢复，用户如需要个人进度可在旧网站“我的学习记录”导出 JSON。

## 实施约束

- 始终中文回复。代码详细注释是用户最后新增的明确要求。
- 各参考仓库原文件尽量不改；修改原创网站和任务文档。新的理论与图解必须有对应正文解释。
- 来源只作出处，读者不应为了补齐本章主要内容被迫跳转外站。联网安装生态软件与离线读教材是两回事。
- 精确说明验证范围：语法、数值单元检查、ROS 构建/互通、仿真/硬件分别记录。不要称“全网无遗漏”或“所有项目均已运行”。
- 既有 Sites 私有项目没有发布；本地 `.openai` 身份配置不上传，不要为恢复教材重新创建托管项目。
