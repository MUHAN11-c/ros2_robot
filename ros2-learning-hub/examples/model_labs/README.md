# 参数化模型、安装资源与无GUI TF验收

环境为Ubuntu24.04 / ROS2 Jazzy，依赖ament_cmake、xacro、urdfdom工具、robot_state_publisher、rclpy及tf2_geometry_msgs。目录提供完整learning_description资源包与独立driver，不依赖urdf_tutorial，不启动RViz、Gazebo或真实驱动。

从教材目录运行：

```bash
# 输入：本目录完整包和已安装ROS依赖；输出：独立/tmp构建/模型/日志/报告。
source /opt/ros/jazzy/setup.bash
# 有限命令与单调等待正常结束；外层timeout只作最后防护。
timeout --signal=INT --kill-after=8s 120s python3 examples/model_labs/validate_model.py
```

driver普通复制安装一个包，不用symlink-install；核安装URDF/Xacro/launch字节与源一致，再从空当前目录启动。它不证明跨机依赖闭包。两个尺寸默认只在Xacro定义，launch空参数沿用默认，再核展开后的范围；显式覆盖半径0.10m/轮距0.40m另验收。裸xacro负责展开，不等于自动满足本例尺寸合同。

默认轮半径0.08m、轮距0.36m，车体中心离base_footprint为r+0.06m。根base_footprint和光学frame只表达参考坐标，不分配刚体质量。其余五个实体提供假设均匀盒体/圆柱的惯量；检查正值与主惯量三角关系，不是实际质量测量、碰撞或物理仿真。车轮圆柱轴已转向关节Y，轴向惯量随之放在Iyy。

包有七link、四fixed和两continuous关节。参数响应后才创建TF Listener，检查晚加入固定边；活动边在没有JointState时不存在。随后只发原始关节名字left_wheel_joint/right_wheel_joint，TF才加model/或alternate/前缀。frame_prefix不自动改消息里的关节键，也不自动替你在任意前缀后加斜杠。

有效位置0/0及π/2、-π/4rad分别核平移与旋转，q和-q按同一旋转处理。默认案例还发name/position不等长的非法长度，以及position空但velocity等长的合法velocity-only消息。后者符合JointState可选数组协议，RSP却无法据其计算位置，警告并跳过。分别核日志与0.25s有限窗口中TF时戳不变，再恢复位置输入。RSP不把速度积分成关节位置；20Hz配置是发布节流上限，并非没有状态也自动生成新变换。

camera_link采用X前/Y左/Z上，camera_optical_frame采用Z前/X右/Y下。固定rpy(-π/2,0,-π/2)后，三个光学单位点变到base_link分别为(1.18,0,0.10)、(0.18,-1,0.10)、(0.18,0,-0.90)m。它们含相机原点平移，不是纯方向向量；没有采集任何图像。

`inspect_model.py`只用标准库检查已展开小模型的树、盒体/圆柱正尺寸和对角惯量。真正语法解析另运行check_urdf；两者通过不保证机械标定、任意URDF、模型资源或动力学正确。CLI帮助不需要ROS导入：

```bash
python3 examples/model_labs/validate_model.py --help
python3 examples/model_labs/inspect_model.py --help
```

完整独立构建/手动启动也可以采用：

```bash
# 普通复制安装，日志与构建空间全部留在/tmp；输出路径自行取新实验目录。
colcon --log-base /tmp/model-demo/log build --base-paths examples/model_labs/learning_description \
  --build-base /tmp/model-demo/build --install-base /tmp/model-demo/install --merge-install
source /tmp/model-demo/install/setup.bash
# 从其他当前目录也能解析安装share；此入口只启动RSP，活动轮子需唯一JointState来源。
ros2 launch learning_description model.launch.py wheel_radius:=0.10 wheel_separation:=0.40
```

新报告默认在/tmp，维护者审核后才刷新教材绑定的证据。保留失败历史和实际版本；检查父launch退出与其记录的子PID，不停止用户ROS daemon。父SIGINT/原生挂起、RViz资源显示、真实状态源、动力学、控制、仿真与硬件仍需各自验证。
