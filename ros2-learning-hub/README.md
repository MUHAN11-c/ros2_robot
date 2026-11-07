# ROS 2 综合离线学习教材

主线为 Ubuntu 24.04 / ROS 2 Jazzy。60 章将原理、API、不同实现、数值案例、实验和答案放在同一处阅读；章末保留出处、版本与验证范围。

## 使用

从工作区根目录运行：

```bash
# 仅监听 127.0.0.1；同时提供白名单内原始资料的站内阅读。
python3 ros2-learning-hub/scripts/serve_local.py
```

访问 http://127.0.0.1:8766/ 。直接双击 `dist/index.html` 也能离线阅读、搜索和使用图解；`dist/book.html` 是无需 JavaScript 的连续教材。`dist/downloads/ros2-learning-guide.md` 为完整 Markdown。

正式阅读器和紫樱审查版均在左栏展开当前章的子目录。主小节使用「章.节」，正文里的实测表和图解使用「章.节.项」。连续阅读版每章有可折叠的本章目录，保留原有深链接。完整工作区的正式页可从右上角进入同章的编辑模式。

`deliverables/ros2-learning-hub-offline.zip` 可复制到其他电脑；校验见 `deliverables/SHA256SUMS`。便携包不包含独立保存的第三方原文，元数据入口会明确说明。运行 ROS、仿真或厂商项目所需的软件与数据仍按章节准备。

## 将编辑保存到教材文件

打开 `design-review/index.html`，选择“编辑模式”。点击“保存到教材”或按 Ctrl / Cmd + S，首次选中 `ros2-learning-hub` 目录。文件写入完成后，页内会显示“已写入教材文件”。

- `source/local-edits.json` 保存实际章节修订，后续构建会读取它。
- `dist/chapters/<章节ID>.html` 和 `.md` 是保存后的章节文件。审查页和正式阅读器可从磁盘重新打开已存修改；再次运行构建会同步全文 Markdown 和无脚本连续版。
- `backups/local-edits/original/` 保存首次修改前的原文，`backups/local-edits/history/` 保存被替换的版本。恢复原文后，可再次保存到教材文件。

