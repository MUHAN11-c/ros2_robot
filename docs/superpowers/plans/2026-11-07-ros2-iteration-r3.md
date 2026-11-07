# 持续内容迭代：第3轮

目标保持“持续迭代完善内容和细节”，active。上一轮为实质进展，本轮从工作树和真实运行继续补齐原审查留下的Count与组件三项需求；不将这些有限实验当作原始资料逐段穷尽或完整机器人验收。

## 内容与实验

- Count：保留基础10包及原两语言服务端，新增独立learning_count_fault_lab。10组、24目标UUID验证busy后取消/自然完成再恢复、非法0/21、默认故障关闭、两语言ABORTED/completed6后短目标成功。拒绝没有执行Result，原因日志与仅含completed的接口分开。
- 组件：新增runtime_lab_components，同一Config类独立/装载入口输出等价；5主场景包含11动态gain、7有效配置、4失败加载及官方三容器。Context CLI1.8、管理当前1.2、加载局部1.5分别验收；未知extra不支持任意NodeOptions setter，严格GetParameters可整批空values。
- 容器：single/mt2/isolated默认每组件ST的并发1/2/2，慢窗口heartbeat0/17/17，记录同PID/线程/成对span。管理参数服务默认关闭，thread_num只读另由显式开启服务的observable_manager验收。没有把额外isolated MT、崩溃或零复制当实测。
- 两次真实父SIGINT生命周期检查：组件约0.516s退出130、自建进程消失；Count发现并修复父组INT后worker重复INT，最终worker不补信号、server正常exit0，约0.662s回收。旧exit-2异常栈和夹具失败保留。Context关闭后的警告不证明业务结果送达，中断goal仍无终态/Result证据。

独立来源审查绑定当前两份报告SHA及15份源指纹，保存31项一手来源、安装与快照版本差异。`build_iteration3_material.py`要求approved与对应报告SHA，再核源码；构建还核审查文件SHA。不是仅文件存在或绿色标签就算通过。

## 网站修订

新增3张实测表、11个完整sourceFile、2组API表和13道练习；当前60章、12实现对照、15API、49公式、274练习、118完整文件导出、8实测表及168教材出处。源码条目包含教学副本，不代表118个独立项目。

修复Fibonacci补充命令误套Count字段注释；未知参数/取消竞态/ABORTED零进度等边界在章内说明。首次通信构建限定examples/src，经实际colcon list确认仅atlas两包，避免扫描新增依赖包；扩展包单独准备环境。基础独立工程ZIP补自身Apache许可证，上游源码和许可保持独立。

手机验收实际发现320px练习长API名撑宽页面，定位为summary文字换行缺口；只修标题换行后重新通过170条路由。表格与长代码继续在自身容器滚动，没有用整页裁剪隐藏内容。

## 实际交付检查

- 内容构建及检查通过，118条完整文件从章节ZIP逐字节对照，sourceFile另与原创工程ZIP比较；Markdown单章、全文、无脚本HTML同步。
- HTTP交互、组件章节实际下载、390/320px共170路由通过；file断网60章，49 MathML、29 SVG、8张实测表，无远程请求或脚本错误。
- 实际解压本轮ZIP执行delivery-checks通过；便携原文缺失提示、复制回退、无脚本连续版及两窄屏通过。最终包再次核被测14个核心指纹及所有当前站点文件字节。
- 未改公式/数值模型或原基础代码，不重复其已通过且未变的运行；新的C++包、协议和中断场景均有实际构建/运行证据。

22项原独立审查已按各自范围修订，详细状态见iteration-worklist.json。持续目标仍active，继续核读其他章节和学习细节；C++参数三阶段、扩展Count取消业务、isolated额外MT分支、完整仿真、跨机和硬件仍明确未运行。没有发布、托管登记、提交/推送或改动第三方参考源码。

预览为ros2-learning-hub/deliverables/iteration3-composition-preview.png，包与最终SHA以deliverables/下当前文件为准。本轮临时服务验收后关闭；日常打开方式见README和CONTINUE。
