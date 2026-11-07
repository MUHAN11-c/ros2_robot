# 有界单目标导航客户端

`bounded_navigation.py` 是 ROS 2 Jazzy / `nav2_msgs/action/NavigateToPose` 的单目标教学客户端。它直接使用公开 `rclpy.action.ActionClient`，把服务发现、目标应答、执行、取消应答和终态分开管理。输入位置单位是米，平面朝向单位是弧度；输出是带目标 UUID 的逐行 JSON。

客户端不发布 `initialpose`。运行前由用户在 RViz 的 **2D Pose Estimate** 等工具设置可信初始定位，并确认定位收敛。目标发送前尚有地图、定位、TF、时钟和生命周期检查，这些检查不能由“发现了 Action 服务器”代替。

## 在已准备好的仿真中运行

以下命令从 `ros2-learning-hub` 目录执行。首次安装依赖需要联网；这与离线阅读教材不同。

```bash
# 仅在 Ubuntu 24.04 / ROS 2 Jazzy 学习环境安装；本例不连接真实底盘。
source /opt/ros/jazzy/setup.bash
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-nav2-minimal-tb3-sim ros-jazzy-ros-gz
# 查看本机安装版本实际提供的参数，再运行成套的默认 sandbox 世界/模型/地图。
ros2 launch nav2_bringup tb3_simulation_launch.py --show-args
ros2 launch nav2_bringup tb3_simulation_launch.py headless:=False use_sim_time:=True
```

在另一个已 `source` 相同 Jazzy 环境的终端检查：

```bash
# 持续观察命令需用 Ctrl+C 结束；先确认输入在推进，再运行客户端。
ros2 lifecycle get /amcl
ros2 lifecycle get /bt_navigator
ros2 action list -t
ros2 action info /navigate_to_pose
ros2 topic echo /clock --once
ros2 run tf2_ros tf2_echo map base_link
```

将 RViz 固定坐标设为 `map`，完成初始位姿估计，观察扫描与地图对齐，检查足印/代价地图，再在当前地图自由空间选定目标。`map` 名称只标识参考系，改字符串不会变换坐标。下面 `1.0 0.5 0.0` 仅演示 CLI 格式，必须替换成自己确认的有效 `X米 Y米 YAW弧度`：

```bash
python3 examples/navigation/bounded_navigation.py --help
# 本客户端不接受 --start；初始定位已在运行前明确完成。
python3 examples/navigation/bounded_navigation.py \
  --goal 1.0 0.5 0.0 --frame map --sim-time \
  --clock-timeout 5 --server-timeout 10 --goal-response-timeout 5 \
  --timeout 60 --cancel-timeout 3 --result-timeout 5
```

多机器人环境用 `--action-name /robot1/navigate_to_pose` 指定绝对 Action 名，并按实际 TF 合同选择 `--frame`。客户端没有隐式重映射参数；不要把另一台机器人的动作名或参考系直接复制进来。普通真实时间环境不传 `--sim-time`，但本教学代码没有因此获得实机运行验证。

## 各期限精确定义

| 参数 | 默认秒 | 开始时刻与限制范围 |
| --- | ---: | --- |
| `--clock-timeout` | 5 | 仅启用仿真时间时，等待节点收到正的 ROS 时间。没有 `/clock` 或一直为零时不发送目标。 |
| `--server-timeout` | 10 | 时钟检查后，等待完整 Action 服务端被发现。发现不等于定位正确或 Nav2 生命周期 active。 |
| `--goal-response-timeout` | 5 | 异步提交目标后，等待接受或拒绝的应答。期限到达后接受状态为 **unknown**，不是 rejected。 |
| `--timeout` | 60 | 客户端观察到接受应答之后，等待本目标的软件终态。这个期限不包括上述启动阶段。 |
| `--cancel-timeout` | 3 | 一个合计窗口，覆盖取消服务发现、取消请求应答及 `UNKNOWN_GOAL_ID` 的有限重试。没有为每次重试重置总期限。 |
| `--result-timeout` | 5 | 取消阶段之后，继续等待精确 UUID 对应的结果或终态状态；期限到达而无证据则报告 unknown。 |

期限均由 `time.monotonic()` 的经过秒计算；目标消息时间戳使用节点 ROS 时钟。仿真暂停不会暂停业务期限，不能为了绕过时钟错误把消息时间戳改成系统日期时间。默认全部窗口的保守和为 88 秒，实际路径经常跳过部分窗口；这个和不包括 Python 导入、DDS 初始化/销毁与操作系统调度开销。

`spin_once(timeout_sec≤0.05)` 限制空闲等待，不抢占已运行回调。本例回调只做短的状态更新与节流日志；普通操作系统调度、阻塞的日志设备和中间件故障仍可能增加耗时。因此这些是可审计的协议软期限，不能当硬实时制动承诺。

