// SPDX-License-Identifier: Apache-2.0
#include <chrono>
#include <memory>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class Talker : public rclcpp::Node {
public:
  Talker() : Node("atlas_talker_cpp") {
    publisher_ = create_publisher<std_msgs::msg::String>("chatter", 10);
    timer_ = create_wall_timer(std::chrono::milliseconds(250), [this]() {
      std_msgs::msg::String message;
      message.data = "ATLAS_MESSAGE cpp " + std::to_string(count_++);
      publisher_->publish(message);
      RCLCPP_INFO(get_logger(), "SENT %s", message.data.c_str());
    });
  }
private:
  std::size_t count_{0};
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};
int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Talker>());
  rclcpp::shutdown();
  return 0;
}