若当前浏览器没有目录写入功能，从工作区根目录运行 `python3 ros2-learning-hub/scripts/serve_local.py --editable`，打开 [本机编辑页](http://127.0.0.1:8766/design-review/)。已有文件页草稿可在“保存位置”导出，并在服务页面的“我的笔记”中导入。普通 `serve_local.py` 启动方式仍为只读。

## 内容与代码

60 章分为七个阶段：基础环境、数学与机器人基础、通信开发、工程运行、模型仿真感知、控制导航操作、嵌入式与前沿生态。原有 44 章继续保留，新增数学 8 章、机器人理论与项目 8 章。

- 12 组对照：C++/Python、回调、服务、Action、参数、三种 launch、执行器、组件、构建、QoS、速度消息和模型描述。
- 23 组 API 表解释输入输出、单位、对象寿命、执行顺序与错误路径，并直接嵌入对应章节。
- 49 组公式附推导、符号与单位、假设、例子及局限，使用离线原生 MathML。
- 341 道练习与答案，17 个 SVG 文件和 2 种交互模型，连续版有 36 个上下文图实例。
- 39 张实测表覆盖通信、调度、参数、生命周期、测试、部署、录放、模型、软件底盘、仿真感知、导航规划、SLAM 建图与图定位。相机、Nav2 和 SLAM 的实测图均绑定原始采样。
- 原有代码的 331 个位置及 64 个原创工程文件补充中文注释。章节完整文件共 164 份导出条目，其中部分是同一源码在不同章节的教学副本。

完整文件、局部片段、终端命令、概念示意明确区分。完整文件仍可能需要所在 ROS 包、依赖、服务或仿真；不表示单文件就构成完整机器人系统。

`examples/` 包含通信2包、5个基础离线模型、16个数学/应用实验、真实API实验、有界导航，以及动作/组件/生命周期/测试/模型各1个独立包。`testing_policy/`保留已知缺口基线和修订策略，`deployment_labs/`做显式范围的只读审计；`bag_labs/`含真实录放和无DDS存储探针。基础10包在`foundation-examples/`。首次通信构建限定`--base-paths src`；附加包按各自README准备依赖，Docker与复制产物未运行。下载包保留源码、中文注释、许可证与验证说明。

## 原始资料与覆盖范围

`source/reference-coverage.json` 记录三个指定教程的 627 个真实文档条目，其中教学正文/附录 527、辅助文件 100；标注深度、核读方式与缺失目标，不能用标题映射推断逐段覆盖。`source/topic-depth.json` 记录本站实际章节范围。

控制、差速、硬件接入、模型、定位和导航项目六章共用一套软件差速实验。对照官方 Example 2、GenericSystem、diff_drive_controller、robot_localization 和实际底盘参考工程，分别检验轮资源、速度与 TF。完整复现见 [软件台架说明](examples/drive_labs/README.md)。

仿真、感知、TF、QoS、录放、SLAM 和 Nav2 七章共用一个本地 Harmonic 传感器实验，包含暂停与恢复、RGB 与内参对齐、实际激光和点云、以及同话题 QoS 对照。完整工作区的两套阅读入口均可从章末打开本轮定点原文。复现条件见 [传感器实验说明](examples/gazebo_labs/README.md)。

地图、定位和规划台架将 Harmonic 扫描接入真实 MapServer、AMCL 和 NavFn。九章融入 39 份固定文件的相关实现，含地图失败回执、初始位姿检查、代价图与路径对照、SLAM 位姿图产物和 Linorobot2 配置。两次运行及完整配置见 [Nav2 固定台架](examples/nav2_labs/README.md) 与 [验证范围](VALIDATION.md)。

SLAM 台架沿离散位姿采集真实 Harmonic 激光，回放时提供独立时钟与带已知偏差的里程计。九章融入 35 份固定参考文件，含栅格重载、位姿图恢复与继续建图，以及图定位缓冲造成的可复原地图变化。复现与边界见 [SLAM 台架](examples/slam_labs/README.md)。

`references/` 保存下载来源、版本、提交、许可证、文档和 ROS 包索引。合计 110 个来源条目、162 个快照；含一组相同归档的来源别名。源正文继续独立保存，不复制为本站统一许可内容。Git 和便携教材包均不包含 `references/sources/archives/state` 本体。

## 重建与检查

从本目录执行，前端无需 npm 安装。公式构建用到的 `latex2mathml==3.81.1` 及许可已保存在 `scripts/vendor/`。

```bash
python3 scripts/build_theory_figures.py
# 只有重新运行了第2轮实验并审核报告后，才重新生成绑定SHA的素材。
# python3 scripts/build_iteration2_material.py
# 第3轮还要求当前报告得到对应SHA的独立审查通过。
# python3 scripts/build_iteration3_material.py
# 第4轮四份报告及对应独立审查通过后，才刷新第4覆层。
# python3 scripts/build_iteration4_material.py
# 第5轮录放与CLI边界报告及独立审查通过后，才刷新对应素材。
# python3 scripts/build_iteration5_material.py
# 第6轮模型/TF与边界报告经当前SHA独立审查后，才刷新对应素材。
# python3 scripts/build_iteration6_material.py
# 软件底盘重新运行后，核对报告及本地上游文件指纹再刷新相应覆层。
# python3 scripts/build_drive_material.py
# 仿真传感器报告和图像更新后，经核对再生成相应覆层及实测图。
# python3 scripts/build_sensor_material.py
# Nav2 本机和解压源码两份报告、原始主图与定点源码核对后再生成。
# python3 scripts/build_nav2_material.py
# SLAM 两份运行报告、原始轨迹、地图和定点源码核对后再生成。
# python3 scripts/build_slam_material.py
python3 scripts/build_content.py --require-full
python3 scripts/package_offline.py
python3 tests/check_content.py
python3 tests/test_math_export.py
python3 tests/test_offline_labs.py
python3 tests/test_watchdog_model.py
python3 tests/test_markdown_tables.py
python3 examples/theory_labs/math_labs.py
python3 examples/theory_labs/applied_labs.py
node tests/logic.test.cjs
node tests/textbook.test.cjs
node tests/preview-geometry.test.cjs
node tests/markdown-tables.test.cjs
```

浏览器检查需要本机 Playwright 与 Chromium，可设置 `PLAYWRIGHT_MODULE` 和 `PLAYWRIGHT_BROWSERS_PATH`。启动本地阅读服务后运行 `node tests/browser-checks.cjs`；文件协议断网检查用 `node tests/reader-checks.cjs`；全图解检查用 `node tests/design-preview-checks.cjs`（历史文件名，现测正式入口）。ROS 构建/集成步骤另见验证说明。

正文和布局参考 [MDN 的学习模块](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core)、[PyTorch 的分步教程](https://docs.pytorch.org/tutorials/beginner/basics/intro.html) 与 [GitBook 官方页面结构示例](https://github.com/GitbookIO/demo-docs-gitbook/blob/main/creating-content/content-structure/page.md)。CSS、图解与教材均独立编写，不复制其页面资产。

原创教材、界面与示例采用 Apache-2.0。上游资料、控制工坊和构建工具许可证保持独立，见 `dist/THIRD_PARTY_NOTICES.md`。当前工作区、便携包和审查报告对应的版本见 [续作说明](../CONTINUE.md)。

第10轮实测 Harmonic 多位姿采集、SLAM Toolbox 建图、两类地图恢复与图定位。第8轮传感器桥接、第7轮软件差速与局部 EKF、第6轮模型与 TF 证据按原报告单列。各实验范围见对应 README 与验证说明。原始资料逐段融合仍在进行，完整导航控制、实物与 GUI 依各章单独验收。
