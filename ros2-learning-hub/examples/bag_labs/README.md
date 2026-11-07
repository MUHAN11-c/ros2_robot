# rosbag2：从录制到读回再到筛选回放

面向Ubuntu24.04 / ROS2 Jazzy。只产生合成软件数据，不接硬件；时间、序号、缓存与格式各自验收。实际结果以同次报告为准，不把本目录存在当作已经运行。

从教材目录运行：

```bash
# 输入：本机Jazzy、rclpy、geometry_msgs、rosgraph_msgs、rosbag2及两个存储插件。
# 输出：独立/tmp目录、关闭后的bag、日志与报告；不覆盖已有bag。
source /opt/ros/jazzy/setup.bash
# 外层INT与强制截止仅作最后防护；正常实验由单调软期限和有限输入结束。
timeout --signal=INT --kill-after=8s 100s python3 examples/bag_labs/record_replay_lab.py
```

脚本先记录SQLite系统时间正例、MCAP软件时间正例，再记录静态历史请求为volatile的反例。每组只发布6个合成位置与6个派生序号；静态String在录制器启动前只发布一次，发布者保持存活。正例预期6+6+1，volatile反例预期6+6+0。缺少历史缓存与消息格式损坏是不同故障。

`--use-sim-time`阶段先不发clock，再只发值为零的clock，最后推进10秒起的正值时钟。前三类测试数据分别使用100/101、200/201与0..5序号，读回能够检查门前数据是否被补录。Header从1000秒起，每序号增加10ms；软件记录时间从10秒起，每序号增加250ms。两者故意不同，均不是传感器实测。

每次主动停止录制器并关闭后，`inspect_bag.py`读回元数据、计数、记录时间、Header和载荷SHA，另实际运行bag info。随后销毁原发布者并确认话题发布端点为零。播放器从暂停开始，等端点和Resume服务就绪后再继续，避免用固定sleep冒充发现成功。

发布前和回放后比较全部Header/Point字段。另一次序列化可能产生不同CDR对齐padding，不能把SHA不同直接判成消息内容损坏；首次实验在这里暴露了夹具错误，历史保留。原bag载荷SHA用于标识实际记录字节；显式Writer把同一bytes写入两个存储时，才另外逐字节核对该输入。

SQLite包完整回放不加`--clock`：订阅者即使设use_sim_time，Header也不会自动变成它的ROS时钟。MCAP包只回放input并显式产生clock，核输入6条、派生输出0条、静态状态0条及唯一clock来源。保持旧派生输出不重放，才能让新的计算模块负责自己的输出；这里没有启动真实算法或宣称轨迹复现。

关闭的bag还可独立检查，路径用本次JSON中的bagDirectory替换：

```bash
# 输入：已停止录制的小型bag；输出：只读JSON，不启动ROS节点。
python3 examples/bag_labs/inspect_bag.py /tmp/本次实验/sim_mcap --storage mcap
# 显式写入相同载荷和不同recv/send时间，再核SQLite表与MCAP字段。
python3 examples/bag_labs/storage_fields.py
```

`storage_fields.py`把Header=7s、recv=10s、send=9s写入两种插件。SQLite按当前schema只保存接收timestamp，MCAP保存logTime与publishTime；普通Python `read_next`只返回topic、载荷与接收时间，不能据此宣称已读出发送时间。MCAP字段探针只解析本例noChunking单消息小文件，不是通用MCAP解析器或压缩/性能建议。时间差由输入指定，不是网络时延测量。

所有等待使用monotonic秒；消息时间为整数ns；合成point.x单位m，整数值另兼作无量纲序号。脚本限定独立域231、LOCALHOST和FastDDS，清理自己的节点与新建进程组，记录必要升级信号。域不是认证。父SIGINT与原生卡住分支须另外注入才能称为验证，常规退出证据不自动覆盖这些分支。

不覆盖真实相机/TF、吞吐、压缩、文件损坏恢复、多机校时、任意类型或硬件安全。来源按教材相关章节与独立审查记录列示，上游许可不受此目录影响。
