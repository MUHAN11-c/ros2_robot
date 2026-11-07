# 本轮验证与复现范围

日期：2026-11-07，Ubuntu 24.04 / ROS 2 Jazzy / 系统 Python 3.12.3。所有 ROS 检查均限制在本机独立域，没有连接机器人。本文件区分已运行、仅核对和待运行。

## 全章目录与排版

在 1440、390 和 320 像素下分别核对正式阅读器与紫樱审查版的全部 60 章。章名、章号、正文层级、目录父级和锚点均逐项比对，另逐段比较 451 个主小节的 1,135 段正文。桌面逐条点击正式版 1,132 个条目与审查版 1,129 个条目。正式版另有两个变换演示和一个 QoS 练习入口。

连续阅读版在断网且禁用脚本的浏览器中检查 60 个折叠目录和其中的 1,129 个链接。分章结果与截图见 `validation-evidence/offline-reader-current-validation.json`、`design-review/validation/browser-report.json` 与 `design-review/screenshots/`。

## 已完成检查

| 层次 | 实际结果 | 证据/入口 |
| --- | --- | --- |
| 内容与交付 | 60 章均至少 5 节、3 道深入练习和案例。49 组公式、23 组 API、341 道练习、164 份完整文件通过检查，39 张实测表及原始采样图核对对应指纹 | `tests/check_content.py`、`source/topic-depth.json` |
| 前端逻辑 | 搜索、存储清洗与 QoS 8 项；旧正文导出模块 3 项；二维/三维几何 6 项通过 | 三个 Node 单元文件直接运行，合计 17 项 |
| 数学与模型 | 数学 8 项、应用 8 项标准库实验通过；四个基础实验 4 项边界测试；看门狗 7 项；公式导出 2 项 | `examples/theory_labs/`、相应 Python tests |
| Markdown表格 | 新增 Python 2 项与 JavaScript 1 项，核对连续表头/分隔行、管道及换行转义；浏览器实际下载参数章节并读取文件比对 | `tests/test_markdown_tables.py`、`tests/markdown-tables.test.cjs`、HTTP交互报告 |
| 通信工作空间 | `atlas_cpp`、`atlas_py` 构建；双向话题、双向服务、三种 launch 解析共 5 项通过 | `tests/test_examples.py`、`examples/VALIDATION.md` |
| 基础工作空间 | 10 包构建；15 项集成检查通过，26 个示例子进程已清理 | `validation-evidence/foundation-current-validation.json` |
| 动作/组件扩展 | 各1个原创C++包独立构建；Count沿用基础接口，组件生成共享插件、独立Config与可观察管理入口 | 两份第3轮报告的build/buildEvidence及sourceHashes |
| 生命周期/注册测试包 | 各1个原创C++包独立构建；生命周期10场景，测试两种构建变体的正常/受控失败分开 | 第4轮两报告与原始构建/测试记录 |
| 导航协议 | 有界客户端在隔离假服务端下完成 12 类场景、18 项阶段耗时断言 | `examples/navigation/README.md`、`source/navigation-revision.json` |
| HTTP 交互 | 搜索、进度导入导出、主题、QoS、实现标签/键盘、章节导出、本地原文、下载及损坏/禁用存储通过；390/320px 共 170 条路由检查无整页溢出 | `validation-evidence/browser-current-validation.json` |
| 完全断网阅读 | 文件协议 60 章、旧路由、图解、公式、进度与搜索通过。无脚本连续版有 49 组 MathML、36 个 SVG 实例和 39 张实测表，远程请求及脚本错误均为零 | `tests/reader-checks.cjs` |
| 便携包 | 实际解压ZIP后断网检查，原文缺失入口禁用、复制/回退、60章、无脚本公式/图解及390/320px连续版通过 | `validation-evidence/delivery-current-validation.json` |
| 图解交互 | 正式入口 15 张常规静态图的 30 处位置、2 种交互及手机检查通过。连续版另有 2 张静态回退图 | `validation-evidence/figures-current-validation.json` |

基础 15 项包括十包/入口/四种接口 typesupport、两个 boot 节点、双向话题/服务、两种 Count 服务端成功及取消、C++/Python gain 动态与启动边界、逐项设置与原子提交差别，以及三种 launch 结构解析。参数拒绝 NaN/±Inf/错误类型，失败后保留旧值。launch 检查只证明解析与结构。

导航测试只启动假 `NavigateToPose` 服务端，覆盖成功、拒绝、失败、导航超时取消、接受迟到、目标无应答、取消无应答、取消无终态、暂停 clock、Ctrl+C、clock 缺失与服务器缺失。取消应答、软件终态和物理停车分别说明。不是完整 Nav2 导航验收。

