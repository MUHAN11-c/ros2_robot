# 工作区与续作说明

更新于 2026-11-07（Asia/Shanghai）。当前目标「基于所有参考内容，融合完善内容」已按用户要求暂停。续作先读本文件，再读 `ros2-learning-hub/README.md` 与 `ros2-learning-hub/VALIDATION.md`。

## 2026-11-07 暂停续作存档

- 存档分支为 `learn`。教材源、生成物、示例工程、验证证据、紫樱审查站、现有截图和版本备份随项目保存。上游资料的 `references/sources/`、`archives/`、`state/` 仍在原机器，清单、固定提交及哈希随 Git 保存。换机时单独复制这些目录，见 [资料库说明](ros2-learning-hub/references/README.md)。
- 第 11 轮 Nav2 差速车执行实验已完成本机与解压工程两次验证。五个场景包括到达、取消、目标越界、无效控制器和恢复后到达。两次从发出取消请求到停稳分别行驶约 0.34 m、0.33 m。源码在 `ros2-learning-hub/examples/nav2_execution/`，报告在 `ros2-learning-hub/validation-evidence/nav2-execution-*-validation.json`，原始采样和失败反例同目录保存。
- 第 11 轮教材覆层已经生成，并用 `build_content.py --require-full` 构建了工作区阅读内容，含 60 章、459 个主小节、44 张实测表和 168 份完整文件导出。现有便携 ZIP、截图、审查基线与浏览器验收报告仍对应上一轮。续作时从 `backups/20261107-before-nav2-execution/` 的旧基线对照并刷新浏览器检查、截图和交付包。
- 所有章节的最新目录复查暂停在文件保存路径。当前工作树已加入单章独立 HTML 的目录和节号，以及保存章嵌入连续版时的锚点调整。恢复后先用临时教材副本验证写盘、原文备份与重建，再逐章核查正式版、紫樱版和连续版，补不同章节的桌面、手机截图。当前新增目录改动及第 11 轮教材界面尚未通过这些验收。

## 2026-11-07 参考融合第10轮

- 将 SLAM 的真实仿真扫描、建图、栅格重载、位姿图恢复和图定位融入 9 章。核 35 份固定参考，新增 6 个主小节、5 张实测表、1 组 API、8 道练习、4 份完整源码及 1 张实测图。15 个定点出处去重后，全书来源共 244 条。
- 本机 Jazzy SLAM Toolbox 2.8.5、Nav2 MapServer 1.3.13、Harmonic 8.15.0、ros_gz_bridge 1.0.24。主试验域 231，实际解压 115 文件示例包后在域 232 重跑。核了七份运行文件和输入，交付工程 ZIP 与复跑时相同。
- 47 对同戳仿真激光与参考位姿，每帧 361 束。先按离散位姿采集，再用独立时钟回放。40 条建图输入产生 37 条位姿。路线长 13.60 m，终点注入里程计偏差 0.1904 m，估计误差约 0.0129 m。位姿图有 37 节点和 38 约束。
- PGM/YAML 在新 MapServer 重载后 13,426 格逐格一致。新同步节点从二进制文件对在首帧前恢复原图，继续加入 4 个节点。图定位产生 4 个短期节点、9 条短期约束和 8 个变化格。清空定位缓冲后原图逐格恢复，磁盘原图指纹一致。保留最初夹具误以为实时栅格恒定的反例。
- 证据在 `ros2-learning-hub/validation-evidence/slam-mapping-*-validation.json`、`slam-mapping-captures/` 与 `slam-localization-raster-finding.json`。本轮重建前的正式与审查基线位于 `ros2-learning-hub/backups/20261107-before-slam-publication/`。
- 下一步沿真实 NavigateToPose 行为树与控制器接运动台架，记录目标执行、取消及异常退出，再继续机械臂、嵌入式与其余参考。SLAM 采集窗内台架静止。轮地运动、强制回环、远处重定位和跨版本图兼容性仍需对应证据。参考融合目标保持 active。

## 2026-11-07 全章目录审查

