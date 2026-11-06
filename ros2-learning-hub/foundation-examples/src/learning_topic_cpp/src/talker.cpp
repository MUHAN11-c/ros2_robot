#include <chrono>
#include <cstdint>
#include <memory>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
using namespace std::chrono_literals;

class LearningTalker : public rclcpp::Node
{
public:
  LearningTalker() : Node("learning_talker_cpp")
  {
    publisher_ = create_publisher<std_msgs::msg::String>("telemetry", 10);
    timer_ = create_wall_timer(500ms, [this]() {
      std_msgs::msg::String message;
      message.data = "cpp sample=" + std::to_string(sequence_++);
      publisher_->publish(message);
      RCLCPP_INFO(get_logger(), "%s", message.data.c_str());
    });
  }
private:
  std::uint64_t sequence_{0};
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<LearningTalker>());
  rclcpp::shutdown();
  return 0;
}
