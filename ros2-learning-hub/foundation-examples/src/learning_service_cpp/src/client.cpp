#include <chrono>
#include <memory>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"
using namespace std::chrono_literals;
using Add = example_interfaces::srv::AddTwoInts;

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("learning_sum_client_cpp");
  auto client = node->create_client<Add>("sum");
  int exit_code = 1;
  if (!client->wait_for_service(2s)) {
    RCLCPP_ERROR(node->get_logger(), "sum service was not discovered");
  } else {
    auto request = std::make_shared<Add::Request>();
    request->a = 4;
    request->b = 8;
    auto future = client->async_send_request(request);
    auto status = rclcpp::spin_until_future_complete(node, future, 2s);
    if (status == rclcpp::FutureReturnCode::SUCCESS) {
      auto text = std::to_string(future.get()->sum);
      RCLCPP_INFO(node->get_logger(), "sum=%s", text.c_str());
      exit_code = 0;
    } else {
      RCLCPP_ERROR(node->get_logger(), "sum response timed out or was interrupted");
    }
  }
  rclcpp::shutdown();
  return exit_code;
}
