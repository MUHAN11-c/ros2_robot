# 测试原例：测试通过与合同覆盖分开看

`baseline_sources.json`逐字节保存第3轮教材的policy.py、test_policy.py、test_talker.py。旧策略只有速度有限性检查，没有纳秒参数类型合同；这是故意保留的教学基线，不能作为修订后的策略使用。

本目录的`policy.py`将纳秒时戳/期限限定为内置整数，bool不算整数时刻，避免float精度或NaN比较绕过过期判断。正整数期限是配置；非法期限抛ValueError。非法运行速度/时刻、缺失、未来、过期返回0.0。速度单位m/s，纳秒差值用整数相减，恰好期限仍有效。速度幅值、时基来源和设备停止属于调用者合同。

从完整教材的ros2-learning-hub目录执行：

```bash
source /opt/ros/jazzy/setup.bash
# 需要pytest、launch_testing、launch_ros、rclpy、std_msgs、demo_nodes_cpp。
/usr/bin/python3 examples/testing_policy/verify_existing.py \
  --output /tmp/testing-existing-result.json
```

仅检查标准库策略与pytest时可加`--unit-only`，报告会明确没有运行ROS集成。`--help`不加载ROS。旧4项pytest先通过，6个合同反例再暴露盲点；修订后的31项参数化测试验证整数纳秒、有限性和配置/运行数据的区别。原talker集成例另检查实际消息与关闭后的退出码，不因ReadyToTest已触发就断言业务就绪。

独立源码工程下载解压后，应将路径`examples/testing_policy/`改为`testing_policy/`。完整目录包含基线JSON、修订策略、测试和driver；只复制driver会缺少它明确依赖的输入。报告默认/tmp，不改教材绑定证据；域230仅LOCALHOST/FastDDS。子进程按各20/40秒保护，失败只清理自己创建的进程组。没有设备、物理制动、跨机或全部故障验证。
