#include <memory>
#include "rclcpp/rclcpp.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("learning_hello_cpp");
  RCLCPP_INFO(node->get_logger(), "C++ node is ready");
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