- 正式阅读器与紫樱审查版共用正文目录逻辑，左栏专用于学习目录。主小节统一为「章.节」，下级实测表和图解使用「章.节.项」。API 与练习按正文归组，正式页右上角可进入同章编辑。
- 两个入口在 1440、390 和 320px 各核对 60 章、445 个主小节及 1,108 段主小节正文。桌面逐条定位正式版 1,115 个链接和审查版 1,112 个链接，连续版修复重复节号并增加 60 个无脚本目录。
- 逐章数据见 `ros2-learning-hub/validation-evidence/offline-reader-current-validation.json` 与 `ros2-learning-hub/design-review/validation/browser-report.json`。截图在 `ros2-learning-hub/design-review/screenshots/`。本轮调整前的正式阅读器、连续版和审查记录备份于 `ros2-learning-hub/backups/20261107-before-chapter-outline/`。
- 该轮已核查的目录规则用于后续章节融合。增补后的当前计数以正式和审查浏览器报告为准。

## 2026-11-07 参考融合第9轮

- 核对 39 份固定文件，将地图读取、AMCL 初始化、主代价图与 NavFn 实测融入 9 章。新增 7 个主小节、4 张实测表、1 组 API、8 道练习、4 份完整文件和 1 张实测图。15 个定点条目按原文地址去重，正文来源共 230 条。
- 使用本机 Jazzy Nav2 1.3.13、Harmonic 8.15.0、ros_gz_bridge 1.0.24 与固定激光。主试验域 229，实际解压 110 文件示例包后在域 230 重跑，复核 5 份运行源文件和输入。Navigation2 固定参考为 1.3.14。
- 80×60 占据图逐格相符，非对称柱用于检查行方向。晚加入易失端先没有历史图，成功重载后收到新发布。空路径、缺 YAML、缺图像分别返回 1、3、2，GetMap 证实旧图保留。错误初值帧有服务回执但无 AMCL 位姿或全局 TF，map 系近真值初值后能按实际扫描时刻查询。
- 固定同一起点与目标。障碍层开启后在箱体附近新增 8 个致命格，原 4.55 m 路径采到 1 格且有效性检查失败。新路径 4.93 m，中心线和有效性检查通过。五类规划错误均先接受，后返回 ABORTED 和各自业务码。两次各完成 12 次生命周期切换和 5 个直接进程回收。
- 上一版正式教材的 7 项审查基线及关键验收快照在 `ros2-learning-hub/backups/20261107-before-nav2-planning/`。两个报告和原始 PGM/YAML、master 栅格均随验证记录交付。原始第三方快照与许可独立保存。
- 后续补运动数据的 SLAM 建图与位姿图恢复、真实行为树和控制器执行，再继续机械臂和嵌入式参考。当前范围是固定台架的地图定位与规划，连续足印、运动定位、控制、建图和硬件仍待相应证据。参考融合目标保持 active。

## 2026-11-07 参考融合第8轮

- 核25份固定版本文件，形成14个定点出处，将真实 Harmonic 传感器实验接入仿真、感知、TF、QoS、录放、SLAM、Nav2 七章。新增3张实测表、1组API、9道练习、3份完整文件和1张含真实采样的图。
- Harmonic 8.15.0、ros_gz_bridge 1.0.24，以本地 SDF 启动 Ogre2 EGL 服务端。DDS 域227和解压源码重跑的域228分别隔离，Gazebo Transport 另有分区。初始 ROS 时间为零，ControlWorld 四次回应成功。暂停后的0.40单调秒内，时钟及五类传感器/处理样本采集戳未变，恢复后推进。
- 主报告96×64 RGB，每行288字节，匹配7组图像、内参、边缘。fx/fy约83.14 px，同阈值的灰度和红通道分别0与128个边缘像素。实际 PNG 逐字节嵌入图解；源码校验报告、图片与图解指纹。
- 激光41束中29束有限，中心约2.2001 m；同戳点云41×1，point_step=32 B、row_step=1312 B，读字段偏移验证中心。零 scan_time/time_increment 与0.10 s采集戳间隔分开解释。两次按采集戳的光学/激光单位点查询均到台架 +X。
- 同一 Best Effort 提供端，匹配订阅收到6条，Reliable 匹配和接收均零。软件 EGL 设备初始化失败、Jazzy Python 时钟 QoS 常量缺失与灰度阈值反例分别保留。两个长期进程各一次INT，返回0并回收。
- 上一版正式基线备份于 `ros2-learning-hub/backups/20261107-before-gazebo-sensors/`。软件底盘与仿真两轮的定点出处可从章末打开本地原文，两个离线ZIP按便携模式显示出处元数据。
- 下一步沿地图、定位、代价地图、规划与动作反馈逐层验证，继续查机械臂、嵌入式和剩余参考内容。固定台架未测运动畸变、建图、完整导航、实物或全量参考融合，目标保持active。