初轮独立内容审查的 12 个发现条目已逐项复核并记录修订；重叠发现对应同一修复。详见 `validation-evidence/review-resolutions.json`。旧审查保留发现时的状态，不覆盖历史证据。

## 持续迭代新增的实际API实验

| 实验 | 已运行证据及边界 |
| --- | --- |
| QoS七场景 | `qos-contract-current-validation.json`；域213/FastDDS/LOCALHOST，单进程双Node。明确不兼容/修复、可靠→尽力、持久性冲突、41/42晚加入历史、易失及writer重建边界；图UNKNOWN不当真实深度0 |
| 异步服务三场景 | `async-poll-clock-current-validation.json`；域215；无clock和正值clock暂停时应答缺失约2.2s收尾，暂停但正常应答sum12；故障通过不调度真实服务端回调注入 |
| tf2 Buffer八组 | `tf-buffer-current-validation.json`；真实安装API、只写内存缓存，无Node/DDS；验证非零旋转、正逆、插值、latest差约0.4142m及异常 |
| 软件clock三阶段 | `clock-timer-current-validation.json`；域223；0.1s周期、0.8s窗口，ROS/STEADY增量0/8、0/8、8/8，跳变结算另测，不等于仿真已运行 |
| 慢消费者四组 | `slow-consumer-current-validation.json`；域216/LOCALHOST/FastDDS/BEST_EFFORT，发布/接收独立进程。请求40Hz、3秒发送+1.2秒排空、80ms慢处理、120ms门限；49运行断言与23年龄边界通过，8个PID自然退出 |
| 执行器/Future四组 | `executor-group-current-validation.json`；域219/LOCALHOST/FastDDS；单线程分组、双线程同组、双线程分组最大并发1/1/2。真实AddTwoInts Future的用户done在响应handler释放组之后与同client组timer重叠；四例线程/Context清理完成 |
| 参数阶段十一组 | `parameter-transaction-current-validation.json`；域223、发现OFF、无参数服务/执行器，直接调用同节点Python API；19节点销毁、Context关闭。pre/on/post、逐项/原子、缓存污染及post异常分别检查存储与应用快照；Node仍有RMW及parameter_events |
| 迟到服务八项 | `service-deadline-current-validation.json`；域221/LOCALHOST/FastDDS，默认探针4例，另运行既有C++/Python客户端各迟到/未发现2例；迟到客户端本地收尾后服务仍执行一次。IPC独立观察，不是ROS服务反馈/取消；所有子进程自然退出 |

源码在examples/runtime_labs/，中文说明及命令见该目录README。原始报告随验证记录ZIP提供，保存源码SHA与具体输入；旧报告只证明其原来范围。第2轮新增27组主场景不表示任意调度、跨机或硬件验证：慢消费者的处理后拒绝在自然负载中未触发，23项边界断言另列；p95含排空尾部，不当通用性能基准。执行器用释放GIL的Event.wait演示调度许可；参数C++三阶段只核源码，未运行。服务测试本身退出0表示预期断言通过，原客户端两类失败都返回1，必须结合日志和服务端观察区分。

第1/2轮的原始报告继续按各自范围有效。第3轮补充如下；当前独立审查状态见`iteration-worklist.json`，持续目标保持active，完整仿真和硬件仍未运行。

## 第3轮：动作、组件与退出路径

| 范围 | 实际结果与边界 |
| --- | --- |
| Count十组主场景 | `count-action-current-validation.json`；域227/LOCALHOST/FastDDS，24个目标UUID。原C++/Python各验证busy拒绝、取消/自然完成后再接合法目标及0/21非法边界；扩展两语言各验证默认故障关闭、显式abort_after=6得到ABORTED/completed6、后续短目标成功 |
| Count退出生命周期 | 同报告的`lifecycleValidation`及保留历史；真实首反馈之后只向父driver发SIGINT，核对自建worker/server的退出和/proc项。中断运行本身不是十组正常案例，也不把进程退出当CANCELED或物理停车 |
| Config与NodeOptions | `component-labs-current-validation.json`；域225/LOCALHOST/FastDDS，5组主场景。11项动态gain、7种加载配置、4类构造/extra失败；finite DOUBLE [0,2]，基值0.2m/s，合法gain1.5输出约0.3m/s。未知extra不启用自动声明；非法加载后已有ID列表不变 |
| 管理参数与转发 | 标准管理参数服务默认关闭。另用同类observable_manager显式开启服务，真实Describe/Set确认thread_num=2且read_only，改范围内1仍拒绝。Context CLI gain1.8、管理当前1.2、LoadNode局部1.5分别观察，不混作参数同步 |
| 官方三容器 | 同组件报告：single/mt(显式2线程)/isolated默认每组件ST，最大业务并发1/2/2、慢窗口heartbeat 0/17/17。保留同PID、TID、成对稳态span；C++等待模拟IO，不作CPU、零复制或实时性能保证 |
| 组件退出生命周期 | 同报告`interruptValidation`；真实slow-start后只INT父driver，约0.516s退出130；自有worker与原生容器进程消失，后续case停止，无外部补救清理 |
| 首次构建范围与许可 | `package-scope-current-validation.json`实际colcon list确认：examples/src仅通信两包，整个下载目录会发现四包；首次通信构建限定src，附加包分别准备依赖。两个独立工程ZIP均携带自身LICENSE |

