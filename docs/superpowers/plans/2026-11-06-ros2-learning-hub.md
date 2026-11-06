# ROS 2 学习图谱 Implementation Plan

> **For agentic workers:** 使用 superpowers:executing-plans，在本次对话完成；用户已授权跳过后续设计确认。

**Goal:** 交付有正文、代码对照、完整来源目录与项目路线的中文 ROS 2 学习网站。
**Architecture:** 独立静态网站；研究 JSON 规范化为浏览器数据；UI 以 hash 路由工作，无外部依赖。
**Tech Stack:** HTML / CSS / JavaScript、Python 标准库、Node 内建测试、浏览器检查。
**Spec:** `docs/superpowers/specs/2026-11-06-ros2-learning-hub-design.md`

## Global Constraints

- ROS 2 Jazzy / Ubuntu 24.04；核查日期 2026-11-06。
- 新建 `ros2-learning-hub/`，源站与参考仓库不修改。
- Sites 默认仅本人可见；可用时发布，服务不可用时交付本地完整版本。
- 原创中文说明、可追溯来源、片段明确标注，不将浏览器测试说成 ROS 运行验证。

## Review Focus

- 损坏或不可用的 localStorage 不影响阅读。
- 搜索输入包含 HTML、符号或中英文混合时安全显示。
- 无效 hash、页内锚点及浏览器返回不使页面空白。
- 长代码、长链接、宽屏对照在 390px 视口内保持可读。
- 下载、来源、教程目录与版本标记对应实际文件和核查范围。

### Task 1: 内容、来源与教学工程

**Files:** `ros2-learning-hub/source/*.json`、`scripts/build_content.py`、`dist/content.js`、`examples/`、`dist/downloads/`。
**Interfaces:** 输出 `ROS2Hub`（meta/stages/lessons/comparisons/resources/catalog/projects/issues/glossary）；章节含 id/title/stage/summary/goals/concepts/steps/expected/pitfalls/exercise/sourceIds。

- [ ] 汇合已核查研究，保留核查方式，加入两套教程全部169个本地页面目录。
- [ ] 编写教学包与运行说明；以真实 Jazzy 安装进行构建/隔离通信验证（若依赖可用），记录限制。
- [ ] 校验唯一 ID、来源引用、路径/源码可达及代码分类。

### Task 2: 文档界面与交互

**Files:** `dist/index.html`、`dist/styles.css`、`dist/logic.js`、`dist/app.js`、`tests/logic.test.cjs`。
**Interfaces:** 消费 ROS2Hub；输出首页、课程、对照、资源、生态、项目、排错路由；`HubLogic.search(data,q)`、`parseRoute(hash)`、`sanitizeState(value,ids)`、`qosCompatible(offered,requested)`。

- [ ] 先为混合搜索、路由降级、进度容错、QoS兼容性写有行为断言的测试，观察缺少实现导致失败。
- [ ] 完成温暖纸白/墨绿/橙色技术文档 UI，带原创 SVG 图解与代码对照。
- [ ] 完成搜索、资料筛选、复制、收藏、进度、导出、快捷键及手机导航。
- [ ] 运行逻辑测试与桌面/手机真实浏览器检查；检查无障碍焦点与整页溢出。

### Task 3: 交付与复核

**Files:** `README.md`、`THIRD_PARTY_NOTICES.md`、`tests/browser-checks.js`、`.openai/hosting.json`（服务可用时）。
**Interfaces:** 消费静态 dist 和测试证据；输出可打开的网站、源码、验证记录、可用时的部署地址。

- [ ] 集成现有控制工坊及其许可，生成离线资料与示例下载。
- [ ] 独立审查全部网站，修复影响阅读、内容准确性或交互的实质问题。
- [ ] 通过 Sites 打包发布已验证源码；记录服务故障而不影响本地交付。
- [ ] 打开最终网站，说明内容数量、验证范围与入口。
