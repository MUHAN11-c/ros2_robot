# ros2_control 零基础学习网站 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 交付本地可运行、内容准确、带双语交互流程图的 Jazzy 入门学习网站。

**Architecture:** 独立静态目录，经典脚本共享 `window.CourseLogic`、`window.LearningContent`、`window.LearningDiagram`。课程通过 hash 路由切换，DOM 事件委派驱动交互；不依赖网络字体、CDN、框架、后台或 ROS 运行环境。

**Tech Stack:** HTML5、CSS Grid/Flex、JavaScript、SVG、Node 原生测试、Python 静态预览。

**Spec:** `docs/superpowers/specs/2026-11-06-ros2-control-learning-design.md`

## Global Constraints

- 用户已确认只做本地网站，其余直接完成；不再增加设计/发布确认。
- 主版本 ROS 2 Jazzy，简体中文，关键英文术语并存。
- 不更改现有参考仓库，不安装/构建/运行 ROS，不连接硬件。
- 独立目录 `ros2-control-learning-web/`，无构建依赖；无联网也能阅读主要课程。
- `TwistStamped`、`/cmd_vel`、`open_loop: true`、10 Hz 等说明与已核对源码一致。
- 浏览器动画是教学演示，进度只保存在本机浏览器。

## Review Focus

- 不可用/损坏的 localStorage：阅读和测验仍可使用，不使页面崩溃。
- 无效 hash 与浏览器前进后退：恢复合法课程，并同步导航/标题/完成状态。
- 只用键盘：流程图节点、模式切换、测验与折叠菜单可访问。
- 动画播放中离开课程：停止计时；暂停后不继续跳步；减少动态效果环境下不自动播放。
- 小屏与长命令：页面本身不横向溢出，图和代码有独立滚动容器。

## Task 1: 课程数据与可靠的浏览器状态

**Files:** `ros2-control-learning-web/content.js`、`logic.js`、`tests/logic.test.cjs`

**Interfaces:** `CourseLogic.wheelSpeeds(v,w,separation,radius)` 返回 `{left,right}`；`createProgress(storage)` 返回读取/完成/重置接口；`resolveLesson(hash, ids)` 返回合法 id；`LearningContent` 提供 lessons、terms、nodes、quizzes、sources。

- [x] 先写并运行有效测试：差速正转/旋转/无效参数、损坏/不可写存储、无效 hash。
- [x] 实现纯逻辑与容错；编写 7 章原创中文课程、准确代码、可观察预期和版本化官方引用。
- [x] 运行 `node --test tests/logic.test.cjs` 验证通过。

## Task 2: 学习工作台、可交互 SVG 与课程操作

**Files:** `index.html`、`styles.css`、`diagram.js`、`app.js`，均位于独立网站目录。

**Interfaces:** `LearningDiagram.render(mode, selected)` 返回 SVG 字符串；节点使用 `data-node`，应用通过事件委派更新详情。课程导航 hash 为 `#start/#architecture/#cycle/#files/#diffbot/#diagnose/#quiz`。

- [x] 实现响应式导航、学习标题、进度、搜索、来源面板、七章内容与完成动作。
- [x] 重绘架构 SVG：管理关系与数据流分开呈现、中文与英文并存、节点键盘选择、详情与官方来源、下载 SVG。
- [x] 实现 read/update/write 播放暂停单步及差速数值演示；离开页面清除计时器。
- [x] 实现代码复制与明确失败回退、文件选项卡、故障折叠面板、测验反馈、进度保存与重置。
- [x] 本地静态预览，检查所有路由及主要交互；先展示可识别的版本，再依据观测修正。

## Task 3: 验证、内容审阅与本地交付

**Files:** `README.md`、`THIRD_PARTY_NOTICES.md`、必要的验证记录。

**Interfaces:** `python3 -m http.server 8765 --bind 127.0.0.1 --directory ros2-control-learning-web`；直接打开 `index.html` 也可阅读。

- [x] 核对命令、模型/状态反馈说明和全部关键资料链接；注明核对日期和本地参考提交。
- [x] 执行桌面和手机浏览器检查：所有课程、图节点与过滤、键盘、复制、动画、测验、完成/重载/重置、无效 hash、存储失败和浏览器控制台。
- [x] 邀请一次独立最终审阅，修复实质问题；重跑受影响检查。
- [x] 交付入口、启动命令和验证范围。当前目录不是可用 Git 仓库，不创建分支或提交。

## 自查

课程、双语图、循环动画、文件职责、真实终端教程、排错、测验、搜索、来源与进度均有对应任务；不包括账号、联网运行机器人、部署或第三方服务。原图与已核对源码已在设计文档标明。
