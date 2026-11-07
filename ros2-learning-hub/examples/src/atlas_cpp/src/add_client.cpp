// SPDX-License-Identifier: Apache-2.0
// 【中文教学注释】 examples/src/atlas_cpp/src/add_client.cpp
// 输入输出：输入为 AddTwoInts 请求中的两个小整数；输出为 sum 响应和成功/失败退出码，无物理单位。
// 执行顺序与边界：先发现服务再发请求；Future 返回不等于响应已完成，等待超时不会撤销服务端已经发生的业务副作用。
#include <chrono>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"

int main(int argc, char **argv) {
  using namespace std::chrono_literals;
  using Add = example_interfaces::srv::AddTwoInts;
  // 初始化进程 ROS 上下文、解析 ROS 参数；必须先于 Node 和通信对象创建。
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("atlas_add_client_cpp");
  // 建立请求接口类型与服务名的客户端；创建成功不等于服务端已发现，仍需wait_for_service。
  auto client = node->create_client<Add>("add_two_ints");
  // 等待服务发现，chrono时长限定本地等待期限；返回false走失败分支，不把发现成功当作响应成功。
  if (!client->wait_for_service(5s)) {
    // 记录当前状态/错误供实验核对；printf格式必须匹配传入类型，日志不等于对端已收到数据。
    RCLCPP_ERROR(node->get_logger(), "Service unavailable after 5 seconds");
    // 关闭当前上下文，让执行器退出；确保异步回调不再访问已销毁对象，不能替代业务层故障处理。
    rclcpp::shutdown();
    return 1;
  }
  auto request = std::make_shared<Add::Request>();
  request->a = 7;
  request->b = 5;
  // 异步发送请求并返回Future或注册完成回调；执行器必须继续推进，超时仅影响本地等待，不撤销远端副作用。
  auto future = client->async_send_request(request);
  // 分发回调直到Future完成、给定chrono期限到达或中断；只适用于此处一次性main流程，不能嵌套spin已被执行器持有的同一节点。
  const auto result = rclcpp::spin_until_future_complete(node, future, 5s);
  if (result != rclcpp::FutureReturnCode::SUCCESS) {
    client->remove_pending_request(future);
    RCLCPP_ERROR(node->get_logger(), "Request timed out or interrupted");
    rclcpp::shutdown();
    return 1;
  }
  // 只在Future已完成时读取响应；get可能抛出异常，不能把其视为无错误、无阻塞的任意时刻查询。
  RCLCPP_INFO(node->get_logger(), "SUM=%ld", static_cast<long>(future.get()->sum));
  rclcpp::shutdown();
  return 0;
}
