# 生命周期状态、假资源与输出门控实验

本目录是完整原创 C++ ROS 包 `runtime_lifecycle_lab`、Python 验收 driver 和软件假资源实验。目标环境为 Ubuntu 24.04、ROS 2 Jazzy、系统 `/usr/bin/python3`。假资源只分配 16 字节内存；诊断消息是无量纲递增序号，不连接任何相机、串口、电机或仿真器。

## 构建和复现

从 `ros2-learning-hub` 根目录执行。依赖由包内 `package.xml` 明确列出；本轮在已安装依赖的环境构建。新报告显式放 `/tmp`，不会覆盖教材按 SHA 绑定的验证记录。

```bash
source /opt/ros/jazzy/setup.bash
colcon --log-base /tmp/ros2-lifecycle-labs/log build \
  --base-paths examples/lifecycle_labs/runtime_lifecycle_lab \
  --build-base /tmp/ros2-lifecycle-labs/build \
  --install-base /tmp/ros2-lifecycle-labs/install --merge-install --symlink-install
source /tmp/ros2-lifecycle-labs/install/setup.bash
LIFECYCLE_LABS_INSTALL_PREFIX=/tmp/ros2-lifecycle-labs/install \
  timeout --signal=INT --kill-after=10s 180s \
  /usr/bin/python3 examples/lifecycle_labs/validate_lifecycle.py \
    --build-root /tmp/ros2-lifecycle-labs --report /tmp/lifecycle-local-result.json
```

`--install-prefix` 可指定当前机器重新构建的任意安装前缀，`--case` 可只运行一个主场景。默认域 229、Fast DDS、`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`；清除旧 `ROS_LOCALHOST_ONLY` 与静态远端 peer 配置。每例创建唯一命名空间、新 worker 进程组和自有 C++ 进程，正常清理只给保存的 PID 发信号，中断处理只覆盖自建组，不操作用户节点或 ROS daemon。

无 ROS 环境也能读取参数帮助，所有 ROS 导入都位于参数解析之后：

```bash
/usr/bin/python3 -I examples/lifecycle_labs/validate_lifecycle.py --help
```

服务等待默认四秒，是依赖执行器推进的软期限，不会抢占任意长原生回调。每例父进程默认二十五秒保护，整轮命令另有外层 timeout。worker 自建 Context，显式采用 `SignalHandlerOptions.NO`，由 Python 捕获 KeyboardInterrupt；它不要求 context.ok 已变成 false。中断后父 driver 不再运行后续场景；worker 记住收到的中断，先等已收到组 SIGINT 的 C++ 孩子收尾，不盲目补第二次 SIGINT。

## 四类证据分别表示什么

节点名默认为 `fake_resource`。driver 将它放入独立命名空间，并使用以下接口：

| 证据 | 接口与含义 |
| --- | --- |
| 转换请求响应 | 标准 `change_state`，记录请求 label、返回的 success 和实际耗时 |
| ROS 状态 | 标准 `get_state`、`get_available_transitions`、`get_transition_graph`；不从日志词语推断状态 |
| 应用资源 | 普通 `~/snapshot` Trigger 返回 JSON：存活数、分配/释放账本、已提交/待清理资源 ID、配置版本、资源是否工作 |
| 实际输出 | `~/ordinary_ticks` 与 `~/managed_ticks`，类型均为 UInt64；按源序号和接收时间限定有限窗口 |

原始 stdout JSON 还记录回调 enter/return/throw、资源 acquire/release 和析构。回调事件里的当前状态可能是 configuring、activating 或 errorprocessing；标准服务在整个转换完成后查询的状态才是该次转换的最终落点。`on_error` 收到的 `previous_state` 是原转换起始状态，不能机械认为它是 errorprocessing。

资源账本只统计 `FakeHandle`，不统计仍存在的 DDS 发布者、诊断 timer 或服务。因此 `resource_live=0` 与普通诊断继续发布并不矛盾；ROS 状态、假资源所有权和基础通信实体是三个不同层次。

请求使用 label，协议中 label 优先于 id。非法 activate 与 finalized 后 configure 都检查服务拒绝、状态不变、对应回调计数不增；不只检查一个布尔值。

## 资源事务与可重试失败

configure 先创建候选 `unique_ptr<FakeHandle>`，成功后才提交为正式资源并增加 `committed_version`。候选通过 RAII 释放，分配和释放均留下独立事件。

`configure_failure_retry` 场景先成功配置再 cleanup，建立旧配置版本 1；随后注入一次 FAILURE。候选被释放，旧配置版本仍为 1，资源存活数为零，ROS 回到 unconfigured，也没有调用 on_error。同一实例再次 configure 成功提交版本 2。这验证的是旧配置元数据保留和部分内存资源释放，没有声称保留一个仍打开的硬件句柄。

activate FAILURE 在调用基类激活逻辑之前发生，所以正式资源保留，LifecyclePublisher 未激活，ROS 回到 inactive；再试 activate 成功后才产生主话题消息。每个阶段在同一实例内最多注入一次，cleanup 不重置注入消费标记；每个独立场景使用新进程，避免前次故障计数影响后次。