动作原因日志与Count.Result不同：Result仍只有completed，拒绝目标没有已执行Result，扩展原因由独立UUID日志记录。受控中途取消得到CANCELED不保证临近完成竞态的同样终态；固定底层状态机允许CANCELING转成功、失败或取消。Python探针验收两种服务端，没有新增C++客户端验证；扩展取消业务路径仍不在本轮已跑清单内。

组件未知参数混入严格GetParameters请求可能让整批返回空values，不能按位置读成gain=0或逐项NOT_SET。ListParameters、合法名查询与动态set拒绝分别核对；两种语言严格服务的相应错误分支以源码限定，Python远程服务分支没有冒称本轮组件实测。isolated额外每组件MT模式、崩溃隔离、零复制及跨机/硬件未运行。

`iteration3-source-review.json`保留安装rclcpp28.1.22/本地快照28.1.23、rclpy7.1.12/快照7.1.13及定点字节比较。容器入口的析构顺序差异与实际调度配置分别记录，局部相同不代表整个版本相同。审查必须approved且绑定当前两份报告SHA，才能生成`iteration-3-revisions.json`；正文还绑定审查文件SHA。保留失败夹具与中断历史，不用刷新标签替代重跑。

源码、依赖与完整复现分别见`examples/action_labs/README.md`和`examples/component_labs/README.md`。读者命令将新报告另存/tmp；维护者确认实验和独立审查后才重建教材绑定证据。Markdown单章、全文与连续HTML同步包含三张新增实测表及完整源码。

## 第4轮：生命周期、测试合同与部署证据

| 范围 | 实际结果与边界 |
| --- | --- |
| 生命周期 | `lifecycle-current-validation.json`；域229/LOCALHOST/FastDDS。10主场景、21消息窗口、17/17 FakeHandle释放；完整往返/重配、configure与activate FAILURE、ERROR/std异常及on_error各结果分别记录。转换表12行含同场景内检查，不能当12个主场景 |
| 请求、恢复与发布 | 原ERROR后on_error SUCCESS可恢复unconfigured，但原ChangeState为false；FAILURE/ERROR/std异常到finalized。正常6个0.3s窗口普通消息各6，managed仅active窗口6，其余0；这是有限窗口观察，不保证任意负载频率。LifecyclePublisher门控与普通回调、资源另验 |
| 生命周期中断 | 仅向父driver一次INT，约0.515s退出130，C++子进程exit0，资源析构回收且无遗留。on_shutdown未被调用、缓存状态仍active；不能把Context关闭/析构当成成功的shutdown转换。自建Context NO下context.ok不能作收到INT的标记，初次夹具失败保留 |
| 原策略与原集成例 | `testing-existing-current-validation.json`；旧4项pytest通过，6个新合同反例暴露NaN时戳/期限、bool和字符串缺口；修订整数纳秒/有限速度策略31项通过。原talker在域230的活动/退出2项实际通过；该辅助driver的父中断/挂死未另注入 |
| 完整注册测试 | `testing-labs-current-validation.json`；域231，两种构建变体。正常3个CTest注册、13个细分JUnit（4+7+2）0失败；受控缺READY细分1failure/0error。默认test/result退出0/1，严格模式1/1，最后正常恢复0/0。CLI聚合16项与故障2failures含包装重复，不当新增案例 |
| 测试夹具与退出 | 空结果CLI0仍拒绝验收；首轮NoMatchingProcess夹具错误保留，修后实际失败原因是缺业务READY断言。父INT一次发给colcon根，driver退出130、自建后代回收、无控制器应急信号；全部本轮日志在/tmp。不是硬件或完整故障覆盖 |
| 安装审计 | `deployment-current-validation.json`；原前缀与保留链接副本均24普通文件、18外链（15 build、1 source、2 underlay）。SHA/链接文本一致仍不自包含；只读显式允许根、环境allowlist与上限，9个自建夹具另列。副本删除，未运行副本、跨机或容器 |
| 宿主exec | 既有组件Config可执行在原安装前缀经source+exec，同PID成为节点；单次TERM后约0.1134s exit0、无孩子且/proc消失。Docker默认CMD改为镜像内固定路径的直接hub_talker_node，入口只负责环境与argv；该Docker节点和docker stop没有运行 |
| 参数来源图 | 图源核对第3轮组件报告中Context1.8、管理当前1.2、局部1.5及三个输出，绑定报告SHA。新增图首次只在连续版出现，定位为交互端旧清单；正式构建现同步同一清单，图源/正文/交互目录有一致性检查 |

