# 应用章节离线实验

日期：2026-11-07（Asia/Shanghai）。输入固定在 `applied_labs.py` 的八个函数中；只使用 Python 标准库，不连接 ROS、仿真器或硬件。

从 `ros2-learning-hub/` 目录运行：

```bash
# 一次执行全部八个实验；每项包含可解释的输出和断言。
python3 examples/theory_labs/applied_labs.py
# 也可只选一个实验；未知名称会被参数解析器拒绝。
python3 examples/theory_labs/applied_labs.py --case planning
```

| case | 对应章节 | 本轮实际检查与结果 |
| --- | --- | --- |
| `engineering` | C++ 软件工程 | 总预算 16 ms、余量 4 ms；拒绝过旧和未来样本；缓存示例为 4 槽 |
| `slam` | SLAM 原理 | 位姿解为 1.033333 m、2.066667 m；残差平方和由 0.04 降为 0.013333 m²；验证平移规范自由度 |
| `planning` | 运动规划 | A* 与 Dijkstra 均为十四步、1.4 m；逐边相邻与避障检查；封路返回无路 |
| `optimal-control` | 最优控制 | Riccati 值函数与直接累计代价一致；最优代价约 14.8063，零输入代价 100 |
| `legged` | 足式原理 | 捕获点超出当前支撑的反例；可达捕获点条件下速度衰减与捕获点守恒 |
| `aerial` | 无人机接口 | ENU/NED 与 FLU/FRD 往返、长度保持；1.5 kg 的理想总悬停推力为 14.715 N |
| `navigation` | 导航项目 | 理想停车距离 0.345 m；旧任务事件不覆盖当前任务、首个终态幂等 |
| `manipulation` | 机械臂项目 | 五次轨迹 T=3.75 s；端点条件与速度/加速度限制检查 |

`source/applied-robotics.json` 中的八个 `complete` Python 代码块另经独立文件、独立进程执行，均返回 0，因此这些完整示例不依赖合并入口的外部全局变量。全部 Python 代码块通过语法解析；17 组公式通过项目所用 TeX→MathML 转换器。

另外，C++ 工程章的 `velocity_cache.hpp` 代码块已使用 `g++ -std=c++17 -Wall -Wextra -Werror -pthread` 编译，检查空缓存、旧样本、未来样本、过期读取和并发快照字段一致性。该检查不等于完整的数据竞争证明，也不证明硬实时截止期。

Panda MoveIt C++ 包、项目仿真launch和安装命令仍是待运行的集成步骤。本轮随后对独立有界导航客户端完成12类隔离假服务端协议测试，记录见 `../navigation/README.md`；仍未启动完整Nav2/Gazebo或机器人。章节中的预期现象不能代替后续 ROS 日志。八个数值实验只验证各自声明的简化模型，不覆盖实体足印、完整 SLAM、摩擦接触、真实飞控或机械臂抓取能力。
