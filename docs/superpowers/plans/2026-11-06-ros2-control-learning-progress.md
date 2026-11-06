# SDD ledger — plan: docs/superpowers/plans/2026-11-06-ros2-control-learning.md

Pre-flight: Task 1 提供 CourseLogic 与 LearningContent，Task 2 使用其名称与签名；Task 2 的固定 hash 由 Task 1 resolveLesson 校验；Task 3 验证前述全部页面。接口一致。

Ruling: 当前目录并非可用 Git 仓库，网站放入独立子目录，不建立 worktree/分支或提交；用本记录保留执行状态 — 遵守用户本地交付与现有参考源码隔离要求 — 若需版本管理可后续在网站目录单独建立。

Ruling: 用户明确授权“其他按方案直接完成”，不再执行计划/草稿的额外确认 — 延续用户已批准范围 — 页面细节由实现者决定。

Task 1: complete. 7 项逻辑测试先失败后通过；`node tests/logic.test.cjs` → 7/7；content.js 语法检查通过。

Ruling: 受限环境下 `node --test` 子进程未输出具体断言，直接运行基于 node:test 的测试文件获得完整 TAP 输出 — 保留同一套 Node 原生测试，避免不必要依赖 — 运行命令改为 `node tests/logic.test.cjs`。

Task 2: 主界面、七章、交互 SVG、动画、代码/测验/进度完成，正在浏览器验证。修正命令流指向广播器的教学歧义：定向浏览器检查先失败，再修正为突出差速控制器 A，通过检查。补齐 Sensor 到状态接口的数据流和 read only/read-write 英文说明。

Task 2: complete. Chromium 7 组行为检查全部通过，涵盖全部课程、图、文件标签、实际复制、循环/数值、测验、进度、搜索/来源、路由、320/390px 布局和异常存储。页面运行错误与控制台错误均为 0。

Final review: 独立只读审阅发现 1 项 Important：原图及初稿省略 Actuator 状态反馈；无 Critical/Minor。核对官方 Jazzy Getting Started 与本地 example_6 后确认。未进行第二次审阅。

Final: fixed Actuator 可选状态反馈 — diagram-checks.js 先失败，再补齐静态/动态连线、状态高亮、read optional 标注和中文解释，定向检查通过；完整浏览器 7 组、逻辑 7/7、离线/复制降级/SVG 导出再次通过。

Final: 发布资源带版本查询参数，修正浏览器保留旧 content.js 的缓存混用；证据为 HTTP 新内容与页面旧运行内容不一致，版本化资源后回归通过。无后台或网络依赖增加。

Task 3: complete. README、来源/许可与已导出全景 SVG 交付。HTML file:// 入口已在实际浏览器中验证；复制拒绝时手动回退通过；SVG 保留中英文字与执行器状态边，XML 解析通过。所有主要 JS 语法检查通过。未安装/构建/运行 ROS，未连接设备，未注册或上传/发布站点。

Final deferred minors: 无。审阅不覆盖真实 ROS 安装、构建、节点运行或实体设备行为；与用户本次本地学习网站范围一致。
