# ROS 2 离线学习网站与参考工程

这是 2026-11-06 的工作区快照，供换电脑后继续开发。按用户要求，它替换 `learn` 分支原有文件，直接位于仓库根目录；`main` 分支不作改动。**当前网站与教材可阅读；理论推导扩展和新版阅读器整合尚未完成。**

## 在另一台电脑恢复

```bash
git clone --branch learn --single-branch https://github.com/MUHAN11-c/ros2_robot.git
cd ros2_robot
python3 -m http.server 8766 --bind 127.0.0.1 --directory ros2-learning-hub/dist
```

- 双栏图解样稿：[本地样稿](http://127.0.0.1:8766/layout-preview.html#/architecture/figure/architecture)。这是最新确认的设计方向。
- 已完成内容的交互入口：[本地教材](http://127.0.0.1:8766/index.html)。目前仍是上一版正式布局。
- 全部正文连续阅读：[本地连续教材](http://127.0.0.1:8766/book.html)。可直接双击打开，关闭 JavaScript 也可阅读。
- 换机续作细节：[CONTINUE.md](CONTINUE.md)。让新电脑上的 Codex 先读这份文件。
- 快照来源与版本：[TRANSFER_MANIFEST.json](TRANSFER_MANIFEST.json)。源码文件 SHA256：[TRANSFER_FILES.sha256](TRANSFER_FILES.sha256)。

## 目录

| 目录 | 内容 |
| --- | --- |
| `ros2-learning-hub/` | 44 章离线教材、12 组写法对照、内容源、构建脚本、测试、图解、示例和离线包 |
| `ros2-learning-hub/work-in-progress/` | 尚未完成的新版正式阅读器；保留供继续实现，不作为可用入口 |
| `ros2-control-learning-web/` | ros2_control 配套工坊 |
| `docs/superpowers/` | 设计方案、实施计划、进度与研究记录 |
| `ros2_tutorial/`、`ROS2_Tuition/`、`Robotics_Tutorial/` | 用户指定的三个教程源码快照 |
| `ros2_control/`、`ros2_controllers/`、`ros2_control_demos/` | Jazzy 控制框架、控制器与示例 |
| `AgroSenseBot/`、`bunker_ros2/`、`ugv_sdk/`、`linorobot2/`、`linorobot2_hardware/` | 移动机器人、履带底盘及上下位机参考工程 |

参考仓库以真实文件保存，不是需要再次下载的子模块。各自的来源、分支、提交与许可证保持独立；原始 Git 历史没有嵌套复制，版本可按 manifest 追溯。根目录 `README.txt`、`projects.json` 和 `references.repos` 是较早的参考工程下载记录，当前状态以本文件和 `CONTINUE.md` 为准。

上传快照不含登录凭据、`.aws`、`.codex`、`.agents`、`.openai`、嵌套 `.git`、缓存、生成的 ROS 编译安装目录。已保留教材、参考源码、项目资源、截图、验证记录和构建期公式转换器。离线包是教材，不是 Ubuntu/ROS 软件镜像；在新电脑运行 ROS 示例需要另行准备 Ubuntu 24.04 与 ROS 2 Jazzy。

## 使用与许可

原创学习网站的许可证见 `ros2-learning-hub/LICENSE`，第三方说明见 `ros2-learning-hub/dist/THIRD_PARTY_NOTICES.md`。第三方项目继续按各目录原有许可证和版权声明使用；本快照不重新许可这些项目。Robotics_Tutorial 为 CC BY-NC 4.0，zsc 教程须按其原仓库授权情况使用，不应将参考快照视为对其内容的重新授权。
