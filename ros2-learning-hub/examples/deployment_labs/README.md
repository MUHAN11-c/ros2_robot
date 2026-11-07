# 安装前缀审计与宿主入口信号实验

这里区分文件清点、同机目录副本、宿主直接节点信号三个层次。审计器只用标准库，不导入 ROS、不执行环境脚本、复制产物或容器。宿主信号检查是单独的显式命令，只运行已有 `runtime_lab_components` 的合成 Config 节点。它输出教学 Float64 数据，不是设备速度命令。

所有报告默认写 `/tmp`，不会自动覆盖教材已绑定证据。输入前缀必须明确给出；没有搜索整个工作区、HOME 或凭据的逻辑。额外范围只用于解析给定链接、读取指定源码及包清单，不会递归清点 underlay。

## 准备与范围

先按组件章构建 `runtime_lab_components`。下面列的是本机已有产物：`/tmp/ros2-component-labs/install`，以及它的 build 和源码目录。换机应替换成自己真实构建后的路径。目录存在、链接能在原机器解引用、文件 SHA 相同，都不是跨机运行成功。

```bash
# 从ros2-learning-hub目录执行，帮助和小夹具检查不需要source ROS。
python3 examples/deployment_labs/audit_prefix.py --help
python3 examples/deployment_labs/audit_prefix.py --self-test

# 明确只清点一个包的安装前缀。源目录只允许这个包，不扫描用户家目录。
# --copy-demo在自建/tmp中保留链接文本复制，检查后自动删除自己的副本。
timeout --signal=INT --kill-after=5s 40s /usr/bin/python3 examples/deployment_labs/audit_prefix.py \
  --prefix /tmp/ros2-component-labs/install \
  --allow-root /tmp/ros2-component-labs/build/runtime_lab_components \
  --allow-root /home/wjz/ros2_robot/ros2-learning-hub/examples/component_labs/runtime_lab_components \
  --allow-root /opt/ros/jazzy --underlay /opt/ros/jazzy \
  --package runtime_lab_components --package rclcpp --package rclcpp_components \
  --package rcl_interfaces --package std_msgs --package std_srvs \
  --source-file /home/wjz/ros2_robot/ros2-learning-hub/examples/component_labs/runtime_lab_components/src/components.cpp \
  --source-file /home/wjz/ros2_robot/ros2-learning-hub/examples/component_labs/runtime_lab_components/CMakeLists.txt \
  --copy-demo --report /tmp/deployment-local-audit.json
```

默认限额为 1000 条目录项、单文件 16MiB、累计读取 96MiB、每阶段 10 个单调秒、最多 24 次链接跳转。目录链接只作为条目记录，不递归展开；越出明确 allowlist 的目标不打开。凭据名称、非普通文件会列为排除项，不读取内容。超限停止并输出失败，不能把部分清点标成全部通过。原生文件系统调用仍可能超时，外层 `timeout` 另作保护。

包版本来自明确 prefix/underlay 下指定的 `share/<包名>/package.xml`。源码和安装文件按实际字节计算 SHA；链接文本、目标 SHA 与文件 SHA 分别记录。环境仅采集代码中列出的九个 ROS/库路径变量，不导出完整环境。ELF64 小端解析只读取直接 `DT_NEEDED`、`RUNPATH/RPATH`，没有运行 `ldd`，也不递归证明系统共享库全部满足。

## symlink-install 的具体证据

`--symlink-install` 适合开发，但安装目录可能仍指向源码、build 或其他前缀。审计报告会分别列出原安装目录和临时副本。副本的普通文件 SHA 以及链接文本应与原清点一致；原源码/build/underlay从不被移动、改名或删除。

如果 `package.xml` 指向原 source，程序或 `.so` 指向原 build，复制后这些依赖仍在副本之外。同机原目标存在只能解释为什么副本暂时能解引用，不能保证目标机器会有同一绝对路径。本实验不运行副本，也不通过删除原工作区制造故障。

`setup.bash`/`setup.sh`还可能记录构建时的 underlay 或前缀。本工具只提取有限的字面路径，不 source 它们。没有外部 symlink也不能推出自包含：普通安装仍可能依赖 `/opt/ros/jazzy`、系统动态库、架构、Python 和运行配置。当前教材 Dockerfile的 `colcon build --merge-install`没有使用 `--symlink-install`；本实验针对开发工作空间产物，不把该 Dockerfile错误归因为 symlink构建。

## 宿主 source + exec + 单PID TERM 正例

这是独立的实际节点检查。`host_entrypoint.sh`读取明确的可信 underlay/原 overlay，然后直接 `exec`已有 ELF。驱动等待 Config 构造事件，以 `/proc/<pid>/exe`和文件身份核对原 shell PID已经变成节点，检查该进程所有线程的孩子列表为空，再仅向该 PID发一次 SIGTERM，检查退出码和回收。

```bash
# 预期SHA应来自自己刚核对的原构建记录。这里先明确计算该原安装文件，传给检查器。
DEPLOYMENT_NODE_SHA=$(sha256sum /tmp/ros2-component-labs/install/lib/runtime_lab_components/config_node | cut -d ' ' -f 1)
timeout --signal=INT --kill-after=5s 25s /usr/bin/python3 examples/deployment_labs/host_exec_signal.py \
  --underlay-setup /opt/ros/jazzy/setup.bash \
  --overlay-setup /tmp/ros2-component-labs/install/setup.bash \
  --executable /tmp/ros2-component-labs/install/lib/runtime_lab_components/config_node \
  --expected-sha256 "$DEPLOYMENT_NODE_SHA" --domain-id 226 \
  --report /tmp/host-exec-signal.json
```

检查器清除子进程继承的旧 ROS 前缀/库路径，再由两个入口建立路径；固定本机 LOCALHOST/FastDDS 和独立域。它不修改当前 shell 或任何持久配置。所有等待都是单调软期限；正常只向保存的 PID发一次 TERM，失败后有界等待，必要时只对自己的 PID升级 KILL。

需要合并宿主实测时，在前面的审计命令中再加入 `--host-signal-report /tmp/host-exec-signal.json`；该报告必须已通过且位于 `/tmp`。合并保存输入报告的 SHA，仍不代表 Docker已经验证。

## Docker 与入口边界

ROS官方 Jazzy `ros-base`镜像定义包括构建工具与 rosdep初始化；具体镜像内容仍应按实际镜像摘要和架构核对。基础摘要不能冻结随后 apt软件源的内容。当前学习机没有 Docker命令，本轮不拉取镜像、不构建或运行容器。

`exec "$@"`仅把 shell换成它收到的直接命令。若命令是 `ros2 run`，PID1首先成为 CLI；对应版本实现再创建节点子进程，不能由 shell中的 exec单独证明所有停止信号都到达叶子节点。教材直接可执行路径应与镜像内固定 install前缀一致，Docker停止行为仍需在真实容器中专门验收。本次宿主正例只证明给定原安装节点的 PID/TERM/退出路径。

镜像归档 SHA证明传输文件一致；容器镜像 ID、仓库摘要、平台清单摘要用途不同。文件清点、目录复制和宿主 exit0都不证明跨机运行、Docker PID1行为、任意依赖兼容或设备已经停车。
