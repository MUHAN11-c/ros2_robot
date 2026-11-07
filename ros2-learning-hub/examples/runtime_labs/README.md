# 通信、调度、参数、时钟与tf2的真实API实验

这些是原创教学实验，目标为Ubuntu24.04 / ROS2 Jazzy。消息、时钟和变换全为合成输入，不连接机器人、相机、仿真器或电机。它们与theory_labs的标准库数学实验分别记录，不能将软件/clock当成已经运行仿真。

从ros2-learning-hub目录执行，先加载环境：

```bash
source /opt/ros/jazzy/setup.bash
# 若未安装，首次准备依赖需软件源；实验本身不自动安装软件。
# sudo apt install ros-jazzy-rclpy ros-jazzy-rmw-fastrtps-cpp ros-jazzy-std-msgs \
#   ros-jazzy-example-interfaces ros-jazzy-rosgraph-msgs \
#   ros-jazzy-tf2-ros-py ros-jazzy-tf2-geometry-msgs
```

| 文件 | 输入、输出与验证范围 |
| --- | --- |
| qos_contract_lab.py | 7个场景；声明策略、发现字段、匹配数及41/42/99样本；独立域213、LOCALHOST、FastDDS，单进程两节点 |
| tf_buffer_lab.py | 8组数值/异常检查；米、弧度、秒/整数纳秒；只写本进程Buffer，不创建Node/DDS |
| clock_timer_lab.py | 受控软件/clock，对照ROS和STEADY timer；不启动物理或仿真世界 |
| async_poll.py | 完整异步加法节点；STEADY timer推进monotonic请求期限，每次最多一个pending请求；服务超时不撤销远端计算 |
| slow_consumer_lab.py | 4组真实发布/订阅；来源、序号、同机单调采样/回调/结束时刻，单位纳秒，统计毫秒；域216、LOCALHOST、FastDDS、BEST_EFFORT |
| executor_group_lab.py | 3组线程/互斥组配置及1组真实客户端Future；起止span、线程ID和并发关系；域219、LOCALHOST、FastDDS |
| parameter_transaction_lab.py | Python pre/on/post共11组；lower/upper/span为有限DOUBLE米，存储与应用快照分开验收；域223、发现OFF，仍初始化RMW |
| service_deadline_lab.py | 默认4例发现/成功/迟到探针，可增加原C++/Python客户端4项；无量纲4+8与独立服务端IPC；域221、LOCALHOST、FastDDS |

```bash
# 断言失败非零；不得用-O关闭实验检查。
/usr/bin/python3 examples/runtime_labs/qos_contract_lab.py --case all
/usr/bin/python3 examples/runtime_labs/tf_buffer_lab.py --json
/usr/bin/python3 examples/runtime_labs/clock_timer_lab.py --report /tmp/clock-timer-validation.json
# 原有demo服务和本章异步客户端分别在两个终端加载相同域/命名空间运行。
ros2 run demo_nodes_cpp add_two_ints_server
# 第二终端：/usr/bin/python3 examples/runtime_labs/async_poll.py
```

QoS实验中的UNKNOWN/depth0只表示图发现未提供该字段，不能推断真实历史深度为0。瞬态本地测试在订阅创建前只发41/42且不补发，late reader应只收到42。负向历史测试在匹配后发送新标记99证明链路正常，再核对旧值未到。负向观察只有0.6秒，不是任意时间或任意RMW的全局结论。

tf2实验使用非零旋转与两时刻平移/旋转插值，验证latest替代采样时刻产生的约0.4142米误差；不会等待网络TF，也不能证明实际标定或时钟同步。

异步节点以0.2秒STEADY timer检查两秒请求年龄，是受调度影响的软期限；等待服务出现之前仍持续轻量轮询，整个进程需Ctrl+C结束。测试用真实服务端点但故意不调度应答，覆盖无clock/固定正clock超时和固定clock正常响应：

```bash
# 仅完整教材工作区提供此自动测试；独立下载工程可按正文手工复现。
/usr/bin/python3 tests/test_async_poll_clock.py
```

报告在工作区validation-evidence/与教材下载的验证记录包中。旧工作空间的构建/互通证据继续保留；新的有限输入成功不扩大为跨机网络、所有执行器配置、所有QoS事件或硬实时保证。

## 慢消费者：测量到处理结束的数据年龄

发布者与消费者为两个进程，避免慢回调同时降低发送timer的频率而掩盖输入压力。每例请求40Hz发送3秒，再排空1.2秒；合成消息包含source_id、递增seq和monotonic_ns。四例为正常处理depth1、80ms处理depth1、80ms处理depth10、depth10加120ms门控。采样时刻为软件生成合成数据的时刻，不能当传感器曝光时刻。

```bash
# 从完整教材的ros2-learning-hub目录运行；默认依次运行四组。
# 外层90秒是进程保护，内部年龄检查和等待都是受调度影响的软期限。
timeout --signal=INT --kill-after=8s 90s /usr/bin/python3 examples/runtime_labs/slow_consumer_lab.py --report /tmp/slow-consumer-report.json
# 只用标准库的23项边界检查，不加载ROS。
/usr/bin/python3 examples/runtime_labs/slow_consumer_lab.py --self-test
```

