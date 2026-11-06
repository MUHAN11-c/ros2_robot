// SPDX-License-Identifier: Apache-2.0
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("atlas_add_server_cpp");
  using Add = example_interfaces::srv::AddTwoInts;
  auto service = node->create_service<Add>("add_two_ints",
    [](const std::shared_ptr<Add::Request> request,
       std::shared_ptr<Add::Response> response) {
      // 本练习使用小整数 7 和 5；生产接口还需定义数值范围。
      response->sum = request->a + request->b;
    });
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
