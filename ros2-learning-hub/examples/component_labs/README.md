# 原创组件参数与容器实验

本目录包含完整 `runtime_lab_components` C++ ROS 包与 `validate_components.py`。目标环境为 Ubuntu 24.04、ROS 2 Jazzy、系统 `/usr/bin/python3`。实验只处理教学数值与临时软件门闩，不连接设备，不启动 Gazebo 或其他仿真器。

`ConfigComponent` 接收 `const rclcpp::NodeOptions &` 并转交 `Node`。同一类既注册为共享库插件，又由 CMake 生成独立入口 `config_node`。它声明无量纲 `DOUBLE gain`，只接受有限值 `[0,2]`，以 0.2 m/s 为基值，每 0.1 秒向私有话题 `~/configured_velocity` 发布 `std_msgs/msg/Float64`。例如完整节点名 `/demo/config` 的输出话题是 `/demo/config/configured_velocity`，`gain=1.5` 对应 0.3 m/s。这是教学数据，不是底盘控制接口。

启动时，静态 double 声明先验证类型，再显式验证有限性和范围。动态 on-set 回调只返回接纳结果，不改 cache 或执行硬件副作用；timer 每次读取正式参数。因此拒绝更新后，参数值与后续输出都保持原配置。句柄保存在成员中，校验器不会因局部对象销毁而消失。

## 构建和完整验收

在 `ros2-learning-hub` 目录执行；依赖列在包内 `package.xml`，缺少时可在已初始化 rosdep 的环境安装。构建及安装产物都放 `/tmp`，不修改其他教学工作空间。

```bash
source /opt/ros/jazzy/setup.bash
# 仅缺少依赖时执行；本轮已有依赖，没有将安装命令算作已执行验证。
# rosdep install --from-paths examples/component_labs/runtime_lab_components --ignore-src --rosdistro jazzy -y
colcon --log-base /tmp/ros2-component-labs/log build \
  --base-paths examples/component_labs/runtime_lab_components \
  --build-base /tmp/ros2-component-labs/build \
  --install-base /tmp/ros2-component-labs/install --merge-install --symlink-install
source /tmp/ros2-component-labs/install/setup.bash
COMPONENT_LABS_INSTALL_PREFIX=/tmp/ros2-component-labs/install \
  timeout --signal=INT --kill-after=10s 180s \
  /usr/bin/python3 examples/component_labs/validate_components.py \
    --build-root /tmp/ros2-component-labs \
    --report /tmp/component-labs-local-result.json
```

driver 默认在独立域 225 使用 Fast DDS，仅 LOCALHOST 发现；清除旧 `ROS_LOCALHOST_ONLY` 和 `ROS_STATIC_PEERS`。每例使用唯一命名空间和私有临时目录，结束后只清理本例保存的 PID/进程组，不停止 ROS daemon 或用户节点。父进程中断后停止后续case、清理自建worker进程组并退出130。运行前需确认没有其他程序在该专用域发布同名实验端点。

`--install-prefix` 或 `COMPONENT_LABS_INSTALL_PREFIX` 可指定任意当前机器的新构建产物，默认路径跟随本目录，不依赖旧电脑。`--report /tmp/my-component-result.json` 可另存报告；`--case` 可选择五个主场景之一。未 source ROS 时仍可查看帮助：

```bash
/usr/bin/python3 -I examples/component_labs/validate_components.py --help
```

上面的复现命令把新报告保存到 `/tmp/component-labs-local-result.json`，不会覆盖教材按SHA绑定的 `validation-evidence/component-labs-current-validation.json`。报告保存每轮结果与历史、实际版本、源码 SHA、命令、服务响应、原始 JSON 事件及清理；`teachingTables` 只是这些实测记录的简表。编译输出和保留日志与运行行为分开记录。

## NodeOptions、参数与管理节点的三层边界

标准 `LoadNode` 中，`parameters` 是给组件的参数覆盖；`extra_arguments` 是标准 manager 显式识别的一小组装载选项，不是整个 `NodeOptions` 的序列化。

本实验核对并验证以下合同：

| 输入 | 作用对象及检查 |
| --- | --- |
| `LoadNode.parameters` 的 `gain=1.5` | Config 声明参数时采用覆盖值，输出 0.3 m/s |
| 默认没有 `forward_global_arguments` | 标准 manager 创建组件 options 时使用 `use_global_arguments(false)`；普通 NodeOptions 的默认值是另一个层次 |
| `forward_global_arguments=true` | 允许组件读取进程 Context 的全局 ROS CLI 参数；不是实时复制管理节点当前参数 |
| 全局 CLI `gain=1.8`、局部请求 `gain=1.5` | 局部 `LoadNode.parameters` 覆盖全局值；读取真实生效值与输出 |
| 管理节点的 gain 从 1.8 改成 1.2 | 已加载组件不自动变化；之后转发全局 CLI 的新组件仍采用 CLI 的 1.8 |
| `parameters` 中出现 `typo_gain` | Config 只声明 gain，未知覆盖不会自动变成已声明参数；用 ListParameters 缺席、GetParameters 实际返回及运行时 set 拒绝共同检查 |
| 未知 extra 中放 `automatically_declare_parameters_from_overrides=true` 和 `allow_undeclared_parameters=true` | 记录两个实际 options 仍为 false；标准 manager 忽略这些未知键，不能将它们当支持开关 |
| 已识别 extra `forward_global_arguments` 使用字符串 | manager 检查其 BOOL 类型并返回明确加载失败；已有有效组件不受影响 |