四份报告与23项源文件/输入指纹经过`iteration4-source-review.json`独立核对并approved，审查绑定当前各报告SHA和整合脚本；生命周期2份文档、真实ELF、JUnit快照与中断原始记录分别复核。安装rclcpp28.1.22/launch_testing3.4.12与所用参考快照28.1.23/3.4.13保持版本差异，选中文件相同不代表整个版本相同。

本轮非法生命周期转换用label，先查可用label；未将任意numeric id、非std异常、全部cleanup/deactivate/shutdown故障组合算为已测。策略只选择教学输出，不限幅、不识别时间域、不控制制动；旧基线在JSON中明确作反例。测试期望失败与正常通过分开，不能把任意异常当受控反例。

Docker命令本机不存在，未安装、构建或运行镜像。宿主信号正例不替代容器PID1、网络、ABI或设备验收；复制字节校验也不证明迁移成功。实验说明分别在`lifecycle_labs/`、`testing_labs/`、`testing_policy/`和`deployment_labs/`的README。新报告另存/tmp，维护者复核后再刷新绑定教材。

本轮`package-scope-current-validation.json`确认原创工程下载包的examples目录现有6个ROS包，首次通信仍只发现src下atlas两包；第3轮“四包”清点作为历史保留。136完整代码逐字节核对，单章/全文Markdown、连续HTML和独立工程包保持同源。

## 第5轮：真实录放、时钟与存储字段

`bag-current-validation.json`实际在Jazzy rosbag2 0.26.11、独立域231/LOCALHOST/FastDDS完成三次CLI录制、关闭读回、两次暂停后CLI回放及无DDS的双后端字段探针。输入是标准合成PointStamped/Int32/String，不接硬件。

| 范围 | 实际证据 | 结论边界 |
| --- | --- | --- |
| 三组录制 | SQLite普通、MCAP软件钟、MCAP易失历史反例分别读回13/13/12；每主题元数据、序号、Header/Point全字段及真实载荷SHA分别保存 | 相同有限消息配置，不是插件吞吐/压缩性能比较 |
| clock门控 | 无clock、仅零clock时三个数据订阅均为零；正值10秒后才发送六条有效input，门前100/101与200/201未补录 | RCL源码判定严格大于零；负时间没有另行注入，数据未被订阅不称回调后丢弃 |
| 回放与唯一来源 | 先销毁原发布者、核零端点；start-paused等待实际匹配与Resume。完整无clock收到6/6/1、消费者ROS时间0；筛选有clock收到6/0/0、唯一clock发布者 | Header不会自动驱动ROS钟；未启动真实算法或GUI模拟器，不证明轨迹重现 |
| 显式时间字段 | Writer同bytes指定Header=7s/recv=10s/send=9s；只读SQLite表仅存recv，MCAP无分块Message保留两字段 | 人工指定时间差不是网络延迟；Python read_next只返回recv，noChunking解析器不是通用MCAP读取器 |
| 退出与历史 | 八个常规子进程均exit0，三个录制器各一次INT，其余自然退出，无升级信号，节点/Context清理且PID消失 | 父SIGINT与原生挂起没有注入，不能借其他实验替代 |
| CLI边界 | 三帮助、域233拒绝、NaN期限拒绝、零读取上限拒绝共六项；相对新目录双后端探针通过 | 报告保留检查标签/返回码，不是任意参数或路径全集验证 |

首次真实运行失败来自夹具把另一次序列化SHA当作消息等同性：60字节CDR的32..35对齐区不同，Header/Point语义仍一致。现对发布/回放比较全部字段，原始SHA只标识实际存储bytes；显式同bytes跨存储仍逐字节核对。第二次失败为不存在的`qos_profile_clock`导出，改显式深度1/best_effort后重新全流程。失败与清理历史没有删除。

