# ROS 2 综合离线学习教材

以 Ubuntu 24.04 / ROS 2 Jazzy 为主线，将官方概念、可执行教程、不同写法对照与生态项目组织成一套中文教材。正常学习不需要打开参考网站。

## 打开教材

- 双击 `dist/index.html`：章节导航、全文搜索、收藏、进度、代码复制与比较。
- 双击 `dist/book.html`：单文件连续阅读版，无需 JavaScript；含全部章节、练习答案、代码与工程文件。
- `dist/downloads/ros2-learning-guide.md`：可编辑、可检索的 Markdown 版。
- `deliverables/ros2-learning-hub-offline.zip`：可复制到另一台电脑的完整网站压缩包。

浏览器若限制本地文件功能，可在本目录执行：

```bash
python3 -m http.server 8766 --bind 127.0.0.1 --directory dist
```

然后打开 http://127.0.0.1:8766 。阅读内容、搜索与图解不依赖网络或 CDN。离线阅读包不包含 Ubuntu 软件包、ROS 2 安装器、仿真器、模型权重或训练数据；需要运行这些生态实验时，应先按对应章节准备软件环境。

## 内容组织

44 章分为基础环境、通信开发、工程运行机制、模型感知、控制导航操作、嵌入式与前沿生态六个阶段。每章提供原理、代码说明、具体实验、预期现象、排错和练习答案。12 组对照覆盖 C++ / Python、回调、服务、Action、参数、三种 launch、执行器、组件、构建、QoS、速度消息与模型描述。

两套已克隆教程的 169 个原页面逐项建立主题映射，可直接进入本站对应章节。来源保留在附录，用于追溯和后续核查；本站是原创综合编写，不是原教程的逐页翻译或镜像，也不声称收尽互联网全部 ROS 2 资料。

## 示例与验证

`examples/` 是可构建的 C++ / Python 通信工作空间，包含发布订阅、服务和 Python / XML / YAML launch；`examples/offline_labs/` 包含四个 Python 标准库实验。构建步骤见 `examples/README.md`，实测范围见 `examples/VALIDATION.md`。各章其他代码文件可从 `dist/downloads/chapter-code.zip` 提取，清单记录对应章节和原文件标签。

代码标记分为完整文件、局部片段、终端命令与概念示意。完整文件需要按章节说明放到对应包中；并非每个文件单独运行就构成完整机器人系统。

## 重建与检查

内容源在 `source/`，网站源在 `dist/`；本项目无前端依赖安装步骤。Python 脚本只使用标准库。

```bash
python3 scripts/build_frontier_source.py
python3 scripts/build_content.py
python3 scripts/package_offline.py
node --test tests/logic.test.cjs tests/textbook.test.cjs
python3 tests/check_content.py
```

浏览器检查使用已安装的 Playwright，可用 `PLAYWRIGHT_MODULE` 指向其 Node 包目录，再运行 `node tests/browser-checks.cjs`。需先启动上述本地服务。ROS 2 集成检查见验证记录；不要将文档内容检查等同于全部生态或实机验证。

正文、界面与原创示例采用 Apache-2.0。第三方来源和已有控制工坊许可见 `dist/THIRD_PARTY_NOTICES.md`。
