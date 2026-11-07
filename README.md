# ROS 2 离线学习网站与参考工程

本工作区保存中文 ROS 2 教材、原创示例和独立参考资料。2026-11-07 已将双栏阅读器、数学与机器人理论、代码注释、API 对照和本地原文入口整合到正式网站。

## 打开网站

在本目录执行：

```bash
# 仅监听本机；可在站内读取独立保存的参考文件。
python3 ros2-learning-hub/scripts/serve_local.py
```

访问 [本地教材](http://127.0.0.1:8766/)。也可以直接双击 `ros2-learning-hub/dist/index.html`；[单文件连续版](ros2-learning-hub/dist/book.html) 无需 JavaScript。

- 正式教材：60 章，覆盖基础、通信、数学、工程、感知、控制、导航、机械臂与前沿应用。
- 实现讲解包含 12 组不同写法、23 组 API 表、49 组公式、341 道练习与答案，代码保留中文注释。
- 教材收录 39 张实测表，覆盖通信、工程、录放、模型、软件差速、仿真感知、Nav2 地图定位与规划、SLAM 建图和图恢复。
- 图解包含 17 个 SVG 文件及二维和三维交互。连续版包含 36 个上下文图实例，其中有真实相机采样、实际主代价图与路径、SLAM 占据栅格与估计轨迹。
- 离线交付：[网站压缩包](ros2-learning-hub/deliverables/ros2-learning-hub-offline.zip) 和 [SHA256](ros2-learning-hub/deliverables/SHA256SUMS)。
- 核查：[本轮验证](ros2-learning-hub/VALIDATION.md)、[续作说明](CONTINUE.md)、[教材工程说明](ros2-learning-hub/README.md)。

原理、公式、代码、案例、实验和答案在同章展开，参考外链集中到章末。页面采用已确认的左章节树、右正文布局，支持全文搜索、代码标签/并排、收藏、进度导入导出、打印与手机导航。

## 已下载的原始资料

[资料库清单](ros2-learning-hub/references/README.md) 保存 99 个新增来源条目、151 个版本快照，另有原来 11 份参考快照；合计 110 个来源条目、162 份快照。新增条目中 `ros2/rttest` 与 `ros2/realtime_support` 使用相同归档，不作为两门独立课程。子模块 12 份、LFS 资源 7 个均单独核查。

包括官方多版本文档与 examples/demos、Nav2、MoveIt、ros2_control、Gazebo、micro-ROS、PX4 和中英文课程。来源、固定提交与许可见 [manifest](ros2-learning-hub/references/manifest.json)，站内“本地原文与源码”支持仓库/版本/文件筛选和目录阅读。

三个指定教程的 627 个实际文档条目分开登记教学正文与辅助文件，明确标记结构扫描、片段核读、概览或延伸；其中 Robotics_Tutorial 的原始导航有 10 个缺失目标。**资料目录数和主题对应数不表示原始正文已逐段吸收。**

`references/sources/`、`archives/`、`state/` 仅存在本机，被 Git 忽略。换机要额外复制整个 `references/` 以及所需的原有参考目录；教材 ZIP 包含元数据，不包含数 GiB 上游源码。旧 `TRANSFER_*` 仅描述 2026-11-06 的迁移快照。

## 目录与运行范围

| 目录 | 用途 |
| --- | --- |
| `ros2-learning-hub/` | 正式教材、内容源、构建脚本、测试和离线包 |
| `ros2-learning-hub/examples/` | 双语言通信包、标准库数值实验、真实API实验和有界导航客户端 |
| `ros2-learning-hub/foundation-examples/` | 10 个基础教学 ROS 包及 Python 示例 |
| `ros2-learning-hub/references/` | 独立许可的资料快照与下载、校验清单 |
| `ros2-control-learning-web/` | ros2_control 配套工坊 |
| `ros2_tutorial/`、`ROS2_Tuition/`、`Robotics_Tutorial/` | 三个指定教程原始快照 |
| `ros2_control/`、`ros2_controllers/`、`ros2_control_demos/` 及底盘工程 | 原有控制与机器人参考源码 |
| `docs/superpowers/` | 设计、实施与最终验收记录 |

已分轮构建通信、基础和扩展示例。已验证的模型、仿真传感器、SLAM 和 Nav2 台架范围见 [教材验证](ros2-learning-hub/VALIDATION.md)。最新实验、生成物版本和暂停位置见 [续作说明](CONTINUE.md)。

原创教材许可见 `ros2-learning-hub/LICENSE`；第三方仓库与控制工坊保持各自许可，见 `ros2-learning-hub/dist/THIRD_PARTY_NOTICES.md`。