`iteration5-bag-source-review.json`独立绑定两份当前报告和生成器SHA，核7源/输入、3Python边界指纹、实际SQLite数据、无分块MCAP头、日志SHA及PID消失。24条一手来源记录与9条教材出处分列。安装与固定快照同为0.26.11但Player结束会话的clock timer补丁不同，正文不把CLI自然退出推成保活节点保证。CDR、RCL和MCAP规范按各自固定版本核读。

新增四表、六完整文件、八练习，并修正三个未带`--clock`命令的旁注。原turtlesim/demo talker练习、真实采集、Foxglove、tracing、性能/压缩、崩溃恢复、保活Player、跨机和硬件均未运行。原创工程仍6个ROS包；本轮包发现另确认src仍只含通信两包，不把发现当重新构建。

本轮网站实测通过HTTP390/320px共170条路由、真实单章Markdown下载、断网60章/无脚本49MathML与30SVG/20表，以及实际解压ZIP的便携入口、复制回退和窄屏检查。142完整文件逐字节对照，最终收录记录后再核15项被测核心指纹与全部站点字节。

汇总的r3历史曾因共享字典误带r4指标，现依据独立交付快照恢复118文件/274练习/8表，只保留可证交付统计；新历史采用deepcopy。原始运行报告保持独立，不用后轮结果覆盖前轮事实。

## 第6轮：完整模型、状态位置与光学坐标

新增learning_description资源包和model_labs工具，原最小URDF保留逐字节教学副本。主报告`model-current-validation.json`在本机RSP3.3.4/xacro2.1.1、独立域219/LOCALHOST实构建、普通复制安装、从空当前目录启动两种配置；未启RViz、joint_state_publisher、仿真器或硬件。

| 范围 | 实际观察 | 结论边界 |
| --- | --- | --- |
| 展开/安装 | 默认半径0.08m、轮距0.36m；覆盖0.10/0.40m，均7link/4fixed/2continuous/5实体惯量；安装4文件字节一致且非源码软链 | 不证明跨机依赖闭包、mesh显示或真实机械标定 |
| 固定与活动TF | 参数回应后再创建Listener，可得到已发送固定边；无位置时活动轮边不存在；两配置base高度0.14/0.16m | RSP20Hz是节流上限，不是自动生成关节运动或全局定位 |
| 状态输入 | 默认四阶段、覆盖两阶段：四有效位置阶段，name/position非法长度1项，合法velocity-only但RSP无法算位置1项；后两项日志/0.25s不变TF与恢复分别记 | JointState协议允许可选数组留空；不能把仅速度消息一概说成畸形，也不证明物理停车 |
| 光学坐标 | 两配置共6单位点，由真实RSP/DDS/tf2转到base_link；轴Z前/X右/Y下，计算含[0.18,0,0.1]m平移 | 不是图像采集、相机标定或非零活动joint origin复合实验 |
| 入口拒绝 | 负轮半径与NaN轮距分别CLI1，预期自定义错误、无节点启动 | 不穷尽任意launch参数或任意模型 |
| 正常清理 | 10个父命令中8正常0、2预期拒绝1；2个launch只收父PID一次INT，RSP子PID均消失，无升级信号 | 父SIGINT/原生挂起未注入，不借其他实验替代 |

`model-boundaries-current-validation.json`另保存两项无ROS帮助、一项非法域及完整argv/输出。负惯量夹具仅改变物理数值left_wheel Iyy=-0.00064 kg*m²：真正check_urdf仍返回0，标准库自检返回1。语法/树、对角惯量合同、显示与动力学应分层验收；自检仅处理小型盒体/圆柱及对角惯量，不作一般非对角特征值或碰撞工具。第一次辅助命令因嵌套shell损坏XPath未执行到该探针，修正记录保留。

独立源码交付另实际验证：正式archive_tree函数生成95文件ZIP、解压到另一目录，从atlas_examples根运行model_labs/validate_model.py，在域220约3.852秒通过。`model-portable-current-validation.json`核8源/输入与原文/ZIP/解压副本逐字节一致，并保存完整复跑。最初误填未创建cwd时工具未启动进程，后按记录中的真实路径运行；不把这次设置错误当ROS运行失败。仍依赖本机ROS安装，不是跨机二进制或ROS安装器交付。

`iteration6-model-source-review.json`独立绑定两核心报告、portable补充及生成器SHA，核10项核心指纹、4安装副本、10日志/12PID与原始数值。15一手来源记录和7教材出处分列；RSP快照对应3.3.4 tag，xacro同2.1.1仍有动态arg名的post-tag差异，普通字面arg不受影响。KDL局部轴/安装变换与根惯量局限按固定实现核对，非零活动origin和根惯量运行反例未执行。