## 2026-11-07 参考融合第7轮

- 复用模型章 Xacro，把 ros2_control 的 GenericSystem、差速控制器、关节广播器、RSP 与局部 EKF 串成软件台架。Jazzy 本机域225通过，解压101文件原创工程后另在域226通过。两个报告各记7个直接进程退出与源码指纹。
- 两轮速度资源由控制器独占。STRICT 拒绝直接激活 reserve，保持原快照；显式零速后同一请求转移资源。`ListHardwareInterfaces` 还列出控制器的链式参考入口，应与硬件接口区分。
- 直行两轮为2/2 rad/s，转弯1.1/2.9 rad/s。停发到软件轮反馈和原始里程计都归零，本次观测约0.329秒。旧1秒命令另有拒收日志和0.35秒零反馈窗口；随后新指令恢复。没有测物理停车。
- 正常阶段仅EKF发局部 odom 边，RSP发车体边。换到 reserve 后0.75秒无新原始时戳，EKF仍输出3条新时戳预测。两个同名TF边分别在隔离话题观测，没有合并进正常TF树。
- 将17份核读并匹配SHA的上游文件接入10个定点出处。控制框架、差速、硬件、定位、导航项目、模型共6章修订，新增3实测表、1组API、8练习、5完整文件。原文与读取基线的备份在 `ros2-learning-hub/backups/20261107-before-drive-fusion/`。17份核读范围见 `source/drive-fusion-revision.json`，第三方许可保持独立。
- 继续依赖实际参考和运行条件补仿真桥、感知、地图定位与导航规划，再延伸机械臂和嵌入式。已有主题映射和本轮软件链路不能证明全部参考内容已融合。目标保持active。

## 2026-11-07 教材文件直存与原文备份

- 编辑模式“保存到教材”或Ctrl/Cmd+S写入 `source/local-edits.json`、`dist/local-edits.js`、单章HTML与Markdown。文件页使用浏览器目录授权；`python3 ros2-learning-hub/scripts/serve_local.py --editable` 提供本机同源保存。常规服务保持只读。浏览器暂存与已写盘的提示分开；无目录能力时可通过备份迁移草稿到本机服务。
- 先备份首次原文及将被覆盖的章节版本，再写文件。原文在 `backups/local-edits/original/`，历史在 `backups/local-edits/history/`。校验教材基线、章节ID和预期版本；备份失败不写教材，写入失败回滚已触及文件。正式阅读器和审查版均读取磁盘修订；构建从源修订生成全文Markdown与连续版。原教材结构化数据、ROS工程和第三方仓库独立保留。
- 独立副本8项实测覆盖浏览器Ctrl+S真实写盘、逐字节原文备份、历史与冲突、文件失败回滚、空白浏览器断网恢复、隔离目录句柄以及实际重建。后端另5项文件边界通过。未自动化原生目录选择；验收数据没有写进实际教材。当前修订表为空，原文备份在首次实际保存时创建。
- 7项正式原教材产物核原SHA，3个读取器入口文件接入磁盘修订，旧版保存于 `ros2-learning-hub/backups/20261107-before-file-saving/`。本轮审查包保留紫樱、截图和本机编辑服务；完整源构建仍在工作区。持续目标保持active。

## 2026-11-07 鸣神文档笔记站：独立可视化审查版

