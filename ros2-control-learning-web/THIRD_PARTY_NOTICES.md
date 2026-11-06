# 来源与第三方说明

本网站是独立编写的中文学习资料，并非 ros-controls 官方网站或官方翻译。课程说明、界面与图解按入门学习顺序重新组织；ROS 2、ros2_control 等名称用于说明技术与来源。

## ros2_control_demos

- 项目：<https://github.com/ros-controls/ros2_control_demos>
- 分支：jazzy
- 核对提交：`fbab026e147824971c97996f3789f97c2ee9e9ac`
- 许可：Apache License 2.0，完整文本见 `licenses/ros2_control_demos-Apache-2.0.txt`。
- 原文件版权标记包括：Copyright 2020 ros2_control Development Team，以及各示例源码头部列出的作者。
- 教学片段改写来源：example_2 的 `diffbot_controllers.yaml`、`diffbot.ros2_control.xacro`、`diffbot.launch.py` 和 `diffbot_system.cpp`；example_1 的官方运行命令。片段省略了与当前讲解无关的配置，硬件 read/write 用伪代码重述，均已在界面说明。
- 内容经过简化和中文解释，未复制整个工程；原始文件以固定提交的 GitHub 链接就近提供。

## ros2_control 与 ros2_controllers

- <https://github.com/ros-controls/ros2_control>，jazzy，`f9e24287fc1d6996e5ba1656a9ee24e5f33adef7`。
- <https://github.com/ros-controls/ros2_controllers>，jazzy，`bee185cbb98815116af9cfb00ff595b0b800e91a`。
- 用于核对管理器循环、硬件接口、差速运动学与广播器的行为。数学公式为标准差速运动学，中文讲解为原创。

## 官方文档与原图

- 官方 Jazzy 文档入口：<https://control.ros.org/jazzy/>。
- 架构图依据用户提供的原图与官方 Getting Started 的 Architecture 一节重新绘制为可交互 SVG，并分开显示静态管理关系与教学数据流。按官方组件定义和 example_6 补充原图省略的 Actuator 可选状态接口关系。彩色高亮与数据流模式为本网站的教学重排，不声称是官方原始图片。
- 官方文档正文不整段转载；各章节和组件详情提供具体来源页。
- 本地字体使用读者设备已安装的字体；没有捆绑外部字体、图片或图标库。
