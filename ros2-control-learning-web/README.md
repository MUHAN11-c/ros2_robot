# ros2_control 学习工坊

面向零基础的本地中文学习网站，以 **ROS 2 Jazzy** 为主。直接打开 `index.html` 即可使用主要功能，不依赖 npm、CDN、在线字体、后台或 ROS 安装。

## 打开网站

方式一：用现代浏览器直接打开本目录的 `index.html`。Chrome、Edge、Firefox 等支持本地静态页面；自动复制是否可用取决于浏览器，失败时页面提供手动复制。

方式二：在终端启动本地静态服务，获得稳定的浏览器存储与复制体验：

```bash
cd /home/mu/Desktop/ros2_jazzy_tracked_refs/ros2-control-learning-web
python3 -m http.server 8765 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8765/>。在终端按 Ctrl+C 停止服务。这个服务只监听本机；不会上传或发布网站。进度按浏览器和网址分别保存，文件地址与 HTTP 地址之间不共享进度。

## 学习内容

1. 从零开始：ROS 2 基本词汇、控制框架的作用、环境前提。
2. 读懂系统架构：依据用户原图与官方架构，用 SVG 重绘中英双语流程图；点击节点查看解释；切换全景、管理、状态反馈、命令下发；可下载独立 SVG。根据官方组件定义补齐原图省略的 Actuator 可选状态反馈。
3. 跟随一个控制周期：read → update → write 的播放、暂停与单步；差速轮速计算滑块。
4. 认识四类文件：URDF/Xacro、YAML、C++ 硬件插件、Launch 的职责和精简代码。
5. 跑通 DiffBot：独立工作空间、构建、启动、自检、发布 TwistStamped、观察状态、停止；后续对照 RRBot。
6. 生命周期与排错：从具体症状选择检查命令，解释状态与接口占用。
7. 知识自测：7 道题、即时反馈和课程回链，全部答对后可标记完成。

学习进度只保存在当前浏览器，可在侧栏重置；浏览器拒绝存储时仍可在本次页面会话中使用。术语搜索支持中文与英文，快捷键 `/`。流程图节点可通过 Tab 和 Enter/空格操作；文件页可用左右方向键切换选项卡。

## 版本与事实边界

资料核对日期：2026-11-06。主要依据：

- [官方 Jazzy Getting Started](https://control.ros.org/jazzy/doc/getting_started/getting_started.html)
- [官方 Jazzy DiffBot](https://control.ros.org/jazzy/doc/ros2_control_demos/example_2/doc/userdoc.html)
- [官方 Jazzy diff_drive_controller](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)
- `ros2_control_demos` jazzy：`fbab026e147824971c97996f3789f97c2ee9e9ac`
- `ros2_control` jazzy：`f9e24287fc1d6996e5ba1656a9ee24e5f33adef7`
- `ros2_controllers` jazzy：`bee185cbb98815116af9cfb00ff595b0b800e91a`

网页“官方文档与源码”面板提供各主题的具体页面，以及固定提交的示例文件链接。官方网页可能随 Jazzy 更新；如与教程出现差异，以实际使用版本的源代码和启动配置为准。

核对的几个重要细节：

- 本例 Python launch 的 manager 为 `/controller_manager`；控制器为 `diffbot_base_controller`；实际输入为重映射后的 `/cmd_vel`，类型为 `geometry_msgs/msg/TwistStamped`。
- 本例配置 `open_loop: true`，里程计使用目标速度积分。里程计变化不能证明真实编码器或设备通信正常。
- 本例 `update_rate=10 Hz`，不同于 YAML 中的 `publish_rate`。教学动画并不模拟真实时序。
- 默认硬件插件在软件中积分/镜像数值，未实现实体通信。网页未安装、编译或运行 ROS，也未连接真实机器人。
- 代码面板区分“可在终端运行的命令”“精简文件片段”和“伪代码”；后两者不可直接当成完整工程运行。

## 验证

无需安装测试依赖，运行逻辑检查：

```bash
node tests/logic.test.cjs
```

浏览器交互检查保存在 `tests/browser-checks.js`、`tests/diagram-checks.js` 和 `tests/offline-and-export-checks.js`，为接收 Playwright `page` 参数的异步函数，可通过 Playwright MCP 的 `browser_run_code_unsafe` 传入 `filename` 执行；执行前启动 8765 端口的静态服务。检查会清理测试浏览器该站点的 localStorage，请使用独立测试浏览器上下文。离线/导出检查会更新 `assets/ros2-control-architecture.svg`。

检查覆盖：7 章导航与路由恢复、流程图键盘操作、选项卡、实际剪贴板复制、数值计算、动画暂停/离页计时清理、测验改答、进度刷新保留、搜索、来源、手机菜单与焦点、320/390px 全课程布局、损坏/不可用存储。测试不会执行代码框中的 ROS 命令。

已在 Chromium 中通过上述检查，另验证了本地 `file://` 入口、剪贴板被拒绝时的手动回退、独立 SVG 导出与 XML 解析。手机检查是浏览器视口检查，未进行实体移动设备测试。`assets/ros2-control-architecture.svg` 提供一份已导出的双语全景图。

## 文件组织

- `index.html`：语义化页面框架和对话框。
- `styles.css`：本地字体、响应式布局、流程图和交互状态样式。
- `content.js`：原创中文课程、术语、测验、代码片段与来源。
- `diagram.js`：可交互中英双语 SVG 架构图。
- `logic.js`：差速计算、进度容错和路由校验。
- `app.js`：课程渲染、导航和交互。
- `tests/`：有行为断言的逻辑与浏览器检查。

本项目不修改同级官方参考源码。示例出处与许可见 `THIRD_PARTY_NOTICES.md`。