- 双栏文档笔记审查版位于 `ros2-learning-hub/design-review/`。按用户反馈恢复历史吉祥物「紫樱」，本轮再将学习目录独占左列并延伸到窗口底部；首页、目录、图解、笔记、资料、素材与审查入口集中在顶部单行。手机顶栏可横向滚动，章节树为抽屉，关闭后不参与键盘焦点。
- 当前章自动展开小节，左栏与顶部目录按正文顺序显示。445 个主小节采用 `章.节`，259 个下级标题归入各自父级，其中 68 项采用 `章.节.项`。在 1440/390/320px 各核对 60 章的编号、层级、开头段落和双目录，桌面逐条定位 1,112 个锚点。章名、二级和三级标题改动后同步到目录。章级明细见 `design-review/validation/browser-report.json`。
- 右上角的编辑模式按最新反馈改为所见即所得：沿用当前正文，点击段落、标题、列表、单元格、练习题目和代码直接修改。可加粗/行内代码、撤销重做、中文输入、仅文本粘贴；450ms自动保存、Ctrl/Cmd+S、跳转前保存、刷新恢复、恢复原文与撤销、草稿搜索与真实导出。公式和图解保留组件结构，实验在编辑状态下仍可交互。Markdown移入可选源码弹窗，点击应用才更改正文；旧Markdown草稿仍兼容。
- 正文排版修改使用带正文指纹的稳定字段，独立存入 `visualDrafts`，与旧 `drafts`、笔记和进度共同备份；源码应用包含已有修改并清掉旧字段。每章修改上限50万字符，存储失败明确显示且可导出。指纹不匹配时保留旧记录并提示。来源、许可、正式教材保持独立。
- 入口 `design-review/index.html`，`#/review` 为六场景审查台、`#/gallery` 为素材画廊。复用现有60章、代码、公式与出处，原教材版本保留；页面样式仍处于独立视觉审查。原始第三方资料本体独立保存。
- 从提交 `266791959045aadc4331755ac6312fdc94da6706` 恢复紫樱插画、头像与贴纸共7个WebP文件，逐字节核对，CC BY-NC 4.0出处独立记录；头像现位于顶部导航。旧角色图与旧审查版本归档在 `.qa/`。本次原排版编辑修复了长英文练习题的手机溢出，失败与重复输入等待的检查历史保留。
- 当前导航与模式验收以 `design-review/validation/` 为准。覆盖 390/320px 共 140 条阅读路由、120 条章节编辑路由、文件协议断网操作、草稿与笔记恢复、备份与存储失败导出。21 张截图含 Nav2 实测图、工作空间、状态估计、深色模型和手机动作章。数据层 18 项检查、独立副本 8 项文件保存和有限几何视口验收沿用原记录。
- `source/component-contract.json`仅核对Peach v1.0.0中的ros2_web_link 0.8.3源码/声明与8个SHA。SceneView/ImageView/SeriesPlot/GraphView/工作台仍为接口预留，未复制或运行SDK，未启动ROS、回放、相机、仿真或硬件。实验几何与原教材产物SHA保持相应基线；读取器接入文件修订的变更单列。
- 当前包及实际解压检查以 `design-review/deliverables/` 为准；包含审查站与所需dist副本，不包含用户浏览器草稿、原始参考仓库或ROS依赖。仍处于独立样稿修订与可视化审查，未整合正式网站；持续内容目标active。

## 2026-11-07 持续迭代第6轮

