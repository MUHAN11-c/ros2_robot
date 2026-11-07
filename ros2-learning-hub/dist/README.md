# ROS 2 综合离线教材

双击 index.html 打开左侧章节树与正文阅读器；双击 book.html 连续阅读全书，后者无需 JavaScript。
包含 60 章、12 组实现对照、23 组 API 表、49 个附解释公式、341 道练习与答案及原创图解。

downloads/ 提供 Markdown 全文、章节代码、通信与数值实验工程、10 包基础工作空间、来源索引和验证记录。
代码保留中文注释，标明完整文件、局部片段、终端命令或概念示意。运行依赖和验证边界请先读工程 README。
control-lab/ 是配套 ros2_control 工坊，来源与许可独立。

浏览器若限制本地文件，可在本目录执行 python3 -m http.server 8766 --bind 127.0.0.1，然后打开 http://127.0.0.1:8766 。

学习进度保存在浏览器，可在“我的进度”导入导出 JSON。
便携包只含教材、原创示例与原始资料元数据；不含 ROS 安装器、仿真镜像和第三方数 GiB 源码。
如需原始资料，额外复制工作区的 references、ros2_tutorial、ROS2_Tuition、Robotics_Tutorial 等独立参考目录；
在完整工作区运行 python3 ros2-learning-hub/scripts/serve_local.py 可在站内查看其文件。
参考内容对应表标明核读范围，主题映射不表示原始全文已逐段编入教材。
验证范围见 downloads/validation-evidence.zip 与示例 README；本轮未运行完整 Nav2/Gazebo/MoveIt 仿真或硬件。

来源与许可见 THIRD_PARTY_NOTICES.md 和 LICENSE。
