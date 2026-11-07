# Count 忙碌、取消、失败与恢复实验

本目录增加独立 `learning_count_fault_lab` 包和验收脚本。原 `foundation-examples/` 的 Count 接口、C++/Python 服务端保持原样。接口仍是 `learning_count_interfaces/action/Count`：目标 `target`、反馈 `current` 和结果 `completed` 都是无量纲整数，Result 没有 `reason` 字段。

验收脚本分十组主场景：原 C++/Python 各验证忙碌时合法目标拒绝、首目标取消后恢复、首目标正常完成后恢复，以及 0/21 非法边界拒绝；扩展 C++/Python 各验证默认故障关闭、显式故障后的 `ABORTED` 与短目标恢复。每个 accepted 目标保存独立 UUID、反馈、状态话题和 GetResult.status/completed；拒绝目标不调用 GetResult。

## 准备、构建与复现

前提是 Jazzy 已安装，且基础章的 `learning_count_interfaces` 与原 `learning_action_cpp` 已构建。以下复用当前机器的 `/tmp/ros2-hub-validation/foundation/install`；换机必须替换成实际基础安装前缀，源码存在不等于已生成接口 Python/C++ 类型支持。

```bash
# 从ros2-learning-hub目录执行。--help无需ROS或已构建产物。
python3 examples/action_labs/verify_count_actions.py --help
source /opt/ros/jazzy/setup.bash
source /tmp/ros2-hub-validation/foundation/install/setup.bash
# 只构建新增包到专属/tmp目录，然后依次运行十组实验。
python3 examples/action_labs/verify_count_actions.py --build \
  --foundation-prefix /tmp/ros2-hub-validation/foundation/install \
  --build-root /tmp/ros2-hub-count-action-lab \
  --domain-id 227 --case-timeout 25 --total-timeout 180 \
  --output /tmp/count-action-rerun.json
# 独立验证父进程Ctrl+C能清理自建worker/server；它不新增取消业务场景。
python3 examples/action_labs/verify_interrupt_cleanup.py \
  --foundation-prefix /tmp/ros2-hub-validation/foundation/install \
  --fault-prefix /tmp/ros2-hub-count-action-lab/install \
  --report /tmp/count-action-rerun.json --domain-id 227
```

`--build` 内部实际执行：

```bash
colcon --log-base /tmp/ros2-hub-count-action-lab/log build \
  --base-paths examples/action_labs/learning_count_fault_lab \
  --build-base /tmp/ros2-hub-count-action-lab/build \
  --install-base /tmp/ros2-hub-count-action-lab/install \
  --merge-install --symlink-install --packages-select learning_count_fault_lab
```

单独运行扩展服务端时，每终端加载相同基础与本例覆盖层，并显式选择实验域。以下运行的是计数任务，不是机器人控制：

```bash
source /opt/ros/jazzy/setup.bash
source /tmp/ros2-hub-validation/foundation/install/setup.bash
source /tmp/ros2-hub-count-action-lab/install/setup.bash
export ROS_DOMAIN_ID=227
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
# 默认abort_after=0，不注入故障；step_seconds默认0.15秒。
ros2 run learning_count_fault_lab count_fault_cpp
# 或在另一个实验命名空间运行Python版本，显式在第6步反馈后注入故障。
ros2 run learning_count_fault_lab count_fault_py --ros-args \
  -r __ns:=/manual_count_fault -p abort_after:=6 -p step_seconds:=0.2
```

一个 `ament_cmake` 包同时安装 C++ 可执行文件和完整 Python 脚本。Python 入口通过 CMake `install(PROGRAMS)` 安装为 `count_fault_py`；这里没有宣称它使用 `ament_python` 的 `console_scripts`。`Count` 接口从基础安装查找，不在本目录重复生成。

## 故障与并发合同