- 修复模型章只给URDF却引用未提供Xacro的缺口，正文和快捷步骤同源指向model_labs。新增完整learning_description资源包、Xacro/launch、标准库数值自检和无GUI driver；原最小URDF逐字节保存并实际check_urdf解析。
- 本机RSP3.3.4/xacro2.1.1实际构建、普通复制安装后从空cwd启动两配置：默认r=0.08m/轮距0.36m、覆盖0.10/0.40m，7link/4fixed/2continuous/5实体惯量，base高度0.14/0.16m。参数回应后才晚加入Listener，固定边可得，活动边在无位置前不存在。
- 共6个JointState阶段：四有效位置阶段、一非法长度拒绝、一协议合法velocity-only但RSP跳过；两个0.25s窗口有日志且TF时戳维持旧值，后续位置恢复。两配置共6光学点通过，区分点含平移与方向只旋转；frame_prefix只改TF frame，不改关节键。
- 负Iyy夹具真正check_urdf为0，自检为1，结构可解析不代表物理数值合格。3项CLI与完整命令/输出另存边界报告。10父命令中8正常0、2预期拒绝1，两RSP子PID消失；父SIGINT/原生挂起、非零活动origin、根惯量运行、GUI/动力学/硬件未测。
- 正式函数打包/解压的95文件独立源码工程，从atlas_examples根直接跑模型driver（域220）也通过；8源/输入逐字节等于原文与ZIP。此前误填临时cwd时没有启动进程，随后按真实记录路径执行。不是跨机二进制或完整离线依赖验证。
- iteration6-model-source-review批准两核心报告、portable补充与生成器SHA，15一手来源/7教材出处分列；xacro同版快照仍有动态arg名补丁差异。新增4表、6完整文件、8练习与1API；.urdf/.xacro加入XML源码索引，构建最后应用iteration-6覆层。
- 当前60章、12实现对照、19API、49公式、308练习、148完整文件导出、24实测表、192教材出处；图源14项、连续版30SVG未变。原创examples实际7个ROS包，首次构建仍只发现src两通信包；模型包另有实构建证据。
- HTTP390/320px共170路由、模型单章真实下载、断网60章/无脚本24表及实际解压网站ZIP检查通过。最终包按同轮delivery与SHA256SUMS核对；后续继续逐章核读，不重复已过且未变实验。持续目标active，参考原文与许可独立，不将目录/条数当正文穷尽。

## 2026-11-07 持续迭代第5轮

- 新增bag_labs：真实CLI录制3组、关闭后读回、暂停就绪后CLI回放2组及双存储字段探针均通过。SQLite系统时间、MCAP软件时间和静态volatile反例分别13/13/12条；回放完整6/6/1和筛选6/0/0分别观察。
- 当前RCL Clock.started要求严格正值，不是任意一条clock：无clock和仅零clock时三个数据订阅均为零，门前四条易失input未补录。Header、RMW source、记录recv及消费者ROS时间分别说明；显式Writer的7/10/9秒不是网络延迟测量。
- 四参数Writer同一bytes核双后端：MCAP logTime/publishTime均保存，当前SQLite仅有接收timestamp；Python read_next只给recv。noChunking只用于单消息字段探针。安装与快照虽同0.26.11，Player会话结束取消clock补丁仍有差异；CLI自然退出不证明节点保活行为。
- 失败历史保留：首轮误用另一次序列化SHA比较CDR对齐padding，次轮引用Jazzy不存在的QoS名称。现核完整字段，八个常规子进程均exit0、无升级信号、PID消失；父SIGINT/原生挂起未注入。6项帮助/非法参数与相对新路径双后端另实测。
- 独立iteration5-bag-source-review批准当前两报告与生成器SHA，核7项源/输入和3Python边界指纹，24一手来源记录、9教材出处分别列示。新4张表、6完整文件、8练习；修3个未带--clock命令旁注并扩原API。build_iteration5_material生成最后覆层，构建绑定审查与报告。
- 当前60章、12实现对照、18API、49公式、300练习、142完整文件导出、20实测表、185教材出处。图源14项、连续版30SVG未变；HTTP390/320px共170路由、断网60章/无脚本20表与实际解压ZIP检查通过。最终包按同轮delivery与SHA256SUMS核对，不含原始第三方资料本体。
- 发现历史汇总浅拷贝误把r4实验数据写入r3，已按独立交付快照恢复r3的118文件/274练习/8表，只留可证交付统计；新历史用deepcopy，原始实验报告不改。
- 其余章节继续逐项核读，不重复已过且未变实验；持续目标active。原海龟/真实采集、Foxglove/tracing、压缩/吞吐/恢复、Docker、完整仿真及硬件仍按各自范围标未运行。

## 2026-11-07 持续迭代第4轮

