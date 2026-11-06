// SPDX-License-Identifier: Apache-2.0
#include <chrono>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"

int main(int argc, char **argv) {
  using namespace std::chrono_literals;
  using Add = example_interfaces::srv::AddTwoInts;
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("atlas_add_client_cpp");
  auto client = node->create_client<Add>("add_two_ints");
  if (!client->wait_for_service(5s)) {
    RCLCPP_ERROR(node->get_logger(), "Service unavailable after 5 seconds");
    rclcpp::shutdown();
    return 1;
  }
  auto request = std::make_shared<Add::Request>();
  request->a = 7;
  request->b = 5;
  auto future = client->async_send_request(request);
  const auto result = rclcpp::spin_until_future_complete(node, future, 5s);
  if (result != rclcpp::FutureReturnCode::SUCCESS) {
    client->remove_pending_request(future);
    RCLCPP_ERROR(node->get_logger(), "Request timed out or interrupted");
    rclcpp::shutdown();
    return 1;
  }
  RCLCPP_INFO(node->get_logger(), "SUM=%ld", static_cast<long>(future.get()->sum));
  rclcpp::shutdown();
  return 0;
}