- 合法 `target` 为 1..20。每次只接受一个目标，忙碌时另一个合法目标拒绝。原 C++ 和扩展 C++ 使用单线程回调；扩展 Python 与原 Python 使用可重入组/多线程，并通过锁保护 busy。
- `abort_after` 只能为整数 0..20，0 关闭故障。`step_seconds` 必须是 `[0.02,2]` 内有限 DOUBLE 秒数。参数只在启动时读取，扩展服务端不提供运行时参数服务。
- 故障启用为 N 后，第 N 步完成、发布 `current=N` 反馈，再调用 abort，结果必须是 `ABORTED` 且 `completed=N`。故障检查先于同一步成功，因此 `target=N` 也失败；`target<N` 先达到成功，可用来验证 busy 释放。
- 扩展服务端用 `COUNT_LAB_EVENT` 日志独立记录原因和已接受目标 UUID。Python 的公开 `goal_callback` 只得到 Goal，没有 UUID，因此拒绝日志的 UUID 为 null；脚本用独立命名空间内唯一的第二目标和顺序关联，不能伪造服务端提供了 UUID。接受后公开 handle 提供 UUID，ABORTED 原因日志可精确关联。
- 原服务端没有结构化原因日志。对其忙碌拒绝，证据是首目标已有反馈、结果尚未完成、第二目标合法且 `accepted=false`，以及原源码中的 busy 条件；报告明确它是受控条件推断，没有凭空增加结果原因字段。
- Python扩展的取消接纳回调没有可靠进度快照，接纳日志的 `completed=null` 表示此时未知，真正步数由反馈/最终Result提供。本轮取消业务实测只覆盖原两种服务端，扩展取消路径不能被算入已通过主场景。

## 接受、取消与结果分别验证

ROS 2 GoalStatus 没有 REJECTED 枚举。拒绝是 SendGoal 应答的 `accepted=false`，此时没有本次已执行的结果；不能用 `completed=0` 假装一次执行失败。对未知 UUID 强行查询得到 UNKNOWN/默认结构，也不能把默认值当业务完成证据。本脚本对拒绝目标始终不请求 GetResult。

取消场景使用 12 步长目标，第一条反馈后发送第二个合法目标，确认被拒绝后才请求取消，给终态处理保留充分余量。取消应答必须包含同一 UUID，但仍独立等待 GetResult 的 `CANCELED` 和状态话题。这个受控中途取消通过，不证明所有竞态都以 CANCELED 结束：取消临近自然完成时，服务端可能最终为 SUCCEEDED 或 ABORTED。服务端在步边界检查取消，接受取消本身不会抢占正在执行的业务。

正常、取消或故障终态之后，脚本只发送一次新合法短目标，要求接受且成功；不使用循环重发掩盖 busy 释放缺陷。扩展故障场景的短目标为 2，小于故障阈值 6。

## 期限、日志与清理

客户端等待分别限制为服务器发现 8 秒、目标应答 4 秒、首反馈 4 秒、取消应答 3 秒、结果 12 秒和终态状态话题 2 秒，均按 monotonic 经过时间计算。`spin_once` 每次空闲等待最多 0.02 秒，不会抢占已执行回调。父进程每 worker 保护 25 秒，十组 worker 合计保护 180 秒；构建另有 100 秒上限。父级对worker组发送INT后最多等待5秒，之后TERM/KILL各等2秒；worker收到组INT后，先给同组server最多2秒完成首次信号清理，不能马上补发第二次INT。这些是普通系统的软期限，不是硬实时保证。

每个 worker 有独立命名空间和自己创建的进程组。正常清理服务端按 SIGINT→SIGTERM→SIGKILL 递进；父进程超时只终止该 worker 创建的组。它不停止 ROS daemon、不扫描/杀死其他节点。临时服务端日志嵌入报告后删除临时目录；专属构建产物保留供核查，不删除基础安装。

报告默认另存为 `/tmp/count-action-rerun.json`，保存完整命令、源码/CMake/package SHA、临时 ELF 与 Python 入口 SHA、每目标 UUID/反馈/状态/completed、取消应答、服务端日志、进程回收与教学摘要表。教材维护者显式用 `--output validation-evidence/count-action-current-validation.json` 保存绑定证据；读者练习应保留/tmp另存，避免覆盖本站报告。重新执行会保留前一轮结果作为 priorAttempts，不将失败静默变成通过。

独立中断检查等待真实首步反馈，再只对验收父进程发送SIGINT；它用Linux `/proc` 检查父进程、独立会话worker及其server均已回收，而不是由检查脚本替父进程清理后假装通过。它还要求worker没有向已获组INT的server重复发信号、server以0正常退出，且没有shutdown/join被KeyboardInterrupt打断的异常栈。其结果放在 `lifecycleValidation`，不把中断时未确认终态的目标计为成功或已取消。旧的重复INT记录保存在priorAttempts，不仅刷新源码指纹掩盖问题。

所有任务只计算整数。服务端返回、进程退出、取消应答或 Action 终态都不是机器人实际停车证明；本实验没有仿真、硬件、网络任意故障或完整控制系统验收。