- testing_policy保留原三个文件逐字节基线：旧4项pytest通过但6个新合同反例暴露NaN时戳/期限等缺口。修订整数ns/有限速度策略31项和原talker活动/退出2项实际通过；原policy/test两块由第4覆层sourceFile替换，不覆盖旧注释基线。
- 新增生命周期与注册测试各1个包。生命周期10场景/21窗口/17假资源释放，ERROR恢复与原请求success分别记录；普通回调、LifecyclePublisher、finalized和进程生死分开。注册测试3个CTest/13细分/16聚合；受控缺READY默认test可0，严格test与result为1，零结果不当通过。
- 部署只读审计原安装与保留链接副本：24普通文件、18外链；副本同SHA/链接仍依赖原source/build/underlay，副本未运行。宿主原Config节点source+exec单次TERM正例通过；Docker默认CMD直达镜像内节点，entrypoint注释及argv边界修正，Docker本身未构建/运行。
- 四报告由iteration4-source-review approved并绑定当前SHA，核23项源文件/输入指纹与独立文档/ELF/XML等。build_iteration4_material生成iteration-4-revisions并最后应用，构建核审查SHA；第3轮绑定报告不改。失败夹具、双SIGINT修订与初始路径问题历史保留。
- 当前60章、12实现对照、18API、49公式、292练习、136完整文件导出、16实测表、176教材出处。新参数来源图核第3轮实测且绑定SHA，图源共14项（12常规、2回退），连续版30个SVG实例。
- 图解QA发现交互端旧目录漏新图，现正式构建同步figure-data与正文同一清单，check_content校验相等。12常规图24处位置、两交互与手机检查通过；HTTP390/320px共170路由、断网60章/无脚本30SVG及16表通过。最终ZIP按同轮delivery记录与SHA256SUMS核对。
- 原创工程examples现6个ROS包，首次通信构建仍只扫描src两包，其余按目录README准备依赖。后续继续核读其他章节，不重复已过且未变实验；goal仍active，原始资料未逐段穷尽，Docker/完整仿真/硬件等未运行边界保持。

## 2026-11-07 持续迭代第3轮

- 剩余3项审查需求已形成实测资产：Count10组/24目标、组件5组（11动态gain、7有效配置、4失败加载及3官方容器），另有两次父driver SIGINT清理验证。原基础10包不改，新增动作/组件包各1；源码、报告和范围见各目录README及VALIDATION。
- 官方manager默认关闭自身参数服务，thread_num只读另由显式开启服务的observable_manager验收；NodeOptions/Context CLI/管理节点当前参数/加载局部参数分别观察。未知extra不等于支持开关，严格GetParameters可整批空values；原文“固定4线程/isolated默认每组件MT”按版本实现纠正。
- 真实中断审查发现并修复父/worker重复SIGINT；最终先等待已有组信号生效，server正常exit0，未补信号，所有自建进程回收。中断goal没有得到业务终态，不能计作CANCELED/ABORTED或停车。旧双INT栈和夹具失败完整保留。
- `scripts/build_iteration3_material.py`要求两份passed报告、所有源码SHA及独立审查approved/对应报告SHA一致，再生成`source/iteration-3-revisions.json`，最后应用；构建另核审查文件SHA。新增7个固定一手出处，不混同安装版本与参考快照。
- 当前60章、12实现对照、15API表、49公式、274练习、118完整文件导出、8实测表、168教材出处。新增11个完整sourceFile；原有331处注释/64文件的历史范围不冒充这些新代码数量。
- 修复官方Fibonacci补充命令与Count注释字段混淆、练习长API名在320px溢出；首次通信构建限定examples/src，附加包单独构建。独立基础ZIP补自身Apache许可证，第三方资料保持独立。
- 断网60章/无脚本8张表与HTTP390/320px共170路由通过；最终ZIP需按同轮delivery-current-validation.json和SHA256SUMS核对。持续目标active，后续继续核读其余章节和改善细节；不要重做已经通过且未变的实验。

## 2026-11-07 持续迭代第2轮

