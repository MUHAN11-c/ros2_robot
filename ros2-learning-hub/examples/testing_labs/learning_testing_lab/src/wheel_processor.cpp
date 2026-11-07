// 软件转换节点：input_twist的linear.x[m/s]和angular.z[rad/s]→wheel_rates.data[左,右][rad/s]。
// 没有/cmd_vel、电机或仿真连接。进程仅在收到输入时计算输出，不自行生成通过测试的数据。
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"
#include "learning_testing_lab/wheel_rates.hpp"

class WheelProcessor : public rclcpp::Node
{
public:
  WheelProcessor()
  : Node("wheel_processor", rclcpp::NodeOptions().start_parameter_services(false))
  {
    track_m_ = declare_parameter<double>("track_m", 0.4);
    radius_m_ = declare_parameter<double>("radius_m", 0.1);
    const bool suppress_ready = declare_parameter<bool>("suppress_ready", false);
    // 启动时即验证几何；参数只读入一次，不宣称参数服务能自动重建本节点配置。
    learning_testing_lab::wheel_rates(0.0, 0.0, track_m_, radius_m_);
    publisher_ = create_publisher<std_msgs::msg::Float64MultiArray>("wheel_rates", 10);
    subscription_ = create_subscription<geometry_msgs::msg::Twist>("input_twist", 10,
      [this](geometry_msgs::msg::Twist::ConstSharedPtr input) {
        try {
          const auto rates = learning_testing_lab::wheel_rates(
            input->linear.x, input->angular.z, track_m_, radius_m_);
          std_msgs::msg::Float64MultiArray output;
          output.data = {rates.left_rad_s, rates.right_rad_s};
          publisher_->publish(output);
        } catch (const std::exception & error) {
          // 非法输入不沿用旧输出、不把NaN转发到下游；测试的故障开关不改变这段算法。
          RCLCPP_WARN(get_logger(), "input rejected: %s", error.what());
        }
      });
    // 可观测业务就绪标记只在输入/输出端点和配置均建立后打印。
    // 测试故障只隐藏此标记，使原样的就绪断言失败，而不是在测试中分支“预期失败即通过”。
    // 独立启动标记让故障配置也有进程I/O记录；不能把“进程有输出”误当业务READY。
    RCLCPP_INFO(get_logger(), "WHEEL_PROCESSOR_STARTED");
    if (!suppress_ready) {RCLCPP_INFO(get_logger(), "WHEEL_PROCESSOR_READY");}
  }
private:
  double track_m_, radius_m_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr publisher_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<WheelProcessor>());
  if (rclcpp::ok()) {rclcpp::shutdown();}
  return 0;
}
