# 一个完整的 ROS 2 测试包

本目录用 `learning_testing_lab` 串起算法测试、消息边界测试和真实进程/话题集成测试。它接收软件 `Twist`，计算差速两轮角速度，再由 `rclpy` probe 检查结果。没有机器人、Gazebo 或电机连接，话题使用每次生成的唯一命名空间，输入名为 `input_twist`，不是 `/cmd_vel`。

## 文件和合同

| 文件 | 输入与输出 | 验证责任 |
| --- | --- | --- |
| `include/learning_testing_lab/wheel_rates.hpp` | 前向速度 m/s、yaw 角速度 rad/s、轮距/半径 m → 左右轮速 rad/s | 平面纯滚动模型；有限数值、正几何及结果溢出检查 |
| `src/wheel_processor.cpp` | `Twist.linear.x/angular.z` → `Float64MultiArray.data=[左,右]` | 真实节点消息处理；收到输入才产生输出 |
| `python/wheel_reader.py` | 两个有限轮速 → 带单位命名字段的不可变快照 | 下游消息边界，不重复实现 C++ 差速算法 |
| `test/test_wheel_math.cpp` | 外部手算值和非法模型输入 | 4 个 gtest 案例 |
| `test/test_rate_reader.py` | 已知消息、错误维数、NaN/Inf/bool | 7 个 pytest 案例 |
| `test/test_wheel_launch.py` | `rclpy` 软件发布者、真实 C++ 进程、话题与退出事件 | 1 个 active 案例和 1 个 post-shutdown 案例 |

轮距为 `0.4 m`、半径为 `0.1 m` 时，`v=0.6 m/s`、`yaw_rate=0.5 rad/s` 对应左右轮缘速度 `0.5/0.7 m/s`，因此角速度是 `5/7 rad/s`。直行为 `6/6 rad/s`；原地左转为 `-1/+1 rad/s`。gtest 使用这些手算 oracle，绝对容差为 `1e-12 rad/s`，没有从实现返回值生成期望值。

集成测试先验证真实输入得到 `5/7`，再改为零输入，验证结果随输入变化为 `0/0`。第二阶段能发现“节点忽略输入、只固定输出通过测试数值”的假实现。这里的零输出只表示收到零软件输入后的换算结果，不是物理停车证明。

## 依赖与一键验收

适用 Ubuntu 24.04 / ROS 2 Jazzy。需要 `ament_cmake_gtest`、`ament_cmake_pytest`、`launch_testing_ament_cmake`、`launch_testing`、`launch_ros`、`rclpy`、`geometry_msgs`、`std_msgs`、pytest 和 gtest。本机安装版本由报告记录；该轮依赖已齐全，无需全局升级。

```bash
# 从ros2-learning-hub目录执行；帮助不导入ROS，也不创建进程/构建目录。
python3 examples/testing_labs/verify_testing_labs.py --help
source /opt/ros/jazzy/setup.bash
# 构建、正常/故障测试、XML核查、中断清理与最终正常测试均由驱动执行。
python3 examples/testing_labs/verify_testing_labs.py \
  --build-root /tmp/ros2-hub-testing-labs --domain-id 231 \
  --output /tmp/testing-labs-rerun.json
```

默认报告另存 `/tmp`，不会覆盖教材绑定证据。维护者明确使用 `--output validation-evidence/testing-labs-current-validation.json` 才保存本站报告。每次重跑保留旧报告为 `priorAttempts`；预期受控失败的原始 XML 和日志单独快照，不会被下一条测试覆盖而消失。

## 注册、构建和数量核对

包的 `CMakeLists.txt`、`package.xml` 都完整保留。`BUILD_TESTING=ON` 下通过 `ament_add_gtest`、`ament_add_pytest_test` 和 `add_launch_test` 注册三个 CTest 项。**3 个注册项与 13 个细分 JUnit 案例是两种计数**，不是测试内部 assert 的条数；工具的聚合汇总可能还包括包装结果，应结合报告中的原始 CLI 输出解释。

脚本为正常与缺就绪变体分别执行完整构建。手工正常路径等价于：

```bash
colcon --log-base /tmp/ros2-hub-testing-labs/good/log-build build \
  --base-paths examples/testing_labs/learning_testing_lab \
  --build-base /tmp/ros2-hub-testing-labs/good/build \
  --install-base /tmp/ros2-hub-testing-labs/good/install --merge-install --symlink-install \
  --packages-select learning_testing_lab --cmake-args -DBUILD_TESTING=ON -DTESTING_LAB_READY_FAULT=OFF
source /tmp/ros2-hub-testing-labs/good/install/setup.bash
export ROS_DOMAIN_ID=231
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
colcon --log-base /tmp/ros2-hub-testing-labs/good/log-test test \
  --base-paths examples/testing_labs/learning_testing_lab \
  --build-base /tmp/ros2-hub-testing-labs/good/build \
  --install-base /tmp/ros2-hub-testing-labs/good/install --merge-install \
  --packages-select learning_testing_lab --return-code-on-test-failure
colcon --log-base /tmp/ros2-hub-testing-labs/good/log-result test-result \
  --test-result-base /tmp/ros2-hub-testing-labs/good/build --verbose
```

