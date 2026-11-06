#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class LearningListener : public rclcpp::Node
{
public:
  LearningListener() : Node("learning_listener_cpp")
  {
    subscription_ = create_subscription<std_msgs::msg::String>(
      "telemetry", 10,
      [this](std_msgs::msg::String::ConstSharedPtr message) {
        on_message(message);
      });
  }
private:
  void on_message(std_msgs::msg::String::ConstSharedPtr message)
  {
    RCLCPP_INFO(get_logger(), "received: %s", message->data.c_str());
  }
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<LearningListener>());
  rclcpp::shutdown();
  return 0;
}