本次四例各发送119条；深队列慢处理47条中46条结束年龄超过120ms，双时刻门控接受38条、处理前拒绝81条、处理后拒绝0条。自然负载未触发处理后拒绝，不能把零次触发当分支已覆盖。门控先验证有限性/未来时刻，再要求入口年龄加80ms预算不超过120ms，工作结束重新检查。p95包含排空尾部，不当稳态或跨中间件性能基准；下次不要求相同序号缺口或毫秒值。单调时戳只能在同机进程间比较，接受合成结果不证明硬件停车。

## 执行器与真实Future：区分线程、组许可和任务

```bash
timeout --signal=INT --kill-after=8s 90s /usr/bin/python3 examples/runtime_labs/executor_group_lab.py --report /tmp/executor-group-report.json
```

0.35秒受控窗口内，单线程/不同互斥组、两线程/同互斥组、两线程/不同互斥组的最大并发为1/1/2。负例确认heartbeat timer已经ready，并在释放慢回调后能运行。Event.wait释放GIL，演示等待与调度许可，不代表纯Python计算加速。

第四例实际调用AddTwoInts得到12，用户done continuation开始后，协调线程等待响应handler释放client组，再启用同组长timer。done与timer在不同线程受控重叠，而timer占组时client实体仍被组许可阻止。记录限本机固定rclpy路径，不泛化成C++或所有Action continuation；共享状态仍需明确同步。本次四例线程、执行器及Context均清理完成，不能由此保证任意原生阻塞都可被软期限抢占。

## 参数三阶段：存储与应用副作用分开验收

```bash
# --json只输出结果，不覆盖教材保存的原始报告。
/usr/bin/python3 examples/runtime_labs/parameter_transaction_lab.py --json > /tmp/parameter-transaction-result.json
```

lower_m、upper_m、span_m单位均为米，要求有限DOUBLE及-100<=lower<upper<=100，span=upper-lower，比较容差1e-12米。pre合并完整候选并补span，on纯校验，post在存储提交之后更新不可变内存快照。11组包括合法/非法整批、部分字段、逐项部分成功、校验器污染、post错误返回/异常、类型和有限性、回调持有/移除、空pre及漏return。19节点销毁、Context关闭。

两个故意错误的反例仅改合成内存：on提前写缓存后被另一校验器拒绝时，存储保旧但缓存已污染；post抛异常时，存储已经改变而缓存可能仍旧。Python post合同为返回None，返回拒绝对象不能当撤销接口。参数原子性不包办文件、硬件、跨线程或跨节点事务。

未启动参数服务和执行器，不发送跨节点参数请求；Node仍初始化RMW并创建parameter_events，发现范围OFF不等于无DDS实体。C++ pre/on/post签名、句柄与顺序只核固定源码，未运行C++三阶段实验。Python pre返回List，C++以void(vector&)修改；Python注册返回None且Node持有callable，C++应保留SharedPtr句柄。多pre组合也有版本差异，本例每节点只有一个pre。

## 迟到服务：本地收尾不能代表远端未执行

```bash
# 默认四例，不依赖基础包的编译产物。
timeout --signal=INT --kill-after=8s 90s /usr/bin/python3 examples/runtime_labs/service_deadline_lab.py --output /tmp/service-deadline-report.json
# 按VALIDATION.md构建基础工作空间后，增加原C++/Python客户端各两项。
# 前缀是本机新构建的安装目录，不能复用另一台电脑的二进制。
timeout --signal=INT --kill-after=8s 90s /usr/bin/python3 examples/runtime_labs/service_deadline_lab.py --foundation-prefix /tmp/ros2-hub-validation/foundation/install --foundation-source foundation-examples --output /tmp/service-deadline-foundation-report.json
```

每例使用唯一服务名与spawn服务子进程，只发一次4+8请求。默认为未发现、正常、迟到但保留pending、迟到并移除pending。首次响应等待只有0.25秒，慢服务等待0.8秒后仍执行一次并返回12；保留登记后继续spin能接收迟到结果，移除后保存的Future仍未完成。独立IPC记录服务端开始/完成/应答调度返回，它不是ROS服务反馈或取消机制。

本次还运行原客户端四项：服务端3秒工作，原C++/Python客户端各自2秒响应等待后退出1；服务端随后完成一次。两种客户端在服务缺失时也退出1，必须结合日志、是否发现、是否发送和服务端完成事件区分。探针列的观察时刻是首次等待返回，原客户端则是进程退出；所有时刻来自同机monotonic。测试脚本返回0只表示预期故障断言通过，不表示每个请求业务成功。不要因超时盲目重试有副作用的服务。

若只解压atlas_examples.zip，命令中的examples/runtime_labs/应改为runtime_labs/；额外基础客户端需另解压foundation_examples.zip，并显式传入--foundation-source及本机--foundation-prefix。源码包不包含自动测试运行器或ROS安装。先加载环境，再逐个实验；帮助命令不加载ROS。前四个实验的旧证据不因本轮增加内容而扩大范围。
