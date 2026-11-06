# ros2_control 零基础学习 Web 设计

## 用户意图

制作中文学习网站，让零基础学习者理解 ros2_control；保留英文术语，以用户提供的架构图为依据重绘流程图，并参考官方文档与示例编写课程。

原始图位于 `/tmp/codex-clipboard-05740d44-b3c0-4b53-8128-689786df0319.png`；中英版本参考 `/home/mu/.codex/generated_images/01a1af79-ac6c-7282-b871-a69b831be536/exec-1ab09784-bc34-4685-93f7-ee3d5c2da7b9.png`。以原始图和官方架构文档核对连接关系，网页内用代码原生 SVG 重绘，无需继续用位图。

## 本次采用的默认选择

- 以当前参考工程对应的 ROS 2 Jazzy 为主，命令和示例均标明版本。
- 独立目录 `ros2-control-learning-web/`，保留现有参考源码；浏览器端 HTML、CSS、JavaScript 和 SVG，无后台、无构建依赖。
- 用户已确认：只做本地网站，其余按方案直接完成；不注册、上传或发布 Sites，不再逐步确认。保留完整源码，支持静态 HTTP 服务和直接打开本地入口。
- 中文正文，关键术语中英对照。课程内容为原创解释，附官方具体页面与 jazzy 源码链接。
- DiffBot 采用本地已核实的 Python launch（默认 `/controller_manager`，`diffbot_base_controller` 的 `~/cmd_vel` 重映射到 `/cmd_vel`），消息为 `TwistStamped`。`open_loop: true` 时里程计来源是目标速度，不能把里程计变化当成硬件反馈证据。避免照抄文档与当前 launch 不匹配的参数。

## 完整页面和课程

桌面为左侧课程导航、中间学习正文、可收起的右侧术语/提示栏；移动端折叠导航，流程图保留可横向浏览的完整比例。

1. **学习起点**：ros2_control 解决什么问题；ROS 2 节点、话题、URDF、关节的最小前置知识；环境准备和学习顺序。
2. **架构地图**：将原图重绘成 SVG，包含 Controllers、Controller Manager、Resource Manager、State/Command Interface、Sensor/System/Actuator、Hardware Resources、可选 Transmissions。点击节点查看通俗解释、职责、示例和官方出处；可切换完整视图、管理关系、状态反馈、命令下发；键盘也能访问节点。
3. **一个控制周期**：read → update → write 的分步动画；播放、暂停、单步；解释 ROS 话题与框架内部接口的区别。动画明确标明教学演示，不连接机器人。
4. **四类文件**：URDF/Xacro、控制器 YAML、硬件插件、Launch 的分工及相互对应，提供带解释的精简代码与复制操作。
5. **DiffBot 动手实验**：以官方 example_2 为主，包含前提、安装/构建参考命令、启动、CLI 检查、发送 TwistStamped、反馈验证、停止；附预期现象，区分浏览器教学与终端操作。提供 RRBot example_1 的后续阅读入口。
6. **生命周期与排错**：unconfigured/inactive/active 的含义，硬件与控制器各自的生命周期；按症状查找服务不可见、接口名称不符、claimed 冲突、消息类型/话题不符、反馈不动等问题。
7. **检查理解**：选择题与即时反馈、错误解释、回到对应课程；学习进度保存在当前浏览器，可重置。

另有术语搜索、官方参考来源列表、已完成课程标记。所有按钮有实际功能，不制作假的运行终端或真实设备状态。

## 流程图准确性

保留原图的架构层级与可选关系，将架构管理关系和动态数据流明确区分。状态接口用于读反馈，命令接口用于写目标；命令接口占用和状态读取不混淆。System 不等于操作系统；Controller 是插件，不默认画成独立 ROS 节点；Transmissions 是可选映射，不表示必需的通信中间件。对原图做教学重排时标注“依据官方架构重绘”。

## 视觉设计（由实现者选择）

- 定位：安静、易读的工程学习工作台；以笔记本阅读为主，兼容手机。
- 配色：纸白 `#f7f8fa`、深海军蓝 `#172b40`、青绿 `#138579`，状态提示使用有限的琥珀色；不使用炫光背景。
- 字体：中文采用本机 Noto Sans CJK SC/思源黑体，英文正文同一字体系统，命令使用本机等宽字体；无需外网字体。
- 8px 间距单位，正文至少 16px，段落行距约 1.8；大块内容用 12–16px 圆角，边框和浅阴影控制层级。
- 动画约 180–240ms，支持减少动态效果；焦点明确，移动端触控区域至少 44px。
- 首屏直接呈现课程、学习目标和交互架构图，不做营销式落地页。

## 验收

- 主要课程和示例完整，中英术语一致，每章有可打开的官方参考。
- 流程图、过滤、解释栏、播放/单步、代码复制、测验、进度和搜索均可操作。
- 核查 Jazzy 的命令消息类型、实际话题、控制器名称及示例文件，不执行真实 ROS 节点和设备操作。
- 浏览器检查桌面和手机布局、键盘操作、无控制台错误、内容不溢出；执行适当的内容与交互检查。
- 完成后交付可访问网址、本地入口和必要的启动说明；如有外部发布阻碍，准确说明。

## 核对的主要官方来源

- https://control.ros.org/jazzy/doc/getting_started/getting_started.html
- https://control.ros.org/jazzy/doc/ros2_control/controller_manager/doc/userdoc.html
- https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/hardware_interface_types_userdoc.html
- https://control.ros.org/jazzy/doc/ros2_control/ros2controlcli/doc/userdoc.html
- https://control.ros.org/jazzy/doc/ros2_control_demos/doc/index.html
- https://control.ros.org/jazzy/doc/ros2_control_demos/example_2/doc/userdoc.html
- https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html

## 留给实现者的常规选择

精确排版、图标、代码组织、SVG 坐标、题目措辞、学习内容的渐进展开方式、发布脚本的具体参数和验证工具，由实现者在上述范围内决定。
