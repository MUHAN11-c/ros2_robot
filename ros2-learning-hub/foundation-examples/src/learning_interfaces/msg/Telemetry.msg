# 【中文教学注释】 foundation-examples/src/learning_interfaces/msg/Telemetry.msg
# 输入输出：输入为 msg/srv/action 定义及生成配置；输出为两种语言可使用的类型和 wheel_feedback 测量。
# 执行顺序与边界：接口必须先生成并加载再导入；轮速单位 rad/s，Header 指定采样时刻与坐标系，gain 无量纲，valid 不能被缺省数值替代。
# Sample time and the frame convention for this measurement.
# 采样时间以sec/nanosec表示，frame_id声明本测量坐标约定；接收方不能只看速度数值而忽略时间与坐标。
std_msgs/Header header
# Positive velocity means forward rolling; unit: rad/s.
# 轮关节角速度rad/s；正方向按本接口约定，不是底盘线速度m/s。
float64 left_velocity_rad_s
float64 right_velocity_rad_s
# 显式标注测量是否有效；false时接收方不能把默认0速度当作可信停车反馈。
bool valid
