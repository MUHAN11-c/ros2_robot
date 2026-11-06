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
    const double initial_gain = declare_parameter<double>("gain", 1.0);
    declare_parameter<bool>("enabled", true);
    if (!valid_gain(initial_gain)) {
      throw std::invalid_argument("gain must be finite and within [0, 2]");
    }
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
    publisher_ = create_publisher<std_msgs::msg::Float64>("configured_value", 10);
    timer_ = create_wall_timer(1s, [this]() {
      std_msgs::msg::Float64 message;
      message.data = get_parameter("enabled").as_bool()
        ? 0.2 * get_parameter("gain").as_double() : 0.0;
      publisher_->publish(message);
      RCLCPP_INFO(get_logger(), "value=%.3f", message.data);
    });
  }
private:
  static bool valid_gain(double value)
  {
    return std::isfinite(value) && value >= 0.0 && value <= 2.0;
  }
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr callback_;
  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  int exit_code = 0;
  try {
    rclcpp::spin(std::make_shared<ConfigNode>());
  } catch (const std::exception & error) {
    RCLCPP_ERROR(rclcpp::get_logger("config_startup"), "%s", error.what());
    exit_code = 1;
  }
  rclcpp::shutdown();
  return exit_code;
}