## 接受未知、取消应答与终态

1. 客户端在发送前生成、记录非零 UUID，并通过 `send_goal_async(..., goal_uuid=...)` 传给服务端。目标应答未到时，不能假定服务端没有执行。
2. 需要取消时，客户端使用公开的 `action_msgs/srv/CancelGoal` 服务，目标为 `<Action绝对名>/_action/cancel_goal`。请求只填本 UUID，时间戳保持零。非零 UUID 加零时间戳只针对这一目标；零 UUID 加零时间戳会取消所有目标，本例不发送这种请求。
3. 取消应答 `ERROR_NONE` 且 `goals_canceling` 包含本 UUID，才记录 `accepted_not_terminal`。这只说明服务端接受取消、进入取消过程。`UNKNOWN_GOAL_ID` 可能是目标尚未登记，也可能确实不存在；客户端仅在同一个取消总期限内重试，不据此宣称撤销成功。
4. 客户端继续处理迟到的接受应答。有 goal handle 时调用 `get_result_async()`，读取结果的 `status` 及 Nav2 `error_code/error_msg`；同时只观察自己 UUID 的 `GoalStatusArray`。精确 UUID 的终态状态也可证明软件终态，但没有完整错误详情，输出会标记 `terminal_source=status_topic`、`nav2_result_available=false`。
5. 没有取消应答、取消被拒绝、服务端失联，或取消受理后没有终态时，客户端在窗口结束后返回 **unknown**。它销毁本地对象或清理 pending 登记，不会撤销远端任务。应由独立监督流程核对服务端/控制链及机器人状态，禁止直接重发目标。

第一次 Ctrl+C/SIGTERM 触发相同的有界取消流程；第二次触发强制结束等待，仍可能留下未确认的远端目标。若超时/中断与成功竞争，客户端记录实际成功终态，但用退出码 6 表示它没有证明期限内业务成功。每条 summary 都包含 `hardware_stop_verified=false`：即使出现 `canceled` 或 `succeeded`，也必须另外观察速度测量和停止链，不能把进程返回、`cmd_vel=0` 或协议终态当成物理停车证明。

| 退出码 | 含义 |
| ---: | --- |
| 0 | 正常执行阶段内观察到本目标 succeeded |
| 2 | 明确收到目标拒绝；此目标没有被接受 |
| 3 | 观察到 aborted |
| 4 | 观察到 canceled；不表示物理停车已核实 |
| 5 | 启动/协议错误或最终状态 unknown；也包括发送前未发现服务或时钟 |
| 6 | 超时、中断或异常流程之后观察到 succeeded；由上层决定业务处置 |

## 为什么替换高层等待

本地固定 Jazzy `nav2_simple_commander` 源码中，`goToPose()` 包含无总期限的服务器发现循环和无 timeout 的目标应答等待，`cancelTask()` 内部也无 timeout 地等待取消 future。因此，把 `deadline+5` 检查放在这些调用之后不能约束它们。`waitUntilNav2Active(localizer='amcl')` 还会在尚未收到 AMCL 回调时主动发布保存的初始位姿；它不是只读的生命周期等待。高层接口仍可用于了解任务编排，本例为逐阶段期限管理选择原生异步 API。

核对的一手接口为：