新4表、6完整文件、8练习与1API接入正文；Xacro缺项同时修正文与快捷步骤，URDF/Xacro加入XML源码索引与下载。当前148完整文件逐字节对照，HTTP390/320px共170路由、真实模型单章Markdown下载、断网60章/无脚本24表通过，无外部请求或脚本错误。图源14与连续版30SVG未变，原图解实测按先前记录沿用。

## 第7轮：软件差速、局部定位与 TF

使用已安装的 controller_manager 4.48.1、diff_drive_controller 4.42.1、joint_state_broadcaster 4.42.1、RSP 3.3.4 与 robot_localization 3.8.3。两次实测分别在本机域225和226运行，第二次在解压的原创工程目录执行。各次均有7个直接进程正常退出，持久进程各收一次INT，未触发信号升级。

| 项目 | 观测与边界 |
| --- | --- |
| 模型和资源 | 复用 Xacro 的0.08 m半径和0.36 m轮距。GenericSystem active，四个硬件状态接口、两个轮速命令接口可用，四个控制器链式参考名称另列 |
| 严格切换 | 已占用时直接激活 reserve 被拒，状态和资源表不变。显式零速后在同一请求中停用 drive、激活 reserve，实际查询资源持有者 |
| 命令和反馈 | 直行2/2、转弯1.1/2.9 rad/s。核对原始与融合的 v/ω，方差是教学输入。停发后约0.329秒观察到软件轮反馈与原始里程计归零 |
| 时间戳 | 归零后发一条旧1秒的非零指令，在0.35秒内收到35条零轮速，日志明确拒收。新指令使轮速恢复。超时阈值0.30 ROS秒与上述单调观测时延分别记录 |
| TF 与估计 | 静态车体边和两轮活动边来自 RSP。正常时由局部 EKF 提供 odom 边。切换后的0.75秒观测窗口中，0条新时戳原始里程计与3条新时戳预测分开记录 |
| 重复边反例 | 在独立的 TF 输出中分别观察到相同的 odom → base_footprint，保持两路隔离。没有 map → odom、全局定位、IMU 或 GNSS |

主报告为 `validation-evidence/drive-current-validation.json`，解压重跑见 `drive-portable-current-validation.json`。实际早期试跑分别遇到日志写权限和沙箱 UDP 限制。后续修正两处验收夹具：接口列表包含控制器参考入口，测量停更后 EKF 的新时戳频率低于有输入时。保留实际服务回执、进程日志尾部、轮速样本、时戳与报告指纹。

教材引用的上游源码固定于本地清点提交。主要参考快照版本为 controller_manager 4.50.0、diff_drive_controller 4.43.1 和 robot_localization 3.8.4，与运行版本分开。BUNKER、AgroSenseBot、Linorobot2 与 Nav2 只核对应源码和参数。软件闭环的反馈来自同一内存模型，没有测物理制动、实时抖动、未来时戳、完整控制器链、实机或完整仿真。

## 第8轮：真实 Harmonic 传感器与桥

主报告为 `validation-evidence/gazebo-sensors-current-validation.json`。在本机 Harmonic 8.15.0、ros_gz_bridge 1.0.24、cv_bridge 4.1.0、OpenCV 4.6.0 中执行。固定场景仅使用本地 SDF，Gazebo Transport 单独分区，DDS 使用域227和LOCALHOST。解压105文件原创工程后另在域228重跑，结果见 `gazebo-sensors-portable-current-validation.json`。

| 范围 | 实际证据 |
| --- | --- |
| 世界控制与时钟 | 初始 ROS 时间为0，后续观察值为0.655、0.660、0.700 s。四次 ControlWorld 成功，0.40单调秒暂停窗口内时钟和五类采样时戳不变 |
| 单向与 QoS | 五条数据桥有实际 ROS 发布端，无同桥反向订阅。同一 BEST_EFFORT 扫描话题由匹配端收到6条，RELIABLE 端有 RELIABILITY 日志、零匹配、零接收 |
| RGB 与内参 | RGB 96×64、每行288字节、fx/fy约83.14 px。按时戳配到7组 Image、CameraInfo、mono8，frame_id 同为 camera_optical_frame |
| 图像对照 | 40/120 阈值对同帧灰度检出0个边缘像素，红通道检出128个。两个原始PNG、生成SVG与报告指纹均核对 |
| 激光与点云 | 41束中29束有限，中心2.2001345 m。点云41×1、每点32字节、每行1312字节，按字段偏移和端序读出同戳中心 |
| 时间字段与 TF | 逐束与逐圈时长字段都为0，相邻 Header 间隔为0.10 s。按采集时戳将光学 Z 前、激光 X 前的单位点变到台架 +X |
| 退出 | 主试验和解压重跑的 Gazebo、桥各收一次INT，返回0且直接PID消失。早先进程失败按各阶段分开保留 |

