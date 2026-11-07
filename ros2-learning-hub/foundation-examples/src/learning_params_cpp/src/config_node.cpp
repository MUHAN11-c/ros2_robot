// 【中文教学注释】 foundation-examples/src/learning_params_cpp/src/config_node.cpp
// 输入输出：输入为启动覆盖值或动态参数请求；输出为 gain/enabled 的验证结果和 configured_value。
// 执行顺序与边界：gain 为有限无量纲 double，范围 [0,2]；先验证启动值，再注册动态验证器。回调通过后才应提交配置，参数回调不能阻塞执行器。
#include <chrono>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <vector>
#include "rclcpp/rclcpp.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"
#include "std_msgs/msg/float64.hpp"
using namespace std::chrono_literals;

class ConfigNode : public rclcpp::Node
{
public:
  ConfigNode() : Node("learning_config")
  {
    // 声明参数类型与默认值，并取得启动覆盖值；gain是无量纲double，仍须检查有限性与[0,2]范围。
    const double initial_gain = declare_parameter<double>("gain", 1.0);
    declare_parameter<bool>("enabled", true);
    if (!valid_gain(initial_gain)) {
      throw std::invalid_argument("gain must be finite and within [0, 2]");
    }
    // 保存动态参数验证回调句柄；句柄销毁会移除注册。验证器只返回是否接受，不做不可回滚的业务修改。
    callback_ = add_on_set_parameters_callback(
      [](const std::vector<rclcpp::Parameter> & parameters) {
        rcl_interfaces::msg::SetParametersResult result;
        result.successful = true;
        for (const auto & parameter : parameters) {
          if (parameter.get_name() == "gain" &&
              (parameter.get_type() != rclcpp::ParameterType::PARAMETER_DOUBLE ||
               !valid_gain(parameter.as_double()))) {
            result.successful = false;
            result.reason = "gain must be a finite double within [0, 2]";
            break;
          }
        }
        return result;
      });
    // 创建指定模板消息类型和话题的发布端；整数10是KeepLast历史条数，不是频率。发布者必须作为成员或其他长寿命对象保留。
    publisher_ = create_publisher<std_msgs::msg::Float64>("configured_value", 10);
    // 创建墙钟/稳态周期定时器，chrono时长明确单位；回调由执行器调度，不随/clock仿真时钟暂停而自然暂停。
    timer_ = create_wall_timer(1s, [this]() {
      std_msgs::msg::Float64 message;
      // 读取已提交参数并按声明类型取值；enabled选择是否输出，gain决定教学值的无量纲比例。
      message.data = get_parameter("enabled").as_bool()
        ? 0.2 * get_parameter("gain").as_double() : 0.0;
      // 提交当前消息给发布端；日志/返回不提供订阅者业务处理确认，端到端行为还取决于QoS、网络和对端执行器。
      publisher_->publish(message);
      // 记录当前状态/错误供实验核对；printf格式必须匹配传入类型，日志不等于对端已收到数据。
      RCLCPP_INFO(get_logger(), "value=%.3f", message.data);
    });
  }
private:
  static bool valid_gain(double value)
  {
    // 拒绝NaN和正负无穷，再检查闭区间[0,2]；只比较大小不足以构成完整的数值输入验证。
    return std::isfinite(value) && value >= 0.0 && value <= 2.0;
  }
  // 持久共享句柄维持ROS对象/目标的寿命；智能指针只管理生存期，不自动解决多线程数据竞争。
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr callback_;
  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  // 初始化进程 ROS 上下文、解析 ROS 参数；必须先于 Node 和通信对象创建。
  rclcpp::init(argc, argv);
  int exit_code = 0;
  try {
    // 持有节点并进入默认单线程执行器，回调在这里得到执行；返回后才能按退出顺序关闭上下文。
    rclcpp::spin(std::make_shared<ConfigNode>());
  } catch (const std::exception & error) {
    RCLCPP_ERROR(rclcpp::get_logger("config_startup"), "%s", error.what());
    exit_code = 1;
  }
  // 关闭当前上下文，让执行器退出；确保异步回调不再访问已销毁对象，不能替代业务层故障处理。
  rclcpp::shutdown();
  return exit_code;
}