驱动先读取 CTest JSON 注册列表，要求名称恰好为 `test_wheel_math`、`test_rate_reader`、`test_wheel_launch`。每阶段只删除它自己构建目录下三个预期 XML，再执行测试，防止旧 XML 冒充本次结果；随后逐份要求案例数分别为 `4/7/2`、没有跳过。缺文件、零测试、数量不符或非预期失败都会使驱动失败，不能因为命令退出 0 就跳过这些条件。

## 可复现的缺失就绪条件

第二个构建目录使用 `-DTESTING_LAB_READY_FAULT=ON`。它通过测试环境配置让被测进程不打印 `WHEEL_PROCESSOR_READY`，但保留独立 `WHEEL_PROCESSOR_STARTED` 启动标记，不改算法源文件、不删测试、不改期望断言。active 测试依然要求业务就绪，最多等待 `2.5 s` 后应实际失败；post-shutdown 测试仍须验证被测进程退出。启动标记也让日志处理器有该进程的I/O记录，避免把静默进程查找错误混同为预期就绪断言。

`ReadyToTest()` 只让测试框架开始执行，并不证明业务就绪。正常测试还分别检查业务标记、输入端点匹配及真实消息到达。故障版没有完成话题验证，不能把该阶段的失败解释为算法已经通过完整集成测试。

本机首轮正常 `test-result` 汇总实际为16项：3个CTest包装结果加13个细分案例。报告同时保存这个原始CLI汇总与逐份JUnit计数，不把16项说成16个独立业务案例。故障时包装结果和内部断言也可能分别计入失败数，应以具体XML和案例名判断。

本机 colcon 源码对 CTest 的测试失败事件与命令任务错误有区别：默认 `colcon test` 可能返回 0；`--return-code-on-test-failure` 才要求非零反映测试失败。`colcon test-result --verbose` 根据解析到的失败/错误返回非零，但没有结果时也可能返回 0。驱动对以下每项都实际运行命令并保存结果，不把它们只当规则复述：

1. 正常配置，默认 `colcon test`，JUnit 必须 13 例、0 失败。
2. 缺业务就绪配置，默认命令；必须保留 13 例、1 个真实失败。
3. 同一故障配置，加入严格失败退出选项，再保存独立 XML 快照。
4. 对真实执行中的正常测试发送父 SIGINT，检查只回收自建进程。
5. 再运行正常严格测试，恢复最终正常 XML，最后核对 `test-result`。
6. 查询一个专属空结果目录，记录 CLI 的实际退出码，但明确拒绝把零结果当通过。

预期故障被正确检出，表示本教学实验完成了反例验证；**故障配置本身没有通过软件测试**。报告将这两个结论分开写。

## fixture、期限和进程清理

active fixture 使用专属 `Context`、节点和单线程执行器；每轮即便断言失败也销毁 pub/sub、节点并关闭 Context。`spin_once` 每次空闲等待最多 `0.02 s`；端点和每种输出的总期限分别为 `4 s`。框架后置案例只在进程关闭后核对退出码 `0`，不会拿 active 断言成功代替退出证明。

驱动每条构建命令有 `100 s` 上限，测试命令有 `60 s` 上限，结果查询有 `15 s` 上限；CTest 的 launch 项还有 `25 s` 保护。期限都是普通系统软期限，阻塞回调与调度负载仍需单独评估。

Linux 下驱动使用子收割器和 `/proc` 父子关系，只登记自己启动的命令及后代，保存 PID/startTicks，防止 PID 复用时误杀无关进程。收到父 SIGINT/超时时先只给命令根 PID 发一次 INT，让框架清理 fixture；必要时才对仍匹配身份的自建后代升级 TERM/KILL，并回收被接管的孤儿。它不扫描或终止 ROS daemon、其他工作空间或硬件进程。

独立中断验证会先观察真实的 `5/7` 和 `0/0` 话题结果，通过测试夹具默认关闭的短保持窗口，给验收子驱动发 SIGINT。它要求实际测试应用与驱动均消失、自己的应急清理未被使用，记录完整命令/信号/结果。此生命周期验证不计为新的业务单元测试，也不把退出当成机器人停车。

## 证据范围

报告保存源码/CMake/package/README SHA、软件包版本、固定 Jazzy 与本机已安装一手源码的核对位置、每条完整命令及退出码、各阶段原始 XML/日志、话题观测、ELF SHA 和进程回收。固定参考快照与实际安装版本分开记录。

未覆盖真实机器人、仿真、跨机器网络、硬实时、任意调度负载、硬件制动或所有 gtest/pytest/launch 插件行为。这个完整包证明所列合同能被注册、执行、故意破坏并通过结果文件检出；不把工具存在、零测试或无断言崩溃当作验证完成。
