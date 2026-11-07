/* 正式构建同步的原创图解清单；来源为source/design-figures.json。 */
window.PreviewFigureData = [
  {
    "id": "architecture",
    "file": "preview/figures/architecture.svg",
    "title": "ROS 2：从应用到通信实现",
    "kind": "架构图",
    "caption": "从上向下读接口层次：应用可选择并列的 rclcpp 或 rclpy，两者都位于共同的 rcl 之上，再经 RMW 接入具体通信实现。图中只画常见 DDS 路径，省略类型支持、执行器内部和操作系统；不表示所有 RMW 都基于 DDS。",
    "alt": "五层 ROS 2 架构：应用、并列的 rclcpp 与 rclpy、rcl、RMW、DDS；侧栏说明跨语言接口、可替换中间件及执行器职责。",
    "placements": [
      {
        "chapter": "architecture",
        "afterSection": 2
      },
      {
        "chapter": "network",
        "afterSection": 0
      }
    ]
  },
  {
    "id": "pubsub",
    "file": "preview/figures/pubsub.svg",
    "title": "发布订阅：一个契约，多个消费者",
    "kind": "架构图",
    "caption": "沿绿色箭头从发布者读到两个独立订阅端。虚线区是逻辑话题的名称、类型与 QoS 契约，不是消息中央服务器；每一对端点独立匹配。订阅端收到数据后仍由 Executor 调度回调，图不规定底层 DDS 的传输拓扑。",
    "alt": "一个发布者通过逻辑话题 /scan 向算法和记录器两个订阅者提供 LaserScan，双方按 QoS 匹配，各订阅节点的执行器调度回调。",
    "placements": [
      {
        "chapter": "pubsub",
        "afterSection": 0
      },
      {
        "chapter": "qos",
        "afterSection": 1
      },
      {
        "chapter": "executors",
        "afterSection": 0
      }
    ]
  },
  {
    "id": "action",
    "file": "preview/figures/action.svg",
    "title": "Action：接受、反馈与结果是不同阶段",
    "kind": "时序图",
    "caption": "时间向下：客户端先发目标并得到接受响应，再异步请求最终结果；运行中可收到多次反馈。橙色表示取消请求及获准响应，获准后仍需等待服务端停止并返回 CANCELED 结果。本例省略目标拒绝和 SUCCEEDED、ABORTED 等其它终态。",
    "alt": "客户端和服务端双泳道时序：目标请求、接受、异步等待结果、两次反馈、取消请求、取消获准、最终 CANCELED；明确取消确认不等于任务结束。",
    "placements": [
      {
        "chapter": "actions",
        "afterSection": 4
      },
      {
        "chapter": "eco-nav2-task-programming",
        "afterSection": 1
      }
    ]
  },
  {
    "id": "lifecycle",
    "file": "preview/figures/lifecycle.svg",
    "title": "生命周期：先准备，再运行，最后清理",
    "kind": "状态图",
    "caption": "先沿正向箭头 configure、activate 进入 active；反向箭头 deactivate、cleanup 回到可重新配置的状态。unconfigured、inactive、active 都可经 shutdown 到 finalized，终结后没有返回箭头。只展示成功转换，省略中间状态、失败返回和错误处理；节点状态也不自动停止所有普通回调。",
    "alt": "四状态生命周期：未配置与未激活通过 configure 和 cleanup 往返，未激活与激活通过 activate 和 deactivate 往返，三个状态均可 shutdown 到终结。",
    "placements": [
      {
        "chapter": "lifecycle",
        "afterSection": 1
      },
      {
        "chapter": "eco-nav2-stack",
        "afterSection": 2
      }
    ]
  },
  {
    "id": "control",
    "file": "preview/figures/control.svg",
    "title": "ros2_control：状态与命令组成反馈闭环",
    "kind": "流程图",
    "caption": "在 controller_manager 框内从左向右读一个典型周期：read 把测量或估计值送入状态接口，update 结合参考计算命令，write 将命令送往设备或仿真。绿色是状态反馈，橙色是参考或命令。省略异步硬件、线程分配、级联控制与故障处理，顺序不构成硬实时保证。",
    "alt": "管理器调度 read、update、write 三步，目标参考输入控制器，设备状态反馈到 read，命令由 write 下发设备，状态和命令用不同颜色区分。",
    "placements": [
      {
        "chapter": "eco-control-framework",
        "afterSection": 0
      },
      {
        "chapter": "eco-hardware-integration",
        "afterSection": 0
      },
      {
        "chapter": "eco-diff-drive-tracks",
        "afterSection": 0
      }
    ]
  },
  {
    "id": "nav2",
    "file": "preview/figures/nav2.svg",
    "title": "Nav2：规划、控制与底盘反馈",
    "kind": "流程图",
    "caption": "自上而下读地图、定位/状态估计和传感器对代价地图的支撑，再沿规划器输出路径、控制器输出速度、底盘执行的链路读。虚线反馈经里程计与状态估计返回坐标链；map→odom 的全局定位与 odom→base_link 的局部运动各有责任来源。各 costmap 按图层选择地图和观测，并非必定使用全部输入；行为树、恢复、平滑器和生命周期未展开。",
    "alt": "地图、odom/TF 和传感器输入支持全局与局部代价地图；全局规划器输出路径到局部控制器，后者输出速度到底盘，状态和里程计反馈回估计与 TF。",
    "placements": [
      {
        "chapter": "eco-nav2-stack",
        "afterSection": 0
      },
      {
        "chapter": "eco-nav2-task-programming",
        "afterSection": 0
      }
    ]
  },
  {
    "id": "rigid-composition",
    "file": "preview/figures/rigid-composition.svg",
    "title": "同一个点，两种坐标表达",
    "kind": "原理图",
    "alt": "车体B与旋转90度的传感器L坐标系，以及点坐标的旋转平移数值案例。",
    "caption": "例中先将传感器坐标旋转90°，再加安装平移。图上两组坐标描述同一个点；改变表达坐标不改变物理点。",
    "placements": [
      {
        "chapter": "math-rigid",
        "afterSection": 0
      },
      {
        "chapter": "math-kinematics",
        "afterSection": 0
      }
    ]
  },
  {
    "id": "tf2-static",
    "file": "preview/figures/tf2-static.svg",
    "title": "二维交互的静态数值案例",
    "kind": "原理图",
    "alt": "二维刚体变换的默认可手算案例，米为长度单位。",
    "caption": "连续版保存一个静态参数案例；交互版可在相关章节调整平移与旋转。",
    "placements": [
      {
        "chapter": "tf2",
        "afterSection": 2
      },
      {
        "chapter": "eco-tf-frames",
        "afterSection": 1
      }
    ],
    "bookOnly": true
  },
  {
    "id": "estimation-loop",
    "file": "preview/figures/estimation-loop.svg",
    "title": "用预测和测量修正状态",
    "kind": "原理图",
    "alt": "运动预测、创新、测量校正和协方差递推的闭环。",
    "caption": "预测与校正既要更新状态，也要处理不确定性、时间戳和观测坐标。图不意味着所有SLAM算法都采用EKF，也不保证所有状态都可观。",
    "placements": [
      {
        "chapter": "math-estimation",
        "afterSection": 1
      },
      {
        "chapter": "eco-state-estimation",
        "afterSection": 0
      }
    ]
  },
  {
    "id": "planning-search",
    "file": "preview/figures/planning-search.svg",
    "title": "比较搜索时，先对齐同一个问题",
    "kind": "原理图",
    "alt": "网格、障碍、起终点和示意路径，以及Dijkstra和A星的优先级。",
    "caption": "虚线是理想距离直觉，橙线是绕障示意路径，未把这条绘制路径标为算法最优输出。真实最优性要以相同图、非负代价和启发条件核查；机器人还需要运动学与碰撞约束。",
    "placements": [
      {
        "chapter": "theory-planning",
        "afterSection": 1
      },
      {
        "chapter": "project-navigation",
        "afterSection": 2
      }
    ]
  },
  {
    "id": "receding-horizon",
    "file": "preview/figures/receding-horizon.svg",
    "title": "预测多步，执行一步，重新观测",
    "kind": "原理图",
    "alt": "模型预测控制的预测时域与滚动执行顺序。",
    "caption": "示意轨迹没有替代具体模型或求解器结果。实际系统需检查约束可行性、终端条件、采样周期、求解上界和失败后的控制策略。",
    "placements": [
      {
        "chapter": "theory-optimal-control",
        "afterSection": 2
      },
      {
        "chapter": "math-control",
        "afterSection": 4
      }
    ]
  },
  {
    "id": "slam-constraints",
    "file": "preview/figures/slam-constraints.svg",
    "title": "SLAM：状态由哪些约束连接？",
    "kind": "原理图",
    "alt": "三个机器人位姿、一个地标、运动与观测约束以及回环边。",
    "caption": "方框是待估计变量，连接表示模型残差或测量约束。回环需要可靠的数据关联；固定一个参考自由度可消除相应规范歧义，但不能自动修复错误观测或保证地图准确。",
    "placements": [
      {
        "chapter": "theory-slam",
        "afterSection": 1
      }
    ]
  },
  {
    "id": "robot-static",
    "file": "preview/figures/robot-static.svg",
    "title": "连杆、局部关节轴与末端位置",
    "kind": "原理图",
    "alt": "三关节机器人几何模型，显示与交互模型一致的默认关节角和末端坐标。",
    "caption": "这是交互模型默认姿态的静态几何图，仅验证运动学关系，不包含质量、碰撞、接触、驱动或ROS连接。交互版可在正文中调整视角和关节。",
    "placements": [
      {
        "chapter": "eco-model-rviz",
        "afterSection": 1
      },
      {
        "chapter": "eco-moveit-planning",
        "afterSection": 1
      },
      {
        "chapter": "math-kinematics",
        "afterSection": 2
      },
      {
        "chapter": "project-manipulation",
        "afterSection": 2
      }
    ],
    "bookOnly": true
  },
  {
    "id": "component-options",
    "file": "preview/figures/component-options.svg",
    "title": "组件参数：来源、覆盖与实际值",
    "kind": "原理图",
    "alt": "Context全局CLI、管理节点当前参数和LoadNode局部覆盖分开；转发开关控制全局CLI，局部覆盖优先，三个实例输出0.20、0.36、0.30米每秒。",
    "caption": "本图针对标准manager创建的组件options，数值取自第3轮真实Config实验。管理节点从1.8改为1.2不改写Context的启动CLI；局部加载参数优先。gain无量纲，输出按0.2m/s基值换算；不是硬件速度或任意NodeOptions默认值的示意。",
    "placements": [
      {
        "chapter": "composition",
        "afterSection": 6
      }
    ],
    "evidenceFile": "validation-evidence/component-labs-current-validation.json",
    "evidenceSha256": "3c44eddd36c25205bc11f0e1d43bc76e211a59ef5e21da851c00515dc1eea2a2"
  },
  {
    "id": "gazebo-sensor-captures",
    "title": "Gazebo 红板的真实相机帧与红通道边缘",
    "alt": "同一采集时戳的96乘64像素红板图像和黑底白边Canny结果。两个结果并排，可看清红板的竖边。",
    "file": "preview/figures/gazebo-sensor-captures.svg",
    "kind": "实测图",
    "caption": "左侧 RGB、右侧红通道 Canny 来自同一台架的实际软件仿真采样。阈值固定为 40/120，像素以最近邻放大。图像处理保留原 Header。",
    "evidenceFile": "validation-evidence/gazebo-sensors-current-validation.json",
    "evidenceSha256": "697c865879d240e7e9266488b308d7a6d7f88f5df9a3527230f03303d6b60686",
    "assetSha256": "576143f5b1f611f4d5e750205f3950a21118c233f98369057579a56d96e9c430",
    "placements": [
      {
        "chapter": "eco-gazebo-simulation",
        "afterSection": 7
      },
      {
        "chapter": "eco-perception-pipeline",
        "afterSection": 7
      }
    ]
  },
  {
    "id": "nav2-costmap-planning",
    "title": "同一目标在障碍标记前后的 NavFn 路径",
    "alt": "左侧的静态代价图上原路径横穿箱体所在区域。右侧的障碍层由实际激光标记箱体前缘，新路径从其侧面绕行。",
    "file": "preview/figures/nav2-costmap-planning.svg",
    "kind": "实测图",
    "caption": "两幅底图来自真实 GetCostmap 主图，路径来自两个实际 ComputePathToPose 回执。箱体虚线是 SDF 几何，红格是扫描新增的可见面。两图比例相同。",
    "evidenceFile": "validation-evidence/nav2-planning-current-validation.json",
    "evidenceSha256": "4366cea60de4f7bfa8a1b8648562b41d2356ca6ee62ceff84dffc2389ae8a0a3",
    "assetSha256": "ffba6f9902df9fbefbcb136614df047700d749fd17a08ebcf8e95d2dcea4d58a",
    "placements": [
      {
        "chapter": "eco-nav2-stack",
        "afterSection": 8
      },
      {
        "chapter": "theory-planning",
        "afterSection": 6
      }
    ]
  },
  {
    "id": "slam-mapping-trajectory",
    "title": "同一圈扫描的占据图、轨迹与误差",
    "alt": "左侧为实测占据图叠加 Gazebo 参考路线、注入偏差的里程计和 SLAM 位姿。右侧比较每次接受扫描时的平面位置误差。",
    "file": "preview/figures/slam-mapping-trajectory.svg",
    "kind": "实测图",
    "caption": "底图是 SLAM Toolbox 实际发布的占据栅格。路线取采集参考、注入偏差的里程计和接受扫描后的位姿回执。估计误差按采集参考位姿计算。",
    "evidenceFile": "validation-evidence/slam-mapping-current-validation.json",
    "evidenceSha256": "1d3a900208f6d9a8ec02b2c9c8f4da16397cfd19bc1513ce48b3263b5f76698e",
    "assetSha256": "512c08e0516505aebfe270e5a346ce52525fcf5b1ce9961e280a5959e6e02f24",
    "placements": [
      {
        "chapter": "eco-slam-mapping",
        "afterSection": 9
      },
      {
        "chapter": "theory-slam",
        "afterSection": 6
      }
    ]
  }
];