严格参数服务对未声明名称可能返回空 `values`；不能把 `get_parameter_or` 或 `allow_undeclared` 下的 `NOT_SET` fallback 机械套用到服务响应，更不能混查已声明和未知名后盲目按位置索引。这是 API 与策略区别，不是 C++、Python 必然不同。

driver 对非法 gain `3.0`、字符串和 NaN 分别检查构造加载失败、错误原因及已有组件列表不变。节点名和 `unique_id` 来自真实加载响应，不硬编码 ID，也不把失败时消耗的 ID 当作有效实例。

## 为什么另外提供 observable_manager

本机官方 `ComponentManager` 默认 NodeOptions 关闭管理参数服务和参数事件发布。官方容器依然声明 `thread_num` 并能读取启动 CLI 覆盖，但不能据此假定 `ros2 param get/set /ComponentManager ...` 服务默认存在。

`observable_manager` 直接使用同版本 `rclcpp_components::ComponentManager`，明确开启管理参数服务，另声明管理节点自己的 gain；根据 manager 的 `thread_num` 创建共享多线程执行器。验收通过真实 Get/Describe/SetParameters 检查：启动 `thread_num=2`、描述符 `read_only=true`、将它改为范围内的 1 也被拒绝且保留 2。管理 gain 与组件加载参数也在这个明确开启接口的 wrapper 上检查。这不冒充官方可执行默认暴露了管理参数服务。

## 官方三容器的调度时间线

`SlowComponent` 和 `HeartbeatComponent` 都使用默认互斥组，但属于不同节点。默认 20 ms 稳态 timer；slow 只执行一次，等私有临时目录中的释放标志，每 5 ms 检查一次，保护上限为 2 秒。该等待模拟 IO，不测量纯 CPU 加速。

driver 先确认 heartbeat timer 实际运行过，再启动 slow；看到 slow 的 start 事件后才启用 heartbeat，并保持约 0.35 秒门闩窗口。随后释放 slow，确认 heartbeat 能继续运行。单线程负例还检查首个 heartbeat 的 `TimerInfo.expected_call_time` 早于 slow 结束，证明 timer 已到期，不把尚未准备好的输入当成阻塞证据。

| 官方可执行 | 源码模型与本轮配置 |
| --- | --- |
| `component_container` | 所有组件共用单线程执行器，slow 期间 heartbeat 无法进入 |
| `component_container_mt --ros-args -p thread_num:=2` | 共用两个工作线程；两节点的默认互斥组不同，可观察 span 重叠 |
| `component_container_isolated` | 默认每组件专属单线程执行器；本轮没有传 `--use_multi_threaded_executor`，组件仍共享同一进程 |

不能把 mt 默认写成固定四线程：本机实现读取 manager 的 thread_num，默认值来自 hardware_concurrency。不能把 isolated 默认写成每组件多线程；显式非 ROS 参数 `--use_multi_threaded_executor` 才选择该分支，本轮没有运行它。

组件事件逐行输出 PID、Linux TID、steady-clock 纳秒、span start/end 和相关字段。它们由同一共享库短锁保护，避免事件行交错，锁内不做慢工作。driver 保留全部原始事件，按成对 span 计算真实交叠及最大业务并发，核对组件 PID 等于容器 PID。isolated 的线程分开不等于进程、地址空间或故障隔离；本实验不通过崩溃注入来证明任何隔离能力。

所有组件提供私有 `~/prepare_unload` Trigger 服务，在自身默认互斥组取消 timer；driver 收到响应后再调用 manager 卸载，并确认列表为空。这是受控资源停止路径，不证明任意外部线程或硬件资源都能安全卸载。

## 时间和验证边界

服务发现/响应的五秒软期限需要执行器持续推进；它不能抢占任意长原生调用。每例另有父进程三十秒期限，整个运行命令再用外层 timeout。日志或返回码本身不证明机器人停止。

本实验没有测试 isolated 的每组件多线程分支、任意 RMW、跨机通信、CPU 独占、进程崩溃隔离、零复制性能或硬件配置事务。原始固定 Jazzy 分支快照与本机 apt 包版本分开记录，不能只因分支名相同就称为同一版本。