ERROR 或 `std::runtime_error` 需要错误处理时，configure 将候选资源交给 `pending_`；activate/deactivate 错误则可能持有已提交资源。on_error 明确停用发布者、停止假资源工作并释放 pending/committed 资源。它不会依靠状态机替应用回滚资源。

## ERROR、异常与 on_error 的落点

本机真实状态图和回调实测共同核对以下分支：

| 原回调 | on_error | 最终 ROS 状态 | 原 ChangeState.success |
| --- | --- | --- | --- |
| configure FAILURE | 不调用 | unconfigured | false |
| activate FAILURE | 不调用 | inactive | false |
| ERROR 或捕获的标准异常 | SUCCESS | unconfigured | false |
| ERROR 或捕获的标准异常 | FAILURE | finalized | false |
| ERROR 或捕获的标准异常 | ERROR | finalized | false |
| 原回调和 on_error 都抛标准异常 | 框架将异常转换为 ERROR | finalized | false |

`on_error SUCCESS` 表示错误处理走向可重配状态，不会把原回调的 ERROR 改成 SUCCESS。本例的 handler FAILURE/ERROR 在释放资源之后返回：返回码表达能否恢复，不应反过来推断资源必然泄漏。ERROR/throw 分支都检查 on_error 只执行一次，没有递归重入。

附加 deactivate ERROR 场景先进入 active，确认主输出，再在错误处理入口记录资源与发布者仍激活；on_error 之后资源和输出门控均关闭。这与 configure 的“部分候选资源”是不同所有权情形。

## 普通 timer 与 LifecyclePublisher 分别测量

构造函数创建普通 50 ms 稳态 timer，并通过自由函数 `rclcpp::create_publisher` 建立普通 `rclcpp::Publisher`。成员工厂 `LifecycleNode::create_publisher` 则建立受激活标志控制的 `LifecyclePublisher`。同一次 timer 回调把同一序号提交给两者；即使 inactive，也实际尝试调用生命周期 publish，由发布者拒绝发送。

driver 先确认两个发布者都匹配了订阅，再取资源 snapshot 的序号作为下边界。有限窗口结束后，只统计序号更大且接收时刻位于窗口内的消息，旧 active 消息即使晚到也不能伪造 inactive 输出。每个负向窗口还要求普通 timer、普通新消息和 managed publish 尝试计数都前进，避免把未发现、未调度或根本没尝试 publish 当作门控成功。

| 阶段 | 普通 timer/普通话题 | LifecyclePublisher | 假资源 |
| --- | --- | --- | --- |
| unconfigured | 持续诊断 | 关闭 | 未持有 |
| configure 后 inactive | 持续诊断 | 关闭 | 持有但不工作 |
| active | 持续诊断 | 发送 | 持有且工作 |
| deactivate 后 inactive | 持续诊断 | 关闭 | 保留但不工作 |
| cleanup 后 unconfigured | 持续诊断 | 关闭 | 已释放，可重配 |
| shutdown 后 finalized | 本例故意保留诊断 | 关闭 | 已释放，同实例不能 configure |

覆写 activate/deactivate 时，本例调用基类以激活/停用已注册生命周期发布者。普通服务、普通 timer 和普通 publisher 不会仅因为继承 LifecycleNode 就自动受相同门控；实际采样工作由 `resource_active_` 明确控制，inactive 窗口要求业务工作计数不变。

LifecyclePublisher 检查的是自己的 `is_activated()` 标志，不直接查询 ROS 状态。本例在 on_error/on_shutdown 明确撤销该标志，才维持“只在 active 发送”的应用合同；不能假定任意覆写回调都自动保持这个关系。CallbackReturn SUCCESS/FAILURE/ERROR 的值为 97/98/99，状态图 on_error 的边 ID 60/61/62 是另一组标识，不能混用。

finalized 不等于 C++ 对象已被销毁。本例保留普通诊断直到进程退出；需要停止诊断 timer 的产品应明确实现该策略。物理停车、设备掉电或线程终止不能由生命周期标签推导。

进程 SIGINT 下的析构资源释放与标准 `shutdown` 转换另行记录。观察到析构释放不能声称 on_shutdown 回调执行过，也不能把进程退出当成成功到达 finalized。

## 范围与维护

报告保留状态图、每次标准服务响应、资源快照、源序号、消息接收时间和完整回调事件；两个 `teachingTables` 仅是原始证据摘要。源码 SHA 与实际安装版本分别记录，固定 Jazzy 参考快照不能冒充本机 apt 相同版本。

未覆盖所有 cleanup/deactivate/shutdown FAILURE/ERROR 组合、非标准异常、内存分配失败、阻塞设备操作、真实外部线程、进程崩溃恢复或硬件。窗口只证明所列输入和匹配条件下的新增消息，不证明精确频率、硬实时或物理安全。