- 新增慢消费者4组、执行器/Future4组、Python参数三阶段11组、迟到服务8项，共27组主场景，均按记录范围实际运行。原始事件、版本、输入、源码SHA和清理证据分别保存；不是27种完整机器人系统验收。
- 第2轮正文素材由`scripts/build_iteration2_material.py`读取四份通过的报告生成；`source/iteration-2-revisions.json`最后应用。报告或源码变更会触发SHA检查，必须先核读结果再重建素材，不能只刷新标签。
- 新增5张实测表、4个sourceFile完整源码、10道练习及第13组参数API表。当前60章、12实现对照、13API表、49公式、261练习、107完整文件导出条目，161教材出处。正文/Markdown/连续版/源码ZIP同源。
- 修复Markdown表格行之间空行破坏渲染的问题；全文与单章均用连续表头/分隔行/正文行，转义管道和单元格换行。新增Python2项、JavaScript1项和真实浏览器下载比对。
- 浏览器断网60章、无脚本5张实测表、HTTP390/320px共170路由通过。剩余审查待办3项：Count忙碌拒绝/ABORTED、组件NodeOptions参数边界、isolated容器与thread_num。22项中19项按各自范围修订；目标继续active。
- 不扩大实测结论：慢消费者自然负载未触发处理后拒绝，23项边界检查另列；执行器用Event.wait释放GIL；参数C++只核源码；服务IPC不是ROS取消。完整仿真/硬件未运行。

## 2026-11-07 持续迭代第1轮

- 新增runtime_labs四个完整源码：QoS七场景、tf2八组、软件clock三阶段、稳态轮询异步服务；全部按各自明确范围实际运行。
- 新增第12组QoS API表与正文内细节，修正Python/C++实体所有权、服务0/1退出码语义、ROS暂停后的检查路径、tf2 timeout时钟条件、view_frames/clock_probe注释及快捷回放主题筛选。
- 当前为60章、12组实现对照、12组API、49公式、251练习、103条完整源码导出。新代码通过sourceFile直接从examples加载，哈希校验，正文/Markdown/源码包同源；Markdown现在逐章保留验证范围。
- `source/iteration-revisions.json`在navigation-revision之后应用；支持appendSections/appendExercises等，不改已有注释索引。生成物只由构建器产生。
- 第1轮当时的待办为慢消费者新鲜度、执行器矩阵、参数阶段、迟到服务应答、Count忙碌/失败路径及组件部署；当前完成状态以第2轮与`validation-evidence/iteration-worklist.json`为准，历史审查报告保留不覆盖。
- 当前goal仍active；继续按上述待办和新证据推进，不重复下载原始资料或重做已经通过的实验。

## 当前可用交付

- `ros2-learning-hub/dist/index.html` 为正式左章节树、右正文阅读器，60 章，12 组实现对照，23 组 API 表，49 组公式，341 道练习与答案，39 张实测表。
- `dist/book.html` 为无脚本单文件连续版，内嵌 49 组 MathML 公式和 36 个上下文 SVG 实例。`dist/downloads/ros2-learning-guide.md` 为 Markdown 全文。
- `dist/reader.js`、`reader-library.js`、`reader.css`：正式代码。旧 `layout-preview.*` 和 `work-in-progress/` 只保留历史设计起点；不再有必须从这些草稿恢复的缺失功能。
- 本文、公式、API、不同实现、案例、实验、排错和答案在同章展开，外链仅作出处。全文搜索、旧 `#/lesson/id` 路由、收藏、进度导入导出、主题、打印、代码复制/标签/并排、390/320px菜单均已验收。
- `deliverables/ros2-learning-hub-offline.zip` 与 `SHA256SUMS` 是本轮重建教材。包内 `environment.js` 标为便携模式，避免提供不存在的原始资料链接；本地工作区保留原文入口。
- `dist/downloads/` 含原创通信和实验工程、基础 10 包工作空间、164 份完整文件导出、来源和覆盖 JSON 及验证记录。完整文件依赖章节所述环境，部分源码在不同章节重复出现。

## 原始资料与来源边界

