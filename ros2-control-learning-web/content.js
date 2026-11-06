/* 原创中文教学说明；官方示例的精简改写见 THIRD_PARTY_NOTICES.md。 */
(function (root) {
  'use strict';
  const base = 'https://control.ros.org/jazzy/doc/';
  const commit = 'fbab026e147824971c97996f3789f97c2ee9e9ac';
  const github = `https://github.com/ros-controls/ros2_control_demos/blob/${commit}/`;
  const sources = {
    start:{title:'Getting Started · 官方架构与入门',url:base+'getting_started/getting_started.html'},
    manager:{title:'Controller Manager · 管理与控制循环',url:base+'ros2_control/controller_manager/doc/userdoc.html'},
    interfaces:{title:'Hardware Interface Types · 接口声明',url:base+'ros2_control/hardware_interface/doc/hardware_interface_types_userdoc.html'},
    components:{title:'Hardware Components · 硬件组件',url:base+'ros2_control/hardware_interface/doc/hardware_components_userdoc.html'},
    plugin:{title:'Writing a Hardware Component · 编写硬件插件',url:base+'ros2_control/hardware_interface/doc/writing_new_hardware_component.html'},
    cli:{title:'ros2 control CLI · 命令行工具',url:base+'ros2_control/ros2controlcli/doc/userdoc.html'},
    demos:{title:'Demos · 安装与官方示例',url:base+'ros2_control_demos/doc/index.html'},
    diffbot:{title:'Example 2 · DiffBot 差速底盘',url:base+'ros2_control_demos/example_2/doc/userdoc.html'},
    rrbot:{title:'Example 1 · RRBot 两关节机械臂',url:base+'ros2_control_demos/example_1/doc/userdoc.html'},
    diffdrive:{title:'diff_drive_controller · 差速控制器',url:base+'ros2_controllers/diff_drive_controller/doc/userdoc.html'},
    broadcaster:{title:'joint_state_broadcaster · 关节状态广播器',url:base+'ros2_controllers/joint_state_broadcaster/doc/userdoc.html'},
    lifecycle:{title:'Lifecycle of a Hardware Component · 硬件生命周期',url:base+'ros2_control/hardware_interface/doc/lifecycle_of_a_hardware_component.html'},
    transmission:{title:'Example 8 · 使用传动映射',url:base+'ros2_control_demos/example_8/doc/userdoc.html'},
    modular:{title:'Example 6 · 模块化执行器与状态接口',url:base+'ros2_control_demos/example_6/doc/userdoc.html'},
    launch:{title:'源码 · diffbot.launch.py（固定提交）',url:github+'example_2/bringup/launch/diffbot.launch.py'},
    yaml:{title:'源码 · diffbot_controllers.yaml（固定提交）',url:github+'example_2/bringup/config/diffbot_controllers.yaml'},
    xacro:{title:'源码 · diffbot.ros2_control.xacro（固定提交）',url:github+'example_2/description/ros2_control/diffbot.ros2_control.xacro'},
    hardware:{title:'源码 · diffbot_system.cpp（固定提交）',url:github+'example_2/hardware/diffbot_system.cpp'},
    rosinstall:{title:'ROS 2 Jazzy · Ubuntu 安装前提',url:'https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html'},
    rosbasics:{title:'ROS 2 Jazzy · 初学者命令行教程',url:'https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools.html'}
  };
  const lessons = [
    {id:'start',title:'从零开始',en:'Start here',time:'约 8 分钟',label:'学习起点',subtitle:'先知道它解决什么问题，再打开终端。',goals:['认清 ROS 2 与 ros2_control 的分工','认识节点、话题、关节与 URDF','准备独立的 Jazzy 练习环境'],sources:['start','demos','rosinstall','rosbasics']},
    {id:'architecture',title:'读懂系统架构',en:'Architecture',time:'约 12 分钟',label:'架构地图',subtitle:'从控制器到真实硬件，把每一层的职责连起来。',goals:['分清控制器与两个管理器','读懂状态接口和命令接口','建立完整的控制链路认知'],sources:['start','interfaces','components']},
    {id:'cycle',title:'跟随一个控制周期',en:'Read · Update · Write',time:'约 10 分钟',label:'控制循环',subtitle:'把静态的结构图，变成一次正在发生的控制过程。',goals:['按顺序解释 read → update → write','把车体速度换算为左右轮角速度','区分话题通信与内部数据接口'],sources:['manager','diffdrive','hardware']},
    {id:'files',title:'认识四类关键文件',en:'Four essential files',time:'约 15 分钟',label:'工程拼图',subtitle:'模型、配置、插件、启动文件，各自负责一件事。',goals:['认出每个文件的职责','追踪同一个关节名如何贯穿工程','找到官方示例里的真实文件'],sources:['interfaces','plugin','xacro','yaml','launch','hardware']},
    {id:'diffbot',title:'跑通 DiffBot 示例',en:'Your first DiffBot',time:'约 25 分钟',label:'动手实践',subtitle:'不用真实机器人，观察一条完整的演示控制链路。',goals:['在独立工作空间构建官方示例','通过 CLI 确认控制器与接口','发送带时间戳的速度命令并观察状态'],sources:['demos','diffbot','diffdrive','launch','yaml']},
    {id:'diagnose',title:'生命周期与排错',en:'Lifecycle & debugging',time:'约 15 分钟',label:'建立判断力',subtitle:'不靠反复重启，从能观察到的状态开始定位问题。',goals:['区分“加载”“配置”“激活”','按症状选择正确的检查命令','理解 claimed 和 open_loop 的边界'],sources:['lifecycle','manager','cli','diffdrive','yaml']},
    {id:'quiz',title:'检查你的理解',en:'Check your understanding',time:'约 6 分钟',label:'知识自测',subtitle:'用几个真实场景，看看你能否解释这条控制链路。',goals:['检验关键概念是否准确','通过反馈回到需要复习的课程','完成第一轮 ros2_control 入门'],sources:['start','diffbot','diffdrive']}
  ];
  const nodes = {
    controllers:{title:'控制器',en:'Controllers',tag:'做计算与发布',body:'控制器是按需加载的插件：接收目标、读取所需状态，再生成命令。广播器也由控制器管理器加载，但主要负责发布状态。',analogy:'像不同岗位的操作员：有人算轮速，有人管理轨迹，有人报告状态。',example:'diff_drive_controller / joint_state_broadcaster',lesson:'files',source:'start'},
    'controller-a':{title:'控制器 A',en:'Controller A',tag:'控制算法插件',body:'图中的 A 是一个通用控制器占位。以差速底盘为例，它可以是 diff_drive_controller：将车体前进与转向速度转换成左右轮速度。',analogy:'你说“向前走”，它算出两侧轮子各该转多快。',example:'diffbot_base_controller → 左右轮 velocity 命令',lesson:'diffbot',source:'diffdrive'},
    'controller-b':{title:'控制器 B',en:'Controller B',tag:'按机器人选择',body:'B 表示另一种控制器。机械臂可以使用轨迹控制器；不同控制器需要的接口不同，不能都去占用同一个命令接口。',analogy:'不同任务使用不同工具，但同一个执行目标需要明确的写入者。',example:'joint_trajectory_controller',lesson:'files',source:'start'},
    'controller-c':{title:'控制器 C',en:'Controller C',tag:'也可以是广播器',body:'C 可以用 joint_state_broadcaster 举例。它读取状态接口并发布 /joint_states；不生成驱动电机的目标命令。',analogy:'像仪表员，把关节测量值整理成外部能看到的消息。',example:'state interfaces → /joint_states',lesson:'diffbot',source:'broadcaster'},
    cm:{title:'控制器管理器',en:'Controller Manager',tag:'协调与调度',body:'加载、配置和切换控制器；为其匹配硬件接口，并调度 read → update → write 控制循环。常见入口进程是 ros2_control_node。',analogy:'像调度员：决定谁工作、使用哪些资源，以及何时开始下一轮。',example:'ros2 control list_controllers -c /controller_manager',lesson:'cycle',source:'manager'},
    rm:{title:'资源管理器',en:'Resource Manager',tag:'管理硬件资源',body:'使用 pluginlib 加载硬件组件，管理其生命周期，以及对外提供的状态接口和命令接口。控制器通过管理器获得这些接口的使用权。',analogy:'像设备管理员，知道有哪些设备、它们提供什么读写能力。',example:'DiffBotSystemHardware 提供左右轮的接口',lesson:'files',source:'start'},
    state:{title:'状态接口',en:'State Interface',tag:'反馈 · 对控制器只读',body:'保存硬件报告的当前数值，例如关节位置、速度或温度。控制器读取它；硬件插件在 read() 中更新它。接口本身不是 ROS 话题。',analogy:'“现在是多少？”——例如编码器测到当前轮子转角。',example:'left_wheel_joint/position · 单位 rad',lesson:'cycle',source:'interfaces'},
    command:{title:'命令接口',en:'Command Interface',tag:'目标 · 控制器写入',body:'控制器把目标值写入命令接口，硬件插件再读取并在 write() 中传给设备。命令接口的占用用于协调写入权；目标值不代表实际运动已完成。',analogy:'“希望变成多少？”——例如目标轮速 3 rad/s。',example:'left_wheel_joint/velocity [available] [claimed]',lesson:'diffbot',source:'interfaces'},
    sensor:{title:'传感器组件',en:'Sensor',tag:'硬件组件类型',body:'用来抽象独立传感器，主要提供状态接口，例如 IMU、力传感器或温度传感器。它属于硬件抽象层，不等于物理传感器本体。',analogy:'设备的翻译层，把原始测量转换成框架能读取的数值。',example:'IMU → orientation / angular_velocity',lesson:'files',source:'components'},
    system:{title:'系统组件',en:'System',tag:'硬件组件类型',body:'把多个关节或设备封装成一个整体，通过统一的通信通道一起读写。这里的 System 不是操作系统；DiffBot 的左右轮由一个 System 插件管理。',analogy:'一个控制盒同时管理机器人上的多台电机。',example:'<ros2_control name="DiffBot" type="system">',lesson:'files',source:'diffbot'},
    actuator:{title:'执行器组件',en:'Actuator',tag:'硬件组件类型 · 可读写',body:'抽象可独立通信的执行器，通常对应单自由度执行单元。它可以同时提供命令接口和状态接口；无法读取反馈的设备可省略读取。与 System 的差别在于组件边界和通信组织方式。',analogy:'一台可接收目标位置、也能报告当前转角的智能电机；有些简单设备只能接收命令。',example:'Example 6：actuator 同时声明 position 命令与状态接口',lesson:'files',source:'modular'},
    transmission:{title:'传动映射',en:'Transmissions',tag:'可选关系',body:'描述执行器空间与关节空间之间的映射，例如减速比造成的角度、速度和力矩换算。需要时由实现使用，不是所有机器人都必须增加的一层。',analogy:'电机转了多圈，经过减速器后关节可能只转一圈。',example:'Example 8 · 使用 transmissions',lesson:'files',source:'transmission'},
    hardware:{title:'物理硬件资源',en:'Hardware Resources',tag:'真实设备 / 演示设备',body:'机器人最终的传感器、电机、驱动器或控制盒。硬件组件负责与它们通信；官方入门演示用软件数值代替真实设备通信。',analogy:'控制链路最下面，是真正测量与运动发生的地方。',example:'编码器、驱动器、电机；演示中也可使用 mock',lesson:'diffbot',source:'diffbot'}
  };
  const terms = [
    ...Object.entries(nodes).map(([id,n])=>({id,title:n.title,en:n.en,description:n.body,lesson:n.lesson})),
    {title:'节点',en:'Node',description:'执行 ROS 2 任务的基本单元，可发布/订阅消息并提供服务。一个进程可包含多个节点。',lesson:'start'},
    {title:'话题',en:'Topic',description:'发布者和订阅者之间的命名消息通道，例如 /cmd_vel。消息类型需要匹配。',lesson:'start'},
    {title:'关节',en:'Joint',description:'连接机器人 link 的运动关系，也常作为状态与命令接口的命名前缀。',lesson:'start'},
    {title:'机器人描述',en:'URDF / Xacro',description:'URDF 描述机器人结构；Xacro 用宏与参数组织 URDF，生成后仍是 XML。',lesson:'files'},
    {title:'状态广播器',en:'joint_state_broadcaster',description:'读取状态接口，将关节运动状态发布到 /joint_states 等话题。',lesson:'diffbot'},
    {title:'接口已占用',en:'claimed',description:'命令接口已被控制器申请使用；不是设备正在运动的证明。',lesson:'diagnose'},
    {title:'激活',en:'active',description:'组件或控制器进入工作的生命周期状态。硬件与控制器需分别检查。',lesson:'diagnose'},
    {title:'开环里程计',en:'open_loop',description:'diff_drive_controller 的 open_loop=true 使用目标速度计算里程计，而非硬件位置或速度反馈。',lesson:'diagnose'},
    {title:'带时间戳的速度',en:'TwistStamped',description:'header 加 twist，记录命令时间戳。Jazzy 差速控制器使用此消息类型。',lesson:'diffbot'},
    {title:'可视化工具',en:'RViz',description:'显示模型、状态与坐标变换；它本身不负责物理仿真，也不是电机驱动。',lesson:'start'}
  ];
  const snippets = {
    prerequisites:{title:'准备练习工具',lang:'bash',source:'demos',note:'前提：Ubuntu 24.04 已正确安装 ROS 2 Jazzy。已有工具无需重复安装；rosdep 尚未初始化时，先执行一次 sudo rosdep init。',code:'source /opt/ros/jazzy/setup.bash\nsudo apt update\nsudo apt install ros-jazzy-ros2-control ros-jazzy-ros2-controllers \\\n  python3-colcon-common-extensions python3-rosdep git'},
    setup:{title:'新建独立工作空间并构建 DiffBot',lang:'bash',source:'demos',note:'在新工作空间操作，不要在这个参考源码集合的根目录直接编译全部项目。克隆 jazzy 分支，依赖也使用 Jazzy；构建耗时取决于电脑。',code:'source /opt/ros/jazzy/setup.bash\nmkdir -p ~/ros2_control_ws/src\ncd ~/ros2_control_ws/src\ngit clone --branch jazzy --depth 1 https://github.com/ros-controls/ros2_control_demos.git\ncd ~/ros2_control_ws\nrosdep update --rosdistro=jazzy\nrosdep install --from-paths src --ignore-src --rosdistro jazzy -r -y\ncolcon build --symlink-install --packages-up-to ros2_control_demo_example_2\nsource install/setup.bash'},
    source:{title:'每个新终端都加载环境',lang:'bash',source:'demos',code:'source /opt/ros/jazzy/setup.bash\nsource ~/ros2_control_ws/install/setup.bash'},
    launch:{title:'终端 A · 启动完整控制示例',lang:'bash',source:'diffbot',code:'ros2 launch ros2_control_demo_example_2 diffbot.launch.py',note:'保持这个终端运行；默认会打开 RViz。无图形环境可追加 gui:=false。无需真实底盘或 Gazebo。'},
    inspect:{title:'终端 B · 确认控制器与接口',lang:'bash',source:'cli',code:'ros2 control list_controllers -c /controller_manager\nros2 control list_hardware_interfaces -c /controller_manager\nros2 control list_hardware_components -c /controller_manager\nros2 topic info /cmd_vel --verbose'},
    drive:{title:'终端 B · 持续发送速度指令',lang:'bash',source:'diffbot',code:'ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/TwistStamped \\\n  "{header: auto, twist: {linear: {x: 0.7}, angular: {z: 1.0}}}"',note:'linear.x：前进速度，单位 m/s；angular.z：转向角速度，单位 rad/s。header: auto 为每次发布填入当前时间戳。保持 10 Hz 发布，避免命令很快超时。'},
    observe:{title:'终端 C · 观察反馈',lang:'bash',source:'diffbot',code:'ros2 topic echo /joint_states\n# Ctrl+C 退出 echo 后，可观察里程计\nros2 topic echo /diffbot_base_controller/odom',note:'在 joint_states 中观察左右轮 position 随时间变化。默认 open_loop=true，因此 odom 的变化不能用来证明硬件编码器反馈正常。'},
    stop:{title:'终端 B · 停止演示运动',lang:'bash',source:'diffdrive',code:'# 先 Ctrl+C 结束之前的非零速度发布，再持续发布零速度\nros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/TwistStamped \\\n  "{header: auto, twist: {linear: {x: 0.0}, angular: {z: 0.0}}}"\n# 观察停止后 Ctrl+C，最后在终端 A 退出 launch',note:'本例配置 cmd_vel_timeout: 0.5，停止发布后旧命令也会超时。这里讲的是演示行为，真实机器人应有独立的急停与安全控制。'},
    urdf:{title:'diffbot.ros2_control.xacro · 精简教学片段',lang:'xml',source:'xacro',code:'<ros2_control name="DiffBot" type="system">\n  <hardware>\n    <plugin>ros2_control_demo_example_2/DiffBotSystemHardware</plugin>\n  </hardware>\n  <joint name="left_wheel_joint">\n    <command_interface name="velocity"/>\n    <state_interface name="position"/>\n    <state_interface name="velocity"/>\n  </joint>\n  <!-- 右轮也声明对应接口；这里只展示左轮 -->\n</ros2_control>',note:'这是完整机器人 URDF 中的 ros2_control 段落。left_wheel_joint 也必须存在于机器人结构描述里；片段省略了右轮、宏参数与硬件参数，不能直接替代原文件。'},
    yaml:{title:'diffbot_controllers.yaml · 精简教学片段',lang:'yaml',source:'yaml',code:'joint_state_broadcaster:\n  ros__parameters:\n    type: joint_state_broadcaster/JointStateBroadcaster\n\ndiffbot_base_controller:\n  ros__parameters:\n    type: diff_drive_controller/DiffDriveController\n    left_wheel_names: ["left_wheel_joint"]\n    right_wheel_names: ["right_wheel_joint"]\n    wheel_separation: 0.10\n    wheel_radius: 0.015\n    open_loop: true\n    cmd_vel_timeout: 0.5',note:'本提交由 spawner 直接加载各控制器参数，不必套 controller_manager 节点层级。控制循环 update_rate=10 写在 launch 中；这与里程计 publish_rate 参数不同。'},
    cpp:{title:'硬件插件 · 职责伪代码',lang:'cpp',source:'hardware',code:'// 教学伪代码，非可编译的完整插件\nread(time, period) {\n  // 实机：读取编码器/驱动器状态\n  // DiffBot 演示：上一轮轮速积分得到位置\n  position += velocity * period.seconds();\n}\n\nwrite(time, period) {\n  // 实机：把 command 发到总线/驱动器\n  // DiffBot 演示：把目标轮速镜像为速度状态\n  velocity = velocity_command;\n}',note:'完整插件还需要生命周期、接口、插件 XML、CMake 导出等部分。演示数值更新不能证明实体通信已实现。'},
    launchfile:{title:'diffbot.launch.py · 精简教学片段',lang:'python',source:'launch',code:'# 片段省略 imports、robot_state_publisher、RViz 和路径构造\nNode(\n    package="controller_manager",\n    executable="ros2_control_node",\n    name="controller_manager",\n    parameters=[{"update_rate": 10}],\n),\nNode(\n    package="controller_manager",\n    executable="spawner",\n    arguments=[\n        "joint_state_broadcaster", "diffbot_base_controller",\n        "--param-file", controllers_yaml,\n        "--controller-ros-args", "-r ~/cmd_vel:=/cmd_vel",\n    ],\n)',note:'controllers_yaml 是这里为讲解使用的占位变量。请点源码查看完整定义。重映射解释了为什么本示例向 /cmd_vel 发布，而不是默认的控制器私有话题。'},
    rrbot:{title:'延伸 · RRBot 位置控制',lang:'bash',source:'rrbot',code:'ros2 launch ros2_control_demo_example_1 rrbot.launch.py\n# 在另一个已加载环境的终端：\nros2 topic pub /forward_position_controller/commands \\\n  std_msgs/msg/Float64MultiArray "{data: [0.5, 0.5]}"',note:'需先单独构建 example_1；上文只构建了 example_2。完成 DiffBot 后停止它，再研究两关节 position 接口与速度接口的差别。'}
  };
  const issues = [
    {title:'命令提示找不到包 / package not found',en:'Environment',body:'新终端可能只加载了 ROS 2，没有加载工作空间；也可能 example_2 尚未成功构建。先检查环境和包是否可见，再检查构建日志。',code:'source /opt/ros/jazzy/setup.bash\nsource ~/ros2_control_ws/install/setup.bash\nros2 pkg prefix ros2_control_demo_example_2',expect:'能打印安装目录，而不是 package not found。',source:'demos'},
    {title:'一直等待 controller_manager 服务',en:'Discovery',body:'确认完整 diffbot.launch.py 仍在运行。view_robot.launch.py 只显示模型，不启动完整控制链路。若改过 manager 节点名，用 -c 指向实际名称。',code:'ros2 node list\nros2 control list_controllers -c /controller_manager',expect:'存在 /controller_manager；两个控制器可列出。',source:'cli'},
    {title:'控制器存在，却没有激活',en:'Lifecycle / interfaces',body:'检查状态是否 active，再核对 YAML 关节名和 URDF 接口名。控制器需要的接口不存在或被其他控制器占用时，激活会失败；根据启动终端日志找到具体接口。',code:'ros2 control list_controllers -c /controller_manager\nros2 control list_hardware_interfaces -c /controller_manager',expect:'diffbot_base_controller 和 joint_state_broadcaster 均 active；左右轮 velocity 命令接口为 available、claimed。',source:'cli'},
    {title:'发了速度，轮子却没有变化',en:'Topic / message type',body:'先核对消息类型和订阅者。本示例由 launch 重映射到 /cmd_vel，Jazzy 使用 TwistStamped。用 header: auto 与持续 10 Hz 发布，避免时间戳过期或命令超时。',code:'ros2 topic info /cmd_vel --verbose\nros2 topic type /cmd_vel\nros2 topic hz /cmd_vel',expect:'类型为 geometry_msgs/msg/TwistStamped，存在控制器订阅者；发布端运行时能观察频率。',source:'diffdrive'},
    {title:'里程计在变化，是否证明编码器正常？',en:'Open-loop odometry',body:'不能。官方 example_2 配置 open_loop: true，里程计用目标车速积分。应分别检查 joint_states、硬件 read()、实际设备反馈；真实反馈控制需要正确的配置与驱动实现。',code:'ros2 topic echo /joint_states\nros2 topic echo /diffbot_base_controller/odom',expect:'理解两种数据的来源，不用 odom 运动替代真实反馈验证。',source:'yaml'},
    {title:'示例能运行，怎么接入自己的履带底盘？',en:'Real hardware',body:'先保留控制器和统一的关节接口，替换演示硬件插件中的状态读取与命令写出，再校准有效轮距、半径和单位。履带存在滑移，差速运动学只是起点，不能直接照搬演示参数。',code:'# 从命名和接口核对开始\nros2 control list_hardware_components -c /controller_manager\nros2 control list_hardware_interfaces -c /controller_manager',expect:'先明确设备通信、单位、反馈、限幅与停止策略，再调试实体底盘。',source:'plugin'}
  ];
  const quizzes = [
    {q:'谁负责调度 read → update → write 控制循环？',choices:['RViz','Controller Manager','joint_state_broadcaster'],answer:1,explanation:'控制器管理器调度循环；硬件组件负责 read/write，激活的控制器在 update 阶段工作。',lesson:'cycle'},
    {q:'left_wheel_joint/velocity 出现在 command interfaces 中，代表什么？',choices:['当前测量到的轮速','控制器写入的目标轮速','ROS 话题名'],answer:1,explanation:'同样叫 velocity，放在命令接口中表示目标值；放在状态接口中表示反馈。接口名本身不是 ROS 话题。',lesson:'architecture'},
    {q:'运行本教程对应的 Python launch 后，正确的输入是什么？',choices:['/cmd_vel + TwistStamped','/cmd_vel + Twist','/diffbot_base_controller/cmd_vel + Float64'],answer:0,explanation:'Jazzy 差速控制器使用 TwistStamped；本示例 launch 把 ~/cmd_vel 重映射成 /cmd_vel。',lesson:'diffbot'},
    {q:'看到 [claimed]，可以得出哪个结论？',choices:['实体电机一定正在转','命令接口已经被控制器申请使用','所有硬件反馈都正常'],answer:1,explanation:'claimed 说明使用权，不证明真实设备运动或反馈正常。继续核查状态、驱动与实际设备。',lesson:'diagnose'},
    {q:'示例 open_loop: true 时，odom 在变化说明什么？',choices:['编码器已经验证成功','目标速度正在被用于计算里程计','电机通信一定正常'],answer:1,explanation:'开环里程计来自命令值积分。观察它不等于验证了硬件反馈。',lesson:'diagnose'},
    {q:'joint_state_broadcaster 主要做什么？',choices:['接收车体速度并控制轮子','读取状态接口并发布关节状态','替代硬件插件与电机通信'],answer:1,explanation:'广播器让框架中的状态对外可见，不接收用于驱动的运动命令。',lesson:'files'},
    {q:'URDF 与 YAML 中的关节名不同，最合理的下一步是什么？',choices:['不断增加 update_rate','核对关节名、接口名及启动日志','把 TwistStamped 换成 Twist'],answer:1,explanation:'接口需要精确匹配。先解决资源与配置对应关系，增加频率不会修复名称不一致。',lesson:'files'}
  ];
  root.LearningContent = {lessons,nodes,terms,snippets,sources,issues,quizzes,commit,checked:'2026-11-06'};
})(window);
