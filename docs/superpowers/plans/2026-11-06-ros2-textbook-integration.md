# ROS 2 理论实践教材整合 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for the site integration. Sites permits bounded research assets; research helpers write separate source JSON only.

**Goal:** 将双栏样稿应用为完整离线教材，纳入 Robotics_Tutorial 的知识范围，补充原理、公式推导、图解和可执行实验。
**Architecture:** 保留原有 44 章，新增数学基础与工程实践课程；所有来源和主题建立本地覆盖索引。静态 HTML/JS 阅读器复用统一内容，连续 HTML 使用原生 MathML 和内嵌 SVG，完整离线包包含代码、索引与许可证。
**Tech Stack:** Python stdlib 内容构建、HTML/CSS/JS、离线 SVG、MathML，Playwright 浏览器检查。
**Spec:** ../specs/2026-11-06-ros2-learning-hub-design.md，及用户本轮要求理论实践结合的回复。

## Global Constraints

- 中文，ROS 2 Jazzy / Ubuntu 24.04 主线，版本差异明确。
- 用户回复设计审查后直接要求完善内容，按现有布局继续；无需再次设计确认。
- 教材可离线完整阅读，外链只作出处；第三方软件安装与数据准备另列。
- 不宣称穷尽全网或未经逐项核实的细节。覆盖索引分别标明详细讲解、主题概览、延伸范围，不把主题关联冒充逐段收录。
- 原创讲解，引用官方文档、维护者源码与原始论文；社区教程的结论需交叉验证，不搬运其全文。
- 当前根目录已在迁移时纳入Git；仅编辑ros2-learning-hub与任务文档，不改变第三方参考源码。
- 优先本地离线交付，本次不发布站点。

## Review Focus

- 公式的坐标约定、单位、推导前提和退化情况；用数值实验检验重要恒等式。
- 文件协议与完全断网时的公式、图形、搜索、下载；连续 HTML 不依赖脚本和外部文件。
- 新旧章节路径、代码多写法、进度记录和移动端无溢出。
- 资源映射的粒度与覆盖声明一致；不能用目录条数证明细节已经完整。
- 示例验证范围诚实：区分语法、数值实验、ROS 编译互通、真实硬件。

### Task 1: 来源清点与理论实践内容

**Files:** source/math-foundations.json、source/applied-robotics.json、source/reference-coverage.json、source/topic-depth.json，必要的 diagrams/*.svg 与 theory_labs/。
**Interfaces:** 新章节遵循现有章节字段，sections 增加 equations: [{tex,label,explanation,symbols:[{symbol,meaning,unit}]}]。研究输出仅作为离线原创正文素材，由主代理合并。

- [x] 克隆并清点新增仓库，记录 revision 与逐页标题。
- [x] 编写八章数学基础与八章机器人理论实践，每章至少五个实质小节、符号解释、逐步推导、数值例子、完整实验和三道带答案练习。
- [x] 整理三个指定教程以及官方/主流项目的主题对应，明确覆盖深度与延伸边界。
- [x] 运行教材数值实验与现有基础示例，保留验证结果。

### Task 2: 双栏阅读器、数学和图解整合

**Files:** scripts/build_content.py、scripts/book_export.py、scripts/math_render.py、dist/index.html、dist/reader.js、dist/reader.css、dist/preview/、tests/reader-checks.cjs。
**Interfaces:** 公式构建为可直接显示的 MathML 字符串；静态图和交互图共享 manifest。旧 #/lesson/id 路由继续可用。

- [x] 为公式导出与覆盖索引建立缺失时失败的检查。
- [x] 应用双栏布局，保留章节阅读、代码标签、搜索、进度/书签、资料、项目、全部下载和旧路由。
- [x] 将公式和图解加入交互教材及连续 HTML/Markdown，长公式容器滚动。
- [x] 检查所有章节、公式和图解，以及 file://、断网和 320/390px 手机布局。

### Task 3: 离线交付与复核

**Files:** README.md、THIRD_PARTY_NOTICES.md、dist/downloads/、deliverables/、tests/。

- [x] 打包基础项目和数值实验，重建完整教材与来源覆盖清单。
- [x] 运行内容结构、数学数值、ROS 示例及浏览器检查。
- [x] 独立审查最终阅读与导出结果，修复重要问题。
- [x] 更新离线压缩包和 SHA256，打开正式入口，说明实际覆盖与验证边界。

## 进度

2026-11-06：用户在设计审查回复中要求直接综合资料完善内容。主代理沿用现有设计开始整合；初始 44 章及双栏图解样稿已存在，不重复制作。


2026-11-07：上述三项任务均已完成并验收。正式入口替换为双栏阅读器，新增16章、49公式、11组API及真实深度/本地资料附录。原有331处代码和64个工程文件加中文注释；100条完整源码导出保存真实文件名。13个SVG与2种交互接入，连续版49MathML/29SVG内嵌，Markdown与ZIP同源。

实际验证：通信2包/基础10包构建，通信5项、基础15项、导航12类假服务端协议、16标准库理论实验及浏览器/单元检查通过。独立审查12个发现条目全部有修订证据，见validation-evidence/review-resolutions.json。完整仿真与硬件未运行；这属于明确验证边界，不冒充通过。最终交付以教材VALIDATION.md、CONTINUE.md和deliverables/SHA256SUMS为准。本轮没有发布或推送。