- 新下载99个来源条目、151份版本快照，复用原有11份快照；合计110来源条目、162快照。rttest/realtime_support有一组同归档别名，不能声称99门独立课程。子模块12份、LFS7个均按固定提交和哈希补齐。
- `references/manifest.json` 记录来源、分支、提交与许可；`documents.csv`、`packages.csv` 和两个SHA256清单保存清点证据。原始源码约数GiB，保持原样和独立许可。
- `references/sources/`、`archives/`、`state/` 被Git忽略，教材ZIP不含其本体。换机须额外复制整个references和所需原有参考目录；仅拉Git不能恢复这些下载。
- `source/reference-coverage.json` 记录三个指定教程627个实际文档条目（527教学正文/附录、100辅助），分开标记核读范围、概览、延伸和缺项。Robotics_Tutorial导航395链接有10个缺失目标；没有冒充完整收录。
- `source/local-library.json`、`dist/reference-data.js` 提供仓库/版本/7122文档元数据；站内原文采用只读白名单API。原始Markdown以文本呈现，不把上游正文重新许可。
- `source/topic-depth.json` 是构建器生成的本站实际章节范围；不是原教程逐段穷尽证明。

## 内容构建关系

- 核心素材：原44章JSON，`math-foundations.json`、`applied-robotics.json`。
- 先应用 `code-annotations.json`（331 位置，64 原创工程文件），再按 `scripts/build_content.py` 的顺序应用正文覆层。`slam-mapping-revision.json` 在 Nav2 覆层后应用，绑定本机和解压两份报告。五张实测表及图解均核对证据指纹。
- 审查修订包括 DDS/Zenoh 安全边界、看门狗NaN/时间门控、ros2_control关节注释、图像依赖、micro-ROS host客户端链、参数逐项/原子设置与稳态时钟。
- 导航两章共用 `examples/navigation/bounded_navigation.py`，各阶段使用monotonic软期限，目标UUID取消、不隐式发布initialpose，unknown不会被当作拒绝或停车。正文、章节ZIP和源码有同源检查。
- 公式转换由 `scripts/math_render.py` 和本地 `scripts/vendor/latex2mathml` 完成，`book_export.py` 内嵌 SVG 并唯一化 ID。17 个 SVG 包含 15 个常规图和 2 个连续版回退图。

## 本轮实际验证

见 `ros2-learning-hub/VALIDATION.md` 与 `validation-evidence/`。已分轮构建通信2包、基础10包、动作/组件/生命周期/测试/模型各1包；通信5项、基础15项集成、导航12类隔离假服务端协议场景、数学/应用16实验、前端基线17项单元、表格格式及内容/导出/浏览器检查通过。基础报告保留先前沙箱限制和夹具错误，最终无跳过项。

浏览器HTTP检查覆盖390/320px共170条路由；文件协议断网60章、无脚本连续版和两种图形交互均通过，未产生外部请求或脚本错误。320px导航长路径溢出已经修复。

没有启动完整Nav2/Gazebo/MoveIt仿真、真实相机链、micro-ROS Agent/host客户端、MCU、飞控或电机。相应教程的执行与验收方案已写清，不能把这些计划当成已运行。原始第三方工程没有批量构建。物理停车不由动作取消或进程退出证明。

## 打开和重建

工作区根目录：

```bash
# 全部教材离线可用；配套服务额外支持站内读取原始参考文件。
python3 ros2-learning-hub/scripts/serve_local.py
```

访问 http://127.0.0.1:8766/；也可直接双击正式index或book。服务仅监听本机，Ctrl+C关闭。本轮验收临时服务结束后不常驻。

教材目录：

```bash
cd ros2-learning-hub
python3 scripts/build_theory_figures.py
python3 scripts/build_content.py --require-full
python3 scripts/package_offline.py
python3 tests/check_content.py
```

完整数值、ROS和浏览器复现见README/VALIDATION。Playwright模块通过 `PLAYWRIGHT_MODULE` 指定，不依赖旧电脑绝对路径；`PLAYWRIGHT_BROWSERS_PATH` 可指定隔离Chromium目录。临时ROS构建位于 `/tmp/ros2-hub-validation`，换机应从保留源码重建，不迁移其安装产物。

## 持续约束

始终中文；代码详细中文注释说明输入输出、单位、参数、顺序和边界。继续优先编辑ros2-learning-hub和任务文档，不覆盖第三方原文与许可。用户已认可双栏设计并要求完成内容，不需要再次设计确认。

早期 `TRANSFER_*` 文件描述 2026-11-06 快照。续作状态和当前交付版本以上方存档为准。增加仿真或硬件证据时，按各章验收步骤记录实际结果。