- 本地 `references/sources/official-core/ros2--rclpy/jazzy--521012e60ba2/rclpy/rclpy/action/client.py`：`send_goal_async(self, goal, feedback_callback=None, goal_uuid=None)`、`ClientGoalHandle.get_result_async()`、`server_is_ready()`。
- 本地 `references/sources/official-core/ros2--rcl_interfaces/jazzy--7aa3caf43377/action_msgs/srv/CancelGoal.srv`：UUID/时间戳选择规则、四个取消返回码与 `goals_canceling`。
- 本地 `references/sources/ecosystem/ros-navigation--navigation2/jazzy--94d1c2a345dd/nav2_msgs/action/NavigateToPose.action`：目标 `pose/behavior_tree`、结果 `error_code/error_msg`、反馈 `distance_remaining`。
- [Nav2 Jazzy 原始实现](https://github.com/ros-navigation/navigation2/blob/94d1c2a345dd/nav2_simple_commander/nav2_simple_commander/robot_navigator.py) 与 [Jazzy rclpy 原始 Action 客户端](https://github.com/ros2/rclpy/blob/521012e60ba2/rclpy/rclpy/action/client.py)。固定快照不保证用户安装的其他发行版具有相同签名。

## 实际验证与边界

2026-11-07 已完成 AST/语法、CLI 有限值断言，并核对本机安装签名。实际包版本为 `rclpy 7.1.12-1noble.20260912.162354`、`nav2_msgs 1.3.13-1noble.20260921.023049`、`action_msgs 2.0.4-1noble.20260911.052334`。

已在仅本机发现范围、独立 `ROS_DOMAIN_ID=217` 和唯一 `/bounded_probe_*` 动作名下运行假 Action 服务端；没有启动 Nav2、Gazebo 或连接机器人。十二类场景均有断言：服务不存在、成功、拒绝、失败、导航超时取消、接受迟到后按 UUID 取消、目标应答不返回、取消应答不返回、取消受理后无终态、正的 `/clock` 暂停、Ctrl+C、没有 `/clock`。逐案例结果与事件摘要嵌入 `source/navigation-revision.json` 的 `meta.validation.protocolCases`。

这些测试证明本例在受控 ROS 协议故障注入下按已设窗口退出，不能证明完整 Nav2 导航质量、代价地图/定位配置、DDS 任意故障恢复或硬件制动。后续仍应在匹配的 Jazzy 仿真中运行自由目标、障碍、封路和移动中取消，并保存目标、地图、参数、TF、时钟、速度测量及 bag；之后才有依据记录仿真验收结果。

可复现的隔离协议测试代码见本文末尾。应先选没有其他节点的域与测试动作名；测试只使用假服务端，不能替换成真实导航名。标准检查如下：

```bash
# 只做语法/参数检查，不发目标。
python3 -m py_compile examples/navigation/bounded_navigation.py
python3 examples/navigation/bounded_navigation.py --help
# 已按下节将脚本保存到 /tmp 后运行；所有日志/结果写入 /tmp。
source /opt/ros/jazzy/setup.bash
ROS_LOG_DIR=/tmp/bounded-navigation-ros-log python3 /tmp/bounded_nav_protocol_probe.py
```

## 隔离协议测试脚本

从 `ros2-learning-hub` 目录运行，把下面完整代码另存为 `/tmp/bounded_nav_protocol_probe.py`。`6` 秒是故意维持假任务的时间，客户端窗口为小于它的单调秒；测试结束强制清理假服务端进程不代表生产系统允许这样停止机器人。模式 `paused_clock` 反复发布数值恒为 `1` 秒的 `/clock`，模拟已接入仿真时钟而时间停止推进。

```python
"""只启动隔离 ROS 假动作服务，不启动 Nav2、仿真或机器人。"""
import json, os, pathlib, signal, subprocess, sys, time
# 输入：从 ros2-learning-hub 运行；只连接下方独立域中的 /bounded_probe_* 假动作名。
# 输出：每种场景的断言结果，以及 /tmp 下的逐事件 JSON；不运行 Nav2 或机器人。
ROOT=pathlib.Path.cwd()
CLIENT=ROOT/'examples/navigation/bounded_navigation.py'

def server(mode,name):
 # mode 控制故障注入；所有 sleep 和客户端期限单位都是单调经过秒。
 import rclpy
 from rclpy.action import ActionServer,GoalResponse,CancelResponse
 from rclpy.callback_groups import ReentrantCallbackGroup
 from rclpy.executors import MultiThreadedExecutor
 from rclpy.node import Node
 from nav2_msgs.action import NavigateToPose
 from rosgraph_msgs.msg import Clock
 rclpy.init(args=[])
 n=Node('bounded_nav_fake_server')
 def goal_callback(goal):
  if mode=='reject':return GoalResponse.REJECT
  # .65 秒接受延迟大于客户端 .25 秒应答窗口，检验 unknown 后按 UUID 取消。
  if mode=='late_accept':time.sleep(.65)
  if mode=='goal_no_ack':time.sleep(5)
  return GoalResponse.ACCEPT
 def cancel_callback(handle):
  if mode=='cancel_no_ack':time.sleep(5)
  return CancelResponse.ACCEPT
 def execute(handle):
  start=time.monotonic()
  while rclpy.ok() and time.monotonic()-start<6:
   elapsed=time.monotonic()-start
   feedback=NavigateToPose.Feedback();feedback.distance_remaining=1.0
   handle.publish_feedback(feedback)
   if mode=='success' and elapsed>.1:
    handle.succeed();return NavigateToPose.Result()
   if mode=='aborted' and elapsed>.1:
    handle.abort();r=NavigateToPose.Result();r.error_code=1;r.error_msg='isolated deliberate failure';return r
   if handle.is_cancel_requested and mode!='cancel_no_terminal':
    handle.canceled();return NavigateToPose.Result()
   time.sleep(.02)
  handle.abort();return NavigateToPose.Result()
 action=ActionServer(n,NavigateToPose,name,execute,goal_callback=goal_callback,
                     cancel_callback=cancel_callback,callback_group=ReentrantCallbackGroup())
 clock_pub=None
 if mode=='paused_clock':
  # 发布固定正时间；有接收样本但之后不再推进，客户端业务期限仍应超时。
  clock_pub=n.create_publisher(Clock,'/clock',10)
  def tick():
   msg=Clock();msg.clock.sec=1;clock_pub.publish(msg)
  n.create_timer(.05,tick)
 executor=MultiThreadedExecutor(num_threads=4);executor.add_node(n)
 print('READY',flush=True)
 try:executor.spin()
 except KeyboardInterrupt:pass
 finally:
  executor.shutdown(timeout_sec=0);action.destroy();n.destroy_node()
  if rclpy.ok():rclpy.shutdown()

if len(sys.argv)>1 and sys.argv[1]=='server':
 server(sys.argv[2],sys.argv[3]);sys.exit()

# 仅当前进程与子进程使用此独立域，客户端没有任何真实机器人动作名。
os.environ['ROS_DOMAIN_ID']='217'
os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
# 每个请求均是无物理副作用的假任务；小期限用于迅速复现协议超时。
base=[sys.executable,str(CLIENT),'--goal','1','2','0','--server-timeout','2',
      '--goal-response-timeout','.25','--timeout','.25','--cancel-timeout','.9',
      '--result-timeout','.4']
records=[]
for mode,expected in [('absent','unknown'),('success','succeeded'),('reject','unknown'),
                      ('aborted','aborted'),('cancel','canceled'),('late_accept','canceled'),
                      ('goal_no_ack','unknown'),('cancel_no_ack','unknown'),
                      ('cancel_no_terminal','unknown'),('paused_clock','canceled'),
                      ('sigint','canceled'),('clock_absent','unknown')]:
 name=f'/bounded_probe_{os.getpid()}_{mode}'
 sp=None
 try:
  if mode not in ('absent','clock_absent'):
   sp=subprocess.Popen([sys.executable,__file__,'server',mode,name],stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,text=True)
   import select
   if not select.select([sp.stdout],[],[],5)[0]:raise RuntimeError('fake server startup timeout')
   ready_deadline=time.monotonic()+5
   while True:
    line=sp.stdout.readline()
    if line.strip()=='READY':break
    if not line or time.monotonic()>ready_deadline:raise RuntimeError(('fake startup failed',line,sp.stderr.read()))
  command=base+['--action-name',name]
  if mode=='absent':command+=['--server-timeout','.3']
  if mode=='paused_clock':command+=['--sim-time','--clock-timeout','1']
  if mode=='clock_absent':command+=['--sim-time','--clock-timeout','.3']
  if mode=='sigint':command+=['--timeout','5']
  start=time.monotonic()
  if mode=='sigint':
   cp=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   time.sleep(1.3);cp.send_signal(signal.SIGINT)
   output,error=cp.communicate(timeout=8);returncode=cp.returncode
  else:
   cp=subprocess.run(command,capture_output=True,text=True,timeout=9)
   output,error,returncode=cp.stdout,cp.stderr,cp.returncode
  events=[json.loads(line) for line in output.splitlines() if line.startswith('{')]
  # 先检查 summary 存在，再核对期望终态与分场景的取消证据。
  summaries=[event for event in events if event['event']=='summary']
  if not summaries:raise AssertionError((mode,returncode,output,error))
  summary=summaries[-1]
  assert summary['terminal']==expected,(mode,summary,output,error)
  assert summary['hardware_stop_verified'] is False
  if mode=='reject':assert returncode==2 and summary['goal_response']=='rejected'
  if mode=='late_accept':assert any(x['event']=='acceptance_unknown' for x in events)
  if mode=='cancel_no_ack':assert summary['cancel_state']=='response_timeout'
  if mode=='cancel_no_terminal':assert summary['cancel_state']=='accepted_not_terminal'
  if mode=='goal_no_ack':assert summary['goal_response']=='unknown'
  if mode=='paused_clock':assert summary['trigger']=='navigation_timeout'
  if mode=='sigint':assert summary['trigger']=='navigation_interrupted'
  record={'case':mode,'processElapsed_s':round(time.monotonic()-start,3),'exitCode':returncode,
          'summary':summary,'events':events,'stderr':error}
  records.append(record)
  print(json.dumps({'case':mode,'pass':True,'elapsed_s':record['processElapsed_s'],
                    'terminal':summary['terminal'],'cancel_state':summary['cancel_state']},ensure_ascii=False),flush=True)
 finally:
  if sp is not None:
   sp.terminate()
   try:sp.communicate(timeout=.5)
   except subprocess.TimeoutExpired:sp.kill();sp.communicate()
pathlib.Path('/tmp/bounded_navigation_probe_results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('ALL',len(records),'PASSED')
```