SDF 校验通过后，受限环境在 Gazebo Transport 初始化阶段无法建套接字。本机的软件渲染尝试在 EGL 设备选择阶段退出139，指定已有的 NVIDIA vendor JSON 后成功。Python 试跑另发现 Jazzy 无 `qos_profile_clock` 导出，已改为 TimeSource 同样的显式深度和可靠性。第一次 Canny 的灰度边缘为零，现作为同样阈值下的教学对照。实验捕获的运行日志与结果都指向最终脚本版本。

教材定点核读25份文件，相关 Jazzy ros_gz 快照版本为1.0.25，与运行版1.0.24分别记录。cv_bridge 的 Humble 参考只用于解释解码路径，运行包来自本机 Jazzy。验证范围为无窗口固定传感器世界，运动平台、图像标定、动态点云去畸变、建图、导航、全套底盘仿真及硬件留待各自验证。

## 第9轮 · 固定激光地图、定位与规划

主试验在 Jazzy Nav2 1.3.13、Harmonic 8.15.0、ros_gz_bridge 1.0.24 上运行。DDS 域 229 使用 LOCALHOST，Gazebo 使用独立分区和本地 SDF。解压 110 文件的原创工程后在域 230 重跑，逐项核五份运行源文件与包内字节。报告分别为 `validation-evidence/nav2-planning-current-validation.json` 和 `nav2-planning-portable-current-validation.json`。

| 验证环节 | 观测 |
| --- | --- |
| 模拟扫描 | 361 束均有有限回波，中心约 1.9501 m。采集时戳相邻间隔 0.10 s，桥提供 BEST_EFFORT 扫描和唯一时钟 |
| MapServer | 80×60、0.10 m/格、原点 (−4, −3) m。逐格相符，其中空闲 3,215 格、占据 529 格、未知 1,056 格。配置未激活时 GetMap 返回空图 |
| 地图保留与失败 | 晚加入瞬态本地读到旧地图，晚加入易失端匹配但无历史。空路径、缺 YAML、缺图像分别返回 1、3、2，随后 GetMap 均仍返回旧图。重载成功后易失端收到一条新图 |
| AMCL | odom 系初值收到空服务响应，0.30 s 扫描窗内无位姿及全局 TF。map 系近真值初值产生定位和 map → odom，无运动更新产生新位姿。扫描时刻查到激光的 z 为 0.30 m |
| 主图与路径 | 同一起终点下原路径 89 点、4.55 m。启用标记后箱体附近新增 8 个致命格，原路径采到其中 1 格且 IsPathValid 为假。新路径 97 点、4.93 m，服务判真且中心线采样未落入 253/254/255 |
| 规划动作 | 三次成功路径回执。柱内、越界、未知区、无插件和无目标帧五次均先接受，随后 ABORTED，错误码分别为 206、204、208、201、202 |
| 退出 | 三个生命周期节点按顺序配置和激活，逆序停用和清理，共 12 次成功切换。两次运行的五个直接进程均各收一次 INT、退出 0 且 PID 消失 |

`validation-evidence/nav2-grid-captures/` 保存 PGM/YAML 和两份 4,800 字节的原始主图。网页实测图由主图、实际 Path 坐标与单独标注的 SDF 箱体外形绘制。成功规划回执中的 ROS 仿真时长为零，计算耗时需另用单调时钟测量。起点为 AMCL 收到近真值初值后的固定台架样本，路径核验限于当前代价图、离散位姿与最多 0.025 m 间隔的中心线采样。

`source/nav2-planning-revision.json` 列出 39 个定点文件及 SHA。Navigation2 本地快照为 1.3.14，运行版本为 1.3.13。Nav2 教学插件、Linorobot2 与 SLAM Toolbox 按本地源码核读。建图、运动中定位、完整 NavigateToPose 行为树、控制器、连续足印扫掠、底盘动力学与硬件另有验收范围。

## 第10轮 · SLAM 采集、建图、恢复与图定位

主试验运行于 Jazzy SLAM Toolbox 2.8.5、Nav2 MapServer 1.3.13、Harmonic 8.15.0、ros_gz_bridge 1.0.24。域 231 为本机原始运行，域 232 从实际解压的 115 文件原创工程重跑，二者均为 LOCALHOST 和独立 Gazebo 分区。七份运行文件和输入逐个核对 SHA。复跑源码包与交付源码包逐字节相同。

