# ROS 2 学习图谱

主线：ROS 2 Jazzy / Ubuntu 24.04。资料核对：2026-11-06。

本网站的完整通信教学工程单独记录构建与测试结果；其余生态命令为版本资料核对，未逐项运行。没有连接或控制真实机器人。

## 1. ROS 2 的分层与通信选型

节点是计算图中的功能实体，进程是操作系统的隔离单位；一个进程可以包含多个节点。包则负责代码、依赖与安装组织，三者不能混为一谈。

### 学习目标

- 把应用、客户端库、RMW、中间件与工具放到正确的位置

- 根据数据流选择 Topic、Service 或 Action

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

节点是计算图中的功能实体，进程是操作系统的隔离单位；一个进程可以包含多个节点。包则负责代码、依赖与安装组织，三者不能混为一谈。

话题传输持续数据；服务表达较短的请求与回应；动作适合需要反馈、结果和取消的长期任务。动作并不是一个普通话题。

rclcpp 与 rclpy 共用接口定义和通信图。语言不同不妨碍通信，但类型、名称、QoS 与发现环境必须匹配。

### 1. 先把机器人问题拆成可验证的数据流

假设你要让一台巡检车看见障碍物并停下。摄像头驱动负责取得图像，感知程序负责判断前方是否有人，任务程序决定继续或停车，底盘程序把速度要求转换成电机动作。若把它们写成一个不断增长的循环，修改摄像头可能影响控制周期，回放数据也需要模拟所有硬件。ROS 2 提供的价值，是让这些功能通过明确接口协作，从而可以独立替换和验证。

ROS 2 不是替代 Linux 的操作系统，也不会自动给机器人提供导航能力。Linux 仍负责进程、驱动、文件和网络；ROS 2 提供通信机制、客户端库、构建组织和调试工具；Nav2、MoveIt、ros2_control 等项目再在这些机制上解决具体机器人问题。学习时应先认识这些层之间的连接，避免一遇到机器人问题就寻找一个所谓的万能 ROS 节点。

设计的起点是接口契约：谁产生什么数据，单位和坐标系是什么，允许多久没有新数据，失败时由谁处理。机器人能启动只是第一层结果；输入停止、通信延迟和节点退出时能否保持可解释的行为，才说明接口边界划分得合理。

### 2. 包、可执行程序、进程和节点是四个概念

包是发布与依赖管理的单位。一个包可以包含源码、模型、参数、启动文件，也可以只有消息定义。可执行程序是安装后能够启动的程序入口；同一个包可以安装多个入口。进程是操作系统创建的运行实例，具有自己的地址空间；同一可执行程序启动两次，会形成两个进程。节点则是 ROS 图中的逻辑实体，拥有名称、接口和参数。

最初的教程通常让一个程序创建一个节点，所以四个名字容易被混为一谈。实际上，一个包可生成发布者和订阅者两个可执行程序；一个组件容器进程可容纳多个节点；同一类节点也可创建多个实例，并分别放在不同命名空间下。由此可见，看到两个 ROS 节点不能推断一定有两个操作系统进程。

执行 ros2 run demo_nodes_cpp talker 时，前一个参数指定包，后一个参数指定安装入口。运行后再用 ros2 node list 看节点名称。程序入口名和节点名可以一样，也可以不同；重命名节点不会修改磁盘上的程序文件，更不会改动包名。

#### 认识三个查询层级

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
ros2 pkg prefix demo_nodes_cpp
ros2 pkg executables demo_nodes_cpp
ros2 node list

```

前两条检查已安装的软件包，最后一条查询当前运行的计算图；没有节点运行时，列表为空并不代表没有安装软件。

### 3. 从应用一路到网络，中间发生了什么

应用使用 rclcpp 或 rclpy 创建节点及发布者。客户端库把语言层对象转换成 ROS 核心层可操作的实体，再经过 RMW 适配层交给具体中间件。RMW 的作用是隔离中间件差异，使应用通常不需要直接操作 DDS 的参与者和发现协议。Jazzy 的常见实现有基于 Fast DDS 或 Cyclone DDS 的 RMW，选择时要安装对应实现并保持配置一致。

消息定义负责双方共享的数据结构。发布端将内存中的消息交给通信层，接收端再恢复成自己的语言对象。C++ 的结构类型和 Python 的消息类来自同一接口定义，因此它们可以通信；双方源程序采用不同编程语言并不要求额外桥接。反过来，名字碰巧相同却结构不同的接口，不能视为兼容。

发现机制让端点知道彼此存在，传输机制负责实际数据到达，执行器负责何时运行你的回调。这是三个不同环节。节点列表里看得到对方，只证明图信息已经被发现；消息类型、QoS、网络路径和回调调度仍可能阻止你的程序获得可用数据。

#### 通信分层示意

代码类型：concept

```text

应用逻辑：巡检、规划、控制
        ↓
rclcpp / rclpy：节点、发布订阅、服务、动作
        ↓
rcl / RMW：核心机制和中间件适配
        ↓
具体中间件：发现、序列化、传输、QoS
        ↓
操作系统、网络接口、计算与存储资源

```

这是理解职责的示意图，不表示每条消息都必须跨机器，也不是运行命令。

### 4. Topic、Service、Action 怎样选

话题适合连续或事件式数据流，例如图像、里程计和速度要求。发布者不需要知道订阅者数量；记录器、可视化和算法都能消费同一数据。发布动作不会返回订阅者业务处理成功的结果，因此不能仅凭 publish 调用成功，就认为电机已经达到目标速度。需要确认真实状态时，应由状态反馈接口表达。

服务包含一个请求和一个响应，适合短时查询、重置计数器或触发一次配置操作。它使调用者能把响应与请求对应起来，却不自带连续进度和完整任务取消语义。如果服务响应迟迟不到，客户端必须设计等待上限；客户端超时也不表示服务端一定没有执行，涉及状态修改时应考虑重复调用是否安全。

动作将长任务表达成目标、反馈和最终结果，并具有目标接受与取消过程。导航到某个位置适合动作，因为用户需要知道走到哪里、能否取消以及是否到达。动作接口比单一话题复杂，是因为它把任务协议标准化；不应为图像流使用动作，也不应把所有长期任务都塞进一个阻塞服务。

- 连续感知：Topic；短查询或配置操作：Service；需要进度与取消的长期任务：Action。

- 参数用于配置节点的行为，不适合替代高速传感器或控制数据通道。

### 5. 名字、命名空间和类型共同定义接口

把相机接口命名成 image，表示它是相对名称，最终路径会受到节点命名空间影响。处于 /robot1 的节点使用相对话题 telemetry，得到的是 /robot1/telemetry；以斜杠开头的 /telemetry 是绝对名称，不随命名空间移动。这种规则允许同一套软件分别部署到多台机器人，而不需要在源码里写死机器人编号。

重映射是在启动时改变名称解析的配置方式。一个节点在源码里发布 chatter，启动时可以把它重映射成 telemetry。重映射不改变消息类型，也不会转换数值单位。若两个系统都叫 cmd_vel，却一个使用 Twist、另一个使用 TwistStamped，仅修改名称仍无法通信，必须明确适配接口。

接口契约还应写出类型之外的含义。float64 velocity 没有告诉读者它是米每秒还是弧度每秒；Header 中有时间戳和 frame_id，也仍然需要约定采样时间和坐标关系。把这些约定写进接口说明，能避免程序编译通过但机器人运动含义相反的错误。

### 6. 第一次跨语言实验：从输出推断系统结构

先选择系统自带的演示节点，这样可以将通信问题与自己写代码的问题分开。打开三个终端，每个终端独立加载 Jazzy 环境。终端 A 启动 C++ talker，终端 B 启动 Python listener；终端 C 不承担业务逻辑，只负责观察。这里没有摄像头、机器人模型或电机依赖，实验目的仅是证明一个图中的跨语言通信链能够建立。

发布者输出周期性日志，订阅者输出接收到的文本。两边计数可能从不同位置开始，因为订阅者启动前的 volatile 消息不必补发给它。停止订阅者并不会让发布者自动停止；再次启动订阅者后，应看到新的消息。这个现象说明话题耦合较弱，同时提醒你：业务若要求消费者确认，必须另行设计确认机制。

观察完把两端语言交换：使用 demo_nodes_py talker 和 demo_nodes_cpp listener。若行为仍相同，说明接口语义不依赖某一种语言。最后一次只改变一个条件，例如重映射话题，让实验能清楚指出哪项配置导致收不到消息。

#### 终端 A / B / C 各自运行对应命令

代码类型：commands

```bash

# 每个终端先执行
source /opt/ros/jazzy/setup.bash
# 终端 A
ros2 run demo_nodes_cpp talker
# 终端 B
ros2 run demo_nodes_py listener
# 终端 C
ros2 node info /talker
ros2 topic info /chatter --verbose
ros2 topic echo /chatter

```

命令按终端分组执行，持续运行的 ros2 run 不会返回到下一行；请不要把所有组顺序粘贴到同一个终端。

### 7. 将演示映射回真实机器人

在移动机器人中，底盘驱动报告轮速，状态估计输出里程计，规划模块产生路线，控制模块产生速度要求。可以把每条接口画为箭头，但还要标明箭头负责的是测量值、估计值还是命令值。命令与反馈具有不同用途，把它们混在一个未经说明的话题里，会使故障定位和录包回放变得困难。

进程拆分需要结合故障与性能，而非越多越好。将相机和任务逻辑分开有助于隔离故障；把某些高带宽处理节点组合在一起可能减少开销，但需要考虑共享进程崩溃的影响。先确定接口，再测量部署布局，能避免过早让进程结构反过来决定业务结构。

本章的验收不是背诵缩写，而是拿到一个启动命令后，说出它属于哪个包、创建几个节点、通过什么接口协作，并指出一个节点退出后其他部分应怎样表现。只有这些关系清楚，后续的 QoS、执行器、组件、生命周期和导航框架才有具体落点。

### 为巡检车建立第一版接口说明

同一台机器人要持续接收激光、接受巡检目标，并允许操作者随时取消任务。

1. 将激光观测定义为 sensor_msgs/msg/LaserScan 话题，并记录采样坐标系与时间戳含义。

2. 把巡检目标定义为 Action，反馈当前航点，结果说明成功或失败原因。

3. 将最大速度作为可校验参数；实际速度要求使用控制话题，测量速度由状态话题反馈。

4. 启动最小演示验证跨语言通信，然后分别替换发布者和消费者。

验收：接口表同时描述数据、时间、单位、任务生命周期和故障行为，后续可以逐模块实现。

### 深入练习 1

一个包安装三个程序，其中一个程序创建两个节点。运行这个程序一次，会有几个包、进程和节点？

参考答案：安装组织上仍涉及一个包；本次启动创建一个进程，程序内部创建两个 ROS 节点。其他未运行入口不因此生成进程。

### 深入练习 2

把 chatter 重映射成 telemetry，能否让 String 发布者与 Float64 订阅者通信？

参考答案：不能。重映射只改变名称解析，不改变接口类型和序列化结构；应修改两端接口或实现明确的转换节点。

### 深入练习 3

服务客户端超时后立即重试“扣减库存”，可能发生什么？

参考答案：第一次请求可能已经被执行，只是响应迟到；重试可能重复修改状态。应设计请求 ID、幂等处理或可查询的任务状态，不能把网络超时等同于未执行。

### 基础验证流程

画出传感器 → 定位 → 规划 → 控制的数据流。

对每条边标注消息类型、频率、是否需要响应与取消。

先启动 demo talker/listener，再把图中的进程和节点分别标出来。

#### 终端 A：C++ 发布者

```bash

ros2 run demo_nodes_cpp talker

```

#### 终端 B：Python 订阅者

```bash

ros2 run demo_nodes_py listener

```

#### 终端 C：观察计算图

```bash

ros2 node list
ros2 topic list -t

```

### 预期结果

- C++ 发布的字符串能被 Python 节点收到。

- 能解释 package、executable、process 和 node 各负责什么。

### 常见问题

- 把“一个节点”默认当作“一个进程”。

- 用服务实现持续遥控速度流，或者用普通话题自行拼接目标取消协议。

### 练习

为巡检机器人设计相机数据、修改曝光、导航到目标点三条接口，并说明选择理由。

#### 参考答案

相机图像使用 sensor_msgs/msg/Image 话题，因为它持续产生数据且可以有多个消费者；修改曝光可用参数或短服务，并校验范围；导航目标使用 Action，因为执行较久，需要反馈、取消和最终结果。实际接口名、频率与 frame_id 还要写入系统接口表。

### 依据

- [ROS 2 Jazzy 概念目录](https://docs.ros.org/en/jazzy/Concepts.html)

- [C++ / Python 客户端库教程](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries.html)

- [Ubuntu 24.04 上安装 Jazzy](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)

## 2. 环境安装与第一条跨语言通信

本路线默认 Ubuntu 24.04 和 Jazzy。Jazzy 是长期支持版本，但截至核对日期并非最新发行版。

### 学习目标

- 建立可复现的 Jazzy 学习环境

- 确认 C++ 与 Python 示例能互通

### 先修

Ubuntu 24.04；安装操作需要本机相应权限；本网站展示命令，不自动修改系统。

### 概念

本路线默认 Ubuntu 24.04 和 Jazzy。Jazzy 是长期支持版本，但截至核对日期并非最新发行版。

desktop 包含常用图形工具与示例；ros-base 适合无图形部署。安装前应按官方页面配置 ROS apt 软件源。

### 1. 安装前先固定目标平台和联网边界

本教材选择 ROS 2 Jazzy 与 Ubuntu 24.04 Noble 作为统一环境。选择一个明确版本，是为了让软件包名、Python 解释器、依赖库和示例分支能相互对应。Jazzy 支持周期较长，但截至本次核对日期并非最新发行版；学习时不必不断追逐更新版本，应先把一个版本上的完整工作链建立起来。

首先读取操作系统和架构，不要只根据桌面外观判断版本。Ubuntu 22.04 的 Humble 软件包不能通过改几个包名就当作 Jazzy 使用；若电脑不符合目标环境，可使用单独的虚拟机或容器，但图形显示、USB 和网络发现还需要额外配置。本章直接描述原生 Ubuntu 24.04 的 deb 安装路线。

教材正文、命令解释和代码可离线阅读；apt 安装、GitHub 发布查询和依赖下载通常仍需联网。真正的离线部署需要提前准备对应架构的软件包及其依赖、仓库索引或完整镜像。只保存网页或几个 deb 文件，不代表已经备齐可离线安装的一整套系统。

#### 只读检查平台

代码类型：commands

```bash

cat /etc/os-release
uname -m
locale

```

预期系统信息包含 Ubuntu 24.04 / noble；架构与所选二进制包应匹配，locale 输出应包含可用 UTF-8 环境。

### 2. 配置 UTF-8 环境并理解 locale 的作用

locale 影响程序处理字符、数字格式和终端输出的方式。精简镜像可能只有 POSIX 环境，而教程中的 Python 工具、包元数据和文件路径可能包含非 ASCII 字符。ROS 并不要求桌面界面必须使用英语，但学习环境应有完整的 UTF-8 编码支持。已正常使用中文 UTF-8 环境的机器通常不需要为了教程强制切换所有桌面语言。

下方步骤生成一个明确可用的 en_US.UTF-8 locale，并在当前 shell 中设置 LANG。系统默认设置与当前 shell 环境不是同一件事：update-locale 写入系统配置，export 则立即影响当前终端及其子进程。修改完成后重新运行 locale 检查，不要因为命令没有报错就假定所有环境已经更新。

如果 apt update 出现网络或软件源错误，应先修复仓库访问，再继续安装。系统安装过程中应阅读 apt 给出的变更清单，尤其是已有复杂开发环境的机器。这里的命令是供你在自己的系统上执行的安装步骤，网站阅读本身不会执行这些命令。

#### 需要时创建 UTF-8 locale

代码类型：commands

```bash

sudo apt update
sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
locale

```

若当前环境已完整支持 UTF-8，可保留原有语言设置；本组展示官方安装路线使用的一种可验证配置。

### 3. 启用 Universe，并由 ros2-apt-source 管理 ROS 软件源

Ubuntu 自带软件源并不包含所有 ROS 发布包，因此需要加入 ROS 软件仓库。当前官方 Jazzy 安装流程使用 ros2-apt-source 软件包提供仓库地址和签名密钥；这样仓库配置的后续更新也能通过软件包管理完成。不要同时叠加多份旧教程里的手工源配置，否则 apt 可能出现重复条目或签名设置冲突。

先启用 Universe 并安装下载工具。随后从 ros-apt-source 的 GitHub 最新发布信息读取标签，把它放入下载文件名。这里“最新”指软件源配置包的发布版本，不是把 ROS 发行版切换到 Rolling 或其他版本。Ubuntu 代号必须仍为 noble；下载路径里使用该代号是为了匹配本机的软件源配置。

下面先查询并打印版本，让你能在继续前确认得到的是非空发布标签。若 GitHub API 请求失败、被限流或返回错误对象，应停止并解决访问问题，不要把空变量拼入下载地址。curl 的失败返回应被注意；只有文件完整下载后，才交给 dpkg 安装。

#### 启用 Ubuntu 仓库与工具

代码类型：commands

```bash

sudo apt install software-properties-common curl python3
sudo add-apt-repository universe
sudo apt update

```

Universe 提供 ROS 开发链需要的一部分 Ubuntu 依赖。

#### 查询 ROS 软件源配置包版本

代码类型：commands

```bash

ROS_APT_SOURCE_VERSION=$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])')
printf '%s
' "$ROS_APT_SOURCE_VERSION"

```

应输出实际发布标签。此处使用 Python 解析 JSON，与官方流程读取 tag_name 的目的相同；请求失败时不要继续下一组。

#### 下载并安装源配置包

代码类型：commands

```bash

. /etc/os-release
ROS_UBUNTU_CODENAME=${UBUNTU_CODENAME:-$VERSION_CODENAME}
curl -fL -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${ROS_UBUNTU_CODENAME}_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update

```

以上两组命令在同一终端连续进行，以保留变量。安装前应确认代号为 noble；配置包负责添加 ROS 仓库及密钥。

### 4. 选择 desktop 或 ros-base，而不是混装发行版

desktop 面向学习和桌面开发，包含 ROS 基础、RViz 及常用示例，是本教材的默认选择。ros-base 更适合无图形的板载电脑，只提供较精简的运行与通信基础；采用它以后，需要按章节补装图形工具和示例。两者是同一发行版里的不同软件包集合，不是两个不兼容的 ROS 系统。

开发还需要编译、构建和依赖工具，ros-dev-tools 用于安装常用开发链。安装前更新系统软件包索引并检查待升级项；需要升级时按本机维护要求执行。Ubuntu 的 noble-updates 和 noble-backports 配置不完整可能导致开发依赖无法满足，此时应检查 /etc/apt/sources.list.d/ubuntu.sources 的 Suites 设置，而不是强制忽略依赖。

apt 软件包名通常采用短横线，例如 ros-jazzy-demo-nodes-cpp；ROS 包名采用下划线，例如 demo_nodes_cpp。安装成功后运行时仍使用 ROS 包名。不要把这两种命名方式机械替换到所有命令中；apt 查询的是系统包，ros2 pkg 查询的是 ROS 安装索引。

#### 默认桌面学习环境

代码类型：commands

```bash

sudo apt update
sudo apt install ros-jazzy-desktop ros-dev-tools
apt policy ros-jazzy-desktop

```

本组是 desktop 路线。若明确选择无图形路线，可将第一项替换为 ros-jazzy-ros-base，再按需安装其他包。

### 5. source 环境到底改变了什么

安装完成后，程序仍需要知道到哪里找 ROS 命令、库和包。source /opt/ros/jazzy/setup.bash 会在当前 shell 中设置相应环境变量，使随后启动的程序继承这些路径。source 不创建后台 ROS 主服务器，也不启动任何机器人节点；它只是准备进程的运行环境。

每个新终端都有自己的环境，A 终端执行 source 不会自动改变 B 终端。确认使用 Bash 后才使用 setup.bash；Zsh 应使用对应脚本。刚开始学习时建议显式加载环境，并用 printenv ROS_DISTRO 验证，等理解后再决定是否放进 shell 启动文件，避免长期自动混入多个发行版或工作空间。

后面自己构建的 install/setup.bash 是 overlay，需要在基础安装之后加载。若装过 Humble、源码版 ROS 或多个工作空间，路径优先级可能影响实际加载的包。遇到奇怪行为时，先用一个干净终端仅加载 Jazzy，再逐层加入自建工作空间，比删除系统安装更容易定位问题。

#### 当前终端加载并确认

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
printenv ROS_DISTRO
command -v ros2
ros2 pkg prefix demo_nodes_cpp

```

ROS_DISTRO 应为 jazzy，ros2 命令与演示包路径应落在预期安装中；具体路径可能因安装方式不同而变化。

### 6. 三步验收：可发现、可收发、可诊断

安装验收应使用最小闭环。终端 A 运行 C++ 发布者，终端 B 运行 Python 订阅者，终端 C 查看节点和话题。这样既覆盖两种客户端库，也检查接口定义和通信环境。只执行 ros2 --help 能证明命令行入口可运行，不能证明消息链已经通畅。

预期发布者持续显示发布日志，订阅者显示收到的字符串；计数通常递增。若发布者工作而订阅者没有输出，先比较两边的 ROS_DOMAIN_ID、RMW_IMPLEMENTATION 以及是否加载同一发行版，再检查话题信息。若节点名称出现但没有数据，继续查看类型和 QoS，避免反复重新安装。

ros2 doctor --report 会给出平台、网络和软件相关信息，适合作为实验记录。报告中的警告需要结合上下文判断，不应把所有 warning 一概解释成无法使用。完成验收后记录操作系统、架构、发行版、安装方式和验证日期；以后排查另一台机器的差异时，这份记录比一句“我装过 ROS”有用。

#### 两个终端分别运行

代码类型：commands

```bash

# 终端 A，先 source Jazzy
ros2 run demo_nodes_cpp talker
# 终端 B，先 source Jazzy
ros2 run demo_nodes_py listener
# 终端 C，先 source Jazzy
ros2 topic info /chatter --verbose
ros2 doctor --report

```

各组位于独立终端。终止示例可按 Ctrl+C；示例不会控制实际底盘。

### 7. 常见安装错误怎样逐步定位

找不到 ros2 命令时，先确认安装是否成功，再确认当前 shell 是否加载正确脚本。找到命令但找不到某个 ROS 包时，用 apt policy 检查系统包、用 ros2 pkg prefix 检查 ROS 索引；如果采用 ros-base，缺少 RViz 或演示包可能只是安装集合不同，不是环境整体损坏。

apt 提示找不到软件包时，检查更新索引是否成功、Ubuntu 代号是否正确，以及 ROS 源配置包是否安装。签名或 TLS 错误应针对软件源、系统时间或网络访问处理，不应通过随意关闭签名验证来让命令表面成功。下载脚本依赖互联网，离线读者应先准备完整依赖再安装。

Python import rclpy 失败时，检查当前 python3 是否属于系统环境，以及是否被 Conda 或另一个虚拟环境替代。Jazzy 的 deb 包针对目标 Ubuntu 的 Python ABI 构建，任意替换解释器可能破坏二进制扩展加载。先在系统 Python 与干净 shell 中复现，再决定如何隔离额外 Python 依赖。

### 为一台新 Ubuntu 工作站建立安装记录

工作站运行 Ubuntu 24.04，需要跟随本教材开发 C++ 和 Python 节点。

1. 读取系统版本、架构和 locale，记录输出。

2. 启用 Universe，安装当前 ros2-apt-source 配置包，确认 apt update 成功。

3. 安装 desktop 和开发工具，在两个新终端加载 Jazzy。

4. 运行 C++ talker 与 Python listener，并保存 doctor 报告。

验收：验收证据包含真实环境输出和消息收发结果；网站中的示例输出不能替代本机验证。

### 深入练习 1

教材可以离线打开，为什么 apt install 仍可能失败？

参考答案：离线阅读只表示网页、正文和示例文件已在本地。apt 仍需要软件包、依赖和仓库索引；真正离线安装必须预先准备完整的软件供应链或镜像。

### 深入练习 2

A 终端能执行 ros2，B 终端提示 command not found，应首先检查什么？

参考答案：检查 B 终端是否加载了对应 shell 的 Jazzy setup 脚本，以及它的 PATH。每个终端环境独立，不能因为 A 已 source 就推断 B 已配置。

### 深入练习 3

ros2-apt-source 的“最新版本”是否表示安装了最新 ROS 发行版？

参考答案：不是。它管理仓库地址和密钥；安装 ros-jazzy-desktop 仍选择 Jazzy。软件源配置包的版本与 ROS 发行版名称属于不同层级。

### 基础验证流程

先检查系统发行版、CPU 架构和 UTF-8 locale。

按官方安装页完成软件源配置，然后选择 desktop。

在两个独立终端分别加载环境并运行示例；把验证通过的环境记录下来。

#### 检查环境

```bash

cat /etc/os-release
uname -m
locale

```

#### 已完成官方 apt 软件源配置后

```bash

sudo apt update
sudo apt install ros-jazzy-desktop ros-dev-tools
source /opt/ros/jazzy/setup.bash
printenv ROS_DISTRO

```

#### 终端 A / B 分别执行

```bash

# 终端 A
ros2 run demo_nodes_cpp talker
# 终端 B
ros2 run demo_nodes_py listener

```

### 预期结果

- ROS_DISTRO 输出 jazzy。

- 两个示例持续收发，说明基础安装和跨语言接口可用。

### 常见问题

- 在 Ubuntu 22.04 上直接照抄 Jazzy deb 安装命令。

- 把第三方教程里的 ros-jazzy-desktop-full 当作本路线的官方推荐命令。

- 用未 source 的新终端诊断“找不到 ros2”。

### 练习

写一份五行环境记录：操作系统、架构、ROS_DISTRO、RMW_IMPLEMENTATION 和安装方式。

#### 参考答案

示例记录：Ubuntu 24.04；amd64（以 uname -m 实际输出为准）；ROS_DISTRO=jazzy；RMW_IMPLEMENTATION 未设置时使用该安装的默认实现，需从诊断输出确认；通过官方 deb 软件源安装 ros-jazzy-desktop。不要把示例环境冒充你的机器实测结果。

### 依据

- [Ubuntu 24.04 上安装 Jazzy](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)

- [ROS 2 发行版与维护周期](https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases.rst)

## 3. 工作空间、包、ament 与 colcon

colcon 编排多个包；ament_cmake 描述 CMake 包构建，ament_python 使用 setuptools 安装 Python 包。rosdep 按 package.xml 安装外部依赖。

### 学习目标

- 理解依赖、构建与安装三个阶段

- 能定位 overlay 中实际运行的软件包

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

colcon 编排多个包；ament_cmake 描述 CMake 包构建，ament_python 使用 setuptools 安装 Python 包。rosdep 按 package.xml 安装外部依赖。

src 存源码，build 存构建中间产物，install 存运行入口，log 存构建日志。编辑 src 后，运行的仍是 install 中的版本。

### 1. 一个工作空间保存什么，哪些东西由构建产生

工作空间是组织一组相互依赖 ROS 包的开发目录。推荐结构是在根目录下创建 src，所有手写包放进 src；构建后出现 build、install 和 log。build 是编译中间数据，install 是安装后的可运行布局，log 记录构建与测试信息。日常编辑源码时进入 src，运行程序时实际依赖 install 中注册的结果。

包与目录并不是任意嵌套关系。一个包由自己的 package.xml 声明边界，同一工作空间里不应出现重复包名，也不应把一个完整包塞进另一个包内部。把学习示例与实机工程分成独立工作空间，能减少同名包覆盖和依赖混杂；本章使用 ~/ros2_learning_ws，与网站源码目录没有绑定。

下面创建的是教材中的独立 learning_* 示例。它们需要读者按文中的路径保存文件，不代表已经包含在网站原有 atlas_* 下载工程里。所有路径、包名、入口名都给出明确值，后续查找“程序不存在”时才能逐一对应。

#### 创建独立工作空间

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
mkdir -p ~/ros2_learning_ws/src
cd ~/ros2_learning_ws/src
ros2 pkg create --build-type ament_cmake --license Apache-2.0 learning_boot_cpp --dependencies rclcpp
ros2 pkg create --build-type ament_python --license Apache-2.0 learning_boot_py --dependencies rclpy

```

两条 create 命令只执行一次。若目录已经存在，先检查内容，不要重新覆盖已有学习代码。

### 2. package.xml 是依赖声明，不是编译器脚本

package.xml 描述包名、版本、维护者、许可证、构建类型与依赖。colcon 需要根据这些声明确定包之间的顺序，rosdep 根据依赖键查找系统软件包。CMake 中的 find_package 能让当前编译找到库，但如果 package.xml 漏掉依赖，别人或持续集成环境仍可能无法按正确顺序准备环境。

依赖有不同阶段：构建工具用于构建机制，构建依赖用于编译，运行依赖用于程序执行。对于同时参与 C++ 编译和运行的库，depend 可以表达合并关系；纯 Python 节点通常把导入的 ROS 库列为 exec_depend。声明许可证只是填写元信息，并不会自动给外部复制代码授予新许可。

本章的两个包只依赖各自客户端库，因此清单很短。文件中的名字必须与目录和构建配置保持一致。示例维护者地址只是教学占位元信息，发布自己的包时应替换成真实可维护信息；学习阶段无需向外发布任何仓库。

#### src/learning_boot_cpp/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_boot_cpp</name>
  <version>0.0.1</version>
  <description>Minimal C++ learning node</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>

```

完整清单，覆盖 create 生成的同名文件即可。

#### src/learning_boot_py/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_boot_py</name>
  <version>0.0.1</version>
  <description>Minimal Python learning node</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_python</buildtool_depend>
  <exec_depend>rclpy</exec_depend>
  <export><build_type>ament_python</build_type></export>
</package>

```

Python 包通过 setuptools 安装，客户端库是运行依赖。

### 3. C++：从源码文件到安装入口

C++ 程序需要先编译，再链接客户端库，最后安装到 ROS 工具能找到的位置。本例 main 初始化 ROS 上下文，创建一个节点，输出日志，然后进入 spin 等待事件。没有订阅或定时器时，节点仍可以存在于图中；按 Ctrl+C 后退出等待并释放上下文。

CMake 的 project 名应与包名一致，add_executable 的目标名 hello 是稍后 ros2 run 使用的入口。ament_target_dependencies 配置目标需要的 ROS 依赖；install 的 lib/${PROJECT_NAME} 是 ROS 可执行查找约定。即使二进制已经在 build 里生成，漏掉安装步骤仍可能使 ros2 run 找不到它。

构建文件只需描述包自身如何构建，整个工作空间由 colcon 编排。不要在包内额外启动另一个 colcon 构建，也不需要把系统 rclcpp 源码复制进自己的包。依赖应通过声明和链接获得。

#### src/learning_boot_cpp/src/hello.cpp

代码类型：complete

```cpp

#include <memory>
#include "rclcpp/rclcpp.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("learning_hello_cpp");
  RCLCPP_INFO(node->get_logger(), "C++ node is ready");
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}

```

完整源码。节点会保持运行，直到收到退出请求。

#### src/learning_boot_cpp/CMakeLists.txt

代码类型：complete

```cmake

cmake_minimum_required(VERSION 3.8)
project(learning_boot_cpp)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(hello src/hello.cpp)
ament_target_dependencies(hello rclcpp)
install(TARGETS hello DESTINATION lib/${PROJECT_NAME})
ament_package()

```

完整构建文件；ament_package 放在末尾完成包的安装索引和导出处理。

### 4. Python：模块、main 与 console_scripts 的对应

Python 不需要把源文件编译成 C++ 二进制，但仍需要安装模块和创建可执行入口。目录 learning_boot_py/learning_boot_py 中的 hello.py 是模块，main 是该模块里的入口函数。setup.py 的 console_scripts 将用户看到的命令 hello 映射到 learning_boot_py.hello:main。

包内的 __init__.py 使目录成为 Python 包；resource/learning_boot_py 是 ament 索引标记；setup.cfg 指定可执行脚本安装位置。ros2 pkg create 已生成前两项，保留它们即可。若手工创建整个包，也必须创建这些文件，不能只有一个 hello.py 就期望包查找自动工作。

Python 示例捕获 KeyboardInterrupt，并在 finally 中销毁节点和关闭上下文。代码逻辑与 C++ main 的生命周期对应，但语法和入口注册方式不同。直接用 python3 执行文件与用 ros2 run 启动已安装入口是两条不同路径，调试时应明确自己正在用哪一种。

#### src/learning_boot_py/learning_boot_py/hello.py

代码类型：complete

```python

import rclpy
from rclpy.node import Node


def main(args=None):
    rclpy.init(args=args)
    node = Node('learning_hello_py')
    node.get_logger().info('Python node is ready')
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

```

完整模块，既能作为 Python 文件执行，也能被 console_scripts 调用。

#### src/learning_boot_py/setup.py

代码类型：complete

```python

from setuptools import setup

package_name = 'learning_boot_py'
setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Learner',
    maintainer_email='learner@example.com',
    description='Minimal Python learning node',
    license='Apache-2.0',
    entry_points={'console_scripts': ['hello = learning_boot_py.hello:main']},
)

```

完整安装文件，entry_points 中的三部分分别是入口名、模块路径和函数名。

#### src/learning_boot_py/setup.cfg

代码类型：complete

```ini

[develop]
script_dir=$base/lib/learning_boot_py
[install]
install_scripts=$base/lib/learning_boot_py

```

完整配置。它使 ros2 run 能在约定位置找到安装后的 Python 入口。

### 5. 依赖先解决，再构建所需包

rosdep 读取源码包的依赖声明，把依赖键转换成当前平台可安装的软件包。第一次使用时，需要管理员执行一次 rosdep init，然后普通用户执行 rosdep update；已经初始化的机器不要反复初始化。update 需要联网获取索引，install 也可能需要下载软件包，所以离线阅读不意味着依赖安装已经离线可用。

构建应从工作空间根目录执行。--packages-select 只选指定包，假设其依赖已经可用；--packages-up-to 会把工作空间内需要的依赖也纳入构建。--symlink-install 使适合链接的安装文件指向源码，方便开发，但改 C++ 代码仍需编译，改 Python 入口或安装规则也仍需重新构建。

观察 colcon 的包汇总和首个失败错误。一个下游包 aborted 可能是上游依赖失败的结果，而不是它自身源码有错。不要只复制最后一行摘要；应该进入失败包的日志，找出最早的编译或配置诊断。

#### 首次 rosdep 初始化，已做过则跳过 init

代码类型：commands

```bash

sudo rosdep init
rosdep update

```

init 使用管理员权限写系统配置，update 用普通用户更新自己的索引。

#### 工作空间根目录构建

代码类型：commands

```bash

cd ~/ros2_learning_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon list
colcon build --symlink-install --packages-select learning_boot_cpp learning_boot_py

```

执行前已加载 Jazzy，且两个包的完整文件已保存。--ignore-src 避免把工作空间里的源码包当作需要另装的依赖。

### 6. underlay 与 overlay：运行时到底找到哪一份包

/opt/ros/jazzy 是本章的基础 underlay，自建工作空间是 overlay。运行前先加载基础环境，再加载自己的 install/setup.bash。overlay 中同名包可能遮盖 underlay 中的包，因此包名冲突会直接改变实际运行的软件版本。环境顺序属于程序可重复性的一部分。

用新终端运行，能减少旧构建环境残留的干扰。source 以后检查 ros2 pkg prefix learning_boot_cpp，结果应指向当前学习工作空间。再用 ros2 pkg executables 查看 hello 是否已注册，最后启动程序；这样能将查找失败定位到包索引、安装入口或程序运行三个阶段。

不要直接编辑 install 中的生成副本来修复问题，因为下一次构建可能覆盖它。修改源码或安装规则，再构建并重新加载环境，才是可持续的修复方式。多个工作空间叠加时，还应记录每层来自哪个提交。

#### 新终端 A：验证 C++ 包

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
source ~/ros2_learning_ws/install/setup.bash
ros2 pkg prefix learning_boot_cpp
ros2 pkg executables learning_boot_cpp
ros2 run learning_boot_cpp hello

```

应看到 C++ node is ready，节点继续运行。

#### 新终端 B：验证 Python 包

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
source ~/ros2_learning_ws/install/setup.bash
ros2 run learning_boot_py hello

```

应看到 Python node is ready。第三个同样加载环境的终端可用 ros2 node list 同时看到两个节点。

### 7. 四种常见错误的定位路径

Package not found 通常先检查 source 和 package.xml，而不是立即修改节点代码。包能找到但 No executable found，优先检查 CMake install 或 Python console_scripts 与 setup.cfg。程序入口能找到但 import 失败，再检查模块路径、__init__.py、依赖和正在使用的 Python 解释器。

构建报找不到依赖时，检查依赖是否同时在清单和构建脚本中声明，并确认 rosdep 是否成功。只有某个旧终端行为不同，则可能是 overlay 顺序不同。逐层检查比删除整个 build/install 后盲目重试更有效；只有明确需要清理缓存时才清理相关构建产物。

最后要保留一个完整工程观念：源码文件负责行为，包清单负责依赖，构建或安装文件负责生成入口，环境脚本负责让入口被发现。任何一层缺失，都可能表现为“节点跑不起来”，但修复位置完全不同。

### 同一工作空间运行两种语言的节点

你已经按本章创建 learning_boot_cpp 和 learning_boot_py，希望确认它们确实来自自己的源码。

1. 检查两个包的 package.xml、源码和安装配置。

2. 在根目录安装依赖并只构建这两个包。

3. 使用新终端加载 Jazzy 与 overlay，查询包前缀。

4. 分别运行 hello，并在第三个终端查看两个节点名称。

验收：两个节点同时出现；修改各自日志后重建，应看到新输出，证明源码、构建、安装和运行链已闭合。

### 深入练习 1

C++ 程序在 build 中能直接运行，但 ros2 run 找不到它，优先检查哪里？

参考答案：检查 CMakeLists.txt 是否有 install(TARGETS hello DESTINATION lib/${PROJECT_NAME})，是否完成 colcon 安装，以及运行终端是否加载了对应 install/setup.bash。

### 深入练习 2

使用 --symlink-install 后修改了 Python console_scripts，还需要构建吗？

参考答案：需要。入口注册和安装元信息由构建安装阶段生成，符号链接不能替你重新生成新的命令入口。

### 深入练习 3

两个工作空间都有 learning_boot_cpp，怎样知道正在运行哪一个？

参考答案：在实际运行的同一终端查询 ros2 pkg prefix learning_boot_cpp，并检查 source 顺序。不要仅凭当前所在目录判断，因为包查找依赖环境路径。

### 基础验证流程

在独立学习工作空间的 src 下创建包。

先解决依赖再构建；用 colcon list 确认包被发现。

在新终端先 source Jazzy，再 source 工作空间 install/setup.bash。

通过 ros2 pkg prefix 检查当前生效的包路径。

#### 创建 Python 入门包

```bash

mkdir -p ~/ros2_learning_ws/src
cd ~/ros2_learning_ws/src
ros2 pkg create --build-type ament_python --license Apache-2.0 --node-name hello learning_py --dependencies rclpy

```

#### 构建并加载

```bash

cd ~/ros2_learning_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix learning_py
ros2 run learning_py hello

```

### 预期结果

- 包能被 colcon 找到，可执行入口能由 ros2 run 启动。

- prefix 指向学习工作空间而非不期望的其他 overlay。

### 常见问题

- 尚未初始化 rosdep；首次使用需按 rosdep 官方指南初始化并 update。

- 把两个同名包放入同一 src。

- Python 修改了 entry_points、package.xml 或 data_files 后以为 --symlink-install 可以免构建。

- 编译时加载正在构建的旧 overlay 导致依赖污染。

### 练习

分别创建 ament_cmake 与 ament_python 包，比较构建文件和可执行安装位置。

#### 参考答案

ament_cmake 包至少包含 package.xml 与 CMakeLists.txt，通过 add_executable 和 install(TARGETS ...) 安装程序；ament_python 包包含 package.xml、setup.py、setup.cfg、resource 标记和 Python 模块，通过 console_scripts 暴露入口。两者最后都通过 colcon 安装到工作空间 install 下，由 ros2 run 查询入口。

### 依据

- [工作空间与 overlay](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html)

- [创建 CMake 或 Python 包](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)

- [rosdep 依赖管理](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Rosdep.html)

- [ament_cmake 用户指南](https://docs.ros.org/en/jazzy/How-To-Guides/Ament-CMake-Documentation.html)

- [colcon 快速开始](https://colcon.readthedocs.io/en/released/user/quick-start.html)

## 4. 用 CLI 读懂运行中的系统

先确认端点存在，再确认类型，最后观察内容与频率。图工具显示连接关系，不能保证每个消息及时到达。

### 学习目标

- 从节点、接口、类型和频率逐层定位问题

- 掌握 turtlesim 作为通信实验台

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

先确认端点存在，再确认类型，最后观察内容与频率。图工具显示连接关系，不能保证每个消息及时到达。

节点名称可重映射；相对话题名会受命名空间影响。查看完整解析后的名字比猜测源码字符串更可靠。

### 1. 把终端当作逐层测量工具

调试运行中的 ROS 系统，应先确定你要验证的事实。包是否安装、节点是否运行、端点是否匹配、消息是否到达、业务是否处理正确，是五个不同问题。ros2 pkg 回答安装问题，node 回答计算图问题，topic/service/action 回答接口问题，日志和业务输出才帮助判断算法行为。一次只验证一层，才能让证据指向具体原因。

命令行工具本身也可能创建临时节点、订阅者或服务客户端，所以观察行为不是绝对无影响。例如 topic echo 会成为一个消费者，topic hz 的测量结果受到观察进程调度和通信负载影响。初学时不必担心所有测量扰动，但应避免把一条终端输出当成对整个系统的最终证明。

本章使用 turtlesim 作为纯软件实验对象。它提供位置反馈、速度输入、生成海龟服务、参数和旋转动作，足以覆盖主要接口。所有速度命令都发给 /turtle1/cmd_vel，不涉及真实底盘；以后调试实机时必须先辨认同名接口究竟连接到哪个执行对象。

### 2. 建立三个终端和稳定的观察顺序

终端 A 运行模拟器，终端 B 运行键盘控制，终端 C 查询系统。每个终端先加载 Jazzy 环境。GUI 中看见海龟只说明模拟器启动成功；把键盘焦点放到 B 终端并按方向键，才能产生控制输入。如果焦点在其他窗口，即使所有通信配置正确，也不会有新的按键消息。

先在 C 中执行 node list，通常能看见 /turtlesim 和 /teleop_turtle。随后使用 node info 查看单个节点声明的发布、订阅、服务等接口。系统还可能有参数、日志和临时工具节点，因此不要死记总数量；应确认你关心的节点及其接口是否存在。

再执行 topic list -t，将每个话题和具体接口类型关联起来。看到 /turtle1/cmd_vel 为 geometry_msgs/msg/Twist 后，才知道下一步该查看什么字段。查询顺序从“有哪些对象”到“对象用什么接口”，可以避免直接猜 YAML 字段名。

#### 启动实验对象

代码类型：commands

```bash

# 终端 A
source /opt/ros/jazzy/setup.bash
ros2 run turtlesim turtlesim_node
# 终端 B
source /opt/ros/jazzy/setup.bash
ros2 run turtlesim turtle_teleop_key

```

持续运行命令分属两个终端，键盘控制需要 B 终端获得焦点。

#### 终端 C：由节点到接口

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
ros2 node list
ros2 node info /turtlesim
ros2 topic list -t
ros2 interface show geometry_msgs/msg/Twist

```

Twist 的 linear 和 angular 都是 Vector3；它们不是一个标量字符串。

### 3. 话题的五种观察方式分别说明什么

list 告诉你有哪些话题，type 给出数据类型，info --verbose 列出端点和 QoS，echo 展示消息内容，hz 估计观察到的接收频率。它们不能相互替代：名称存在不等于有数据，有数据不等于频率正确，频率正确也不等于时间戳和坐标系正确。

当键盘节点只有按键时才发布时，echo 暂时没有输出是正常的。按方向键后应看到 linear.x 或 angular.z 改变。查看 /turtle1/pose 可看到模拟器连续提供状态。cmd_vel 表示要求海龟怎样运动，pose 表示模拟后的状态；二者分别对应控制输入和状态反馈。

如果一个话题被多个发布者同时使用，echo 输出可能交错。info --verbose 可以帮助你确认是谁在发布，而不是误把两个来源混成同一条时间序列。录制数据或调试控制时，先确认发布者数量和来源十分重要。

#### 分别运行各个观察命令，按 Ctrl+C 结束持续观察

代码类型：commands

```bash

ros2 topic type /turtle1/cmd_vel
ros2 topic info /turtle1/cmd_vel --verbose
ros2 topic echo /turtle1/cmd_vel
# 结束 echo 后再执行
ros2 topic hz /turtle1/pose

```

频率命令需要一段采样时间；输出是本观察端测得的统计，不是发行版承诺的固定频率。

### 4. 主动发送消息与调用服务

除了观察，CLI 还能充当临时发布者或服务客户端。发布之前先用 interface show 确认结构。Twist 的 angular.z 表达绕 z 轴的角速度，turtlesim 只使用平面运动相关分量。下面只发送一次小的速度命令，用来验证订阅端确实接受该接口；持续控制通常由一个明确频率的节点负责。

服务采用请求与响应协议。/spawn 的请求包含位置、朝向和名字，响应给出实际生成的名称。调用前先用 service type 或 service list -t 确认类型，再构造请求；服务名称和服务类型是两项独立信息。空服务请求也应传入有效的空 YAML 对象，而不是把类型名当请求内容。

终端中的 requester 和 response 行表示 CLI 发出请求并收到了返回值。若服务不存在，工具可能等待发现；若请求已经到达但业务处理未完成，则等待发生在另一阶段。排查时不要把所有“没有返回”都解释为服务名称拼错。

#### 一次话题发布

代码类型：commands

```bash

ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.2}}"

```

这是 turtlesim 实验命令，未给出的 Vector3 分量使用默认值。

#### 查询并调用生成服务

代码类型：commands

```bash

ros2 service list -t
ros2 service type /spawn
ros2 interface show turtlesim/srv/Spawn
ros2 service call /spawn turtlesim/srv/Spawn "{x: 2.0, y: 2.0, theta: 0.0, name: 'second'}"

```

成功后应出现名为 second 的海龟及其相关接口；重复使用同名可能被拒绝，应阅读响应而非只看进程退出。

### 5. 参数和动作是另外两种观察入口

参数描述节点配置。param list 只查询某个节点拥有的参数，get 查看当前值，set 请求修改。turtlesim 的背景色参数适合练习整数类型和范围；把参数改成字符串并不等同于同一个数值，服务端有权拒绝类型或范围不合法的变更。dump 可以把当前配置输出为可保存的 YAML。

动作与服务不同，发送目标后先有接受或拒绝，再有反馈和最终结果。turtlesim 的 RotateAbsolute 可让海龟旋转到指定角度；--feedback 让 CLI 显示执行过程。目标的 theta 单位是弧度，不能直接把九十度写成 90 而不换算。

这些工具给出了一个实用区分：参数修改观察配置是否接受，服务调用观察请求结果，动作发送观察任务生命周期。即使它们底层都通过 ROS 通信实现，应用层含义仍然不同，学习时应保留这种区别。

#### 配置查询与修改

代码类型：commands

```bash

ros2 param list /turtlesim
ros2 param get /turtlesim background_r
ros2 param set /turtlesim background_r 160
ros2 service call /clear std_srvs/srv/Empty "{}"
ros2 param dump /turtlesim

```

clear 清除画面轨迹并重新绘制，便于观察背景变化；dump 输出可重用配置。

#### 动作查询与发送

代码类型：commands

```bash

ros2 action list -t
ros2 action info /turtle1/rotate_absolute
ros2 action send_goal /turtle1/rotate_absolute turtlesim/action/RotateAbsolute "{theta: 1.57}" --feedback

```

旋转过程中会出现反馈，最终结果与目标接受消息分开显示。

### 6. 用命名空间复用同一套程序

命名空间给一组相对名称增加共同前缀。假如同时运行两套 turtlesim，直接使用默认节点名会使日志和查询难以区分；给第二套加 /robot2 前缀，再把节点重命名为 sim2，能让它的相对话题落到独立路径。源码无需修改，只调整启动配置。

键盘控制节点也必须处于对应命名空间，才能将其相对 turtle1/cmd_vel 解析到第二套模拟器的接口。如果只移动模拟器而没移动控制端，控制端仍可能向第一套发布。遇到这种情况应看最终全限定话题名，而不是只看源码中的短名字。

命名空间用于组织和避免名称碰撞，不提供网络安全隔离。ROS_DOMAIN_ID 才影响发现分组，而安全权限需要其他机制。不要把在命名空间里隐藏得较深的控制接口当作不可被其他节点访问。

#### 第二套 turtlesim，分别使用两个新终端

代码类型：commands

```bash

# 终端 D
ros2 run turtlesim turtlesim_node --ros-args -r __ns:=/robot2 -r __node:=sim2
# 终端 E
ros2 run turtlesim turtle_teleop_key --ros-args -r __ns:=/robot2 -r __node:=keys2
# 观察终端
ros2 node info /robot2/sim2
ros2 topic info /robot2/turtle1/cmd_vel --verbose

```

各终端仍需先加载 Jazzy。预期控制与反馈接口都在 /robot2 下。

### 7. 形成能复现的排错记录

当出现收不到消息，先记录启动命令和环境，再查询两端节点信息、完整话题名、接口类型及 QoS。随后观察发送端是否真的产生数据，最后再研究接收回调是否阻塞。这个顺序能防止你在没有输入的情况下反复修改订阅代码。

环境改变后，CLI daemon 可能仍保留旧环境下启动的图查询进程。比如切换 RMW 或域之后，可以停止旧 daemon，让后续查询按当前环境重新启动。daemon 只服务 CLI 查询，并不是所有节点通信依赖的中心服务器；停止它不能被当作重启整个 ROS 系统。

提交问题时附上包版本、最小启动命令、实际接口输出和预期行为。截图可以展示现象，但可复制的命令与文本输出更利于复现。若你能把复杂机器人问题缩减成两个节点和一条接口，往往已经完成了最关键的一半诊断工作。

#### 保存可解释的环境线索

代码类型：commands

```bash

printenv ROS_DISTRO
printenv ROS_DOMAIN_ID
printenv RMW_IMPLEMENTATION
ros2 doctor --report
# 仅在确实切换环境或怀疑旧 daemon 时执行
ros2 daemon stop

```

环境变量未设置可能表示采用默认值；不要把空输出直接解释为配置错误。

### 海龟不动，但模拟器窗口正常

键盘节点已启动，按方向键后海龟仍不移动。

1. 确认按键焦点在控制终端，并用 echo 检查是否有 cmd_vel 消息。

2. 用 node info 查看控制端的实际发布话题。

3. 比较模拟器订阅的话题是否处于同一命名空间。

4. 检查类型和端点 QoS；用一次 CLI 发布验证模拟器自身可接收。

验收：每个步骤排除一个具体层面，能区分输入没产生、名称不匹配和订阅处理异常。

### 深入练习 1

topic list 中出现 /scan，但 echo 没有输出，至少列出三种可能。

参考答案：发布者当前未产生数据；订阅 QoS 与发布者不兼容；观察端与数据端的类型或环境有问题；回调或网络资源拥塞也可能造成延迟。应进一步查看 info --verbose 和发布端日志。

### 深入练习 2

为什么给模拟器加 /robot2 后，原来的键盘节点可能控制不到它？

参考答案：相对话题名解析到了不同前缀。键盘端仍向原路径发布，应给它相同命名空间或显式重映射到 /robot2/turtle1/cmd_vel。

### 深入练习 3

停止 ros2 daemon 是否会停止正在运行的 talker 与 listener？

参考答案：不会。daemon 为命令行图查询提供辅助，不是 ROS 1 式中央通信主节点。已经运行的业务节点仍按自己的进程生命周期工作。

### 基础验证流程

运行 turtlesim 和键盘节点。

列出节点、话题与消息定义。

按方向键并观察 /turtle1/cmd_vel，接着用 node info 查发布端。

把节点改到另一命名空间，再比较完整话题名称。

#### 终端 A / B

```bash

# 终端 A
ros2 run turtlesim turtlesim_node
# 终端 B
ros2 run turtlesim turtle_teleop_key

```

#### 终端 C：由外到内检查

```bash

ros2 node list
ros2 node info /turtlesim
ros2 topic list -t
ros2 topic info /turtle1/cmd_vel --verbose
ros2 interface show geometry_msgs/msg/Twist
ros2 topic echo /turtle1/cmd_vel

```

### 预期结果

- 按键时可看到 linear/angular 数值变化。

- 能找出每条数据流的生产者和消费者。

### 常见问题

- 键盘终端未获得焦点，看不到数据却误判通信失败。

- 仅因 topic list 中出现名称就断言订阅一定收到消息。

### 练习

给第二只 turtlesim 设置 /robot2 命名空间，列出它和第一只不会冲突的名字。

#### 参考答案

可运行 ros2 run turtlesim turtlesim_node --ros-args -r __ns:=/robot2 -r __node:=sim2；其相对接口解析到 /robot2 下，例如 /robot2/turtle1/cmd_vel。键盘节点也需相同命名空间。注意绝对话题名以 / 开头，不会随命名空间自动改变。

### 依据

- [CLI 工具学习路线](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools.html)

- [话题检查与调试](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)

- [ros2 doctor 诊断](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Getting-Started-With-Ros2doctor.html)

## 5. C++ / Python 发布订阅与回调写法

发布者决定消息何时产生；订阅回调由执行器在消息到来时调度。timer 也需要执行器调度，构造了 timer 并不等于程序会自动运行。

### 学习目标

- 写出周期发布与事件订阅节点

- 在 lambda、成员函数和 Python 方法间建立映射

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

发布者决定消息何时产生；订阅回调由执行器在消息到来时调度。timer 也需要执行器调度，构造了 timer 并不等于程序会自动运行。

C++ 模板类型 std_msgs::msg::String 对应 Python 的 std_msgs.msg.String。接口语义相同，内存管理与回调绑定方式不同。

### 1. 先确定消息契约和节点生命周期

本章实现两个角色：发布者每半秒在 telemetry 上发送一个带序号的字符串，订阅者收到后输出日志。四个完整节点分别使用 C++ 和 Python，所以可以交叉组合验证。这里使用 std_msgs/String 是为了把注意力放在通信机制；实际传感器数据应使用有明确单位、时间和结构的专用接口。

发布订阅不需要把接收者地址写进发布者代码。端点通过名称、类型、发现条件和 QoS 建立联系。发布者可以在没有订阅者时工作，订阅者也可以先启动再等待发布者。这个低耦合特性使记录器和可视化工具能随时加入，但它不提供业务处理完成确认。

一个最小节点仍然具有完整生命周期：初始化 ROS，创建节点及通信对象，spin 处理事件，退出时销毁资源。timer 回调也是执行器调度的事件，不是创建 timer 后自动生成一个永不阻塞的独立线程。把这些阶段分清，有助于解释为什么“代码创建了发布者，却没有周期输出”。

### 2. 建立两个独立的示例包

本章的路径位于 ~/ros2_learning_ws/src，包名为 learning_topic_cpp 与 learning_topic_py。两者都依赖 std_msgs，但分别使用 rclcpp 和 rclpy。创建包后将下面完整文件保存到指定路径；示例不会自动出现在网站已有 atlas 下载包中。

C++ 的两个源码文件分别编译为 talker 与 listener。Python 的两个模块分别暴露同名入口。用户看到的入口名相同不意味着源码组织相同，关键是安装配置把入口映射正确。包清单、构建文件和代码共同构成可运行示例，单独复制一个类无法替代全部工程文件。

为避免实验日志混淆，四个节点使用不同节点名；它们仍共享相对话题 telemetry。默认命名空间下解析为 /telemetry。每次先运行一个发布者和一个订阅者，确认基本行为后再增加更多端点，这样可以清楚解释每条日志来自哪个节点。

#### 创建包骨架

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
mkdir -p ~/ros2_learning_ws/src
cd ~/ros2_learning_ws/src
ros2 pkg create --build-type ament_cmake --license Apache-2.0 learning_topic_cpp --dependencies rclcpp std_msgs
ros2 pkg create --build-type ament_python --license Apache-2.0 learning_topic_py --dependencies rclpy std_msgs

```

若包已存在，检查已有文件后再继续；保留 Python 骨架中的 __init__.py 和 resource/learning_topic_py。

### 3. C++ 发布者：模板类型、成员对象和定时器

create_publisher 的模板参数指定消息类型，字符串 telemetry 指定话题名称，整数 10 指定 KeepLast 历史深度。这里没有任何参数表示十赫兹；发送周期由 create_wall_timer 的 500ms 决定。wall timer 适合本章简单实验，涉及仿真时间时需进一步区分时钟语义。

publisher_ 与 timer_ 保存为成员，是为了使它们在节点运行期间始终存在。定时器 lambda 捕获 this 来读取计数器和发布者，因此节点对象必须保持有效。main 通过 shared_ptr 持有节点并交给 spin，直到退出后才结束其生命周期。

回调内部创建一个消息，填写 data，再 publish；日志只是辅助观察。序号在发布端递增，使订阅端能察觉间断和多来源交错。下面代码是完整文件，没有省略 main，但仍需配套包清单和 CMake 才能由 ros2 run 启动。

#### src/learning_topic_cpp/src/talker.cpp

代码类型：complete

```cpp

#include <chrono>
#include <cstdint>
#include <memory>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
using namespace std::chrono_literals;

class LearningTalker : public rclcpp::Node
{
public:
  LearningTalker() : Node("learning_talker_cpp")
  {
    publisher_ = create_publisher<std_msgs::msg::String>("telemetry", 10);
    timer_ = create_wall_timer(500ms, [this]() {
      std_msgs::msg::String message;
      message.data = "cpp sample=" + std::to_string(sequence_++);
      publisher_->publish(message);
      RCLCPP_INFO(get_logger(), "%s", message.data.c_str());
    });
  }
private:
  std::uint64_t sequence_{0};
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<LearningTalker>());
  rclcpp::shutdown();
  return 0;
}

```

完整 C++ 文件。序号在一个默认单线程执行器的定时回调内更新。

### 4. C++ 订阅者：lambda 与成员函数如何对应

订阅者没有主动轮询话题，而是注册消息到达后的回调。create_subscription 同样指定消息类型、名称和 QoS。ConstSharedPtr 表示回调持有只读消息的共享引用，本例只读取 data，不修改收到的消息。回调被执行的时间取决于执行器调度，不应假定与发布瞬间完全相同。

短逻辑可以直接写在 lambda 中；逻辑较长时可写成具名成员方法，再用 std::bind 或一个简单 lambda 转发。写法改变的是代码组织，不改变话题协议。下面完整文件使用成员方法配合 lambda 转发，既能看清回调签名，也避免初学时被绑定占位符分散注意。

订阅对象同样必须保持存活。只在构造函数局部变量里创建 subscription 然后不保留，可能在构造函数结束时失去所需对象。订阅回调应尽量短；大计算和阻塞 I/O 会影响同一执行器中的其他回调，这属于后续并发设计问题。

#### src/learning_topic_cpp/src/listener.cpp

代码类型：complete

```cpp

#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class LearningListener : public rclcpp::Node
{
public:
  LearningListener() : Node("learning_listener_cpp")
  {
    subscription_ = create_subscription<std_msgs::msg::String>(
      "telemetry", 10,
      [this](std_msgs::msg::String::ConstSharedPtr message) {
        on_message(message);
      });
  }
private:
  void on_message(std_msgs::msg::String::ConstSharedPtr message)
  {
    RCLCPP_INFO(get_logger(), "received: %s", message->data.c_str());
  }
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<LearningListener>());
  rclcpp::shutdown();
  return 0;
}

```

完整订阅者文件。对应 std::bind 写法需要 functional 头文件，但不是通信机制的另一种实现。

#### src/learning_topic_cpp/CMakeLists.txt

代码类型：complete

```cmake

cmake_minimum_required(VERSION 3.8)
project(learning_topic_cpp)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
foreach(target talker listener)
  add_executable(${target} src/${target}.cpp)
  ament_target_dependencies(${target} rclcpp std_msgs)
endforeach()
install(TARGETS talker listener DESTINATION lib/${PROJECT_NAME})
ament_package()

```

完整构建文件，分别生成并安装两个可执行入口。

#### src/learning_topic_cpp/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_topic_cpp</name>
  <version>0.0.1</version>
  <description>C++ publisher and subscriber lesson</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend>
  <depend>std_msgs</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>

```

完整包清单，与构建脚本里的依赖一致。

### 5. Python 用相同接口表达相同行为

Python 将模板消息类型改为普通函数参数 String，成员对象通过 self 保存。create_timer 接收以秒为单位的浮点周期，所以 0.5 对应 C++ 的 500ms。回调方法无需手工传入 self，访问 self.on_tick 得到的绑定方法已经包含对象引用。

发布者每次创建新的 String 对象，并把计数器组合成文本。订阅者收到生成的消息类实例，通过 message.data 读取字段。你不能直接 publish 一个普通 Python 字符串；发布者声明的类型是 String 消息类，需要把文本填入它的 data 字段。

Python 版本保留与 C++ 一致的初始化、spin 和清理流程。两种语言代码都采用单线程的简单执行方式，足以展示通信；如果稍后添加耗时操作，应重新评估回调调度，不能因使用 Python 就忽略节点生命周期。

#### src/learning_topic_py/learning_topic_py/talker.py

代码类型：complete

```python

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class LearningTalker(Node):
    def __init__(self):
        super().__init__('learning_talker_py')
        self.publisher = self.create_publisher(String, 'telemetry', 10)
        self.sequence = 0
        self.timer = self.create_timer(0.5, self.on_tick)

    def on_tick(self):
        message = String()
        message.data = f'py sample={self.sequence}'
        self.sequence += 1
        self.publisher.publish(message)
        self.get_logger().info(message.data)


def main(args=None):
    rclpy.init(args=args)
    node = LearningTalker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

```

完整 Python 发布者模块。

#### src/learning_topic_py/learning_topic_py/listener.py

代码类型：complete

```python

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class LearningListener(Node):
    def __init__(self):
        super().__init__('learning_listener_py')
        self.subscription = self.create_subscription(
            String, 'telemetry', self.on_message, 10)

    def on_message(self, message):
        self.get_logger().info(f'received: {message.data}')


def main(args=None):
    rclpy.init(args=args)
    node = LearningListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

```

完整 Python 订阅者模块；其协议与 C++ 版本相同。

### 6. 完成 Python 入口安装并构建

setup.py 中的两个 console_scripts 将 talker 和 listener 分别映射到两个模块的 main。文件路径、模块路径和入口字符串必须彼此一致：源码文件叫 talker.py，模块部分才是 learning_topic_py.talker。省略包名或把冒号写成点，都可能导致安装后入口无法正确导入。

构建前确认两个包同时声明了 std_msgs；仅在 Python 文件里 import 不能替代依赖声明。学习时机器可能碰巧已经安装依赖，但清单不完整会让别人在干净环境中失败。rosdep 的意义正是从声明恢复所需依赖，而不是依赖作者电脑的偶然状态。

--symlink-install 有助于 Python 源码编辑后快速验证，不过更改 setup.py 的入口仍应重建。完成构建后在每个运行终端加载 install/setup.bash。不要在源码目录里执行一个同名旧脚本后，以为 ros2 run 的安装入口也已经更新。

#### src/learning_topic_py/setup.py

代码类型：complete

```python

from setuptools import setup

package_name = 'learning_topic_py'
setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Learner',
    maintainer_email='learner@example.com',
    description='Python publisher and subscriber lesson',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'talker = learning_topic_py.talker:main',
        'listener = learning_topic_py.listener:main',
    ]},
)

```

完整安装文件。

#### src/learning_topic_py/setup.cfg

代码类型：complete

```ini

[develop]
script_dir=$base/lib/learning_topic_py
[install]
install_scripts=$base/lib/learning_topic_py

```

完整入口安装位置配置。

#### src/learning_topic_py/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_topic_py</name>
  <version>0.0.1</version>
  <description>Python publisher and subscriber lesson</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_python</buildtool_depend>
  <exec_depend>rclpy</exec_depend>
  <exec_depend>std_msgs</exec_depend>
  <export><build_type>ament_python</build_type></export>
</package>

```

完整清单。

#### 构建两个包

代码类型：commands

```bash

cd ~/ros2_learning_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --symlink-install --packages-select learning_topic_cpp learning_topic_py
source install/setup.bash

```

需要先完成所有源码与安装文件；依赖安装可能联网。

### 7. 交叉运行，理解输出与失败模式

先运行 C++ talker 与 Python listener，预期订阅端显示 received: cpp sample=0 及后续序号。计数从哪一个数字开始取决于订阅建立的时机；不要求一定从零收到。停止两个进程后再运行 Python talker 与 C++ listener，文本前缀应变为 py。两组实验说明共享接口而非共享源语言才是互通条件。

如果一个订阅者同时面对两个发布者，输出会交错出现 cpp 与 py 的序列。此时不应把两个独立计数器误认为一个计数器倒退。实际系统通常还需要消息来源标识、时间戳和明确的发布者职责，避免控制通道出现互相争抢的命令来源。

若没有消息，按顺序检查节点是否运行、topic info 的类型与端点、话题重映射和 QoS、回调是否被耗时操作阻塞。只提高队列深度不一定解决问题；若消费者长期比生产者慢，堆积会增加延迟。本章先保证可解释的最小链路，再进入 QoS 和执行器章节。

#### 组合 A：C++ 发布，Python 接收

代码类型：commands

```bash

# 两个终端都先 source Jazzy 和学习工作空间
# 终端 A
ros2 run learning_topic_cpp talker
# 终端 B
ros2 run learning_topic_py listener
# 观察终端
ros2 topic info /telemetry --verbose
ros2 topic hz /telemetry

```

大约两次每秒是由 0.5 秒定时周期产生；测得频率还会受运行环境影响。

#### 组合 B：先停止组合 A，再交换语言

代码类型：commands

```bash

# 终端 A
ros2 run learning_topic_py talker
# 终端 B
ros2 run learning_topic_cpp listener

```

本章给出了完整文件，但这些新增文件尚未由本次资料撰写过程编译或运行；实际验收以你的构建与终端结果为准。

### 同一接口下互换发布者实现

你先用 Python 快速实现数据源，后来希望替换为 C++，但不改下游接收者。

1. 固定接口为 /telemetry 与 std_msgs/msg/String，并记录定时周期和 QoS。

2. 运行 Python 发布者配 C++ 订阅者，记录正常输出。

3. 仅停掉发布者，改运行 C++ 发布者，保持订阅者不变。

4. 观察发现过程和新序列，确认下游不需要知道发布者源码语言。

验收：节点实现可被替换，但协议、名称、QoS 和数据语义仍必须保持兼容。

### 深入练习 1

将 create_publisher 的 10 改成 100，会把发送频率改成多少？

参考答案：不会直接改变发送频率。该数值是 KeepLast 历史深度；频率仍由定时器的 0.5 秒周期决定。

### 深入练习 2

Python 发布者能否执行 self.publisher.publish("hello")？

参考答案：不能把普通 str 当作 std_msgs.msg.String 消息。应创建 String 对象并设置 data，然后 publish 该对象。

### 深入练习 3

为什么构造函数中创建订阅后要保存 self.subscription 或 subscription_？

参考答案：要使订阅实体在节点生命周期中保持存在。只创建临时对象后丢失引用可能使其被销毁，导致节点虽然运行却没有持续订阅。

### 深入练习 4

两个发布者各从零计数，订阅输出出现 0、0、1、1，是否一定是重传重复？

参考答案：不是。它可能来自两个独立发布者。应先检查端点数量和消息来源，再分析传输层重复或应用逻辑。

### 基础验证流程

先运行官方跨语言 demo，确认环境无误。

阅读 examples 中 member_function 与 lambda 的不同实现。

创建自己的包，声明依赖、添加安装入口并构建。

将话题重映射到同一名称，交换 C++ 和 Python 的发布订阅角色。

#### 互换两端语言

```bash

# 终端 A
ros2 run demo_nodes_py talker
# 终端 B
ros2 run demo_nodes_cpp listener

```

#### 统一接口后检查

```bash

ros2 topic type /chatter
ros2 topic hz /chatter
ros2 topic info /chatter --verbose

```

### 预期结果

- 不同语言节点在同名同类型话题上通信。

- 将周期从 1 秒改为 0.1 秒后，观察频率相应改变。

### 常见问题

- 把 publisher、subscription 或 timer 只存于临时局部变量，未维持对象生命周期。

- C++ lambda 捕获对象生命周期短于回调；Python 未设置 console_scripts。

- 把 QoS depth=10 误当成发布频率 10 Hz。

### 练习

给消息加递增序号；停掉订阅者后继续发布，再解释恢复后收到的序号。

#### 参考答案

每次发布前增加序号。默认 volatile 订阅恢复后通常从重新匹配后的新消息继续，不能期待补收离线期间的全部消息；具体缓存与可靠重传也受 QoS、资源和端点生命周期影响。若确需离线数据，应记录到 bag 或应用持久存储，不把 reliable 当成无限历史。

### 依据

- [C++ 发布者与订阅者](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Publisher-And-Subscriber.html)

- [Python 发布者与订阅者](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html)

- [ros2/examples · jazzy](https://github.com/ros2/examples/tree/jazzy)

- [rclcpp · jazzy](https://github.com/ros2/rclcpp/tree/jazzy)

- [rclpy · jazzy](https://github.com/ros2/rclpy/tree/jazzy)

## 6. 自定义消息、服务与动作接口包

.msg 定义消息；.srv 以一处分隔线区分请求和响应；.action 以两处分隔线区分目标、结果和反馈。

### 学习目标

- 建立跨语言共用的接口层

- 分清数据结构与通信模式

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

.msg 定义消息；.srv 以一处分隔线区分请求和响应；.action 以两处分隔线区分目标、结果和反馈。

Jazzy 官方生成接口路径使用 ament_cmake 和 rosidl_generate_interfaces；即使使用者全部是 Python，接口包仍可独立为 CMake 包。

### 1. 接口首先是双方共享的语义契约

自定义接口不是把几个变量写进文件就结束。发布者和消费者必须同意字段代表什么、单位是什么、时间戳对应采样还是发送、无效数据如何表示。以左右轮反馈为例，两端都使用浮点数仍可能一个采用转每分钟、另一个采用弧度每秒；这种错误不会被类型检查发现，却会直接影响里程计。

先搜索系统已有标准接口。几何速度、图像、激光和关节状态通常有成熟类型，复用它们能与工具和生态组件直接连接。只有标准接口无法准确表达业务，或者需要独立定义任务协议时，再创建自定义消息。不要为了少写几个字段，把所有数据塞进一个 String 再让每个节点自行解析。

本章建立 learning_interfaces 包，包含 Telemetry.msg、Scale.srv 和 Count.action。它们分别展示数据流、短请求响应和长期任务的结构。接口包自身不创建运行节点；编译完成后只是生成各语言可导入的类型，由其他包使用这些类型建立通信端点。

### 2. 三种定义文件的组成与字段规则

.msg 的每一行描述一个字段类型和字段名；.srv 用一条三个短横线的分隔线区分请求和响应；.action 用两条分隔线区分目标、结果和反馈。分隔线属于定义语法，不是可有可无的视觉装饰。修改区域位置会改变生成的类型和协议含义。

字段名使用清晰的小写与下划线。内置整数类型有固定范围，float64 是双精度浮点；数组需要说明每个元素代表什么，并考虑无界数组造成的内存增长。可以引用其他包的消息类型，例如 std_msgs/Header，但相应依赖必须写入包清单与生成配置。

Telemetry 中的轮速明确以 rad/s 表示，header.stamp 约定为采样时间，valid 表示本次双轮数据是否有效。若左右轮可能分别失效，实际设计应使用两个有效标记或更详细状态。Count 的目标是总步数，反馈是当前进度，结果是最终完成步数；同一种 uint32 在不同区域承担不同职责。

#### src/learning_interfaces/msg/Telemetry.msg

代码类型：complete

```text

# Sample time and the frame convention for this measurement.
std_msgs/Header header
# Positive velocity means forward rolling; unit: rad/s.
float64 left_velocity_rad_s
float64 right_velocity_rad_s
bool valid

```

完整消息定义。单位与正方向属于接口约定，不能仅依赖 float64 类型推断。

#### src/learning_interfaces/srv/Scale.srv

代码类型：complete

```text

float64 value
float64 gain
---
float64 scaled

```

完整服务定义，请求包含输入与系数，响应包含计算结果。

#### src/learning_interfaces/action/Count.action

代码类型：complete

```text

uint32 target
---
uint32 completed
---
uint32 current

```

完整动作定义，后面的动作章节使用该接口实现可取消计数任务。

### 3. 为什么 Python 项目也使用 CMake 接口包

接口生成不等同于普通 Python 模块安装。rosidl 根据定义文件生成 C/C++ 类型支持、Python 消息类及通信所需元信息。Jazzy 的这条标准生成路线由 ament_cmake 组织，所以纯 Python 应用也可以依赖一个单独的 CMake 接口包；这不意味着应用逻辑必须改写成 C++。

把接口与节点分包还有架构上的好处。客户端和服务端都可以依赖轻量接口包，而不用互相依赖对方实现。若接口定义藏在某个大型驱动包里，另一个只想读取消息的项目也可能被迫引入不相关的设备依赖。清晰分包能降低构建耦合，并方便多个语言消费者共享。

创建包后建立 msg、srv、action 三个子目录，再保存上一节文件。学习目录中的包名必须保持唯一；如果已经创建过 learning_interfaces，应合并新增文件并检查定义，不能再次创建同名包或无意覆盖已经使用的接口。

#### 创建接口包与目录

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
mkdir -p ~/ros2_learning_ws/src
cd ~/ros2_learning_ws/src
ros2 pkg create --build-type ament_cmake --license Apache-2.0 learning_interfaces
mkdir -p learning_interfaces/msg learning_interfaces/srv learning_interfaces/action

```

只创建目录与骨架；下一步仍需保存三个定义文件和两个完整构建文件。

### 4. 生成依赖与运行依赖要配套声明

rosidl_default_generators 在构建阶段把定义转成代码；rosidl_default_runtime 表示运行时需要的生成类型支持。member_of_group 将包归入接口包组，供构建与发布工具识别。std_msgs 是 Header 所在包；action_msgs 支持动作通信所需的通用消息。

rosidl_generate_interfaces 的文件列表是显式清单。目录里新增文件不会自动证明它已经参与生成，必须将相对路径列入该调用。DEPENDENCIES 写出引用的外部接口包，使生成器能解析字段和类型支持依赖。CMake 末尾的 ament_export_dependencies 让下游包获得运行依赖信息。

错误信息应按生成流程阅读。若提示找不到定义文件，检查路径与大小写；若提示未知类型，检查字段引用和依赖；若 Python 导入失败但构建成功，先检查终端是否加载了最新 install 环境。不要把所有失败都归因于 Python 包安装。

#### src/learning_interfaces/CMakeLists.txt

代码类型：complete

```cmake

cmake_minimum_required(VERSION 3.8)
project(learning_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(action_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Telemetry.msg"
  "srv/Scale.srv"
  "action/Count.action"
  DEPENDENCIES std_msgs action_msgs
)
ament_export_dependencies(rosidl_default_runtime)
ament_package()

```

完整构建文件，明确生成三个接口。

#### src/learning_interfaces/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_interfaces</name>
  <version>0.0.1</version>
  <description>Shared interfaces for learning examples</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <depend>std_msgs</depend>
  <depend>action_msgs</depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_cmake</build_type></export>
</package>

```

完整接口包清单，构建类型仍是 ament_cmake。

### 5. 构建以后观察生成类型，而不是猜名字

从工作空间根目录先解决依赖，再只构建接口包。构建成功后 source install/setup.bash，将生成类型加入运行环境。ros2 interface show 可以显示定义，Python 的导入测试可以进一步证明当前解释器找到了生成模块。只在源码目录看见 .msg 文件还不能说明类型可被运行程序使用。

C++ 头文件名会按生成规则转为小写下划线风格，例如 Telemetry.msg 对应 learning_interfaces/msg/telemetry.hpp，类型则是 learning_interfaces::msg::Telemetry。Python 使用 from learning_interfaces.msg import Telemetry。服务和动作分别位于 srv 与 action 命名空间，不能全部从 msg 导入。

接口包构建后，消费者还需要把 learning_interfaces 写入自己的依赖。C++ 要 find_package 并关联目标依赖；Python 包需运行依赖，并在启动终端加载包含接口的 overlay。生成代码属于构建产物，不应手工修改它来“修复字段”，应修改原始定义再重新生成。

#### 构建与查询

代码类型：commands

```bash

cd ~/ros2_learning_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --packages-select learning_interfaces
source install/setup.bash
ros2 interface show learning_interfaces/msg/Telemetry
ros2 interface show learning_interfaces/srv/Scale
ros2 interface show learning_interfaces/action/Count
python3 -c 'from learning_interfaces.msg import Telemetry; print(Telemetry())'

```

预期能显示三个区域明确的接口定义；Python 输出字段的默认值。

#### C++ 类型使用位置

代码类型：snippet

```cpp

#include "learning_interfaces/msg/telemetry.hpp"
// 在已创建的 rclcpp::Node 方法中：
auto publisher = create_publisher<learning_interfaces::msg::Telemetry>(
    "wheel_feedback", 10);

```

局部片段，展示生成头文件与类型写法；它不是可独立编译的完整节点，实际 publisher 应持久保存。

### 6. 用一个完整 Python 文件验证自定义消息

为了让接口实验不被另一套安装入口分散注意，本节将发布节点保存为独立 Python 文件，直接用 python3 运行。它仍是 ROS 节点，只是没有注册 ros2 run 入口。前提是系统安装了 rclpy，并且当前终端已加载刚构建的 learning_interfaces。

节点每秒填写一次采样时间、坐标系、左右轮速和有效状态，再发布 wheel_feedback。数值是固定的教学模拟数据，并不是来自编码器。时间戳使用节点时钟，便于后续接入仿真时间；frame_id 的具体含义应与机器人接口约定一致，不能因为字段存在就随意填一个看起来合理的名字。

另一个终端用 echo 查询自定义类型。若字段可正常显示，就证明定义、生成、导入与通信链已闭合。接着可以修改 valid 或一个轮速观察输出，但修改字段结构本身必须重建接口和相关消费者，不是热修改普通配置。

#### 创建独立脚本目录

代码类型：commands

```bash

mkdir -p ~/ros2_learning_ws/lessons/interfaces

```

将下一份完整源码保存到该目录；本节不创建额外 Python 包。

#### lessons/interfaces/send_feedback.py

代码类型：complete

```python

import rclpy
from rclpy.node import Node
from learning_interfaces.msg import Telemetry


class FeedbackSource(Node):
    def __init__(self):
        super().__init__('learning_feedback_source')
        self.publisher = self.create_publisher(Telemetry, 'wheel_feedback', 10)
        self.timer = self.create_timer(1.0, self.publish_sample)

    def publish_sample(self):
        message = Telemetry()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = 'base_link'
        message.left_velocity_rad_s = 0.7
        message.right_velocity_rad_s = 0.5
        message.valid = True
        self.publisher.publish(message)


def main():
    rclpy.init()
    node = FeedbackSource()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

```

完整文件，模拟左右轮反馈；没有读取真实硬件。

#### 两个终端验证

代码类型：commands

```bash

# 终端 A
source /opt/ros/jazzy/setup.bash
source ~/ros2_learning_ws/install/setup.bash
python3 ~/ros2_learning_ws/lessons/interfaces/send_feedback.py
# 终端 B 同样加载两个环境后
ros2 topic echo /wheel_feedback

```

消息应包含 header、左右轮速和 valid；这些预期结果仍需由实际运行确认。

### 7. 接口演进和跨机器一致性

修改接口字段会影响生成代码与通信类型信息。即使包名和话题名保持不变，两台机器使用不同版本的定义也不能被视为兼容。接口变更应作为系统级变更管理，重建所有消费者并记录版本，尤其是同时涉及上位机、下位机和离线分析脚本时。

对外发布接口时，尽量保持字段含义稳定。将单位从转每分钟改成弧度每秒却不改说明，比显式增加一个新字段更难发现。可以使用清楚的字段名、版本说明和迁移测试帮助团队识别变化；不要把接口注释当成无关紧要的装饰。

无效数据的设计也影响算法。若编码器断线时仍发布零速度，消费者可能把故障误认为机器人静止；明确 valid 或状态码能保留这种区别。类型设计的目的不是让消息尽可能短，而是让上下游在正常和异常情况下都能正确解释数据。

### 为左右轮反馈建立跨语言接口

C++ 驱动将来负责采样，Python 记录器负责保存，你希望先用模拟数据验证协议。

1. 明确轮速单位、正方向、采样时间和无效状态。

2. 创建并构建 learning_interfaces，确认三种语言可见名称。

3. 运行完整 Python 模拟发布脚本，通过 CLI 查看字段。

4. 在未来 C++ 驱动中复用同一 Telemetry 类型，保持下游接口不变。

验收：接口与硬件实现分离，记录器可以先完成开发，后续替换数据源无需更换协议。

### 深入练习 1

纯 Python 应用为什么仍可依赖 ament_cmake 接口包？

参考答案：接口包负责 rosidl 多语言代码生成，不负责决定应用语言。生成后的 Python 消息类可以被 ament_python 包或独立 Python 节点导入。

### 深入练习 2

向 msg 目录增加 NewState.msg 后，为什么 interface show 可能仍找不到？

参考答案：需要在 rosidl_generate_interfaces 中列出该文件，重新构建接口包，并在查询终端加载更新后的 install 环境。

### 深入练习 3

断线时轮速填零和 valid=false 有什么区别？

参考答案：零是一个可能有效的物理测量，表示静止；valid=false 表示本次测量不能信任。混淆两者会让状态估计和故障判断失去信息。

### 深入练习 4

两台机器使用同名接口包但字段版本不同，只重映射话题能解决吗？

参考答案：不能。应统一接口定义和生成版本，重建消费者。名称重映射不能转换不同消息结构。

### 基础验证流程

优先检查标准接口是否已经能表达数据。

独立创建 learning_interfaces 并添加 msg/srv/action 文件。

声明生成、运行时和成员组依赖，再在 CMake 中列出全部接口文件。

先构建接口包、加载 install，再构建使用接口的节点包。

#### 创建接口包

```bash

cd ~/ros2_learning_ws/src
ros2 pkg create --build-type ament_cmake --license Apache-2.0 learning_interfaces

```

#### 理解标准结构

```bash

ros2 interface show std_msgs/msg/Header
ros2 interface show geometry_msgs/msg/TwistStamped
ros2 interface show example_interfaces/srv/AddTwoInts

```

#### 完成定义和构建配置后

```bash

cd ~/ros2_learning_ws
colcon build --packages-select learning_interfaces
source install/setup.bash

```

### 预期结果

- 生成的接口可同时被 C++ include 和 Python import。

- ros2 interface show 能显示自己定义的类型。

### 常见问题

- 只新建 .msg 文件，却忘记 rosidl_generate_interfaces。

- 没有说明数值单位、坐标系、时间戳或数组长度约束。

- 用不同定义却同名的接口在两台机器间通信。

### 练习

设计 WheelFeedback.msg，明确时间戳、左右轮角速度单位和有效性字段。

#### 参考答案

可用 std_msgs/Header header、float64 left_velocity_rad_s、float64 right_velocity_rad_s、bool valid。header.stamp 表示采样时间；约定左右轮从机器人前进方向看，正值对应向前滚动；若数据可能独立失效应分别提供有效性而非单一 bool。只有确需引用坐标系时才为 frame_id 定义明确语义。

### 依据

- [自定义 msg 和 srv](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.html)

- [创建 action 接口](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Creating-an-Action.html)

- [ament_cmake 用户指南](https://docs.ros.org/en/jazzy/How-To-Guides/Ament-CMake-Documentation.html)

## 7. 服务调用、Future 与超时

服务适合查询、重置等短操作。长任务若需要进度与取消，应选择动作。

### 学习目标

- 实现短请求响应功能

- 用异步调用保持节点可继续处理事件

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

服务适合查询、重置等短操作。长任务若需要进度与取消，应选择动作。

rclcpp 的服务客户端以 async_send_request 返回 future；rclpy 推荐 call_async。返回 future 只表示请求已提交，不表示响应已得到。

### 1. 将一次请求与一次响应关联起来

话题适合数据流，服务适合调用者需要得到明确回应的短操作。本章用两个整数相加展示协议：客户端提交 a 和 b，服务端返回 sum。服务名设为 sum，类型为 example_interfaces/srv/AddTwoInts；类型定义由系统示例接口包提供，不需要为这个实验重新创建接口。

服务端注册回调后等待请求，客户端先等待服务被发现，再发送请求。发现等待与响应等待是两个不同阶段：前者说明是否存在可联系的服务端，后者说明某次请求是否得到回应。日志应把两者区分，否则“服务没响应”会掩盖名称错误和业务阻塞这两类完全不同的原因。

本章只使用小整数进行计算，以集中解释调用流程。接口的 int64 范围有限，真实业务若允许任意输入，需要定义越界处理。AddTwoInts 没有成功标记或错误字段，说明接口能力本身也会限制业务如何报告失败；不能把一个简化教学接口当作所有生产场景的通用协议。

### 2. C++ 服务端的回调参数与生存期

create_service 的模板参数指定服务类型，回调接收请求和响应对象。请求字段已经由通信层解码，服务端将计算值写入响应，回调结束后框架发送回应。本例不需要自己创建网络连接、序列号或套接字，但仍需保证服务对象在节点运行期间存在。

把服务保存为成员 service_，main 持有节点并进入 spin。回调中的计算非常短，适合放在默认执行器里。若把数秒甚至数分钟的操作塞进这里，其他回调可能被拖住，客户端也难以获得进度；需要取消和反馈的长期任务应使用动作协议。

同一个实验一次只启动一个名为 sum 的服务端。多个同名服务端并不能自然构成你想要的负载均衡，也会使“究竟哪个实现回应了请求”变得难以判断。跨语言对照时先停止一个版本再启动另一个版本，保持其他条件相同。

#### 创建 C++ 服务示例包

代码类型：commands

```bash

cd ~/ros2_learning_ws/src
ros2 pkg create --build-type ament_cmake --license Apache-2.0 learning_service_cpp --dependencies rclcpp example_interfaces

```

保存下面三个完整文件，包名与目录保持一致。

#### src/learning_service_cpp/src/server.cpp

代码类型：complete

```cpp

#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"
using Add = example_interfaces::srv::AddTwoInts;

class SumServer : public rclcpp::Node
{
public:
  SumServer() : Node("learning_sum_cpp")
  {
    service_ = create_service<Add>("sum",
      [this](std::shared_ptr<Add::Request> request,
             std::shared_ptr<Add::Response> response) {
        response->sum = request->a + request->b;
        RCLCPP_INFO(get_logger(), "request handled");
      });
  }
private:
  rclcpp::Service<Add>::SharedPtr service_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<SumServer>());
  rclcpp::shutdown();
  return 0;
}

```

完整服务端；实验输入限制为本章给出的小整数，未加入生产级数值越界协议。

### 3. C++ 客户端：异步发送，主函数有界等待

客户端先创建与服务端同类型、同名的 client，再用 wait_for_service 等待发现。async_send_request 返回 future，表示“将来可能得到响应”；它不保证此刻结果已经到达。客户端的执行器仍需运行，才能处理返回的数据并完成 future。

本例是一次性命令行客户端，因此在 main 中调用 spin_until_future_complete，并设置两秒上限。这是在顶层驱动执行器等待，而不是在一个已运行的节点回调里嵌套 spin。两者外观看起来都像等待结果，但并发条件完全不同；将本段代码直接搬进定时回调可能导致死锁或执行器使用错误。

等待超时后客户端返回非零退出码，供脚本判断失败。超时不会自动撤销服务端已经执行的操作；这里只做无副作用的加法，重试较容易。若服务用于扣款、写入设备或修改状态，应增加幂等请求标识或状态查询，而不能假设“没有收到响应就是没有执行”。

#### src/learning_service_cpp/src/client.cpp

代码类型：complete

```cpp

#include <chrono>
#include <memory>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"
using namespace std::chrono_literals;
using Add = example_interfaces::srv::AddTwoInts;

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("learning_sum_client_cpp");
  auto client = node->create_client<Add>("sum");
  int exit_code = 1;
  if (!client->wait_for_service(2s)) {
    RCLCPP_ERROR(node->get_logger(), "sum service was not discovered");
  } else {
    auto request = std::make_shared<Add::Request>();
    request->a = 4;
    request->b = 8;
    auto future = client->async_send_request(request);
    auto status = rclcpp::spin_until_future_complete(node, future, 2s);
    if (status == rclcpp::FutureReturnCode::SUCCESS) {
      auto text = std::to_string(future.get()->sum);
      RCLCPP_INFO(node->get_logger(), "sum=%s", text.c_str());
      exit_code = 0;
    } else {
      RCLCPP_ERROR(node->get_logger(), "sum response timed out or was interrupted");
    }
  }
  rclcpp::shutdown();
  return exit_code;
}

```

完整一次性客户端。它在 main 中等待，不能原封不动嵌入正在被 spin 的回调。

#### src/learning_service_cpp/CMakeLists.txt

代码类型：complete

```cmake

cmake_minimum_required(VERSION 3.8)
project(learning_service_cpp)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(example_interfaces REQUIRED)
foreach(target server client)
  add_executable(${target} src/${target}.cpp)
  ament_target_dependencies(${target} rclcpp example_interfaces)
endforeach()
install(TARGETS server client DESTINATION lib/${PROJECT_NAME})
ament_package()

```

完整构建文件。

#### src/learning_service_cpp/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_service_cpp</name>
  <version>0.0.1</version>
  <description>C++ service lesson</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend>
  <depend>example_interfaces</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>

```

完整依赖清单；服务接口来自 example_interfaces。

### 4. Python 服务端和客户端的对应关系

Python 用 AddTwoInts 类作为 create_service 的参数，回调接收 request 和 response，并返回填好的 response。C++ 则通过共享指针写入响应；这属于客户端库的调用形式差异，传输的请求响应协议相同。服务名都为 sum 时，可用 Python 服务端回应 C++ 客户端，反过来也一样。

为减少重复安装配置，本节给出两个独立 Python 文件，保存在 lessons/services，通过 python3 启动。它们不是 ros2 run 的已安装入口；若希望打包，可采用工作空间章节的 ament_python 和 console_scripts 方式。本章已经提供完整源码，所以不需要跳转其他站点获得缺失的执行逻辑。

Python 客户端同样使用 call_async，并在顶层运行 spin_until_future_complete 处理响应。完成后检查 future 是否就绪，再读取结果；异常与超时应有可见日志。finally 负责清理节点，即使请求失败也应释放资源，避免一次性工具以不明确状态退出。

#### 准备 Python 脚本目录

代码类型：commands

```bash

mkdir -p ~/ros2_learning_ws/lessons/services

```

两个完整文件保存到此目录；系统需安装 rclpy 与 example_interfaces。

#### lessons/services/server.py

代码类型：complete

```python

import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class SumServer(Node):
    def __init__(self):
        super().__init__('learning_sum_py')
        self.service = self.create_service(AddTwoInts, 'sum', self.on_request)

    def on_request(self, request, response):
        response.sum = request.a + request.b
        self.get_logger().info('request handled')
        return response


def main():
    rclpy.init()
    node = SumServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

```

完整 Python 服务端，与 C++ 版本共用相同服务名和接口。

#### lessons/services/client.py

代码类型：complete

```python

import sys
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


def main():
    rclpy.init()
    node = Node('learning_sum_client_py')
    client = node.create_client(AddTwoInts, 'sum')
    exit_code = 1
    try:
        if not client.wait_for_service(timeout_sec=2.0):
            node.get_logger().error('sum service was not discovered')
        else:
            request = AddTwoInts.Request()
            request.a, request.b = 4, 8
            future = client.call_async(request)
            rclpy.spin_until_future_complete(node, future, timeout_sec=2.0)
            if future.done():
                response = future.result()
                node.get_logger().info(f'sum={response.sum}')
                exit_code = 0
            else:
                node.get_logger().error('sum response timed out')
    except Exception as error:
        node.get_logger().error(f'request failed: {error}')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())

```

完整一次性客户端；失败返回 1，成功返回 0，便于脚本验收。

### 5. 构建、交叉调用与终端结果解释

先构建 C++ 包并加载环境，再启动一个服务端。用 service list -t 确认 /sum 和 AddTwoInts 的对应关系，用 CLI 发出一组已知输入。得到 sum=12 只验证这次请求的计算结果；服务发现、接口类型和客户端退出码仍是另外的验收信息。

接着运行 Python 客户端调用 C++ 服务端。停止 C++ 服务端后启动 Python 服务端，再运行 C++ 客户端。如果两种组合都能输出十二，说明服务接口的跨语言兼容链工作正常。测试时不要让两个同名服务端同时运行，否则结果来源不明确。

最后执行一次故障路径：不启动任何服务端，只运行客户端。它应在设定的发现等待上限之后输出明确错误并以非零码结束，而不是无期限等待。这是本章比“能算出十二”更重要的工程练习，因为实际系统必须能区分正常结果与依赖不可用。

#### 构建 C++ 包

代码类型：commands

```bash

cd ~/ros2_learning_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --packages-select learning_service_cpp
source install/setup.bash

```

所有运行终端都需加载 Jazzy；使用自建 C++ 包的终端还需加载 overlay。

#### 组合 A：C++ 服务端，Python 客户端

代码类型：commands

```bash

# 终端 A
ros2 run learning_service_cpp server
# 终端 B
python3 ~/ros2_learning_ws/lessons/services/client.py
# 观察或额外测试终端
ros2 service list -t
ros2 service call /sum example_interfaces/srv/AddTwoInts "{a: 4, b: 8}"

```

客户端和 CLI 都应得到 12。

#### 组合 B：停止旧服务端后交换语言

代码类型：commands

```bash

# 终端 A
python3 ~/ros2_learning_ws/lessons/services/server.py
# 终端 B
ros2 run learning_service_cpp client

```

这两份程序并未由本次教材撰写过程实际运行；请保留本机构建和运行结果。

### 6. 将一次性客户端放进长期节点时要改变等待方式

长期节点通常已有执行器在运行，服务请求可能由定时器或订阅回调触发。此时推荐发出异步请求后立即返回，再通过完成回调处理结果，而不是在原回调里等待。这样执行器才有机会处理服务响应和其他事件。异步 API 与程序是否阻塞是两件事：调用 call_async 后再忙等，仍然会阻塞当前线程。

默认回调组是互斥的。若当前回调占着该组同步等待，而完成 future 所需的回调也属于同一组，就会形成互相等待。单纯换成多线程执行器不一定解决，因为同组互斥规则仍然存在。应先设计事件流程，再配置回调组和共享数据保护。

生产客户端还应管理未完成请求数量、超时和迟到结果。若定时器每次都提交新请求而服务端很慢，未完成 future 可能不断积累。可限制同一时刻只存在一个请求，超时后标记它失效，并避免迟到响应覆盖更新状态。

#### Python 长期节点中的异步模式

代码类型：snippet

```python

# 已在 Node 中创建 self.client，并定义 self.on_response。
request = AddTwoInts.Request()
request.a, request.b = 4, 8
self.pending = self.client.call_async(request)
self.pending.add_done_callback(self.on_response)
# 当前回调在这里返回，完成回调之后再读取结果。

```

局部模式片段，不是完整文件；必须另外设计异常、超时、并发请求限制及 on_response。

### 7. 选择服务还是动作，以及错误信息如何设计

如果操作只需要一个短回应，服务通常足够；如果用户要看到进度、取消操作或区分多个目标，动作更合适。用服务执行长期设备校准并不是语法错误，但调用者可能只能等待最终响应，无法标准化地观察中间状态。接口选择应来自用户和系统需要的交互语义。

自定义业务服务可以在响应中加入 success 和 message，或者用明确的状态枚举，帮助客户端区分通信成功与业务失败。收到响应说明网络交互完成，不代表请求一定被业务接受。输入校验失败、资源忙碌和设备故障都应有可区分的结果，避免全部打印到服务端日志后让客户端猜测。

接口设计还需要考虑重试。只读查询通常容易重试，带副作用的操作需要识别重复请求。对无法保证幂等的动作，客户端超时后可以先查询状态，再决定是否再次执行，而不是无限循环地发送相同命令。

### 服务可用与不可用都能得到明确结论

你要写一个自动化脚本，调用服务计算结果，失败时停止后续步骤。

1. 先启动 C++ 服务端，运行 Python 客户端，确认输出十二且退出码为零。

2. 停止服务端，再运行同一客户端，确认发现等待后返回非零码。

3. 改用 Python 服务端重复成功路径，验证语言可替换。

4. 把服务名故意写错一次，观察失败发生在发现阶段，而不是响应计算阶段。

验收：脚本能够依据结果与退出码区分成功、依赖不存在和响应超时，而不是仅依赖某一条日志文字。

### 深入练习 1

async_send_request 返回后能否立刻认为计算完成？

参考答案：不能。它返回的是未来结果的句柄；执行器还需要处理响应。应等待 future 就绪或通过完成回调读取结果。

### 深入练习 2

为何 main 中使用 spin_until_future_complete 与回调内使用它不是同一条件？

参考答案：main 中尚未由另一个执行器驱动该节点，可以有界运行执行器等待；回调内往往已经处于执行器和互斥组中，嵌套等待可能阻塞完成响应所需的回调。

### 深入练习 3

客户端两秒超时后，能否断定服务端没有执行？

参考答案：不能。请求可能已经执行，响应只是延迟或丢失。带副作用的操作需要幂等设计、请求 ID 或状态查询。

### 深入练习 4

返回 success=false 的响应，与服务不可达有什么区别？

参考答案：前者表示通信成功且业务明确拒绝或失败；后者连业务响应都没有得到。客户端应分别处理，不要把两者统一叫作网络错误。

### 基础验证流程

启动加法服务，先用 CLI 验证服务名和接口。

分别阅读 C++ 与 Python 官方客户端。

在节点回调里使用完成回调处理结果，并设计超时及失败日志。

停掉服务端，确认客户端能报告不可用而非永久卡住。

#### 终端 A：服务端

```bash

ros2 run demo_nodes_cpp add_two_ints_server

```

#### 终端 B：检查和调用

```bash

ros2 service list -t
ros2 service type /add_two_ints
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 4, b: 8}"

```

### 预期结果

- 响应 sum 为 12。

- 服务不存在时能分清等待发现和等待响应两个阶段。

### 常见问题

- 在默认互斥回调组的回调中同步等待本组负责完成的 future，造成死锁。

- 把 spin_until_future_complete 随意放进已由同一执行器 spin 的回调。

### 练习

给客户端添加有限等待和失败重试上限，并记录每次请求耗时。

#### 参考答案

等待服务发现应有总超时；请求提交后记录 steady-clock 起点并用异步完成回调处理结果；超时后标记请求已过期，忽略迟到结果，并按有限次数和退避重试。超时并不保证服务端没有执行，所以会改变状态的操作应考虑幂等性或请求 ID。

### 依据

- [C++ 服务与客户端](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Service-And-Client.html)

- [Python 服务与客户端](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html)

- [同步与异步服务调用](https://docs.ros.org/en/jazzy/How-To-Guides/Sync-Vs-Async.html)

- [回调组及死锁规避](https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html)

## 8. 动作：目标、反馈、结果与取消

动作客户端先请求目标，服务器可接受或拒绝；接受后会持续反馈并最终产生成功、取消或失败结果。

### 学习目标

- 实现可观察、可终止的长任务协议

- 理解目标接受与目标成功是两个不同阶段

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

动作客户端先请求目标，服务器可接受或拒绝；接受后会持续反馈并最终产生成功、取消或失败结果。

C++ rclcpp_action 和 Python rclpy.action 的语法不同，但目标状态机和接口定义一致。取消请求还需要服务端检查并落实。

### 1. 动作把长期任务表达成可观察的状态机

一个导航目标可能需要几十秒才完成。调用者通常希望知道目标是否被接受、当前进度、能否取消，以及最终为何成功或失败。普通话题不自带这些任务语义，短服务又只有最后一个响应。Action 将这些需求统一为目标、反馈和结果，并为每个目标维护独立状态与身份。

客户端发送目标以后，首先得到目标是否被接受的回应。接受不代表任务已经完成；之后可以收到多次反馈，最终才获得结果。取消同样是一个过程：客户端提交取消请求，服务端决定是否接受，然后执行代码在合适位置停止并设置 canceled。收到取消请求被接受的回应，也不能直接替代等待最终取消结果。

本章任务是每半秒完成一个计数步骤，总数由 target 指定。只允许一个活动目标，范围为一到二十。它足够简单，却能完整展示成功、拒绝、反馈和取消四条路径；后续可把每一步替换成巡检航点或设备操作，而保留相同任务协议。

### 2. 创建本章独立接口包，避免隐藏前置文件

为了允许直接从本章动手，使用独立 learning_count_interfaces 包，仅包含 Count.action。目标区域是 uint32 target，结果区域是 uint32 completed，反馈区域是 uint32 current。字段顺序由两条分隔线确定，目标和反馈虽然都是整数，含义却不能互换。

接口包使用 ament_cmake 与 rosidl_default_generators 生成代码，运行阶段依赖 rosidl_default_runtime。动作还会使用 action_msgs 提供的通用状态与协议消息。这个包没有业务节点，C++ 服务端和 Python 客户端都依赖它；只要二者加载同一份生成类型，就能跨语言交互。

请按路径保存三份完整文件，再构建。若以前已经完成自定义接口章节，那里的 Count 可以用作理解参照，但本章使用了不同包名，避免直接覆盖旧接口或让示例依赖未展示的文件。包名改变后，所有导入、头文件和 CLI 类型字符串都必须同步改变。

#### 创建接口与服务端包

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
mkdir -p ~/ros2_learning_ws/src
cd ~/ros2_learning_ws/src
ros2 pkg create --build-type ament_cmake --license Apache-2.0 learning_count_interfaces
mkdir -p learning_count_interfaces/action
ros2 pkg create --build-type ament_cmake --license Apache-2.0 learning_action_cpp --dependencies rclcpp rclcpp_action learning_count_interfaces
mkdir -p ~/ros2_learning_ws/lessons/actions

```

保存本章完整文件后再构建。

#### src/learning_count_interfaces/action/Count.action

代码类型：complete

```text

uint32 target
---
uint32 completed
---
uint32 current

```

完整动作接口，分别定义目标、结果和反馈。

#### src/learning_count_interfaces/CMakeLists.txt

代码类型：complete

```cmake

cmake_minimum_required(VERSION 3.8)
project(learning_count_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(action_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "action/Count.action"
  DEPENDENCIES action_msgs
)
ament_export_dependencies(rosidl_default_runtime)
ament_package()

```

完整生成配置。

#### src/learning_count_interfaces/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_count_interfaces</name>
  <version>0.0.1</version>
  <description>Count action interface</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <depend>action_msgs</depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_cmake</build_type></export>
</package>

```

完整清单，接口包可被两种语言共用。

### 3. C++ 服务端：用短定时回调推进任务

create_server 注册三个关键回调：收到目标时决定接受或拒绝，收到取消请求时决定是否允许取消，目标接受后保存 GoalHandle。这里把实际工作放进每半秒执行的定时回调，避免在目标接受回调里长时间阻塞。默认单线程执行器下，这些回调按次运行，便于理解状态变化。

busy_ 在接受目标时置位，使第二个目标被拒绝；active_ 保存当前目标句柄；completed_ 记录已完成步骤。每次 tick 首先检查取消状态，再执行一个步骤并发布反馈，到达目标后调用 succeed。取消时调用 canceled，结果中的 completed 保留已经完成的工作，而不是一律清零。

此写法不创建后台工作线程，所以每个步骤必须很短。若真实步骤要等待设备数秒，应改成异步设备接口或专门工作线程，并补充线程同步和关闭处理。动作协议不会自动把耗时操作变成非阻塞；是否能及时处理取消，仍由执行结构决定。

#### src/learning_action_cpp/src/server.cpp

代码类型：complete

```cpp

#include <chrono>
#include <cstdint>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "learning_count_interfaces/action/count.hpp"
using namespace std::chrono_literals;
using Count = learning_count_interfaces::action::Count;
using GoalHandle = rclcpp_action::ServerGoalHandle<Count>;

class CountServer : public rclcpp::Node
{
public:
  CountServer() : Node("learning_count_cpp")
  {
    server_ = rclcpp_action::create_server<Count>(this, "count",
      [this](const rclcpp_action::GoalUUID &, std::shared_ptr<const Count::Goal> goal) {
        if (busy_ || goal->target == 0 || goal->target > 20) {
          return rclcpp_action::GoalResponse::REJECT;
        }
        busy_ = true;
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
      },
      [](const std::shared_ptr<GoalHandle>) {
        return rclcpp_action::CancelResponse::ACCEPT;
      },
      [this](const std::shared_ptr<GoalHandle> handle) {
        active_ = handle;
        completed_ = 0;
      });
    timer_ = create_wall_timer(500ms, [this]() { tick(); });
  }
private:
  void tick()
  {
    if (!active_) {return;}
    if (active_->is_canceling()) {
      auto result = std::make_shared<Count::Result>();
      result->completed = completed_;
      active_->canceled(result);
      active_.reset();
      busy_ = false;
      return;
    }
    ++completed_;
    auto feedback = std::make_shared<Count::Feedback>();
    feedback->current = completed_;
    active_->publish_feedback(feedback);
    if (completed_ >= active_->get_goal()->target) {
      auto result = std::make_shared<Count::Result>();
      result->completed = completed_;
      active_->succeed(result);
      active_.reset();
      busy_ = false;
    }
  }
  bool busy_{false};
  std::uint32_t completed_{0};
  std::shared_ptr<GoalHandle> active_;
  rclcpp_action::Server<Count>::SharedPtr server_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CountServer>());
  rclcpp::shutdown();
  return 0;
}

```

完整 C++ 服务端。共享状态由默认单线程执行器串行访问，不能不加分析就换成并发回调。

#### src/learning_action_cpp/CMakeLists.txt

代码类型：complete

```cmake

cmake_minimum_required(VERSION 3.8)
project(learning_action_cpp)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(learning_count_interfaces REQUIRED)
add_executable(server src/server.cpp)
ament_target_dependencies(server rclcpp rclcpp_action learning_count_interfaces)
install(TARGETS server DESTINATION lib/${PROJECT_NAME})
ament_package()

```

完整构建文件。

#### src/learning_action_cpp/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_action_cpp</name>
  <version>0.0.1</version>
  <description>C++ count action server</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend>
  <depend>rclcpp_action</depend>
  <depend>learning_count_interfaces</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>

```

完整依赖声明。

### 4. Python 服务端：执行回调与取消回调并存

Python ActionServer 使用 execute_callback 执行目标，goal_callback 和 cancel_callback 分别决定接受策略。本例执行回调在每个步骤之间 sleep 半秒，因此使用两个工作线程和 ReentrantCallbackGroup，让取消请求能在任务等待期间被处理。锁只保护 busy 状态的检查与更新，不把整个任务循环锁住。

这与 C++ 定时推进的内部结构不同，但外部协议相同：一次只接受一个有效目标，定期发 current，成功返回 completed，取消后保留进度。对照重点是任务语义，而不是把每一个 API 调用强行做成逐行翻译。若采用单线程加阻塞 execute 回调，取消可能无法及时得到处理。

finally 清除 busy，避免异常后永久拒绝新目标。执行代码还必须在取消被请求时调用 canceled，而不是只从函数返回；正常结束则先 succeed 再返回结果。完整示例的异常关闭行为仍需在具体部署中测试，本章不声称它已连接硬件或完成生产级任务恢复。

#### lessons/actions/server.py

代码类型：complete

```python

import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from learning_count_interfaces.action import Count


class CountServer(Node):
    def __init__(self):
        super().__init__('learning_count_py')
        self.lock = threading.Lock()
        self.busy = False
        self.group = ReentrantCallbackGroup()
        self.server = ActionServer(
            self, Count, 'count', self.execute,
            goal_callback=self.on_goal,
            cancel_callback=self.on_cancel,
            callback_group=self.group)

    def on_goal(self, goal):
        with self.lock:
            if self.busy or not 1 <= goal.target <= 20:
                return GoalResponse.REJECT
            self.busy = True
        return GoalResponse.ACCEPT

    def on_cancel(self, goal_handle):
        return CancelResponse.ACCEPT

    def execute(self, goal_handle):
        result = Count.Result()
        try:
            for current in range(1, goal_handle.request.target + 1):
                if not rclpy.ok():
                    return result
                time.sleep(0.5)
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    return result
                result.completed = current
                feedback = Count.Feedback()
                feedback.current = current
                goal_handle.publish_feedback(feedback)
            goal_handle.succeed()
            return result
        finally:
            with self.lock:
                self.busy = False


def main():
    rclpy.init()
    node = CountServer()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

```

完整 Python 服务端，通过 python3 运行。sleep 只用于模拟任务耗时；真实设备步骤应有自身的超时与失败处理。

### 5. 完整客户端：分别等待接受、取消确认和最终结果

客户端先等待动作服务端可发现，再调用 send_goal_async。这个 future 的结果是 GoalHandle，不是最终 Count.Result。检查 accepted 以后，才通过 get_result_async 请求任务结果；反馈经独立回调到达。把这几个阶段命名清楚，比仅用一个变量 result 存放所有 future 更容易避免逻辑错误。

下面客户端默认请求五步任务；加 --cancel 时请求十步，并在两秒后发出取消请求。取消定时器在第一次触发后立即停用，避免重复请求。日志中的 cancel accepted 只说明服务端允许取消，程序仍继续等待最终状态 CANCELED 和完成步数。

动作结果还带有通用状态码，用于区分 SUCCEEDED、CANCELED 和 ABORTED。业务 result 则表达任务自身的数据。本例分别打印二者；未来导航任务也应同时检查状态与业务结果，而不是只看目标是否曾经被接受。

#### lessons/actions/client.py

代码类型：complete

```python

import argparse
import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from learning_count_interfaces.action import Count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cancel', action='store_true')
    options, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    node = Node('learning_count_client')
    client = ActionClient(node, Count, 'count')
    cancel_timer = None
    try:
        if not client.wait_for_server(timeout_sec=2.0):
            node.get_logger().error('count action server was not discovered')
            return 1
        goal = Count.Goal()
        goal.target = 10 if options.cancel else 5

        def on_feedback(message):
            node.get_logger().info(f'current={message.feedback.current}')

        accepted_future = client.send_goal_async(goal, feedback_callback=on_feedback)
        rclpy.spin_until_future_complete(node, accepted_future, timeout_sec=2.0)
        if not accepted_future.done():
            node.get_logger().error('goal response timed out')
            return 1
        handle = accepted_future.result()
        if not handle.accepted:
            node.get_logger().error('goal rejected')
            return 1
        result_future = handle.get_result_async()

        def on_cancel_response(future):
            response = future.result()
            node.get_logger().info(f'cancel accepted={bool(response.goals_canceling)}')

        def request_cancel():
            cancel_timer.cancel()
            future = handle.cancel_goal_async()
            future.add_done_callback(on_cancel_response)

        if options.cancel:
            cancel_timer = node.create_timer(2.0, request_cancel)
        rclpy.spin_until_future_complete(node, result_future, timeout_sec=15.0)
        if not result_future.done():
            node.get_logger().error('result timed out')
            return 1
        wrapped = result_future.result()
        labels = {
            GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
            GoalStatus.STATUS_CANCELED: 'CANCELED',
            GoalStatus.STATUS_ABORTED: 'ABORTED',
        }
        status = labels.get(wrapped.status, str(wrapped.status))
        node.get_logger().info(f'status={status}, completed={wrapped.result.completed}')
        expected = GoalStatus.STATUS_CANCELED if options.cancel else GoalStatus.STATUS_SUCCEEDED
        return 0 if wrapped.status == expected else 1
    except Exception as error:
        node.get_logger().error(f'action failed: {error}')
        return 1
    finally:
        if cancel_timer is not None:
            cancel_timer.cancel()
        client.destroy()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())

```

完整客户端可连接本章 C++ 或 Python 服务端；超时后的任务回收策略在真实项目中仍需进一步设计。

### 6. 依次验证成功、拒绝和取消

构建时 --packages-up-to learning_action_cpp 会包含工作空间内的接口依赖，确保类型先生成再编译服务端。运行 Python 文件的终端也必须加载 install 环境，否则导入 learning_count_interfaces 会失败，即使它没有使用 ros2 run。

第一次只运行 C++ 服务端，用 CLI 发送五步目标并显示反馈；应先看到目标接受，再看到递增进度和成功结果。随后发送 target=0，服务端应拒绝，不进入执行。最后运行带 --cancel 的完整客户端，预期获得 CANCELED，完成步数小于十，但不要求固定为某一个数字，因为计时和调度存在边界差异。

停止 C++ 服务端，换成 Python 服务端重复同样测试。一次只替换一个实现，可以清楚识别协议一致性；若同时运行两个同名动作服务端，测试结果来源会不明确。本章完整文件经过教材层面的检查，实际构建和运行结果仍应由你的环境验证并记录。

#### 构建并加载

代码类型：commands

```bash

cd ~/ros2_learning_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --packages-up-to learning_action_cpp
source install/setup.bash
ros2 interface show learning_count_interfaces/action/Count

```

生成接口和 C++ 服务端；所有运行终端先加载 Jazzy 与 overlay。

#### 终端 A 与测试终端

代码类型：commands

```bash

# 终端 A
ros2 run learning_action_cpp server
# 终端 B，逐个测试，等待上一目标结束
ros2 action send_goal /count learning_count_interfaces/action/Count "{target: 5}" --feedback
ros2 action send_goal /count learning_count_interfaces/action/Count "{target: 0}" --feedback
python3 ~/ros2_learning_ws/lessons/actions/client.py --cancel

```

最后一条明确执行取消测试；Ctrl+C 关闭 CLI 不应被当作标准化的取消测试。

#### 替换服务端后测试相同客户端

代码类型：commands

```bash

# 停止旧 C++ 服务端后，在终端 A
python3 ~/ros2_learning_ws/lessons/actions/server.py
# 终端 B
python3 ~/ros2_learning_ws/lessons/actions/client.py
python3 ~/ros2_learning_ws/lessons/actions/client.py --cancel

```

成功和取消是两种预期路径，客户端根据命令选项检查对应终态。

### 7. 动作接口之外仍需应用负责的部分

动作提供目标协议，但不会替你决定抢占策略。本例新目标到来时直接拒绝；其他应用可能先取消旧目标、排队等待或同时执行多个目标。每一种策略都应明确说明，并保证目标之间的资源不会互相覆盖。不能仅因为 ActionServer 支持多个目标句柄，就推断你的设备可以并行执行多个任务。

取消应检查在能保持状态一致的位置。对于不可立即中断的设备动作，可以先确认取消请求，然后在安全的步骤边界退出；但需要向用户说明延迟，并保持反馈或诊断可见。取消不是简单杀死线程，更不等于终止客户端进程。

故障路径同样需要结果。真实任务若遇到设备错误，应设置 abort 并在自定义结果中包含可解释原因；如果客户端断开，服务端是否继续执行也要有策略。最终验收应覆盖成功、非法目标、忙碌拒绝、取消和故障，而不止观察一次正常反馈。

### 同一客户端对照两种动作服务端

你希望证明服务端的内部调度方式可以变化，而任务协议保持一致。

1. 构建独立 Count 接口和 C++ 服务端。

2. 使用完整 Python 客户端验证五步成功和十步中途取消。

3. 停止 C++ 服务端，启动 Python 服务端，重复相同输入。

4. 比较终态与完成步数，允许反馈时间存在调度差异。

验收：客户端只依赖目标、反馈、结果和取消协议，不依赖服务端采用定时推进还是工作线程执行。

### 深入练习 1

目标 accepted=true 是否代表任务成功？

参考答案：不是。它只表示服务端接受了目标；还需等待最终结果，并检查通用状态是否 SUCCEEDED。

### 深入练习 2

客户端收到取消请求被接受的回应后，为什么还要等待结果？

参考答案：取消接受是协议过程的一步，任务可能需要到下一个执行边界才真正停止。最终 CANCELED 状态和结果才说明任务已经结束。

### 深入练习 3

Python 示例为什么使用 ReentrantCallbackGroup 和两个执行线程？

参考答案：执行回调中的 sleep 会占用一个线程；另一个线程需要处理取消等回调。回调组还必须允许并发，单纯增加线程数而保持同组互斥不一定有效。

### 深入练习 4

若把 C++ 示例切换成并发执行器，busy_ 是否仍可不加保护？

参考答案：不能直接假定。原示例依赖单线程串行访问；若回调可能并发，应增加适当的互斥或原子状态，并重新分析目标接受和任务结束的竞争。

### 基础验证流程

先运行发行版自带的 Fibonacci 动作演示。

用 action info 和 interface show 读出类型。

发送目标并观察 feedback 与最终 result。

在自己的实现中加入可取消的执行循环以及目标输入范围校验。

#### 如未安装，先安装官方示例

```bash

sudo apt install ros-jazzy-action-tutorials-py

```

#### 终端 A：动作服务端

```bash

ros2 run action_tutorials_py fibonacci_action_server

```

#### 终端 B：观察与发送目标

```bash

ros2 action list -t
ros2 action info /fibonacci
ros2 action send_goal /fibonacci action_tutorials_interfaces/action/Fibonacci "{order: 5}" --feedback

```

### 预期结果

- 能看到目标被接受、反馈更新以及最终序列。

- 知道客户端收到 GoalHandle 不等于任务完成。

### 常见问题

- 执行回调阻塞所有其他回调，导致取消请求不能及时处理。

- 服务端忘记设定 succeed/abort/canceled 终态或返回结果。

- 直接把教程 action 类型名替换成其他包而没同步构建接口。

### 练习

把演示改成带总步数和当前步数的巡检任务，分别测试成功、拒绝与取消路径。

#### 参考答案

Goal 包含目标点列表或总步数；Feedback 提供已完成步数；Result 提供完成状态和说明。拒绝空任务或越界输入；执行过程中定期发布反馈并检查取消；成功调用 succeed，取消调用 canceled，故障调用 abort，最终返回对应 Result。并发配置要确保取消请求能被处理。

### 依据

- [创建 action 接口](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Creating-an-Action.html)

- [C++ 动作服务端与客户端](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Cpp.html)

- [Python 动作服务端与客户端](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html)

- [动作 Python 示例可执行入口](https://raw.githubusercontent.com/ros2/demos/jazzy/action_tutorials/action_tutorials_py/setup.py)

## 9. 参数、YAML 与动态配置

参数属于具体节点，具有名称和类型；它们不是 ROS 1 的全局参数服务器。

### 学习目标

- 把可调配置从代码中抽离

- 理解启动覆盖与运行时变更的区别

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

参数属于具体节点，具有名称和类型；它们不是 ROS 1 的全局参数服务器。

declare_parameter 提供默认值和类型边界。参数文件以节点名和 ros__parameters 组织；启动参数可覆盖代码默认值。

参数被接受后，应用仍需将新值真正用于算法；仅修改参数存储不会自动重建定时器或控制器内部状态。

### 1. 参数描述配置，而不是实时数据流

参数属于某个具体节点，用于设置行为，例如增益、阈值、设备路径和是否启用某功能。它不是 ROS 1 式的全局参数服务器，也不适合用来代替高频图像、轮速和遥控消息。每个节点可以有同名参数，查询时必须说明目标节点，才能确定你在读哪一份配置。

一个参数具有名称、类型和值。Python 的 1 与 1.0 看起来都表示一，但在 ROS 参数类型里分别对应整数与双精度浮点；声明为 double 的参数不能被随意改成字符串。参数还可有描述、范围和只读约束，这些信息让配置工具和用户能理解有效取值，而不仅是猜测。

启动覆盖与运行时修改是两个阶段。节点可以用代码提供默认值，由命令行或 YAML 在启动时覆盖；运行后再通过参数服务提出变更。参数服务接受新值，只意味着配置存储更新，算法是否真正采用新值还取决于实现，尤其是缓存参数或已经创建定时器的节点。

### 2. 一个可观察的配置节点：gain 与 enabled

本章节点名为 learning_config，声明 gain 为零到二范围内的有限 double，默认一；enabled 是布尔值，默认 true。每秒计算一次固定输入 0.2 乘以 gain，并发布到 configured_value。enabled 为 false 时发布零。这个数值只是教学数据，没有连接任何执行器。

定时回调每次都读取当前参数，因此成功设置 gain 后，下一次输出就会改变。这样能同时验证参数服务的结果和业务行为，避免只看到 param get 更新却不知道内部算法是否仍用旧值。由于输入固定，gain=1.5 时预期输出为 0.3，便于检查。

自定义校验分两处：声明完成后检查启动覆盖值，运行时用 on-set 回调检查变更请求。校验回调只决定接受或拒绝，不应在其中执行有副作用的硬件操作，因为同一次变更可能还会被其他校验者拒绝。将“检查合法性”和“应用配置”分开，是参数实现的关键。

#### 创建 C++ 包和脚本目录

代码类型：commands

```bash

cd ~/ros2_learning_ws/src
ros2 pkg create --build-type ament_cmake --license Apache-2.0 learning_params_cpp --dependencies rclcpp rcl_interfaces std_msgs
mkdir -p ~/ros2_learning_ws/lessons/parameters

```

本章两种实现使用同一节点名，因此一次只运行一个版本。

### 3. C++ 完整实现与回调句柄

C++ 用 declare_parameter<double> 明确类型，用 get_parameter(...).as_double() 读取当前值。add_on_set_parameters_callback 返回的句柄保存在成员里，使校验持续生效。回调返回 SetParametersResult，其中 successful 表示是否接受，reason 给用户说明拒绝原因。

本例检查 gain 必须是有限 double 且位于零到二之间。只有检查通过才让框架保存新值；定时回调随后读取新配置。启动时参数覆盖可能在注册校验回调之前发生，所以构造函数也检查初始值，避免运行时约束严格而启动 YAML 却能绕过范围限制。

默认单线程执行器使参数服务和定时回调串行处理，适合本例。如果未来把参数缓存到多个工作线程，仍需定义配置快照与同步方式；参数 API 不会自动让任意应用成员变成线程安全。

#### src/learning_params_cpp/src/config_node.cpp

代码类型：complete

```cpp

#include <chrono>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <vector>
#include "rclcpp/rclcpp.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"
#include "std_msgs/msg/float64.hpp"
using namespace std::chrono_literals;

class ConfigNode : public rclcpp::Node
{
public:
  ConfigNode() : Node("learning_config")
  {
    const double initial_gain = declare_parameter<double>("gain", 1.0);
    declare_parameter<bool>("enabled", true);
    if (!valid_gain(initial_gain)) {
      throw std::invalid_argument("gain must be finite and within [0, 2]");
    }
    callback_ = add_on_set_parameters_callback(
      [](const std::vector<rclcpp::Parameter> & parameters) {
        rcl_interfaces::msg::SetParametersResult result;
        result.successful = true;
        for (const auto & parameter : parameters) {
          if (parameter.get_name() == "gain" &&
              (parameter.get_type() != rclcpp::ParameterType::PARAMETER_DOUBLE ||
               !valid_gain(parameter.as_double()))) {
            result.successful = false;
            result.reason = "gain must be a finite double within [0, 2]";
            break;
          }
        }
        return result;
      });
    publisher_ = create_publisher<std_msgs::msg::Float64>("configured_value", 10);
    timer_ = create_wall_timer(1s, [this]() {
      std_msgs::msg::Float64 message;
      message.data = get_parameter("enabled").as_bool()
        ? 0.2 * get_parameter("gain").as_double() : 0.0;
      publisher_->publish(message);
      RCLCPP_INFO(get_logger(), "value=%.3f", message.data);
    });
  }
private:
  static bool valid_gain(double value)
  {
    return std::isfinite(value) && value >= 0.0 && value <= 2.0;
  }
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr callback_;
  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  int exit_code = 0;
  try {
    rclcpp::spin(std::make_shared<ConfigNode>());
  } catch (const std::exception & error) {
    RCLCPP_ERROR(rclcpp::get_logger("config_startup"), "%s", error.what());
    exit_code = 1;
  }
  rclcpp::shutdown();
  return exit_code;
}

```

完整 C++ 节点，启动与动态更新均检查范围。

#### src/learning_params_cpp/CMakeLists.txt

代码类型：complete

```cmake

cmake_minimum_required(VERSION 3.8)
project(learning_params_cpp)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(std_msgs REQUIRED)
add_executable(config_node src/config_node.cpp)
ament_target_dependencies(config_node rclcpp rcl_interfaces std_msgs)
install(TARGETS config_node DESTINATION lib/${PROJECT_NAME})
ament_package()

```

完整构建文件。

#### src/learning_params_cpp/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_params_cpp</name>
  <version>0.0.1</version>
  <description>Validated parameter lesson</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend>
  <depend>rcl_interfaces</depend>
  <depend>std_msgs</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>

```

完整依赖清单。

### 4. Python 对应实现与类型校验

Python 的 declare_parameter 返回 Parameter，默认值 1.0 使 gain 的类型明确为 double。运行时校验通过 Parameter.Type.DOUBLE 检查类型，再检查数值是否有限及范围。特别处理 NaN 和无穷大很有必要，因为仅用大于或小于比较可能不能表达完整的数值约束。

Python 回调返回同样的 SetParametersResult 消息。这里没有在校验函数里直接改 self.gain，而是让框架保存参数，定时器读取正式状态。这样被拒绝的请求不会提前改变算法成员。对于需要一次更新多个相关字段的项目，可以将参数合成不可变配置快照，再在接受后切换。

本节使用独立 Python 文件启动，避免再次重复打包细节。它与 C++ 版本的外部节点名、参数名和发布类型完全相同，便于执行相同 CLI 测试。切换实现前停止旧节点，否则同名节点会使参数服务查询来源不清楚。

#### lessons/parameters/config_node.py

代码类型：complete

```python

import math
import sys
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import Float64


class ConfigNode(Node):
    def __init__(self):
        super().__init__('learning_config')
        initial = self.declare_parameter('gain', 1.0)
        initial_gain = initial.value
        self.declare_parameter('enabled', True)
        if initial.type_ != Parameter.Type.DOUBLE or not self.valid_gain(initial_gain):
            raise ValueError('gain must be finite and within [0, 2]')
        self.add_on_set_parameters_callback(self.validate)
        self.publisher = self.create_publisher(Float64, 'configured_value', 10)
        self.timer = self.create_timer(1.0, self.tick)

    @staticmethod
    def valid_gain(value):
        return math.isfinite(value) and 0.0 <= value <= 2.0

    def validate(self, parameters):
        for parameter in parameters:
            if parameter.name == 'gain':
                if parameter.type_ != Parameter.Type.DOUBLE or not self.valid_gain(parameter.value):
                    return SetParametersResult(
                        successful=False,
                        reason='gain must be a finite double within [0, 2]')
        return SetParametersResult(successful=True)

    def tick(self):
        message = Float64()
        enabled = self.get_parameter('enabled').value
        message.data = 0.2 * self.get_parameter('gain').value if enabled else 0.0
        self.publisher.publish(message)
        self.get_logger().info(f'value={message.data:.3f}')


def main():
    rclpy.init()
    node = None
    exit_code = 0
    try:
        node = ConfigNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f'configuration failed: {error}', file=sys.stderr)
        exit_code = 1
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())

```

完整 Python 文件，参数行为与 C++ 示例对应。

### 5. CLI 与 YAML 都能配置同一节点

命令行覆盖写在 --ros-args 后，例如 -p gain:=1.5。参数 YAML 则以节点名为第一层，ros__parameters 下列出参数。使用 /learning_config 明确匹配完整节点名；如果启动时改了节点名或命名空间，文件中的键也要相应变化，否则程序可能正常启动却一直使用默认值。

YAML 里的数值类型同样重要。gain: 1.0 与 gain: 1 的解析类型不同；enabled 应写 true 或 false，而不是把所有值都加引号变成字符串。保存参数时用可读文件管理配置，比把许多 -p 选项散落在 shell 历史里更方便复现。

启动后用 param get 确认最终值，用 topic echo 确认业务输出。再尝试 gain=3.0，应该收到拒绝原因并保留旧值。参数接口的验收应同时包含合法修改、非法修改和启动覆盖，不能只测试默认启动一次。

#### lessons/parameters/config.yaml

代码类型：complete

```yaml

/learning_config:
  ros__parameters:
    gain: 1.5
    enabled: true

```

完整参数文件，不是 launch YAML；它没有 launch 动作。

#### 构建和带参数启动

代码类型：commands

```bash

cd ~/ros2_learning_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --packages-select learning_params_cpp
source install/setup.bash
ros2 run learning_params_cpp config_node --ros-args --params-file ~/ros2_learning_ws/lessons/parameters/config.yaml

```

预期每秒输出约 0.300。Python 文件可使用同样的 --ros-args --params-file 参数。

#### 另一个已加载环境的终端验证

代码类型：commands

```bash

ros2 param get /learning_config gain
ros2 param set /learning_config gain 1.2
ros2 param set /learning_config gain 3.0
ros2 param get /learning_config gain
ros2 param set /learning_config enabled false
ros2 topic echo /configured_value

```

1.2 被接受，3.0 被拒绝；enabled=false 后业务输出应为零。

### 6. 参数一致性、原子更新与动态生效

多个参数可能共同组成约束，例如最小速度必须小于最大速度。逐项设置时，中间状态可能暂时违反约束；set_parameters_atomically 表达一组参数要么整体接受，要么整体拒绝。验证函数应针对候选的新配置整体检查，不能只分别检查每个字段范围。

即使参数原子地存入节点，应用层若把它们逐个复制到不同线程，也可能看见不一致快照。需要并发读取时，考虑构建一份完整的新配置对象，在受控位置一次替换。参数协议负责存储和通知，应用仍负责算法内部的一致性。

改变频率参数不会自动改变已经创建的定时器。若节点启动时按频率创建 timer，动态更新后需要取消并重建或重新配置相关资源。本章故意让 tick 每次读取 gain，避免隐藏这一步；以后设计相机分辨率、硬件模式或控制周期时，必须明确哪些参数支持运行时生效，哪些只能重新配置或重启。

### 7. 排查“参数改了但行为没变”

先确认操作的是正确节点，包括命名空间和是否存在同名实例；接着读取参数服务的返回结果，不能只看命令被执行。若返回成功，再 get 最终值；如果值已经改变但输出不变，问题通常位于算法缓存、未重建资源或另一个实际工作节点。

启动参数未生效时，检查 YAML 节点匹配、缩进、参数类型和实际传入路径。可以先用单个 CLI -p 覆盖做最小实验，排除文件解析与匹配问题，再恢复完整文件。对于复杂 launch，最终参数经过多层组合时应记录来源和优先级，不要只看其中一个默认值。

最后保留配置快照。param dump 能帮助记录运行时值，但它不能保存设备固件、外部文件内容或所有隐含默认行为。可重复实验还应同时记录代码版本、地图和标定文件、发行版及启动命令。

#### 保存当前参数快照

代码类型：commands

```bash

ros2 param dump /learning_config > ~/ros2_learning_ws/lessons/parameters/runtime.yaml

```

这是运行时参数输出，不应被误认为完整系统备份；修改文件路径前确认不会覆盖需要保留的记录。

### 证明参数变更确实进入算法

操作者把 gain 从一改成一点五，希望输出从零点二变成零点三。

1. 用默认值启动一个实现，观察输出约 0.200。

2. 设置 gain=1.5，读取参数并观察下一次输出约 0.300。

3. 尝试 gain=3.0，确认被拒绝且输出保持不变。

4. 设置 enabled=false，确认输出归零；再用 YAML 重启验证启动覆盖。

验收：配置接口、范围校验和业务生效三个环节都获得可观察证据。

### 深入练习 1

gain 声明为 double，为什么 YAML 中写 gain: 1 可能被拒绝？

参考答案：YAML 将 1 解析为整数，而 1.0 才是浮点。ROS 参数具有类型，不能假定它会自动按业务意图转换。

### 深入练习 2

为什么参数校验回调不应该立即写入硬件？

参考答案：校验阶段的变更仍可能被其他检查拒绝。提前执行副作用会造成参数存储未更新而设备状态已改变，破坏一致性。

### 深入练习 3

param get 显示频率已经变化，定时器却仍按旧周期运行，原因是什么？

参考答案：定时器是按旧参数创建的资源，参数存储改变不会自动重建它。实现需要明确更新定时器或规定该参数只能在重新配置时生效。

### 深入练习 4

min_limit 和 max_limit 有联合约束时，怎样避免逐个修改产生非法中间状态？

参考答案：使用原子参数更新，基于旧配置和全部候选新值构造完整配置后校验；应用层也应以一致快照更新。

### 基础验证流程

用 turtlesim 的背景色参数练习 list/get/set。

dump 参数并检查 YAML 中的节点名。

启动自己的节点时传入 --params-file。

给动态参数建立范围校验；把相互约束的参数作为一个配置整体处理。

#### turtlesim 正在运行时

```bash

ros2 param list /turtlesim
ros2 param get /turtlesim background_r
ros2 param set /turtlesim background_r 160
ros2 param dump /turtlesim

```

#### 命令行覆盖示例

```bash

ros2 run turtlesim turtlesim_node --ros-args -r __node:=configured_sim -p background_r:=160

```

### 预期结果

- 参数查询能看到新值。

- 同一可执行程序可通过不同参数创建不同实例。

### 常见问题

- YAML 的节点名称与最终重映射后的名字不匹配。

- 整数 1 和浮点数 1.0 被当成完全相同参数类型。

- 把 launch argument 当作已经声明到节点的 ROS 参数。

### 练习

为自己的节点设计频率参数，并拒绝 0 和负值；测试参数变化是否真正改变发布周期。

#### 参考答案

声明 double 类型频率，并在参数回调中校验有限且大于 0。验证失败返回 unsuccessful，保持旧配置；成功后在适当的更新路径重新设置定时器周期。用 ros2 param set 进行合法/非法值测试，再用 ros2 topic hz 和时间戳证实行为变化；只检查 param get 不够。

### 依据

- [C++ 参数节点](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-CPP.html)

- [Python 参数节点](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-Python.html)

- [Python / XML / YAML launch 对照](https://docs.ros.org/en/jazzy/How-To-Guides/Launch-file-different-formats.html)

## 10. Python / XML / YAML 启动系统

launch 文件描述启动动作；节点源码实现运行逻辑。Python launch 可以启动 C++ 节点，XML/YAML 也可以启动 Python 节点。

### 学习目标

- 用一个入口启动可配置的节点集合

- 把三种 launch 写法映射到相同语义

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

launch 文件描述启动动作；节点源码实现运行逻辑。Python launch 可以启动 C++ 节点，XML/YAML 也可以启动 Python 节点。

Python 用 LaunchDescription 与 Node 对象；XML/YAML 由前端解析到动作。复杂动态计算可用 Python，但普通参数、重映射、命名空间三种格式均可表达。

### 1. 启动文件负责组织系统，不代替节点业务逻辑

当一个系统需要多个节点时，手工打开终端并重复输入参数容易产生遗漏。launch 将这些启动动作、名称、命名空间、参数和重映射写成可保存的系统入口。节点仍然负责处理消息和运行算法，启动文件不应该变成另一个难以测试的业务处理程序。

Python launch 可以启动 C++ 节点，XML 和 YAML 也可以启动 Python 节点；文件格式与节点源码语言没有绑定关系。三种格式最终都描述启动动作。Python 能使用语言本身组织更复杂的逻辑，但简单系统用声明式格式可能更容易评审，选择应取决于团队需求而非认为某一种格式天然更高级。

本章用官方 demo_nodes_cpp talker 与 demo_nodes_py listener 组成同一系统：二者放在可配置命名空间中，把 chatter 重映射为 telemetry。三种完整文件应产生相同节点名与话题路径，从而让你通过运行结果理解等价关系，而不只是比较外观。

### 2. 创建只安装配置的 bringup 包

启动文件应随包安装到 share 目录，才能通过 ros2 launch 包名 文件名 找到。源码目录里有文件，不意味着已经被安装。一个 bringup 包可以没有 C++ 或 Python业务源码，只负责组织 launch 和 config；它仍需 package.xml 描述运行时需要哪些节点包和启动库。

本章创建 learning_bringup，下面有 launch 和 config 两个目录。CMake 将这两个目录安装到 share/learning_bringup；包清单声明三种 launch 前端、演示节点和 turtlesim。这样即使在干净环境中安装依赖，工具也知道这些配置需要哪些软件。

如果只用绝对文件路径执行 ros2 launch，也可以做临时实验，但包安装方式更适合分享和部署，因为它不依赖开发者个人目录。保存完整文件后再构建；修改安装规则或新增配置文件时应重新构建，以确保安装布局包含新内容。

#### 创建配置包与目录

代码类型：commands

```bash

cd ~/ros2_learning_ws/src
ros2 pkg create --build-type ament_cmake --license Apache-2.0 learning_bringup
mkdir -p learning_bringup/launch learning_bringup/config

```

此包只组织启动配置，不生成节点二进制。

#### src/learning_bringup/CMakeLists.txt

代码类型：complete

```cmake

cmake_minimum_required(VERSION 3.8)
project(learning_bringup)
find_package(ament_cmake REQUIRED)
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})
ament_package()

```

完整安装文件，将 launch 和 config 目录一起安装。

#### src/learning_bringup/package.xml

代码类型：complete

```xml

<?xml version="1.0"?>
<package format="3">
  <name>learning_bringup</name>
  <version>0.0.1</version>
  <description>Equivalent ROS 2 launch formats</description>
  <maintainer email="learner@example.com">Learner</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <exec_depend>launch</exec_depend>
  <exec_depend>launch_ros</exec_depend>
  <exec_depend>launch_xml</exec_depend>
  <exec_depend>launch_yaml</exec_depend>
  <exec_depend>demo_nodes_cpp</exec_depend>
  <exec_depend>demo_nodes_py</exec_depend>
  <exec_depend>turtlesim</exec_depend>
  <export><build_type>ament_cmake</build_type></export>
</package>

```

完整依赖清单，三种格式的解析前端也明确列出。

### 3. Python：LaunchDescription、Node 与延迟求值

Python 文件提供 generate_launch_description 函数，返回 LaunchDescription，其中包含按配置执行的动作。Node 的 package 指定包，executable 指定安装入口，name 改变 ROS 节点名，namespace 影响相对接口名称，remappings 则指定旧名称到新名称的映射。output=screen 让进程输出出现在启动终端。

DeclareLaunchArgument 声明可由命令行传入的启动参数，LaunchConfiguration 表示运行启动描述时再解析的值。它不是已经求出的普通字符串，因此不能随意对它执行普通 Python 字符串比较来决定条件。需要条件控制时应使用 launch 的条件与替换机制，或在明确的上下文中求值。

两个 Node 都使用相同 robot_ns 和相同重映射，因此发布和订阅解析到同一条 /robot1/telemetry。修改命名空间参数会同时移动两端，不需要修改任何节点源码。name 分别是 source 与 sink，避免继承默认节点名后难以区分系统实例。

#### src/learning_bringup/launch/telemetry.launch.py

代码类型：complete

```python

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robot_ns = LaunchConfiguration('robot_ns')
    return LaunchDescription([
        DeclareLaunchArgument('robot_ns', default_value='robot1'),
        Node(
            package='demo_nodes_cpp', executable='talker',
            name='source', namespace=robot_ns, output='screen',
            remappings=[('chatter', 'telemetry')]),
        Node(
            package='demo_nodes_py', executable='listener',
            name='sink', namespace=robot_ns, output='screen',
            remappings=[('chatter', 'telemetry')]),
    ])

```

完整 Python launch 文件。启动参数只是启动系统的输入，不会自动成为节点的 ROS 参数。

### 4. XML 与 YAML：同一配置的两种声明式表达

XML 中 arg 对应启动参数声明，node 对应 ROS 节点动作，remap 对应名称映射。ROS 2 的节点入口属性是 exec，不应直接照搬 ROS 1 的 type。$(var robot_ns) 是启动时替换表达式，对应 Python 的 LaunchConfiguration。

YAML 的最外层是 launch，下面是动作列表；每个 node 包含 pkg、exec、namespace 等字段，remap 是映射列表。它与参数 YAML 的结构完全不同：参数文件以节点名和 ros__parameters 组织。看到扩展名都是 yaml，不能据此判断文件可被同一个工具解析。

三份文件在本例语义等价，但不代表所有高级 Python 能力都能逐字翻译成 XML 或 YAML。复杂动态生成和自定义动作可能需要 Python。先把公共概念对应清楚，再按需要使用扩展能力，能减少把特定语法误当成 ROS 原理的情况。

#### src/learning_bringup/launch/telemetry.launch.xml

代码类型：complete

```xml

<launch>
  <arg name="robot_ns" default="robot1"/>
  <node pkg="demo_nodes_cpp" exec="talker" name="source"
        namespace="$(var robot_ns)" output="screen">
    <remap from="chatter" to="telemetry"/>
  </node>
  <node pkg="demo_nodes_py" exec="listener" name="sink"
        namespace="$(var robot_ns)" output="screen">
    <remap from="chatter" to="telemetry"/>
  </node>
</launch>

```

完整 XML launch，节点配置与 Python 版本对应。

#### src/learning_bringup/launch/telemetry.launch.yaml

代码类型：complete

```yaml

launch:
  - arg:
      name: robot_ns
      default: robot1
  - node:
      pkg: demo_nodes_cpp
      exec: talker
      name: source
      namespace: "$(var robot_ns)"
      output: screen
      remap:
        - from: chatter
          to: telemetry
  - node:
      pkg: demo_nodes_py
      exec: listener
      name: sink
      namespace: "$(var robot_ns)"
      output: screen
      remap:
        - from: chatter
          to: telemetry

```

完整 launch YAML。缩进表达层级，列表前的短横线不可随意省略。

### 5. 启动参数如何变成节点参数

启动参数与 ROS 参数属于不同层。robot_ns 只是 launch 的输入；只有显式放进 Node 的 namespace 才影响节点命名空间。同样，声明一个 red 启动参数并不会自动给 turtlesim 设置 background_r，必须在 parameters 配置里进行映射。

下面完整示例先读取 config/sim.yaml，再用启动参数覆盖 background_r。FindPackageShare 在已安装包索引中查找目录，PathJoinSubstitution 组合路径，不把用户主目录写死在代码里。ParameterValue 将延迟得到的 red 明确转换为整数，避免字符串解析和参数类型不一致。

文件中的 /config_sim 要与最终节点名对应。若再加命名空间，必须调整匹配规则或配置组织。参数列表的后续值可覆盖前面同名参数，适合保留一份基础配置，再针对当前运行覆盖少量字段；团队应明确这种优先级，避免多个文件相互覆盖却无人知道最终值。

#### src/learning_bringup/config/sim.yaml

代码类型：complete

```yaml

/config_sim:
  ros__parameters:
    background_r: 100
    background_g: 80
    background_b: 40

```

完整参数 YAML，注意它没有 launch 顶层。

#### src/learning_bringup/launch/with_parameters.launch.py

代码类型：complete

```python

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config_file = PathJoinSubstitution([
        FindPackageShare('learning_bringup'), 'config', 'sim.yaml'])
    red = ParameterValue(LaunchConfiguration('red'), value_type=int)
    return LaunchDescription([
        DeclareLaunchArgument('red', default_value='160'),
        Node(
            package='turtlesim', executable='turtlesim_node',
            name='config_sim', output='screen',
            parameters=[config_file, {'background_r': red}]),
    ])

```

完整文件，包含参数文件定位、启动参数声明和显式类型转换；运行需要图形环境。

### 6. 构建后以实际图验证三种格式等价

安装依赖并构建 learning_bringup 后，在新终端加载 Jazzy 和 overlay。先运行 Python 版本，确认 source、sink 节点都位于 robot1 下，且订阅日志持续出现。观察终端使用 topic info 检查 /robot1/telemetry 的发布与订阅端点。

停止本次 launch，再分别运行 XML 与 YAML 版本。不要同时启动三份相同配置，否则会产生重复节点名和多个发布者，破坏对照条件。比较的重点是节点全名、话题类型、重映射和数据流，而不是要求进程 ID 或日志时间戳相同。

最后传入 robot_ns:=robot2，确认完整接口移动到 /robot2。若想同时运行两套实例，分别使用 robot1 和 robot2 即可。只要节点内部使用相对接口名，启动配置就能复用软件；写死的绝对名称则可能逃出命名空间，需要单独检查。

#### 构建启动包

代码类型：commands

```bash

cd ~/ros2_learning_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --symlink-install --packages-select learning_bringup
source install/setup.bash
ros2 launch learning_bringup telemetry.launch.py robot_ns:=robot1

```

最后一条持续运行，其他检查放到新终端。

#### 逐个替换格式或命名空间

代码类型：commands

```bash

# 停止上一组后分别运行
ros2 launch learning_bringup telemetry.launch.xml robot_ns:=robot1
ros2 launch learning_bringup telemetry.launch.yaml robot_ns:=robot1
ros2 launch learning_bringup telemetry.launch.py robot_ns:=robot2

```

这是三个独立实验，不是要求一口气顺序执行。

#### 观察终端

代码类型：commands

```bash

ros2 node list
ros2 topic info /robot1/telemetry --verbose
ros2 topic echo /robot1/telemetry

```

运行 robot2 实验时相应改为 /robot2/telemetry。

### 7. 大型系统的 include、分组和就绪条件

大型机器人通常把模型、传感器、控制和导航分成子启动文件，再由顶层入口组合。IncludeLaunchDescription 复用子系统，GroupAction 可以为一组动作设置作用域，PushROSNamespace 为其增加共同命名空间。划分应沿着可独立配置和验证的子系统，而不是按文件长度机械切分。

启动顺序与业务就绪不是一回事。某进程已经创建，不代表设备初始化完成；延迟几秒的 TimerAction 也只是时间延后，不是可靠的就绪检测。对于需要严格依赖的系统，应使用生命周期状态、服务可用、明确事件或健康检查来决定后续步骤。

进程退出事件可以触发其他启动动作，但也要区分正常退出与失败退出。复位一个相机驱动时是否需要同时重启感知和导航，应由系统策略决定。launch 提供组织工具，不能替代你对故障传播和恢复边界的设计。

### 8. 常见报错的定位顺序

提示 launch 文件找不到时，先用 ros2 pkg prefix 确认实际包位置，再检查 share/learning_bringup/launch 是否安装了文件。提示 Unknown substitution 或解析错误时，检查所用前端、格式、缩进与 ROS 1/ROS 2 语法差异。启动 Python 文件报 ImportError，则检查 launch 相关依赖和系统 Python 环境。

节点启动了却互相不通信，应检查最终解析名称和重映射是否两端都应用。参数没有生效，则读取目标节点的最终参数，而不是只看 launch 源码里的字面值。with_parameters 示例可用 red:=200 启动，再查询 /config_sim 的 background_r，验证覆盖链。

将复杂问题缩减到本章两个演示节点的配置，能帮助区分启动系统错误与业务节点错误。保留一份已验证的最小启动文件，逐项增加参数和子系统，比同时修改所有文件更容易看清是哪一步改变了行为。

#### 检查参数覆盖链

代码类型：commands

```bash

# 终端 A
ros2 launch learning_bringup with_parameters.launch.py red:=200
# 终端 B
ros2 param get /config_sim background_r
ros2 param get /config_sim background_g

```

预期 red 来自命令行覆盖值 200，green 来自参数文件的 80；实际结果仍需本机验证。

### 为两个独立机器人复用同一套通信入口

你希望同一台开发机同时运行两套演示系统，接口互不混淆。

1. 构建 learning_bringup 并运行 robot_ns:=robot1。

2. 在另一终端运行相同 launch 文件但传入 robot_ns:=robot2。

3. 查询两套 source/sink 节点和 telemetry 话题。

4. 停止其中一组，确认另一组仍继续工作，再检查绝对名称是否意外跨组共享。

验收：同一源码通过配置形成两个命名空间实例；配置复用并不等于安全隔离。

### 深入练习 1

Python launch 是否只能启动 Python 节点？

参考答案：不是。launch 文件语言与业务节点语言独立，Node 根据 package 和 executable 启动已安装程序。

### 深入练习 2

声明 red 启动参数后，turtlesim 的 background_r 为什么不会自动改变？

参考答案：启动参数只存在于 launch 上下文，必须显式通过 Node(parameters=...) 映射成对应 ROS 参数，并处理正确类型。

### 深入练习 3

为什么同样是 YAML，参数文件不能直接当本章 launch YAML 使用？

参考答案：两者有不同模式。参数文件按节点名和 ros__parameters 组织；launch YAML 包含 launch 动作列表。扩展名相同不代表语法语义相同。

### 深入练习 4

TimerAction 延迟五秒启动导航，是否证明传感器已就绪？

参考答案：不能。延迟只说明时间经过，无法证明初始化成功。应依据生命周期状态、服务可用或明确健康检查决定后续启动。

### 基础验证流程

先制作仅启动一个 talker 的最小文件。

添加 namespace 与 chatter→telemetry 的 remap。

用 Python、XML、YAML 分别表达同一配置并逐个运行。

最后加入 launch argument、参数文件和 include，确认参数传递链。

#### 保存对应完整示例后，逐个测试

```bash

ros2 launch ./telemetry.launch.py
# 停止后测试另一个格式
ros2 launch ./telemetry.launch.xml
# 停止后测试另一个格式
ros2 launch ./telemetry.launch.yaml

```

#### 另一个终端验证三者语义

```bash

ros2 node list
ros2 topic list -t
ros2 topic echo /robot1/telemetry

```

### 预期结果

- 三种文件均启动 /robot1/talker，并发布 /robot1/telemetry。

- 文件格式改变不影响节点语言和接口。

### 常见问题

- 混淆参数 YAML 与 launch YAML；前者有 ros__parameters，后者有 launch 动作。

- 把 ROS 1 XML 的 type 属性直接用到 ROS 2 Node 配置；ROS 2 前端使用 exec。

- launch.py 文件存在 src 中但没有安装到包 share 目录。

### 练习

将 robot1 改成启动参数，运行两个命名空间，确认它们不会共用同名相对话题。

#### 参考答案

在 Python 中用 DeclareLaunchArgument 与 LaunchConfiguration，把 namespace 传给 Node；XML/YAML 用 arg 和对应 var substitution。分别以 robot1 和 robot2 启动，预期出现 /robot1/telemetry 与 /robot2/telemetry。不要把输入参数写成固定字符串 namespace="robot_ns"。

### 依据

- [Python / XML / YAML launch 对照](https://docs.ros.org/en/jazzy/How-To-Guides/Launch-file-different-formats.html)

- [官方 YAML launch 源文件](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/How-To-Guides/launch/different_formats_launch.yaml)

- [官方 Python launch 源文件](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/How-To-Guides/launch/different_formats_launch.py)

- [创建 CMake 或 Python 包](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)

## 11. QoS：能发现不等于能通信

QoS 是发布端与订阅端的契约。可靠订阅者要求 reliable，best_effort 发布者无法满足；reliable 发布者可以向 best_effort 订阅者提供数据。

### 学习目标

- 根据传感器和状态数据选择 QoS

- 诊断 requested/offered 不兼容

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

QoS 是发布端与订阅端的契约。可靠订阅者要求 reliable，best_effort 发布者无法满足；reliable 发布者可以向 best_effort 订阅者提供数据。

transient_local 用于保留历史样本给晚加入者，但双方 durability 及历史深度仍需正确配置；它不等于永久数据库。

depth 控制 KeepLast 缓存，不控制频率。提高可靠性也不能保证任意网络下的实时截止时间。

### 从业务要求推导通信契约

设想相机每秒产生三十帧图像，而识别器只来得及处理十帧。保存全部图像适合离线分析，在线避障却更需要最新图像。QoS 的选择必须先回答：允许丢哪些数据、最旧可以接受多久、晚启动是否需要历史、失联如何发现。它配置的是通信行为，不能替应用决定过期指令是否仍然有效。

排查时把链路分成发现、端点匹配、传输、回调处理四层。节点出现在图中只能证明发现发生过；发布者和订阅者的名称与类型相同也不保证策略兼容。即使底层已经接收，执行器忙于其他回调仍会推迟处理。把这四层混在一起，会出现不断调大队列却无法改善延迟的情况。

### 逐项判断请求与提供是否相容

可靠性可以理解为订阅者提出最低要求：可靠发布者能够连接可靠或尽力订阅者；尽力发布者只能满足尽力订阅者。持久性也有方向：瞬态本地发布者可以匹配瞬态本地或易失订阅者；易失发布者不能满足要求历史数据的瞬态本地订阅者。两项都兼容才可能通信，不能只检查其中一项。

截止间隔比较的是持续时间。发布端承诺的最大间隔应小于或等于订阅端允许的最大间隔；发布端二十毫秒、订阅端五十毫秒可兼容，反向则不满足要求。默认的无限持续时间不能当作一个具体的短间隔。活性策略及租约也参与兼容判断，手动话题活性比自动活性要求更严格；history 和 depth 不要求两端数字完全相同。

- 可靠发布 → 可靠订阅：兼容；可靠发布 → 尽力订阅：兼容。

- 尽力发布 → 可靠订阅：不兼容；尽力发布 → 尽力订阅：兼容。

- 瞬态本地发布 → 易失订阅：能匹配，但不能据此要求晚加入历史；历史重放应明确配置双方瞬态本地。

### 缓存、过期与业务确认解决不同问题

KeepLast 的深度表示保留的样本数，不是发布频率。假设单条图像约三兆字节、深度十，仅样本有效载荷就约三十兆字节；复制、分配和中间件缓冲还会增加内存。KeepAll 也受资源限制，不能视为无限存储。如果每个回调耗时八十毫秒，单线程最多约每秒处理十二点五条，调整深度不能让它处理完每秒四十条的持续输入。

可靠传输会重试，但不保证应用在指定时刻处理数据，也不保证设备已经执行动作。控制指令应携带可校验的时间或序号，并设计超时停止；需要确认结果的操作应有响应或反馈。Lifespan 让过期样本失效，Deadline 反映预期消息间隔并可触发事件，它们都不会自动提高发布频率或替控制器执行保护逻辑。

### 用最小实验分离不匹配与处理迟缓

本实验只需 Jazzy 的命令行工具和 std_msgs。每个终端先加载同一环境、使用相同域，确保没有同名旧发布者。终端甲持续发布尽力消息，终端乙先提出可靠要求，再终止并改成尽力要求。终端丙保留端点详情，作为判断原因的证据；不要用“画面没有更新”代替对策略的检查。

首次组合应无法传递样本，并可能出现不兼容提示；改为尽力后应持续收到内容。若仍无数据，首先检查类型、域、名称重映射及多个发布端，再检查订阅进程是否真的在执行回调。命令中的可靠性只覆盖对应策略，其余策略保留工具默认值，因此正式工程仍应保存完整配置。

#### 三个终端的匹配实验

代码类型：commands

```bash

# 所有终端先执行
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
# 终端甲
ros2 topic pub /qos_probe std_msgs/msg/String '{data: sample}' --rate 2 --qos-reliability best_effort
# 终端乙：先执行第一条，Ctrl+C 后执行第二条
ros2 topic echo /qos_probe std_msgs/msg/String --qos-reliability reliable
ros2 topic echo /qos_probe std_msgs/msg/String --qos-reliability best_effort
# 终端丙
ros2 topic info /qos_probe --verbose

```

终端甲每半秒生成一个样本；终端乙只改变请求的可靠性，以控制变量；终端丙查看每个发布和订阅端点，避免把另一节点的配置误认为当前实验配置。注释所标终端应分别打开，不能把阻塞命令当作顺序脚本一次执行。

### 晚加入实验与瞬态本地的存活边界

下面是独立 Python 文件，保存为 durable_once.py 后运行。它只发布一次并继续存活；几秒后再启动订阅者，就能把历史交付与周期性重发区分开。发布者退出后由它维护的瞬态本地缓存也随之失去，不应把此策略当作跨重启数据库。保存地图文件与发布地图消息是两个独立责任。

示例在节点构造中创建深度一的可靠瞬态本地发布者，发布后进入 spin 保持上下文和通信实体存活。生产程序还应根据配置检查资源限制和版本行为；多个历史状态是否有意义取决于业务，而不是深度越大越好。先启动易失订阅者再发送，与晚启动易失订阅者是两个不同实验条件。

#### durable_once.py 完整脚本

代码类型：complete

```python

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String

def main():
    rclpy.init()
    node = Node('durable_once')
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
    publisher = node.create_publisher(String, '/last_state', qos)
    publisher.publish(String(data='configured'))
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()

```

QoSProfile 固定三项关键策略；publisher 变量在 spin 期间保持引用。String 是消息而非裸字符串。脚本没有定时器，因此晚加入收到的 configured 来自历史缓存。

#### 另一终端晚加入

代码类型：commands

```bash

ros2 topic echo /last_state std_msgs/msg/String --qos-durability transient_local --qos-reliability reliable --once

```

明确消息类型可避免依赖类型自动发现；--once 收到一个样本即退出。应在发布者仍运行时执行。

### 把选择写成可以复查的配置说明

对传感器流，可从尽力、易失、小深度开始，再以可接受丢帧率和数据年龄检验；对最新配置，可选可靠、瞬态本地、深度一；对带副作用的服务，通常使用可靠且易失，避免重启后把陈旧请求当作新事务。以上是有条件的起点，最终取舍应写出负载和容许故障，而非只记录一个预设名称。

验收记录至少保留两端策略、发送和接收数量、消息时间戳或序号、观察窗口与失联行为。重连、晚加入、慢消费者三种情况分开测试。频率正常但数据很旧，意味着新鲜度目标仍失败；无丢序号但控制超时，也不能称为业务成功。本章命令与代码用于教学，未在本次内容扩写中实际运行 ROS。

### 为地图和激光分别定义契约

机器人需要让晚打开的界面立即看到已有地图，同时只用近时刻激光做避障。

1. 地图采用可靠、瞬态本地、深度一，保持发布者存活；先发布再打开界面，核查它收到历史地图。

2. 激光采用匹配的尽力订阅及有限深度，记录扫描采样时间与处理时间；人为增加处理耗时，观察数据年龄。

3. 先调整处理能力或丢弃过旧样本，再评估队列；重启地图发布者，验证需要重新加载地图文件。

验收：两类数据分别满足“晚加入能获得状态”和“只使用足够新的观测”，不会用同一个大队列掩盖不同需求。

### 深入练习 1

尽力、瞬态本地发布者能否连接可靠、瞬态本地订阅者？

参考答案：不能。持久性相容，但可靠性请求高于提供能力。应按业务选择提高发布可靠性或降低订阅要求，并重新检查其他策略；只把双方深度改为相同无效。

### 深入练习 2

每秒五十条输入，每次回调五十毫秒，增加深度到一百能否长期不积压？

参考答案：单线程持续处理能力约每秒二十条，低于五十条输入，增加深度只能延后拥塞并增加潜在等待。应降低输入频率、减少回调工作、设计受控并发或明确丢弃策略，然后测量数据年龄和资源使用。

### 深入练习 3

可靠订阅收到速度指令，能否据此断言电机执行成功？

参考答案：不能。收到只是通信证据；还需要驱动反馈或业务确认，以及时间戳、超时和故障处理。可靠传输不等于执行器被调度，也不等于物理设备响应。

### 基础验证流程

用 topic info --verbose 读取两个端点 QoS。

让 best_effort 发布者对接 reliable 订阅者，观察不兼容。

把订阅者改为 best_effort，再观察消息到达。

针对地图、激光与控制状态分别写出 QoS 选择理由。

#### 终端 A：best-effort 发布

```bash

ros2 topic pub /qos_demo std_msgs/msg/String "{data: qos}" --rate 2 --qos-reliability best_effort

```

#### 终端 B：先观察不匹配，再中断并修改

```bash

ros2 topic echo /qos_demo --qos-reliability reliable
# Ctrl+C 后
ros2 topic echo /qos_demo --qos-reliability best_effort

```

#### 端点证据

```bash

ros2 topic info /qos_demo --verbose

```

### 预期结果

- 不匹配组合不传输消息；匹配后收到数据。

- 能从端点输出而非猜测判断 reliability 和 durability。

### 常见问题

- 把 reliable 等同于应用处理“绝不丢数据”。

- 只改 RViz 订阅名称却忽略 QoS。

- 把 SensorDataQoS 的默认深度误记为所有语言的 depth=10。

### 练习

为 30 Hz 图像与一次性地图发布分别设计 QoS，并测试晚加入订阅者。

#### 参考答案

30 Hz 图像可先从 SensorDataQoS（best effort、volatile、有限历史）开始，接受个别帧丢失以控制延迟；地图晚加入者需要历史数据，通常选择 reliable 与 transient_local，并正确配置发布订阅两端。具体 depth 应由消息大小、频率和允许内存确定，再测试延迟与丢失。

### 依据

- [QoS 策略与兼容性](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html)

- [话题检查与调试](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)

- [ros2/examples · jazzy](https://github.com/ros2/examples/tree/jazzy)

## 12. 执行器、回调组与并发边界

执行器取出就绪事件并运行回调。多线程执行器提供线程资源，回调组决定哪些回调允许并发；只换执行器不保证并发。

### 学习目标

- 解释回调为何没有按预期并发

- 设计不会互相阻塞的服务、定时器和订阅

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

执行器取出就绪事件并运行回调。多线程执行器提供线程资源，回调组决定哪些回调允许并发；只换执行器不保证并发。

默认回调组为 MutuallyExclusive。同一互斥组内的回调不能并行；Reentrant 允许重入，应用需要自己保护共享数据。

C++ 和 Python 都支持回调组，但 Python 的 CPU 密集型计算还受解释器执行模型和所用扩展影响。

### 等待集、就绪回调与执行资源

节点创建订阅、服务和定时器后，还需要执行器不断等待事件并调用处理函数。消息进入中间件并不等于订阅回调已经开始；等待线程调度、互斥回调组和共享资源都可能增加延迟。把回调执行拆成“事件就绪、获得执行许可、进入函数、完成工作”，才容易解释频率下降发生在哪里。

单线程执行器每次只能执行一个回调，因此一个耗时一秒的服务会占住这一秒的执行资源。多线程执行器提供多个工作线程，但允许并发的回调才有机会使用它们。调度还受操作系统影响，不能把就绪顺序理解为严格消息先进先出，也不能从线程数量推导确定的截止时间。

### 回调组表达哪些工作可以同时进行

互斥组保证同组回调不同时执行，可用于保护一组共享而不具备线程安全的状态。可重入组允许不同回调并行，也可能让同一个回调的两次调用重叠。不同互斥组之间允许并发，因此“订阅一个组、慢服务一个组”常比把所有东西塞进可重入组更容易推理。

未指定回调组的实体通常进入节点默认互斥组。即使用四线程执行器，如果所有实体都留在该组，这个节点仍会串行执行。创建组后保存为成员，确保其生命周期覆盖相应实体。Python 的线程还受解释器和扩展库执行方式影响：等待网络的任务可能获益，纯 Python 密集计算并不能简单获得与核数等比例的加速。

### 用等待关系识别服务死锁

假设定时器与客户端属于同一互斥组。定时器调用同步服务并等待结果，客户端处理响应所需的回调也要进入这个组；组却被仍在等待的定时器占用，于是形成循环等待。服务端即使早已返回响应，也无法解除客户端内部的阻塞。多加线程不能突破互斥组的许可，所以这个错误经常表现为“服务器有日志，客户端永远不返回”。

优先让定时器发出异步请求后立即返回，再在之后的回调或轮询中处理完成的 future。若确实需要同步等待，等待者与响应处理必须具备可并发的组配置和足够线程，同时不能持有完成路径需要的锁；还需要超时。不要在已由执行器管理的节点回调内递归调用 spin_until_future_complete 来碰运气，这会引入嵌套执行或节点归属问题。

### 完整异步客户端：同一个互斥组也能前进

先在另一个终端运行 demo_nodes_cpp 的 add_two_ints_server，再将以下脚本保存为 async_poll.py 并运行。程序使用一个短定时器维护“空闲或等待”状态：空闲时发请求，等待时只检查 future 是否完成，绝不在定时器里等待网络结果。单线程执行器就能在两次定时器之间处理响应。

这个例子故意不引入多线程，以证明解决死锁首先是解除等待依赖。一次仅保留一个未完成请求，避免服务变慢后积累大量 future。服务不可用时定时器直接返回；超过两秒就移除本地未完成请求记录并报警。移除记录不等于撤销服务端已经开始的操作，因此真实有副作用的请求还必须考虑重复执行与幂等。

#### async_poll.py 完整脚本

代码类型：complete

```python

import time
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts

class AsyncPoll(Node):
    def __init__(self):
        super().__init__('async_poll')
        self.client = self.create_client(AddTwoInts, 'add_two_ints')
        self.pending = None
        self.sent_at = 0.0
        self.timer = self.create_timer(0.2, self.tick)

    def tick(self):
        if self.pending is not None:
            if self.pending.done():
                try:
                    result = self.pending.result()
                    self.get_logger().info(f'sum={result.sum}')
                except Exception as error:
                    self.get_logger().error(str(error))
                self.pending = None
            elif time.monotonic() - self.sent_at > 2.0:
                self.client.remove_pending_request(self.pending)
                self.get_logger().warning('response timeout')
                self.pending = None
            return
        if not self.client.service_is_ready():
            return
        request = AddTwoInts.Request()
        request.a = 7
        request.b = 5
        self.sent_at = time.monotonic()
        self.pending = self.client.call_async(request)

def main():
    rclpy.init()
    node = AsyncPoll()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()

```

tick 的每条路径都快速返回，响应回调因此可以运行；done 只读完成状态，不阻塞。monotonic 用于真实等待超时，不受仿真暂停或系统时钟校正影响。捕获结果异常是为了把服务失败与调度失败分开。

#### 启动依赖与脚本

代码类型：commands

```bash

# 两个终端均先 source /opt/ros/jazzy/setup.bash
# 终端甲
ros2 run demo_nodes_cpp add_two_ints_server
# 终端乙，位于脚本所在目录
python3 async_poll.py

```

运行前需要 demo_nodes_cpp、rclpy 和 example_interfaces。正常可观察到 sum=12；停止服务端后客户端停止发新请求，服务恢复后重新开始。

### 需要并行时如何划分共享状态

并行设计先列出可变数据的读写者。例如订阅回调更新最新传感器快照，定时器读取快照生成输出，慢服务保存诊断文件。可把快照复制和交换放在短临界区，耗时文件操作放在锁外；或者用有界队列让专门工作线程处理。不要为了避免竞争而把整段磁盘写入锁住，否则其它线程仍会被拖住。

必须明确析构顺序：先停止新任务，再唤醒并结束工作线程，最后释放它们引用的数据和 ROS 实体。对成员的引用捕获并不会自动延长对象寿命。线程安全、回调组许可、执行器线程数是三个独立约束；解决了一个并不意味着另外两个自动成立。

### 用时间线给调度问题留下证据

记录回调名称、开始和结束的单调时刻、线程标识、输入序号，并将日志采样或缓冲，避免测量本身主导耗时。比较单线程、同组多线程、分组多线程三个配置，检查长服务期间定时器间隔是否变大。接收频率只是外部现象，进入和退出时间才能说明线程是在计算、等待锁还是没有被调度。

若所有线程都在等待同一锁，应修复锁依赖；若一个组持续被占用，应缩短回调或重新划组；若 CPU 已饱和，应减少工作或改变进程与计算部署。每次只改一项，保留负载和数据集。本章给出的是结构推演与教学代码，未把资料核对冒充目标机器的并发验证。

### 定时发布被慢服务拖住

一个节点每一百毫秒发布一次状态，同时服务请求需要一秒磁盘操作。

1. 先用单线程记录状态回调间隔，确认磁盘操作期间出现长间隙。

2. 换多线程但保持默认互斥组，预期仍不能同时执行两种回调。

3. 把慢服务放入独立互斥组，保持状态组短小，并在共享快照上使用短临界区；再次测量时间线。

验收：分组且存在空闲执行线程后，两种回调允许重叠；是否达到一百毫秒目标仍由实测抖动、负载与锁等待决定。

### 深入练习 1

客户端和定时器在同组，增加到八个线程为何仍可能死锁？

参考答案：定时器等待响应而占住互斥组，处理响应的回调无法获得同一组许可。线程空闲也无助于解除循环。应使发起回调返回，或者在正确的不同组配置与足够线程下设置有界等待，并检查锁依赖。

### 深入练习 2

把两个回调放进可重入组后，计数偶尔减少，如何判断？

参考答案：先检查两个回调是否读出同一旧值再各自写回，造成更新覆盖；也检查同一回调是否重入。用锁、原子操作或单一写入者保护更新，再验证吞吐和延迟。可重入只允许调度，不保证共享数据安全。

### 深入练习 3

异步客户端为什么仍要限制未完成请求数量？

参考答案：异步解决阻塞，不会限制请求增长。服务长期变慢时，无界 future 会消耗内存并让结果过时。应设置在途数量、超时和重试规则；本章一次一条最容易验证，且超时后不能假设服务端停止执行。

### 基础验证流程

先用单线程执行器观察长回调对定时器的影响。

为独立的订阅和服务建立不同回调组并保存引用。

换为 MultiThreadedExecutor，检查延迟是否改善。

用线程安全队列或锁保护共享状态，并为同步等待绘制依赖关系。

#### 观察现象而非仅看线程数

```bash

ros2 topic hz /chatter
ros2 topic info /chatter --verbose

```

#### 阅读对应官方最小源码

```bash

# 对照 ros2/examples 的 rclcpp/executors 与 rclpy/executors 目录；代码按 Jazzy 分支阅读。

```

### 预期结果

- 能够指出哪个回调组允许并发，哪个资源需要同步。

- 服务响应不会因同组回调阻塞而永久等待。

### 常见问题

- 在同一互斥组里进行同步服务等待。

- 忘记保存回调组对象引用。

- 把回调开始顺序当作严格 FIFO 或实时调度保证。

### 练习

给一个 100 ms 的定时器和 1 秒的服务处理添加时间日志，比较执行器与回调组的组合。

#### 参考答案

单线程下长服务回调会推迟定时器；多线程但同一默认互斥组也不能并发；多线程配不同互斥组或合适的 Reentrant 组后允许并发。记录回调进入/退出的 steady 时间与线程 ID，比较定时器抖动，并对共享状态加保护。

### 依据

- [执行器概念](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html)

- [回调组及死锁规避](https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html)

- [同步与异步服务调用](https://docs.ros.org/en/jazzy/How-To-Guides/Sync-Vs-Async.html)

## 13. 生命周期节点与启动顺序

生命周期节点有 unconfigured、inactive、active、finalized 等主要状态。configure/activate 等转换触发对应回调。

### 学习目标

- 把初始化、运行、停用和清理分开

- 按状态组织可控的驱动启动过程

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

生命周期节点有 unconfigured、inactive、active、finalized 等主要状态。configure/activate 等转换触发对应回调。

驱动可在 configure 分配资源，在 activate 开始对外工作，在 deactivate 停止输出，再由 cleanup 释放资源。状态机提供协议，具体行为仍由节点实现。

### 把进程存在与业务就绪分开

一个驱动进程能够出现在节点列表里，不代表设备已经打开、标定已经加载或数据值得使用。生命周期把这些准备和运行阶段暴露为可查询的协议，使启动管理器能够先验证资源，再允许主功能输出。对于依赖相机、定位和控制器的系统，这比猜测启动需要几秒更可控。

主要状态包括未配置、未激活、激活和终结；转换过程还有配置中、激活中、停用中、清理中及错误处理等中间状态。外部管理者请求转换，节点执行相应回调并报告结果。状态机提供合法路径和接口，设备操作的具体顺序、失败后资源如何恢复，仍需要实现者明确设计。

### 状态转换应遵守资源的所有权

未配置状态应允许设置和检查配置；configure 成功后进入 inactive，此时资源准备好但主功能还没运行；activate 成功进入 active；deactivate 成功回到 inactive；cleanup 成功回到 unconfigured。finalized 是终结状态，不能再原地 configure，通常由进程管理器销毁并重新创建实例。

以串口传感器为例，配置阶段校验参数、打开串口并加载标定，激活阶段启动采样；停用阶段停止采样和输出，清理阶段关闭串口并释放缓冲。把耗时初始化集中在配置阶段，能让启动管理者区别“准备慢”与“运行异常”。资源申请成功后才更新成员状态，失败路径释放已取得的部分资源，避免重试时重复占用设备。

- 合法常见顺序：unconfigured → configure → inactive → activate → active。

- 可重配顺序：active → deactivate → inactive → cleanup → unconfigured，再重新配置。

- 一次状态转换返回成功后，仍应检查输入新鲜度、输出有效性和设备状态；状态标签不是传感器质量报告。

### 在官方演示中逐步观察状态与消息

本实验需要 lifecycle 演示包。终端甲运行 lifecycle_talker，终端乙持续观察 lifecycle_chatter，终端丙按顺序请求转换。每一步后都读取状态，并等几秒观察是否有新消息。不要同时运行自动切换状态的 lifecycle_service_client，否则它会与手工命令争用状态机，使观察结果难以解释。

这个演示最有价值的细节是：配置后已经创建普通定时器，inactive 时定时器仍可能执行，只是生命周期发布者不发送消息。因而日志显示“publisher inactive”并不说明停用失败。它说明生命周期发布者的输出门控与普通回调的调度是不同机制；需要停止耗时采样的驱动应主动取消定时器或阻止采样工作。

#### 三个终端的分步实验

代码类型：commands

```bash

# 如未安装演示包，在学习机执行一次
sudo apt install ros-jazzy-lifecycle
# 所有终端均先执行
source /opt/ros/jazzy/setup.bash
# 终端甲
ros2 run lifecycle lifecycle_talker
# 终端乙
ros2 topic echo /lifecycle_chatter std_msgs/msg/String
# 终端丙：每次转换后观察终端甲乙，再执行下一步
ros2 lifecycle get /lc_talker
ros2 lifecycle set /lc_talker configure
ros2 lifecycle get /lc_talker
ros2 lifecycle set /lc_talker activate
ros2 lifecycle get /lc_talker
ros2 lifecycle set /lc_talker deactivate
ros2 lifecycle get /lc_talker
ros2 lifecycle set /lc_talker cleanup
ros2 lifecycle get /lc_talker

```

configure 后应为 inactive，activate 后应为 active，deactivate 后为 inactive，cleanup 后为 unconfigured。echo 是持续运行的观察者；消息是否新增与 get 返回状态共同构成证据。示例激活回调本身有演示性等待，因此命令响应不一定立即完成。

### 失败返回、异常与恢复不是同一条路径

配置回调返回 FAILURE 表示本次配置没有成功，正常回到未配置状态；返回 ERROR 或未捕获异常会进入错误处理流程。激活回调返回 FAILURE 则回到 inactive。程序应把预期的可恢复失败，例如端口暂不可用，与内部状态已经不可信的错误区分开，日志写明具体阶段、设备与恢复建议。

进入错误处理后要执行必要的停止和清理，根据实现的返回结果决定能否回到未配置状态；不能假设任何错误都会自动恢复。转换回调若无限等待，管理请求也可能一直挂起。应对设备等待设置有界超时，并定义超时后已申请资源的归属。外部管理器重试前先重新读取状态，而不是重复发送上一条命令。

### 按依赖关系组织一组节点

假设定位依赖里程计和激光，导航又依赖定位。启动管理者可先配置所有必要资源，再激活上游输入，确认其数据与 TF 可用，之后激活下游算法。这里的“确认”应该检查实际主题、频率、坐标关系与时间，而不只是节点名存在。静态地图已经加载但地图发布者尚未提供历史，也可能让下游等待。

停用时常需要先阻止下游产生新动作，再停止上游数据源，最后清理资源；具体顺序由系统依赖决定。对驱动的停止行为必须在驱动层实现，不能把切换 lifecycle 状态本身当作物理急停。普通订阅、服务、后台线程和非生命周期发布者不会仅因继承了 LifecycleNode 就全部自动受控。

### 用状态、行为与资源三类证据验收

状态证据来自 lifecycle get 和转换事件；行为证据来自新增消息、设备访问和业务反馈；资源证据来自线程结束、文件关闭和再次配置成功。三者需要一致。例如 inactive 后还出现新采样说明采样门控可能遗漏；cleanup 后再次 configure 报端口占用，说明释放路径不完整。只检查日志中出现“成功”容易漏掉这些问题。

测试至少覆盖完整往返、配置失败再重试、激活失败、运行中停用，以及终结后的管理行为。测试可先使用假设备，注入打开失败和读取超时，避免依赖真实硬件才能发现状态管理缺陷。状态图和具体行为应随实现一起更新。本章依据 Jazzy 演示源码解释状态与定时器行为，未执行真实设备操作。

### 相机驱动可重试配置

相机第一次打开失败，第二次恢复，要求整个导航系统不能提前消费无效图像。

1. 驱动 configure 尝试打开相机，失败时释放部分资源并返回 FAILURE，状态保持 unconfigured；管理器记录原因。

2. 恢复设备后再次 configure，成功进入 inactive，校验标定与帧名称，然后 activate 并观察带正确时间戳的图像。

3. 只有图像和所需 TF 有效后才启动依赖算法；停用时先阻止下游动作，再停相机采样并 cleanup。

验收：恢复依赖于明确的状态与数据证据，重复配置不会遗留第二条采样线程或占用旧设备句柄。

### 深入练习 1

unconfigured 能否直接 activate？

参考答案：不能，必须先 configure 成功进入 inactive，再请求 activate。若命令被拒绝，应查询当前状态与可用转换，不要通过延长 sleep 绕开状态约束。

### 深入练习 2

inactive 时仍看到定时器日志，是否违反生命周期？

参考答案：不一定。普通定时器仍可能运行，生命周期发布者只限制消息发送。应根据节点合同判断是否需要取消定时器、停止后台线程或屏蔽处理；不能用状态名推断所有实现行为。

### 深入练习 3

cleanup 后重新配置失败，错误为设备已被占用，该查什么？

参考答案：检查停用是否停止并等待采样线程、清理是否关闭设备句柄，以及配置失败路径是否释放此前资源。先查实际占用进程和线程，再核对状态。仅重启管理器不会修复节点内部泄漏。

### 基础验证流程

启动官方 lifecycle_talker。

先读取状态，再 configure 和 activate。

观察 inactive 与 active 时消息行为的差异。

设计设备初始化失败时的错误返回和重新尝试流程。

#### 终端 A：官方演示节点

```bash

ros2 run lifecycle lifecycle_talker

```

#### 终端 B：操作状态机

```bash

ros2 lifecycle get /lc_talker
ros2 lifecycle set /lc_talker configure
ros2 lifecycle set /lc_talker activate
ros2 lifecycle set /lc_talker deactivate
ros2 lifecycle set /lc_talker cleanup

```

### 预期结果

- 能按合法转换顺序进入 active 再返回 unconfigured。

- 理解“节点进程存在”与“节点已激活工作”不同。

### 常见问题

- 对 unconfigured 节点直接 activate。

- 把普通 publisher 当作会自动遵守所有生命周期状态。

- 在转换回调里无期限等待设备，拖住系统 bringup。

### 练习

为一个虚拟温度传感器定义每个状态下允许的操作，并添加初始化失败分支。

#### 参考答案

unconfigured 只接受配置；configure 建立传感器资源，失败返回失败状态并保留明确日志；inactive 资源就绪但停止主输出；activate 开始采样，deactivate 停止采样；cleanup 释放资源。再次 configure 前应确保旧资源已清理；错误处理不能留下后台线程继续输出。

### 依据

- [官方 Lifecycle 演示说明](https://github.com/ros2/demos/blob/jazzy/lifecycle/README.rst)

- [ros2/demos · jazzy](https://github.com/ros2/demos/tree/jazzy)

## 14. 组件化、独立进程与进程内通信

rclcpp_components 可把注册好的 C++ 节点共享库加载到容器中；独立进程更容易隔离崩溃，组合部署减少进程开销。

### 学习目标

- 用同一节点功能选择不同部署方式

- 理解组件化和零拷贝是不同问题

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

rclcpp_components 可把注册好的 C++ 节点共享库加载到容器中；独立进程更容易隔离崩溃，组合部署减少进程开销。

C++ 组件构造函数接收 NodeOptions，并通过注册宏和 CMake 声明可加载插件。Python 多节点执行器不等同于此 C++ 动态组件机制。

同进程部署不自动保证零拷贝；还需考虑 intra-process 选项、消息所有权、订阅数量和 RMW 能力。

### 节点边界与进程边界可以独立选择

ROS 节点是接口和功能的组织单位，操作系统进程是内存及故障隔离单位。两个节点可以位于两个进程，也可以位于同一个进程；主题名称和消息合同不必因此改变。组合部署适合数据交换频繁、希望减少进程间开销的模块，独立进程则更容易单独重启并限制一次崩溃的影响范围。

组件化把 C++ 节点实现编译为共享库，由容器加载并把节点加入执行器。它改变部署方式，不自动改变算法、QoS 或回调组，也不承诺速度一定更快。若图像链路传输成本很小而算法计算占主要时间，组合后总体收益可能有限；应先量出真正的瓶颈。

### 一个可加载组件需要哪些组成部分

节点类必须能接收 NodeOptions，并把它传给基类构造函数，使容器提供的参数、名称、命名空间及进程内通信选项真正生效。注册宏让共享库暴露节点工厂，构建系统的注册命令把插件类型写入可发现的资源索引。这两部分缺一不可：库能编译不代表 ros2 component types 能看到它。

下面建立一个最小 ament_cmake 包，依赖由 ros2 pkg create 写入 package.xml。把节点源码与完整 CMakeLists.txt 保存到标注位置再构建；生成的独立可执行入口与动态组件使用同一个类。不要在组件构造函数里调用 spin，也不要让构造函数无限等待硬件，否则加载服务会被阻塞。

#### 创建包：在新工作空间根目录执行

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
mkdir -p src
cd src
ros2 pkg create hub_component --build-type ament_cmake --dependencies rclcpp rclcpp_components std_msgs

```

该命令生成 package.xml 和目录骨架；下一段源码保存为 src/hub_component/src/talker.cpp，CMake 内容替换该包现有 CMakeLists.txt。这里的 src 路径均相对工作空间根目录。

#### src/hub_component/src/talker.cpp

代码类型：complete

```cpp

#include <chrono>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_components/register_node_macro.hpp"
#include "std_msgs/msg/string.hpp"

namespace hub {
class Talker : public rclcpp::Node {
public:
  explicit Talker(const rclcpp::NodeOptions & options)
  : Node("hub_talker", options) {
    publisher_ = create_publisher<std_msgs::msg::String>("chatter", 10);
    timer_ = create_wall_timer(std::chrono::seconds(1), [this]() {
      auto message = std::make_unique<std_msgs::msg::String>();
      message->data = "component ready";
      publisher_->publish(std::move(message));
    });
  }
private:
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};
}
RCLCPP_COMPONENTS_REGISTER_NODE(hub::Talker)

```

构造函数只建立通信实体并返回；成员引用保持发布者与定时器存活。unique_ptr 表达消息所有权转移，为支持的进程内路径提供优化条件；宏注册的全限定类名必须与 CMake 和加载命令一致。

#### src/hub_component/CMakeLists.txt

代码类型：complete

```text

cmake_minimum_required(VERSION 3.8)
project(hub_component)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(std_msgs REQUIRED)
add_library(hub_talker SHARED src/talker.cpp)
target_compile_features(hub_talker PUBLIC cxx_std_17)
ament_target_dependencies(hub_talker rclcpp rclcpp_components std_msgs)
rclcpp_components_register_node(hub_talker
  PLUGIN "hub::Talker"
  EXECUTABLE hub_talker_node)
install(TARGETS hub_talker
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin)
ament_package()

```

SHARED 创建可动态加载的库；注册命令同时生成资源索引和独立入口 hub_talker_node。安装规则把运行所需的库放入 install，避免只能在 build 目录偶然运行。代码块用 text 标注 CMake 文本。

### 加载、查看与卸载应使用实际标识

在工作空间根目录构建后，每个新终端先加载 install/setup.bash。组件类型是 hub::Talker，包名是 hub_component，默认节点名是 hub_talker，容器管理节点名是 ComponentManager；它们承担不同角色，不应相互替换。加载返回的数字是容器内组件标识，卸载时应采用本次实际返回值。

卸载会销毁组件实例，之后该节点应从图中消失，其他组件仍可继续运行。若组件自行创建线程，应在析构时正确停止和回收它们，否则卸载可能阻塞或访问已释放内存。动态卸载不是处理任意崩溃的隔离机制，同一进程内错误仍可能导致整个容器退出。

#### 构建并加载组件

代码类型：commands

```bash

# 工作空间根目录
colcon build --packages-select hub_component
source install/setup.bash
ros2 component types
# 终端甲，已 source 同一 install/setup.bash
ros2 run rclcpp_components component_container
# 终端乙，已 source 同一 install/setup.bash
ros2 component load /ComponentManager hub_component hub::Talker
ros2 component list
ros2 topic echo /chatter std_msgs/msg/String
# echo 结束后，只有上面的 list 显示 ID 为 1 时才用此示例 ID
ros2 component unload /ComponentManager 1

```

types 检查安装与注册，load 检查实际装载，list 给出容器与实例 ID，echo 检查业务输出。每层分别验证能够缩小“包存在但组件不能运行”的原因范围。

### 选择执行器并显式开启进程内通信

默认 component_container 使用单线程执行器，多个节点的回调仍可能彼此阻塞。component_container_mt 提供多线程执行器，最终并发仍受各节点回调组约束。将独立节点迁入容器时，如果原来的 main 选择了多线程，现在也必须在容器层保留合适配置，不能只删掉 main 就认为运行语义完全相同。

下面的完整 launch 文件使用官方 composition 示例，在一个多线程容器中装入发布者和订阅者，显式开启进程内通信。extra_arguments 属于组件装载选项，和节点参数 parameters 不同。应在使用此文件前安装 composition 与 launch_ros，并保存为本地 pair.launch.py；可以直接 ros2 launch ./pair.launch.py 运行。

#### pair.launch.py 完整文件

代码类型：complete

```python

from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

def generate_launch_description():
    container = ComposableNodeContainer(
        name='pair_container', namespace='',
        package='rclcpp_components', executable='component_container_mt',
        output='screen',
        composable_node_descriptions=[
            ComposableNode(package='composition', plugin='composition::Talker',
                           name='talker',
                           extra_arguments=[{'use_intra_process_comms': True}]),
            ComposableNode(package='composition', plugin='composition::Listener',
                           name='listener',
                           extra_arguments=[{'use_intra_process_comms': True}]),
        ])
    return LaunchDescription([container])

```

两个描述创建两个节点实例但共享容器进程；相同的选项分别传给双方。此文件展示部署配置，不应与上一实验中尚在运行的同名话题发布者混用。

### 为何同一进程不等于任何情况都零拷贝

进程内路径可以减少序列化和复制，但实际行为依赖消息所有权、订阅回调签名、订阅者数量和是否还存在进程外消费者。一个独占消息面对多个需要各自修改的数据处理者，不可能简单让所有人同时拥有唯一所有权。混合订阅时还可能需要为中间件保留另一条传输路径。

DDS 共享内存和借用消息属于另外的机制，还受所选中间件、消息类型及支持能力约束。打开 use_intra_process_comms 不能证明它们也打开了。实验中比较延迟、CPU、分配和复制证据，比把所有优化统称为零拷贝更有意义；即使优化确实减少复制，也不能由此推出硬实时保证。

### 按插件、调度与故障三个层次排错

找不到类型时检查包前缀、注册类名、共享库安装和新终端 overlay；类型可见却加载失败时检查构造异常、缺少共享依赖和重复节点配置；节点存在却不输出时再查执行器、回调组、话题重映射和 QoS。不要用更换容器一次同时掩盖注册与通信问题。

部署取舍应记录故障范围、升级频率、消息负载与性能结果。可把同属一条图像流水线的组件组合，同时把不稳定第三方驱动放在独立进程；这是工程选择，不是必须全部合并的原则。本章源码为完整教学示例，构建和时延结论需在目标 Jazzy 环境执行后确认。

迁移后还应比较两种部署的外部合同：完整节点名、话题类型、参数值、启动失败和退出行为。特别检查使用相对名称的组件是否获得预期命名空间。只有外部行为一致，独立进程与容器之间的性能比较才是在比较同一个系统。

### 把一条图像处理链迁入容器

现有采集、滤波、检测三节点独立运行，怀疑大型图像复制导致开销。

1. 先固定图像大小、频率、订阅者数量，记录原布局下的延迟分布与资源使用。

2. 逐个把类改为 NodeOptions 构造并完成注册，先保持原 QoS 和算法验证输出一致。

3. 选择适合回调组的容器，开启进程内选项，再加入和移除进程外观察者，分别测量。

验收：只有输出合同仍满足且测量显示收益，才把该布局作为部署选择；还需接受一个组件崩溃可能带走整条链的故障范围。

### 深入练习 1

component types 能看到类型，但 node list 看不到节点，是否异常？

参考答案：不一定。types 只说明已安装的资源索引包含该组件类型，尚未证明实例已经加载。应启动容器并执行 load，检查其响应，再看 list 和节点图。

### 深入练习 2

删去 main 后原来并行的节点开始阻塞，优先查什么？

参考答案：检查 main 原先的执行器类型和回调组设置是否在组件容器中保留。默认单线程容器可能改变调度；换成多线程容器后仍需确保相关回调组允许并发。

### 深入练习 3

同进程且开启进程内选项，能否断言没有任何复制？

参考答案：不能。需要结合消息所有权、订阅数量、回调签名、跨进程消费者与传输机制判断，并以测量或追踪佐证。进程内选项不等于 DDS 共享内存或借用消息支持。

### 基础验证流程

列出已经注册的组件类型。

启动容器，动态加载 Talker 与 Listener。

查询容器与组件 ID，再按 ID 卸载一个组件。

把自己的节点转换成接收 NodeOptions 的可组合类。

#### 终端 A：启动容器

```bash

ros2 run rclcpp_components component_container

```

#### 终端 B：加载与检查

```bash

ros2 component types
ros2 component load /ComponentManager composition composition::Talker
ros2 component load /ComponentManager composition composition::Listener
ros2 component list

```

### 预期结果

- 一个容器进程中出现多个节点并收发消息。

- 知道组件 ID 与 ROS 节点名称是不同标识。

### 常见问题

- 认为多个节点在同一容器里就必定并行。

- 忘记注册、安装或导出共享库，导致 component types 找不到类型。

- 未经测量即宣称所有消息实现零拷贝。

### 练习

比较两个独立 demo 进程与一个容器的启动方式，记录优缺点并注明尚未实测的性能假设。

#### 参考答案

独立进程启动简单，故障隔离较强，通信需要跨进程；组件容器可动态加载并探索进程内优化，但一个进程的崩溃可能影响全部组件。线程模型由容器执行器与回调组决定。只有实测后才能比较 CPU、内存和延迟，不能仅凭进程数量给出性能结论。

### 依据

- [在一个进程里组合节点](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html)

- [把 C++ 节点写成组件](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-a-Composable-Node.html)

- [执行器概念](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html)

## 15. ROS 时间、录包与可重复实验

ROS time 可由 /clock 驱动；use_sim_time 是节点参数。系统时间和 steady time 适用于不同目的，不应把所有时间差都来自同一种时钟。

### 学习目标

- 让仿真、回放与节点共享一致的时间基准

- 用 rosbag2 固定输入重现算法问题

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

ROS time 可由 /clock 驱动；use_sim_time 是节点参数。系统时间和 steady time 适用于不同目的，不应把所有时间差都来自同一种时钟。

bag 保存消息与元数据，回放会重新发布数据。录制时应考虑 /tf、/tf_static、传感器与配置上下文。

记录数据不会自动记录整个系统的运行逻辑；重现结果还依赖代码版本、参数与时间配置。

### 三种时钟分别回答不同问题

系统时间用于与真实日期和其它主机对齐，但校时可能让它跳变；单调时间用于本机经过多久的测量，适合设备超时和性能计时；ROS 时间用于把算法放在真实运行、仿真或回放的共同时间轴。选择时钟首先看问题：传感器观测属于哪个时刻，与等待串口还剩多少时间，不一定使用同一种时钟。

节点启用 use_sim_time 后，其 ROS 时间由 /clock 驱动。这个参数是逐节点设置的，一个节点启用不会自动替整个图启用。在尚未收到时钟时 ROS 时间可能为零；暂停或向后跳转也属于可能行为。依赖时间差的积分器、滤波缓存和超时逻辑必须定义如何处理零值与回退，不能默认时间永远递增。

### 把消息时间与录制时间区别开

带 Header 的消息可以保存原采样时间，bag 还会记录用于组织播放时序的时间。通常录制时间来自录制节点收到消息时的时钟，而非自动解析每种消息内部的 Header；传感器先采样再经网络到达，两者本来就可能不同。读取 bag 元数据中的起止时间，不能直接推导所有传感器的实际同步精度。

仿真录制使用 --use-sim-time 时，录制器用收到的 /clock 更新记录时间；在第一条 /clock 之前不会写消息，以避免零时间与正常仿真时间混在一起。应同时保存消息内时间、时钟配置和必要的 TF。多机真实数据还需要校时记录，否则回放虽然能重发原数据，也会保留当时已经存在的时间不一致。

### 录制一个有明确输入输出的最小实验

安装 turtlesim 和 rosbag2 后，在独立实验域中启动 turtlesim。先启动录制，再启动速度发布者，使包里包含命令和实际姿态；持续数秒后依次停止发布者与录制器，用 bag info 检查类型、数量和时长。记录命令不等于记录运动结果，因此同时保存姿态有助于区分输入缺失和模型行为差异。

回放前将海龟重置到初始状态，停止所有实时速度发布者。本次只播放 cmd_vel，保留当前模拟器作为 pose 的唯一来源；若同时重放原 pose，会在同一主题混入录制轨迹与新轨迹。比较两次姿态时需区分主题或保存独立结果，不能把观察到任意姿态消息当作重现成功。

#### 按终端分别运行的录制与回放步骤

代码类型：commands

```bash

# 所有终端先加载 Jazzy 环境并使用同一实验域
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
# 终端甲
ros2 run turtlesim turtlesim_node
# 终端乙：目录 turtle_trial 必须尚不存在
ros2 bag record -o turtle_trial --topics /turtle1/cmd_vel /turtle1/pose
# 终端丙：运行约十秒后 Ctrl+C
ros2 topic pub /turtle1/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}' --rate 2
# 终端乙 Ctrl+C 停止录制后，在该目录检查
ros2 bag info turtle_trial
# 已停止实时速度发布者，再重置与回放
ros2 service call /reset std_srvs/srv/Empty '{}'
ros2 bag play turtle_trial --topics /turtle1/cmd_vel

```

record 订阅并保存指定主题；info 检查实际录到什么；reset 恢复起点；play 的主题筛选避免旧姿态与新姿态竞争。该实验演示数据重放，不保证 GUI 模拟器在不同调度负载下逐浮点数完全一致。

### 让消费算法与回放共享时间轴

对定位等依赖时间戳的算法，应在启动配置里把所有相关消费者的 use_sim_time 设为 true，并选一个 /clock 来源。使用 bag play --clock 时由播放器产生时钟；若仿真器仍同时发 /clock，应停用其中一个。Jazzy 播放器在该模式下排除包中原 /clock 的重放，但不能替你停止外部仿真器的时钟。

下面完整探针故意用单调时钟触发打印，输出的却是节点 ROS 时间。保存为 clock_probe.py，带 use_sim_time 参数运行后，即使回放暂停或没有 /clock，探针仍能打印并揭示 ROS 时间停在哪里。若探针本身也采用暂停的 ROS 定时器，恰好会失去观察“时钟暂停”的能力。

#### clock_probe.py 完整脚本

代码类型：complete

```python

import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType

def main():
    rclpy.init()
    node = Node('clock_probe')
    steady = Clock(clock_type=ClockType.STEADY_TIME)
    timer = node.create_timer(
        1.0, lambda: node.get_logger().info(
            f'ros_time_ns={node.get_clock().now().nanoseconds}'),
        clock=steady)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_timer(timer)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()

```

单调时钟只负责一秒一次的观察节奏；node.get_clock 返回节点选定的 ROS 时钟。两种时钟用于不同目的，不在同一个时间差公式中相减。

#### 探针与播放器分别在两个终端运行

代码类型：commands

```bash

python3 clock_probe.py --ros-args -p use_sim_time:=true
# 另一终端，使用已录好的包
ros2 bag play turtle_trial --clock --rate 0.5 --topics /turtle1/cmd_vel

```

先运行探针且没有时钟来源时可看到未初始化时间；播放器开始后时间推进，半速回放使包内时间相对墙钟更慢。若回放速度提高，消费算法也必须有足够计算能力。

### QoS、静态 TF 与不完整录包

录制器也是订阅者，播放器也是发布者，因此同样受 QoS 相容性限制。自动推导通常能覆盖常见情况，但对特殊策略或晚加入静态数据，应检查实际端点及包中的数量。若 /tf_static 没录到，回放时图上可能只剩动态链；要么录到原静态消息，要么按原标定启动唯一的静态来源。

下面 YAML 展示一个主题的显式覆盖，保存为 bag_qos.yaml。它让静态 TF 的录制订阅请求可靠、瞬态本地的有限历史，前提是原发布者确实提供匹配策略。覆盖文件只解决匹配与缓存请求，不会自动重建已经丢失的数据，也不会修正错误的传感器 frame_id。

#### bag_qos.yaml

代码类型：complete

```yaml

/tf_static:
  history: keep_last
  depth: 10
  reliability: reliable
  durability: transient_local

```

顶层是完整主题名，下面是对应策略。这里深度十仅为教学选择，实际应结合静态发布者组织方式和资源需求确定。

#### 为现有机器人数据使用覆盖配置

代码类型：commands

```bash

ros2 bag record -o localization_trial --qos-profile-overrides-path bag_qos.yaml --topics /scan /odom /tf /tf_static

```

前提是这些主题已由待调查系统发布，且输出目录未存在。仿真数据还应给录制器加 --use-sim-time，并确认 /clock 正常到达。

### 把可重现条件作为录包的一部分保存

一份可复查实验还包括代码提交、软件版本、参数文件、地图、标定、启动命令、时钟来源与初始状态。bag 只保存选定数据，不会自动把动态加载的参数、随机种子、设备固件和外部文件都封存。若算法读取当前系统时间或访问未记录网络服务，即使输入主题相同也可能产生不同输出。

排错顺序是先确认消息存在且数量合理，再检查回放端点 QoS 与唯一发布来源，之后检查时钟和 TF，最后比较算法输出。循环播放和跳转可能让时间向后，需要清空或重置有历史状态的算法；不要把第二轮残留状态与第一轮比较后误判随机性。本章命令经过资料核对，未在此次写作中实际采集录包。

### 复现一次定位跳变

已有一次实机定位跳变，需要在离线机器上判断是扫描输入、TF 还是参数导致。

1. 保存扫描、里程计、动态与静态 TF、定位输出以及参数和地图快照，记录各主机校时状态。

2. 离线启动算法并统一 use_sim_time，只保留播放器时钟与录制输入；避免同时启动原驱动。

3. 先单次慢速回放，记录跳变前后的消息时间与变换范围；再只改变一个参数并保存输出到另一个主题或包。

验收：对照能够把输入不完整、时间基准错配和算法行为区分开；重发消息成功本身不足以证明问题已复现。

### 深入练习 1

启用 use_sim_time 后程序没有进展，第一步检查什么？

参考答案：检查 /clock 是否存在并更新，以及该节点是否真的启用了参数。没有收到时钟时 ROS 时间可能为零；若使用 ROS 定时器，它也可能不触发。用单调时钟探针观察可以避免自身被暂停。

### 深入练习 2

录了 pose 和 cmd_vel，为什么重放 pose 会干扰运动验收？

参考答案：模拟器本身也发布当前 pose，同主题会同时出现原记录和新结果。应只回放输入命令，或把原输出重映射到参考主题，再比较两条来源清晰的轨迹。

### 深入练习 3

把回放速度改为两倍是否会把消息 header.stamp 数值也乘二？

参考答案：不会按这种方式缩放原始消息内容。播放器改变发布调度，并可推进对应回放时钟；Header 通常仍是原观测时间。消费算法须使用同一时间轴，并处理更高的实际输入负载。

### 基础验证流程

在 turtlesim 中录制控制话题。

停止录制并检查消息数量和时长。

停止键盘输入，重置场景后回放。

对使用时间戳的算法明确 use_sim_time，并由回放提供 /clock。

#### 录制：turtlesim 与键盘节点已运行

```bash

ros2 bag record -o turtle_session /turtle1/cmd_vel /turtle1/pose

```

#### 停止录制后检查与回放

```bash

ros2 bag info turtle_session
ros2 bag play turtle_session

```

#### 对依赖仿真时间的重放系统

```bash

ros2 bag play turtle_session --clock
# 消费节点须配置 use_sim_time=true；勿同时启动竞争的 /clock 发布者。

```

### 预期结果

- 能查看录包包含的类型、数量和持续时间。

- 同一输入可重复用于调试，时间基准有明确来源。

### 常见问题

- 启用 use_sim_time 却没有 /clock，导致 ROS 时间不推进。

- 回放和实机驱动同时发布同名传感器数据。

- 以为重放速度改变后所有外部设备行为也会同步改变。

### 练习

为一次定位故障写录包清单：必需话题、参数快照、代码提交和时钟设置。

#### 参考答案

清单至少包含相关传感器话题、/tf、/tf_static，以及定位输出和诊断；另保存参数 YAML、地图/标定、Git 提交、ROS 发行版与软件包版本。记录使用真实时间还是 /clock；回放时停止竞争输入源，统一消费者 use_sim_time，并明确采用哪个 /clock 发布者。

### 依据

- [rosbag2 录制与回放](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html)

- [ROS 时间设计](https://design.ros2.org/articles/clock_and_time.html)

- [QoS 策略与兼容性](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html)

## 16. 测试、诊断与持续集成

纯算法适合用 gtest/pytest 做输入输出测试；节点连接、进程退出和话题行为适合 launch_testing 等集成测试。

### 学习目标

- 把算法测试和节点集成测试分层

- 用可重复证据判断构建是否可用

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

纯算法适合用 gtest/pytest 做输入输出测试；节点连接、进程退出和话题行为适合 launch_testing 等集成测试。

构建成功不等于测试成功；colcon test 启动测试后，还应检查 test-result。

诊断工具提供环境线索，不能替代业务验收。测试环境要记录发行版、依赖和参数。

### 测试从可观察合同出发

先写系统应在什么输入下产生什么结果，再选择测试工具。纯算法测试验证数值和边界，节点测试验证消息类型、参数和错误处理，集成测试验证多进程连接、就绪和退出。构建成功只能证明某些源码经过编译与链接，不能证明接口连接正确，更不能证明超时路径真正工作。

例如“命令停止更新后输出归零”至少包含新命令可用、过期判定、边界时刻、没有任何命令和时间异常五类情况。如果测试只重复给新命令并观察非零输出，即使通过，也没有覆盖最重要的停止条件。把计算策略从 ROS 回调中分离，可以用可控时间直接验证，而不必等待真实半秒反复试验。

### 用注入时间验证明确的边界

下方两个完整文件保存到同一目录。策略函数接收命令、最后接收时刻、当前时刻和超时界限；时间单位全部为纳秒。约定恰好达到界限仍有效，超过界限才归零；负年龄表示时间基准异常，也返回零。这里验证的是教学输出策略，不是完整车辆制动或功能安全方案。

测试使用整数时刻而不依赖真实 sleep，所以运行快且没有调度随机性。新鲜、恰好到边界、超出一个纳秒、未来时刻和缺失输入分别对应独立断言。有限值检查防止无穷和非数值进入后续计算；真实应用还应按自身合同限制幅值，并明确非法参数是拒绝启动还是返回错误。

#### policy.py 完整文件

代码类型：complete

```python

import math

def select_output(speed, last_seen_ns, now_ns, timeout_ns):
    if timeout_ns <= 0:
        raise ValueError('timeout must be positive')
    if last_seen_ns is None or not math.isfinite(speed):
        return 0.0
    age = now_ns - last_seen_ns
    if age < 0 or age > timeout_ns:
        return 0.0
    return speed

```

时间来自函数参数，函数没有访问系统时钟或 ROS 状态。这样测试可精确控制边界，运行节点则负责把同一时钟来源的时刻传入。

#### test_policy.py 完整文件

代码类型：complete

```python

import pytest
from policy import select_output

def test_fresh_command():
    assert select_output(0.4, 100, 150, 100) == 0.4

def test_timeout_boundary():
    assert select_output(0.4, 100, 200, 100) == 0.4
    assert select_output(0.4, 100, 201, 100) == 0.0

def test_missing_future_and_nonfinite():
    assert select_output(0.4, None, 150, 100) == 0.0
    assert select_output(0.4, 200, 150, 100) == 0.0
    assert select_output(float('nan'), 100, 150, 100) == 0.0

def test_invalid_timeout():
    with pytest.raises(ValueError):
        select_output(0.4, 100, 150, 0)

```

四个测试函数分别覆盖正常、边界、异常数据及非法配置。使用 pytest -q test_policy.py 运行，需要已安装 python3-pytest；若故意把大于改为大于等于，边界测试应失败，以证明断言有区分力。

### 集成测试必须等实际消息并设置总期限

单元测试不验证 ROS 发现和消息传递。下面完整 launch_testing 文件启动官方 talker，用测试节点订阅独立命名空间中的 chatter，并在五秒真实时间内等待非空消息。ReadyToTest 只允许测试开始，不宣称 talker 已经完成发现；循环通过 spin_once 接收消息，以“条件满足或总期限到达”结束。

保存为 test_talker.py，安装 launch_testing、launch_ros、rclpy、std_msgs 与 demo_nodes_cpp 后运行 launch_test test_talker.py。该示例验证通信合同和退出码，没有把控制台日志文字作为唯一依据。固定测试主题仍需要隔离实验域，避免另一个同名测试的发布者让本测试错误通过。

#### test_talker.py 完整文件

代码类型：complete

```python

import time
import unittest
import launch
import launch_ros.actions
import launch_testing
import launch_testing.actions
import launch_testing.asserts
import rclpy
from std_msgs.msg import String

def generate_test_description():
    talker = launch_ros.actions.Node(
        package='demo_nodes_cpp', executable='talker',
        namespace='integration_case', output='screen')
    return launch.LaunchDescription([
        talker, launch_testing.actions.ReadyToTest()
    ]), {'talker': talker}

class TestMessages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def test_nonempty_message(self):
        node = rclpy.create_node('integration_observer')
        received = []
        subscription = node.create_subscription(
            String, '/integration_case/chatter',
            lambda message: received.append(message.data), 10)
        end = time.monotonic() + 5.0
        try:
            while not received and time.monotonic() < end:
                rclpy.spin_once(node, timeout_sec=0.1)
            self.assertTrue(received, 'no message within 5 seconds')
            self.assertTrue(received[0], 'message is empty')
        finally:
            node.destroy_subscription(subscription)
            node.destroy_node()

@launch_testing.post_shutdown_test()
class TestExit(unittest.TestCase):
    def test_exit_code(self, proc_info, talker):
        launch_testing.asserts.assertExitCodes(proc_info, process=talker)

```

活动测试与被测进程同时运行，关闭后的测试再核对退出状态。测试节点在 finally 中清理，避免失败后残留订阅。总期限使用单调时间，因此仿真时钟暂停不会让测试无限等待。

### 注册测试与确认确实运行

把测试文件放进包的 test 目录并不总会自动注册。ament_cmake 包可在 BUILD_TESTING 条件内查找 launch_testing_ament_cmake 并添加 launch 测试，同时在 package.xml 声明测试依赖。Python 包则需要正确的 pytest 配置与依赖。注册失败可能导致报告显示零测试，而命令仍没有直接报编译错误。

运行时先构建，再执行 colcon test，最后读取 colcon test-result --verbose。必须确认期望的测试数量、失败和错误数量，以及日志路径。旧测试结果也可能留在构建目录中，持续集成最好使用干净工作空间或明确管理本次结果，不能拿昨天的 XML 当作今天的验证。

#### 加入已有 ament_cmake 包的注册片段

代码类型：snippet

```text

if(BUILD_TESTING)
  find_package(launch_testing_ament_cmake REQUIRED)
  add_launch_test(test/test_talker.py TIMEOUT 30)
endif()

```

该片段位于已有 CMakeLists.txt 的 ament_package() 之前。package.xml 需添加 launch_testing_ament_cmake、launch_ros、rclpy、std_msgs 和 demo_nodes_cpp 的 test_depend；这是注册片段，不是完整软件包。

#### 工作空间中的验证命令

代码类型：commands

```bash

colcon build
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose

```

test 负责运行，test-result 汇总结果。遇到失败应读取对应包的测试输出，不以终端最后出现一行 finished 推断所有断言通过。

### 让集成测试免受其它 ROS 图干扰

每个并行测试应使用独立域或项目提供的域分配机制，并为节点和资源分配独立名称。仅改 namespace 不能隔离绝对主题、固定服务、设备文件或全局 /clock。手工学习实验可以在空闲域运行；持续集成应由测试启动器分配并回收资源，避免多个作业都硬编码四十二。

测试数据使用固定种子和已知初始状态，等待条件应有期限和有用错误消息。发现延迟、首次初始化和正常运行的性能要求需要分别规定，不能给所有断言套同一个任意 sleep。若只在繁忙机器偶尔失败，先保存时间线和资源指标，再判断是测试期限不合理还是产品确有负载问题。

### 故障注入与结果解释

关键路径还应验证未发现服务、参数非法、消息过期、节点退出和时间跳变等情况。故障注入优先使用假设备或受控输入，使预期结果清楚且可恢复。测试不仅要证明正常时会输出，还要证明异常时不会悄悄沿用陈旧状态。每种故障应对应可读的断言，而非仅检查程序没有崩溃。

诊断报告能帮助比较系统、依赖和中间件，但不能替代行为断言。验收记录应写明测试层次、范围、环境和未覆盖部分；单元测试通过不意味着硬件已验证，浏览器测试也不验证 ROS 程序。本章提供可保存的测试文件，其 ROS 集成部分未在本次教材扩写中实际执行。

### 验证命令过期后的输出策略

系统收到一条有效命令，之后输入中断，需要确认边界和节点集成都符合约定。

1. 先用注入整数时间验证未收到命令、刚好到界限和超过界限三种输出，不依赖真实等待。

2. 再启动节点并发送带测试标识的命令，等待确认输入已处理，然后停止发送，在有界期限内等待零输出。

3. 隔离测试域和时钟，检查节点正常退出；失败时保留接收、过期判断与输出的关联日志。

验收：算法边界与 ROS 连接被分层验证，既不会把网络迟到误判为计算错误，也不会用纯函数通过掩盖节点没有调用策略。

### 深入练习 1

colcon test 结束但报告零测试，能否视为通过？

参考答案：不能。需要检查测试注册、BUILD_TESTING、依赖和发现规则，并确认本次期望的测试数量。零测试只表示没有执行到这些断言，不证明功能正确。

### 深入练习 2

为什么等待五秒后检查一次比条件循环更容易出问题？

参考答案：固定等待既可能浪费时间，也可能在繁忙环境仍不够。带总期限的条件循环能尽早成功并在失败时清楚报告缺少什么证据；同时必须 spin 或采用能推进回调的等待方式。

### 深入练习 3

只有正常输入测试通过，是否覆盖了超时保护？

参考答案：没有。应独立测试缺失输入、恰好边界、过期和异常时钟，并在节点层验证策略确实影响输出。故意破坏边界条件后测试应失败，这有助于发现空洞断言。

### 基础验证流程

先为纯计算函数写可重复单元测试。

增加进程启动、有效消息到达与退出行为的集成检查。

在干净的 Jazzy 环境运行构建和测试。

失败时保存日志、依赖版本和最小重现命令。

#### 工作空间根目录

```bash

colcon build --symlink-install
colcon test --event-handlers console_direct+
colcon test-result --verbose

```

#### 环境基线

```bash

ros2 doctor --report

```

### 预期结果

- 能区分构建失败、测试断言失败和测试根本未注册。

- 报告包含测试数量、失败数量与日志路径。

### 常见问题

- 只看 colcon test 命令退出，而不读取 test-result。

- 依赖任意 sleep 代替就绪检测，造成偶发失败。

- 在同一 ROS_DOMAIN_ID 上并行运行互相干扰的集成测试。

### 练习

给“超时后停止输出命令”的行为添加一个可重复测试，并说明如何隔离 ROS 图。

#### 参考答案

给控制逻辑注入可控时间和命令输入：有效命令到达后输出应更新；超过超时阈值后输出应为零。集成测试用独立 ROS_DOMAIN_ID 和明确命名空间，等待端点就绪而非固定长 sleep；在测试结束销毁进程，检查退出状态与消息内容。

### 依据

- [ROS 2 自动化测试](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Testing/Testing-Main.html)

- [colcon 快速开始](https://colcon.readthedocs.io/en/released/user/quick-start.html)

- [ros2 doctor 诊断](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Getting-Started-With-Ros2doctor.html)

## 17. DDS、RMW、多机发现与隔离

RMW 是 ROS 客户端与中间件之间的适配层。切换实现要先安装对应软件包，并保持整个实验的配置可追溯。

### 学习目标

- 为双机通信建立一致的发现配置

- 按层定位网络与中间件问题

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

RMW 是 ROS 客户端与中间件之间的适配层。切换实现要先安装对应软件包，并保持整个实验的配置可追溯。

ROS_DOMAIN_ID 用于逻辑分组，不是安全认证。DDS 发现还受子网、多播、防火墙、网络接口和发现范围影响。

Jazzy 的动态发现环境变量用于支持它们的 DDS 实现；rmw_zenoh 使用自己的配置方式。

### 把 ROS 图、发现与数据通道分开理解

客户端库通过 RMW 适配层调用通信实现；在常见 DDS 部署中，参与者先发现彼此，再交换端点资料，匹配类型与 QoS，最后传输业务数据。图中出现远端节点只证明部分发现信息已经到达，不等于每种消息都能通过网络，更不等于应用回调已经处理完数据。

多机故障应先从最小发布订阅对定位。若连字符串都无法跨机传输，先处理环境和网络；若字符串正常而大图像卡顿，再检查带宽、分片、缓存和负载。每次改变一个条件，并记录两端的观察。一次同时换中间件、域和路由，虽然可能暂时成功，却无法知道哪个条件真正起作用。

### 域号提供逻辑隔离，名称提供接口组织

ROS_DOMAIN_ID 把实验图划入不同逻辑域。同一实验的发布者、订阅者和命令行观察者应使用同一个值；相同主题名位于不同域时通常不会互相发现。域号不是密码，知道或尝试相同域的进程仍可加入。因此它适合让两组学习实验避免误连，不能代替身份认证、加密和访问控制。

域号也影响常见 DDS 的端口计算，不能任意选一个很大的整数。少量进程的入门实验可以在官方建议的零到一百零一区间选取如四十二，并避开同网络已有实验；大量参与者、特定系统临时端口范围和厂商配置仍需单独核查。命名空间则组织同一图中的接口，即使两个机器人名称不同，仍可能共享 /tf 或其它绝对主题，不能混淆两种隔离。

### 先建立能解释的单机与双机基线

以下以两台 Ubuntu 24.04/Jazzy 学习机为例，默认它们已安装 demo_nodes_cpp 与同一个可用 RMW。先在每台机器各自验证 talker 和 listener，再在甲机运行 talker、乙机运行 listener。停止单机试验中的旧进程，避免远端失败却误把本机残留消息当成跨机成功。

每个实际运行节点的终端都需要设置环境，修改另一个终端不会改变已启动进程。先加载系统环境，再加载需要的工作空间；自定义消息应在两机使用一致定义与构建版本。下面显式选择已安装的 Fast DDS，清除与基线相冲突的旧发现设置；如果未安装该 RMW，应先安装对应 Jazzy 软件包。

#### 两台机器的每个实验终端都执行

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
unset ROS_LOCALHOST_ONLY
unset ROS_STATIC_PEERS
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop
# 甲机
ros2 run demo_nodes_cpp talker
# 乙机，另一个终端
ros2 run demo_nodes_cpp listener

```

先统一域、实现与发现范围，减少不必要变量。SUBNET 对支持此配置的 DDS 实现使用子网发现，并不保证跨路由器或被隔离无线客户端之间可达。

#### 在两端分别保留诊断输出

代码类型：commands

```bash

printenv ROS_DISTRO ROS_DOMAIN_ID RMW_IMPLEMENTATION ROS_AUTOMATIC_DISCOVERY_RANGE ROS_STATIC_PEERS
ros2 node list
ros2 topic info /chatter --verbose
ros2 doctor --report

```

只读取相关环境项。比较两端端点数量、名称、类型与策略；环境值未设置时 printenv 可能返回非零，这本身不等于 ROS 节点故障。

### 发现范围与静态对端的选择条件

Jazzy 对支持这些设置的 DDS RMW 提供 SUBNET、LOCALHOST、OFF 与 SYSTEM_DEFAULT。LOCALHOST 限制自动发现到本机；OFF 禁止发现其它节点；SYSTEM_DEFAULT 不主动覆盖中间件自己的设置。ROS_STATIC_PEERS 是以分号分隔的指定对端列表，可在关闭子网自动发现而保留本机发现时联系明确的远端地址。

假设甲机地址为一九二点一六八点五十点十一，乙机末段为十二，下方配置在两边互相填对端。执行前应换成实际地址，并确认两边都没有 OFF；地址列表不是防火墙规则，更不是访问许可名单，网络路由和所需数据端口仍必须可达。rmw_zenoh 不采用这两项发现变量，应使用它自己的路由与会话配置，不能机械照搬。

#### 明确对端的示例，先终止原节点再重新启动

代码类型：commands

```bash

# 甲机：把地址替换为乙机实际地址
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_STATIC_PEERS='192.168.50.12'
# 乙机：把地址替换为甲机实际地址
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_STATIC_PEERS='192.168.50.11'
# 各机在自己的配置下重新启动节点与观察工具
ros2 daemon stop

```

分号用于多个对端时必须留在引号内，避免被 shell 当作命令分隔符。配置影响后续创建的节点；现有进程不会随终端变量改变而自动重新配置。

### 网络证据应逐层缩小问题范围

先核查主机地址、路由和所选网卡，再测试基本可达性与多播。ping 成功只说明 ICMP 路径可用，不能证明 DDS 发现或数据端口可用。无线接入点可能隔离客户端，VPN 可能改变路由，多网卡机器可能选择了不可达接口；容器还会增加网络命名空间与地址转换层。

使用 ros2 multicast 的发送接收可以辅助判断多播路径，但它成功也只代表该测试的组和端口通过，不是所有 DDS 配置都正确。若发现正常而大消息异常，应进一步观察丢包、分片、接口 MTU 和接收缓冲，并复核两端 QoS。保留最小消息大小和负载，逐步增加，才能看出故障阈值。

#### 仅在有权限诊断的两台学习机执行

代码类型：commands

```bash

# 接收机
ros2 multicast receive
# 发送机
ros2 multicast send
# 分别查看本机地址与路由
ip -brief address
ip route

```

receive 应先运行，再从另一台发送。工具若不存在需安装 ros-jazzy-ros2multicast。测试结果应与实际 DDS 端点结果分开记录，不通过时再检查允许的网络策略和接口配置。

### 更换 RMW 与 CLI 缓存时保持实验一致

RMW_IMPLEMENTATION 指定的是进程启动时要加载的实现，设置一个未安装的标识会导致加载失败。比较不同实现时，应先安装其软件包、终止旧节点、统一两端配置并重新启动。不同 DDS 厂商的普通数据互通存在条件，安全互通又有额外限制，入门基线最好先用同一实现排除变量。

ROS 命令行可能使用后台 daemon 缓存图信息。更换实现后旧 daemon 不会自动按新环境重建，所以可能出现应用彼此通信而 node list 仍异常的现象。停止对应 daemon 后再观察，必要时使用支持的无 daemon 查询方式。最终验收应有跨机接收内容与序号、恢复连接和负载记录，而不是仅截取一个节点列表。本章未在本次写作中进行双机联网试验。

### 两台电脑同域却看不到彼此

甲机单机演示正常，乙机单机演示正常，跨机没有字符串到达。

1. 终止所有旧演示，分别保存两端相关环境、消息类型和 RMW；确认观察命令与节点在同域。

2. 检查子网、路由、多播与无线隔离；若需要明确对端，使用 LOCALHOST 加互相填写的静态对端重新试验。

3. 若图已出现而消息仍不到，再检查实际端点 QoS 与数据路径；切换 RMW 后停止旧 daemon。

验收：每一步都有能排除一层原因的证据，避免把网络、匹配和执行器三个问题混为“DDS 不稳定”。

### 深入练习 1

两个节点在不同域，但主题和消息完全相同，是否应该通信？

参考答案：通常不会。不同域用于逻辑隔离；把实际节点进程与诊断工具都设置为同域后重新启动。修改某个 shell 的变量不能改变已经运行的节点。

### 深入练习 2

ping 成功、multicast 测试成功，能否排除网络问题？

参考答案：不能。它们只验证特定协议路径和测试端口，DDS 端口、接口选择、大消息分片及回程路由仍可能不同。还需端点发现和实际业务消息证据。

### 深入练习 3

把静态对端列表设为两台可信主机是否完成访问控制？

参考答案：没有。发现名单只影响主动联系的方式，不认证身份或限制对方发布哪些内容。敏感图应独立设计身份、权限、加密和网络边界；域号也不是安全凭证。

### 基础验证流程

先确保单机 talker/listener 能通信。

在两台机器使用相同域和兼容消息定义。

逐项检查发现范围、网络互通与接口配置。

切换 RMW 后停止旧 daemon，再启动诊断工具。

#### 每个相关终端统一设置

```bash

export ROS_DOMAIN_ID=42
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop

```

#### 可选：安装并选择 Cyclone DDS

```bash

sudo apt install ros-jazzy-rmw-cyclonedds-cpp
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 daemon stop
ros2 run demo_nodes_cpp talker

```

### 预期结果

- 同域、匹配配置的两台机器能收发 demo 消息。

- 改变域后节点不再互相发现，恢复后重新发现。

### 常见问题

- 把 domain ID 当成访问控制。

- 后台 daemon 使用旧 RMW，CLI 视图与节点环境不一致。

- 在 DDS 和 Zenoh 间机械复制发现变量。

### 练习

写一份双机诊断顺序：环境、域、消息类型、QoS、网络、RMW，再记录每步证据。

#### 参考答案

先确认两个终端加载相同目标发行版和预期 overlay，再核对域与发现范围；检查 interface 定义与 topic info 的 QoS；确认主机网络、接口和多播/防火墙条件；最后比较 RMW 配置及 daemon。每一步保存输出，并用最小 talker/listener 排除上层算法问题。

### 依据

- [选择不同 RMW 实现](https://docs.ros.org/en/jazzy/How-To-Guides/Working-with-multiple-RMW-implementations.html)

- [ROS_DOMAIN_ID 与端口约束](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Domain-ID.html)

- [动态发现范围与静态对等端](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html)

- [ros2 doctor 诊断](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Getting-Started-With-Ros2doctor.html)

## 18. SROS2：身份、加密与权限

SROS2 为支持 DDS-Security 的中间件准备身份与权限材料。节点使用 enclave 选择安全身份；安全通信还依赖治理和访问权限配置。

### 学习目标

- 理解 keystore 与 enclave 的职责

- 完成安全通信前的配置检查

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

SROS2 为支持 DDS-Security 的中间件准备身份与权限材料。节点使用 enclave 选择安全身份；安全通信还依赖治理和访问权限配置。

安全模式不能只靠 ROS_DOMAIN_ID 实现。证书配置和应用权限应分开审查。

不同中间件及发行版的安全支持存在限制，不能直接假设跨厂商安全互通。

### 身份、授权与保密分别解决什么问题

身份认证回答通信对端是谁；授权决定该身份能发布、订阅或调用哪些接口；加密保护传输内容。仅把域号改成难猜的数字，没有提供上述保证。SROS2 为支持 DDS-Security 的中间件管理证书与权限材料，使 ROS 应用能够选择安全身份，但操作系统账号、进程文件权限和设备访问仍是另外的管理层。

先明确哪些节点需要哪些接口，再准备身份。传感器可发布观测，监控器可订阅观测，监控器不应因为“能看数据”就获得控制指令发布权。一个 enclave 表示一组安全材料与权限边界，不必机械等同于节点名；同一进程或共享上下文的组件身份设计还需要结合中间件参与者布局，不能假设每个组件天然隔离。

### 在独立实验目录准备身份材料

以下实验限定同一台 Jazzy 学习机、已具备安全支持的 rmw_fastrtps_cpp，以及 sros2、demo_nodes_cpp、demo_nodes_py。使用全新的 security_lab 目录，先创建 keystore，再为两个独立进程创建 enclave。默认生成的权限适合连通性演示，不能直接当成最终最小权限策略。

keystore 包含身份与权限的证书颁发材料，以及每个 enclave 的证书、私钥、治理和权限文件。运行节点只需适当的运行材料；能够签发或签署权限的管理员私钥不应随所有运行节点一起分发。实验采用 umask 收紧新文件默认权限，目录不要加入代码仓库或作为普通教材附件分享。

#### 一次性建立实验材料

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
umask 077
mkdir security_lab
cd security_lab
ros2 security create_keystore keystore
ros2 security create_enclave keystore /lab/talker
ros2 security create_enclave keystore /lab/listener

```

mkdir 使用新的目录名，避免误改已有 keystore。两个 enclave 路径用于定位材料，并不改变程序的 ROS 节点名：demo 仍分别叫 talker 和 listener。

### 显式启用并强制使用安全身份

所有运行终端都需设置 keystore 的绝对路径、启用开关和 Enforce 策略，再通过 --enclave 选择自己的身份。Enforce 使缺失或错误材料不能悄悄降级为无安全运行。两个终端必须采用一致域和兼容的安全中间件；Jazzy 官方教程不支持把跨厂商安全互通当作可保证条件。

下面先做正常收发，证明证书和环境能够一起工作。另一个测试使用不存在的 enclave，预期创建安全节点失败。这个失败仅证明缺失身份被拒绝，还不能证明某个已经认证的身份受到主题权限限制；后面必须再做真实的越权发布测试。

#### 两个终端均进入 security_lab 后执行共同配置

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_SECURITY_KEYSTORE="$(pwd)/keystore"
export ROS_SECURITY_ENABLE=true
export ROS_SECURITY_STRATEGY=Enforce
unset ROS_SECURITY_ENCLAVE_OVERRIDE
# 终端甲
ros2 run demo_nodes_cpp talker --ros-args --enclave /lab/talker
# 终端乙
ros2 run demo_nodes_py listener --ros-args --enclave /lab/listener
# 停止一个演示后，单独验证不存在的身份
ros2 run demo_nodes_cpp talker --ros-args --enclave /lab/missing

```

ROS_SECURITY_KEYSTORE 必须指向实际同一个实验目录。最后一条应失败；正常演示应收到 chatter。命令行工具也是进程，若参与受保护图，需要独立考虑其身份和允许的操作，不能把无权限的 CLI 视图当成图不存在。

### 将主题允许清单写入权限并重新签名

权限最终以签名文件交给中间件使用，只编辑可读 XML 不会自动改变已签署的策略。下面完整脚本应保存为 restrict_permissions.py，在 security_lab 目录且两节点都停止后运行。它只修改本实验两份权限，保留生成的身份主体和有效期，把域限制为四十二，并分别只允许业务主题 chatter 的发布或订阅。

普通 ROS 主题映射为带 rt/ 前缀的 DDS 主题；参数服务还包含请求和响应实体。脚本允许每个 demo 自己节点名称下的服务实体，以及日志、参数事件和必要发现信息，所以它是限制业务主题的教学策略，并非适用于任意应用的通用最小权限模板。新增动作或改变命名空间前，需要重新梳理实际接口。

#### restrict_permissions.py 完整实验脚本

代码类型：complete

```python

from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

root = Path('keystore').resolve()
for role in ('talker', 'listener'):
    enclave = root / 'enclaves' / 'lab' / role
    path = enclave / 'permissions.xml'
    tree = ET.parse(path)
    grant = tree.getroot().find('./permissions/grant')
    if grant is None:
        raise RuntimeError(f'grant missing: {path}')
    for child in list(grant):
        if child.tag in ('allow_rule', 'deny_rule', 'default'):
            grant.remove(child)
    rule = ET.SubElement(grant, 'allow_rule')
    domains = ET.SubElement(rule, 'domains')
    ET.SubElement(domains, 'id').text = '42'
    own_services = f'*/{role}/*'
    published = ['rt/rosout', 'rt/parameter_events',
                 own_services, 'ros_discovery_info']
    subscribed = ['rt/parameter_events', own_services, 'ros_discovery_info']
    if role == 'talker':
        published.append('rt/chatter')
    else:
        subscribed.append('rt/chatter')
    for direction, names in (('publish', published), ('subscribe', subscribed)):
        topics = ET.SubElement(ET.SubElement(rule, direction), 'topics')
        for name in names:
            ET.SubElement(topics, 'topic').text = name
    ET.SubElement(grant, 'default').text = 'DENY'
    ET.indent(tree, space='  ')
    tree.write(path, encoding='utf-8', xml_declaration=True)
    subprocess.run([
        'openssl', 'smime', '-sign', '-text',
        '-in', str(path), '-out', str(enclave / 'permissions.p7s'),
        '-signer', str(enclave / 'permissions_ca.cert.pem'),
        '-inkey', str(root / 'private' / 'permissions_ca.key.pem')
    ], check=True)
    print(f'updated and signed: {role}')

```

脚本先移除原允许规则，避免旧的广泛权限继续生效，再写唯一域和允许清单，最后用权限 CA 签名。check=True 使签名失败立即报错；不应在失败后继续把旧权限当作新策略。它使用的是权限 CA 私钥，不是某个节点的身份私钥。

### 同时验证允许路径与拒绝路径

重新启动原 talker 和 listener，正常 chatter 应仍能传输；随后停止原 talker，用同一合法 enclave 把 chatter 重映射为 forbidden_chatter。身份没有变化，但新的业务主题不在允许清单，应被中间件拒绝创建对应通信实体，应用可能因此退出并记录授权错误。再恢复原命令，应恢复正常。

拒绝测试需要看拒绝原因，不能只看“没有收到”。程序崩溃、网络断开或 QoS 不兼容也会导致没有消息，却不是权限发挥作用。保留安全日志、所用 enclave、域、最终话题名及策略版本。修改 XML 后忘记重新签名、修改了错误目录、进程没有重启，都会让实验仍使用旧配置。

#### 停止原 talker 后测试越权发布

代码类型：commands

```bash

ros2 run demo_nodes_cpp talker --ros-args --enclave /lab/talker --remap chatter:=forbidden_chatter

```

该命令仍使用有效身份，但试图创建未授权主题。需保持 Enforce 和正确 keystore 环境，确认报错来自权限拒绝，再用未重映射命令复验正常路径。

### 从实验策略过渡到可维护部署

部署材料需要记录身份主体、证书有效期、签署者、权限版本和目标设备。到期、撤换设备或接口变化后，应有重新签发、分发和恢复验证流程；系统时间错误也可能使本来正确的证书被判定尚未生效或已过期。权限变更应与接口变更一起审查，防止应用改了名称而策略仍指向旧名称。

发现信息可见不代表所有业务数据都可读取，加密包也不等于端点被攻陷后仍安全。把管理员签名能力与运行私钥分开、限制文件可读范围，并以必要权限部署，才能让通信保护成为系统中的一层。本章依据官方安全与访问控制教程补齐离线步骤，未声称已经在本机完成加密抓包或拒绝验证。

### 监控器可读但不能改写控制指令

需要让只读监控进程读取传感器，同时防止它借用合法身份发布控制主题。

1. 先把读取、日志和必要基础接口列为允许项，不给控制主题发布权限；为监控进程分配独立运行材料。

2. 正常启动监控并核对数据，再用同一身份尝试未授权发布，检查明确的授权拒绝日志。

3. 保留正常与拒绝两种验证记录，签署后的策略、证书有效期和应用版本一同管理。

验收：身份有效与动作被授权被分别验证；域隔离和主题名称约定不会被误当作访问控制。

### 深入练习 1

打开 ROS_SECURITY_ENABLE 就一定禁止降级吗？

参考答案：不够。还需设置 Enforce、提供正确 keystore 与 enclave，并选择支持安全的 RMW。用缺失身份启动应失败，才能验证没有静默回落；之后还需验证权限拒绝。

### 深入练习 2

编辑 permissions.xml 后越权发布仍成功，优先检查什么？

参考答案：检查是否移除了旧的广泛允许规则、是否用正确权限 CA 重新生成 permissions.p7s、进程是否重启、环境是否指向修改的目录。再核对最终 DDS 主题匹配与域，不能仅凭 XML 文件内容断言运行策略。

### 深入练习 3

为何运行设备不应带整个 keystore 的管理员私钥？

参考答案：运行节点只需要自身身份和受信任的签名材料，签发权限的 CA 私钥能为其它身份或更大权限背书。把它分发到每台设备会扩大单台失陷的影响，应在受控签署环境保存，按身份分发运行材料。

### 基础验证流程

先确认所用 RMW 的安全支持。

在专用实验目录创建 keystore 和两个 enclave。

按官方教程设置 ROS_SECURITY_KEYSTORE、ROS_SECURITY_ENABLE 和 Enforce 策略。

分别启动带 enclave 的 talker/listener，最后收紧权限测试拒绝路径。

#### 只创建实验身份材料

```bash

ros2 security create_keystore ./security_demo
ros2 security create_enclave ./security_demo /demo/talker
ros2 security create_enclave ./security_demo /demo/listener

```

#### 后续配置入口

```bash

# 按官方 SROS2 教程设置绝对 keystore 路径、启用安全及 Enforce 策略。
# 运行节点时通过 --ros-args --enclave 指定其身份。

```

### 预期结果

- 能找到为各 enclave 生成的材料并解释谁可以访问哪个话题。

- 启用强制策略后错误身份不能静默退回无安全模式。

### 常见问题

- 把带私钥的整个 keystore 提交到公共仓库。

- 仅启用加密却未检查发布/订阅权限。

- 将某一 DDS 厂商验证成功推断为所有 RMW 均适用。

### 练习

为传感器发布者和只读监控器列出最小话题权限，并测试未授权写入被拒绝。

#### 参考答案

传感器身份只获得发布其数据话题所需权限；监控身份只允许订阅这些数据及必要诊断接口，默认拒绝控制命令发布。用未授权身份尝试写入控制话题并核对拒绝日志；同时验证正常订阅仍可用。证书和私钥按各节点身份分发，不共享整套管理员材料。

### 依据

- [启用 DDS-Security / SROS2](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Security/Introducing-ros2-security.html)

- [SROS2 安全教程目录](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Security/Security-Main.html)

- [选择不同 RMW 实现](https://docs.ros.org/en/jazzy/How-To-Guides/Working-with-multiple-RMW-implementations.html)

## 19. 性能分析、Tracing 与实时边界

topic hz 是观测工具，测得的接收频率会受观察节点和资源竞争影响；它不是端到端延迟的完整证明。

### 学习目标

- 建立吞吐、延迟和回调耗时的测量方法

- 区分平均性能与截止时间保证

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

topic hz 是观测工具，测得的接收频率会受观察节点和资源竞争影响；它不是端到端延迟的完整证明。

tracing 可关联执行器与回调事件，用于定位排队、阻塞和过长计算。优化前要固定负载、消息大小和机器配置。

多线程、组合节点与零拷贝各有条件；在普通桌面内核上平均更快并不等于硬实时保证。

### 先把指标定义到时间点与单位

性能问题可能是发布太慢、消息排队、计算太久或输出过旧。首先为链路定义时间点：产生输入、调用发布、开始订阅回调、完成处理、形成输出。发布到回调开始的差值包括传输与调度等待；回调开始到结束反映处理区间；采样到执行结果则是更完整的端到端延迟。不同差值不能共用一个含糊的“延迟”名称。

同时记录吞吐、丢失或重复序号、内存和处理器使用率。接收频率达到三十赫兹，数据仍可能落后一秒；平均耗时很低，也可能每隔几秒出现一次长暂停。应在确定业务目标后报告中位数、较高分位数、最大观测值和超时次数，并保留负载与观察时长。

### 保证时钟可比较并控制测量扰动

在同一台 Linux 主机上，可用共享的单调时钟来源记录发布与回调时刻，不受系统校时和仿真暂停影响。跨主机的单调时刻没有共同起点，不能直接相减；跨机单向延迟需要对齐时钟并评估同步误差，或者改测同一时钟下的往返时间。往返的一半也只在额外对称假设成立时近似单向延迟。

每条消息都打印长日志、保存大文件或调用外部绘图，会改变被测程序的调度和 I/O。优先记录紧凑序号与时间，使用有界缓冲，结束后再输出。还要报告工具开关：同一话题多一个观察者可能增加序列化、复制或带宽，测量工具不是没有成本的透明窗口。

### 一个可以手算并核对的分布示例

把同一发布者的每个样本记录为序号、调用发布前时刻、订阅回调开始和结束时刻。下方 CSV 只是合成数据，时间单位纳秒，对应发布到回调开始分别为一、二、三、四、五十毫秒。平均值为十二毫秒，中位数三毫秒，最高延迟五十毫秒；若目标是十毫秒，其中一个样本已经违约。

完整分析脚本采用最近秩方法计算分位数，并明确计算的是内部序号缺口，而非完整网络丢包率。测试开始前和结束后的丢失无法仅由接收到的序号范围推断。五个样本只用于核对算法，正式实验需要足够样本与多轮运行，不能把小样本百分之九十九分位数包装成稳定的系统保证。

#### sample_latency.csv 合成数据

代码类型：complete

```text

seq,send_ns,start_ns,end_ns
1,100000000,101000000,102000000
2,200000000,202000000,203000000
3,300000000,303000000,304000000
4,400000000,404000000,405000000
5,500000000,550000000,551000000

```

send_ns 与 start_ns 差值包含该观察边界内的等待；end_ns 与 start_ns 差值在合成例中均为一毫秒。数据并非任何机器人实测结果。

#### latency_report.py 完整分析脚本

代码类型：complete

```python

import csv
import math
import sys

with open(sys.argv[1], newline='', encoding='utf-8') as stream:
    rows = list(csv.DictReader(stream))
if not rows:
    raise SystemExit('no samples')
sequences = []
waiting_ms = []
callback_ms = []
for row in rows:
    sequence = int(row['seq'])
    sent, start, end = (int(row[key]) for key in ('send_ns', 'start_ns', 'end_ns'))
    if not sent <= start <= end:
        raise ValueError(f'invalid clock ordering at sequence {sequence}')
    sequences.append(sequence)
    waiting_ms.append((start - sent) / 1_000_000)
    callback_ms.append((end - start) / 1_000_000)

def report(name, values):
    ordered = sorted(values)
    def percentile(fraction):
        index = max(0, math.ceil(fraction * len(ordered)) - 1)
        return ordered[index]
    print(name, {
        'count': len(ordered),
        'mean_ms': sum(ordered) / len(ordered),
        'p50_ms': percentile(0.50),
        'p95_ms': percentile(0.95),
        'p99_ms': percentile(0.99),
        'max_ms': ordered[-1],
    })

report('publish_to_callback_start', waiting_ms)
report('callback_duration', callback_ms)
unique = set(sequences)
print('duplicate_samples', len(sequences) - len(unique))
print('missing_inside_observed_range', max(unique) - min(unique) + 1 - len(unique))
print('out_of_order_pairs', sum(b < a for a, b in zip(sequences, sequences[1:])))

```

用 python3 latency_report.py sample_latency.csv 运行。程序拒绝时钟顺序矛盾的样本，而不是把负延迟取绝对值；跨机器未经同步的数据不能靠此脚本自动修复。分析以单一发布者且序号不重置为前提。

### 用 tracing 找到延迟落在哪一段

如果外部测量显示长尾，下一步需要观察内部事件。ROS 追踪点可记录回调进入和退出、发布及执行相关事件。对同一回调实例匹配开始结束，结合进程、线程和对象标识，能够区别回调自身很慢与回调迟迟没有被调度。跨多个节点的因果链还需要业务序号或其它关联信息，不能把相邻两条事件直接当作同一消息。

下面是在有追踪支持的 Linux/Jazzy 环境中的采集流程。先确认 Tracing enabled，再启动会话，按提示开始记录，然后在另一个终端启动待测程序。若节点在追踪开始前已经创建，某些初始化映射事件可能缺失，后续分析会更困难。采集结束后读取实际事件，确认不是一个空目录。

#### 追踪能力、会话与原始事件检查

代码类型：commands

```bash

sudo apt install ros-jazzy-ros2trace ros-jazzy-tracetools-analysis babeltrace
source /opt/ros/jazzy/setup.bash
ros2 run tracetools status
ros2 trace --session-name engineering_probe --list
# 按提示开始后，在另一终端运行待测 ROS 程序
# 程序完成后回到追踪终端，按提示停止
babeltrace "$HOME/.ros/tracing/engineering_probe"

```

--list 会显示将启用的事件，交互式会话仍需按提示开始和停止。输出目录以工具实际打印为准；如果设置过追踪基础目录，应采用对应路径。这里只采集并检查数据，不把“追踪已开启”当作性能已达标。

### 一次改变一个因素并解释取舍

固定处理器、系统版本、RMW、消息大小、发布频率、订阅数、QoS、参数和数据集，先预热再采集基线。比较不同执行器或组件布局时，保持业务工作量相同，并重复多轮。可以交错运行甲乙配置，减少温度、后台负载和缓存状态随时间变化造成的偏差；保留异常样本，不只挑最好的一次。

优化方向应由证据决定：回调计算长可降低算法成本，等待锁长应缩短临界区，排队长应控制负载，传输复制成本大再考虑组件、进程内路径或支持的共享内存。降低可靠性可能减少等待却增加丢样，减小队列可能改善新鲜度却放弃历史，应同时报告收益与业务代价。

### 实时性是可满足截止时间的系统属性

普通桌面系统平均更快，不意味着最坏情况存在可保证上界。硬实时需要对调度、内存、锁、驱动和硬件链路一起分析；实时路径中不可控的内存分配、缺页、同步打印和无限等待都可能制造长尾。安装实时内核或提高线程优先级只是其中一环，不会自动解决回调组死锁或设备阻塞。

工程报告应写“在何种负载、多久观察、多少样本下，最大观测值和违约次数是多少”。最大观测值不是理论最坏值，没有看到违约也不证明任何未来负载都安全。先把功能正确、软实时性能与硬实时论证区分，才能为后续优化留下可信基线。本章合成数据可离线核算，追踪命令未在本次写作中执行。

### 平均延迟正常但周期性出现卡顿

一条图像链平均六毫秒，但界面每隔数秒停顿，要求定位是否来自计算或调度。

1. 采集输入到输出的序号与时刻，报告高分位、最大值和超过业务期限的次数，确认卡顿对应真实数据延迟。

2. 在相同负载下追踪回调，比较异常样本的回调持续时间与开始前等待，检查日志、磁盘和锁行为。

3. 只改变一个已确认因素，如把同步写盘移出回调，再重复测量并核对输出质量与丢样。

验收：结论说明具体延迟段和变更代价，不用频率均值或某次最快记录代替长尾证据。

### 深入练习 1

两台机器分别取 monotonic_ns 后相减，为什么可能得到无意义延迟？

参考答案：两机单调时钟没有共同起点，值之间不能直接比较。应采用评估过同步误差的公共时间基准，或测同一端时钟下的往返时间；不能把负数简单修成正数。

### 深入练习 2

五个样本延迟为一、二、三、四、五十毫秒，平均与中位数分别多少？

参考答案：平均为十二毫秒，中位数三毫秒，最大五十毫秒。最近秩方法下百分之九十五和百分之九十九分位都是五十毫秒；样本很少，仅说明计算方式，不能表示稳定的长尾概率。

### 深入练习 3

topic hz 达到目标且没有丢序号，能否证明实时性？

参考答案：不能。频率不反映样本年龄，可靠队列可能完整传递过时消息；还需时间点明确的延迟分布、违约次数和负载条件。有限测量也只能给观测证据，不能独自证明硬实时最坏上界。

### 基础验证流程

选定指标：发布频率、端到端延迟分布、CPU、内存和丢失序号。

记录原始基线并启用 tracing。

一次只改变一个因素，例如执行器或部署方式。

比较分位数和最坏样本，解释异常来自何处。

#### 安装并检查追踪能力

```bash

sudo apt install ros-jazzy-ros2trace ros-jazzy-tracetools-analysis
ros2 run tracetools status

```

#### 按教程采集会话

```bash

ros2 trace --session-name learning-trace --list
# 根据提示开始记录，再在另一终端运行待分析节点。

```

### 预期结果

- 能获得一份可用于分析回调耗时的 trace。

- 每个优化结论都有固定负载和前后测量数据。

### 常见问题

- 只报告平均值，忽略长尾和超时。

- 把 intra-process、DDS shared memory 与 loaned message 混成同一个开关。

- 为追求频率在实时路径里大量分配内存或同步打印日志。

### 练习

比较单进程组件与独立进程的同一消息链；列明环境、指标和未验证的推测。

#### 参考答案

保持同一机器、发行版、RMW、消息类型、大小、频率与订阅数。分别记录进程布局、intra-process 配置、CPU/内存、延迟分布与序号丢失；重复多轮并报告分位数和异常样本。把未测的零拷贝、实时性或跨机器收益明确标为假设。

### 依据

- [ros2_tracing 性能分析](https://docs.ros.org/en/jazzy/Tutorials/Advanced/ROS2-Tracing-Trace-and-Analyze.html)

- [执行器概念](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html)

- [在一个进程里组合节点](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html)

- [QoS 策略与兼容性](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html)

## 20. 可重复部署：依赖、容器与版本固定

让另一台电脑复现结果，需要记录的不只是源码。把操作系统、发行版、依赖版本、参数和运行入口作为一份交付物管理。

### 学习目标

- 分清构建环境与运行环境

- 建立可复查的依赖和启动记录

- 识别容器对网络与硬件的边界

### 先修

已理解 package.xml 与 colcon；可选 Docker；先按其官方安装文档配置

### 概念

colcon 组织构建，rosdep 按 package.xml 解析系统依赖，容器固定用户空间；三者解决不同问题。容器共享宿主机内核，不会自动替你提供实时调度或 GPU 驱动。

先固定源码提交与发行版，再记录软件包版本。镜像标签可能移动，发布记录中应保存实际镜像摘要。params.yaml、标定文件和地图也是配置输入，应与运行结果关联。

开发镜像可以保留编译器和调试工具；部署镜像只需可执行文件、共享库和必要资源。先证明 install 目录包含 launch、配置和模型，再缩减镜像。

DDS 发现、设备文件权限、时钟和 GPU 访问需要独立配置。容器能启动只说明进程起来了；还需要从外部观察话题、TF 和退出行为。

### 交付物是可运行系统的全部输入

把源码复制到另一台机器，并不意味着系统可以复现。实际运行还取决于操作系统、ROS 发行版、系统依赖、编译选项、消息定义、参数、标定、地图和设备固件。应把这些输入与一次验收结果关联，使别人能够知道“运行的是哪一版”，而不是只知道某个文件夹的名字。

先区分开发环境、构建环境与运行环境。开发环境可能包含编辑器和调试工具，构建环境需要编译器与头文件，运行环境需要可执行文件、共享库和资源。精简运行环境的前提是证明安装产物齐全；如果 launch 或模型只在源码目录中存在，删除源码就会暴露之前被开发路径掩盖的问题。

### 依赖声明、源码版本与安装规则

package.xml 描述包的依赖关系，rosdep 将系统依赖键映射为平台软件包，colcon 按工作空间组织构建。它们不是同一层的锁文件：安装成功不代表每次取到完全相同的软件版本。可复现交付应保存源码提交或精确仓库清单、系统包版本以及所用依赖来源，涉及离线部署还需提前准备对应包或镜像。

运行入口应通过包索引定位资源，不把开发者家目录写死到 launch 中。C++ 包应安装共享库、程序、launch、配置和模型；Python 包应配置正确的模块、console_scripts 与数据文件。重新开一个只加载目标环境的终端，检查包前缀与程序入口，可以发现旧 overlay 偶然提供依赖的情况。

#### 在已经构建的目标工作空间记录环境与产物

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 doctor --report
ros2 pkg prefix hub_component
ros2 pkg executables hub_component
dpkg-query -W 'ros-jazzy-*'

```

示例包来自组件章节；换成自己的包时应检查实际名称。prefix 应指向本次目标安装目录，executables 应包含约定入口。版本清单用于追溯，不能自动替代依赖包归档。

### 容器固定用户空间，但不固定整个机器人

容器把用户空间文件与依赖封装起来，仍共享宿主机内核。它不能自动提供真实硬件、实时调度、GPU 驱动兼容性或跨主机 DDS 发现。初次验证可以把发布和观察命令放在同一个容器内，先证明应用产物可用；然后分别增加宿主机、网络和设备边界，逐层验收。

下面是完整教学镜像，构建上下文包含本章 Dockerfile、entrypoint.sh，以及组件章节生成的 src/hub_component 包。它保留编译工具和源码以方便学习，并不宣称是最小生产镜像。构建时需要已配置的软件源和网络，完成后镜像可以归档带到符合平台条件的离线机器；网站正文阅读本身不依赖联网。

#### Dockerfile 完整示例

代码类型：complete

```text

ARG ROS_IMAGE=ros:jazzy-ros-base
FROM ${ROS_IMAGE}
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
WORKDIR /work
COPY src/ src/
RUN apt-get update && \
    rosdep update --rosdistro jazzy && \
    rosdep install --from-paths src --ignore-src --rosdistro jazzy -y && \
    source /opt/ros/jazzy/setup.bash && \
    colcon build --merge-install --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    rm -rf /var/lib/apt/lists/*
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "run", "hub_component", "hub_talker_node"]

```

基础 ros-base 镜像提供构建与依赖工具；COPY 只复制本项目源码；rosdep 读取 package.xml，随后生成合并安装目录。删除 apt 索引减少无用体积，不等于删除已安装依赖。

#### entrypoint.sh 完整文件

代码类型：complete

```bash

#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
source /work/install/setup.bash
exec "$@"

```

先加载系统与工作空间环境，再用 exec 把入口进程替换为应用，使停止信号更直接到达应用。它不后台化节点，也不依赖交互式 shell 的个人启动文件。

### 固定镜像输入并验证正常停止

镜像标签便于阅读，但标签指向的内容可能变化。首次拉取后记录仓库摘要，并用摘要作为构建参数，才能固定基础镜像内容；随后 apt 安装的依赖仍可能随软件源更新，所以还要保存构建结果和包清单。保留最终镜像本身，比仅保存一份使用浮动软件源的 Dockerfile 更接近可再次运行的交付。

下面先在本机构建并运行，再进入同一个容器观察 chatter。发布消息证明入口、库和消息支持能工作，正常停止证明信号与清理路径基本可用。这个结果不包含跨容器通信、跨主机通信或设备访问；每增加一种边界，都应该用相同业务合同再检查一次。

#### 构建、启动与容器内观察

代码类型：commands

```bash

docker pull ros:jazzy-ros-base
JAZZY_BASE_IMAGE=$(docker image inspect ros:jazzy-ros-base --format '{{index .RepoDigests 0}}')
docker build --build-arg ROS_IMAGE="$JAZZY_BASE_IMAGE" -t hub-demo:local .
# 终端甲：前台运行
docker run --rm -it --name hub-demo hub-demo:local
# 终端乙：进入同一容器，复用明确的环境入口
docker exec -it hub-demo /entrypoint.sh ros2 topic echo /chatter std_msgs/msg/String
# 观察结束后停止容器
docker stop hub-demo

```

构建参数保存实际基础摘要，镜像名称 hub-demo:local 是本地标签。exec 启动观察进程时也加载工作空间，因为它不会自动继承另一个进程后来修改的 shell 环境。stop 后检查应用是否正常退出及是否有清理错误。

### 硬件、网络与配置作为显式部署边界

真实驱动通常需要特定设备文件、组权限和稳定设备标识；只授予需要的设备和资源，比把所有问题交给全特权容器更易维护。DDS 跨容器或跨主机发现需要考虑网络命名空间、多播和路由，不能因为容器内部演示成功就推断宿主机一定能看到节点。时钟同步与安全身份材料也必须按目标部署提供。

参数、地图和标定可作为只读配置输入，与运行日志分开保存。配置变更应有版本或校验值，避免镜像相同但现场文件不同造成难复现的问题。启动顺序依赖实际就绪条件：设备打开、地图可用、TF 连通和所需生命周期状态；简单延迟十秒不能证明这些条件已经满足。

### 从发布包到可回退验收

交付清单应包含入口命令、环境变量、预期节点与主题、参数值、坐标边、日志位置、停止方式以及已验证的平台。先在不加载开发工作空间的环境中执行，再从外部确认消息内容、QoS、时间与退出行为。若涉及硬件，再加入固件、设备权限和设备反馈验收，不能把进程启动当成整机成功。

保留上一版镜像与配置，先验证新版本再切换，并定义回退条件。离线导出可用 docker save，导入可用 docker load；还要检查架构与宿主机能力，并用文件校验值确认传输完整。回退应同时恢复相容配置和数据格式，否则换回旧程序仍可能读不了新配置。本章示例未在本次写作中构建容器。

#### 归档已验证的本地镜像

代码类型：commands

```bash

docker image inspect hub-demo:local --format '{{.Id}}'
docker save -o hub-demo.tar hub-demo:local
sha256sum hub-demo.tar
# 在已安装 Docker、平台相容的目标机器上
docker load -i hub-demo.tar

```

本地镜像 ID、基础仓库摘要与 tar 校验值是不同标识，均应注明用途。tar 校验值确认传输内容一致，不能代替运行验收或证明目标硬件兼容。

### 交给另一台离线学习机复现

目标机器不能临时下载依赖，需要运行组件章节的字符串发布程序。

1. 在可构建机器上固定基础摘要，构建并验收最终镜像，记录架构、镜像 ID、入口和预期消息。

2. 导出镜像并计算校验值，同时交付明确配置和验证命令；在目标机器导入前核对文件和平台。

3. 运行后检查消息内容、包前缀和停止行为，再保存目标机器的验收日志。

验收：离线机器不需要重新猜测依赖和构建路径；仍需已具备相容的容器运行环境，且本实验不包含真实设备验证。

### 深入练习 1

固定源码提交是否足以固定部署结果？

参考答案：不够。基础系统、依赖版本、编译选项、消息定义和运行配置都可能变化。应保存这些输入或最终产物，并记录实际运行验收。

### 深入练习 2

同一 Dockerfile 一个月后构建为什么可能不同？

参考答案：基础标签和软件源内容可能更新，依赖解析结果也可能变化。固定基础摘要、保存依赖版本并归档最终镜像可以改善可追溯性；只固定标签并不能锁住所有输入。

### 深入练习 3

容器中话题正常，宿主机看不到，首先应该重新编译吗？

参考答案：先查网络命名空间、发现范围、域与接口路由，再核对宿主机观察环境和 QoS。容器内部成功说明部分应用链路已工作，不能直接说明跨边界通信配置正确。

### 基础验证流程

#### 先记录工作环境

保存结果到项目自己的验证记录；不同机器对比这些信息后再排查代码。

```bash

printenv ROS_DISTRO
ros2 doctor --report
dpkg-query -W 'ros-jazzy-*'

```

#### 检查安装产物

在已经构建并 source 的独立工作空间中，确认包解析到预期 overlay。

```bash

ros2 pkg prefix atlas_cpp
ros2 pkg executables atlas_cpp

```

#### 选择明确版本的容器入口

仅在已安装 Docker 且允许联网的学习机执行。这个示例进入一个新的临时容器；不会自动获得宿主机器人的设备访问。

```bash

docker run --rm -it ros:jazzy-ros-base bash

```

#### 给部署写验收条件

列出必须出现的节点、话题类型、参数值、TF 边和退出条件。把同样的检查用于本机、容器和目标设备，并保存各次日志。

### 预期结果

- 源码、依赖和配置都有可辨认的版本记录。

- 同一套验证步骤能够区分包未安装、环境未加载、网络不通和设备未映射。

### 常见问题

- 把开发工作空间的 source 绝对路径写死到另一台机器。

- 把宿主网络、设备访问和特权模式作为所有问题的默认解决方式。

- 只打包源码，忘记安装 launch、URDF、YAML 与资源文件。

### 练习

为自己的底盘项目设计一份交付清单：别人拿到哪些文件、执行哪些命令、看到哪些证据，才算复现成功？

#### 参考答案

清单应包括源码提交、Ubuntu/ROS版本、依赖或镜像摘要、构建命令、安装产物、启动入口、参数/地图/标定及验证日志。验收至少检查节点名称、输入输出类型与QoS、TF时间一致性和退出行为。涉及硬件时另外记录固件、设备权限、接口协议和停止策略。

### 依据

- [OSRF Docker Images](https://github.com/osrf/docker_images)

- [ROS Jazzy 发行清单](https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml)

## 21. 迁移与版本边界：ROS 1、Humble 与 Jazzy

迁移不是替换几个命令名称。先列出接口与行为，再逐项迁移构建、API、参数、时间和依赖，让变化保持可验证。

### 学习目标

- 理解ROS 1与ROS 2的结构差异

- 识别Humble教程中需要重查的内容

- 为旧工程设计渐进迁移顺序

### 先修

熟悉一个ROS节点的输入输出；已明确项目目标发行版

### 概念

ROS 2 的发现与通信机制不依赖 ROS 1 的 roscore。节点参数由节点持有，回调由执行器调度；仅把 ros:: 前缀改成 rclcpp:: 不足以完成迁移。

迁移先确定外部可观察的合同：话题/服务/动作的名称与类型、坐标系、时间戳、参数含义、错误和取消行为。内部组织可以变化，但必须逐项验证这些合同。

Humble 与 Jazzy 示例常共享概念，操作系统、第三方库、Gazebo、控制器和命令类型却可能不同。选择目标发行版源码和文档作为裁决依据，旧教程作为解释材料。

ros1_bridge 需要可同时提供两端依赖和类型的兼容构建环境。其 README 明确列出 Ubuntu/ROS 组合限制；Ubuntu 24.04 上不能把它当成默认可安装的 Jazzy 软件包。

### 迁移目标是保持明确的行为合同

迁移不能只按函数名称搜索替换。先列出每个模块的输入输出名称、消息类型、单位、坐标系、时间含义、频率、超时、错误与取消行为，再确定哪些保持不变、哪些有意改变。旧程序中未写出的默认行为也属于风险来源，例如默认队列、参数缺失处理或启动先后顺序。

先选一条不直接操作设备的最小链路作为样板，把计算与通信封装分开。保留旧版本的已知输入和结果，用同一数据验证新实现。每完成一个模块都能说明“这个输入会得到什么输出”，比等所有文件都编译通过之后才排查整机更容易定位差异，也便于在某阶段失败时回退。

### ROS 1 到 ROS 2 的结构变化

ROS 2 的常见发现机制不依赖 ROS 1 的 roscore，节点参数由各节点持有，回调由执行器和回调组控制。原来的全局参数读取、同步等待与自定义线程假设都需要重新检查。服务请求发出并不等于副作用完成，动作的接受、反馈、取消和结果也应分别验证，不能仅因为接口有相似名称就视为语义相同。

构建从 catkin 迁到 ament 与 colcon 时，要更新依赖声明、消息生成、安装规则和运行入口；Python 导入从旧接口模块迁到对应 msg、srv 或 action 命名空间。迁移后应从 install 环境运行，确认程序不是偶然从源码目录找到资源。旧 roslaunch 配置也需要逐项翻译参数归属、重映射和条件，不是只改文件后缀。

### 跨发行版先建立目标平台矩阵

本教材目标是 Ubuntu 24.04 与 ROS 2 Jazzy。来自 Humble 的教程可能使用不同系统库、Python 版本、Gazebo 代际、控制器接口或插件 API；来自 Rolling 的代码则可能使用 Jazzy 尚不存在的功能。把发行版、源码分支、实际安装版本和插件类型一起写入迁移记录，才能在遇到不一致时选定裁决依据。

Gazebo Classic 的插件不能仅改一个名字就当作现代 Gazebo 插件加载；速度输入也可能是 Twist 或 TwistStamped，必须检查实际控制器，而非认定所有 Jazzy 软件都统一更换了类型。参数名相似也不保证单位和默认值相同。先通过运行端点和接口定义取证，再决定是否需要适配层。

#### 在目标环境核对真实合同

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
ros2 topic list -t
ros2 topic info /cmd_vel --verbose
ros2 interface show geometry_msgs/msg/Twist
ros2 interface show geometry_msgs/msg/TwistStamped
ros2 param list /controller_manager

```

前两条需要对应系统正在运行；controller_manager 也须实际存在。不存在应回到启动与安装检查，而非据此编造参数。接口定义说明字段，真实端点详情说明目标到底接受哪种消息。

### 桥接能够连接系统，但有平台和类型前提

ros1_bridge 需要一个能同时提供两侧依赖的可构建环境，桥接能力取决于构建时可见的接口。自定义消息通常需要先在两侧构建并提供映射，再构建桥；动态桥也可能要等匹配的发布订阅关系出现才建立连接。它不是一种把任意未知字节流自动理解成新消息的通用转换器。

截至本教材核查日，维护者支持表明确 Ubuntu 24.04 不提供 ROS 1 支持，不能把 ros1_bridge 当作 Jazzy 主机上的默认二进制依赖。旧系统若必须保留，应单独设计相容的桥接环境或明确的边界协议，并评估维护和部署成本。桥接会增加延迟、故障点和类型约束，因此仍需逐接口验收，不能把“桥启动了”当作迁移完成。

### 完整适配案例：明确新时间戳的含义

假设旧软件输出不带 Header 的速度消息，目标消费合同要求带时间戳的消息。下面完整脚本在独立教学主题间适配，接收旧消息时读取当前 ROS 时间并填入 Header。它只能声明“适配器在此时接收这条命令”，无法恢复旧消息真正产生的时刻；若旧链路可能积压，这种加戳会把旧命令伪装成新鲜输入，正式设计应在源头提供时间。

保存为 stamp_twist.py，依赖 rclpy 和 geometry_msgs。这里 frame_id 固定为 base_link，仅在旧数据的速度语义本来就相对该坐标系时成立；代码没有做坐标旋转。消息结构适配、坐标变换、单位转换和过期保护是四件不同的事，应分别定义与验证。下面所有主题均是教学名称，不连接真实控制器。

#### stamp_twist.py 完整教学适配器

代码类型：complete

```python

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped

class StampTwist(Node):
    def __init__(self):
        super().__init__('stamp_twist')
        self.publisher = self.create_publisher(
            TwistStamped, '/migration/stamped_cmd', 10)
        self.subscription = self.create_subscription(
            Twist, '/migration/legacy_cmd', self.receive, 10)

    def receive(self, message):
        output = TwistStamped()
        output.header.stamp = self.get_clock().now().to_msg()
        output.header.frame_id = 'base_link'
        output.twist = message
        self.publisher.publish(output)

def main():
    rclpy.init()
    node = StampTwist()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()

```

发布与订阅采用明确的不同主题，避免形成回路。赋给 twist 的是原消息数值；新 Header 来自适配器当前时钟。仿真使用时适配器与消费者必须一致设置 use_sim_time。

#### 在三个终端验证结构与数值

代码类型：commands

```bash

# 所有终端先 source /opt/ros/jazzy/setup.bash
# 终端甲
python3 stamp_twist.py
# 终端乙
ros2 topic echo /migration/stamped_cmd geometry_msgs/msg/TwistStamped
# 终端丙
ros2 topic pub --once /migration/legacy_cmd geometry_msgs/msg/Twist '{linear: {x: 0.2}, angular: {z: 0.1}}'

```

应看到 linear.x 与 angular.z 保持输入值，并增加 base_link 和当前接收时刻。这个观察只证明适配器按设计赋值，不能证明旧命令足够新或真实控制器接受该合同。

### 回归顺序与可回退的变更边界

回归从纯计算与接口定义开始，再测试单节点、跨语言通信、参数和完整启动；之后用固定录制输入验证时间与坐标，进入仿真，最后才在明确边界下验证设备。每一阶段都保存输入、期望结果、允许误差和失败日志。与旧系统比较时，应说明算法、依赖或时间语义是否有意变化，而不是把所有差异都算作错误或都忽略。

迁移期间保留旧环境和配置快照，在新环境使用独立工作空间，避免同时加载相互覆盖的包。对于必须改变的接口，提供清楚的适配责任与退役条件；不能让临时桥永久隐藏未迁移的关键模块。完成标准应是合同、构建、运行、诊断和部署均有对应证据。本章只提供迁移方法和教学适配器，未移植用户实机工程。

### 将旧底盘教程迁到 Jazzy

旧教程使用 Humble、某款 Classic 仿真插件和不带戳的速度消息，目标是现有 Jazzy 工程。

1. 先记录旧工程实际插件、输入类型、TF 与时钟约定，建立可重放的基线，不从教程标题猜接口。

2. 在 Jazzy 环境确认替代仿真与控制器插件、消息类型和参数；必要的适配层逐项声明单位、坐标和时间含义。

3. 先在教学或仿真主题验证，再完成启动、录包回归和部署检查；保留旧版本与配置供回退。

验收：版本变化被拆成可检查的依赖、接口和行为差异，而不是一次性全局替换 Twist 或插件名字。

### 深入练习 1

把 Twist 包装成 TwistStamped 是否恢复了原始采样时间？

参考答案：没有。接收时加戳只记录适配器接收时刻，不能知道此前排队多久。若业务依赖命令新鲜度，应让源头携带时间或使用另有明确保证的时效合同。

### 深入练习 2

旧 C++ 包编译通过但 launch 找不到参数文件，优先查什么？

参考答案：检查安装规则是否把配置复制到 share 下，以及 launch 是否通过包索引定位资源。开发目录存在文件不表示 install 中存在；再核对目标环境是否加载了正确 overlay。

### 深入练习 3

能否直接在 Ubuntu 24.04 安装 ROS 1 再默认使用 ros1_bridge？

参考答案：不能按维护者支持情况作此假设。需要同时支持两侧依赖的专门环境，并为自定义接口完成构建和映射。Jazzy 迁移计划必须把桥接平台与验证作为独立工作项，而非默认可用组件。

### 基础验证流程

#### 建立接口清单

对旧系统列出每个接口的生产者、消费者、类型、单位、频率和坐标系。优先迁移不直接驱动设备的模块。

#### 先移植一个最小包

把清晰的算法从ROS API封装中分离，建立ament包，迁移依赖声明与安装规则，使用录制数据验证输出。

#### 对照实际类型与参数

新旧版本不要根据教程标题猜输入类型；下面的检查只在已有匹配节点时有意义。

```bash

ros2 topic list -t
ros2 topic info /cmd_vel --verbose
ros2 interface show geometry_msgs/msg/TwistStamped

```

#### 安排回归顺序

先单节点与跨语言通信，再完整launch，然后回放、仿真，最后设备。每一阶段保留基线与可回退配置。

### 预期结果

- 每项变化都关联一个可检查的输入输出行为。

- 能够解释为何Twist与TwistStamped、Gazebo Classic与Harmonic不能直接混用。

### 常见问题

- 误认为 ros1_bridge 在 Ubuntu24.04/Jazzy 上有默认二进制支持。

- 把ROS 1参数服务器语义直接套到ROS 2节点参数。

- 用Rolling文档修Jazzy程序，却没有核对API所在的发布版本。

### 练习

一套Humble底盘教程使用Twist和Gazebo Classic。迁到Jazzy前，你会先核查哪四类接口？

#### 参考答案

先核查目标驱动或控制器实际订阅的速度消息类型与话题名；再核查仿真插件/ros_gz桥接及消息方向；再查TF、/clock与use_sim_time；最后核查控制器、硬件插件API、依赖和launch参数。Twist是否需要转换取决于目标节点的真实合同，不能全局替换。

### 依据

- [官方 ROS 1 → ROS 2 迁移指南](https://docs.ros.org/en/jazzy/How-To-Guides/Migrating-from-ROS1.html)

- [ros1_bridge 官方仓库与平台支持](https://github.com/ros2/ros1_bridge)

- [Gazebo 与 ROS 版本配对](https://gazebosim.org/docs/harmonic/ros_installation/)

- [diff_drive_controller 参数与接口](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)

## 22. tf2：坐标树、时间戳与外参

tf2 保存随时间变化的坐标关系。查询不仅需要两个 frame，还需要数据对应的时间。

### 学习目标

- 把传感器观测变换到机器人或地图坐标系

- 用工具排查断链、方向与时间问题

### 先修

已安装 ROS 2 Jazzy；每个新终端先 source /opt/ros/jazzy/setup.bash。

### 概念

tf2 保存随时间变化的坐标关系。查询不仅需要两个 frame，还需要数据对应的时间。

静态外参表达固定安装关系；运动关系需要动态发布。坐标树要求每个子 frame 有明确父节点，避免多个发布者竞争同一关系。

常见移动机器人链是 map → odom → base_link → sensor。不同边由不同模块负责，不能重复发布。

### 一个坐标数值必须带上坐标系和时刻

激光报告前方一点距离一米，只能说明它相对激光原点的位置。若激光安装在车体前方二十厘米，那么同一点在车体坐标系的前向坐标是一点二米。坐标变换改变的是同一几何对象的表示，不能只改消息中的 frame_id 而保留原来的数值；那样相当于把一个不同位置的点冒充原观测。

约定目标坐标系为 A、源坐标系为 B，变换写成 p_A = R_AB p_B + t_AB。lookup_transform 的前两个参数正是目标、源：它返回把源中的数值转换到目标所需的变换。反向变换需要旋转矩阵转置和负的旋转后平移，只有没有旋转的特殊情况才是直接把平移取负。

### 树结构与每条边的责任

一棵 TF 树中，每个子坐标系在同一有效关系中应有明确父坐标系，不能形成环。移动机器人常把全局修正放在 map 到 odom，把连续局部运动放在 odom 到 base_link，再通过固定外参连接传感器。每条边只由职责明确的模块维护，两个模块同时抢发同一子坐标系会让跳变难以解释。

固定安装关系通过静态广播器发布到 /tf_static；车轮里程计、关节运动等关系通过动态广播发布到 /tf。静态关系对查询时刻不随时间变化，但仍要让订阅者确实获得这条边。动态关系需要时间序列，缓冲区仅保留有限历史。发布一个看起来正确的当前姿态，不能回答已经被丢弃的很久以前姿态。

### 先用可手算的外参检验方向和单位

以下实验只创建 base_link 到 laser 的静态关系，平移单位是米，欧拉角参数单位是弧度。保持静态广播器运行，在另一终端查询正反方向。正向应得到约零点二、零、零点三的平移；反向在本例无旋转时为对应负数。再用激光中的点一、零、零手算车体中的一点二、零、零点三。

若观察结果与预期相反，先画出父子关系和源、目标的箭头，再考虑是否写错数值。四元数采用四个分量表示旋转，需要是有效的单位四元数；不能把三个欧拉角直接填进其前三项。相机光学坐标轴与车体常用坐标轴不同，外参应包含方向转换，不能只关注安装位置。

#### 建立并检查固定安装关系

代码类型：commands

```bash

# 终端甲，先 source /opt/ros/jazzy/setup.bash
ros2 run tf2_ros static_transform_publisher --x 0.2 --y 0 --z 0.3 --roll 0 --pitch 0 --yaw 0 --frame-id base_link --child-frame-id laser
# 终端乙：分别运行并观察，Ctrl+C 后切换下一条
ros2 run tf2_ros tf2_echo base_link laser
ros2 run tf2_ros tf2_echo laser base_link
ros2 run tf2_tools view_frames

```

前两个 frame 参数决定查询方向；view_frames 汇总一段观察窗口内收到的树，生成的图可用来找断链和重复责任，但图形连通并不自动证明每个历史时刻均有可用数据。

### 查询采样时刻，理解最新与当前的差别

传感器消息的 header.stamp 应表示数据对应的采样时刻，算法一般要查询该时刻的变换。用接收时刻替代，会把传输延迟期间机器人的运动混入空间误差。速度每秒一米、延迟一百毫秒，就可能仅因时间错位产生十厘米位置偏差；机器人转弯时还会产生与观测距离相关的角度误差。

零时间在 TF 查询中有特殊含义，表示最新可用变换；它不是“此刻”，多段动态链路还要满足共同可用时间。查询 now 时最新 TF 可能尚未到达，出现向未来外推；查询过旧观测则可能早于缓存。增大等待超时只能等待未来到达的数据，不能制造已丢失历史，也不能修复一台机器使用系统时间、另一台使用仿真时间的错误。

### 非阻塞地消费带时间戳的点

下面完整脚本保存为 point_transform.py，依赖 rclpy、geometry_msgs、tf2_ros 和 tf2_geometry_msgs。它订阅 /sensor_point，按原始时间查询到 base_link 的变换，成功后发布 /base_point。查询不设置阻塞等待，因此单线程执行器仍有机会处理 TF 订阅；如果暂时缺少变换，本教学程序明确丢弃该点并记录原因。

生产应用若不能丢弃，应加入有界待处理队列或合适的消息过滤机制，等待对应 TF 到达，再按采样顺序处理，并设最大等待时间。不要在同一个单线程回调中长时间等待还需要该线程接收的 TF。例子将输出时间保留为原观测时刻，让下游知道坐标换了，而数据并没有因此变新。

#### point_transform.py 完整文件

代码类型：complete

```python

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import PointStamped
from tf2_ros import Buffer, TransformListener, TransformException
from tf2_geometry_msgs import do_transform_point

class PointTransformer(Node):
    def __init__(self):
        super().__init__('point_transformer')
        self.buffer = Buffer(node=self)
        self.listener = TransformListener(self.buffer, self)
        self.publisher = self.create_publisher(PointStamped, '/base_point', 10)
        self.subscription = self.create_subscription(
            PointStamped, '/sensor_point', self.receive, 10)

    def receive(self, message):
        if not message.header.frame_id:
            self.get_logger().warning('empty source frame')
            return
        try:
            transform = self.buffer.lookup_transform(
                'base_link', message.header.frame_id,
                Time.from_msg(message.header.stamp))
        except TransformException as error:
            self.get_logger().warning(f'point dropped: {error}')
            return
        result = do_transform_point(message, transform)
        result.header.stamp = message.header.stamp
        self.publisher.publish(result)

def main():
    rclpy.init()
    node = PointTransformer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()

```

Buffer 保存收到的关系，TransformListener 建立 TF 订阅；Time.from_msg 把输入时间转换为查询类型；do_transform_point 同时计算旋转和平移。异常表示当前无法完成这一坐标请求，不能悄悄把未变换数据标为目标坐标系。

#### 仅针对上面的静态关系进行数值验证

代码类型：commands

```bash

# 保持静态广播器运行，另开终端运行脚本
python3 point_transform.py
# 再开终端观察输出
ros2 topic echo /base_point geometry_msgs/msg/PointStamped
# 最后一个终端发送测试点；省略 stamp 得到零时间
ros2 topic pub --once /sensor_point geometry_msgs/msg/PointStamped '{header: {frame_id: laser}, point: {x: 1.0, y: 0.0, z: 0.0}}'

```

本次只验证固定外参，零时间查询最新关系足够。动态机器人数据必须使用真实采样时间，不能照搬省略 stamp 的测试输入。预期输出 frame_id 为 base_link，坐标约为 1.2、0、0.3。

### 先分类型再排查时间与发布来源

找不到坐标系时，检查拼写、命名空间是否误加到 frame 名以及广播者是否存活；树不连通时，查缺失的中间边和父子责任；时间外推时，保留请求时间、最早和最新可用时间、各节点 use_sim_time 与 /clock 来源。三个问题的解决路径不同，不能统一用加大 timeout 处理。

对于实机跨计算机数据，检查时钟同步和驱动是否把设备时钟转换到约定时间基准；对于回放，检查 TF 与传感器是否来自同一次记录，以及回放跳转后缓存是否被重建。不要把所有 frame 强行连接到世界原点来消除报错，这会把可诊断的缺边变成隐蔽的错误几何。本章为资料核对与推演，未验证目标机器的外参。

### 激光点在转弯时拖出重影

静止时点云与地图重合，转弯时明显拖尾，传感器消息晚于采样一百毫秒到达。

1. 检查传感器 header 是否记录采样时刻，比较处理代码是否用 now 或零时间查询。

2. 读取相同时间段的 odom 到 base_link 及固定激光外参，按消息原时间计算变换。

3. 若原时间不在缓存中，再查延迟、缓存长度和时钟；只在确认关系稍晚到达时采用有界等待。

验收：空间误差被分解为安装外参、时间错位和缓存可用性三类，不能用静态外参调偏来补偿随速度变化的时间误差。

### 深入练习 1

laser 相对 base_link 前移零点二米，laser 中 x=1 的点在车体中 x 是多少？

参考答案：无旋转时为一点二米，因为目标坐标等于源坐标加激光原点在车体中的位置。反向查询应使用逆变换；存在旋转时先旋转再平移，不能只给 x 加常量。

### 深入练习 2

查询 now 报未来外推，是否说明系统时间来自未来？

参考答案：不一定。TF 生成与传输需要时间，查询时最新变换可能比 now 早几毫秒。先比对时间差与时钟来源；合理延迟可用有界等待解决，巨大时间差则优先查时间基准。

### 深入练习 3

把旧点的 frame_id 改为 map 后发布，为什么不是坐标变换？

参考答案：数值仍表示旧坐标系中的位置，修改标签没有应用旋转和平移。应在原采样时刻查询从源到 map 的变换并计算新坐标，同时保留观测时间。

### 基础验证流程

先用静态广播器建立 base_link → laser。

用 tf2_echo 检查方向和平移。

运行 view_frames 观察树结构。

再加入带 Header 的传感器数据，按其时间戳查询变换。

#### 终端 A：显式参数静态变换

```bash

ros2 run tf2_ros static_transform_publisher --x 0.2 --y 0 --z 0.3 --roll 0 --pitch 0 --yaw 0 --frame-id base_link --child-frame-id laser

```

#### 终端 B：检查

```bash

ros2 run tf2_ros tf2_echo base_link laser
ros2 run tf2_tools view_frames

```

### 预期结果

- laser 相对 base_link 的位置与输入一致。

- 能分清缺少 frame、树不连通和时间外推三类错误。

### 常见问题

- 交换 target/source 后误以为结果数值应不变。

- 混用角度制和弧度制，或给四元数填入欧拉角。

- 实机时间与 use_sim_time 混用，导致变换时间不在缓存范围。

### 练习

再添加 camera_link，解释如何由 tf2 合成 laser 到 camera_link 的变换。

#### 参考答案

给 camera_link 也定义相对 base_link 的固定外参。查询 camera_link 与 laser 的关系时，tf2 沿树组合一条变换及另一条的逆变换。查询时明确目标坐标系和源坐标系，先用已知点验证方向；固定外参只需静态发布，避免重复动态发布同一边。

### 依据

- [tf2 C++ / Python 教程路线](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html)

- [静态 TF 与命令行广播器](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html)

- [ROS 时间设计](https://design.ros2.org/articles/clock_and_time.html)

## 23. tf2：建立一致的坐标与时间关系

机器人并不是只有一个位置。激光、相机、车体和地图分别拥有坐标系，tf2 负责在指定时刻把数据从一个坐标系换算到另一个。先画出树，再写广播器，通常比到 RViz 中反复调整更有效。

### 学习目标

- 分清 map、odom、base_link 和传感器坐标系

- 区分静态标定与运动变换

- 能通过 CLI 定位断开的 TF 边

### 先修

节点与话题；时间戳与 ROS 时钟；三维平移与四元数基础

### 概念

map→odom 表示全局定位对局部里程计的修正；odom→base_link 应连续，适合短时间控制，但允许长期漂移。

base_link→laser 等固定安装关系用静态变换；关节引起的动态关系由 robot_state_publisher 根据 joint_states 计算。

一次变换查询同时约束源坐标系、目标坐标系和时间。时间超出缓存范围也会失败，不能只看 frame 名字是否存在。

### 先把位置问题写成坐标问题

一个激光点的数值只有连同坐标系和采样时刻才有意义。雷达测得前方一米，指的是雷达自身轴向；雷达装在车头偏左的位置时，这个点在车体坐标中会改变。tf2 保存坐标关系，使每个算法不必自己维护整套安装和运动关系。它不负责判断定位是否准确，也不会从图像或编码器自动推导缺失的变换。

本章使用三个层次：世界或地图、连续局部里程计、车体与传感器。地图允许全局定位修正，里程计要求短时间平滑，车体内部关系来自机械安装和关节状态。先把每条边的发布者写在纸上，再运行节点，可以提前发现两个节点同时声明同一关系的问题。

### 理解变换的方向和复合

把激光坐标中的点变换到车体坐标时，先按激光坐标轴相对车体的旋转转动点，再加上激光原点在车体中的平移。交换源和目标得到的是逆变换，不能只把平移改为负数而保持旋转不动。多级变换按照路径依次相乘，顺序通常不可交换。

ROS 常用右手坐标约定：车体向前为 x、向左为 y、向上为 z。相机 optical frame 常用另一种专门约定，不能因为模型画面看起来正确就省略它与 camera_link 的旋转。四元数应为合法单位四元数；全零不是没有旋转，单位四元数的 w 为一。

- 长度使用米，角速度使用弧度每秒；角度命令需检查是欧拉角还是四元数。

- 命名空间不会自动重写消息内的 frame_id。

### 给每条消息定义时间与发布合同

TF 动态关系通过 /tf 发布，固定安装关系通过 /tf_static 发布。静态广播使用适合晚加入订阅者的持久性语义，因此传感器节点晚启动仍能取得安装关系。动态广播则需要连续更新，缓存只能回答其保存时间范围内的问题。查询失败既可能是树不连通，也可能是请求时间落在缓存之外。

传感器 header.stamp 应表达测量发生的时间，而不是任意改成算法收到消息的时间。仿真时让传感器、TF 与消费节点都使用同一个 /clock；实机上则要同步主机和设备时间。将查询改成最新变换能够帮助诊断，却可能把延迟数据投到错误位置，不能视作所有时间问题的正式修复。

### 最小实验：定义一个雷达安装位置

实验只需要已安装 Jazzy 与 tf2_ros。每个新终端先执行 source /opt/ros/jazzy/setup.bash。终端一保持静态发布进程运行，终端二执行查询。下面命令为可复现实验说明，本次编写时没有启动 ROS 节点。它只发布坐标关系，不会向底盘发送运动命令。

这里假定雷达在车体前方二十厘米、上方十五厘米，方向与车体一致。先查询车体到雷达，再交换顺序。由于旋转为单位旋转，这个特例的逆变换平移恰好取负；随后把 yaw 改为九十度，就能观察为什么一般情况不能仅取负。

#### 终端一：静态安装关系

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
ros2 run tf2_ros static_transform_publisher --x 0.2 --y 0 --z 0.15 --roll 0 --pitch 0 --yaw 0 --frame-id base_link --child-frame-id laser

```

保持进程运行；修改参数时先停止旧进程，防止两个发布者同时声明 laser。

#### 终端二：查询与检查

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
ros2 run tf2_ros tf2_echo base_link laser

```

输出平移应为指定安装位置。结束查询后可交换两个 frame 名重复实验。

### 把实验扩展成一棵真实机器人树

通常由定位或建图节点发布 map 到 odom，由轮式里程计或融合节点发布 odom 到 base_link，由 robot_state_publisher 发布车体内部关系。传感器安装也可以放进 URDF 的固定关节，此时不要再另外运行同名静态发布者。对旋转云台等运动部件，关节状态必须随测量更新。

检查时从局部到全局逐段证明连通性。先确认 base_link 到 laser，再确认 odom 到 base_link，最后确认 map 到 odom。只在 RViz 使用 map 显示整个系统，容易把最末端的缺失关系误认为地图问题。一个稳定的 TF 树不应存在环，每个 child 应有明确且唯一的父节点。

#### 有完整机器人后执行

代码类型：commands

```bash

ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo odom base_link

```

需要安装 tf2_tools；生成树图后对照预先画出的发布责任表。

### 用现象定位失败层次

报 unknown frame 时先检查名字和发布者是否存在；报无法连接时检查中间边；报过去外推时检查消息是否过旧或缓存是否太短；报未来外推时检查时间源、时间偏差和最新 TF 是否滞后。增大等待时间只能处理短暂到达顺序问题，无法修正两个时钟相差几分钟的系统。

如果点云会偶尔跳动，除了定位算法，还要检查重复发布和时间戳。把 odom 到 base_link 的发布者缩减到一个，录制 /tf、/tf_static 和原始传感器后再重放。验收不仅是查询成功，还应包括静止时关系稳定、运动时变化连续，以及在传感器实际时间戳处可以查询。

可以用一个已知位置的点检查变换方向：令雷达前方一米的点为输入，在无旋转安装条件下，车体坐标应为前方一米二、上方十五厘米。先手算再与程序结果比较，这比只确认 TF 树连通更能发现父子关系写反或单位混用。

### 给一台差速小车接入前置雷达

雷达安装正确，但 RViz 使用 map 作为 Fixed Frame 后仍无法显示扫描。

1. 证明 base_link 到 laser 可查询，排除安装边缺失。

2. 证明 odom 到 base_link 连续更新，确认里程计发布者。

3. 发现 map 到 odom 尚未发布；启动定位或在无全局定位的实验中暂用 odom 显示。

4. 核对扫描时间与 TF 时间同属仿真时钟后再观察。

验收：显示恢复的原因是补齐正确层次的坐标关系，而非修改雷达数据。

### 深入练习 1

为什么静态坐标关系不能用每帧最新测量来回覆盖？

参考答案：固定安装关系应保持稳定。若安装会变化，它就是动态关系，需要真实关节测量和正确时间戳，而不是多个节点竞争发布。

### 深入练习 2

查询最新变换能消除时间问题吗？

参考答案：它可能避免缓存外推报错，但延迟传感器会被转换到错误时刻的机器人姿态，运动中产生几何误差。

### 深入练习 3

EKF 与底盘都发布 odom→base_link 会怎样？

参考答案：同一 child 的来源竞争可能造成跳变和不一致，应保留一个负责该边的发布者，另一方仅发布测量话题。

### 基础验证流程

#### 先做一个完全独立的静态变换实验

在已经 source Jazzy 的终端发布一个传感器安装位姿。此命令只发布坐标关系，不控制任何设备。

```bash

ros2 run tf2_ros static_transform_publisher --x 0.2 --y 0 --z 0.15 --roll 0 --pitch 0 --yaw 0 --frame-id base_link --child-frame-id laser

```

#### 从另一个终端查询

观察查询结果是否保持不变，再交换两个 frame 的顺序，解释逆变换的含义。

```bash

ros2 run tf2_ros tf2_echo base_link laser

```

#### 接入已有机器人后检查完整链

安装 tf2_tools 后生成坐标树。先分别证明 map→odom、odom→base_link、base_link→laser 可查询，再观察完整链。

```bash

ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo odom base_link

```

#### 将时间当成接口的一部分

仿真节点统一使用 use_sim_time；真机传感器使用同步后的时间。查日志中的 extrapolation 方向，而不是增大所有超时来隐藏错误。

### 预期结果

- 静态实验中 base_link 到 laser 的平移为设置值，重复查询保持一致。

- 完整机器人每个子 frame 有明确且唯一的父关系。

### 常见问题

- 同一条 TF 边被 EKF 与底盘驱动同时发布会导致跳变。

- frame_id 不带前导斜杠；命名空间不自动改变消息内的 frame_id。

- 把仿真时间与系统时间混用，通常会出现过去或未来外推错误。

### 练习

设计一台带雷达、IMU、云台相机的底盘 TF 树，逐条写出发布者与静态/动态属性，并验证相机到地图的完整查询。

#### 参考答案

可采用 map→odom→base_link→laser、base_link→imu_link 和 base_link→pan_link→camera_link→camera_optical_frame。map→odom 由定位/SLAM 发布，odom→base_link 由轮式里程计或融合节点发布，固定传感器安装边为静态。

云台可动关节由关节状态和 robot_state_publisher 发布动态变换。验收时每个 child frame 只能有一个有效父关系；在传感器消息时间处可查询 camera_optical_frame 到 map。

### 依据

- [geometry2／tf2 Jazzy 源码](https://github.com/ros2/geometry2/tree/jazzy)

- [robot_state_publisher 源码](https://github.com/ros/robot_state_publisher/tree/jazzy)

- [Nav2 首次机器人接入指南](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/)

## 24. URDF、Xacro 与 RViz：把机器人描述变成可检查模型

用 URDF 表达刚体和关节，用 Xacro 把尺寸及重复结构参数化，再用 RViz 检查坐标、外观和关节关系。模型不仅服务显示，还会影响碰撞检测、运动学与控制器中的关节名称。

### 学习目标

- 建立 link/joint 的树状结构

- 理解 visual、collision、inertial 的职责

- 将模型、关节状态和 TF 三者对应起来

### 先修

tf2 坐标树；XML 基础；ROS 包资源路径

### 概念

visual 只决定显示，collision 决定碰撞几何；惯量和质量进入动力学计算，不能用随意的零值敷衍。

Xacro 是生成 URDF 的宏语言；先展开再检查，可以把宏求值问题与模型问题分开。

robot_state_publisher 消费模型和 joint_states，RViz 消费 TF 与显示消息；两者都不是物理模拟器。

### 模型是多个模块共享的结构合同

URDF 用 link 描述刚体，用 joint 描述刚体之间的连接。一个轮子是一个 link，轮轴约束由 joint 表达；传感器固定安装也通过 fixed joint 连接。模型应构成树，模型中的名字会继续出现在 joint_states、控制器参数和运动规划配置中，因此名字属于跨模块接口，不能只为了显示方便随意改变。

同一个 link 可以有不同的 visual 和 collision。前者决定外观，后者决定接触与碰撞检测；为了计算效率，复杂网格常用简单几何近似碰撞体。质量与惯量描述动力学。RViz 可以显示一个没有合理惯量的模型，但物理仿真可能发散，所以外观正确只是第一层验收。

### 理解关节原点、轴和状态的关系

joint 的 origin 定义子关节坐标相对父 link 的安装变换，axis 定义在关节坐标中的运动方向。车轮的旋转轴通常不沿车体前进方向。若左右轮使用镜像模型，要分别核对正方向，不能只凭 mesh 外观推断编码器符号。continuous 用于连续旋转，revolute 需要上下限，fixed 没有可变关节状态。

robot_state_publisher 读取 robot_description，并结合 JointState 中的关节位置发布 TF。它不会从速度目标积分出正确轮子位置，也不会提供底盘全局位姿。joint_state_publisher 可以为显示提供人为关节值，实际运行时应由硬件或控制系统提供真实状态，避免两套状态同时驱动模型。

### 先制作可独立打开的最小描述

把下面完整 XML 保存为 robot.urdf。它只包含车体和固定雷达，用于验证资源、模型和 TF 链，不包含车轮、电机、碰撞规划或惯量求解。使用最小模型能使显示问题与复杂机械结构分离。本章代码和命令未经本次 ROS 运行验证，读者应按输出判据逐步检查。

模型尺寸使用米，颜色值在零到一之间。雷达的几何中心与 link 原点在此示例中重合，因此 joint origin 就是安装位置。增加 mesh 时优先使用 package:// 资源地址，并让安装规则把资源复制到包的 share 目录；个人电脑上的绝对路径无法被其他工作区可靠解析。

#### robot.urdf：完整的最小显示模型

代码类型：complete

```xml

<?xml version="1.0"?>
<robot name="learning_base">
  <link name="base_link">
    <visual>
      <geometry><box size="0.4 0.3 0.12"/></geometry>
      <material name="body"><color rgba="0.15 0.4 0.55 1"/></material>
    </visual>
    <collision><geometry><box size="0.4 0.3 0.12"/></geometry></collision>
  </link>
  <link name="laser">
    <visual>
      <geometry><cylinder radius="0.04" length="0.05"/></geometry>
      <material name="sensor"><color rgba="0.9 0.5 0.1 1"/></material>
    </visual>
  </link>
  <joint name="base_to_laser" type="fixed">
    <parent link="base_link"/><child link="laser"/>
    <origin xyz="0.15 0 0.1" rpy="0 0 0"/>
  </joint>
</robot>

```

这是显示/TF 教学文件，未提供用于物理仿真的惯量与传感器插件。

### 按模型、状态、显示的顺序启动

在已经安装 urdf_tutorial、robot_state_publisher 和 RViz 的环境中，可用官方 display launch 加载刚保存的文件。终端当前目录要包含 robot.urdf；路径应展开成完整路径。启动后先把 RViz Fixed Frame 设为 base_link，再打开 RobotModel 和 TF，检查雷达是否处于车头上方。

只有固定关节时，即使没有持续 joint_states，固定边也应出现。加入活动关节后才需要关节状态，状态数组中的 name 与 position 必须对应，位置单位通常为弧度或米。先确认 TF 变化，再看 mesh 是否跟随，能区分状态问题与资源显示问题。

#### 加载本地文件

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
ros2 launch urdf_tutorial display.launch.py model:="$(pwd)/robot.urdf"

```

此命令依赖已安装的教学包。可在另一个终端执行 tf2_echo base_link laser 检查安装关系。

### 用 Xacro 消除尺寸与重复结构的不一致

当左右轮、螺栓或传感器结构重复时，复制 XML 很容易遗漏一次修改。Xacro 允许定义尺寸属性和结构宏，最终仍展开成普通 URDF。应先单独展开文件并检查输出，再交给 launch；这样宏错误不会被大量启动日志淹没。

参数化不应只覆盖外观。轮半径和轮距还进入控制器运动学，关节名称进入控制资源清单。可以让同一份工程配置生成各文件，或至少在验收清单中比较两边值。Xacro 中修改一个尺寸，并不会神奇地修改独立 YAML 中的数字，维护者仍需建立它们的关联。

#### 展开并检查

代码类型：commands

```bash

xacro robot.urdf.xacro > /tmp/learning_robot.urdf
check_urdf /tmp/learning_robot.urdf

```

第二条需要 urdfdom 工具。结构检查通过仅证明树和语法基本成立，不证明质量、惯量与单位正确。

### 把模型验收分成四个层次

第一层是语法和树结构，确认没有重复 link、断开的 joint 或多个根。第二层是坐标，检查轮轴、传感器轴和光学轴。第三层是资源，确认 mesh 与材料可以在安装后的 share 路径找到。第四层才是动力学与控制，核对惯量正定、关节限位、碰撞几何和导出的控制接口。

常见现象可以按层判断：模型完全不出现时先查 robot_description 和 Fixed Frame；单个部件缺失时查资源路径与父子关系；关节转反时查 axis、驱动符号和状态单位；仿真爆炸时查碰撞穿透、质量、惯量及步长。不要在 RViz 中随意旋转显示来掩盖源模型的轴向错误。

### 组织文件与保证安装后仍能打开

建议把描述文件放在 description 或 urdf 目录，网格放 meshes，显示配置放 rviz，启动文件放 launch。包的安装规则应覆盖这些目录，使用者通过包的 share 路径查找资源，而不依赖源码目录。检查时先构建并 source 安装空间，再从另一个当前目录启动同一模型，能够发现被本地相对路径掩盖的问题。

修改一个 link 或 joint 的名称后，搜索模型、控制器、状态发布和规划配置中的所有引用，并重新生成 TF 图。把命名表作为模型的一部分维护，避免同一机械部件在不同文件中使用多个近似名字。版本记录应包含模型参数，而不只是 mesh 文件；轮距、工具偏置和安装旋转的变化都可能改变算法结果。

### 为已有底盘增加雷达

模型已能显示，但新增雷达与扫描相差九十度。

1. 单独展开 Xacro，确认固定关节安装位置。

2. 显示 TF 坐标轴，区分 laser 与 camera optical 等不同约定。

3. 核对驱动消息的 frame_id 是否正是新增 link。

4. 在 URDF 中修正真实安装旋转，重新启动发布者。

验收：雷达模型、扫描方向与 TF 坐标一致，修改保持在唯一的模型来源中。

### 深入练习 1

visual 和 collision 能否使用不同形状？

参考答案：可以。显示网格可详细，碰撞体可简化，但简化必须覆盖实际需要避免的接触区域。

### 深入练习 2

为什么 joint_state_publisher 不能替代编码器反馈？

参考答案：它提供人为或默认关节值，不代表实际测量。用于实机状态会让显示与真实机械状态脱离。

### 深入练习 3

Xacro 改了轮距，控制器会自动改变吗？

参考答案：不会。独立 YAML 仍保留原值，需要共同配置来源或明确同步和校验。

### 基础验证流程

#### 检查可用教学包

需要安装 Jazzy 的 urdf_tutorial、xacro、robot_state_publisher 与 RViz 相关包。先确认包资源目录。

```bash

ros2 pkg prefix --share urdf_tutorial
ros2 pkg prefix --share robot_state_publisher

```

#### 运行官方最小模型

下面命令引用已安装教学包中的模型，不依赖当前目录。

```bash

ros2 launch urdf_tutorial display.launch.py model:="$(ros2 pkg prefix --share urdf_tutorial)/urdf/01-myfirst.urdf"

```

#### 将自己的模型展开为 URDF

把 robot.urdf.xacro 替换为实际文件；先检查展开结果，再接入 launch。

```bash

xacro robot.urdf.xacro > /tmp/robot.urdf

```

#### 在 RViz 分层排查

先设置 Fixed Frame 为模型根 frame，启用 TF 与 RobotModel；再观察 /joint_states。没有关节状态时不要先修改 mesh。

```bash

ros2 topic echo /joint_states --once

```

### 预期结果

- RViz 模型显示与设计的坐标树一致。

- 调整关节时，对应子 link 和 TF 一起变化。

### 常见问题

- joint 名称在 URDF、控制器 YAML 和 JointState 中必须逐字一致。

- mesh 路径优先用 package://；绝对个人路径无法在另一台机器复现。

- URDF 显示正确不代表碰撞模型、惯量或控制接口正确。

### 练习

把一个双轮底盘的轮距和轮半径改成 Xacro 参数，增加雷达 link，并用 TF 显示核对轴向。

#### 参考答案

轮距和轮半径设置为 Xacro 属性或参数，左右轮位置由同一轮距参数的正负一半生成；控制器参数也必须使用对应数值或由同一配置来源生成。

雷达 link 通过 fixed joint 连到 base_link；展开 Xacro 后核对 joint 名称、轮轴方向和 TF。改变参数后模型与控制配置若不一致，视为练习未完成。

### 依据

- [URDF 官方教程源码](https://github.com/ros/urdf_tutorial/tree/ros2)

- [Xacro 项目](https://github.com/ros/xacro)

- [robot_state_publisher 源码](https://github.com/ros/robot_state_publisher/tree/jazzy)

- [RViz2 源码与说明](https://github.com/ros2/rviz/tree/jazzy)

## 25. Gazebo Harmonic：仿真、桥接与统一时钟

先把仿真世界跑起来，再桥接一个消息，最后接入控制器。这样可以区分物理模型、Gazebo Transport、ROS 消息和控制器四个层次。Jazzy 路线使用现代 Gazebo Harmonic。

### 学习目标

- 辨认 Gazebo 与 ROS 的两个通信图

- 显式配置桥接方向和类型

- 让传感器、TF、导航共用仿真时间

### 先修

URDF/Xacro；话题类型与 QoS；use_sim_time

### 概念

ros_gz_bridge 只转换已经支持的消息类型，并非任意消息的自动桥。

/clock 是仿真时间源；需要仿真时间的 ROS 节点必须开启 use_sim_time。

gz_ros2_control 把仿真关节作为硬件后端，controller_manager 与控制器仍运行相同的 ROS 控制接口。

### 先区分模拟器、传输桥和机器人算法

Gazebo 计算世界中的物理和传感器，Gazebo Transport 传送模拟器消息，ros_gz_bridge 在已支持的 ROS 与 Gazebo 类型间转换，ROS 节点再处理数据。机器人在 Gazebo 中出现，不等于 ROS 已经收到传感器；ROS 能看到话题，也不等于控制器真正驱动了模拟关节。

Jazzy 与 Ubuntu24.04 的本章主线使用 Harmonic。旧 Gazebo Classic 的插件名、启动包与模型搜索变量不能直接迁移使用。先固定这三个版本，再选择 ros_gz 与 gz_ros2_control，能避免把不同代的仿真接口拼在同一个工程里。

### 用一个文件定义可观察的世界

下面的 SDF 是独立最小世界，包含物理、用户命令和场景广播系统。它不包含机器人，目的是证明世界可以运行并产生时间。将文件保存为 learning.sdf，在有可用图形环境的终端启动。此处给出的是实验文件和运行方法，本次没有实际启动 Gazebo。

世界文件决定物理步长与实时目标。仿真时间每一步增加多少与墙上时钟走了多少是两个概念。机器算力不足时实时因子可能下降，但正确使用仿真时间的机器人算法仍能按仿真时间理解事件；若一部分节点坚持使用系统时间，时间关系就会被破坏。

#### learning.sdf：完整最小世界

代码类型：complete

```xml

<?xml version="1.0"?>
<sdf version="1.9">
  <world name="learning">
    <physics name="default" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
  </world>
</sdf>

```

完整世界文件只验证时间与基础系统；没有机器人、地面和传感器。

### 把桥接配置当作明确的数据合同

每条桥都应列出 Gazebo 话题、ROS 话题、两端消息类型和方向。时钟通常只从模拟器流向 ROS，速度命令通常从 ROS 流向模拟器，传感器通常反向。随意开启双向桥会引入重复发布或循环，最小权限式的数据方向也更便于排错。

下面配置将 /clock 单向转换成 rosgraph_msgs/msg/Clock。如果你的世界只发布 /world/learning/clock，就把 gz_topic_name 改成实际列出的名字，ROS 一侧仍可保持 /clock。不要靠猜测桥接消息存在，先查看 Gazebo 话题，再查看 ROS 输出。

#### bridge.yaml：完整时钟桥配置

代码类型：complete

```yaml

- ros_topic_name: /clock
  gz_topic_name: /clock
  ros_type_name: rosgraph_msgs/msg/Clock
  gz_type_name: gz.msgs.Clock
  direction: GZ_TO_ROS

```

可继续追加传感器映射；每条映射需要检查 ros_gz_bridge 是否支持该类型。

### 按世界、桥、算法的次序运行

首先启动世界并让其运行，再启动桥接器，确认 ROS 收到时钟后才启动依赖仿真时间的算法。每个 ROS 终端先 source Jazzy。启动命令中的 config_file 使用绝对路径，避免不同终端当前目录造成“文件存在但加载不到”的误解。

暂停世界时，/clock 数值应停止推进，恢复后继续增长。观察节点的定时器是否跟随暂停：使用 ROS 时钟的定时器和基于墙上时钟的监控逻辑可能有不同表现，这种区别应该是设计选择。一次实验只启用一个时钟源，避免回放 bag 时另一个模拟器还在发布 /clock。

#### 三个独立终端的操作

代码类型：commands

```bash

gz sim -r learning.sdf
# 在另一个已 source Jazzy 的终端运行：
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:="$(pwd)/bridge.yaml"
# 在第三个终端检查：
ros2 topic echo /clock --once

```

前两个命令是常驻进程，必须在不同终端运行。

### 再接入机器人、传感器和控制器

机器人模型进入 Gazebo 后，需要质量、惯量、碰撞与关节结构形成有效物理对象。添加激光或相机时，还需要对应传感器系统和插件配置。先从一个传感器开始，列出频率、frame、噪声和消息编码，再在 RViz 检查几何方向。显示帧率不一定等于传感器采样频率。

使用 gz_ros2_control 时，仿真关节成为 ros2_control 的硬件后端。控制器看到的状态和命令接口可以与实机一致，但摩擦、延迟与饱和不会自动等同真实设备。保持同一控制接口有利于迁移，仍需用实测数据逐项校准模型，而不是把模拟成功视为最终硬件验收。

### 建立分层输出判据

世界层验收是时间持续推进且模型物理稳定；桥层验收是两端类型、方向和频率符合合同；算法层验收是参数时钟与 TF 一致；控制层验收是目标、关节状态和里程计形成预期关系。每层至少保留一个命令行观测点，使失败时不必只盯着三维画面猜测。

若模拟器有激光但 ROS 无话题，查桥配置和类型；ROS 有数据但 RViz 不显示，查 Fixed Frame、TF 和 QoS；机器人抖动或穿地，查惯量、碰撞和步长；控制器 active 却不动，查 joint 名、接口 claimed 状态和实际后端。把这些问题分开修复，避免同时调多个无关参数。

### 保存一套可迁移的仿真实验目录

把 learning.sdf、bridge.yaml、机器人描述、控制器配置和 RViz 配置放在同一个学习包中，并记录启动顺序。地图、模型材质或其他外部资源若由远程服务器首次下载，应说明缓存条件；网页能离线阅读不代表所有模拟资产已经在每台电脑存在。为了复现实验，应优先固定小型本地模型和确定的参数。

结束实验时先停止发送控制命令，再停止算法、桥和世界，避免下次运行仍有旧发布者。新实验开始前检查 /clock 和相关话题的发布者数量。若不同启动文件被重复运行，多个机器人状态发布者或桥接器可能同时存在，表现为重复数据而非明显启动错误。把进程生命周期也列入实验记录，才能区分模型问题与环境残留。

### 定位一个“导航启动后一直等待”的仿真问题

Nav2 已启动，机器人模型可见，但时间相关日志持续等待。

1. 查看 ROS /clock 是否存在并有数值。

2. 发现 Gazebo 只发布世界路径时钟，而桥配置使用错误话题。

3. 修正 gz_topic_name，保持 ROS 输出为 /clock。

4. 确认所有导航和 TF 节点 use_sim_time 一致后重试。

验收：算法获得同一个有效时间源，后续定位和控制问题才有可比较的时间基础。

### 深入练习 1

为什么不能让 bag 和模拟器同时发布 /clock？

参考答案：两个时间源可能互相覆盖或跳变，使定时器、缓存与消息排序无法保持一致，应明确选择一个时间源。

### 深入练习 2

桥接成功说明物理模型正确吗？

参考答案：不说明。桥只转换数据，惯量、碰撞、摩擦与关节约束属于模拟器模型层。

### 深入练习 3

Jazzy 旧教程中的 gazebo_ros2_control 能直接用于 Harmonic 吗？

参考答案：不能直接当作同一接口。本路线使用现代 Gazebo 对应的 gz_ros2_control，需要核对插件和依赖版本。

### 基础验证流程

#### 确认版本配对

在已配置 ROS 软件源的 Ubuntu24.04 上，按官方配对安装 Jazzy ros_gz。

```bash

sudo apt install ros-jazzy-ros-gz

```

#### 启动一个空世界

图形环境需要可用显示和图形驱动；无图形环境按官方说明使用无 GUI 模式。

```bash

ros2 launch ros_gz_sim gz_sim.launch.py gz_args:="-r empty.sdf"

```

#### 桥接时钟

另开终端，下面的 [ 表示 Gazebo 到 ROS 的单向桥。引号避免 shell 解释特殊字符。

```bash

ros2 run ros_gz_bridge parameter_bridge "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"

```

#### 从 ROS 一侧验证

确认时钟连续推进，再向世界加入模型与传感器。按各传感器消息类型分别建立桥。

```bash

ros2 topic echo /clock --once
ros2 topic list -t

```

### 预期结果

- Gazebo 启动，ROS 侧可收到 /clock。

- 暂停仿真时仿真时钟停止，恢复后继续推进。

### 常见问题

- gazebo_ros_pkgs 的 Classic 教程不能直接当作 ros_gz 教程。

- 桥接双向同名消息可能形成反馈或重复发布，应只开启需要的方向。

- use_sim_time 为 true 但没有 /clock 时，许多时间相关逻辑会等待。

### 练习

加入一个二维激光传感器，桥接 LaserScan，在 RViz 中同时显示机器人、TF 与激光，并说明数据链中每个组件的职责。

#### 参考答案

数据链应为 Gazebo 激光传感器→Gazebo Transport→ros_gz_bridge→sensor_msgs/LaserScan→RViz。桥只转换消息，传感器模拟由 Gazebo 完成。

从同一个 /clock 驱动仿真时间；LaserScan.header.frame_id 必须通过 TF 连到 RViz Fixed Frame。验收包括暂停时钟、恢复时钟后仍正确显示。

### 依据

- [Gazebo Harmonic 文档](https://gazebosim.org/docs/harmonic/)

- [Gazebo 与 ROS 版本配对](https://gazebosim.org/docs/harmonic/ros_installation/)

- [ros_gz Jazzy 源码](https://github.com/gazebosim/ros_gz/tree/jazzy)

- [gz_ros2_control 源码](https://github.com/ros-controls/gz_ros2_control/tree/jazzy)

## 26. 感知管线：图像、深度、点云与时间同步

感知节点接收的不只是像素或点。编码、相机内参、坐标系、时间戳和 QoS 共同组成数据契约。先证明输入的几何与时序正确，再接入检测模型或点云算法。

### 学习目标

- 理解 Image 与 CameraInfo 的配对

- 用 cv_bridge 正确转换编码

- 把点云变换与滤波接到可观察的数据链

### 先修

话题与 QoS；tf2；Python/OpenCV 或 C++ 基础

### 概念

cv_bridge 把 ROS 图像与 OpenCV 表示互换，颜色通道顺序和深度类型必须显式理解。

image_transport 选择 raw/compressed 等传输插件；压缩节省带宽，但会增加编解码和可能的损失。

PointCloud2 是带字段布局的二进制数据；不能假设每个点都只有 x,y,z 三个 float。

### 把图像当作带几何和时间的数据

一帧图像不仅是一块像素数组，还包含宽高、编码、行步长、坐标系和采样时间。相机内参描述像素射线与相机坐标之间的关系，畸变参数描述镜头造成的偏差。若处理节点修改尺寸或裁剪图像，却仍沿用旧 CameraInfo，后续三维计算会使用错误的几何模型。

ROS Image 与 OpenCV 图像之间由 cv_bridge 进行表示转换。BGR 和 RGB 的通道数相同，但含义不同；深度图可能是十六位无符号整数或浮点数，单位也依设备而异。不能把所有输入强制转换成普通彩色图后再做距离判断。先写清数据合同，再讨论检测模型精度。

### 设计源、处理和显示三个模块

最小管线由图像源发布原始帧，处理节点订阅并生成结果，显示工具只消费输出。各模块之间使用明确的话题和编码，处理节点保留输入时间与 frame，便于观察延迟和进行空间关联。若结果代表原图中的边缘，它应仍属于同一个光学坐标和采样时刻。

传感器流通常更重视新鲜数据，队列过深可能让处理器一直工作在几秒前的图像上。QoS 应兼容发布者，同时根据任务选择丢帧、可靠传输和缓冲策略。可靠通信不意味着队列不会积压，最好分别记录输入频率、处理耗时、输出频率与消息年龄。

### 完整合成图像与边缘实验

下面单文件节点既生成测试图像，也通过 ROS 订阅接口接收该图像并处理，因此能检查消息转换与回调链，不需要实体相机。它使用黑底白框的确定图案，以 bgr8 发布，输出 Canny 边缘为 mono8。源和处理器在真实工程中可以拆成不同节点，但其话题合同保持相同。

保存为 image_lab.py，使用系统 Python 与发行版提供的 cv_bridge、OpenCV、NumPy。不要为了运行示例随意用 pip 覆盖系统 NumPy，否则可能破坏二进制扩展兼容性。代码是完整教学节点，未在本次编写环境实际运行；它不包含真实相机标定和硬件驱动。

#### image_lab.py

代码类型：complete

```python

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class ImageLab(Node):
    def __init__(self):
        super().__init__("image_lab")
        self.bridge = CvBridge()
        self.raw_pub = self.create_publisher(Image, "/camera/image_raw", qos_profile_sensor_data)
        self.edge_pub = self.create_publisher(Image, "/camera/edges", qos_profile_sensor_data)
        self.sub = self.create_subscription(Image, "/camera/image_raw", self.process, qos_profile_sensor_data)
        self.timer = self.create_timer(0.1, self.generate)

    def generate(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.rectangle(frame, (80, 60), (240, 180), (255, 255, 255), 3)
        msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera_optical_frame"
        self.raw_pub.publish(msg)

    def process(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        output = self.bridge.cv2_to_imgmsg(edges, encoding="mono8")
        output.header = msg.header
        self.edge_pub.publish(output)

def main():
    rclpy.init()
    node = ImageLab()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()

```

处理结果保留输入 header；没有把处理完成时间冒充原始采样时间。

### 按输入、输出和元数据检查实验

启动后先检查 /camera/image_raw 的类型、编码和频率，再检查 /camera/edges。用 rqt_image_view 分别打开两条话题，预期原图为白框，结果为边缘线。由于像素边界与阈值会影响局部形状，验收重点是输入输出关系、尺寸和编码，而不是对某张截图逐像素猜测。

比较两条消息的 header，结果应保留相同 frame 与采样时间。若处理慢导致消息年龄增大，应通过减少计算、限制队列或合理丢帧改善，而不是把输出时间戳改成当前时间隐藏延迟。显示工具默认 QoS 不兼容时要调整订阅设置，不能据此断言处理节点没发布。

#### 检查与显示

代码类型：commands

```bash

python3 image_lab.py
# 另一个已 source 的终端：
ros2 topic info /camera/image_raw --verbose
ros2 topic hz /camera/edges
ros2 run rqt_image_view rqt_image_view

```

显示命令需要 rqt_image_view；前两条常驻命令按需要在独立终端运行。

### 传输压缩和几何处理要分开

image_transport 允许选择原始或压缩传输，目的是管理带宽和编解码开销。压缩传输并不自动完成去畸变、缩放或相机标定，丢失压缩也可能改变像素值。深度图需要符合其专门传输格式，不能作为普通彩色 JPEG 处理后再用于精确距离。

图像去畸变依赖正确 CameraInfo，双目深度依赖左右相机标定与同步，深度到点云还需要相机投影模型。每一步都应保留能够追溯的输入来源。若相机标定文件与实际分辨率不一致，即使图像看起来清楚，空间位置仍可能产生系统误差。

### 点云处理遵守字段和 frame 合同

PointCloud2 使用字段描述和二进制布局，点中可能包含颜色、强度、时间或其他数据。处理器不能假定所有点都是连续三个 float。转换到 PCL 或 NumPy 时检查字段名、偏移、字节序与有效点，滤波后也应正确更新消息结构和 header。

把点云变换到 base_link 或 map 时，使用采样时刻的 TF。不同传感器同时观测同一物体时，空间重叠不良可能来自外参或时间偏差。先用静止环境检查外参，再用运动环境检查同步，能够减少在几何与时序两种错误之间反复猜测。

### 建立端到端感知验收

一条合格管线应能回答：输入来自哪里、编码是什么、在哪个 frame、何时采样、处理花多久、丢了多少帧、输出如何用于下游。算法精度与系统新鲜度需要一起评估，迟到的高精度结果也可能不适合当前控制决策。保存固定 bag 是比较不同实现的可靠起点。

黑屏先查编码与显示订阅，颜色异常先查通道顺序，几何错位先查内外参，运动时重影先查同步，内存增长先查队列和缓存生命周期。只有这些合同成立后，调整检测阈值或替换模型才有可解释意义。

### 边缘处理正常却看不到结果

输出话题有频率，图像显示窗口仍为空。

1. 查看输出编码为 mono8，确认显示工具支持。

2. 检查发布者为传感器数据 QoS。

3. 调整显示订阅兼容性，再比较原图与边缘。

4. 确认 header 没有被改写，记录数据年龄。

验收：把显示连接问题与图像算法问题分离。

### 深入练习 1

输出为什么保留输入时间戳？

参考答案：结果描述原始采样时刻的场景，保留它才能与 TF、其他传感器和延迟分析正确关联。

### 深入练习 2

压缩传输会自动去畸变吗？

参考答案：不会，传输编码与几何校正是不同步骤，后者需要有效标定。

### 深入练习 3

PointCloud2 能直接按三个浮点数一组读取吗？

参考答案：不能普遍如此，必须按字段、偏移、步长和字节序解析。

### 基础验证流程

#### 确认相机话题契约

以实际相机命名替换 /camera 路径，检查类型、QoS、分辨率、编码和 CameraInfo。

```bash

ros2 topic info /camera/image_raw --verbose
ros2 topic echo /camera/camera_info --once

```

#### 先显示原始数据

在 RViz 或 image_view 中观察输入；显示有问题时不要先调识别模型。检查 optical frame 与机器人坐标之间的旋转。

#### 对比两个图像传输方案

记录 raw 与 compressed 的带宽、CPU 与延迟，同时确认订阅端支持所选 transport。

```bash

ros2 topic bw /camera/image_raw

```

#### 让每个处理节点保留可追溯元数据

滤波或检测输出保留正确 header；需要多传感器同步时设定可解释的时间容差，并观察丢帧数量。

### 预期结果

- 图像方向、颜色与深度单位符合传感器说明。

- 点云在正确 TF 下与机器人和地图几何对齐。

### 常见问题

- BGR/RGB 混用会改变模型输入；16UC1 深度不能当作普通 8 位彩图。

- 只调整队列大小不能弥补不同设备的时钟偏移。

- 某些 image_pipeline 参数在 Jazzy 发生过更名，旧教程需要逐项核查。

### 练习

搭建相机→去畸变→处理→可视化链路，对每个节点记录输入类型、编码、frame、时间戳以及处理耗时。

#### 参考答案

输入契约至少包括 Image 编码、尺寸、步长、CameraInfo、frame_id、采样时间与 QoS；每个处理阶段列出输出格式和是否改变分辨率/相机内参。

验收用同一输入检查颜色、几何对齐、处理延迟和丢帧。改变图像尺寸后仍沿用旧内参，或丢弃 header，都属于链路错误。

### 依据

- [image_pipeline Jazzy 源码](https://github.com/ros-perception/image_pipeline/tree/jazzy)

- [vision_opencv／cv_bridge](https://github.com/ros-perception/vision_opencv)

- [image_common／image_transport](https://github.com/ros-perception/image_common)

- [image_transport 教程源码](https://github.com/ros-perception/image_transport_tutorials)

- [perception_pcl 项目](https://github.com/ros-perception/perception_pcl)

## 27. 数据与诊断：rosbag2、MCAP、Foxglove 与 tracing

可复现的机器人问题需要数据证据。记录输入、状态、TF 和关键配置，再用同一份记录重跑算法，能把偶发现场问题转化为可检查的回归场景。

### 学习目标

- 录制并回放一段完整数据

- 区分记录时间与消息 header 时间

- 选择日志、诊断与 trace 的合适用途

### 先修

话题与消息；ROS 时间；节点参数

### 概念

rosbag2 负责消息录制回放，存储插件决定文件格式；MCAP 能承载多话题与 Schema，但不会自动保存所有外部配置。

diagnostics 适合汇总健康状态，日志解释事件，trace 关注回调与执行时序，这三类证据互补。

回放机器人数据时需要重建原先的时钟与 TF 条件，避免现场驱动与 bag 同时发布相同数据。

### 先定义问题需要什么证据

机器人问题经常只在某一帧、某一次重连或某种负载下出现。日志可以解释节点做了什么，消息记录保存它看到了什么，诊断状态反映设备是否健康，trace 展示回调和调度的时间关系。这些工具回答不同问题，不能只保留一张终端截图就期待复现实验。

记录计划应从待验证假设出发。定位异常需要原始传感器、TF、里程计和参数；控制延迟需要输入命令、反馈与时间线；图像错误需要原始编码和相机信息。全量录制虽然简单，但可能增加磁盘和通信负载，应确认记录过程本身没有显著改变系统行为。

### 时间、QoS 和类型决定记录是否完整

bag 中的接收时间与消息 header 中的采样时间并不总相同。网络延迟和节点队列会拉开两者，回放时应保留这种区别。自定义消息还需要相应类型支持，单有文件不代表另一台机器就能解释所有字段。记录说明中应保存包版本、接口定义和配置。

录制器也是订阅者，需要与发布者 QoS 兼容。静态 TF 和某些状态话题使用持久性语义，晚启动的录制器是否能收到历史状态要检查。若话题存在却消息数为零，先查看端点和 QoS，而不是立即判断存储插件损坏。

### 从最小 chatter 实验学会完整闭环

先运行系统自带 talker，在另一个终端录制 /chatter，几秒后停止录制。输出目录使用一个尚不存在的新名字，避免误覆盖或混合实验。录制停止后先查看 metadata，再停止原始 talker，最后回放。这样观察者看到的消息来源只有一个，不会把实时发布与回放混在一起。

命令要求安装 demo_nodes_cpp、rosbag2 及 MCAP 存储插件，并在各终端 source Jazzy。本章未实际执行这些命令。实验成功标准是记录消息数大于零、能够说明录制时长，并在原始发布者停止后从回放再次收到同类消息。

#### 终端一：产生测试数据

代码类型：commands

```bash

ros2 run demo_nodes_cpp talker

```

保持运行直到录制完成，再用 Ctrl+C 停止。

#### 终端二：录制后检查

代码类型：commands

```bash

ros2 bag record -s mcap -o learning_chatter /chatter
# Ctrl+C 停止录制后运行：
ros2 bag info learning_chatter

```

目录名必须是新实验目录；不要把停止提示当作另一个自动执行命令。

#### 停止原 talker 后回放

代码类型：commands

```bash

ros2 bag play learning_chatter
# 另一个终端观察：
ros2 topic echo /chatter

```

回放和观察分别运行；确认实时 talker 已经停止。

### MCAP 与 SQLite 是存储选择

rosbag2 负责发现、订阅、序列化与回放，存储插件决定数据如何落盘。MCAP 是可保存多种带时间数据和 schema 的容器，SQLite 插件使用数据库形式组织记录。格式选择会影响索引、压缩、工具兼容性和恢复方式，但不会自动修复缺失消息或错误时间戳。

比较格式时使用同一数据集和消息速率，记录写入吞吐、CPU、文件大小、随机访问与恢复需求。不要只以压缩后的大小判断优劣。压缩级别越高可能越耗 CPU，造成原本没有的丢帧；对实时录制而言，完整性和可恢复性往往比最小文件更关键。

### 重放机器人数据时重建时钟和 TF

包含运动数据的 bag 常需要 /tf、/tf_static 与地图等上下文。让下游算法开启 use_sim_time，再使用回放时钟。此时关闭其他 /clock 发布者，停止真实驱动对同名输入的发布，避免两个源竞争。改变播放速率也不意味着算法时钟和计算负载会自动保持原来的关系。

记录使用的参数与 launch 版本同样重要。bag 保存消息，不会自动捕获所有文件、模型权重、地图路径和系统环境。复现包应包括这些依赖的版本或内容，以及启动顺序和预期判据。数据可以离线读取，但某些算法仍需要额外模型或插件才能重跑。

#### 以回放时间驱动算法

代码类型：commands

```bash

ros2 bag play learning_chatter --clock

```

对时间敏感的下游节点需显式启用 use_sim_time；本例 chatter 本身没有空间语义。

### 诊断和 tracing 的使用边界

DiagnosticArray 可以汇总设备温度、通信状态、频率或错误码，关键是定义每项状态什么时候更新、何时过期以及怎样判为异常。一个绿色状态若十分钟前发布后再未更新，不应被当作当前健康。诊断聚合帮助观察，但不承担底层执行器的停止功能。

当问题是回调延迟或线程竞争时，需要时序 trace，而不是在每次循环中大量打印日志。ros2_tracing 的事件能够帮助区分等待、回调执行和消息路径，但使用前要确认系统工具、权限与插桩支持。采集会产生额外开销，应记录开启和关闭采集时的行为差异。

### 用复现包而不是口头描述交付问题

一个最小复现包可以包含 bag、参数 YAML、机器人模型版本、软件提交清单、启动命令和一句可自动或人工判定的故障描述。例如“第十秒到第十二秒输出位姿跳变超过某个阈值”比“定位有点怪”更适合比较修复。对敏感数据还应按实际权限控制共享范围。

验收时使用新终端或独立工作区，按记录顺序重新启动，确认不依赖旧进程和环境残留。修复后重放同一数据，再加入新的边界样例。若只有原作者的电脑能够重现，说明还存在未记录依赖，应继续补齐，而不是把问题归为不可重复。

### 录制成功但回放无法显示激光

bag 文件可打开，RViz 报找不到 laser 到 map 的变换。

1. 检查记录话题，发现缺少 /tf_static。

2. 核对传感器安装模型，补充固定变换的可复现来源。

3. 统一回放时钟与消费节点 use_sim_time。

4. 再次记录包含必要上下文的数据并验证新终端回放。

验收：问题是记录上下文不完整，不是激光算法失效。

### 深入练习 1

bag 有文件就代表录制完整吗？

参考答案：不代表，应检查消息数、时长、话题、QoS 和所需上下文。

### 深入练习 2

为什么重放前停掉原始驱动？

参考答案：避免同名话题出现实时与回放两个发布者，造成重复数据和时间混乱。

### 深入练习 3

日志能替代 trace 分析回调延迟吗？

参考答案：通常不能。日志说明事件，trace 更适合精确时间关系，大量日志还可能改变系统时序。

### 基础验证流程

#### 录制一个小而完整的实验

仅录制实际存在的话题，给输出目录取新的名称。下面示例针对已有 /scan、/odom、/tf 和 /tf_static 的系统。

```bash

ros2 bag record -s mcap -o learning_run /scan /odom /tf /tf_static

```

#### 查看记录内容

停止录制后检查话题数、消息数、时长和存储格式。

```bash

ros2 bag info learning_run

```

#### 使用记录时钟回放

让下游算法开启 use_sim_time，再回放。不要同时保留原始驱动发布同名输入。

```bash

ros2 bag play learning_run --clock

```

#### 从现象深入到时间线

先用 RViz/Foxglove 比较输出，再用 diagnostics 观察健康状态；若问题是回调延迟，按 ros2_tracing 指南采集 trace。

### 预期结果

- 相同 bag 在固定参数下能重现相同类别的问题。

- 记录说明中包括软件提交、参数、frame 约定和实验环境。

### 常见问题

- 未录制 /tf_static 可能使回放无法重建传感器安装关系。

- QoS 不匹配会造成录制缺数据；先查看订阅兼容性，再使用 QoS override。

- 只看 ros2 topic hz 的平均频率可能漏掉长尾延迟与突发丢帧。

### 练习

制作一个故障复现包：bag、参数 YAML、版本清单、启动命令和预期现象；换一个新终端验证可复现性。

#### 参考答案

复现包应包含原始 bag、必要 TF、参数 YAML、软件提交/包版本、启动顺序、时钟设置与问题判定标准。若涉及外部模型和地图，也要记录来源与版本。

使用新终端和隔离话题环境重放，确认没有现场驱动重复发布；用同一判定标准再次观察问题才算复现成功。

### 依据

- [rosbag2 Jazzy 源码与使用说明](https://github.com/ros2/rosbag2/tree/jazzy)

- [MCAP 官方指南](https://mcap.dev/guides)

- [Foxglove Bridge 文档](https://docs.foxglove.dev/docs/fleet/bridge)

- [ROS diagnostics 项目](https://github.com/ros/diagnostics/tree/ros2)

- [ros2_tracing Jazzy](https://github.com/ros2/ros2_tracing/tree/jazzy)

## 28. ros2_control：读懂从命令到硬件的闭环

控制管理器周期性读取硬件状态、调用控制器更新，再写出硬件命令。学习时从官方 DiffBot 示例观察接口的申请与生命周期，比直接修改真实电机驱动更容易建立完整理解。

### 学习目标

- 区分硬件插件与控制器插件

- 理解状态接口、命令接口和资源占用

- 能解释控制器为何处于 inactive 或无法激活

### 先修

URDF 和关节命名；ROS 参数与 launch；基础 C++

### 概念

硬件插件抽象数据交换，控制器负责控制算法或命令转换；两者通过具名接口连接。

state interface 表示测得或估计的量，command interface 表示可写目标；velocity 一词出现在两边时含义不同。

activate 之前通常要完成配置及接口检查；同一个命令资源不能被不兼容的控制器同时独占。

### 从周期循环理解控制框架

ros2_control 将设备通信与控制算法拆开：硬件组件提供状态和可写命令，控制器消费状态并计算命令，controller_manager 管理生命周期、资源和更新顺序。典型循环先 read、再 update、最后 write。这里的顺序表示依赖关系，实际执行线程与异步设置还要由具体配置确定。

这种分层让同一个差速控制器可以连接模拟器、mock 硬件或真实设备，而硬件层不必重复实现导航速度转换。框架没有替用户提供完整设备协议，也没有自动保证任何控制周期都满足硬实时要求。必须测量循环耗时、阻塞和抖动，才能判断目标频率是否合适。

### 接口名称、单位与占用是一份合同

接口通常按 joint/interface 命名，例如 left_wheel_joint/velocity。状态侧的 velocity 是测量或估计的速度，命令侧的 velocity 是希望设备执行的目标，两者不应因为同名就混为一个数组。转动关节位置使用弧度、速度使用弧度每秒，硬件层负责把编码器计数和厂商单位换算到这个合同。

一个命令接口通常只能由被允许的控制链占用。available 表示资源存在且可供使用，claimed 表示当前控制器已经取得它。控制器 inactive 时可能配置完成但尚未占用执行资源。硬件生命周期和控制器生命周期相关却不相同，排错时要分别查看，而不是只看某一个节点是否存在。

#### URDF 中的控制标签示意

代码类型：snippet

```xml

<ros2_control name="LearningSystem" type="system">
  <hardware><plugin>mock_components/GenericSystem</plugin></hardware>
  <joint name="left_wheel_joint">
    <command_interface name="velocity"/>
    <state_interface name="position"/>
    <state_interface name="velocity"/>
  </joint>
  <joint name="right_wheel_joint">
    <command_interface name="velocity"/>
    <state_interface name="position"/>
    <state_interface name="velocity"/>
  </joint>
</ros2_control>

```

这是嵌入合法 robot 模型中的片段；对应关节必须已在 URDF 定义。它不构成独立机器人文件。

### 用官方本地源码准备一个隔离实验

本地参考目录已包含 Jazzy 的 ros2_control_demos。为避免把教材工程与现有实机工作区混合，复制到独立学习工作区。先 source 系统 Jazzy，再用 rosdep 安装依赖并仅构建 example_2 及其工作区依赖。下面命令未在本次任务运行；如果某项依赖未解析，应先记录包名并解决版本问题。

复制的是参考源码，不代表必须重编整个 ros2_control。系统二进制包通常可提供框架依赖，但源码分支可能随维护更新；若出现 API 不一致，要将示例提交与框架包版本一起固定，不能随意修改头文件来让编译通过。构建成功后在新终端 source 学习工作区再运行。

#### 准备与构建本地示例

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
mkdir -p "$HOME/ros2_learning_ws/src"
cp -a /home/mu/Desktop/ros2_jazzy_tracked_refs/ros2_control_demos "$HOME/ros2_learning_ws/src/"
cd "$HOME/ros2_learning_ws"
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --symlink-install --packages-up-to ros2_control_demo_example_2
source install/setup.bash

```

首次配置 rosdep 的环境还需完成 rosdep init/update。目标目录应是新学习目录，重复执行前先检查是否已有源码。

### 启动、配置和激活分别在做什么

启动文件先提供 robot_description，再启动管理器和相关节点，spawner 负责加载、配置并按要求激活控制器。机器人模型告诉资源管理器有哪些硬件接口，控制器 YAML 告诉管理器选择什么控制算法和哪些关节。两边名字必须完全一致，单独能解析 YAML 并不证明资源匹配。

使用 mock 后端先检查整个管理链，能够在没有总线和电机的情况下观察接口占用。它的行为通常是根据命令模拟或回显状态，不包含真实编码器误差、设备延迟和失联。不要把 mock 中能动当作真实硬件闭环已经成立。

#### 常驻示例与另一个终端的检查

代码类型：commands

```bash

ros2 launch ros2_control_demo_example_2 diffbot.launch.py use_mock_hardware:=True
# 在另一个已 source 学习工作区的终端执行：
ros2 control list_hardware_components
ros2 control list_hardware_interfaces
ros2 control list_controllers

```

若管理器使用自定义名字，给控制 CLI 的 -c 参数提供实际管理器路径。

### 逐项判读输出而不是只看机器人移动

先在硬件列表中确认组件生命周期符合预期，再在接口列表中找到左右轮的命令和状态。底盘控制器 active 后，其需要的命令接口应被 claimed；关节状态广播器应能发布 JointState。若控制器类型正确但接口仍未占用，查看配置阶段的第一条错误，不要直接重启整个桌面环境。

运动命令到达后，比较目标速度、关节状态和里程计。轮子显示转动只证明显示链收到了状态；里程计变化也可能来自 open_loop 对命令的积分。完整验收应写明状态来源、命令超时策略以及控制器停用后命令资源是否释放。

### 性能与故障要落到明确边界

read 和 write 中的长时间阻塞会占用周期预算，频繁分配内存和打印日志也会引入抖动。设备通信可使用独立线程和有界缓冲，但线程间必须定义数据的新鲜度、所有权和异常状态。不能为了“非阻塞”而把过期测量无限重复使用。

插件无法发现时查导出 XML 和安装路径；接口缺失时查模型与硬件导出；激活失败时查设备准备条件和资源冲突；运行不稳时查周期耗时和反馈时间。建议每次保留启动日志、参数文件和版本清单，使下一次修改能够与已知状态比较。

### 参数文件与资源表一起版本化

建议在实验目录同时保存 controllers.yaml、机器人描述和一份接口清单。清单逐项列出关节、状态接口、命令接口、单位、控制器及反馈来源。更新硬件插件或控制器后，重新导出 list_hardware_interfaces 和 list_controllers 的结果，与清单比较。这样可以在真正发送命令前发现接口删除、更名或占用变化。

需要切换控制器时，先明确旧控制器退出后的命令状态，以及新控制器是否使用当前测量作为起点。释放资源并不天然意味着设备立即停机，接管成功也不意味着目标连续。模拟中检查切换前后的命令突变和生命周期日志，比只验证切换服务返回成功更接近实际系统要求。

### 控制器 active 失败的逐层排查

差速控制器类型能加载，但激活时提示找不到右轮速度接口。

1. 列出硬件接口，发现硬件使用 right_wheel_joint。

2. 检查 YAML，发现误写成 right_wheel。

3. 修正控制器关节名称并重新加载配置。

4. 再次确认两个 velocity 命令接口 claimed，随后检查 JointState。

验收：修复接口合同即可激活，无需更换控制器或修改底层算法。

### 深入练习 1

state velocity 与 command velocity 为什么要分开？

参考答案：一个表示实际反馈，一个表示目标；分开才能观察跟踪误差、饱和和故障。

### 深入练习 2

控制器进程存在等于控制器 active 吗？

参考答案：不等于。进程、加载、配置、激活和资源占用是不同状态，需要控制 CLI 与日志验证。

### 深入练习 3

提高 update_rate 一定改善控制吗？

参考答案：不一定。硬件通信和计算可能超过周期预算，导致更大抖动；应先测量耗时和真实反馈频率。

### 基础验证流程

#### 使用已编译的 Jazzy 官方示例

本地源码位于 ros2_control_demos/example_2；先在独立工作区安装依赖并编译，再 source install/setup.bash。

```bash

ros2 launch ros2_control_demo_example_2 diffbot.launch.py use_mock_hardware:=True

```

#### 查看硬件导出的接口

先确认 joint 名称和 velocity 接口都存在。

```bash

ros2 control list_hardware_interfaces

```

#### 查看控制器状态

joint_state_broadcaster 与底盘控制器应按示例进入 active；若管理器改名，给 CLI 添加 -c 指定路径。

```bash

ros2 control list_controllers
ros2 control list_hardware_components

```

#### 追溯配置来源

依次阅读模型中的 ros2_control 标签、插件 XML、控制器 YAML 与 spawner 启动动作，把每个名称连到定义位置。

### 预期结果

- 命令接口显示 available，并在控制器启动后由正确控制器 claimed。

- 控制器状态和关节状态发布符合示例预期。

### 常见问题

- 动态库能编译并不等于 pluginlib 能发现它；还需正确导出和安装描述文件。

- 硬件 on_activate 成功之前不应假定 write 已经可向电机下发。

- 示例 mock hardware 回显的是模型行为，不证明真实编码器闭环正确。

### 练习

绘制 read→update→write 的数据流，在每条连线上标出单位、数据来源和调用频率，并解释接口未被 claimed 时应查哪一层。

#### 参考答案

read 把编码器/仿真位置和速度更新到 state interfaces；update 读取状态并产生 command interfaces；write 将命令转换到驱动或仿真接口。轮速应是 rad/s，车体线速度是 m/s。

available 但未 claimed 时先查控制器是否配置/激活以及 joint/interface 名是否匹配；接口不存在时查 URDF 和硬件插件导出。不要先修改控制算法。

### 依据

- [ros2_control 官方文档](https://control.ros.org/jazzy/index.html)

- [DiffBot 差速底盘官方示例](https://control.ros.org/jazzy/doc/ros2_control_demos/example_2/doc/userdoc.html)

- [Controller Manager](https://control.ros.org/jazzy/doc/ros2_control/controller_manager/doc/userdoc.html)

- [编写 ros2_control 硬件组件](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/writing_new_hardware_component.html)

## 29. 差速与履带底盘：从 TwistStamped 到左右轮速

差速模型把车体线速度和角速度换算为左右侧速度。履带底盘可以先借用此接口组织软件，但转弯滑移会使几何轮距与有效轮距不同，必须通过实测与外部定位校准。

### 学习目标

- 理解 v_left = v − ωb/2、v_right = v + ωb/2

- 识别 Twist 与 TwistStamped 的接口差别

- 区分开环里程计和编码器反馈里程计

### 先修

ros2_control 基础；里程计与 TF；线速度/角速度单位

### 概念

diff_drive_controller 输出的是关节角速度，因此左右线速度还需除以有效轮半径。

Jazzy 文档使用带时间戳的 TwistStamped；时间戳用于判断命令是否过期。

履带滑移不是修改一个 PID 就能完全解决的问题；校准、速度限制、IMU 和外部定位应协同设计。

### 从车体命令推导左右侧运动

差速底盘的常用输入是车体前向速度 v 和绕竖直轴的角速度 ω。若左右轮接触线间距为 b，左右侧线速度分别为 v−ωb/2 与 v+ωb/2。轮半径为 r 时，再分别除以 r 得到轮轴角速度。这个推导假定平面运动和理想无侧滑滚动，解释了为什么正向直行时两侧同向、原地转向时两侧反向。

输入线速度单位为米每秒，角速度为弧度每秒，控制器输出的轮速通常为弧度每秒。若驱动使用每分钟转数或编码器每周期增量，转换必须放在明确的边界。左右电机安装镜像可能使电气正方向相反，应在硬件层统一成模型定义的关节正方向。

### 履带模型可借用，但滑移不能忽略

履带转向依靠地面接触中的滑移，几何轮距与从转弯数据反推的有效轮距可能不同，并随地面、载荷和速度变化。因此差速模型可以作为软件接口和初始近似，却不能承诺在所有场景得到无偏里程计。应分别记录直行距离误差和转角误差，再考虑半径和有效轮距的校准。

里程计还有两种数据来源：反馈模式根据实际关节位置或速度积分，open_loop 则根据命令估计运动。后者在示例和没有反馈的场景有用途，但无法知道轮子是否受阻、打滑或驱动未执行。若需要可靠状态估计，应把真实轮速、IMU 和外部定位纳入可解释的融合链。

### 先确认命令消息与时间戳合同

当前 Jazzy diff_drive_controller 文档的速度输入为 TwistStamped，其 linear.x 与 angular.z 承载平面速度，header.stamp 表示命令时间。控制器可据此拒绝过期命令。很多旧驱动和本地 BUNKER 示例仍使用 Twist，没有 header。两种消息不是可自动互换的同一类型，桥接节点必须明确处理补时间戳与过期语义。

实际话题可能是控制器私有的 cmd_vel，也可能被 launch 重映射到 /cmd_vel。先用 topic info 检查真实类型、发布者和订阅者，再写命令。速度命令属于持续控制流，不应只保证一条消息到达而忽略发布频率与看门狗；可靠传输也无法替代超时停止机制。

#### 查看实际端点

代码类型：commands

```bash

ros2 topic list -t
ros2 topic info /cmd_vel --verbose
ros2 control list_controllers

```

如果实际输入名称不同，后续发布命令必须随之修改，不能假定所有机器人都使用全局 /cmd_vel。

### 读懂一份最小控制器参数

下面片段只描述差速控制器本身，应放入项目采用的参数加载结构中，并由 spawner 或管理器正确加载。关节名称必须匹配模型和硬件接口。示例设置反馈式里程计，并由控制器发布 odom 到 base_link；若 EKF 改为负责这条 TF，就应关闭这里的 TF 发布。

轮距和轮半径只是教学值，需要替换为实际模型和标定结果。命令超时、速度限制和加速度限制都属于系统合同，配置后还要通过实验验证。某些历史版本的参数名称和限速开关不同，使用当前安装包的参数定义，不要把跨发行版片段直接拼接。

#### controllers.yaml 中的控制器片段

代码类型：snippet

```yaml

diffbot_base_controller:
  ros__parameters:
    type: diff_drive_controller/DiffDriveController
    left_wheel_names: [left_wheel_joint]
    right_wheel_names: [right_wheel_joint]
    wheel_separation: 0.30
    wheel_radius: 0.05
    open_loop: false
    position_feedback: true
    odom_frame_id: odom
    base_frame_id: base_link
    enable_odom_tf: true
    cmd_vel_timeout: 0.5
    publish_rate: 50.0
    linear.x.max_velocity: 0.3
    angular.z.max_velocity: 0.5

```

配置片段依赖已存在的管理器、硬件、joint_state_broadcaster 和启动流程；不是独立可启动工程。

### 在模拟后端执行三个小实验

先使用前章的 DiffBot mock 或仿真后端。第一步只发布低速直行，检查左右目标符号一致；第二步只发布低角速度，检查两侧符号相反；第三步停止发布，观察命令超时后的行为。下面命令没有在本次编写中执行，且只适用于确认类型为 TwistStamped 的模拟话题。

header: auto 由 CLI 在发布时生成时间戳。若 use_sim_time 为真，命令发布进程也需要正确使用模拟时间，避免命令落在不同时间域。停止键盘发布后不要只看画面，应查看控制器输出或轮速反馈是否按预期衰减到零，并记录达到停止状态的时间。

#### 模拟中低速直行

代码类型：commands

```bash

ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/TwistStamped "{header: auto, twist: {linear: {x: 0.1}, angular: {z: 0.0}}}"

```

先确认模拟后端和话题类型；停止发布后观察 cmd_vel_timeout 的效果。仿真时可通过 --ros-args -p use_sim_time:=true 为 CLI 节点选择模拟时间。

### 校准与失败定位需要可测量证据

直行一段距离后比较外部测量与 odom 距离，转动一整圈后比较外部角度与 odom 角度。每次只改一个校准因素，并记录地面、载荷、速度、时间和轮胎或履带状态。多次往返比单次测量更能揭示系统偏差。若正反向误差不对称，还要检查间隙、死区与机械阻力。

收到消息却不动时，先看控制器 active 和接口 claimed，再看命令时间是否过期，最后看硬件写入和驱动使能。方向相反时先查单位与符号，曲线误差大时再查轮距和滑移。导航控制器不应被用来掩盖底层里程计单位错误，否则所有上层调参都失去可靠基础。

用数值先检查公式：取 v 为每秒零点二米、ω 为每秒一弧度、b 为零点四米、r 为零点一米，则左轮角速度为零，右轮为每秒四弧度。这代表绕左侧接触点转弯。将这个结果与软件输出比较，可以在机器人不运动时发现左右次序或量纲错误。

### 计算并检查一次原地转向

轮距为零点三米、半径零点零五米，目标角速度零点四弧度每秒。

1. 左右线速度分别为负零点零六与正零点零六米每秒。

2. 除以轮半径得到负一点二与正一点二弧度每秒。

3. 在模拟中对比命令、关节状态和 odom 角速度。

4. 停止发布并测量超时停止；实机标定另需外部角度测量。

验收：理想模型的计算、接口单位与可观察输出形成一致链路。

### 深入练习 1

为何不能把 Twist 直接发到 TwistStamped 话题？

参考答案：消息结构与类型支持不同，ROS 不会自动补 header 或转换。需要显式适配并定义时间戳语义。

### 深入练习 2

open_loop 里程计能检测车轮受阻吗？

参考答案：不能，它依赖命令估计运动，即使电机未执行也可能继续积分。

### 深入练习 3

履带有效轮距能用一次实验永久确定吗？

参考答案：通常不能。接触和滑移随地面、载荷与速度变化，应记录条件并评估不同工况。

### 基础验证流程

#### 先查实际输入接口

在官方 DiffBot 示例运行时检查 /cmd_vel，其他工程要替换为真实控制器的话题名。

```bash

ros2 topic info /cmd_vel --verbose

```

#### 只在示例或已确认的仿真中发送低速命令

header: auto 让 CLI 填写当前时间。该示例针对 TwistStamped 订阅者。

```bash

ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/TwistStamped "{header: auto, twist: {linear: {x: 0.1}, angular: {z: 0.0}}}"

```

#### 观察状态和里程计

从 ros2 topic list -t 查出 odom 路径，检查速度、位姿和 frame_id，而不只看 RViz 是否移动。

```bash

ros2 topic list -t
ros2 topic echo /joint_states --once

```

#### 设计校准实验

在实机批准测试条件下分别记录直行距离和原地转角，使用外部测量估计半径与有效轮距；保留地面材质、载荷和速度条件。

### 预期结果

- 直行指令下左右侧目标方向一致；原地转向时左右侧方向相反。

- 停止发布后控制器依据 cmd_vel_timeout 处理过期命令。

### 常见问题

- 不要向 Twist 订阅者发布 TwistStamped，或反向混用；ROS 不会自动转换。

- open_loop=true 使用命令估计里程计，不等于测到了轮速。

- 本地 BUNKER 驱动与 ros2_control 示例的消息类型不同，应按实际驱动检查。

### 练习

对照本地 example_2 与 bunker_ros2，列出输入消息、底层通信、里程计发布者、TF 发布者和超时处理的差别。

#### 参考答案

当前 example_2 接收 TwistStamped 并经 diff_drive_controller 产生关节速度，BUNKER wrapper README 接收 Twist 并调用 ugv_sdk。差异必须由 topic info 与实际源码确认。

验收应把每套系统的 odom 和 TF 发布者、命令超时、编码器反馈路径列清。履带有效轮距需要标定，几何轮距只能作为起点。

### 依据

- [diff_drive_controller 参数与接口](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)

- [DiffBot 差速底盘官方示例](https://control.ros.org/jazzy/doc/ros2_control_demos/example_2/doc/userdoc.html)

- [bunker_ros2 本地固定提交](https://github.com/agilexrobotics/bunker_ros2/tree/f24f722b245eb1d2572c47d091fc847d9fd68cf4)

- [AgroSenseBot 本地固定提交](https://github.com/AIRLab-POLIMI/AgroSenseBot/tree/4ad700b090b9f3ddb8513c7519938bd7f0974709)

## 30. 实机接入：标准硬件接口与厂商 SDK 两条路线

真实底盘常见两种接入方式：通过 ros2_control 硬件插件暴露关节接口，或用厂商 SDK 包装成 ROS 驱动节点。先追踪测量与命令链路，再决定是否需要统一成控制器框架。

### 学习目标

- 理解驱动包装与硬件插件的分工

- 记录总线、协议、单位、超时和故障反馈

- 能从物理通信逐层定位故障

### 先修

ros2_control；C++ 与线程基础；CAN/串口基础

### 概念

SDK 通常解决报文编解码与设备抽象，ROS wrapper 解决话题、参数和时间戳；它们不是同一层。

read/write 热路径中要控制阻塞、内存分配与日志开销；通讯线程和控制周期的交界需要清晰。

驱动失联、命令超时与急停反馈应作为具体状态处理，不能只让上层继续发送零速。

### 先选择接入边界，再实现设备协议

一条路线是 ROS 驱动节点直接调用厂商 SDK，把车体速度、设备状态和里程计暴露为话题；另一条路线是 ros2_control 硬件插件把关节状态与命令暴露给通用控制器。前者适合已有完整底盘控制盒，后者适合需要统一关节控制资源的设备。两者可以共存，但不能让两个路径同时争夺同一执行器。

厂商 SDK 常负责报文打包、协议版本和设备类型抽象，ROS wrapper 负责话题、参数、时间戳和生命周期。把这两层分开，能让没有 ROS 的协议测试先证明设备通信，再检查 ROS 集成。不要把节点启动成功当作设备已经在线，也不要用持续重发运动命令来判断设备状态。

### 写清楚硬件接口的六项合同

每项命令至少写出单位、范围、符号、刷新周期、超时动作与使能条件；每项反馈至少写出测量来源、采样时间、误差、无效值和丢失处理。例如编码器计数需要分辨率、减速比和方向才能转成关节弧度，电机内部速度目标也未必等于车轮真实速度。

时间合同尤其容易被忽略。设备报文可能没有时间戳，此时主机接收时间只是近似，不能假装它就是准确采样时刻。多个状态在不同报文到达时，还要决定一次 read 是否可以组合不同年龄的数据。为每个缓存维护更新时间和有效标志，比盲目重复最后一帧更可诊断。

### 最小无硬件实验：把协议转换单独验证

下面使用自定义教学报文，不代表 BUNKER、CANopen 或任何厂商协议。它规定速度以毫米每秒编码为有符号十六位小端数，温度以摄氏度编码为有符号字节。保存为 protocol_check.py，用普通 Python 即可验证单位、符号与长度检查，完全不需要 ROS 或连接设备。

这种实验把“数学和二进制转换是否正确”从“电机是否响应”中分离。真实项目应根据厂商公开协议替换字段、量程、校验和与消息标识，并用记录到的已知报文做回归。教学测试通过只证明这份自定义格式一致，不能推导真实硬件可以使用同样字节。

#### protocol_check.py：完整的离线编码实验

代码类型：complete

```python

import struct

def encode_speed(speed_m_s):
    raw = round(speed_m_s * 1000)
    if not -32768 <= raw <= 32767:
        raise ValueError("speed out of range")
    return struct.pack("<h", raw)

def decode_status(payload):
    if len(payload) != 3:
        raise ValueError("expected three bytes")
    speed_raw, temperature = struct.unpack("<hb", payload)
    return speed_raw / 1000.0, temperature

if __name__ == "__main__":
    assert encode_speed(-0.25) == bytes([6, 255])
    assert decode_status(bytes([250, 0, 30])) == (0.25, 30)
    print("teaching protocol checks passed")

```

这是完整可运行的纯 Python 教学程序，未在本次文档编写时执行；不存在任何实机写入操作。

### 从物理链路向 ROS 图逐层检查

真实接入时先确认设备、电源、驱动与通信接口准备好，再用只读观测查看总线状态和已有报文。Linux 中 can0 存在不代表波特率、接线终端、设备协议或报文 ID 正确。看见原始帧后，再运行只读 SDK 查询，最后启动 ROS wrapper 或硬件组件。

本地 BUNKER 工程通过 ugv_sdk 接入底盘，README 的速度接口使用 Twist；AgroSenseBot 展示 ros2_control 与 CANopen 的组合，但本地 Jazzy 分支 README 仍有 Iron 安装指令。阅读时固定提交并查代码实际接口，不应将旧安装命令简单替换发行版名称后执行。

#### 已经配置好的 CAN 接口只读观测

代码类型：commands

```bash

ip -details link show can0
candump can0

```

需要系统已有 can-utils 与正确接口配置。candump 常驻运行；这里只观测现有报文，不注入 CAN 帧。

### 控制循环和通信线程如何交换数据

把可能阻塞的串口读取放到通信线程，控制周期读取一个受保护或无锁设计正确的最新状态快照，是常见组织方式。关键不是使用了多少线程，而是快照是否原子一致、命令何时被发送、异常何时被看见。队列应有明确容量和满队列策略，不能让旧速度命令排队数秒后才执行。

硬件激活前应完成必要握手和状态确认；停用时定义停止指令、资源释放与故障保持方式。通信断开后，软件应将状态标为无效并触发定义好的控制行为。靠近执行器的看门狗和硬件停止条件应独立于上位机网页或调度程序，避免上位机卡死时只能期待下一条零速消息。

### 给每一层设计一个失败观测点

设备层查看供电、接口和使能状态；传输层查看错误计数与收发帧；协议层查看长度、校验和、ID 与量纲；SDK 层查看设备状态；ROS 层查看消息类型、频率、时间和控制器状态。故障定位时寻找第一个不满足合同的层次，不要从最上层不断增加重试次数。

验收至少包含正常启动、重复启动、客户端掉线、设备掉线、反馈过期和恢复。对每个场景记录状态迁移与停止时间，并明确哪些情况允许自动恢复、哪些需要人工确认。测试顺序从离线解码、虚拟后端到批准的实机条件逐步推进；本章没有声称这些实机测试已经完成。

设备心跳新鲜不代表每个传感器反馈都新鲜。控制盒可能持续发心跳，却停止更新编码器；应分别记录报文接收序号、数据采样序号和更新时间。通过回放重复编码器帧、同时保持心跳更新的记录，可以验证系统是否把旧测量误判为有效状态。

### 底盘状态不更新的定位过程

ROS 节点在线，但 odom 一直不变。

1. 确认 can0 有报文且错误计数没有持续增长。

2. 用已知协议检查报文 ID，发现设备配置为另一型号协议。

3. 在 SDK 层选择匹配型号并重新验证只读状态。

4. 确认反馈时间更新后，再检查 ROS 消息和里程计积分。

验收：问题定位在设备协议选择，而不是导航器或 RViz。

### 深入练习 1

为什么接收时间不总等于采样时间？

参考答案：设备内部采样、排队和传输都有延迟。没有设备时间戳时只能记录接收近似并评估误差。

### 深入练习 2

为何运动命令队列不宜无限增长？

参考答案：旧命令延迟执行会使机器人响应过去的意图，应使用有界队列、最新命令语义或明确拒绝策略。

### 深入练习 3

SDK 解码测试通过是否证明整车控制安全？

参考答案：不证明。还需验证使能、限幅、反馈、超时、急停和系统故障行为，且须在明确的实机条件下实施。

### 基础验证流程

#### 记录已固定的本地来源

本地有 Jazzy 的 AgroSenseBot、BUNKER、Linorobot2 和 main 的 ugv_sdk；阅读时记录提交，避免更新后示例含义变化。

#### 先检查通信设备

以下是只读观测命令；只有设备已由正确配置启用时，candump 才能看到数据。

```bash

ip -details link show can0
candump can0

```

#### 再检查 ROS 接口

启动实际驱动前核对厂商的电源、通信、使能与测试条件；启动后首先观察状态话题，而不是立即发送运动命令。

```bash

ros2 node list
ros2 topic list -t
ros2 topic info /cmd_vel --verbose

```

#### 把集成方案写成契约

为输入命令、状态反馈、坐标系、时钟、重连策略与停止路径各写一条可验证要求。选择虚拟 CAN 或 mock 后端先测试异常路径。

### 预期结果

- 能够明确指出每个关节状态或底盘状态来自哪一条测量链路。

- 通信中断时系统状态可被观察，并进入定义好的停止或降级流程。

### 常见问题

- AgroSenseBot 本地虽检出 jazzy，README 仍有 Iron 安装命令；不能直接复制执行。

- ugv_sdk 为通用 C++ SDK，main 不代表 ROS Jazzy 专用分支。

- 在 Linux 上看到 CAN 帧并不证明 ID、协议版本和设备型号匹配。

### 练习

选 BUNKER 或 AgroSenseBot，绘制从 ROS 命令到 CAN 报文再到反馈的链路，并为五个可能故障各指定一个观测点。

#### 参考答案

BUNKER 链路可归纳为 cmd_vel→ROS wrapper→ugv_sdk 设备抽象→CAN 报文→底盘控制器，反馈按相反方向转换成 ROS 状态与里程计。AgroSenseBot 采用 ros2_control 硬件层接入 CANopen。

五个观测点可选：设备枚举、ip link 总线状态、candump 原始报文、SDK 解码状态、ROS 话题/控制器状态。超时或协议不匹配应停在出现证据异常的最早层。

### 依据

- [编写 ros2_control 硬件组件](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/writing_new_hardware_component.html)

- [AgroSenseBot 本地固定提交](https://github.com/AIRLab-POLIMI/AgroSenseBot/tree/4ad700b090b9f3ddb8513c7519938bd7f0974709)

- [bunker_ros2 本地固定提交](https://github.com/agilexrobotics/bunker_ros2/tree/f24f722b245eb1d2572c47d091fc847d9fd68cf4)

- [ugv_sdk 本地固定提交](https://github.com/agilexrobotics/ugv_sdk/tree/f2704eacdc90357078cd93ec60aae08bb4baab35)

- [linorobot2 本地固定提交](https://github.com/linorobot/linorobot2/tree/f6b0bd0350c4a9d6b815ef4bb5c701a1e5129711)

## 31. 二维 SLAM：从传感器数据到可复用地图

SLAM 同时估计机器人轨迹与环境地图。先用可靠的扫描、短期里程计和时间同步建立输入条件，再讨论地图质量。成功显示一张图，只证明数据曾被处理，不代表地图可用于长期定位。

### 学习目标

- 检查 SLAM 必需的扫描和变换

- 区分栅格地图与位姿图

- 能保存地图并验证再次加载

### 先修

tf2；LaserScan；里程计和仿真时间

### 概念

SLAM 常提供 map→odom，底盘或融合节点提供 odom→base_link；这条链让扫描能被放到地图上。

地图分辨率会影响内存、细节和后续规划；更细不一定更准确。

栅格地图适合已知地图定位；可继续优化的 SLAM 会话还需要算法自己的位姿图数据。

### SLAM 的输入不是一张图，而是一段运动证据

二维激光 SLAM 将连续扫描和运动估计结合，构建机器人轨迹与占据栅格。激光提供周围障碍几何，里程计提供短期运动先验，扫描匹配再寻找与历史观测一致的姿态。回到已经见过的地方时，回环约束可调整累积误差，但算法无法凭空恢复从未被传感器观察到的区域。

本章先做一个静止方形房间实验：自己产生 LaserScan，不需要真实雷达或完整物理模拟器。实验只验证消息、TF 和地图生成的数据链，不证明移动建图质量。将静止输入替换为真实运动数据后，才需要评价重影、漂移、回环和地图一致性。

### 定义扫描、坐标与时钟合同

LaserScan 中每条距离对应 angle_min 加索引乘 angle_increment，长度单位是米，角度是弧度。range_min/range_max 之外的值需要按消息和算法约定处理，不能将“没有测到障碍”误写为零距离。header.frame_id 表示扫描坐标，header.stamp 应与 TF 查询的采样时间一致。

slam_toolbox 通常使用 odom 到 base frame 的运动关系，并发布 map 到 odom。机器人内部 base_link 到 laser 必须已知。只让扫描话题有数据而没有 TF，无法把不同时间的观测组合起来。最小实验使用系统时间，所有节点关闭 use_sim_time；以后回放或仿真时再整体切到统一时钟。

### 生成一份完整的合成扫描

将下方脚本保存为 square_scan.py。它在原点朝四周发射三百六十条射线，房间边界位于 x、y 的正负两米。每条射线取与四面墙最先相交的距离，因此角点附近距离更长。脚本使用传感器数据 QoS，以十赫兹发布，所有值和几何关系都能直接检查。

运行前需要系统 Jazzy 的 rclpy 和 sensor_msgs，终端 source 系统环境后用 python3 启动。代码为完整单文件节点，编写时未实际运行。它故意不模拟噪声、遮挡、滚动扫描或运动畸变，避免把教学几何与真实雷达性能混为一谈。

#### square_scan.py：完整合成传感器

代码类型：complete

```python

import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

class SquareScan(Node):
    def __init__(self):
        super().__init__("square_scan")
        self.pub = self.create_publisher(LaserScan, "/scan", qos_profile_sensor_data)
        self.timer = self.create_timer(0.1, self.publish_scan)

    def publish_scan(self):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "laser"
        msg.angle_min = -math.pi
        msg.angle_increment = 2.0 * math.pi / 360.0
        msg.angle_max = msg.angle_min + 359 * msg.angle_increment
        msg.range_min = 0.05
        msg.range_max = 10.0
        msg.scan_time = 0.1
        for i in range(360):
            a = msg.angle_min + i * msg.angle_increment
            distance = min(2.0 / max(abs(math.cos(a)), 1e-9),
                           2.0 / max(abs(math.sin(a)), 1e-9))
            msg.ranges.append(distance)
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = SquareScan()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()

```

该节点没有运动控制功能，仅发布合成扫描。

### 配置并按顺序启动建图

将配置保存为 mapping.yaml，先启动合成扫描，再分别启动 odom 到 base_link 和 base_link 到 laser 的静态变换，最后启动 slam_toolbox。静止机器人允许这两条关系保持单位变换；真实移动系统绝不能把里程计边固定为零来掩盖缺失驱动。每个常驻命令使用独立终端。

最小参数说明了地图、里程计、车体和扫描名称；其他参数采用安装包默认值。若节点报告参数或求解器不兼容，首先核查是否确实运行 Jazzy 包，并查看第一条配置错误。地图分辨率设为五厘米，表示每个栅格覆盖的地面长度，不等于传感器测量精度。

#### mapping.yaml

代码类型：complete

```yaml

slam_toolbox:
  ros__parameters:
    use_sim_time: false
    mode: mapping
    map_frame: map
    odom_frame: odom
    base_frame: base_link
    scan_topic: /scan
    resolution: 0.05
    map_update_interval: 2.0

```

供 slam_toolbox 的在线异步 launch 读取。

#### 每个命令在独立已 source 的终端运行

代码类型：commands

```bash

python3 square_scan.py
ros2 run tf2_ros static_transform_publisher --frame-id odom --child-frame-id base_link
ros2 run tf2_ros static_transform_publisher --frame-id base_link --child-frame-id laser
ros2 launch slam_toolbox online_async_launch.py slam_params_file:="$(pwd)/mapping.yaml" use_sim_time:=false

```

需要安装 ros-jazzy-slam-toolbox；静态边仅属于本节静止实验。

### 判读地图并保存可以再次加载的结果

在 RViz 中选择 map 作为 Fixed Frame，添加 Map、LaserScan 和 TF。预期能观察到围绕原点的方形墙体，墙内空间被标为已观测自由区域。先比较扫描几何和地图，而不是追求图像边缘完全平滑：占据栅格离散化会使斜向边缘出现台阶。

保存导航用地图时，map_saver_cli 生成图像和 YAML。YAML 保存分辨率、原点和阈值，单独拷贝图像无法完整恢复地图。若希望以后继续优化建图，还需要 slam_toolbox 自己的位姿图序列化；导航栅格和算法内部图不是同一种持久化对象。

#### 检查并保存

代码类型：commands

```bash

ros2 topic echo /map --once --field info
ros2 run nav2_map_server map_saver_cli -f /tmp/square_map

```

需要 nav2_map_server。保存后应同时保留地图图像与 YAML。

### 从合成房间过渡到真实数据

接入移动平台时撤掉假的 odom 静态边，由底盘或融合节点提供运动变换，保留真实安装关系。先缓慢直行和转弯，检查扫描在 odom 中是否合理，再探索环境。重影可能来自时间偏差、错误安装、里程计尺度或运动畸变，不能只靠扫描匹配参数弥补。

比较参数时录制同一份 /scan、TF 和必要状态，固定时钟后重复建图。记录地图重影、回到起点后的对齐、CPU 和积压。空白地图先查扫描数量、TF、时间和节点状态；地图弯曲先查里程计尺度与传感器安装；重复墙体先查时间延迟和回环条件。

### 把“地图可用”写成可重复判据

最低验收包括：地图话题持续发布，frame 为 map，分辨率和尺寸符合预期，保存后可以重新加载，扫描与墙体在正确姿态下对齐。真实场景还应选取几段独立测量距离比较尺度，记录动态物体造成的污染，并确认导航所需区域没有因遮挡而被错误假定为自由空间。

静止方房实验提供一个确定基线。若更换算法后连这个简单输入都不能生成合理图形，应先修复接口；若基线正常而实测失败，再逐步引入噪声、运动和回环。这样的实验阶梯能够把系统集成问题与算法鲁棒性问题分开。

### 从零消息到一张方形地图

没有实体雷达，希望学习扫描、TF、SLAM 和地图文件的关系。

1. 运行合成扫描，确认每帧三百六十个距离。

2. 发布静止机器人两条 TF，并用 tf2_echo 验证。

3. 加载最小建图参数，等待地图更新。

4. 在 RViz 比较方形扫描与地图，再保存图像和 YAML。

验收：完成一个可检查的静止建图链路；它只验证接口，不包含移动定位与回环性能结论。

### 深入练习 1

静止实验为何能用 odom→base_link 静态变换？

参考答案：因为机器人位置被明确设为不动。真实移动平台必须由运动估计持续更新这条边。

### 深入练习 2

保存一张地图图片足够吗？

参考答案：不够，还需要分辨率、原点等 YAML 信息。继续建图还可能需要算法自己的位姿图数据。

### 深入练习 3

地图出现两层墙先查什么？

参考答案：先查传感器时间、安装 TF、运动估计和消息延迟，再判断扫描匹配或回环参数。

### 基础验证流程

#### 先验证扫描和 TF

在带二维激光的模拟机器人或实机上检查。将 /scan 与 laser 替换为实际名称。

```bash

ros2 topic hz /scan
ros2 topic echo /scan --once
ros2 run tf2_ros tf2_echo base_link laser

```

#### 启动异步 SLAM 示例

需要已安装 slam_toolbox 且输入话题/坐标系符合所用参数。use_sim_time 在真机上改为 false。

```bash

ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true

```

#### 缓慢覆盖环境并形成回环

在 RViz 显示 /map、扫描与 TF。以回到起点后的重合程度评估闭环效果，保留原始 bag 以便复盘。

#### 保存导航用地图

需要 nav2_map_server；输出路径所在目录应存在。

```bash

ros2 run nav2_map_server map_saver_cli -f /tmp/learning_map

```

### 预期结果

- 地图随扫描扩展，回环后已有墙体与新扫描尽量对齐。

- 保存得到地图图像与 YAML 描述，可以在新会话加载。

### 常见问题

- 扫描 frame 无法转换到 base frame 会让建图停滞或丢帧。

- 把反光、玻璃和运动物体造成的异常完全归因于算法参数，容易掩盖传感器问题。

- 仅保存 PNG/PGM 不包含地图原点、分辨率和阈值等 YAML 信息。

### 练习

在同一份 bag 上对比两种建图参数，记录地图重影、回环表现、CPU 与处理延迟，解释取舍。

#### 参考答案

比较时必须使用同一份 bag、时钟和输入话题，仅改变指定参数。记录墙体重影、闭环前后偏差、CPU 和处理延迟；单看地图截图不足以判断优劣。

参数改变若提高细节却显著增加处理积压，应解释其代价。导航地图与位姿图分别保存，并在新会话验证读取。

### 依据

- [slam_toolbox Jazzy 源码与指南](https://github.com/SteveMacenski/slam_toolbox/tree/jazzy)

- [Nav2：建图与定位](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/sensors/mapping_localization/)

- [rosbag2 Jazzy 源码与使用说明](https://github.com/ros2/rosbag2/tree/jazzy)

## 32. 状态估计：轮速、IMU、GNSS 与定位坐标系

融合的目标是利用互补传感器约束状态，同时承认各自的不确定性。首先统一单位、轴向、时间戳和协方差，再配置 EKF/UKF；滤波器无法自动识别错误的传感器契约。

### 学习目标

- 分辨连续局部估计与可能跳变的全局定位

- 按状态量选择融合输入

- 理解协方差和重复测量的影响

### 先修

tf2 与 odom/map；Odometry 与 Imu 消息；协方差基础

### 概念

轮速擅长短期平面运动，IMU 提供角速度与加速度约束，GNSS 提供全局位置但可能跳变。

robot_localization 输入配置通常按 x,y,z,roll,pitch,yaw 及速度/加速度的固定顺序选择量；必须逐项核对。

同一个编码器同时生成的位置和速度并非两份独立信息，重复融合可能制造过度自信。

### 估计状态与测量状态是两件事

轮式里程计、IMU 和 GNSS 都只从各自物理机制观察机器人。状态估计器将测量与运动模型结合，输出在当前信息下最合理的状态及不确定性。它不是把所有传感器简单平均，也不会自动识别错误单位、错误坐标或重复信息。输入合同错误时，滤波结果可能很平滑却完全错误。

robot_localization 的 EKF 和 UKF 处理位置、姿态、速度与加速度等状态。二维底盘通常限制垂直运动和横滚俯仰，但仍须理解真实 IMU 如何测量重力与角速度。学习时先用一项速度测量看清积分行为，再逐渐加入互补信息，避免第一天就配置十个输入。

### 设计 map、odom 和 base_link 的发布职责

odom 表达连续的局部运动估计，允许缓慢漂移，适合控制；map 表达全局参考，可因重新定位发生修正。局部滤波器通常提供 odom 到 base_link，全局定位提供 map 到 odom。使用 GNSS 或其他全局来源时，必须决定如何保持局部控制所依赖的连续关系。

每条 TF 边只保留一个负责发布的节点。如果底盘驱动已经发布 odom 到 base_link，而 EKF 也发布同一条边，就要关闭其中一个。消息仍可由底盘发布供融合使用，关闭 TF 不等于关闭测量。输入消息的 frame 与 child_frame 应与真实量的表达坐标一致。

### 协方差和输入选择决定融合含义

协方差表达测量不确定性及状态间相关性，不是为了通过格式检查随便填写的数组。把不可靠测量标成极小协方差会让它主导估计；把同一个编码器派生的位置和速度当作独立高置信来源重复输入，也可能造成虚假的确定性。应先了解设备给出的数值究竟是否可信。

输入配置向量按固定顺序对应位置三项、姿态三项、线速度三项、角速度三项和加速度三项。必须逐个写出名称，不要只复制一长串 true/false。二维约束可利用确实不存在的侧向运动，但履带打滑等实际现象需要谨慎，不能把所有横向速度都当作绝对为零的测量。

### 最小实验：只融合一条前向速度

将下面配置保存为 ekf.yaml。输入只启用前向速度，其他维度不声明为测量。world_frame 选 odom，节点负责发布局部 TF。该实验是滤波接口教学，不代表可以用单一速度完成可靠定位；没有绝对约束时，位置随积分漂移是预期现象。

发布器提供每秒十次的零点一米每秒速度和明确协方差。该数据是合成测量，未连接设备。本章代码和命令未在本次编写环境运行。需要已安装 robot_localization，并在每个终端 source Jazzy；节点运行后再启动输入，观察从等待到输出的变化。

#### ekf.yaml：完整最小参数文件

代码类型：complete

```yaml

ekf_filter_node:
  ros__parameters:
    frequency: 30.0
    sensor_timeout: 0.3
    two_d_mode: true
    publish_tf: true
    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom
    odom0: /wheel/odom
    odom0_config: [false, false, false, false, false, false, true, false, false, false, false, false, false, false, false]
    odom0_differential: false
    odom0_relative: false

```

只有配置向量的第七项为 true，代表前向线速度。

#### 启动滤波器

代码类型：commands

```bash

ros2 run robot_localization ekf_node --ros-args --params-file "$(pwd)/ekf.yaml"

```

本例不使用仿真时钟；真实仿真输入要统一 use_sim_time。

### 用完整合成测量观察输出

下面文件保存为 wheel_measurement.py。消息 pose 不作为融合输入，因此只给出合法单位四元数；速度协方差的六个对角元素均明确填写。真实设备应使用自己的误差估计，不能照搬这些教学数值。header.frame_id 为 odom，child_frame_id 为 base_link，时间由节点时钟产生。

输出 /odometry/filtered 应开始更新，前向速度趋近输入值，位置随时间推进。停止发布后，估计器可能按预测模型继续演化，而不会自然变成机器人控制用的急停逻辑。这说明“测量超时”和“执行器停止”属于不同系统职责。

#### wheel_measurement.py

代码类型：complete

```python

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

class WheelMeasurement(Node):
    def __init__(self):
        super().__init__("wheel_measurement")
        self.pub = self.create_publisher(Odometry, "/wheel/odom", 10)
        self.timer = self.create_timer(0.1, self.publish_measurement)

    def publish_measurement(self):
        m = Odometry()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = "odom"
        m.child_frame_id = "base_link"
        m.pose.pose.orientation.w = 1.0
        m.twist.twist.linear.x = 0.1
        for i in [0, 7, 14, 21, 28, 35]:
            m.twist.covariance[i] = 0.01
        self.pub.publish(m)

def main():
    rclpy.init()
    n = WheelMeasurement()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()

```

这是独立的合成测量节点，只供验证滤波输入合同。

### 逐步增加 IMU 和全局约束

加入 IMU 前先静止记录角速度与加速度，检查轴向、偏置、重力处理和姿态参考。某些设备使用 NED，ROS 常用 ENU，二者转换不仅是改 frame 名。需要明确的旋转或驱动输出设置，并在已知姿态下验证结果。方向错误的角速度会让转弯估计持续偏离。

GNSS 进入全局估计时，还涉及地理坐标投影、航向和基准。位置精度并非任何时候固定，遮挡和多路径会改变误差。每加入一个来源，使用同一 bag 比较有无该来源的漂移、延迟与协方差变化，确认改善来自有效信息，而不是显示曲线变得更平滑。

### 用残差和失效实验判断估计质量

静止时检查输出速度是否接近零，直行时检查侧向漂移，转弯时检查角速度符号和尺度。若加入某个传感器后立即跳变，先查该传感器时间、frame、单位与协方差。若速度正确但位置越来越远，要区分无绝对约束的正常漂移与单位或积分错误。

为每项输入分别做中断和恢复实验，记录输出是否持续、协方差是否合理增长，以及重连时是否突然跃迁。最终验收不是“滤波器没报错”，而是在已知路径或外部测量下有可解释的误差，并能明确报告失效状态。传感器失效后继续输出数值，不等于数值仍然可信。

### 解释看起来平滑却持续漂移的输出

单独融合恒定前向速度，机器人估计位置一直增加。

1. 确认合成输入确实持续报告非零速度。

2. 确认配置只融合速度，没有绝对位置观测。

3. 认识到位置积分增长符合模型。

4. 改用零速度输入并观察响应，再讨论真实偏置的影响。

验收：能够区分模型的预期行为与滤波器错误，而不是通过任意减小协方差追求静止图像。

### 深入练习 1

为什么不能把所有输入协方差都设很小？

参考答案：这会过度相信不可靠测量，掩盖噪声和重复信息，导致估计不一致。

### 深入练习 2

输入超时会自动使电机停止吗？

参考答案：不会。状态估计与执行器安全是不同职责，电机停止应由控制和硬件看门狗处理。

### 深入练习 3

为何 map 与 odom 常要分开？

参考答案：全局修正可能跳变，局部控制需要连续参考。分开能同时表达长期定位和短期平滑运动。

### 基础验证流程

#### 验证原始数据

在任何融合之前，静止记录 IMU 与轮式里程计，检查轴向、噪声、协方差与消息时间。

```bash

ros2 topic echo /imu/data --once
ros2 topic echo /odom --once

```

#### 建立最小二维配置

从维护者参数示例开始，只启用真实可测的平面状态；先融合一种里程计，再逐项增加 IMU。

#### 显式指定唯一 TF 发布者

若 EKF 发布 odom→base_link，关闭底盘驱动对同一边的发布，并检查 RViz/TF 无跳变。

```bash

ros2 run tf2_ros tf2_echo odom base_link

```

#### 对比原始与融合输出

以同一段直行、转弯和静止数据比较 /odometry/filtered 的稳定性与延迟。

```bash

ros2 topic echo /odometry/filtered --once

```

### 预期结果

- 静止时估计没有明显持续漂移，运动方向与真实坐标约定一致。

- 滤波输出包含合理的协方差，且 TF 无重复发布。

### 常见问题

- ENU/NED 混用会让 IMU/GNSS 轴向错误，滤波参数无法修正坐标定义。

- 协方差填零不代表测量绝对精确；应理解包对各字段的解释。

- 把 map 与 odom 的职责合并，会使控制面对不连续位姿跳变。

### 练习

为履带底盘设计局部 EKF 与全局定位的 TF 分工，写出每个传感器贡献哪些状态，并用 bag 验证一项输入失效后的表现。

#### 参考答案

局部融合节点发布连续的 odom→base_link，使用轮式里程计与 IMU 的适当状态；全局 SLAM/定位或全局融合节点提供 map→odom。相同边只能有一个发布者。

断开一项输入后检查协方差、漂移、更新率和日志，而不是只判断节点是否还活着。输入选择不能把同一编码器派生的多项数据都视为独立高置信测量。

### 依据

- [robot_localization 项目](https://github.com/cra-ros-pkg/robot_localization)

- [Nav2：融合里程计](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/odom/setup_robot_localization/)

- [Nav2：建图与定位](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/sensors/mapping_localization/)

## 33. Nav2：从给定目标到可解释的导航行为

导航系统将目标、定位、地图、传感器和底盘控制组合起来。学习重点是能解释机器人为什么停下、为什么绕路，以及哪个服务器或输入条件导致失败。

### 学习目标

- 跑通官方仿真导航

- 区分规划器、控制器与 costmap

- 利用 lifecycle 和 action 反馈排查失败

### 先修

SLAM 或已知地图定位；tf2；差速控制；action

### 概念

全局规划器生成路径，局部控制器依据路径与局部环境产生速度，代价地图提供障碍与通行代价。

footprint 应覆盖机器人真实外形；圆形半径近似适合的对象有限。

导航 lifecycle 节点未 active、定位未初始化或 TF 不连通时，发布目标也不会得到正常运动。

### 把导航拆成可观察的能力链

一个导航目标进入系统后，定位提供机器人当前姿态，全局规划器选择通路，局部控制器生成速度，底盘执行命令，传感器不断更新障碍信息。Nav2 将这些能力分成服务器，并用行为树组织调用与恢复。地图只是其中一种环境信息，不能代替实时传感器或正确的机器人模型。

理解每一层的输入输出，比只记住某个 launch 名更有迁移价值。规划器通常输出路径，控制器输出车体速度，底盘输出关节运动与里程计。若路径正常但机器人不动，应向控制和底盘层追踪；若没有路径，先检查定位、地图和规划请求，不必先修改电机参数。

### 明确地图、代价地图与外形的区别

静态地图记录环境占据情况，costmap 在此基础上或局部传感器基础上构建通行代价。障碍层处理观察到的障碍，膨胀层为靠近障碍的区域增加代价。膨胀半径不等于机器人真实外形；footprint 描述机器人接触地面的几何范围，两者分别影响可行性与路径偏好。

长方形履带底盘转弯时扫过的区域大于中心点路径。用过小圆形半径近似会让规划看似能通过，实际车角却碰撞。应先确定模型尺寸与 footprint，再调路径平滑度、控制速度和膨胀代价。把速度降得很低不能弥补错误的碰撞几何。

### 建立导航必须满足的接口合同

定位和地图相关消息通常处于 map 坐标，局部运动使用 odom，底盘是 base_link，传感器必须通过 TF 连通。时间统一后，传感器消息才能正确落入代价地图。话题名称之外，还要核对 LaserScan 或 PointCloud2 类型、QoS、频率及障碍有效时间。

导航服务器采用生命周期管理，进程存在不等于已经 active。地图、定位或 TF 尚未准备好时，生命周期或行为树可能持续等待。速度输出的类型也要与下游驱动匹配，当前系统可能使用 Twist 或 TwistStamped；应实际查看，而不是用不同年代教程的默认值推断。

### 从官方集成仿真建立基线

在已正确安装系统 Jazzy 的 Ubuntu24.04 上安装 navigation2 和 nav2_bringup，并使用其集成示例。它包含机器人、仿真和 RViz 的常用组合，便于先验证一条已组织好的链路。此处命令是读者运行说明，本次没有执行安装或导航。下载依赖需要网络，教材正文与解释可离线阅读。

Jazzy 使用现代 Gazebo；若仿真资源缺失，安装对应 nav2-minimal-tb 系列包后再启动，不应改去使用 Iron 的 Gazebo Classic 包。启动完成后等待地图和 RViz 加载，观察节点状态。没有图形环境时需要相应无 GUI 配置，不能仅把窗口打不开等同导航失败。

#### 安装并启动 Jazzy 集成实验

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup
ros2 launch nav2_bringup tb3_simulation_launch.py headless:=False

```

若缺少仿真资源，核对 ros-jazzy-nav2-minimal-tb 系列包。该 launch 是常驻进程。

### 先定位，再下发一个明确目标

在 RViz 中使用 2D Pose Estimate，把初始位置放到与模拟机器人相符的地图位置，并拖动箭头设置朝向。定位尚不确定时，直接发送很远目标会同时引入多个变量。先选附近自由区域，观察粒子分布、全局路径、局部轨迹和速度命令，确认方向正确后再增加距离。

设置初始姿态不是永久锁定机器人位置，而是给定位器一个起始分布。若粒子或扫描与地图不匹配，应重新核对地图、frame、时间和初始朝向。不要用反复点击目标掩盖定位尚未成立的事实；目标取消、失败和成功都应该有可观察的 action 结果。

#### 检查系统状态

代码类型：commands

```bash

ros2 lifecycle nodes
ros2 lifecycle get /controller_server
ros2 action list -t
ros2 topic info /cmd_vel --verbose

```

有命名空间时替换为实际路径。把检查结果与 RViz 现象一起记录。

### 把调整限制在一个可解释变量上

首先固定地图、机器人外形和传感器合同，再调整速度与加速度范围，之后才比较规划器或控制器插件。每次使用同一组起终点和障碍场景，记录成功率、时间、最小障碍距离以及速度平滑程度。只看某一次走得更快，很容易把偶然定位差异误认为参数改进。

控制频率提高会增加计算负担，并不必然改善跟踪。传感器更新太慢、TF 延迟或底盘响应慢时，局部控制器仍然面对陈旧状态。查看整个链路的采样、计算与执行频率，确认瓶颈在哪里，再决定要优化算法、减少数据量还是更改硬件接口。

### 按失败阶段定位原因

目标被拒绝时检查 action 服务与生命周期；规划失败时检查目标是否在自由空间、地图连通和规划器约束；控制失败时检查局部障碍、进度判据、速度限制和底盘反馈；恢复失败时检查行为树是否允许当前恢复动作。错误发生的阶段决定优先检查对象。

导航成功的最低标准包括：action 报告成功，最终位置和朝向在设定容差内，过程没有违反定义好的外形和速度约束，停止后没有继续执行过期命令。加入临时障碍、取消和传感器失效实验，才能了解系统在正常路径之外如何表现。仿真验收仍不替代实机测试。

### 路径已经画出，机器人却不动

全局路径正常，局部控制器 active，但底盘状态保持零。

1. 查看 /cmd_vel 是否有发布以及真实消息类型。

2. 查看下游驱动的订阅类型和重映射。

3. 发现上游 TwistStamped 与驱动 Twist 不匹配。

4. 通过明确的适配或正确配置统一接口，再验证命令超时与停止。

验收：问题在控制接口合同，重新调规划器不会解决。

### 深入练习 1

footprint 与 inflation radius 是同一个量吗？

参考答案：不是。footprint 表达机器人几何，膨胀层表达靠近障碍的代价区域，两者不能互相替代。

### 深入练习 2

为什么先设置初始姿态再导航？

参考答案：定位器需要建立地图中的姿态估计，否则 TF 和代价地图无法可靠支持规划与控制。

### 深入练习 3

路径存在但不动先查哪里？

参考答案：先查局部控制输出、消息类型、重映射、控制器状态和底盘反馈，而非立即修改全局规划参数。

### 基础验证流程

#### 准备官方 Jazzy 仿真依赖

在已安装 ROS Jazzy 和配置软件源后安装 Nav2。

```bash

sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup

```

#### 启动集成示例

该示例依赖 nav2_bringup 的仿真资源，缺失时按官方 Quickstart 安装 nav2-minimal-tb 系列包。

```bash

ros2 launch nav2_bringup tb3_simulation_launch.py headless:=False

```

#### 建立定位再发送目标

在 RViz 使用 2D Pose Estimate 设置初始位置与朝向，再发送导航目标；观察全局路径、局部路径和代价地图。

#### 检查失败发生在哪一层

先看 lifecycle 状态，再看 action 类型和反馈，最后查传感器与 TF。

```bash

ros2 lifecycle nodes
ros2 lifecycle get /controller_server
ros2 action list -t
ros2 topic info /cmd_vel --verbose

```

### 预期结果

- 机器人在模拟环境中到达可通行的目标，并报告导航结果。

- 在路径被阻挡时能观察到重新规划或恢复，而不只看到停止。

### 常见问题

- Jazzy 选择现代 Gazebo；不要从同页 Iron 标签复制 Classic 安装命令。

- 地图坐标与初始位姿不一致会让粒子滤波定位失败。

- 改快控制频率不能解决错误 footprint、TF 延迟或速度接口不匹配。

### 练习

设计三个失败场景：目标在障碍中、激光丢失、局部路径被挡住，分别记录 action 结果、日志和 costmap 变化。

#### 参考答案

障碍中的目标通常在规划或目标可达性阶段失败；激光丢失要观察 costmap 数据有效性与传感器超时；临时阻挡主要观察局部控制、重规划和恢复。具体结果以当前插件和参数为准。

每个场景记录 action 的终态、错误日志、TF 连通性和代价地图截图/数据。能找到首次异常的组件，比记住单一错误码更重要。

### 依据

- [Nav2 仿真快速开始](https://docs.nav2.org/jazzy/getting_started/quickstart/quickstart/)

- [Nav2 首次机器人接入指南](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/)

- [Nav2 参数与插件配置](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/)

## 34. 导航任务编排：行为树与 Python Commander

导航服务器解决一次导航能力，任务层则决定下一步做什么、何时取消、失败后如何处理。先通过 Python Commander 编排简单流程，再深入行为树，把两层职责分清。

### 学习目标

- 用 Commander 发送目标并读取结果

- 理解行为树 tick、条件和恢复

- 避免阻塞式任务逻辑吞掉取消请求

### 先修

Nav2 仿真；Python；action 状态与取消

### 概念

行为树不是简单的顺序脚本；运行节点会跨 tick 保持状态，需要清晰处理成功、失败和运行中。

Simple Commander 封装常见导航 action，但调用前仍需 Nav2 服务 active 和有效定位。

任务成功要读取明确结果，不能因为 isTaskComplete 返回 true 就视为到达。

### 任务层与导航层分别负责什么

一次 NavigateToPose 解决“到达这个目标”，巡检程序还要决定访问顺序、超时、失败记录和是否继续下一点。任务层不应重新实现局部避障，导航层也不知道每个巡检点的业务意义。把两层分开后，测试任务逻辑可以复用同一套已验证导航能力。

BasicNavigator 是常见导航 action 的 Python 封装，简化客户端创建与反馈读取，但并不会自动启动所有服务、生成地图或建立定位。调用前仍需满足前章的服务器、TF、时钟和底盘合同。代码跑到 goToPose 一行不意味着机器人已经接受任务，更不意味着最后到达。

### 区分接受、运行、取消和结束

action 请求经历目标提交、接受或拒绝、运行中反馈、最终结果等阶段。任务结束可能是成功，也可能是失败或取消。isTaskComplete 仅表示当前等待阶段结束，必须继续读取结果。若程序在结束时不分原因就标记“完成”，巡检统计会把失败点算成已巡检。

取消同样是一个过程。发送 cancelTask 后，应等待服务器给出结果并继续观察底盘状态；任务结果属于软件协议，实际停止还取决于控制链和硬件。业务超时通常从导航任务开始计时，服务器启动等待应另设系统级期限，不能混用一个计时变量掩盖启动阻塞。

### 目标消息的坐标和时钟合同

PoseStamped 包含位置、单位四元数、frame 与时间戳。地图中的目标通常使用 map frame，位置单位为米，朝向用四元数表达。平面 yaw 转四元数时 z 等于半角正弦，w 等于半角余弦，其余两项为零。把 yaw 直接写进 orientation.z 不是合法的一般转换。

初始定位与导航目标不是同一件事。初始姿态告诉定位器机器人在哪里，目标告诉任务希望机器人去哪里。两者都应选择当前地图中合理位置。程序示例通过命令行显式提供起点和目标，避免把某一张演示地图的坐标假装成所有地图都可用的固定答案。

### 完整单目标任务脚本

把代码保存为 navigate_once.py，需要已安装 nav2_simple_commander 并运行前章的导航仿真。脚本设置初始姿态，等待服务激活，发送一个目标，超时后请求取消，并输出最终结果。它是完整应用脚本，但依赖已经运行的导航系统，不能单独替代地图、定位与驱动。代码未经本次 ROS 运行验证。

--sim-time 用于与仿真系统保持一致；真实系统通常不传该开关。--timeout 只约束目标执行阶段，waitUntilNav2Active 的启动等待不在此期限内。若启动条件不成立，应回到生命周期和 TF 检查，实际部署可再为进程启动设置独立监督期限。

#### navigate_once.py

代码类型：complete

```python

import argparse
import math
import time
import rclpy
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

def pose(nav, values):
    x, y, yaw = values
    result = PoseStamped()
    result.header.frame_id = "map"
    result.header.stamp = nav.get_clock().now().to_msg()
    result.pose.position.x = x
    result.pose.position.y = y
    result.pose.orientation.z = math.sin(yaw / 2.0)
    result.pose.orientation.w = math.cos(yaw / 2.0)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", nargs=3, type=float, required=True)
    parser.add_argument("--goal", nargs=3, type=float, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--sim-time", action="store_true")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("timeout must be positive")
    rclpy.init(args=[])
    nav = BasicNavigator()
    nav.set_parameters([Parameter("use_sim_time", Parameter.Type.BOOL, args.sim_time)])
    try:
        nav.setInitialPose(pose(nav, args.start))
        nav.waitUntilNav2Active()
        if not nav.goToPose(pose(nav, args.goal)):
            print("rejected")
            return
        deadline = time.monotonic() + args.timeout
        cancellation_requested = False
        while not nav.isTaskComplete():
            if time.monotonic() >= deadline and not cancellation_requested:
                nav.cancelTask()
                cancellation_requested = True
            time.sleep(0.1)
        result = nav.getResult()
        names = {TaskResult.SUCCEEDED: "succeeded",
                 TaskResult.CANCELED: "canceled",
                 TaskResult.FAILED: "failed"}
        print(names.get(result, "unknown"))
    finally:
        nav.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()

```

仅在已准备好的仿真中运行，起点和目标必须来自当前地图的有效自由空间。

### 将一次任务扩展为可审计巡检

不要简单把多个 goToPose 连在一起而不等待结果。为每个点保存目标、提交时间、接受状态、最终结果和失败原因，再决定继续、重试或退出。重试次数应有上限，重试前也应确认失败条件已经改变，否则只是在重复同一个错误。

巡检过程中的“到达”可能还需附加业务条件，例如停稳、采集图像或读取仪表。这些应作为独立阶段，导航成功后再验证。日志中的一行成功不代表相机数据已保存。若任务中断，持久化记录应足以决定从哪里恢复，避免重复执行不可重复的业务动作。

### 行为树描述一次导航内部的决策

行为树通过周期性 tick 评估条件与动作。节点可返回成功、失败或运行中，控制节点决定执行哪些子节点。恢复节点可以在规划或控制失败后调用清理代价地图、等待或其他策略，再重试主流程。它与普通顺序脚本最大的区别是运行中状态和重新评估机制。

修改 BT XML 时从安装版本提供的树复制到自己的配置包，保持插件类型和端口定义一致。新增一个条件后，先画出成功与失败两条路径，再运行场景。Rolling 文档里的新插件不一定已发布到 Jazzy，因此不能仅凭节点名字看起来合理就插入 XML。本章不提供脱离插件版本的伪完整行为树。

### 验证业务期限和异常路径

先用附近有效目标验证成功，再用不可达目标验证失败，最后用较短任务期限验证取消。比较脚本结果与 action 状态和底盘停止情况，确认三者一致。模拟服务器未激活时，应能把问题定位为启动条件，而不是将其记为正常导航失败。

循环内不要执行长时间图像计算或阻塞网络请求，否则反馈处理和取消可能延迟。任务层需要耗时业务时，使用明确的异步或独立执行结构，并保留取消传播。测试的重点是状态转换和责任边界，而不是让脚本在任何情况下都打印一条令人安心的结束消息。

### 三点巡检的状态记录

第二个路点被临时障碍堵住，但第三点仍可能可达。

1. 逐点执行并记录结果，而非同时覆盖当前目标。

2. 第二点超过期限后请求取消并等待确认。

3. 根据业务规则记录跳过原因或退出，不把失败计为完成。

4. 仅在规则允许时继续第三点，并单独记录其结果。

验收：能够恢复和解释任务过程，导航层与业务层各自的失败清晰可见。

### 深入练习 1

isTaskComplete 为真代表成功吗？

参考答案：不代表，必须读取最终结果区分成功、失败和取消。

### 深入练习 2

为什么目标执行超时用 monotonic 时钟？

参考答案：它适合计算经过时间，不受系统时间调整影响；是否使用真实时间或仿真时间作为业务期限应明确选择。

### 深入练习 3

行为树与巡检脚本为何不是重复实现？

参考答案：行为树通常组织一次导航中的规划、控制与恢复，巡检脚本组织业务路点和结果规则，层次不同。

### 基础验证流程

#### 先观察导航接口

在官方仿真启动且初始定位完成后，查看服务的 action 类型。

```bash

ros2 action list -t
ros2 action info /navigate_to_pose

```

#### 阅读 Commander 的最小流程

核心顺序为构建 BasicNavigator → 设置初始位姿 → waitUntilNav2Active → goToPose → 反馈/取消 → getResult。每个 PoseStamped 都填写 map frame、时间戳和合法四元数。

#### 为任务加上截止条件

循环等待任务时检查超时和反馈；取消后继续等待取消完成并记录最终结果。把移动中的异常状态留在日志和 bag 中。

#### 再修改行为树

复制安装包中与当前版本匹配的 BT XML 到自己的配置包，每次只调整一个恢复行为或规划条件，保留原始版本用于对照。

### 预期结果

- 任务脚本区分成功、失败和取消，并能在期限到达时停止等待。

- 行为树修改前后可通过相同场景复现差异。

### 常见问题

- Rolling 新增的 BT 插件不一定已发布在 Jazzy；插件名要从安装包核对。

- 坐标设为 (0,0) 不一定是有效导航目标，应在当前地图中选择自由空间。

- 在单线程回调内长期阻塞等待 action 可能妨碍反馈与取消处理。

### 练习

实现三个路点巡检：每个点记录到达结果与耗时，超过任务期限就取消；将应用任务层与 Nav2 内部 BT 的职责画成两层流程。

#### 参考答案

任务层按路点构造带 map frame 和时间戳的 PoseStamped，调用导航后持续检查反馈、超时与取消；任务完成后读取明确结果，再决定是否进入下一点。

应用层负责巡检顺序与业务期限，Nav2 BT 负责一次导航中的规划、跟踪与恢复。取消请求发出后还要等待确认并记录结果，不能立刻假定机器人已停止。

### 依据

- [Nav2 Simple Commander Python API](https://docs.nav2.org/jazzy/configuration_and_development/simple_commander_api/simple_commander_api/)

- [Nav2 参数与插件配置](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/)

- [Nav2 仿真快速开始](https://docs.nav2.org/jazzy/getting_started/quickstart/quickstart/)

## 35. MoveIt 2：规划场景、运动规划与轨迹执行

MoveIt 将机器人模型、关节状态、碰撞环境、运动学求解和轨迹执行接在一起。先在模拟或 mock 控制环境中完整走通“规划—检查—执行”，再接入真实机械臂控制器。

### 学习目标

- 区分 URDF、SRDF 与 MoveIt 配置

- 解释规划成功但执行失败的原因

- 对照 C++ MoveGroupInterface 与 Python moveit_py 的边界

### 先修

URDF/Xacro 与 TF；joint_states；action；ros2_control

### 概念

URDF 表达几何与关节；SRDF 增加规划组、末端执行器和语义关系。

规划场景包括机器人状态与环境碰撞对象；屏幕上看见物体不等于规划器已经把它当作障碍。

规划输出 JointTrajectory，执行仍依赖控制器及 FollowJointTrajectory 等接口。

### 把机械臂流程分成建模、规划与执行

MoveIt 根据机器人模型、当前关节状态、运动学求解器和环境碰撞信息计算运动路径，再交给执行接口完成。规划成功只说明找到了满足当前模型约束的候选轨迹，不证明真实机械臂已经执行，也不证明模型与现场完全一致。应在每个阶段留下可观察输出。

URDF 说明几何和关节，SRDF 说明规划组、末端执行器和语义，joint limits 限制可用范围，kinematics 配置选择求解器，controller 配置描述轨迹送到哪里。这些文件共同组成机器人配置，缺少任何一类都可能使“界面能打开”却无法完成规划或执行。

### 关节状态、坐标和控制接口必须一致

JointState 的名称、位置和时间戳定义当前机器人状态。规划场景若长期使用旧状态，生成的轨迹起点就可能与真实关节差距很大。关节角使用弧度，移动关节使用米，末端目标的 frame 必须能够变换到规划参考系。错误的工具安装变换会让目标在错误位置被解释。

轨迹执行常通过 FollowJointTrajectory action，控制器必须识别相同关节集合和名称。时间字段表示轨迹点相对开始时刻的到达时间，必须递增。速度与加速度若提供，也要与位置轨迹一致。MoveIt 控制器配置中的名称、action namespace 与 ros2_control 实际端点应一一对应。

### 准备一个不连接真实机械臂的基线

本章选用官方示例机器人配置的 mock 或 fake 控制后端。先安装 Jazzy 的 MoveIt 与示例资源，确认当前环境只 source 同一发行版。下面给出 Panda 配置包的常见二进制入口；若目标软件源没有该包，应停下来核对发布版本，不能把 main 分支随意混入当前工作区。

启动后应在 RViz 看到机器人模型、规划组和交互标记。先选择已定义的命名姿态或小范围合法目标，使用 Plan 生成路径，再检查轨迹展示，最后在 mock 环境执行。运行任何 demo 前明确其控制后端，避免把同一套启动文件误接到已有真实控制器。命令未在本次任务运行。

#### 准备 Panda mock 演示

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
sudo apt install ros-jazzy-moveit ros-jazzy-moveit-resources-panda-moveit-config
ros2 launch moveit_resources_panda_moveit_config demo.launch.py ros2_control_hardware_type:=mock_components

```

这是具名示例配置包的演示入口。运行前检查安装包中的 launch 默认使用的控制后端与当前 ROS 图。

### 用只读检查定位规划之前的问题

先确认 joint_states 正在更新，再确认机器人描述和语义配置已加载，最后检查所选 planning group 是否包含预期关节。RViz 显示模型只说明渲染拿到了部分信息，不代表 move_group 正在使用同一个完整参数集。尤其在多个命名空间中，参数和状态订阅路径可能不同。

在已有 MoveIt 配置中，分别记录规划参考 frame、末端 link、关节组和控制器 action 名称。任何代码示例都应把这些名称作为配置而不是默认猜测。Panda 示例里的组名不能直接用于 AUBO、UR 或自制机械臂，机械结构和控制关节数量也可能不同。

#### 检查输入与执行端点

代码类型：commands

```bash

ros2 topic echo /joint_states --once
ros2 action list -t
ros2 control list_controllers
ros2 param list /move_group

```

根据实际命名空间调整路径。先保存输出再调参数，便于确认修改是否生效。

### 理解轨迹文件而不立即驱动硬件

下方是 JointTrajectory 数据概念示例，只有两关节和两个时间点，展示名称顺序、位置及时间的对应关系。它不是 Panda 的完整控制目标，也不应直接发往任意机械臂。真实轨迹必须满足所有受控关节的名字、限位、速度、加速度及控制器允许的起点误差。

使用轨迹前逐点检查时间递增，并根据相邻位置差和时间差估算平均速度。这不能代替完整动态验证，但能抓住秒与毫秒混淆、角度与弧度混淆以及关节顺序颠倒等明显错误。把数据结构看懂之后，再使用规划接口生成符合实际模型的轨迹。

#### trajectory.yaml：数据结构概念示例

代码类型：concept

```yaml

joint_names: [joint_a, joint_b]
points:
  - positions: [0.0, 0.0]
    time_from_start: {sec: 1, nanosec: 0}
  - positions: [0.2, -0.1]
    time_from_start: {sec: 3, nanosec: 0}

```

此数据只用于解释结构，不是任何真实机器人的可执行目标；不要直接发布到设备。

### 规划场景与可视标记并不等价

向 RViz 发布一个 Marker 只会让观察者看见物体，规划器不会因此把它当作障碍。碰撞对象必须进入 planning scene，带有正确几何、姿态和 frame。附着物还要指定附着 link 和允许接触关系，才能让抓着物体的机械臂按正确外形规划。

做一个对照实验：先在无障碍场景规划到固定目标，再通过规划场景接口或 RViz 场景工具加入障碍，保持起点和目标不变。预期路径绕开障碍或明确返回无解。如果轨迹完全穿过障碍，先查场景同步、对象 frame 和规划组，而不是先更换规划算法。

### C++、Python 与版本之间的边界

MoveGroupInterface 提供常见的 C++ 规划和执行入口，moveit_py 提供 Python 侧接口；它们共享机器人配置与规划系统，但调用形式和能力细节不必完全一致。ROS1 的 moveit_commander 不能当作 ROS2 moveit_py 的等价导入。教程中的 main 页面是 Rolling，Jazzy 应以实际安装 API 为准。

排错按阶段进行：当前状态超时查 joint_states 与时间；逆解失败查目标和运动学；规划失败查碰撞和约束；执行失败查控制器 action、关节名字和跟踪容差。最终记录规划成功率、规划时间、执行结果及末端误差。mock 验证只证明软件配置链路，不证明真实机构动态性能。

### 规划成功但执行 action 不存在

RViz 可以显示规划轨迹，点击执行却失败。

1. 确认规划场景与当前状态有效。

2. 列出 action，发现配置指向的 FollowJointTrajectory 端点不存在。

3. 核对 ros2_control 控制器是否 active 以及实际 action namespace。

4. 修正 MoveIt 控制器映射，在 mock 环境再次执行并观察关节变化。

验收：修复的是执行集成，规划器本身不需要重新调参。

### 深入练习 1

Marker 能阻止 MoveIt 规划穿过物体吗？

参考答案：不能，必须把碰撞对象加入 planning scene；显示与规划是不同数据通道。

### 深入练习 2

关节名字正确但顺序错误有何影响？

参考答案：轨迹数值可能被对应到错误关节，导致规划或执行异常，必须按 joint_names 与每个数组逐项对应。

### 深入练习 3

Panda 的规划组名能直接用到其他机械臂吗？

参考答案：不能，规划组来自该机器人的 SRDF，必须核对实际配置和关节集合。

### 基础验证流程

#### 固定教程和源码版本

先阅读入门环境指导并锁定 Jazzy 的 MoveIt 软件包/源码。main 文档是 Rolling，必要时查 Jazzy 头文件和示例。

#### 用已配置好的机器人演示包启动

选择官方教程对应的 Panda 或自己的 MoveIt 配置包，先启用 mock/fake 后端。不要省略机器人描述、语义模型和控制配置。

#### 检查状态与执行接口

在 RViz 中规划到命名姿态前，确认关节状态持续更新以及控制 action 存在。

```bash

ros2 topic echo /joint_states --once
ros2 action list -t
ros2 control list_controllers

```

#### 加入一个碰撞物体再规划

比较无障碍与有障碍时的路径；确认 planning scene 收到对象，而不是仅在 RViz 添加了一个视觉 marker。

### 预期结果

- RViz 能显示有效机器人状态并规划到合法目标。

- 执行 action 返回的结果与模拟机器人关节变化一致。

### 常见问题

- 目标不可达、IK 无解、碰撞和控制器错误属于不同阶段，应分别查看错误码。

- Python moveit_py 与旧 ROS1 moveit_commander 不可混为同一套 API。

- moveit.picknik.ai/jazzy 并非本次可核实的文档入口，不能凭路径猜测存在。

### 练习

为同一机械臂任务分别记录规划时间、规划成功率和执行结果，故意加入碰撞物体验证场景同步。

#### 参考答案

规划时间从请求到返回轨迹计算，执行时间从发送控制 action 到结果返回；两者必须分开记录。规划成功但 controller action 不可用，属于执行集成失败。

加入碰撞物体后应确认 planning scene 中存在对象，并观察路径绕行或返回无解；仅向 RViz 发布 marker 不满足验收。

### 依据

- [MoveIt 2 教程总览](https://moveit.picknik.ai/main/index.html)

- [MoveIt 2 入门环境](https://moveit.picknik.ai/main/doc/tutorials/getting_started/getting_started.html)

- [MoveIt 2 Jazzy 源码](https://github.com/moveit/moveit2/tree/jazzy)

- [joint_trajectory_controller](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html)

## 36. 机械臂进阶：Servo 与 Task Constructor

离线轨迹规划、在线增量伺服和多阶段抓放解决不同问题。Servo 适合连续交互或视觉伺服，Task Constructor 把接近、抓取与放置拆成可组合阶段，二者都依赖准确模型和状态反馈。

### 学习目标

- 区分规划一次轨迹与持续发送增量命令

- 理解 Servo 的坐标、限速与碰撞约束

- 把抓放任务分成具有明确输入输出的阶段

### 先修

MoveIt 基础规划；控制器轨迹接口；碰撞模型与末端坐标系

### 概念

Servo 输入表达关节或末端增量运动，输出需要匹配下游控制器；消息坐标系错误会改变运动方向。

Servo 的软件碰撞/奇异性处理不替代驱动限制和硬件安全机制。

MTC 用阶段传播候选解，能分别解释抓取姿态生成、IK、接近和连接阶段的失败。

### 三种运动问题需要三种组织方式

预先规划一段轨迹适合明确起点、目标和碰撞环境；Servo 适合持续输入小增量并根据最新状态更新；多阶段抓放需要把接近、对准、夹持和搬运等步骤组织起来。选择方式取决于任务的信息变化和控制周期，而不是哪套 API 看起来更简短。

MoveIt Task Constructor 将复杂任务分为阶段，并在阶段间传递候选解。某个抓取姿态可能有逆解，却无法从当前状态接近；另一个姿态可能能接近，但夹持后无法抬升。分阶段表示有助于解释哪一项约束首先使任务失败，避免把所有失败都归结为“规划不好”。

### Servo 的输入输出与坐标合同

在线伺服常输入关节增量速度或末端笛卡尔速度，输出满足下游控制接口要求的关节命令。TwistStamped 的 frame_id 说明速度在哪个坐标中表达，同样的 x 方向在工具坐标和基座坐标中可能完全不同。时间戳和输入超时定义了命令何时仍然有效。

关节反馈必须足够及时，碰撞模型与场景需要持续一致。软件可以根据奇异性和碰撞距离缩放速度，但这些功能不等同硬件急停或认证安全控制。Rolling 文档中存在的命令类型、服务名和参数，不一定已经进入 Jazzy，接入时应先列出安装包真实接口。

### 用离线数值实验理解增量运动

在启动机器人之前，可先验证速度与周期的关系。若每秒希望关节转动零点二弧度，控制周期为十毫秒，则单周期位置增量为零点零零二弧度。若周期抖动，使用固定时间步积分会与真实时间产生差异；若队列积压，又会执行过时意图。

下面脚本用有界速度和显式时间步生成关节增量，并检查输出。它只是纯 Python 的数值模型，不调用 MoveIt，也不是完整 Servo 算法。通过这种小实验先理解限幅和时间，再观察真正 Servo 的输出，可以避免把单位错误误判为运动学或线程问题。

#### increment_check.py：完整离线实验

代码类型：complete

```python

def step(position, requested_velocity, dt, velocity_limit):
    if dt <= 0 or velocity_limit <= 0:
        raise ValueError("positive dt and limit required")
    velocity = max(-velocity_limit, min(velocity_limit, requested_velocity))
    return position + velocity * dt

if __name__ == "__main__":
    q = 0.0
    for _ in range(100):
        q = step(q, 0.2, 0.01, 0.1)
    assert abs(q - 0.1) < 1e-9
    print("position after one second:", q)

```

输出应为约零点一弧度，因为请求速度被限幅。本次编写未执行该实验。

### 在模拟中建立在线命令链

先完成上一章的模型、状态和 mock 控制器，再选择与 Jazzy 安装版本相符的 Servo launch 配置。启动后列出输入话题、命令类型选择服务、状态输出和控制器端点，把它们写入实验记录。先只观察系统是否准备好，不要立即连续发送多轴命令。

第一组运动仅在模拟中测试单轴小速度，检查方向和输出关节；第二组停止输入，检查命令超时；第三组将目标靠近模型限位或受控障碍，观察软件缩放或拒绝。每次保留明确的停止路径。参数文件至少说明 planning frame、末端 link、输入话题、输出类型和命令超时。

#### 运行前只读核查

代码类型：commands

```bash

ros2 pkg prefix --share moveit_servo
ros2 topic list -t
ros2 service list -t
ros2 action list -t
ros2 topic echo /joint_states --once

```

这是接口调查命令，不会启动伺服或驱动机械臂。记录实际接口后再按本机版本配置测试。

### 把抓放分解成具有后置条件的阶段

一个自足任务至少包括获取当前状态、打开夹爪、移动到预抓取位姿、接近、闭合、确认抓取、抬升、转移、放置和释放。每一步都要有可检查的成功条件。夹爪 action 完成只证明控制动作结束，不证明物体真的被抓住，业务上可能还需要力、触觉或视觉反馈。

MTC 阶段可以生成候选状态、向前或向后传播运动、连接两个可行片段。阶段顺序不应只按照自然语言排列，还要考虑需要哪些前置状态与碰撞允许关系。夹持后应把物体附着到正确 link，放置后再解除附着，否则规划场景与真实搬运状态会逐渐脱离。

#### 任务状态表：完整概念示例

代码类型：concept

```text

PREGRASP -> APPROACH -> CLOSE -> VERIFY -> LIFT -> TRANSFER -> PLACE -> OPEN
APPROACH 失败：退回已知预抓取状态
VERIFY 失败：不抬升，重新观察或释放
TRANSFER 失败：保持已验证夹持，重新规划或进入人工处理
OPEN 成功：确认释放，解除场景中的附着对象

```

这是业务状态设计，不是可直接执行的 MTC 源码；每个阶段的真实 API 与机器人配置相关。

### 让感知更新与运动决策协调

视觉给出的物体位姿可能抖动或延迟，不能把每帧检测直接作为无限速度的新目标。先将检测变换到规划参考系，确认时间、置信度和目标身份，再决定是否更新目标。目标已经被夹持后，其状态模型也应改变，不能继续把原始桌面检测当作唯一真值。

接近阶段可用小范围 Servo 修正，长距离绕障则通常需要规划。两者交接时明确谁拥有控制接口，避免两个命令源同时有效。切换应有停止、确认和接管条件；只是暂停某个 Python 循环，不一定释放底层控制资源或清空已经排队的命令。

### 以失败注入验证完整任务

在模拟中分别设置不可达抓取姿态、碰撞阻挡、反馈停止、目标丢失和夹持失败。每种情况都应在正确阶段失败并进入定义好的恢复。若所有失败都统一重启整个系统，说明任务状态还不够明确，也不利于保护已经握持的物体。

记录阶段耗时、候选数量、首个失败原因和最终业务结果，才能比较策略。性能指标不能只包括抓取成功次数，还应包括错误抓取、恢复成功和物体损伤等与任务相关的结果。本章的离线与模拟设计没有验证任何真实机械臂安全性能。

### 夹爪闭合但物体未被抓住

闭合 action 返回成功，视觉仍看到物体在桌面。

1. 将 action 成功解释为夹爪动作完成。

2. 进入 VERIFY 阶段检查物体或夹持反馈。

3. 验证失败时保持机械臂在已知接近状态，不执行抬升。

4. 释放或重新观察后再生成候选抓取。

验收：控制协议成功与业务抓取成功被明确区分。

### 深入练习 1

Servo 输入 frame 错误会造成什么？

参考答案：同样数值会沿错误坐标轴解释，运动方向与操作者意图不一致，必须核对参考系。

### 深入练习 2

为什么抓放要有 VERIFY 阶段？

参考答案：夹爪动作完成不等于物体被可靠夹持，需要独立反馈确认业务条件。

### 深入练习 3

规划与 Servo 切换只停一个上层循环够吗？

参考答案：不一定。需要处理控制权、队列、超时和接管状态，避免两个命令源同时作用。

### 基础验证流程

#### 先核对 Jazzy 支持的接口

以 moveit2 的 jazzy 分支确认 Servo 的消息、服务和参数；Rolling 教程中出现的新命令类型只作为扩展阅读。

```bash

ros2 pkg prefix --share moveit_servo
ros2 service list -t
ros2 topic list -t

```

#### 先运行模拟示例

按所选版本的 Servo 演示启动完整模型与控制器，确保 joint_states 及时且坐标链连通。

#### 从单轴小增量开始

只在模拟中检查关节方向、末端 frame 与停止行为；逐步增加复杂度，记录指令超时后的输出。

#### 按阶段调试抓放

将 MTC 任务拆成当前状态、打开夹爪、接近、生成抓取、闭合、抬升、转移、放置；失败时检查第一个无解阶段。

### 预期结果

- 能解释同一目标为何适合规划、Servo 或多阶段任务。

- 模拟中停止输入后不会持续沿旧命令运动。

### 常见问题

- Rolling Servo 教程中的服务名和输入支持不能未经核对用于 Jazzy。

- 末端速度在工具坐标系与世界坐标系中含义不同。

- 夹爪闭合成功只说明执行接口完成，不自动证明物体被可靠抓取。

### 练习

设计一个模拟抓放流程，为每个阶段列出成功条件、失败恢复以及需要的传感器反馈；说明哪一步可以使用 Servo。

#### 参考答案

至少拆成接近、对准、闭合夹爪、确认抓取、抬升、转移、放置与释放。每阶段分别定义位置、力/触觉或视觉确认及失败恢复。

近距离连续对准可用 Servo，远距离绕障碍移动可用轨迹规划，多阶段候选解组织可用 MTC；最终选择取决于传感器和控制接口，不是 API 名称。

### 依据

- [MoveIt Servo 教程](https://moveit.picknik.ai/main/doc/examples/realtime_servo/realtime_servo_tutorial.html)

- [MoveIt Task Constructor 抓放教程](https://moveit.picknik.ai/main/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.html)

- [MoveIt 2 Jazzy 源码](https://github.com/moveit/moveit2/tree/jazzy)

## 37. micro-ROS：把微控制器纳入 ROS 图

micro-ROS 在资源受限设备上实现 ROS 2 客户端能力，通过 Agent 与较大计算机上的 ROS 系统连接。先用主机示例理解会话，再讨论板卡、实时性和静态内存。

### 学习目标

- 解释 client、transport、Agent 的分工

- 保持固件与 Agent 的接口版本一致

- 区分执行器逻辑与底层 RTOS 调度

### 先修

C 语言；发布订阅；串口或 UDP 基础

### 概念

Agent 建立通信桥，但微控制器的控制逻辑与故障响应仍需自身设计。

动态长度消息需要预先规划内存；桌面端随手创建容器的写法不适合直接搬到小内存设备。

ROS 发行版、板卡工具链与 micro-ROS 分支共同决定兼容性。

### client、传输和 Agent 各做一层工作

micro-ROS 把 ROS 2 客户端能力带到资源受限设备。微控制器上的应用建立节点、发布者和订阅者，通过选定传输与主机 Agent 建立会话，Agent 再与较完整的 ROS 系统交互。它不是把桌面 Linux 全部搬到 MCU，也不会让任意板卡自动拥有足够内存和算力。

把这三层分开有助于排错：固件负责本地逻辑与设备采样，传输负责串口或网络字节，Agent 负责会话与图连接。Agent 启动成功只是主机端准备好，客户端尚未连接时 ROS 图里可能没有预期节点。必须同时观察会话日志和消息数据。

### 资源约束影响程序结构

桌面程序可以频繁创建字符串、向量和动态消息，MCU 往往需要预先规划容量和生命周期。包含可变长度字段的消息尤其要明确分配策略。队列、执行器句柄、传输缓存与应用栈都占内存，不能只按一个消息结构体的大小估算需求。

rclc executor 决定回调和定时器如何被调度，但底层 RTOS、驱动中断和控制任务仍有自己的时序。一个 ROS 回调处理过久可能拖延其他事件。需要硬实时的电机环通常应在设备本地明确组织，通信回调只更新有界目标或状态，不应让网络抖动直接决定控制周期。

### 先完成主机上的 Agent 与通信实验

选择 Linux 主机实验可以先理解会话，而不涉及刷写或损坏硬件。Jazzy 路线使用 micro_ros_setup 的 jazzy 分支，在独立工作区安装依赖并构建工具，再构建 Agent。下面步骤未在本次执行，下载和编译需要网络及工具链，正文解释可离线阅读。

micro-ROS 网站已经迁移，部分入门正文仍以 Humble 为例，因此不能照抄旧容器标签。工具分支、Agent 和客户端类型支持应属于一致版本集合。若构建失败，记录实际提交和依赖错误，不要通过混入其他发行版的 setup 脚本尝试解决。

#### 构建主机 Agent 的具体顺序

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
mkdir -p "$HOME/microros_learning_ws/src"
cd "$HOME/microros_learning_ws"
git clone -b jazzy https://github.com/micro-ROS/micro_ros_setup.git src/micro_ros_setup
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --symlink-install
source install/local_setup.bash
ros2 run micro_ros_setup create_agent_ws.sh
ros2 run micro_ros_setup build_agent.sh
source install/local_setup.bash

```

使用全新工作区；已存在源码时先检查，不重复覆盖。系统初次 rosdep 初始化另行完成。

### UDP 与串口使用不同连接合同

UDP 客户端必须知道 Agent 所在主机地址和端口，双方要有网络路由；串口客户端和 Agent 则需要设备路径、波特率及访问权限一致。把 UDP 端口写正确不能解决串口权限，选择正确传输后再观察对应层的证据。防火墙和容器网络也会影响 UDP 会话。

下面分别展示两种 Agent 入口，一次实验只选择一种。设备路径必须换成真实枚举结果，不应随意对所有设备放开权限。Agent 详细日志用于观察会话建立、实体创建和断线，稳定运行后可降低日志量。启动 Agent 不会自行产生传感器节点，仍需要匹配客户端。

#### UDP Agent

代码类型：commands

```bash

ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888 -v6

```

客户端需配置此主机地址与端口；这是常驻服务。

#### 串口 Agent：替换实际设备路径

代码类型：commands

```bash

ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0 -b 115200 -v6

```

仅在固件使用同一串口传输和波特率时使用。

### 定义一条可完整验证的电机通信合同

以底盘为例，上位机发送目标车体速度，MCU 更新本地控制目标并周期性读取编码器，返回里程计或轮速。应明确每项量的单位、正方向、频率、最大消息年龄和失联动作。上下位机都需要知道命令何时过期，而不是只依赖 DDS 已收到一条消息。

自定义消息需要在双方构建相同接口。仅在主机安装一个新的 msg 包，不会自动改变已经烧录的固件。改变字段顺序、类型或数组长度后应重新生成并编译客户端与 Agent 相关支持，保存接口版本。名称相同但类型定义不同也可能无法通信。

### 先用离线状态机验证失联逻辑

下面程序模拟命令新鲜度判断，不调用 ROS、不写电机，也不代表完整固件。它使用单调经过时间，避免系统时钟调整造成超时判断混乱。程序表达一条清楚规则：只有已收到命令且年龄在阈值内，才允许目标进入控制层。

真实固件还需结合使能、急停、驱动故障和通信状态。恢复连接后是否自动恢复旧目标要明确设计，通常不应把断线前的陈旧命令重新当作新命令。通过断线、重连和重新启动的顺序测试，能暴露仅正常运行时看不出来的状态错误。

#### watchdog_model.py：完整离线状态模型

代码类型：complete

```python

def accepted_target(now, received_at, requested, timeout=0.3):
    if received_at is None:
        return 0.0
    age = now - received_at
    if age < 0 or age > timeout:
        return 0.0
    return max(-0.2, min(0.2, requested))

assert accepted_target(1.0, None, 0.1) == 0.0
assert accepted_target(1.1, 1.0, 0.1) == 0.1
assert accepted_target(1.5, 1.0, 0.1) == 0.0
assert accepted_target(1.1, 1.0, 0.8) == 0.2
print("watchdog model checks passed")

```

这是明确的教学模型，未在本次执行；实机停止路径需要独立验证。

### 按重启和失效矩阵完成验收

至少测试客户端先启动、Agent 先启动、客户端重启、Agent 重启和传输断开。每个场景记录会话是否恢复、ROS 实体是否重新出现、命令是否保持过期、状态是否被正确标记。节点重新可见不代表所有业务状态已经恢复。

参考本地 Linorobot2 固件时，先核对板卡、PlatformIO 环境、传输、接口与上位机分支。它提供工程组织参考，不意味着任何电机驱动和编码器都能直接使用相同参数。验收结果应写清实际硬件与软件版本，本章没有对任何板卡刷写或实机行为作运行证明。

### Agent 正常运行却没有 MCU 话题

主机进程没有退出，但 ros2 topic list 看不到预期编码器数据。

1. 查看 Agent 是否真正建立客户端会话。

2. 核对固件使用 UDP 还是串口以及地址或设备配置。

3. 会话建立后检查实体创建和接口类型支持。

4. 最后查看固件采样任务是否发布，并验证断线停止规则。

验收：从会话层逐步定位，不把空 ROS 图直接归因于 QoS。

### 深入练习 1

Agent 启动成功等于 MCU 已连接吗？

参考答案：不等于，需要会话、实体创建日志以及实际数据证明。

### 深入练习 2

改了自定义 msg 只重编主机够吗？

参考答案：不够，客户端和相关类型支持也要保持一致，固件需重新生成和构建。

### 深入练习 3

通信回调能代替硬实时电机环吗？

参考答案：不能自动代替。网络和调度抖动需要与本地控制周期隔离，并设计明确的目标更新与超时机制。

### 基础验证流程

#### 从迁移后的官方文档进入

新版站点为 micro.vulcanexus.org；Linux 教程正文仍使用 Humble，应将其作为流程说明并核查 Jazzy 分支。

#### 先在主机验证工具链

在独立工作区构建 Jazzy 的 micro_ros_setup 或按维护者提供的发行包准备 Agent。先运行 Linux ping/pong，再选择具体板卡。

#### 启动匹配传输的 Agent

以下示例仅启动 UDP Agent，不刷写设备。微控制器端必须配置相同主机地址和端口。

```bash

ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888

```

#### 验证会话与图发现

连接客户端后先观察 Agent 会话日志，再检查节点和话题；自定义消息必须在双方生成一致的类型支持。

```bash

ros2 node list
ros2 topic list -t

```

### 预期结果

- 客户端会话建立后，主机 ROS 图能发现预期实体。

- 重启客户端或断开传输时，系统按设计恢复或报告故障。

### 常见问题

- 串口设备权限与波特率问题不同于 ROS QoS 问题，应逐层检查。

- Agent 能启动不代表固件已经连接；需要会话日志与话题证据。

- micro-ROS 不自动提供安全认证或硬实时控制保证。

### 练习

用 Linorobot2 硬件参考，列出上位机与 MCU 的消息、频率、单位、时间源以及失联停止条件。

#### 参考答案

上位机通常发送车体速度，MCU 采集编码器与 IMU 并执行底层控制，经 micro-ROS Agent 向 ROS 图发布。每项消息记录单位、频率、时间源与传输方式。

验收至少包含客户端重启、Agent 重启和传输断开三种情形。失联停止应由靠近执行机构的逻辑保证，不能依赖网页或上位机继续运行。

### 依据

- [micro-ROS 官方新站](https://micro.vulcanexus.org/)

- [micro-ROS Linux 首个应用](https://micro.vulcanexus.org/docs/tutorials/core/first_application_linux/)

- [micro_ros_setup Jazzy](https://github.com/micro-ROS/micro_ros_setup/tree/jazzy)

- [micro-ROS Agent Jazzy](https://github.com/micro-ROS/micro-ROS-Agent/tree/jazzy)

- [linorobot2_hardware 本地固定提交](https://github.com/linorobot/linorobot2_hardware/tree/fbbbb922f4bd778e23268210b7bd7a6ac4c75d83)

## 38. 多机器人：命名、隔离与 Open-RMF 任务协调

两台机器人一起运行时，问题首先是身份、坐标和数据隔离，然后才是任务分配。Open-RMF 在更高层协调车队与设施，而每台机器人的定位和避障仍需要可靠运行。

### 学习目标

- 为机器人建立一致命名方案

- 区分 ROS_DOMAIN_ID 隔离与命名空间

- 理解车队适配器和交通协商的职责

### 先修

命名空间与 remap；Nav2；tf2；网络发现

### 概念

命名空间改变 ROS 资源名，但不会自动重写消息中的 frame_id；这两种命名要一同设计。

同一域中允许共享地图与任务信息，也要避免 /cmd_vel、/tf 等资源碰撞。

RMF 的 fleet adapter 把车队状态和任务接口接到协调系统；它不是统一替代所有机器人驱动。

### 从两台机器人的身份开始设计

单机器人常使用全局 /cmd_vel、/scan 和 /odom，多机器人直接复制后就可能互相覆盖。第一步不是分配复杂任务，而是为每台机器人定义唯一身份，并让节点、话题、服务和 action 在可预测的命名空间下运行。共享资源应显式列出，不能让它们恰好因为名字相同而混在一起。

命名空间解决 ROS 图资源名的组织，frame_id 是消息内部字符串，通常不会自动跟着改变。两台机器人若都发布 odom 到 base_link，即使命令话题已经隔离，TF 仍可能冲突。身份方案应同时覆盖图名称、TF 名称、设备标识、地图关系和日志目录。

### 先做完整的双 turtlesim 隔离实验

本章用桌面包中的 turtlesim 建立最小实验，不需要两台实体底盘。分别启动两个窗口，给它们不同命名空间，再把键盘控制节点放入其中一个命名空间。预期只有目标窗口中的海龟响应。这个实验只验证图名称隔离，不包含 TF、网络延迟或真实避障。

每个常驻命令在独立终端运行，并 source 同一 Jazzy 环境。终端必须有图形显示支持，键盘控制终端保持焦点。下面命令未在本次执行，读者应先列出真实话题，再验证控制只作用于预期实例。

#### 两个模拟机器人

代码类型：commands

```bash

ros2 run turtlesim turtlesim_node --ros-args -r __ns:=/robot1
# 另一个终端：
ros2 run turtlesim turtlesim_node --ros-args -r __ns:=/robot2
# 第三个终端，只控制 robot1：
ros2 run turtlesim turtle_teleop_key --ros-args -r __ns:=/robot1

```

三个常驻进程分别运行。相对话题会被展开到对应命名空间。

#### 检查隔离结果

代码类型：commands

```bash

ros2 node list
ros2 topic info /robot1/turtle1/cmd_vel --verbose
ros2 topic info /robot2/turtle1/cmd_vel --verbose

```

比较两条命令话题的发布和订阅端点，验证没有意外串线。

### 命名空间和域隔离解决不同问题

同一 ROS_DOMAIN_ID 中的机器人可以发现并共享数据，命名空间用来组织各自资源。不同域通常互相不直接发现，可以作为逻辑分组，但不等于身份认证或访问授权。跨域通信需要明确的桥接或其他架构，不能只把域号改回相同就宣称已经完成安全设计。

多机器人既需要共享全局任务，又可能需要隔离高带宽传感器。应按带宽、失联行为和权限定义哪些信息跨边界传递。例如共享低频状态和任务结果，而原始相机留在本机处理。桥接还需要时间戳和来源身份，避免调度器误把旧状态当作当前状态。

### 规划共享坐标与每台机器人的局部坐标

一种常见设计使用共享 map，再为每台机器人保留独立 odom 和 base frame。定位器提供 map 到该机器人 odom，局部估计提供机器人 odom 到 base。传感器 frame 继续带上该机器人的身份前缀。另一种设计让机器人使用不同地图，再通过经过定义的地图变换连接，复杂度更高。

共享 /tf 话题本身并不危险，关键是 frame 名是否唯一和关系是否一致。反过来，把 /tf 重映射为不同话题，也不自动解决上层算法如何同时查询各机器人坐标的问题。选择方案时应明确消费者需要哪棵树、在哪里获得它，以及多地图时如何处理漂移和全局修正。

### Open-RMF 协调的是车队与设施

机器人本机导航负责局部定位、路径跟踪和避障，Open-RMF 在更高层组织任务、车队和设施交通。fleet adapter 把某种机器人或厂商车队的状态、任务和完成反馈翻译给协调系统。门、电梯等设施也需要适配接口，不能仅在地图上画一个图标就认为可以被调度。

交通计划反映预期占用，不等于所有机器人都会绝对按计划执行。适配器应持续报告实际位置、剩余任务和异常，协调层才能调整。先把单台机器人任务的成功、失败、取消和重连做可靠，再接到车队层；否则车队调度只会放大已有不确定性。

### 用离线资源模型理解共享通道

下方是完整的教学资源预约程序：两台机器人申请同一个窄门，只有当前持有者释放后下一台才能进入。它不是 Open-RMF 的实现，也没有解决路径规划、死锁或分布式一致性；它用最少代码表达资源所有权为什么必须显式存在。

真实系统还需要租约、超时、持有者失联、取消和恢复策略。如果机器人失联时立即释放资源，但实际机器人仍停在门内，另一台就可能被派往已占用区域。因此“软件任务结束”和“物理资源已空闲”应有独立的确认条件。

#### reservation_model.py

代码类型：complete

```python

owners = {}

def acquire(resource, robot):
    current = owners.get(resource)
    if current is None or current == robot:
        owners[resource] = robot
        return True
    return False

def release(resource, robot):
    if owners.get(resource) != robot:
        raise ValueError("only owner may release")
    del owners[resource]

assert acquire("door_a", "robot1")
assert not acquire("door_a", "robot2")
release("door_a", "robot1")
assert acquire("door_a", "robot2")
print("reservation model checks passed")

```

纯 Python 概念实验，未在本次执行；不能作为真实交通安全控制器。

### 验收多机器人系统的异常路径

在正常任务之外，模拟一台机器人离线、一个门不可用、地图版本不一致和任务被取消。检查其他机器人是否仍可运行，调度器是否显示明确原因，以及旧任务是否会在重连后意外恢复。给每台机器人保留独立日志与数据标识，才能追踪跨系统事件顺序。

最低验收包括命令不串线、状态有唯一来源、TF 不冲突、任务结果可追踪、共享资源有明确释放条件。多机器人数量增加后再测带宽与发现开销，而不是仅复制更多节点观察是否启动。相同配置在两台成功，不保证在几十台和无线网络中仍有相同性能。

### 两台底盘使用同名 frame 导致显示跳动

命令已经放进 robot1 和 robot2 命名空间，但 RViz 中底盘位置来回跳。

1. 检查 /tf，发现两台都声明 child frame 为 base_link。

2. 为 frame 设计独立名称并修改模型、驱动和导航配置。

3. 保留清楚的共享 map 关系。

4. 再验证话题命名空间和消息内部 frame 同时正确。

验收：图资源隔离与坐标身份隔离同时成立。

### 深入练习 1

命名空间会自动改 frame_id 吗？

参考答案：通常不会，消息内部坐标名称必须由模型或节点参数显式配置。

### 深入练习 2

机器人掉线就能立即释放门资源吗？

参考答案：不能简单这样做，机器人可能仍占用物理通道，需要定义额外确认和恢复策略。

### 深入练习 3

Open-RMF 能替代本机 Nav2 吗？

参考答案：不能直接替代。它协调车队和设施，本机仍需要可靠定位、运动与避障能力。

### 基础验证流程

#### 先在仿真中复制两台机器人

使用 robot1、robot2 两个命名空间，并记录每台机器人 TF frame 的完整名字。

#### 检查资源是否串线

查看各自节点、话题与 action；向 robot1 发出任务时，robot2 的控制接口不应收到该命令。

```bash

ros2 node list
ros2 topic list -t
ros2 action list -t

```

#### 加入共享设施与任务层

阅读 Open-RMF 主仓库对应发行版的依赖清单，再选一个已维护的 rmf_demos 场景学习门、电梯和车队适配。

#### 定义恢复和观测

模拟一个机器人离线、门不可用或任务被取消，明确任务层与机器人层各自报告什么状态。

### 预期结果

- 两台机器人的传感器、TF 与命令互不串线。

- 协调层能观察任务进展及失联，而不是只依赖网页上的位置动画。

### 常见问题

- 共享 /tf 不等于 frame 名可以重复。

- ROS_DOMAIN_ID 不同通常无法直接发现彼此，需要明确的桥接或跨域设计。

- RMF 交通计划与机器人局部避障是不同层次，不能只实现其中之一。

### 练习

画出两台底盘、一扇门和一个调度器的数据图，标出私有资源、共享资源和每类故障的负责组件。

#### 参考答案

robot1、robot2 的命令、传感器与局部 TF 身份应独立；地图或调度任务可以共享，但共享规则要明确。消息内 frame_id 需显式命名，不能只靠 ROS namespace。

门状态由设施适配器负责，车队任务由调度/适配层负责，机器人避障与执行由本机负责。离线或取消时各层应有可观察结果。

### 依据

- [Open-RMF 主仓库](https://github.com/open-rmf/rmf)

- [Open-RMF 演示工程](https://github.com/open-rmf/rmf_demos)

- [Nav2 首次机器人接入指南](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/)

## 39. 通信与安全：DDS、Zenoh、发现和权限边界

分布式 ROS 系统的排错应从网络连通、发现、类型、QoS 到应用逻辑逐层推进。更换 RMW 是一次通信架构选择，安全身份与访问控制也必须独立于域号配置。

### 学习目标

- 理解 DDS 与 Zenoh 的发现差别

- 避免 CLI daemon 残留造成错误观察

- 知道域隔离与身份授权的区别

### 先修

QoS；网络与端口基础；环境变量

### 概念

DDS 实现共享标准接口，但其发现、传输与调优配置不同；上游 latest 文档也可能超出 Jazzy 包版本。

rmw_zenoh 默认配置依赖路由器进行发现；直接套用 DDS 多播经验可能看不到节点。

SROS2 基于密钥库、身份和权限策略；ROS_DOMAIN_ID 只用于逻辑分组，不是认证。

### 按照发现、数据和应用三层理解通信

两个节点不能互通时，先判断是否发现彼此，再判断消息类型与 QoS 是否兼容，最后检查应用是否正确处理数据。网络连通测试只能证明部分传输路径，不保证 ROS 发现和数据流成立。节点列表为空也可能是本地 CLI daemon 使用了不同 RMW，而不是远端程序根本没有启动。

RMW 将 ROS 上层接口连接到底层通信实现。Fast DDS、Cyclone DDS 与 Zenoh 的发现和配置机制不同，应用消息不变并不代表网络部署方式完全相同。更换实现应当是可记录、可回退的实验，所有参与进程和观察工具的环境都要一致。

### 先建立可重复的双机基线

记录每台主机的 ROS 发行版、RMW、域号、网卡、容器或虚拟机网络模式和时间同步方式。先用低速小消息证明发布订阅互通，再增加到目标数据量。一次只改变一个因素，否则无法解释是中间件、网络接口还是 QoS 改善了结果。

在真实网络中，发现可能依赖多播或显式服务器，数据传输还受路由、防火墙、MTU 和无线质量影响。不要为排错无限放开所有端口；应从当前实现的配置与观测得到具体需求。检查消息年龄和丢帧比仅看节点能够出现更接近应用实际要求。

#### 记录环境并重启观察工具

代码类型：commands

```bash

printenv ROS_DISTRO RMW_IMPLEMENTATION ROS_DOMAIN_ID
ros2 daemon stop
ros2 doctor --report

```

daemon 停止只影响 CLI 发现缓存；不需要强杀所有 ROS 进程。

### 用明确环境比较 DDS 实现

以 Cyclone DDS 为例，先安装对应 Jazzy RMW 包，再在所有实验终端选择同一实现。一个终端运行 talker，另一个运行 listener。最好使用新的终端，避免此前安全配置、域号和发现参数残留。环境变量只对之后启动的进程生效，不会改变已经运行的节点。

上游 latest 文档可能描述比 Jazzy 系统库更高的版本，网络配置字段需要按安装版本核对。比较时固定消息大小、频率、网络和 CPU 负载，报告发现时间、吞吐、延迟分布与恢复行为，不能只凭单次平均频率给某实现下普遍结论。

#### 各实验终端使用相同设置

代码类型：commands

```bash

source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=42
ros2 daemon stop
ros2 run demo_nodes_cpp talker

```

另一个同样设置的终端运行 demo_nodes_cpp listener。需预先安装 ros-jazzy-rmw-cyclonedds-cpp。

### Zenoh 需要理解路由器和默认发现

Jazzy 的 rmw_zenoh 默认配置与常见 DDS 多播发现不同，节点通常借助路由器获得发现信息。没有路由器时直接运行两个普通 demo，可能看起来像 ROS 发布订阅坏了，实际是部署前提缺失。跨主机时还需要按选定版本显式配置路由器连接，不应假定默认配置已经跨所有网卡开放。

实验先限制在单机：运行路由器，再让 talker 和 listener 使用 rmw_zenoh_cpp，确认图和数据都成立。之后再增加第二台主机并记录连接配置。切换实现前停掉旧 demo 和 daemon，避免不同通信图混在一次观察里。本章命令未实际运行。

#### 终端一启动路由器

代码类型：commands

```bash

ros2 run rmw_zenoh_cpp rmw_zenohd

```

需要 ros-jazzy-rmw-zenoh-cpp。

#### 其他终端运行应用

代码类型：commands

```bash

export RMW_IMPLEMENTATION=rmw_zenoh_cpp
ros2 daemon stop
ros2 run demo_nodes_cpp talker

```

另一个相同环境运行 listener；跨主机另需路由器连接配置。

### 域号不是身份，命名空间不是权限

ROS_DOMAIN_ID 用于逻辑分组，命名空间用于资源组织，二者都不证明发送者是谁。SROS2 提供创建密钥库、身份和 enclave 的工具，底层安全能力还取决于 RMW 与构建支持。安全设计需要明确谁可以发布哪些话题、调用哪些服务，而不是只把话题名改得难猜。

下面先建立两个测试 enclave。它验证身份材料的生成与强制启用流程，不代表已经完成最小权限策略。默认生成的权限可能较宽，真实项目还要按通信合同制定和验证策略。私钥只保存在授权环境，不能随教材、日志或源码仓库一起发布。

#### 在新的练习目录创建测试身份

代码类型：commands

```bash

ros2 security create_keystore learning_keystore
ros2 security create_enclave learning_keystore /learning/talker
ros2 security create_enclave learning_keystore /learning/listener

```

这些命令创建本地测试文件；目录应是新的教学目录。

#### 各安全实验终端选择同一密钥库

代码类型：commands

```bash

export ROS_SECURITY_KEYSTORE="$(pwd)/learning_keystore"
export ROS_SECURITY_ENABLE=true
export ROS_SECURITY_STRATEGY=Enforce
ros2 run demo_nodes_cpp talker --ros-args --enclave /learning/talker

```

另一个终端配置同一路径后，用 /learning/listener 启动 listener。使用支持所需安全能力的相同 RMW。

### 正向成功与反向拒绝都要验证

一个安全实验不能只证明合法节点可通信，还应证明缺失身份、错误身份或未授权端点被拒绝。先在隔离教学环境中使用不存在的 enclave 检查 Enforce 是否阻止启动或通信，再为具体话题制定最小权限并测试允许与拒绝。拒绝日志应能区分身份材料缺失和授权不匹配。

加密和授权也不能替代应用的数据校验。合法节点可能发送超范围速度、过旧时间戳或错误 frame，接收端仍需执行接口合同检查。浏览器桥和远程控制界面同样需要认证、授权和连接范围，不能因为机器人网络在局域网就默认所有访问都可信。

### 形成可复现的网络与权限验收

验收记录至少包含软件版本、环境变量、发现配置、网络拓扑、消息大小与频率、延迟分位数、丢帧和断线恢复时间。安全部分记录策略版本和测试主体，不记录私钥内容。若中间件切换使发现改善但数据延迟变差，应如实解释取舍。

故障顺序建议从主机网络、进程环境、发现、类型、QoS、时间和应用逐层排除。避免在不知道根因时同时更换 RMW、关闭安全、扩大队列并改用最新代码。一次受控实验得到的可解释证据，比偶然恢复通信更适合作为后续部署基础。

### 换了 RMW 后节点列表仍异常

talker 与 listener 正常收发，但 CLI 的节点列表不符合预期。

1. 记录应用和 CLI 的 RMW 环境。

2. 发现旧 daemon 在更换实现之前启动。

3. 停止 daemon，并在相同环境重新运行观察命令。

4. 确认数据通路与观察通路的实现一致。

验收：修复观察环境残留，而非误改正在正常工作的应用。

### 深入练习 1

域号相同意味着对端可信么？

参考答案：不意味着，域号只是逻辑分组，身份和授权需要独立机制。

### 深入练习 2

环境变量会改变已经运行的节点吗？

参考答案：不会，通常只影响之后启动的进程，需要明确重启相关实验进程。

### 深入练习 3

合法节点收到授权后还需要校验速度范围吗？

参考答案：需要。授权解决谁可通信，应用合同解决数据是否有效、及时和在允许范围内。

### 基础验证流程

#### 记录两端通信环境

先核对发行版、RMW、domain、网络接口和系统时间，再查看 QoS；每次实验只改一层。

```bash

printenv ROS_DISTRO RMW_IMPLEMENTATION ROS_DOMAIN_ID

```

#### 在独立终端比较 RMW

安装目标 RMW 后停止旧 daemon，再在所有参与进程中选择一致的实现。不要强杀所有 ROS 进程。

```bash

ros2 daemon stop
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

```

#### 测试 Zenoh 路由器方案

已安装 Jazzy rmw_zenoh_cpp 后，在终端一运行路由器；终端二、三设置 RMW_IMPLEMENTATION=rmw_zenoh_cpp 后分别运行 demo talker/listener。

```bash

ros2 run rmw_zenoh_cpp rmw_zenohd

```

#### 学习安全身份配置

在临时练习目录建立独立密钥库与 enclave，按 SROS2 Jazzy 教程配置启用和强制策略；不要提交私钥。

```bash

ros2 security create_keystore demo_keystore
ros2 security create_enclave demo_keystore /learning/talker

```

### 预期结果

- 同一套发布订阅能在选定通信实现下稳定互通，错误能定位到具体层。

- 启用安全后，允许和拒绝的通信都能用明确测试观察。

### 常见问题

- RMW 改变后旧 daemon 可能仍使用原实现，先停止并重启观察工具。

- 不同机器域号相同不保证网络可发现，路由、防火墙和容器网络仍会影响通信。

- 不要把命名空间、域号或未加密 WebSocket 当作访问控制。

### 练习

为双机传感器传输制作检查表：发现、吞吐、延迟、断线恢复和权限拒绝各设计一个实验，并保存版本及配置。

#### 参考答案

先用小消息证明发现和互通，再测目标数据量下的吞吐/P95 延迟与丢帧；断开链路后测恢复时间。保留 domain、RMW、网络接口与版本。

权限测试应同时证明允许的通信成功、未授权的通信被拒绝。仅设置不同 ROS_DOMAIN_ID 或隐藏话题不能替代身份与授权测试。

### 依据

- [Fast DDS 维护者文档](https://fast-dds.docs.eprosima.com/en/latest/)

- [Cyclone DDS 维护者文档](https://cyclonedds.io/docs/cyclonedds/latest/)

- [rmw_zenoh Jazzy](https://github.com/ros2/rmw_zenoh/tree/jazzy)

- [SROS2 Jazzy](https://github.com/ros2/sros2/tree/jazzy)

- [rosbridge_suite ROS 2](https://github.com/RobotWebTools/rosbridge_suite/tree/ros2)

## 40. GPU 感知与 AI 仿真：Isaac ROS、Isaac Sim 的接入边界

GPU 加速和高保真仿真能扩展感知与数据能力，但应放在稳定的数据契约之上。先完成普通 ROS 输入输出，再核对供应商平台矩阵，最后引入容器、推理和仿真桥。

### 学习目标

- 区分 Isaac ROS 软件管线与 Isaac Sim 仿真器

- 核对 GPU/驱动/容器/ROS 的兼容关系

- 用端到端指标评价加速收益

### 先修

图像与点云管线；ROS 时间和 TF；Linux 容器基础

### 概念

Isaac ROS 侧重加速感知与机器人软件包，Isaac Sim 侧重仿真、传感器和场景，两者可以结合但不是同一个产品。

GPU 算子耗时降低不代表端到端响应更快；拷贝、队列、同步和序列化可能成为新瓶颈。

仿真中的相机帧率、时钟与物理步长会改变数据分布，训练或测试时应记录这些设置。

### 先区分加速管线与高保真模拟器

Isaac ROS 提供以 GPU 加速感知和机器人计算为重点的软件组件，Isaac Sim 提供物理、场景、传感器和 ROS 桥接等仿真能力。它们可以结合，但不是同一个程序，也不要求所有 ROS 学习都从 GPU 开始。普通 ROS 数据管线建立稳定后，再引入加速更容易解释收益与失败。

供应商产品以自己的版本矩阵发布，支持的 GPU、驱动、JetPack、操作系统、容器和 ROS 版本会变化。不能因为电脑有 CUDA 就认定所有组件兼容，也不能把 latest 文档视为 Jazzy 的固定契约。项目应记录确切镜像或软件版本，把环境本身作为实验条件。

### 定义算法替换前后必须相同的合同

比较普通和加速实现时，保持输入消息类型、编码、尺寸、时间戳、frame 和输出语义一致。图像去畸变输出的内参应对应新图像，检测输出的类别和坐标含义应可比较，深度结果单位不能因为后端变化而改变。否则看到的差异可能来自不同问题定义而非实现性能。

某些优化通过共享 GPU 内存或特殊传输减少复制，这会改变节点组合、内存生命周期和调试方式。它仍需要在与普通 ROS 模块交界处提供明确数据契约。使用加速传输不意味着消息天然无延迟，队列、同步和设备调度仍可能决定端到端表现。

### 用离线时间模型看清瓶颈

端到端响应包含采样等待、传输、排队、复制、计算和输出发布。GPU 核函数更快，但如果新增两次大图复制和批处理等待，总延迟可能反而更高。吞吐量表示单位时间处理多少帧，延迟表示某一帧多久到达结果，这两个指标不能互相替代。

下面程序使用人工给定的时间分量，展示为什么只报告计算时间会得出错误结论。它不是硬件 benchmark，也没有推断任何具体 GPU 的性能。真正实验应从同一时钟域或可靠时间同步中测量各阶段，记录中位数和高分位，而不是只记录最好的一帧。

#### latency_model.py：完整离线分析实验

代码类型：complete

```python

def percentile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight

cpu_ms = [2 + 12 + x for x in [1, 2, 1, 3, 2]]
gpu_ms = [4 + 3 + 4 + x for x in [1, 2, 8, 12, 20]]
for name, samples in [("cpu", cpu_ms), ("gpu", gpu_ms)]:
    print(name, "median", percentile(samples, 0.5), "p95", percentile(samples, 0.95))

```

数值是教学假设；程序未在本次执行。GPU 计算项更小，但排队波动会增加尾部延迟。

### 建立可以复现的输入基线

先用普通 ROS 相机或已知 bag 固定输入，记录分辨率、帧率、编码、标定和场景。把基线算法输出保存下来，定义可比较的误差指标，例如像素差、检测精确率或深度误差。没有质量约束时，用更低分辨率、更小模型获得的速度提升不能直接称为同一算法的加速。

运行前记录 CPU、内存、GPU、驱动和电源模式。Jetson 等平台的散热和功耗模式会改变频率，长时间负载可能与刚启动时不同。测试应包含预热和稳定运行区间，并说明初始化模型加载是否计入响应时间。对于实际机器人，启动时间和失败恢复也可能是关键指标。

#### ROS 数据基线检查

代码类型：commands

```bash

ros2 topic info /camera/image_raw --verbose
ros2 topic hz /camera/image_raw
ros2 topic bw /camera/image_raw
ros2 bag record -s mcap -o perception_baseline /camera/image_raw /camera/camera_info /tf /tf_static

```

替换为实际存在的话题；录制与观察可能增加负载，需记录其影响。

### 让模拟器桥接满足相同时间与坐标约定

Isaac Sim 中的相机、关节和机器人状态通过 ROS 2 bridge 接入应用。桥接后的消息仍需正确 frame、采样时间、编码和频率。模拟器的世界坐标约定与 ROS 机器人约定可能存在转换，导入 URDF 后也要检查关节轴与单位，而不是只看模型尺寸似乎正常。

选择模拟时钟后，下游节点统一使用 use_sim_time，且只有一个 /clock 来源。传感器更新率、物理步长和渲染帧率并非必然相同，快放仿真可能让处理节点积压。先用一个传感器和一个简单消费节点验证，再增加神经网络、多个机器人或复杂场景。

### 把模拟数据与真实数据差异列为实验因素

高保真画面不保证传感器统计与真实设备一致。镜头畸变、曝光、噪声、滚动快门、深度无效值和时间偏差都可能影响算法。用于训练或评估时，应记录场景、光照、材质、随机种子和传感器设置，并使用独立真实数据检查迁移差异。

域随机化是一种改变训练条件的方法，不会自动证明覆盖了真实环境。若算法在模拟中成功、实机失败，先比较输入合同和数据分布，再判断是否需要模型调整。切换到更复杂模拟器不能替代对真实错误的测量。

### 交付一份有边界的性能结论

报告应同时给出吞吐、端到端中位和高分位延迟、资源占用、输出质量、启动时间与版本组合。说明输入数据、测试时长和失效条件，避免把某台设备上的单次结果推广成所有 ROS 系统的普遍结论。若加速只改善吞吐而未改善控制响应，也应如实标明。

排错时，导入错误查环境与二进制依赖，节点无数据查传输和 QoS，延迟增长查队列与复制，结果偏差查编码、标定和模型输入，运行一段时间后变慢查温度与资源泄漏。前沿组件仍应遵守这些基础系统方法。本章没有安装供应商环境或声称完成真实 GPU 性能测试。

### GPU 算子更快但机器人响应更慢

推理从十二毫秒降为三毫秒，但输出偶尔晚到数十毫秒。

1. 分开记录复制、排队、推理和发布耗时。

2. 发现批处理等待和输出复制形成长尾。

3. 在质量和吞吐约束下调整批量与传输边界。

4. 使用相同 bag 重测端到端高分位延迟。

验收：以机器人需要的响应指标判断收益，而非只比较单个算子的耗时。

### 深入练习 1

吞吐高是否一定延迟低？

参考答案：不一定，批处理可提高吞吐却增加单帧等待，必须分别测量。

### 深入练习 2

模拟器画面逼真是否证明实机效果？

参考答案：不证明，真实传感器分布、标定、时间和噪声可能不同，需要独立验证。

### 深入练习 3

如何公平比较普通与加速实现？

参考答案：固定输入数据、质量要求、分辨率、算法参数和环境，测量完整链路并报告版本和资源条件。

### 基础验证流程

#### 从计算平台矩阵开始

记录目标硬件、驱动、JetPack 或 x86 系统、容器镜像与 ROS 发行版。只使用维护者声明支持的组合。

#### 先验证普通 ROS 数据链

通过 bag 或真实传感器建立输入基线，记录帧率、带宽、端到端延迟和输出质量。

```bash

ros2 topic hz /camera/image_raw
ros2 topic bw /camera/image_raw

```

#### 在仿真桥两侧检查同一个消息

Isaac Sim 启用 ROS 2 bridge 后，核对图像编码、TF、/clock 与 use_sim_time。官方当前文档推荐 Humble/Jazzy，但具体版本仍需固定。

#### 再替换为加速组件

保持输入数据集不变，用相同任务指标比较 CPU/GPU 方案，明确启动耗时、显存、吞吐与延迟之间的取舍。

### 预期结果

- 能记录并复现完整软硬件版本组合。

- 加速方案的收益由同一数据集上的端到端测量支持。

### 常见问题

- 供应商 latest 文档会变化，不应把当日教程当作长期兼容保证。

- 显卡可用不等于驱动、容器或特定 Isaac 包兼容。

- 在模拟器中表现良好不能直接证明真实传感器分布和硬件时序正确。

### 练习

选择图像去畸变或深度处理任务，写一份普通 ROS 与加速实现的对照实验，至少报告吞吐、P95 延迟、资源占用与输出差异。

#### 参考答案

固定输入 bag、图像尺寸、算法参数和输出质量标准，分别测 CPU/GPU 路径的吞吐、端到端 P95 延迟、CPU、内存、GPU/显存及启动耗时。

若 GPU 算子更快但端到端延迟更高，应查数据复制、批处理等待和队列。报告具体兼容矩阵与不支持的环境，避免泛化为所有设备都更快。

### 依据

- [NVIDIA Isaac ROS](https://nvidia-isaac-ros.github.io/)

- [Isaac ROS 计算平台配置](https://nvidia-isaac-ros.github.io/getting_started/compute/index.html)

- [Isaac Sim ROS 2 教程](https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/index.html)

- [image_pipeline Jazzy 源码](https://github.com/ros-perception/image_pipeline/tree/jazzy)

## 41. 强化学习与 Sim2Real：从策略实验到 ROS 2 接口

把强化学习拆成环境、策略、训练和部署四部分，先用可解释的参数搜索理解闭环，再讨论如何把训练结果接到机器人。

### 学习目标

- 定义观测、动作、奖励和回合边界

- 区分训练循环与 ROS 2 在线控制循环

- 建立仿真到实机的接口检查与评估步骤

### 先修

已理解 ROS 2 话题、Action、时间戳与日志；Python 3；本章离线实验仅依赖标准库

### 概念

把强化学习拆成环境、策略、训练和部署四部分，先用可解释的参数搜索理解闭环，再讨论如何把训练结果接到机器人。

### 把机器人任务写成可检查的接口

设想一台小车停在目标位置。环境保存位置与速度，策略读取观测并选择加速度或速度目标，环境推进一段时间后返回新观测和奖励。这里最容易遗漏的是动作的物理意义：同样的数值 0.5 可以表示米每秒、弧度、归一化电流或者无量纲网络输出。先把单位、维度、排列顺序和采样周期写进接口表，再选择学习算法。

观测应是部署时能获得的量。仿真器能直接提供真实速度和接触力，并不代表实机有相同传感器。若训练使用了实机没有的量，要设计估计器，或把它仅用于训练时的辅助信息。部署可见的策略输入与训练时帮助优化的额外信息应分别列出，否则仿真成功也无法构造在线输入。

### 奖励、终止与时间截断分别表达什么

本章的原创实验用位置误差平方惩罚偏离目标，同时用控制量平方限制过大动作。奖励是优化目标的一种表达，既不是安全证明，也不保证学到人期待的行为。观察每个奖励分量与实际轨迹，比只看总回报更容易发现漏洞。例如只奖励前进距离时，机器人可能忽略姿态和停止要求。

Gymnasium 的 step 接口返回下一观测、奖励、terminated、truncated 和 info。任务成功或失败可构成终止，外部时间上限可构成截断；两者都需要重置回合，但价值估计处理并不总相同。reset 返回观测与附加信息。旧教程的单一 done 标志不能机械替换训练目标中的终止掩码。这个区别影响算法更新，不只是变量命名。

### 完整实验：对一个小策略做参数搜索

下面文件从零实现一维质点、固定时间积分和一个反馈策略。它不依赖学习框架；训练在这里指比较候选增益，并选择训练种子上的平均回报最高者。用这一小实验可以完整观察环境、候选策略、训练集和留出评估之间的数据流，随后再把搜索器换成适合任务的强化学习算法。

position 是相对目标的误差，velocity 是速度，force 被限幅到正负一。每轮动作先更新速度，再更新位置；改变质量会改变相同动作下的响应。脚本先用五个初始状态选择增益，再用十个不同种子、三种质量评估。输出同时保留回报和最终误差，避免仅看一个指标作判断。

#### rl_gain_search.py

代码类型：complete

```python

"""A tiny policy-search experiment; standard library only, no robot connection."""
import json
import random

def rollout(gain, seed, mass=1.0, steps=120):
    rng = random.Random(seed)
    position, velocity = rng.uniform(-2.0, 2.0), 0.0
    reward = 0.0
    for _ in range(steps):
        force = max(-1.0, min(1.0, -gain * position - 0.8 * velocity))
        velocity += (force / mass - 0.1 * velocity) * 0.05
        position += velocity * 0.05
        reward -= position ** 2 + 0.01 * force ** 2
    return reward, abs(position)

def evaluate(gain, seeds, mass=1.0):
    results = [rollout(gain, seed, mass) for seed in seeds]
    return {"gain": gain, "mass": mass,
            "mean_return": sum(x[0] for x in results) / len(results),
            "mean_final_error": sum(x[1] for x in results) / len(results)}

def main():
    candidates = [evaluate(g, range(5)) for g in (0.0, 0.25, 0.5, 1.0, 2.0)]
    best = max(candidates, key=lambda item: item["mean_return"])["gain"]
    print(json.dumps({"training": candidates, "selected_gain": best,
                      "held_out": [evaluate(best, range(100, 110), mass)
                                   for mass in (0.7, 1.0, 1.5)]}, indent=2))

if __name__ == "__main__":
    main()


```

完整、可运行的原创参数搜索实验。不是 PPO、SAC 或 Isaac Lab 的实现，也不代表任何机器人性能结果。

### 将策略装进 ROS 2 节点之前先固定时序

实际部署可拆成观测收集、模型推理、输出适配三个节点或组件。观测收集检查时间戳并按训练顺序拼接数据；推理输出原始动作；适配层执行反归一化、限幅和接口转换。关节命令可进入合适的 ros2_control 控制器，移动速度可进入底盘命令入口。接口选择取决于任务的控制量，不能仅因为某个话题名字熟悉就直接连接。

训练环境的 step 常常同步推进仿真，ROS 2 回调却由数据到达驱动。定时推理时必须说明取最近一帧还是一组同步观测，以及数据超过多久视为过期。慢推理线程不能无限堆积历史请求，否则控制输出虽然不断产生，实际对应的却是几秒前的世界。记录观测时间、推理起止和命令时间，才能分辨感知延迟和模型延迟。

### 从仿真到真实环境需要验证哪些差异

先在相同仿真中重放导出的策略，再换一个物理配置验证鲁棒性，最后才进入受约束的硬件测试。质量、摩擦、延迟、噪声、执行器响应与相机外观都可能形成差异。域随机化的作用是覆盖合理变化范围；范围必须有测量依据，盲目扩大所有噪声可能让训练任务失去意义。

Isaac Lab 提供机器人学习环境与训练工作流，但其版本、仿真后端和导出接口独立演进。将项目使用的版本和模型文件摘要与 ROS 2 工作空间一起记录。不要把网页 main 分支的新示例直接套进旧安装环境。离线教材能完整解释连接方法；大型仿真器、模型权重和训练数据仍需要单独准备，不能由一份 HTML 替代。

### 建立可重复的评估与故障实验

固定测试场景集，分别统计成功率、碰撞或越界事件、到达时间、控制变化和推理延迟。把训练时见过的场景与未见过的场景分开，保留失败轨迹。小样本中的一次成功只能说明这一回合完成，不能推断泛化能力。先比较简单反馈策略，才能判断新模型究竟改善了什么。

故障实验可以从断开一类观测、加入延迟、交换关节顺序开始，在纯仿真或离线回放中验证拒绝与恢复逻辑。系统应能指出输入违反了哪条合同，并停止接纳过期策略输出。把模型的平均效果和控制系统的失效处理分别验收，二者不能互相代替。

### 独立训练种子与评估种子

比较反馈增益在不同质量下的表现，理解训练成绩与泛化评估的差别。

1. 运行完整脚本，保存 selected_gain 与三组 held_out 指标。

2. 把候选增益限制为 0，比较平均回报和最终误差。

3. 保持训练种子不变，将质量改为 0.3 与 3.0；记录是否仍能接近目标。

4. 写出若将 force 换成 TwistStamped 速度命令，需要改变哪些模型、单位和接口。

验收：得到可复查的数值表，并明确这个实验只验证一维模型中的策略搜索流程。

### 深入练习 1

为什么不能把仿真器提供的所有状态直接作为部署观测？

参考答案：部署时必须能通过传感器或估计器构造同样的输入。无法获取的真实状态会造成训练与部署接口不一致。

### 深入练习 2

回报提高而最终位置误差变大可能意味着什么？

参考答案：总奖励含有多个时间步和多个分量。策略可能更快减少早期误差，却在结束时仍有偏差；应检查轨迹、奖励分量和任务验收指标。

### 深入练习 3

ROS 2 推理变慢时，增加队列长度能解决吗？

参考答案：通常只会保留更多过期观测。需要设定数据新鲜度、丢弃过期请求、测量耗时，并调整模型或频率；控制层另有超时处理。

### 基础验证流程

#### 运行本章完整离线实验

在随教材提供的 examples 目录执行。程序不连接机器人，也不调用云端服务。

```bash

python3 offline_labs/rl_gain_search.py

```

### 预期结果

- 输出五个候选策略、选定增益和三组留出评估。

- 所有计算在本地完成，不创建 ROS 节点。

### 常见问题

- 把算法演示的成功当成真实机器人已通过验收。

- 训练与部署的单位、时间、关节顺序或归一化不一致。

### 练习

写出本章模块的输入、输出、时间约束，以及失败时系统如何恢复。

#### 参考答案

输入应包含明确类型、单位、参考系、时间戳与版本；输出应有范围和有效期。超时、无效数值与未知任务必须形成可观察的失败状态，交给已经验证的控制或任务层处理；不能继续沿用过期输出。用一次正常输入和一次故障注入证明这条链路。

### 依据

- [Gymnasium 环境 API](https://gymnasium.farama.org/api/env/)

- [Isaac Lab 官方文档](https://isaac-sim.github.io/IsaacLab/main/index.html)

## 42. 语言模型与具身任务：结构化计划、技能与反馈

把自然语言转换成可以验证、执行和取消的任务计划。使用明确的技能合同连接 Nav2、MoveIt 与感知模块。

### 学习目标

- 设计模型输出与机器人技能之间的边界

- 验证任务参数并管理异步执行状态

- 以失败场景评价任务规划系统

### 先修

已理解 ROS 2 话题、Action、时间戳与日志；Python 3；本章离线实验仅依赖标准库

### 概念

把自然语言转换成可以验证、执行和取消的任务计划。使用明确的技能合同连接 Nav2、MoveIt 与感知模块。

### 自然语言、世界状态和动作技能各负责什么

一句“去桌旁看看杯子”隐含了地点、物体、观察方法和结束条件。语言模型可以协助分解任务，但系统仍需要真实地图中的地点、来自感知的物体观测和可执行的机器人技能。把这三层混在同一段提示词中，往往很难判断失败发生在理解、定位还是执行。

先定义一个小世界：只有 desk 和 dock 两个地点，只有 navigate 与 inspect 两个技能。模型的职责是选择技能和参数；地点对应的地图坐标由应用配置提供。机器人姿态、物体置信度和观测时间属于运行状态，应随着执行更新，不能把几分钟前的文字描述当成当前环境。

### 两种写法：生成程序与生成结构化任务

Code as Policies 研究了将语言指令组织为调用机器人接口的程序；RAI 提供将模型工具与 ROS 2 集成的框架。它们展示了不同的系统组织方式。学习时应区分研究方法与自己机器人上已经验证的能力，不能根据演示视频推断任何型号都能直接使用。

本章采用结构化任务列表作为教学入口。相比自由程序，有限技能名和参数字段更容易定义完整的验收规则，也便于记录和回放。需要复杂条件时，可以把任务编译到状态机或行为树，由已有执行器处理重试与取消。这里的选择是本教材的工程设计示例，并不是声称所有任务都应使用同一种表示。

### 完整实验：对计划做结构与语义检查

完整脚本验证步骤数量、技能名称、字段集合、地点和超时。它有意只打印 DRY_RUN，没有连接 ROS 2。先验证一个正常计划，再输入未知技能与不存在的地点，观察 REJECTED。这样可以在没有模型账号、网络或机器人的情况下理解“候选计划”到“允许执行的计划”的转换。

JSON 能解析只说明语法正确，不能说明地点存在或技能可用。检查时还要拒绝额外字段、非有限数值和超出预算的时间。对实际项目，应把合同扩展为任务类型定义与参数校验函数，并让每个版本的技能库声明自己支持哪些合同。错误信息应保留字段与原因，方便定位生成或配置问题。

#### plan_contract.py

代码类型：complete

```python

"""Validate a task proposal and print a dry-run; never executes ROS commands."""
import json
import math

PLACES = {"desk": (1.0, 0.5, 0.0), "dock": (0.0, 0.0, 0.0)}

def validate(raw):
    plan = json.loads(raw)
    if not isinstance(plan, list) or not 1 <= len(plan) <= 8:
        raise ValueError("plan must contain 1..8 steps")
    for step in plan:
        if not isinstance(step, dict):
            raise ValueError("step must be an object")
        skill = step.get("skill")
        allowed = {"navigate": {"skill", "place", "timeout"},
                   "inspect": {"skill", "object", "timeout"}}
        if not isinstance(skill, str) or skill not in allowed or set(step) != allowed[skill]:
            raise ValueError("unknown skill or unexpected fields")
        timeout = step["timeout"]
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise ValueError("invalid timeout")
        if skill == "navigate" and (not isinstance(step["place"], str) or step["place"] not in PLACES):
            raise ValueError("unknown place")
        if skill == "inspect" and step["object"] not in ("cup", "marker"):
            raise ValueError("unsupported object")
    return plan

def main():
    sample = '[{"skill":"navigate","place":"desk","timeout":60},{"skill":"inspect","object":"cup","timeout":10}]'
    for index, step in enumerate(validate(sample), 1):
        print("DRY_RUN", index, step)
    for bad in ('[{"skill":"shell","command":"anything","timeout":10}]',
                '[{"skill":"navigate","place":"unknown","timeout":60}]'):
        try:
            validate(bad)
        except ValueError as error:
            print("REJECTED", error)
        else:
            raise AssertionError("invalid plan accepted")

if __name__ == "__main__":
    main()


```

完整离线计划校验器；只预览任务，不执行模型生成的代码，不启动机器人。

### 把技能连接到 ROS 2 Action 状态机

navigate 技能可以封装 Nav2 的导航 Action：确认服务器可用，构造带 map 参考系与时间戳的目标，发送后保存 goal handle，订阅反馈并等待最终结果。任务层需要分别处理目标被拒绝、执行失败、超时和取消；发送请求成功并不等于到达目标。inspect 可以是感知请求，也可以是一个需要多步观察的 Action，取决于持续时间和反馈需求。

连续步骤只在前一步达到明确成功条件后推进。例如导航成功后还要确认相机观测是新鲜的，再读取杯子检测结果。失败时可选择重试、回退到观察点或返回需要人工处理的状态；具体策略由任务需求决定。不要让语言模型反复生成同一个无效动作而没有次数上限和状态记录。

### 使用世界模型，避免用聊天历史代替状态

世界模型可以很小：地点表、机器人当前姿态、物体列表、技能可用性和当前任务状态。每条观测包含来源与时间，物体坐标包含参考系。若检测结果在 camera_link，需要在对应观测时间转换到 map 或机器人基座坐标后才能交给运动模块。没有转换证据时，应请求重新观察，而不是填一个看似合理的坐标。

提示词提供任务目标和工具说明，运行状态由程序构建。日志分别保存用户指令、候选计划、校验结果、实际技能调用与结果。这种分离让你能够不重新调用模型就重放执行流程，也能比较同一任务的不同模型输出。日志中不应保存访问令牌；这是部署记录设计的一部分。

### 如何评价完整任务而不仅是生成质量

建立包含正常任务、未知地点、不可见物体、导航失败和取消请求的小测试集。分别统计计划合法率、技能执行成功率、端到端完成率以及恢复所用时间。生成文字流畅不代表计划有用，计划合法也不代表环境允许执行。把每一层的失败分开，才能知道应该改提示、感知还是控制。

离线阶段可用固定 JSON 计划和模拟 Action 结果完成所有状态转换测试；再接入真实模型时，只替换候选计划来源。最后才把经过验证的技能适配到仿真或硬件。对于云端模型，还需处理网络中断和调用超时，使任务层保持有界等待；已运行的控制循环不应依赖持续联网聊天。

### 桌旁观察任务的离线验收

让系统把“到桌旁观察杯子”转换成两步任务，并证明未知动作不会进入执行阶段。

1. 运行校验器，确认两条 DRY_RUN 和两条 REJECTED。

2. 将 desk 改为 dock，观察目标仅来自地点白名单。

3. 将 timeout 改为负数，确认校验失败。

4. 纸面模拟 Nav2 返回 ABORTED，写出第二步是否执行及最终任务状态。

验收：掌握计划合同与执行状态机的边界；无需在线模型就能验证核心流程。

### 深入练习 1

为何不能把“计划合法”作为“任务成功”？

参考答案：合法只说明满足输入合同。服务器可能拒绝，路线可能被阻挡，物体可能不存在，必须观察实际执行结果。

### 深入练习 2

目标地点应该由模型自由生成坐标吗？

参考答案：教学实现从已知地点表解析坐标。若允许自由坐标，仍需验证参考系、范围、可达性和观测依据，并由运动规划模块检查。

### 深入练习 3

任务取消后应该只停止生成下一条计划吗？

参考答案：还需取消已发送的活动 goal，等待取消响应和终态，并执行该技能定义的停止或恢复流程。只停止规划不会自动停止当前动作。

### 基础验证流程

#### 运行本章完整离线实验

在随教材提供的 examples 目录执行。程序不连接机器人，也不调用云端服务。

```bash

python3 offline_labs/plan_contract.py

```

### 预期结果

- 正常任务输出 DRY_RUN；未知技能与地点输出 REJECTED。

- 程序结束后没有 ROS 节点或后台任务。

### 常见问题

- 把算法演示的成功当成真实机器人已通过验收。

- 训练与部署的单位、时间、关节顺序或归一化不一致。

### 练习

写出本章模块的输入、输出、时间约束，以及失败时系统如何恢复。

#### 参考答案

输入应包含明确类型、单位、参考系、时间戳与版本；输出应有范围和有效期。超时、无效数值与未知任务必须形成可观察的失败状态，交给已经验证的控制或任务层处理；不能继续沿用过期输出。用一次正常输入和一次故障注入证明这条链路。

### 依据

- [RAI 维护者仓库](https://github.com/RobotecAI/rai)

- [Code as Policies 作者项目页](https://code-as-policies.github.io/)

## 43. 模仿学习与神经策略：数据、动作块与部署适配

沿着示范数据、训练样本、动作预测与控制执行理解模仿学习，比较逐步回归、ACT 与 Diffusion Policy 的输出方式。

### 学习目标

- 把机器人示范转换成带版本的数据合同

- 理解动作块、预测窗口与执行窗口

- 验证神经策略输出进入控制器前的必要条件

### 先修

已理解 ROS 2 话题、Action、时间戳与日志；Python 3；本章离线实验仅依赖标准库

### 概念

沿着示范数据、训练样本、动作预测与控制执行理解模仿学习，比较逐步回归、ACT 与 Diffusion Policy 的输出方式。

### 先定义示范到底记录了什么

模仿学习从示范中学习观测到动作的映射。记录相机画面和关节值并不足以自动形成训练数据：还需要明确关节值是测得状态还是下发目标，以及动作在画面采集前后哪个时刻生效。一个示范回合应保存时间戳、关节顺序、单位、控制模式、相机标定和任务结果。

数据处理先对齐时钟，再按选定频率采样。异步传感器可使用近邻或插值，但必须记录容许的时间误差。关节角通常可以在合理条件下插值，离散抓手开关不能随意平均成半个动作。保留原始记录和转换配置，避免之后只能得到一份无法追溯的训练数组。

### 三种策略写法的联系与区别

简单行为克隆可以把当前观测映射成下一步动作，用监督误差拟合示范。它易于建立基线，但部署时小误差可能把系统带到训练数据很少覆盖的状态。增加更多同类静态画面并不一定解决这个问题；包含恢复过程的示范和针对失败场景的数据更有解释力。

ACT 使用动作分块，预测一段未来动作；Diffusion Policy 使用条件去噪过程生成动作序列，并采用滚动执行思路。理解二者时先比较输入历史长度、预测长度、实际执行长度和重新规划频率。这些长度影响延迟与反馈响应，不能仅按论文中的网络名称选择控制周期。算法细节和训练依赖仍需固定对应实现版本。

### 归一化、数据划分与坐标合同

训练集计算出的均值和尺度是模型的一部分，应随权重一起保存。推理阶段使用同一组统计量，输出反归一化后才具有物理单位。绝对关节角、关节角增量和末端位姿增量不是同一种动作表示；同维度数组也可能表达完全不同的控制意图。部署前写出每个维度的名称和含义。

训练与验证应按回合、场景或采集批次划分，避免相邻帧分别进入两边造成成绩虚高。视觉任务还应检查同一背景、同一物体实例是否跨越划分边界。测试集用于最后的固定评估，不应在每次观察失败后继续调参并仍称其为未见数据。教材的小实验不训练网络，而是验证预测结果进入控制系统时的合同。

### 完整实验：预测动作的时间与数值门控

下面文件约定六个关节位置目标，单位为弧度，并检查维度、有限数值、数据年龄和每步最大变化。脚本演示接受新鲜输出、拒绝过期输出和拒绝 NaN。它的作用是把接口假设变成可运行的规则；正负一的关节范围仅用于数学示例，实际机器人必须从自身模型和控制需求确定。

返回 None 表示这次预测不能使用。调用方应进入已经设计并验证的保持、停止或其他恢复模式；对于不同控制器，这些行为并不相同。把关节位置命令全部写成零可能造成大幅运动，因此不能将零数组作为通用停止方案。限幅本身也不是碰撞检查，仍需要规划场景与控制层约束。

#### policy_gate.py

代码类型：complete

```python

"""Demonstrate timestamp/dimension/finite/rate checks for a six-joint policy."""
import math

def gate(candidate, previous, age_seconds, dt, limit=0.5):
    # These are position targets in radians, not torques or velocities.
    if len(candidate) != 6 or len(previous) != 6:
        raise ValueError("expected six joints in the agreed order")
    if not all(math.isfinite(x) for x in (*candidate, *previous, age_seconds, dt, limit)):
        raise ValueError("non-finite input")
    if dt <= 0 or limit <= 0:
        raise ValueError("invalid control interval or rate limit")
    if age_seconds < 0 or age_seconds > 0.1:
        return None  # Caller must select its independently verified stop/hold mode.
    output = []
    for target, last in zip(candidate, previous):
        bounded = max(-1.0, min(1.0, target))
        output.append(last + max(-limit * dt, min(limit * dt, bounded - last)))
    return output

def main():
    print("ACCEPTED", gate([0.5] * 6, [0.0] * 6, 0.02, 0.02))
    print("STALE", gate([0.5] * 6, [0.0] * 6, 0.3, 0.02))
    try:
        gate([float("nan")] * 6, [0.0] * 6, 0.02, 0.02)
    except ValueError as error:
        print("REJECTED", error)

if __name__ == "__main__":
    main()


```

完整标准库实验。以六关节位置目标演示合同检查；不是机器人控制器，也不是安全认证组件。

### 动作块如何接入在线执行

假设模型预测二十步未来动作，只执行前四步后重新观测，可以减少一次预测误差累积过长的问题。推理线程与控制线程之间用明确的序列号和时间戳交换动作块。新块到达时，应说明替换剩余动作还是平滑衔接；旧块用完而新块未到时，应进入定义好的超时行为。

对 ROS 2，可将已验证的关节轨迹交给合适的轨迹控制器，或者由专用适配节点按约定频率产生目标。控制器所需的关节名、轨迹时间和当前状态必须一致。推理节点的平均耗时还不够，要统计尾部延迟与连续超时；多摄像头预处理、GPU同步和日志写入都可能影响这条链路。

### 从离线误差走向任务验收

离线损失用于发现拟合问题，任务验收还需检查成功率、恢复能力、动作平滑度和耗时。先用录包回放验证输入处理和模型输出，再在仿真中验证闭环，最后逐步接入硬件。每一步保存模型摘要、归一化统计、控制频率和测试场景，才能解释不同结果来自模型还是部署配置。

当同一场景存在多种合理动作时，简单平均可能生成无效的中间动作。这解释了学习动作分布的动机，但生成式模型同样可能产生无效输出。不要省略接口校验和反馈执行。针对失败回合，先检查示范覆盖、时间对齐和动作定义，再决定是否更换模型结构。

### 验证六关节策略输出合同

在不加载模型和不连接机械臂的情况下，检查三种预测结果的处理。

1. 运行脚本，确认 ACCEPTED 六个值均为 0.01。

2. 确认过期输入得到 STALE None，非有限值被拒绝。

3. 将控制周期改为 0.01，预测每步最大变化后再运行。

4. 为真实机械臂写出六个关节名、实际限位和停用策略，但先不接硬件。

验收：理解策略输出与控制器输入之间还需要时间、数值和语义适配。

### 深入练习 1

为什么离线损失很低但机器人仍可能失败？

参考答案：部署状态可能偏离示范分布，传感器时间或动作含义也可能不一致。还可能存在推理延迟、未覆盖场景和控制执行误差。

### 深入练习 2

预测二十步是否必须全部执行？

参考答案：不必。预测窗口与执行窗口可以不同，滚动观测和重新预测允许只执行前一部分；实际长度应通过闭环评估选择。

### 深入练习 3

为什么训练数据不能简单按相邻帧随机分割？

参考答案：连续帧高度相似，可能把同一示范的信息泄漏到验证集。按回合或场景分割更能评价未见条件下的表现。

### 基础验证流程

#### 运行本章完整离线实验

在随教材提供的 examples 目录执行。程序不连接机器人，也不调用云端服务。

```bash

python3 offline_labs/policy_gate.py

```

### 预期结果

- 新鲜预测被限速为每关节 0.01 弧度的变化。

- 过期或非有限输入不会被当作可用命令。

### 常见问题

- 把算法演示的成功当成真实机器人已通过验收。

- 训练与部署的单位、时间、关节顺序或归一化不一致。

### 练习

写出本章模块的输入、输出、时间约束，以及失败时系统如何恢复。

#### 参考答案

输入应包含明确类型、单位、参考系、时间戳与版本；输出应有范围和有效期。超时、无效数值与未知任务必须形成可观察的失败状态，交给已经验证的控制或任务层处理；不能继续沿用过期输出。用一次正常输入和一次故障注入证明这条链路。

### 依据

- [ACT 作者实现](https://github.com/tonyzhaozh/act)

- [Diffusion Policy 作者项目页](https://diffusion-policy.cs.columbia.edu/)

## 44. 云端与边缘：机器人数据集、模型版本与交付闭环

把录包、标注、训练、评估和部署组织成可追溯的数据流程。边缘设备负责有时限的执行，云端或工作站承担可异步完成的任务。

### 学习目标

- 设计原始数据到模型发布的版本链

- 用离线清单验证数据是否变化

- 建立边缘模型切换、断网与回滚的验收流程

### 先修

已理解 ROS 2 话题、Action、时间戳与日志；Python 3；本章离线实验仅依赖标准库

### 概念

把录包、标注、训练、评估和部署组织成可追溯的数据流程。边缘设备负责有时限的执行，云端或工作站承担可异步完成的任务。

### 按时限划分边缘和远端职责

机器人上的控制循环需要在确定时间内得到结果，数据清洗和模型训练通常可以延后完成。先给每项工作标注延迟预算、带宽需求、离线要求和失败影响，再决定放在哪台机器。云端是可选部署位置，本章实验完全在本地进行；同样的方法也适用于实验室服务器和移动硬盘。

把原始传感器数据持续传到远端不一定必要。可以先在边缘记录完整回合与关键指标，再按任务选择上传数据。网络中断时，正在执行的机器人任务应依照本地策略处理；远端服务不可用不应让控制线程无限等待。模型更新是独立管理流程，不应在每次推理时下载权重。

### 从 rosbag 记录到训练样本的五层关系

第一层保存原始录包与设备信息，第二层保存时间同步和标定参数，第三层保存清洗及标注结果，第四层保存训练划分与转换程序，第五层保存权重、评估和部署配置。每一层指向输入版本。只保留最终权重，无法回答模型为什么在某台机器人上表现不同。

对相机数据，标定分辨率、裁剪和图像编码会影响输入；对关节数据，名称、单位和控制模式会影响动作含义。将这些合同写进数据集元信息，并在转换程序入口验证。新的标定不能悄悄覆盖旧数据的解释，应形成新的转换版本。rosbag 是原始记录容器，不等同于已经清洗好的训练集。

### 完整实验：给数据目录生成确定性清单

下面程序逐个读取文件，计算 SHA-256 摘要，记录相对路径和字节数。相同内容产生相同清单，修改一行后对应摘要变化。它用分块读取避免一次把大文件装进内存；不修改数据目录。实验输出应放到输入目录之外，否则下一次会把上一次生成的清单也纳入输入。

摘要说明字节内容是否一致，不证明数据正确、标签可靠或来源可信。采集设备、场景、许可和标注规范还需要元信息。符号链接在本实验中被拒绝，因为它可能把目录外数据引入版本范围；真实项目应明确选择跟随、固化还是禁止链接，而不是无意中改变数据边界。

#### dataset_manifest.py

代码类型：complete

```python

"""Create a deterministic manifest on stdout. Input data is never modified."""
import hashlib
import json
import sys
from pathlib import Path

def manifest(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("dataset root must be a directory")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symbolic links require an explicit data policy")
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        files.append({"path": path.relative_to(root).as_posix(),
                      "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
    return {"schema": 1, "files": files}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 dataset_manifest.py DATA_DIRECTORY")
    print(json.dumps(manifest(sys.argv[1]), ensure_ascii=False, indent=2))


```

完整只读目录清单工具。输出写到标准输出，由调用者决定保存位置。

### 把数据处理步骤组织成可重跑的流水线

可以先用普通脚本组织 extract、validate、split、train 和 evaluate，每一步声明输入文件、参数和输出。DVC 等工具可进一步跟踪数据依赖与流水线，帮助判断输入变化后哪些步骤需要重跑。工具不能替代语义合同：即使缓存命中，也仍需知道训练划分是否正确、评估是否使用了相同配置。

固定随机种子有助于比较实验，但并不保证所有硬件与并行算子产生逐位相同结果。发布记录应同时保存环境、代码提交、数据清单、参数和指标容许范围。先复现一份小样本流水线，再扩展到大数据，通常更容易区分依赖问题和算法问题。

### 模型发布与 ROS 2 部署配置要一起验收

一个模型发布单元至少包括权重、输入输出定义、归一化统计、依赖版本、评估摘要和启动参数。边缘节点加载时先检查合同，再执行本地预热或固定样本推理，确认维度和数值范围，最后进入可用状态。生命周期节点可以表达配置、激活和停用过程，但切换策略仍需要应用自己定义。

保留一个经过验证的旧版本，更新失败时回到已知状态。切换时应明确处理进行中的任务、旧模型的输出队列和新模型的时间基准。仅替换磁盘上的文件并不能让已加载的进程自动采用新权重；反过来，强行重启进程也不等于完成了任务级交接。

### 用证据闭合采集、训练与部署循环

部署日志应能关联模型版本与具体回合，记录成功、失败、输入异常和延迟。回收失败样本时保留场景上下文，避免只挑选容易成功的数据继续训练。用固定评估集比较新旧版本，并另建新场景集观察泛化；这样才能解释改进是来自模型还是测试条件变化。

最后做三个可观察实验：断网时本地读取仍正常，数据文件变化时清单能发现，模型合同不匹配时启动被拒绝。它们分别覆盖网络、数据和接口边界。把实验结果与发布记录一起保存，使另一位开发者能够从记录重建同样的输入并验证结论。

### 可复查的数据清单

为一个小型模拟数据目录生成清单，证明修改数据会改变摘要。

1. 在临时目录创建 raw 子目录和一份 CSV，使用本章命令生成清单到 raw 之外。

2. 不修改输入再次生成并比较，结果应完全相同。

3. 向 CSV 增加一行，再生成清单，观察 bytes 和 sha256 改变。

4. 把清单、转换参数和模型版本关联到一份发布记录。

验收：得到可复现的数据身份记录，并理解哈希校验与数据质量评价的区别。

### 深入练习 1

为何权重文件不能单独构成可交付模型？

参考答案：还需要输入输出合同、归一化统计、依赖与部署配置，以及可复查的评估。否则无法确定同一权重是否接收了相同含义的数据。

### 深入练习 2

哈希相同是否表示标签一定正确？

参考答案：不表示。哈希比较字节一致性，标签质量、采集条件和任务适用性需要另外检查。

### 深入练习 3

边缘设备断网后应该如何处理远端任务？

参考答案：按照预先定义的超时与恢复流程处理远端请求，并保留本地有时限的控制能力。重连后再同步有版本的数据，避免阻塞控制回调。

### 基础验证流程

#### 运行本章完整离线实验

在随教材提供的 examples 目录执行。程序不连接机器人，也不调用云端服务。

```bash

workdir=$(mktemp -d)
mkdir "$workdir/raw"
printf "t,q\n0,0.1\n" > "$workdir/raw/sample.csv"
python3 offline_labs/dataset_manifest.py "$workdir/raw" > "$workdir/manifest.json"
cat "$workdir/manifest.json"

```

### 预期结果

- 清单包含 sample.csv 的相对路径、长度和 SHA-256。

- 相同输入可生成相同清单；输入目录内容不会被修改。

### 常见问题

- 把算法演示的成功当成真实机器人已通过验收。

- 训练与部署的单位、时间、关节顺序或归一化不一致。

### 练习

写出本章模块的输入、输出、时间约束，以及失败时系统如何恢复。

#### 参考答案

输入应包含明确类型、单位、参考系、时间戳与版本；输出应有范围和有效期。超时、无效数值与未知任务必须形成可观察的失败状态，交给已经验证的控制或任务层处理；不能继续沿用过期输出。用一次正常输入和一次故障注入证明这条链路。

### 依据

- [DVC 数据流水线文档](https://doc.dvc.org/user-guide/pipelines)

## 不同写法对照

### 相同发布行为：rclcpp 与 rclpy

同一 std_msgs/String 话题如何用两种语言发布？

#### C++ / rclcpp

核心片段；需完整节点类、头文件、main、依赖及安装目标

```cpp

// Node 派生类的方法内；publisher_ 为持久成员
publisher_ = create_publisher<std_msgs::msg::String>("telemetry", 10);
std_msgs::msg::String message;
message.data = "robot ready";
publisher_->publish(message);

```

#### Python / rclpy

核心片段；需导入 String、完整节点、main 和 console_scripts

```python

# Node 派生类的方法内；self.publisher 持久保存对象
self.publisher = self.create_publisher(String, "telemetry", 10)
message = String()
message.data = "robot ready"
self.publisher.publish(message)

```

两端接口类型和解析后的话题名必须相同。

10 表示 KeepLast 队列深度，不是 10 Hz。周期发布需另建 timer。

不把语言选择直接等同于实时性保证。

- [C++ 发布者与订阅者](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Publisher-And-Subscriber.html)

- [Python 发布者与订阅者](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html)

### 回调的不同写法：lambda、绑定成员方法、Python 方法

改变回调写法时，通信逻辑是否改变？

#### C++ lambda

类方法内核心片段；subscription_ 需为成员

```cpp

subscription_ = create_subscription<std_msgs::msg::String>(
  "telemetry", 10,
  [this](std_msgs::msg::String::ConstSharedPtr message) {
    RCLCPP_INFO(get_logger(), "%s", message->data.c_str());
  });

```

#### C++ 成员函数

核心片段；需定义 TelemetryNode::on_message 并包含 functional

```cpp

subscription_ = create_subscription<std_msgs::msg::String>(
  "telemetry", 10,
  std::bind(&TelemetryNode::on_message, this, std::placeholders::_1));
// on_message 的签名：
// void on_message(std_msgs::msg::String::ConstSharedPtr message);

```

#### Python 绑定方法

片段；构造函数语句与类方法需放在对应位置

```python

self.subscription = self.create_subscription(
    String, "telemetry", self.on_message, 10)

def on_message(self, message):
    self.get_logger().info(message.data)

```

三种写法都由 executor 调度；不改变 QoS 或数据类型。

C++ 捕获 this 时必须保证对象在回调期间存活。

- [ros2/examples · jazzy](https://github.com/ros2/examples/tree/jazzy)

- [C++ 发布者与订阅者](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Publisher-And-Subscriber.html)

- [Python 发布者与订阅者](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html)

### 服务：C++ Future 与 Python Future

发送请求后如何继续处理其他事件？

#### C++ 异步客户端

核心片段；client_ 已 create_client 且服务可用；节点持续 spin

```cpp

auto request = std::make_shared<example_interfaces::srv::AddTwoInts::Request>();
request->a = 4;
request->b = 8;
client_->async_send_request(request,
  [this](rclcpp::Client<example_interfaces::srv::AddTwoInts>::SharedFuture result) {
    RCLCPP_INFO(get_logger(), "sum=%ld", result.get()->sum);
  });

```

#### Python 异步客户端

核心片段；client 已创建，需导入接口并持续 spin

```python

request = AddTwoInts.Request()
request.a, request.b = 4, 8
future = self.client.call_async(request)
future.add_done_callback(self.on_response)

# 另定义类方法，并为异常/超时添加处理
def on_response(self, future):
    self.get_logger().info(f"sum={future.result().sum}")

```

需要服务发现等待、超时和异常处理；此对照仅展示请求与结果 API。

Python 的同步 call() 不是 C++ 的直接对应物；官方建议优先 call_async。

- [C++ 服务与客户端](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Service-And-Client.html)

- [Python 服务与客户端](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html)

- [同步与异步服务调用](https://docs.ros.org/en/jazzy/How-To-Guides/Sync-Vs-Async.html)

### 动作：两种语言的同一状态机

Goal、Feedback 和 Result 在 C++/Python 中怎样对应？

#### C++ / rclcpp_action

API 对照清单；不是可执行源码

```text

创建服务端：rclcpp_action::create_server<ActionT>(...)
处理目标：handle_goal → ACCEPT_AND_EXECUTE / REJECT
反馈：goal_handle->publish_feedback(feedback)
成功：goal_handle->succeed(result)
取消：goal_handle->is_canceling() → canceled(result)
客户端：async_send_goal → async_get_result

```

#### Python / rclpy.action

API 对照清单；不是可执行源码

```text

创建服务端：ActionServer(node, ActionT, name, execute_callback, ...)
处理目标：goal_callback → GoalResponse.ACCEPT / REJECT
反馈：goal_handle.publish_feedback(feedback)
成功：goal_handle.succeed(); return result
取消：goal_handle.is_cancel_requested → canceled(); return result
客户端：send_goal_async → get_result_async

```

两端可共用同一 .action。

接受目标、完成执行和收到结果是不同阶段。

取消回调、可取消执行循环和 executor 配置需要配套设计。

- [C++ 动作服务端与客户端](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Cpp.html)

- [Python 动作服务端与客户端](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html)

- [创建 action 接口](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Creating-an-Action.html)

### 相同参数：命令行、参数 YAML、Python launch

运行配置放在哪一层更合适？

#### CLI

可直接运行，需图形环境及 turtlesim

```bash

ros2 run turtlesim turtlesim_node --ros-args -r __node:=sim -p background_r:=160

```

#### 参数文件

保存为 colors.yaml 后使用 --params-file colors.yaml；节点名设为 sim

```yaml

sim:
  ros__parameters:
    background_r: 160
    background_g: 80
    background_b: 40

```

#### Python launch 中的参数

LaunchDescription 中的单个动作片段；需 Node 导入

```python

Node(
    package="turtlesim", executable="turtlesim_node", name="sim",
    parameters=[{"background_r": 160, "background_g": 80, "background_b": 40}],
)

```

参数文件 YAML 和 launch YAML 是两种格式。

节点名、命名空间、参数类型都影响配置是否生效。

- [C++ 参数节点](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-CPP.html)

- [Python 参数节点](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-Python.html)

- [Python / XML / YAML launch 对照](https://docs.ros.org/en/jazzy/How-To-Guides/Launch-file-different-formats.html)

### 等价系统：Python / XML / YAML launch

启动同一命名空间下的 talker 并重映射话题，三种写法如何对应？

#### Python

完整最小 launch 文件；保存为 telemetry.launch.py 后 ros2 launch ./telemetry.launch.py

```python

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(package="demo_nodes_cpp", executable="talker",
             namespace="robot1", name="talker", output="screen",
             remappings=[("chatter", "telemetry")])
    ])

```

#### XML

完整最小 launch 文件；保存为 telemetry.launch.xml

```xml

<launch>
  <node pkg="demo_nodes_cpp" exec="talker"
        namespace="robot1" name="talker" output="screen">
    <remap from="chatter" to="telemetry"/>
  </node>
</launch>

```

#### YAML

完整最小 launch 文件；保存为 telemetry.launch.yaml

```yaml

launch:
  - node:
      pkg: demo_nodes_cpp
      exec: talker
      namespace: robot1
      name: talker
      output: screen
      remap:
        - from: chatter
          to: telemetry

```

三者都发布 /robot1/telemetry；每次只运行一种避免重复节点名。

Python launch 并不要求所启动的节点也是 Python。

本组可直接启动，但本研究未实际运行 ROS；依赖 demo_nodes_cpp 和对应 launch 前端。

- [Python / XML / YAML launch 对照](https://docs.ros.org/en/jazzy/How-To-Guides/Launch-file-different-formats.html)

- [官方 YAML launch 源文件](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/How-To-Guides/launch/different_formats_launch.yaml)

- [官方 Python launch 源文件](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/How-To-Guides/launch/different_formats_launch.py)

### 执行器：单线程与多线程的对应写法

有多个就绪回调时，谁决定能否并发？

#### C++ 单线程

main 中核心片段；node 已创建且 rclcpp 已初始化

```cpp

rclcpp::executors::SingleThreadedExecutor executor;
executor.add_node(node);
executor.spin();

```

#### C++ 多线程

main 中核心片段；需配套 callback groups

```cpp

rclcpp::executors::MultiThreadedExecutor executor(
    rclcpp::ExecutorOptions(), 2);
executor.add_node(node);
executor.spin();

```

#### Python 多线程

main 中核心片段；需初始化、回调组与清理代码

```python

from rclpy.executors import MultiThreadedExecutor
executor = MultiThreadedExecutor(num_threads=2)
executor.add_node(node)
executor.spin()

```

默认互斥组中的回调不会因为使用多线程执行器自动并发。

Reentrant 并不替代线程安全设计。

- [执行器概念](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html)

- [回调组及死锁规避](https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html)

### 部署：独立节点与 C++ 组件容器

同样的节点功能怎样选择进程边界？

#### 独立进程

可直接运行；各自为独立进程

```bash

# 两个终端分别运行
ros2 run demo_nodes_cpp talker
ros2 run demo_nodes_cpp listener

```

#### 组件容器

可直接运行；需官方 composition 包

```bash

# 终端 A
ros2 run rclcpp_components component_container
# 终端 B
ros2 component load /ComponentManager composition composition::Talker
ros2 component load /ComponentManager composition composition::Listener

```

这里对照相同话题功能的两种官方示例部署；不是声称二者是同一可执行文件。

Python 多节点 executor 不等于 rclcpp_components 动态共享库加载。

是否获得零拷贝收益需要单独验证。

- [在一个进程里组合节点](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html)

- [把 C++ 节点写成组件](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-a-Composable-Node.html)

- [ros2/demos · jazzy](https://github.com/ros2/demos/tree/jazzy)

### 构建：ament_cmake 与 ament_python

ROS 包如何把源码变成可被 ros2 run 找到的入口？

#### C++ 包

在工作空间 src 运行，生成 CMake 包骨架

```bash

ros2 pkg create --build-type ament_cmake --license Apache-2.0 --node-name hello learning_cpp --dependencies rclcpp

```

#### Python 包

在工作空间 src 运行，生成 Python 包骨架

```bash

ros2 pkg create --build-type ament_python --license Apache-2.0 --node-name hello learning_py --dependencies rclpy

```

#### 共同构建入口

两种包可位于同一工作空间

```bash

cd ~/ros2_learning_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --symlink-install
source install/setup.bash

```

CMake 需要安装可执行目标；Python 需要正确的 entry_points 和 setup.cfg。

接口包与使用它的节点包可采用不同构建类型。

- [创建 CMake 或 Python 包](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)

- [ament_cmake 用户指南](https://docs.ros.org/en/jazzy/How-To-Guides/Ament-CMake-Documentation.html)

- [colcon 快速开始](https://colcon.readthedocs.io/en/released/user/quick-start.html)

- [自定义 msg 和 srv](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.html)

### QoS：便捷配置与显式配置

如何在 C++ 和 Python 表达传感器数据订阅？

#### C++ SensorDataQoS

Node 方法内片段；需已有 callback 和持久 subscription_

```cpp

subscription_ = create_subscription<sensor_msgs::msg::LaserScan>(
    "scan", rclcpp::SensorDataQoS(), callback);

```

#### Python 预定义配置

Node 方法内片段；需导入 LaserScan 和定义 on_scan

```python

from rclpy.qos import qos_profile_sensor_data
self.subscription = self.create_subscription(
    LaserScan, "scan", self.on_scan, qos_profile_sensor_data)

```

#### Python 显式指定

核心片段；展示主要传感器 QoS 策略，其他字段使用默认值

```python

from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
qos = QoSProfile(depth=5,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE)

```

不要只比较 depth；reliability 与 durability 会影响匹配。

显式设置片段只说明关键字段，预定义配置的完整值以当前 Jazzy API 为准。

- [QoS 策略与兼容性](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html)

- [rclcpp · jazzy](https://github.com/ros2/rclcpp/tree/jazzy)

- [rclpy · jazzy](https://github.com/ros2/rclpy/tree/jazzy)

### 底盘速度：Twist 与 TwistStamped

同样表示车体速度，为什么有的驱动接收Twist，有的控制器需要带时间戳的消息？

#### BUNKER 示例 · Twist

仅在独立仿真或已确认的演示接口使用。先检查话题类型；这是零速度消息，不启动硬件。

```bash

ros2 topic info /cmd_vel --verbose
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"

```

#### DiffBot Jazzy · TwistStamped

当前example_2将控制器输入重映射至/cmd_vel；header:auto为发布时间填入时钟值。

```bash

ros2 topic info /cmd_vel --verbose
ros2 topic pub --once /cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: auto, twist: {linear: {x: 0.0}, angular: {z: 0.0}}}"

```

话题同名不代表类型相同；重映射也不转换类型。

TwistStamped增加header，速度数值位于twist内部。

命令新鲜度、发布频率和超时策略由驱动或控制器共同定义。不要用过期时间戳反复发送。

这里的零速度命令不能替代真实设备的独立停止机制。

- [diff_drive_controller 参数与接口](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)

- [DiffBot 差速底盘官方示例](https://control.ros.org/jazzy/doc/ros2_control_demos/example_2/doc/userdoc.html)

- [bunker_ros2 本地固定提交](https://github.com/agilexrobotics/bunker_ros2/tree/f24f722b245eb1d2572c47d091fc847d9fd68cf4)

### 模型描述：URDF 与 Xacro

重复的机器人结构，如何从手写XML变成可复用的参数和宏？

#### URDF · 直接描述

robot元素内的局部片段；完整模型还需要父子link与其他关节。

```xml

<joint name="laser_joint" type="fixed">
  <parent link="base_link"/>
  <child link="laser"/>
  <origin xyz="0.2 0 0.15" rpy="0 0 0"/>
</joint>

```

#### Xacro · 参数化描述

放在声明xmlns:xacro的robot元素中；先经xacro展开再交给URDF读取者。

```xml

<xacro:property name="laser_height" value="0.15"/>
<joint name="laser_joint" type="fixed">
  <parent link="base_link"/>
  <child link="laser"/>
  <origin xyz="0.2 0 ${laser_height}" rpy="0 0 0"/>
</joint>

```

Xacro是生成URDF的宏处理工具，不是另一种物理仿真器。

先运行 xacro robot.urdf.xacro > /tmp/robot.urdf，再检查最终结构；不要只检查源模板。

ros2_control标签、惯性、碰撞与视觉是不同层面的描述，不能相互替代。

- [URDF 官方教程源码](https://github.com/ros/urdf_tutorial/tree/ros2)

- [Xacro 项目](https://github.com/ros/xacro)

- [robot_state_publisher 源码](https://github.com/ros/robot_state_publisher/tree/jazzy)

## 综合项目

### 两种语言，一个通信图

用随站点提供的完整工程，在C++和Python之间交换消息，并比较三种launch格式。

1. 下载并解压教学工程，在独立目录构建atlas_cpp与atlas_py。

2. 启动C++发布者和Python订阅者，观察ATLAS_MESSAGE；再交换语言。

3. 用Python/XML/YAML launch启动同一组节点，每次只使用一种。

4. 修改命名空间或QoS，预测现象后再用CLI检查。

```bash

# 在解压后的 atlas_examples 目录
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch atlas_cpp demo.launch.py

```

完整工程包含package.xml、CMakeLists、setup.py、节点与三种launch文件。下载包README说明构建与验证范围。

### 把车体速度接到左右轮

以Jazzy官方DiffBot为起点，读懂read→update→write，再对照履带平台的真实接口。

1. 在独立工作空间按官方example_2说明构建并启动DiffBot。

2. 确认控制器active、关节名称和命令接口一致。

3. 核对/cmd_vel为TwistStamped，观察joint_states与里程计。

4. 识别open_loop与模拟硬件，写出替换为真实反馈所需的工作。

```bash

# 启动已经构建的官方示例
ros2 launch ros2_control_demo_example_2 diffbot.launch.py
# 另一个已source的终端
ros2 control list_controllers
ros2 control list_hardware_interfaces
ros2 topic info /cmd_vel --verbose

```

官方演示硬件使用软件数值，并未连接底盘。open_loop里程计的变化不证明编码器反馈正常。

### 建图、定位，再去一个目标点

将激光、TF、状态估计与Nav2组合起来，逐层解释导航失败发生在哪里。

1. 按Nav2 Jazzy quickstart搭建匹配的仿真依赖。

2. 证明scan有效、时钟一致，map→odom→base_link→laser链完整。

3. 完成建图与保存，再用保存地图定位。

4. 发送导航Action，记录规划、控制、取消和恢复的结果。

```bash

# 在已启动的匹配导航系统旁逐层检查
ros2 topic info /scan --verbose
ros2 run tf2_ros tf2_echo map base_link
ros2 action list -t
ros2 lifecycle nodes

```

导航参数应由机器人尺寸、传感器与动力学决定；先用官方仿真基线，再替换自己的模型。

### 从目标位姿到可执行轨迹

先在规划场景中理解碰撞和约束，再连接轨迹控制器，最后组合多步任务。

1. 为选定机械臂确认URDF、SRDF、关节限位和规划组。

2. 在RViz中检查起始状态与障碍物，执行一次仅规划。

3. 检查FollowJointTrajectory动作与控制器映射后，在仿真中执行。

4. 加入抓取接近、夹爪动作和撤离步骤，并测试失败分支。

```bash

# 在已启动的MoveIt演示系统中检查
ros2 topic echo /joint_states --once
ros2 action list -t
ros2 control list_controllers

```

MoveIt main站点可能是Rolling。Jazzy工程必须核对对应源码与依赖版本，示例机器人名字不能直接替换为自己的硬件。

### 让微控制器和第二台机器人加入系统

从一个低频传感器话题开始，逐步建立Agent、命名空间、断线恢复和任务边界。

1. 先明确板卡、RTOS、内存、传输和micro-ROS分支。

2. 只接入一个传感器发布者，确认类型、时间戳与丢包行为。

3. 引入robot1和robot2命名空间，逐条核对TF frame_id，不依靠命名空间自动改消息。

4. 测试Agent或网络断开时的状态处理，再研究Open-RMF的车队适配。

```bash

# Agent与设备按所选板卡官方流程启动后
ros2 node list
ros2 topic list -t
ros2 topic info /robot1/sensor --verbose
# /robot1/sensor 是规划接口示例，替换为实际话题名

```

固件、Agent与消息定义需要匹配。DDS域隔离不是权限控制；本项目路线不包含实机烧录或车队调度验证。

## 完整教学工程文件

### LICENSE

```text


                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "[]"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright [yyyy] [name of copyright owner]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.


```

### README.md

````markdown

# ROS 2 学习图谱 · 完整通信工程

目标环境：Ubuntu 24.04 / ROS 2 Jazzy。包含 `atlas_cpp` 与 `atlas_py`，各有一个发布者、订阅者、加法服务端与异步客户端，以及等价的 Python / XML / YAML launch 文件。所有消息都是教学字符串；没有设备或电机控制接口。

## 构建

在独立目录解压 `atlas_examples.zip`，进入其中的 `atlas_examples/`：

```bash
source /opt/ros/jazzy/setup.bash
# 尚未安装这些依赖时：
sudo apt install python3-colcon-common-extensions ros-jazzy-rclcpp ros-jazzy-rclpy \
  ros-jazzy-std-msgs ros-jazzy-launch-ros ros-jazzy-launch-xml ros-jazzy-launch-yaml
sudo apt install ros-jazzy-example-interfaces
colcon build --symlink-install
source install/setup.bash
```

## 实验一：C++ 发布，Python 订阅

每个终端都先加载 Jazzy 和刚构建的 `install/setup.bash`。为了不与其他练习混淆，可在每个终端设置同一个独立域与本机发现范围：

```bash
export ROS_DOMAIN_ID=197
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
```

终端 A：

```bash
ros2 run atlas_cpp talker --ros-args -r __ns:=/atlas
```

终端 B：

```bash
ros2 run atlas_py listener --ros-args -r __ns:=/atlas
```

每 250ms 发布一条 `ATLAS_MESSAGE cpp N`，订阅者显示 `RECEIVED ATLAS_MESSAGE ...`。两端 Ctrl+C 退出。Domain ID 不是安全权限控制。

## 实验二：交换语言

把 A 改为 `ros2 run atlas_py talker --ros-args -r __ns:=/atlas`，B 改为 `ros2 run atlas_cpp listener --ros-args -r __ns:=/atlas`。观察消息后检查 `ros2 topic info /atlas/chatter --verbose`。所有发布/订阅对象都保持为节点成员，避免生命周期结束。

## 实验三：三种启动文件

每次只启动其中一种；Ctrl+C 退出再换下一种：

```bash
ros2 launch atlas_cpp demo.launch.py
ros2 launch atlas_cpp demo.launch.xml
ros2 launch atlas_cpp demo.launch.yaml
```

三者都启动 `/atlas/talker`（C++）和 `/atlas/listener`（Python），使用 `/atlas/chatter`。启动文件的语言不限制节点实现语言。

## 实验四：跨语言服务与异步响应

沿用两个终端的相同 Domain ID 与环境。终端 A：

```bash
ros2 run atlas_cpp add_server --ros-args -r __ns:=/atlas
```

终端 B：

```bash
ros2 run atlas_py add_client --ros-args -r __ns:=/atlas
```

客户端请求 7+5，输出 `SUM=12` 后退出。服务端继续等待请求。退出服务端，再把它换成 `atlas_py add_server`、客户端换成 `atlas_cpp add_client`，验证相同类型和接口可跨语言使用。每次只运行一个同名服务端。

客户端先等待服务发现，随后发送异步请求并调度执行器等待 Future，两阶段分别设置 5 秒超时。这里的等待在主程序中，不位于互斥回调组的回调内部。关闭服务端再运行客户端，应在超时后返回错误，而非永远等待。请求使用小整数；生产接口还需定义允许范围和失败响应。

## 练习

1. 改变发布周期，分别说明 timer 周期和 QoS 队列深度的作用。
2. 只改变一端命名空间，预测结果再检查端点。
3. 让发布者用 best effort、订阅者用 reliable，解释为何可发现但收不到。
4. 把 CLI 的命名空间配置移入三种 launch，验证完整话题名相同。

本工程为原创教学代码，参考 ROS 官方 Jazzy examples 的客户端库用法，使用 Apache-2.0 许可。构建和通信验证状态见随包 `VALIDATION.md`；网站其他示例片段不因此视为已执行。

## 四个无需 ROS 环境的离线实验

`offline_labs/` 下的程序只需 Python 3 标准库。分别对应教材的强化学习、语言模型任务规划、模仿学习与数据流程章节：

```bash
python3 offline_labs/rl_gain_search.py
python3 offline_labs/plan_contract.py
python3 offline_labs/policy_gate.py
python3 offline_labs/dataset_manifest.py /path/to/your/data
```

最后一个命令只读指定目录并输出清单；保存清单时请放在输入目录之外。详细原理、预期输出与练习答案已包含在离线教材中。


````

### VALIDATION.md

````markdown

# 示例验证记录

日期：2026-11-06。环境：Ubuntu 24.04、ROS 2 Jazzy、Python 3.12、系统 C++ 编译器。只使用本机教学节点，没有连接或控制真实机器人。

已完成：

1. `atlas_cpp` 与 `atlas_py` 经 colcon 构建并安装，构建日志无编译错误。
2. C++ 发布 / Python 订阅，接收 `ATLAS_MESSAGE`。
3. Python 发布 / C++ 订阅，接收 `ATLAS_MESSAGE`。
4. C++ 服务端 / Python 客户端，返回 `SUM=12`。
5. Python 服务端 / C++ 客户端，返回 `SUM=12`。
6. Python、XML、YAML launch 均经 Jazzy 解析器加载，各产生两个节点动作。此项验证解析和结构，未声称三套 launch 全部进行了长时间运行。
7. 四个标准库离线实验完成正常与故障输入检查，结果记录在网站项目的 `VALIDATION.md`。

集成测试使用 `ROS_DOMAIN_ID=197`、`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`，在测试结束时关闭其创建的进程。复现时在网站工程根目录执行：

```bash
source /opt/ros/jazzy/setup.bash
colcon --log-base /tmp/ros2-atlas-build/log build \
  --base-paths examples/src --build-base /tmp/ros2-atlas-build/build \
  --install-base /tmp/ros2-atlas-build/install --merge-install --symlink-install
source /tmp/ros2-atlas-build/install/setup.bash
python3 tests/test_examples.py
```

这组结果只覆盖随包通信工程。正文中其他生态命令、硬件配置、网络配置、仿真、学习框架与模型不因此视为在本机全部运行过；各章另有适用环境和验证说明。


````

### offline_labs/dataset_manifest.py

```python

"""Create a deterministic manifest on stdout. Input data is never modified."""
import hashlib
import json
import sys
from pathlib import Path

def manifest(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("dataset root must be a directory")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symbolic links require an explicit data policy")
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        files.append({"path": path.relative_to(root).as_posix(),
                      "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
    return {"schema": 1, "files": files}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 dataset_manifest.py DATA_DIRECTORY")
    print(json.dumps(manifest(sys.argv[1]), ensure_ascii=False, indent=2))


```

### offline_labs/plan_contract.py

```python

"""Validate a task proposal and print a dry-run; never executes ROS commands."""
import json
import math

PLACES = {"desk": (1.0, 0.5, 0.0), "dock": (0.0, 0.0, 0.0)}

def validate(raw):
    plan = json.loads(raw)
    if not isinstance(plan, list) or not 1 <= len(plan) <= 8:
        raise ValueError("plan must contain 1..8 steps")
    for step in plan:
        if not isinstance(step, dict):
            raise ValueError("step must be an object")
        skill = step.get("skill")
        allowed = {"navigate": {"skill", "place", "timeout"},
                   "inspect": {"skill", "object", "timeout"}}
        if not isinstance(skill, str) or skill not in allowed or set(step) != allowed[skill]:
            raise ValueError("unknown skill or unexpected fields")
        timeout = step["timeout"]
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise ValueError("invalid timeout")
        if skill == "navigate" and (not isinstance(step["place"], str) or step["place"] not in PLACES):
            raise ValueError("unknown place")
        if skill == "inspect" and step["object"] not in ("cup", "marker"):
            raise ValueError("unsupported object")
    return plan

def main():
    sample = '[{"skill":"navigate","place":"desk","timeout":60},{"skill":"inspect","object":"cup","timeout":10}]'
    for index, step in enumerate(validate(sample), 1):
        print("DRY_RUN", index, step)
    for bad in ('[{"skill":"shell","command":"anything","timeout":10}]',
                '[{"skill":"navigate","place":"unknown","timeout":60}]'):
        try:
            validate(bad)
        except ValueError as error:
            print("REJECTED", error)
        else:
            raise AssertionError("invalid plan accepted")

if __name__ == "__main__":
    main()


```

### offline_labs/policy_gate.py

```python

"""Demonstrate timestamp/dimension/finite/rate checks for a six-joint policy."""
import math

def gate(candidate, previous, age_seconds, dt, limit=0.5):
    # These are position targets in radians, not torques or velocities.
    if len(candidate) != 6 or len(previous) != 6:
        raise ValueError("expected six joints in the agreed order")
    if not all(math.isfinite(x) for x in (*candidate, *previous, age_seconds, dt, limit)):
        raise ValueError("non-finite input")
    if dt <= 0 or limit <= 0:
        raise ValueError("invalid control interval or rate limit")
    if age_seconds < 0 or age_seconds > 0.1:
        return None  # Caller must select its independently verified stop/hold mode.
    output = []
    for target, last in zip(candidate, previous):
        bounded = max(-1.0, min(1.0, target))
        output.append(last + max(-limit * dt, min(limit * dt, bounded - last)))
    return output

def main():
    print("ACCEPTED", gate([0.5] * 6, [0.0] * 6, 0.02, 0.02))
    print("STALE", gate([0.5] * 6, [0.0] * 6, 0.3, 0.02))
    try:
        gate([float("nan")] * 6, [0.0] * 6, 0.02, 0.02)
    except ValueError as error:
        print("REJECTED", error)

if __name__ == "__main__":
    main()


```

### offline_labs/rl_gain_search.py

```python

"""A tiny policy-search experiment; standard library only, no robot connection."""
import json
import random

def rollout(gain, seed, mass=1.0, steps=120):
    rng = random.Random(seed)
    position, velocity = rng.uniform(-2.0, 2.0), 0.0
    reward = 0.0
    for _ in range(steps):
        force = max(-1.0, min(1.0, -gain * position - 0.8 * velocity))
        velocity += (force / mass - 0.1 * velocity) * 0.05
        position += velocity * 0.05
        reward -= position ** 2 + 0.01 * force ** 2
    return reward, abs(position)

def evaluate(gain, seeds, mass=1.0):
    results = [rollout(gain, seed, mass) for seed in seeds]
    return {"gain": gain, "mass": mass,
            "mean_return": sum(x[0] for x in results) / len(results),
            "mean_final_error": sum(x[1] for x in results) / len(results)}

def main():
    candidates = [evaluate(g, range(5)) for g in (0.0, 0.25, 0.5, 1.0, 2.0)]
    best = max(candidates, key=lambda item: item["mean_return"])["gain"]
    print(json.dumps({"training": candidates, "selected_gain": best,
                      "held_out": [evaluate(best, range(100, 110), mass)
                                   for mass in (0.7, 1.0, 1.5)]}, indent=2))

if __name__ == "__main__":
    main()


```

### src/atlas_cpp/CMakeLists.txt

```text

cmake_minimum_required(VERSION 3.16)
project(atlas_cpp)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(example_interfaces REQUIRED)
foreach(node talker listener add_server add_client)
  add_executable(${node} src/${node}.cpp)
  target_compile_features(${node} PUBLIC cxx_std_17)
  ament_target_dependencies(${node} rclcpp std_msgs example_interfaces)
  install(TARGETS ${node} DESTINATION lib/${PROJECT_NAME})
endforeach()
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
ament_package()


```

### src/atlas_cpp/launch/demo.launch.py

```python

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='atlas_cpp', executable='talker', namespace='atlas',
             name='talker', output='screen'),
        Node(package='atlas_py', executable='listener', namespace='atlas',
             name='listener', output='screen'),
    ])


```

### src/atlas_cpp/launch/demo.launch.xml

```xml

<launch>
  <node pkg="atlas_cpp" exec="talker" namespace="atlas" name="talker" output="screen"/>
  <node pkg="atlas_py" exec="listener" namespace="atlas" name="listener" output="screen"/>
</launch>


```

### src/atlas_cpp/launch/demo.launch.yaml

```yaml

launch:
  - node:
      pkg: atlas_cpp
      exec: talker
      namespace: atlas
      name: talker
      output: screen
  - node:
      pkg: atlas_py
      exec: listener
      namespace: atlas
      name: listener
      output: screen


```

### src/atlas_cpp/package.xml

```xml

<?xml version="1.0"?>
<package format="3">
  <name>atlas_cpp</name><version>0.1.0</version>
  <description>ROS 2 学习图谱：完整 C++ 发布订阅与三种 launch 示例</description>
  <maintainer email="learner@example.com">ROS 2 Atlas contributors</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend><depend>std_msgs</depend>
  <depend>example_interfaces</depend>
  <exec_depend>atlas_py</exec_depend><exec_depend>launch_ros</exec_depend>
  <exec_depend>launch_xml</exec_depend><exec_depend>launch_yaml</exec_depend>
  <export><build_type>ament_cmake</build_type></export>
</package>


```

### src/atlas_cpp/src/add_client.cpp

```cpp

// SPDX-License-Identifier: Apache-2.0
#include <chrono>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"

int main(int argc, char **argv) {
  using namespace std::chrono_literals;
  using Add = example_interfaces::srv::AddTwoInts;
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("atlas_add_client_cpp");
  auto client = node->create_client<Add>("add_two_ints");
  if (!client->wait_for_service(5s)) {
    RCLCPP_ERROR(node->get_logger(), "Service unavailable after 5 seconds");
    rclcpp::shutdown();
    return 1;
  }
  auto request = std::make_shared<Add::Request>();
  request->a = 7;
  request->b = 5;
  auto future = client->async_send_request(request);
  const auto result = rclcpp::spin_until_future_complete(node, future, 5s);
  if (result != rclcpp::FutureReturnCode::SUCCESS) {
    client->remove_pending_request(future);
    RCLCPP_ERROR(node->get_logger(), "Request timed out or interrupted");
    rclcpp::shutdown();
    return 1;
  }
  RCLCPP_INFO(node->get_logger(), "SUM=%ld", static_cast<long>(future.get()->sum));
  rclcpp::shutdown();
  return 0;
}


```

### src/atlas_cpp/src/add_server.cpp

```cpp

// SPDX-License-Identifier: Apache-2.0
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("atlas_add_server_cpp");
  using Add = example_interfaces::srv::AddTwoInts;
  auto service = node->create_service<Add>("add_two_ints",
    [](const std::shared_ptr<Add::Request> request,
       std::shared_ptr<Add::Response> response) {
      // 本练习使用小整数 7 和 5；生产接口还需定义数值范围。
      response->sum = request->a + request->b;
    });
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}


```

### src/atlas_cpp/src/listener.cpp

```cpp

// SPDX-License-Identifier: Apache-2.0
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class Listener : public rclcpp::Node {
public:
  Listener() : Node("atlas_listener_cpp") {
    subscription_ = create_subscription<std_msgs::msg::String>(
      "chatter", 10, [this](std_msgs::msg::String::ConstSharedPtr message) {
        RCLCPP_INFO(get_logger(), "RECEIVED %s", message->data.c_str());
      });
  }
private:
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
};
int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Listener>());
  rclcpp::shutdown();
  return 0;
}


```

### src/atlas_cpp/src/talker.cpp

```cpp

// SPDX-License-Identifier: Apache-2.0
#include <chrono>
#include <memory>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class Talker : public rclcpp::Node {
public:
  Talker() : Node("atlas_talker_cpp") {
    publisher_ = create_publisher<std_msgs::msg::String>("chatter", 10);
    timer_ = create_wall_timer(std::chrono::milliseconds(250), [this]() {
      std_msgs::msg::String message;
      message.data = "ATLAS_MESSAGE cpp " + std::to_string(count_++);
      publisher_->publish(message);
      RCLCPP_INFO(get_logger(), "SENT %s", message.data.c_str());
    });
  }
private:
  std::size_t count_{0};
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};
int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Talker>());
  rclcpp::shutdown();
  return 0;
}


```

### src/atlas_py/atlas_py/__init__.py

```python

"""Original ROS 2 learning examples."""


```

### src/atlas_py/atlas_py/add_client.py

```python

# SPDX-License-Identifier: Apache-2.0
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


def main(args=None):
    rclpy.init(args=args)
    node = Node('atlas_add_client_py')
    client = node.create_client(AddTwoInts, 'add_two_ints')
    status = 1
    try:
        if not client.wait_for_service(timeout_sec=5.0):
            node.get_logger().error('Service unavailable after 5 seconds')
        else:
            request = AddTwoInts.Request()
            request.a, request.b = 7, 5
            future = client.call_async(request)
            rclpy.spin_until_future_complete(node, future, timeout_sec=5.0)
            if future.done() and future.exception() is None:
                node.get_logger().info(f'SUM={future.result().sum}')
                status = 0
            else:
                future.cancel()
                node.get_logger().error('Request timed out or failed')
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return status


if __name__ == '__main__':
    raise SystemExit(main())


```

### src/atlas_py/atlas_py/add_server.py

```python

# SPDX-License-Identifier: Apache-2.0
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class AddServer(Node):
    def __init__(self):
        super().__init__('atlas_add_server_py')
        self.service = self.create_service(AddTwoInts, 'add_two_ints', self.add)

    def add(self, request, response):
        response.sum = request.a + request.b
        return response


def main(args=None):
    rclpy.init(args=args)
    node = AddServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()


```

### src/atlas_py/atlas_py/listener.py

```python

# SPDX-License-Identifier: Apache-2.0
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):
    def __init__(self):
        super().__init__('atlas_listener_py')
        self.subscription = self.create_subscription(
            String, 'chatter', self.receive_message, 10)

    def receive_message(self, message):
        self.get_logger().info(f'RECEIVED {message.data}')


def main(args=None):
    rclpy.init(args=args)
    node = Listener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()


```

### src/atlas_py/atlas_py/talker.py

```python

# SPDX-License-Identifier: Apache-2.0
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    def __init__(self):
        super().__init__('atlas_talker_py')
        self.publisher = self.create_publisher(String, 'chatter', 10)
        self.count = 0
        self.timer = self.create_timer(0.25, self.publish_message)

    def publish_message(self):
        message = String()
        message.data = f'ATLAS_MESSAGE python {self.count}'
        self.count += 1
        self.publisher.publish(message)
        self.get_logger().info(f'SENT {message.data}')


def main(args=None):
    rclpy.init(args=args)
    node = Talker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()


```

### src/atlas_py/package.xml

```xml

<?xml version="1.0"?>
<package format="3">
  <name>atlas_py</name><version>0.1.0</version>
  <description>ROS 2 学习图谱：完整 Python 发布订阅示例</description>
  <maintainer email="learner@example.com">ROS 2 Atlas contributors</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_python</buildtool_depend>
  <exec_depend>rclpy</exec_depend><exec_depend>std_msgs</exec_depend>
  <exec_depend>example_interfaces</exec_depend>
  <export><build_type>ament_python</build_type></export>
</package>


```

### src/atlas_py/resource/atlas_py

```text




```

### src/atlas_py/setup.cfg

```ini

[develop]
script_dir=$base/lib/atlas_py
[install]
install_scripts=$base/lib/atlas_py


```

### src/atlas_py/setup.py

```python

from setuptools import setup

setup(
    name='atlas_py', version='0.1.0', packages=['atlas_py'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/atlas_py']),
        ('share/atlas_py', ['package.xml']),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='ROS 2 Atlas contributors', maintainer_email='learner@example.com',
    description='ROS 2 学习图谱 Python 发布订阅示例', license='Apache-2.0',
    entry_points={'console_scripts': [
        'talker = atlas_py.talker:main',
        'listener = atlas_py.listener:main',
        'add_server = atlas_py.add_server:main',
        'add_client = atlas_py.add_client:main',
    ]},
)


```

## 全部来源目录

- [ROS 2 Jazzy 官方教程总目录](https://docs.ros.org/en/jazzy/Tutorials.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [ROS 2 Jazzy 概念目录](https://docs.ros.org/en/jazzy/Concepts.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [ROS 2 Jazzy 操作指南](https://docs.ros.org/en/jazzy/How-To-Guides.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [Ubuntu 24.04 上安装 Jazzy](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [CLI 工具学习路线](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [C++ / Python 客户端库教程](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [中级教程](https://docs.ros.org/en/jazzy/Tutorials/Intermediate.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [高级教程](https://docs.ros.org/en/jazzy/Tutorials/Advanced.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [工作空间与 overlay](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [创建 CMake 或 Python 包](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [话题检查与调试](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [C++ 发布者与订阅者](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Publisher-And-Subscriber.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [Python 发布者与订阅者](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [C++ 服务与客户端](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Service-And-Client.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [Python 服务与客户端](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [自定义 msg 和 srv](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [C++ 参数节点](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-CPP.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [Python 参数节点](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-Python.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [创建 action 接口](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Creating-an-Action.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [C++ 动作服务端与客户端](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Cpp.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [Python 动作服务端与客户端](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [QoS 策略与兼容性](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [执行器概念](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [回调组及死锁规避](https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [同步与异步服务调用](https://docs.ros.org/en/jazzy/How-To-Guides/Sync-Vs-Async.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [在一个进程里组合节点](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [把 C++ 节点写成组件](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-a-Composable-Node.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [Python / XML / YAML launch 对照](https://docs.ros.org/en/jazzy/How-To-Guides/Launch-file-different-formats.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [rosdep 依赖管理](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Rosdep.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [ament_cmake 用户指南](https://docs.ros.org/en/jazzy/How-To-Guides/Ament-CMake-Documentation.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [tf2 C++ / Python 教程路线](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [静态 TF 与命令行广播器](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [ROS 2 自动化测试](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Testing/Testing-Main.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [SROS2 安全教程目录](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Security/Security-Main.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [启用 DDS-Security / SROS2](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Security/Introducing-ros2-security.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [ros2_tracing 性能分析](https://docs.ros.org/en/jazzy/Tutorials/Advanced/ROS2-Tracing-Trace-and-Analyze.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [选择不同 RMW 实现](https://docs.ros.org/en/jazzy/How-To-Guides/Working-with-multiple-RMW-implementations.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [rosbag2 录制与回放](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [ros2 doctor 诊断](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Getting-Started-With-Ros2doctor.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [动态发现范围与静态对等端](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [ROS_DOMAIN_ID 与端口约束](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Domain-ID.html) · Jazzy · 已读取官方 jazzy 分支原文；正式文档域名触发 Anubis，未声称网页直连成功

- [ros2/examples · jazzy](https://github.com/ros2/examples/tree/jazzy) · Jazzy · 已联网读取一手来源

- [ros2/demos · jazzy](https://github.com/ros2/demos/tree/jazzy) · Jazzy · 已联网读取一手来源

- [rclcpp · jazzy](https://github.com/ros2/rclcpp/tree/jazzy) · Jazzy · 已联网读取一手来源

- [rclpy · jazzy](https://github.com/ros2/rclpy/tree/jazzy) · Jazzy · 已联网读取一手来源

- [官方 Lifecycle 演示说明](https://github.com/ros2/demos/blob/jazzy/lifecycle/README.rst) · Jazzy · 已联网读取一手来源

- [ROS 时间设计](https://design.ros2.org/articles/clock_and_time.html) · ROS 2 通用设计 · 已联网读取一手来源

- [colcon 快速开始](https://colcon.readthedocs.io/en/released/user/quick-start.html) · colcon released · 已联网读取一手来源

- [ROS 2 发行版与维护周期](https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases.rst) · 发行版总览 · 已联网读取一手来源

- [官方 YAML launch 源文件](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/How-To-Guides/launch/different_formats_launch.yaml) · Jazzy · 已联网读取一手来源

- [官方 Python launch 源文件](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/How-To-Guides/launch/different_formats_launch.py) · Jazzy · 已联网读取一手来源

- [动作 Python 示例可执行入口](https://raw.githubusercontent.com/ros2/demos/jazzy/action_tutorials/action_tutorials_py/setup.py) · Jazzy · 已联网读取一手来源

- [Nav2 官方文档（Jazzy）](https://docs.nav2.org/jazzy/) · Jazzy · 已读取官方或维护者页面

- [Nav2 仿真快速开始](https://docs.nav2.org/jazzy/getting_started/quickstart/quickstart/) · Jazzy · 已读取官方或维护者页面

- [Nav2 首次机器人接入指南](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/) · Jazzy · 已读取官方或维护者页面

- [Nav2 参数与插件配置](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/) · Jazzy · 已读取官方或维护者页面

- [Nav2 Simple Commander Python API](https://docs.nav2.org/jazzy/configuration_and_development/simple_commander_api/simple_commander_api/) · Jazzy · 已读取官方或维护者页面

- [Nav2：融合里程计](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/odom/setup_robot_localization/) · Jazzy · 已读取官方或维护者页面

- [Nav2：建图与定位](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/sensors/mapping_localization/) · Jazzy · 已读取官方或维护者页面

- [ros2_control 官方文档](https://control.ros.org/jazzy/index.html) · Jazzy · 已读取官方或维护者页面

- [DiffBot 差速底盘官方示例](https://control.ros.org/jazzy/doc/ros2_control_demos/example_2/doc/userdoc.html) · Jazzy · 已读取官方或维护者页面

- [diff_drive_controller 参数与接口](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html) · Jazzy · 已读取官方或维护者页面

- [joint_trajectory_controller](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html) · Jazzy · 已读取官方或维护者页面

- [编写 ros2_control 硬件组件](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/writing_new_hardware_component.html) · Jazzy · 已读取官方或维护者页面

- [Controller Manager](https://control.ros.org/jazzy/doc/ros2_control/controller_manager/doc/userdoc.html) · Jazzy · 已读取官方或维护者页面

- [gz_ros2_control 源码](https://github.com/ros-controls/gz_ros2_control/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [Gazebo Harmonic 文档](https://gazebosim.org/docs/harmonic/) · Harmonic · 已读取官方或维护者页面

- [Gazebo 与 ROS 版本配对](https://gazebosim.org/docs/harmonic/ros_installation/) · 多版本 · 已读取官方或维护者页面

- [ros_gz Jazzy 源码](https://github.com/gazebosim/ros_gz/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [geometry2／tf2 Jazzy 源码](https://github.com/ros2/geometry2/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [URDF 官方教程源码](https://github.com/ros/urdf_tutorial/tree/ros2) · ROS 2 · 已读取官方或维护者页面

- [robot_state_publisher 源码](https://github.com/ros/robot_state_publisher/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [RViz2 源码与说明](https://github.com/ros2/rviz/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [Xacro 项目](https://github.com/ros/xacro) · 多版本 · 已读取官方或维护者页面

- [slam_toolbox Jazzy 源码与指南](https://github.com/SteveMacenski/slam_toolbox/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [robot_localization 项目](https://github.com/cra-ros-pkg/robot_localization) · 多版本 · 已读取官方或维护者页面

- [image_pipeline Jazzy 源码](https://github.com/ros-perception/image_pipeline/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [vision_opencv／cv_bridge](https://github.com/ros-perception/vision_opencv) · 多版本 · 已读取官方或维护者页面

- [perception_pcl 项目](https://github.com/ros-perception/perception_pcl) · 多版本 · 已读取官方或维护者页面

- [image_common／image_transport](https://github.com/ros-perception/image_common) · 多版本 · 已读取官方或维护者页面

- [image_transport 教程源码](https://github.com/ros-perception/image_transport_tutorials) · 多版本 · 已读取官方或维护者页面

- [micro-ROS 官方新站](https://micro.vulcanexus.org/) · 多版本 · 已读取官方或维护者页面

- [micro-ROS Linux 首个应用](https://micro.vulcanexus.org/docs/tutorials/core/first_application_linux/) · Humble 示例 · 已读取官方或维护者页面

- [micro_ros_setup Jazzy](https://github.com/micro-ROS/micro_ros_setup/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [micro-ROS Agent Jazzy](https://github.com/micro-ROS/micro-ROS-Agent/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [SROS2 Jazzy](https://github.com/ros2/sros2/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [rosbag2 Jazzy 源码与使用说明](https://github.com/ros2/rosbag2/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [MCAP 官方指南](https://mcap.dev/guides) · 格式与 SDK · 已读取官方或维护者页面

- [Foxglove Bridge 文档](https://docs.foxglove.dev/docs/fleet/bridge) · 滚动文档 · 已读取官方或维护者页面

- [rmw_zenoh Jazzy](https://github.com/ros2/rmw_zenoh/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [Fast DDS 维护者文档](https://fast-dds.docs.eprosima.com/en/latest/) · 最新上游 · 已读取官方或维护者页面

- [Cyclone DDS 维护者文档](https://cyclonedds.io/docs/cyclonedds/latest/) · 最新上游 · 已读取官方或维护者页面

- [Open-RMF 主仓库](https://github.com/open-rmf/rmf) · 多版本 · 已读取官方或维护者页面

- [Open-RMF 演示工程](https://github.com/open-rmf/rmf_demos) · 多版本 · 已读取官方或维护者页面

- [NVIDIA Isaac ROS](https://nvidia-isaac-ros.github.io/) · 供应商版本 · 已读取官方或维护者页面

- [Isaac ROS 计算平台配置](https://nvidia-isaac-ros.github.io/getting_started/compute/index.html) · 供应商版本 · 已读取官方或维护者页面

- [Isaac Sim ROS 2 教程](https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/index.html) · 供应商版本 · 已读取官方或维护者页面

- [TurtleBot3 官方手册](https://emanual.robotis.com/docs/en/platform/turtlebot3/quick-start/) · 多版本 · 已读取官方或维护者页面

- [MoveIt 2 教程总览](https://moveit.picknik.ai/main/index.html) · Rolling 文档 · 已读取官方或维护者页面

- [MoveIt 2 入门环境](https://moveit.picknik.ai/main/doc/tutorials/getting_started/getting_started.html) · 多版本指导 · 已读取官方或维护者页面

- [MoveIt 2 Jazzy 源码](https://github.com/moveit/moveit2/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [MoveIt Servo 教程](https://moveit.picknik.ai/main/doc/examples/realtime_servo/realtime_servo_tutorial.html) · Rolling 文档 · 已读取官方或维护者页面

- [MoveIt Task Constructor 抓放教程](https://moveit.picknik.ai/main/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.html) · Rolling 文档 · 已读取官方或维护者页面

- [rosbridge_suite ROS 2](https://github.com/RobotWebTools/rosbridge_suite/tree/ros2) · ROS 2 · 已读取官方或维护者页面

- [ROS diagnostics 项目](https://github.com/ros/diagnostics/tree/ros2) · ROS 2 · 已读取官方或维护者页面

- [ros2_tracing Jazzy](https://github.com/ros2/ros2_tracing/tree/jazzy) · Jazzy · 已读取官方或维护者页面

- [ROS Jazzy 发行清单](https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml) · Jazzy · 已读取官方或维护者页面

- [ros2_control 本地固定提交](https://github.com/ros-controls/ros2_control/tree/f9e24287fc1d6996e5ba1656a9ee24e5f33adef7) · jazzy · 本地 Git 与源码核对；未执行联网逐文件抓取

- [ros2_controllers 本地固定提交](https://github.com/ros-controls/ros2_controllers/tree/bee185cbb98815116af9cfb00ff595b0b800e91a) · jazzy · 本地 Git 与源码核对；未执行联网逐文件抓取

- [ros2_control_demos 本地固定提交](https://github.com/ros-controls/ros2_control_demos/tree/fbab026e147824971c97996f3789f97c2ee9e9ac) · jazzy · 本地 Git 与源码核对；未执行联网逐文件抓取

- [AgroSenseBot 本地固定提交](https://github.com/AIRLab-POLIMI/AgroSenseBot/tree/4ad700b090b9f3ddb8513c7519938bd7f0974709) · jazzy · 本地 Git 与源码核对；未执行联网逐文件抓取

- [bunker_ros2 本地固定提交](https://github.com/agilexrobotics/bunker_ros2/tree/f24f722b245eb1d2572c47d091fc847d9fd68cf4) · jazzy · 本地 Git 与源码核对；未执行联网逐文件抓取

- [linorobot2 本地固定提交](https://github.com/linorobot/linorobot2/tree/f6b0bd0350c4a9d6b815ef4bb5c701a1e5129711) · jazzy · 本地 Git 与源码核对；未执行联网逐文件抓取

- [linorobot2_hardware 本地固定提交](https://github.com/linorobot/linorobot2_hardware/tree/fbbbb922f4bd778e23268210b7bd7a6ac4c75d83) · jazzy · 本地 Git 与源码核对；未执行联网逐文件抓取

- [ugv_sdk 本地固定提交](https://github.com/agilexrobotics/ugv_sdk/tree/f2704eacdc90357078cd93ec60aae08bb4baab35) · main · 本地 Git 与源码核对；未执行联网逐文件抓取

- [ROS2 完全教程 · zsc](https://zsc.github.io/ros2_tutorial/) · Humble / Jazzy 混合 · 页面及本地源码核对

- [ROS2 理论与实践 · 核心篇](https://rzl6.github.io/ROS2_Tuition/) · Humble / Ubuntu 22.04 · 页面及本地源码核对

- [动手学 ROS 2 · 鱼香 ROS](https://fishros.com/d2lros2/) · 多版本，按章节辨认 · 入口与作者仓库核对

- [Articulated Robotics · 移动机器人实作](https://articulatedrobotics.xyz/tutorials/) · 多版本 · 作者目录核对

- [Automatic Addison · ROS 2 教程目录](https://automaticaddison.com/tutorials/) · Jazzy / Lyrical / Iron 分区 · 作者目录核对

- [Murilo’s ROS2 Tutorial](https://ros2-tutorial.readthedocs.io/en/latest/) · Jazzy / Ubuntu 24.04 · 教程首页核对

- [Intelligent Systems Lab · ROS 2 Examples](https://github.com/IntelligentSystemsLabUTV/ros2-examples/tree/jazzy) · Jazzy 分支 · Jazzy分支README核对

- [官方 ROS 1 → ROS 2 迁移指南](https://docs.ros.org/en/jazzy/How-To-Guides/Migrating-from-ROS1.html) · Jazzy · 官方 Jazzy 源文件核对

- [ros1_bridge 官方仓库与平台支持](https://github.com/ros2/ros1_bridge) · 按 Ubuntu / ROS 组合核对 · 官方 README 核对

- [OSRF Docker Images](https://github.com/osrf/docker_images) · 按镜像标签选择 Jazzy · 维护者仓库核对

- [Gymnasium 环境 API](https://gymnasium.farama.org/api/env/) · Gymnasium，独立于 ROS 发行版 · 2026-11-06 维护者或作者页面核对；教材实验为原创

- [Isaac Lab 官方文档](https://isaac-sim.github.io/IsaacLab/main/index.html) · main；实施时固定版本 · 2026-11-06 维护者或作者页面核对；教材实验为原创

- [RAI 维护者仓库](https://github.com/RobotecAI/rai) · 项目独立版本 · 2026-11-06 维护者或作者页面核对；教材实验为原创

- [Code as Policies 作者项目页](https://code-as-policies.github.io/) · 研究方法，非 Jazzy 安装教程 · 2026-11-06 维护者或作者页面核对；教材实验为原创

- [ACT 作者实现](https://github.com/tonyzhaozh/act) · 研究实现，独立依赖 · 2026-11-06 维护者或作者页面核对；教材实验为原创

- [Diffusion Policy 作者项目页](https://diffusion-policy.cs.columbia.edu/) · 研究实现，独立依赖 · 2026-11-06 维护者或作者页面核对；教材实验为原创

- [DVC 数据流水线文档](https://doc.dvc.org/user-guide/pipelines) · 独立工具版本 · 2026-11-06 维护者或作者页面核对；教材实验为原创

## 两套教程与本书的主题对应关系

- 课程简介 → ROS 2 的分层与通信选型 · [原出处](https://rzl6.github.io/ROS2_Tuition/index.html)

- 1.1.1 ROS2发展历程 → ROS 2 的分层与通信选型 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/11-ros2jian-jie/111-ros2fa-zhan-li-cheng.html)

- 1.1 ROS2简介 → ROS 2 的分层与通信选型 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/11-ros2jian-jie.html)

- 1.1.2 ROS2组成体系 → ROS 2 的分层与通信选型 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/11-ros2jian-jie/112-ros2zu-cheng-ti-xi.html)

- 1.1.3 ROS2优势 → ROS 2 的分层与通信选型 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/11-ros2jian-jie/113-ros2you-shi.html)

- 第1章 ROS2概述与环境搭建 → ROS 2 的分层与通信选型 / 环境安装与第一条跨语言通信 / 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1.html)

- 1.2.1 安装ROS2 → 环境安装与第一条跨语言通信 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/12-ros2an-zhuang/121-an-zhuang-ros2.html)

- 1.2 ROS2安装 → 环境安装与第一条跨语言通信 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/12-ros2an-zhuang.html)

- 1.2.2 测试ROS2 → 环境安装与第一条跨语言通信 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/12-ros2an-zhuang/122-ce-shi-ros2.html)

- 1.2.3 安装colcon构建工具 → 环境安装与第一条跨语言通信 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/12-ros2an-zhuang/123-an-zhuang-ros2-gou-jian-gong-ju.html)

- 1.3.1 案例简介 → 工作空间、包、ament 与 colcon / C++ / Python 发布订阅与回调写法 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/13-ros2kuai-su-ti-yan/131.html)

- 1.3.2 HelloWorld（C++） → 工作空间、包、ament 与 colcon / C++ / Python 发布订阅与回调写法 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/13-ros2kuai-su-ti-yan/131-helloworldcshi-73b029.html)

- 1.3 ROS2快速体验 → 工作空间、包、ament 与 colcon / C++ / Python 发布订阅与回调写法 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/13-ros2kuai-su-ti-yan.html)

- 1.3.3 HelloWorld（Python） → 工作空间、包、ament 与 colcon / C++ / Python 发布订阅与回调写法 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/13-ros2kuai-su-ti-yan/132-helloworldpythonshi-73b029.html)

- 1.3.4 运行优化 → 工作空间、包、ament 与 colcon / C++ / Python 发布订阅与回调写法 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/13-ros2kuai-su-ti-yan/134-yun-xing-you-hua.html)

- 1.4.1 安装VSCode → 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/14-ros2ji-cheng-kai-fa-huan-jing-da-jian/141-an-zhuang-vscode.html)

- 1.4.2 安装终端 → 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/14-ros2ji-cheng-kai-fa-huan-jing-da-jian/142-an-zhuang-zhong-duan.html)

- 1.4 ROS2集成开发环境搭建 → 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/14-ros2ji-cheng-kai-fa-huan-jing-da-jian.html)

- 1.4.3 安装git → 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/14-ros2ji-cheng-kai-fa-huan-jing-da-jian/143-an-zhuang-git.html)

- 1.5.1 ROS2文件系统 → ROS 2 的分层与通信选型 / 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/15-ros2ti-xi-kuang-jia/151-ros2wen-jian-xi-tong.html)

- 1.5 ROS2体系框架 → ROS 2 的分层与通信选型 / 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/15-ros2ti-xi-kuang-jia.html)

- 1.5.2 ROS2核心模块 → ROS 2 的分层与通信选型 / 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/15-ros2ti-xi-kuang-jia/153-xue-xi-mo-kuai.html)

- 1.5.3 ROS2技术支持 → ROS 2 的分层与通信选型 / 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/15-ros2ti-xi-kuang-jia/153-ros2jie-shu-zhi-chi.html)

- 1.5.4 ROS2应用方向 → ROS 2 的分层与通信选型 / 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/15-ros2ti-xi-kuang-jia/154-ros2jie-mei-zu-zhi.html)

- 1.6 本章小结 → ROS 2 的分层与通信选型 · [原出处](https://rzl6.github.io/ROS2_Tuition/chapter1/16-ben-zhang-xiao-jie.html)

- 2.1 通信机制简介 → 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/21-jie-kou-xiao-xi.html)

- 2.2 话题通信 → C++ / Python 发布订阅与回调写法 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/22-hua-ti-tong-xin.html)

- 第2章 ROS2通信机制核心 → C++ / Python 发布订阅与回调写法 / 服务调用、Future 与超时 / 动作：目标、反馈、结果与取消 / 参数、YAML 与动态配置 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin.html)

- 2.2.1 案例以及案例分析 → C++ / Python 发布订阅与回调写法 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/22-hua-ti-tong-xin/221-hua-ti-tong-xin-an-li-fen-xi.html)

- 2.2.2 话题通信之原生消息（C++） → C++ / Python 发布订阅与回调写法 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/22-hua-ti-tong-xin/222-hua-ti-tong-xin-c-shi-73b028-yuan-sheng-xiao-606f29.html)

- 2.2.3 话题通信之原生消息（Python） → C++ / Python 发布订阅与回调写法 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/22-hua-ti-tong-xin/223-hua-ti-tong-xin-python-shi-73b028-yuan-sheng-xiao-606f29.html)

- 2.2.4 话题通信自定义接口消息 → C++ / Python 发布订阅与回调写法 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/22-hua-ti-tong-xin/222-hua-ti-tong-xin-jie-kou-xiao-xi.html)

- 2.2.5 话题通信之自定义消息（C++） → C++ / Python 发布订阅与回调写法 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/22-hua-ti-tong-xin/223-hua-ti-tong-xin-c-shi-xian.html)

- 2.2.6 话题通信之自定义消息（Python） → C++ / Python 发布订阅与回调写法 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/22-hua-ti-tong-xin/224-hua-ti-tong-xin-python-shi-xian.html)

- 2.3 服务通信 → 服务调用、Future 与超时 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/23-fu-wu-tong-xin.html)

- 2.3.1 案例以及案例分析 → 服务调用、Future 与超时 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/23-fu-wu-tong-xin/231-fu-wu-tong-xin-li-lun-mo-xing.html)

- 2.3.2 服务通信接口消息 → 服务调用、Future 与超时 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/23-fu-wu-tong-xin/232-hua-ti-tong-xin-jie-kou-xiao-xi.html)

- 2.3.3 服务通信（C++） → 服务调用、Future 与超时 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/23-fu-wu-tong-xin/233-fu-wu-tong-xin-c-shi-xian.html)

- 2.3.4 服务通信（Python） → 服务调用、Future 与超时 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/23-fu-wu-tong-xin/234-fu-wu-tong-xin-python-shi-xian.html)

- 2.4 动作通信 → 动作：目标、反馈、结果与取消 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/24-dong-zuo-tong-xin.html)

- 2.4.1 案例以及案例分析 → 动作：目标、反馈、结果与取消 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/24-dong-zuo-tong-xin/241-dong-zuo-tong-xin-li-lun-mo-xing.html)

- 2.4.2 动作通信接口消息 → 动作：目标、反馈、结果与取消 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/24-dong-zuo-tong-xin/242-dong-zuo-tong-xin-jie-kou-xiao-xi.html)

- 2.4.3 动作通信（C++） → 动作：目标、反馈、结果与取消 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/24-dong-zuo-tong-xin/243-dong-zuo-tong-xin-c-shi-xian.html)

- 2.4.4 动作通信（Python） → 动作：目标、反馈、结果与取消 / 自定义消息、服务与动作接口包 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/24-dong-zuo-tong-xin/244-dong-zuo-tong-xin-python-shi-xian.html)

- 2.5 参数服务 → 参数、YAML 与动态配置 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/25-can-shu-fu-wu.html)

- 2.5.1 案例以及案例分析 → 参数、YAML 与动态配置 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/25-can-shu-fu-wu/251-can-shu-fu-wu-li-lun-mo-xing.html)

- 2.5.2 参数数据类型 → 参数、YAML 与动态配置 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/25-can-shu-fu-wu/252-can-shu-shu-ju-lei-xing.html)

- 2.5.3 参数服务（C++） → 参数、YAML 与动态配置 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/25-can-shu-fu-wu/253-can-shu-fu-wu-c-shi-xian.html)

- 2.5.4 参数服务（Python） → 参数、YAML 与动态配置 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/25-can-shu-fu-wu/254-can-shu-fu-wu-python-shi-xian.html)

- 2.6 本章小结 → C++ / Python 发布订阅与回调写法 / 服务调用、Future 与超时 / 动作：目标、反馈、结果与取消 / 参数、YAML 与动态配置 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-2-zhang-ros2-tong-xin-ji-zhi-he-xin/28-ben-zhang-xiao-jie.html)

- 3.1 分布式 → DDS、RMW、多机发现与隔离 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/31-fen-bu-shi.html)

- 3.2 工作空间覆盖 → 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/32-gong-zuo-kong-jian-fu-gai.html)

- 第3章 ROS2通信机制补充 → 用 CLI 读懂运行中的系统 / DDS、RMW、多机发现与隔离 / 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong.html)

- 3.3 元功能包 → 工作空间、包、ament 与 colcon · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/33-yuan-gong-neng-bao.html)

- 3.4 节点重名 → 用 CLI 读懂运行中的系统 / Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/34-jie-dian-zhong-ming.html)

- 3.4.1 ros2 run设置节点名称 → 用 CLI 读懂运行中的系统 / Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/34-jie-dian-zhong-ming/341-rou-si.html)

- 3.4.2 launch文件设置节点名称 → 用 CLI 读懂运行中的系统 / Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/34-jie-dian-zhong-ming/342-launch-wen-jian-jie-jue-jie-dian-zhong-ming-wen-ti.html)

- 3.4.3 编码设置节点名称 → 用 CLI 读懂运行中的系统 / Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/34-jie-dian-zhong-ming/343-bian-ma-jie-jue-jie-dian-zhong-ming-wen-ti.html)

- 3.5 话题重名 → 用 CLI 读懂运行中的系统 / Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/35-hua-ti-zhong-ming.html)

- 3.5.1 ros2 run设置话题名称 → 用 CLI 读懂运行中的系统 / Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/35-hua-ti-zhong-ming/351-ros2-run-xiu-gai-hua-ti-ming-cheng.html)

- 3.5.2 launch文件设置话题名称 → 用 CLI 读懂运行中的系统 / Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/35-hua-ti-zhong-ming/352-launch-wen-jian-xiu-gai-hua-ti-ming-cheng.html)

- 3.5.3 编码设置话题名称 → 用 CLI 读懂运行中的系统 / Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/35-hua-ti-zhong-ming/353-bian-ma-she-zhi-hua-ti-ming-cheng.html)

- 3.6 时间相关API → ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/36-chang-yong-api.html)

- 3.6.1 Rate → ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/36-chang-yong-api/361-rate.html)

- 3.6.2 Time → ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/36-chang-yong-api/362-time.html)

- 3.6.3 Duration → ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/36-chang-yong-api/363-duration.html)

- 3.6.4 Time 与 Duration 运算 → ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/36-chang-yong-api/364-time-yu-duration-yun-suan.html)

- 3.7 通信机制工具 → 用 CLI 读懂运行中的系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/37-tong-xin-ji-zhi-ming-ling.html)

- 3.7.1 命令工具 → 用 CLI 读懂运行中的系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/37-tong-xin-ji-zhi-ming-ling/371-ming-ling-gong-ju.html)

- 3.7.2 rqt工具箱 → 用 CLI 读懂运行中的系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/37-tong-xin-ji-zhi-ming-ling/372-rqtgong-ju-xiang.html)

- 3.8 通信机制实操 → C++ / Python 发布订阅与回调写法 / 服务调用、Future 与超时 / 动作：目标、反馈、结果与取消 / 参数、YAML 与动态配置 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/38-tong-xin-ji-zhi-lian-xi.html)

- 3.8.1 话题通信案例分析 → C++ / Python 发布订阅与回调写法 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/38-tong-xin-ji-zhi-lian-xi/381-hua-ti-tong-xin-lian-xi.html)

- 3.8.2 话题通信实现 → C++ / Python 发布订阅与回调写法 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/38-tong-xin-ji-zhi-lian-xi/382-fu-wu-tong-xin-lian-xi.html)

- 3.8.3 服务通信案例分析 → 服务调用、Future 与超时 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/38-tong-xin-ji-zhi-lian-xi/383-dong-zuo-tong-xin-lian-xi.html)

- 3.8.4 服务通信实现 → 服务调用、Future 与超时 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/38-tong-xin-ji-zhi-lian-xi/384-can-shu-fu-wu-lian-xi.html)

- 3.8.5 动作通信案例分析 → 动作：目标、反馈、结果与取消 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/38-tong-xin-ji-zhi-lian-xi/385-dong-zuo-tong-xin-an-li-fen-xi.html)

- 3.8.6 动作通信实现 → 动作：目标、反馈、结果与取消 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/38-tong-xin-ji-zhi-lian-xi/386-dong-zuo-tong-xin-shi-xian.html)

- 3.8.7 参数服务案例分析 → 服务调用、Future 与超时 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/38-tong-xin-ji-zhi-lian-xi/387-can-shu-fu-wu-an-li-fen-xi.html)

- 3.8.8 参数服务实现 → 服务调用、Future 与超时 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/38-tong-xin-ji-zhi-lian-xi/388-can-shu-fu-wu-shi-xian.html)

- 3.9 本章小结 → 用 CLI 读懂运行中的系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-3-zhang-ros2-tong-xin-ji-zhi-bu-chong/39-ben-zhang-xiao-jie.html)

- 4.1 启动文件launch简介 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/41-launch-jian-jie.html)

- 4.1.1 launch 基本使用流程 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/41-launch-jian-jie/411-launch-ji-ben-shi-yong-liu-cheng.html)

- 4.2 launch之Python实现 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/42-launchzhi-python-shi-xian.html)

- 4.2.1 节点设置 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/42-launchzhi-python-shi-xian/421-jie-dian-she-zhi.html)

- 4.2.2 执行指令 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/42-launchzhi-python-shi-xian/422-zhi-xing-ming-ling.html)

- 第4章 ROS2工具之launch与rosbag2 → Python / XML / YAML 启动系统 / ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt.html)

- 4.2.3 参数设置 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/42-launchzhi-python-shi-xian/424-wen-jian-bao-han.html)

- 4.2.4 文件包含 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/42-launchzhi-python-shi-xian/425-wen-jian-bao-han.html)

- 4.2.5 分组设置 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/42-launchzhi-python-shi-xian/426-fen-zu-she-zhi.html)

- 4.2.6 添加事件 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/42-launchzhi-python-shi-xian/423-tian-jia-shi-jian.html)

- 4.3 launch之xml、yaml实现 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/43-launchzhi-xml-shi-xian.html)

- 4.3.1 节点设置 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/43-launchzhi-xml-shi-xian/431-jie-dian-she-zhi.html)

- 4.3.2 执行指令 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/43-launchzhi-xml-shi-xian/432-zhi-xing-zhi-ling.html)

- 4.3.3 参数设置 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/43-launchzhi-xml-shi-xian/433-can-shu-she-zhi.html)

- 4.3.4 文件包含 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/43-launchzhi-xml-shi-xian/434-wen-jian-bao-han.html)

- 4.3.5 分组设置 → Python / XML / YAML 启动系统 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/43-launchzhi-xml-shi-xian/435-fen-zu-she-zhi.html)

- 4.4.1 ros2 bag 命令工具 → ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/44-rosbag2/441-ros2-bag-ming-ling-gong-ju.html)

- 4.4 录制回放工具——rosbag2 → ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/44-rosbag2.html)

- 4.4.2 rosbag2 编程（C++） → ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/44-rosbag2/442-rosbag2-zhi-c-shi-xian.html)

- 4.4.3 rosbag2 编程（Python） → ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/44-rosbag2/443-rosbag2-zhi-python-shi-xian.html)

- 4.5 本章小结 → Python / XML / YAML 启动系统 / ROS 时间、录包与可重复实验 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-4-zhang-ros2-gong-ju-zhi-launch-rosbag2-yu-rqt/46-ben-zhang-xiao-jie.html)

- 5.1 坐标变换简介 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/51-zuo-biao-bian-huan-jian-jie.html)

- 5.1.1 案例安装以及运行 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/51-zuo-biao-bian-huan-jian-jie/511-an-li-an-zhuang-yi-ji-yun-xing.html)

- 5.2 坐标相关消息 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/52-zuo-biao-xiao-xi.html)

- 第5章 ROS2工具之坐标变换 → tf2：坐标树、时间戳与外参 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan.html)

- 5.3 坐标变换广播 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo.html)

- 5.3.1 坐标系广播案例以及分析 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo/531-jing-tai-zuo-biao-xi-guan-xi-guang-bo.html)

- 5.3.2 静态广播器（命令） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo/532-jing-tai-guang-bo-qi-ff08-ming-ling-ff09.html)

- 5.3.3 静态广播器（C++） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo/533-jing-tai-guang-bo-qi-ff08-c-++.html)

- 5.3.4 静态广播器（Python） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo/534-jing-tai-guang-bo-qi-ff08-python.html)

- 5.3.5 动态广播器（C++） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo/535-dong-tai-guang-bo-qi-ff08-c-++.html)

- 5.3.6 动态广播器（Python） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo/536-dong-tai-guang-bo-qi-ff08-python.html)

- 5.3.7 坐标点发布案例以及分析 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo/537-zuo-biao-dian-fa-bu-an-li-fen-xi.html)

- 5.3.8 坐标点发布（C++） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo/538-zuo-biao-dian-fa-bu-ff08-c-++.html)

- 5.3.9 坐标点发布（Python） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/53-zuo-biao-xi-guang-bo/539-zuo-biao-dian-fa-bu-ff08-python.html)

- 5.4 坐标变换监听 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/54-zuo-biao-xi-jian-ting.html)

- 5.4.1 坐标系变换案例以及分析 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/54-zuo-biao-xi-jian-ting/541-zuo-biao-xi-bian-huan.html)

- 5.4.2 坐标系变换（C++） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/54-zuo-biao-xi-jian-ting/542-zuo-biao-dian-bian-huan.html)

- 5.4.3 坐标系变换（Python） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/54-zuo-biao-xi-jian-ting/543-zuo-biao-xi-bian-huan-ff08-c-++.html)

- 5.4.4 坐标点变换（C++） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/54-zuo-biao-xi-jian-ting/544-zuo-biao-dian-bian-huan-ff08-c-++.html)

- 5.4.5 坐标点变换（Python） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/54-zuo-biao-xi-jian-ting/545-zuo-biao-dian-bian-huan-ff08-python.html)

- 5.5 坐标变换工具 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/55-tfgong-ju.html)

- 5.6 坐标变换实操 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/56-zuo-biao-bian-huan-shi-cao.html)

- 5.6.1 乌龟跟随案例以及分析 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/56-zuo-biao-bian-huan-shi-cao/561-wu-gui-gen-sui-an-li-yi-ji-an-li-fen-xi.html)

- 5.6.2 乌龟跟随实现（C++） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/56-zuo-biao-bian-huan-shi-cao/562-wu-gui-gen-sui-shi-xian-ff08-c-++.html)

- 5.6.3 乌龟跟随实现（Python） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/56-zuo-biao-bian-huan-shi-cao/563-wu-gui-gen-sui-shi-xian-ff08-python.html)

- 5.6.4 乌龟护航案例以及分析 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/56-zuo-biao-bian-huan-shi-cao/562-wu-gui-hu-hang-an-li-yi-ji-fen-xi.html)

- 5.6.5 乌龟护航实现（C++） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/56-zuo-biao-bian-huan-shi-cao/565-wu-gui-hu-hang-shi-xian-ff08-c-++.html)

- 5.6.6 乌龟护航实现（Python） → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/56-zuo-biao-bian-huan-shi-cao/566-wu-gui-hu-hang-shi-xian-ff08-python.html)

- 5.7 本章小结 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-5-zhang-ros2-gong-ju-zhi-zuo-biao-bian-huan/57-ben-zhang-xiao-jie.html)

- 6.1 可视化简介 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/61-gai-shu.html)

- 第6章 ROS2工具之可视化 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen.html)

- 6.2 rviz2 基本使用 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/62-rviz2-ji-ben-shi-yong.html)

- 6.3.1 案例以及案例分析 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/63-urdfji-cheng-rviz2-ji-ben-liu-cheng/631-an-li-yi-ji-an-li-fen-xi.html)

- 6.3.2 案例实现 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/63-urdfji-cheng-rviz2-ji-ben-liu-cheng/632-an-li-shi-xian.html)

- 6.3 rviz2集成URDF基本流程 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/63-urdfji-cheng-rviz2-ji-ben-liu-cheng.html)

- 6.4 URDF使用语法 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/64-urdfyu-fa.html)

- 6.4.1 URDF语法01_robot → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/64-urdfyu-fa/641-urdfyu-fa-01-robot.html)

- 6.4.2 URDF语法02_link → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/64-urdfyu-fa/642-urdfyu-fa-02-link.html)

- 6.4.3 URDF语法03_joint → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/64-urdfyu-fa/643-urdfyu-fa-03-joint.html)

- 6.4.4 URDF练习 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/64-urdfyu-fa/644-urdflian-xi.html)

- 6.4.5 URDF工具 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/64-urdfyu-fa/645-urdfgong-ju.html)

- 6.5 URDF优化_xacro → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/65-urdfyou-hua-xacro.html)

- 6.5.1 xacro_快速体验 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/65-urdfyou-hua-xacro/651-xacrokuai-su-ti-yan.html)

- 6.5.2 xacro_使用语法 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/65-urdfyou-hua-xacro/652-xacroshi-yong-yu-fa.html)

- 6.5.3 xacro_练习 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/65-urdfyou-hua-xacro/653-xacroshi-yong-shi-li.html)

- 6.6 本章小结 → URDF、Xacro 与 RViz：把机器人描述变成可检查模型 · [原出处](https://rzl6.github.io/ROS2_Tuition/di-6-zhang-ros2-ji-qi-ren-jian-mo-yu-fang-zhen/66-ben-zhang-xiao-jie.html)

- 第 1 章：ROS1 核心概念回顾 → ROS 2 的分层与通信选型 / 迁移与版本边界：ROS 1、Humble 与 Jazzy · [原出处](https://zsc.github.io/ros2_tutorial/chapter1.html)

- 第 2 章：ROS1 的局限性分析 → ROS 2 的分层与通信选型 / DDS、RMW、多机发现与隔离 · [原出处](https://zsc.github.io/ros2_tutorial/chapter2.html)

- 第 3 章：从 ROS1 到 ROS2 的迁移策略 → 迁移与版本边界：ROS 1、Humble 与 Jazzy · [原出处](https://zsc.github.io/ros2_tutorial/chapter3.html)

- 第 4 章：ROS2 架构与设计理念 → ROS 2 的分层与通信选型 · [原出处](https://zsc.github.io/ros2_tutorial/chapter4.html)

- 第 5 章：节点与执行器模型 → 执行器、回调组与并发边界 / 生命周期节点与启动顺序 / 组件化、独立进程与进程内通信 · [原出处](https://zsc.github.io/ros2_tutorial/chapter5.html)

- 第 6 章：通信机制深度解析 → C++ / Python 发布订阅与回调写法 / 服务调用、Future 与超时 / 动作：目标、反馈、结果与取消 / QoS：能发现不等于能通信 · [原出处](https://zsc.github.io/ros2_tutorial/chapter6.html)

- 第 7 章：Launch 系统与配置管理 → Python / XML / YAML 启动系统 / 参数、YAML 与动态配置 · [原出处](https://zsc.github.io/ros2_tutorial/chapter7.html)

- 第 8 章：tf2 坐标变换框架 → tf2：坐标树、时间戳与外参 / tf2：建立一致的坐标与时间关系 · [原出处](https://zsc.github.io/ros2_tutorial/chapter8.html)

- 第 9 章：时间同步与回放系统 → ROS 时间、录包与可重复实验 · [原出处](https://zsc.github.io/ros2_tutorial/chapter9.html)

- 第 10 章：传感器数据处理管道 → 感知管线：图像、深度、点云与时间同步 · [原出处](https://zsc.github.io/ros2_tutorial/chapter10.html)

- 第 11 章：SLAM 与定位系统 → 二维 SLAM：从传感器数据到可复用地图 / 状态估计：轮速、IMU、GNSS 与定位坐标系 · [原出处](https://zsc.github.io/ros2_tutorial/chapter11.html)

- 第 12 章：导航栈 Nav2 → Nav2：从给定目标到可解释的导航行为 / 导航任务编排：行为树与 Python Commander · [原出处](https://zsc.github.io/ros2_tutorial/chapter12.html)

- 第 13 章：ros2_control 框架 → ros2_control：读懂从命令到硬件的闭环 / 实机接入：标准硬件接口与厂商 SDK 两条路线 · [原出处](https://zsc.github.io/ros2_tutorial/chapter13.html)

- 第 14 章：MoveIt2 运动规划 → MoveIt 2：规划场景、运动规划与轨迹执行 / 机械臂进阶：Servo 与 Task Constructor · [原出处](https://zsc.github.io/ros2_tutorial/chapter14.html)

- 第 15 章：实时系统与性能优化 → 性能分析、Tracing 与实时边界 · [原出处](https://zsc.github.io/ros2_tutorial/chapter15.html)

- 第 16 章：安全性与诊断系统 → SROS2：身份、加密与权限 / 数据与诊断：rosbag2、MCAP、Foxglove 与 tracing · [原出处](https://zsc.github.io/ros2_tutorial/chapter16.html)

- 第 17 章：仿真集成（Gazebo/Ignition） → Gazebo Harmonic：仿真、桥接与统一时钟 · [原出处](https://zsc.github.io/ros2_tutorial/chapter17.html)

- 第 18 章：多机器人系统 → 多机器人：命名、隔离与 Open-RMF 任务协调 · [原出处](https://zsc.github.io/ros2_tutorial/chapter18.html)

- 第 19 章：计算机视觉与深度学习 → 感知管线：图像、深度、点云与时间同步 / GPU 感知与 AI 仿真：Isaac ROS、Isaac Sim 的接入边界 · [原出处](https://zsc.github.io/ros2_tutorial/chapter19.html)

- 第 20 章：机器人强化学习 → 强化学习与 Sim2Real：从策略实验到 ROS 2 接口 · [原出处](https://zsc.github.io/ros2_tutorial/chapter20.html)

- 第 21 章：大语言模型与具身智能 → 语言模型与具身任务：结构化计划、技能与反馈 · [原出处](https://zsc.github.io/ros2_tutorial/chapter21.html)

- 第 22 章：神经网络运动控制 → 模仿学习与神经策略：数据、动作块与部署适配 · [原出处](https://zsc.github.io/ros2_tutorial/chapter22.html)
