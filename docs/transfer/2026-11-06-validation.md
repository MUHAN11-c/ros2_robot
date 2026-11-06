# 2026-11-06 换机前检查

本记录验证迁移时仍可使用的内容，不代表教材扩展已完成。

在 `ros2-learning-hub/` 执行并通过：

```bash
node --test tests/logic.test.cjs tests/textbook.test.cjs tests/preview-geometry.test.cjs
python3 tests/test_math_export.py
python3 tests/test_offline_labs.py
python3 tests/check_content.py
node tests/design-preview-checks.cjs
```

- 逻辑、教材渲染与几何的三个 Node 测试文件通过。
- 公式导出两个 Python 检查通过；四个标准库离线实验检查通过。
- 内容检查通过：44 章、104148 个正文汉字、182 项练习及答案、330 个代码块、83 个完整代码文件、169 个早期教程页面映射。
- 双栏样稿断网检查：6 张静态图、14 处上下文位置、2 种交互图；390px/320px 无整页溢出，无脚本错误、无 HTTP 请求。
- 正式入口从既有离线包恢复；未完成的新阅读器已转存 `work-in-progress/`。`tests/reader-checks.cjs` 保留为待实现后的目标验收，目前有预期失败。
- 没有因本次迁移重新构建或运行全部 ROS 工程；以前的运行记录与源文件分别保留。

同步时还核对传输文件的 SHA256、嵌套 Git 元数据与凭据路径排除、按用户授权替换 learn 分支原有文件（不改 main），以及推送后 `learn` 分支提交号。