| 验证环节 | 实际观测 |
| --- | --- |
| 采集 | 47 对同戳激光与 Gazebo 位姿，每帧 361 束。各帧回波与盒形几何绝对距离差的 P95 最大 0.02945 m。沿 13.60 m 路线离散移位，各采样窗 0.40 s |
| 建图输入 | 错误扫描帧无位姿。40 帧建图输入有 37 条位姿回执，其余为静止预热。最后扫描 16.00 s，map → odom 时戳为 16.20 s。按扫描时刻查询得到约 0.30 m 的激光安装高度 |
| 地图与误差 | 最终图 137 × 98 格，约 0.05 m/格，空闲 12,318、占据 659、未知 449。末帧输入注入偏差 0.1904 m，SLAM 平面误差 0.01287 m。图标记给出 37 个节点与 38 条约束 |
| 持久化 | 首图前 SaveMap 返回 1。有效地图保存与位姿图序列化均返回 0。新 MapServer 重载后 13,426 格逐格一致，原点 xy 差约 0.354 mm |
| 继续建图 | 缺失前缀、错误模式和成功请求均收到空响应。正确首节点模式在送入新扫描前恢复原图，继续接收 4 帧后保存 41 节点、46 约束的新图 |
| 图定位 | 按已知初始位姿载入原图。7 条留存输入中 4 条有定位回执，最大误差约 0.00496 m。活动图加入 4 个短期节点、9 条短期约束，实时栅格变化 8 格。清空缓冲后恢复全部格值，原图文件指纹一致 |
| 回收 | 两次各有 16 次生命周期切换。六个直接进程各收到一次 INT，退出 0 且 PID 消失 |

`validation-evidence/slam-mapping-captures/` 含原始扫描轨迹、SDF、实际占据格、PGM/YAML 和二进制图文件对。两份运行报告分别为 `slam-mapping-current-validation.json` 和 `slam-mapping-portable-current-validation.json`。首轮实时栅格恒定的错误断言、再测得到的格值转移和清空后的结果收在 `slam-localization-raster-finding.json`。

`source/slam-mapping-revision.json` 列出 35 份固定参考及指纹。SLAM Toolbox 快照标为 2.8.5，Navigation2 快照 1.3.14、ros_gz 快照 1.0.25，后二者与本机运行版本分列。采集是离散移位，里程计偏差由回放注入。轮地运动、运动畸变、强制回环、全局重定位、跨版本图文件兼容性及完整 Nav2 控制仍各需验收。

## ROS 复现

以下从 `ros2-learning-hub` 目录运行。先按两个工作空间 README 安装依赖；安装需要联网，离线阅读不需要。

```bash
source /opt/ros/jazzy/setup.bash
# 构建目录可自行替换；不要复用另一台电脑的二进制安装产物。
colcon --log-base /tmp/ros2-hub-validation/atlas/log build   --base-paths examples/src --build-base /tmp/ros2-hub-validation/atlas/build   --install-base /tmp/ros2-hub-validation/atlas/install --merge-install --symlink-install
source /tmp/ros2-hub-validation/atlas/install/setup.bash
ATLAS_INSTALL_PREFIX=/tmp/ros2-hub-validation/atlas/install /usr/bin/python3 tests/test_examples.py

colcon --log-base /tmp/ros2-hub-validation/foundation/log build   --base-paths foundation-examples/src --build-base /tmp/ros2-hub-validation/foundation/build   --install-base /tmp/ros2-hub-validation/foundation/install --merge-install --symlink-install
source /tmp/ros2-hub-validation/foundation/install/setup.bash
FOUNDATION_INSTALL_PREFIX=/tmp/ros2-hub-validation/foundation/install   /usr/bin/python3 tests/test_foundation_examples.py
```

独立域为通信 197、基础 211、导航假服务端 217，发现范围 LOCALHOST。测试只清理自己创建的进程。基础报告保留前两轮沙箱 UDP 限制和测试夹具错误的历史；最终 15 项全部通过，没有跳过断言。

## 验证边界

- 已验证的是列出的有限输入、解析、数学性质和本机 ROS 协议行为；不是所有依赖版本或任意中间件故障的证明。
- 未运行完整 Nav2/Gazebo/MoveIt 仿真、真实相机链、micro-ROS 主机客户端/Agent、MCU、飞控或实际电机。相应章节提供准备、执行、验收和排错步骤，并标为未运行。
- 数值实验不证明硬实时、真实噪声分布、接触稳定或硬件停车。图解是原创几何/架构示意。
- 原始资料只做下载、子模块/LFS 补齐、目录和完整性核查，未逐段穷尽或批量构建其全部示例。
- 便携包不包含原始参考源码本体、ROS 安装器与仿真镜像；许可证和来源不合并。
