// 【中文教学注释】 foundation-examples/src/learning_service_cpp/src/client.cpp
// 输入输出：输入为 AddTwoInts 请求中的两个小整数；输出为 sum 响应和成功/失败退出码，无物理单位。
// 执行顺序与边界：先发现服务再发请求；Future 返回不等于响应已完成，等待超时不会撤销服务端已经发生的业务副作用。
#include <chrono>
#include <memory>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"
using namespace std::chrono_literals;
using Add = example_interfaces::srv::AddTwoInts;

int main(int argc, char ** argv)
{
  // 初始化进程 ROS 上下文、解析 ROS 参数；必须先于 Node 和通信对象创建。
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("learning_sum_client_cpp");
  // 建立请求接口类型与服务名的客户端；创建成功不等于服务端已发现，仍需wait_for_service。
  auto client = node->create_client<Add>("sum");
  int exit_code = 1;
  // 等待服务发现，chrono时长限定本地等待期限；返回false走失败分支，不把发现成功当作响应成功。
  if (!client->wait_for_service(2s)) {
    // 记录当前状态/错误供实验核对；printf格式必须匹配传入类型，日志不等于对端已收到数据。
    RCLCPP_ERROR(node->get_logger(), "sum service was not discovered");
  } else {
    auto request = std::make_shared<Add::Request>();
    request->a = 4;
    request->b = 8;
    // 异步发送请求并返回Future或注册完成回调；执行器必须继续推进，超时仅影响本地等待，不撤销远端副作用。
    auto future = client->async_send_request(request);
    // 分发回调直到Future完成、给定chrono期限到达或中断；只适用于此处一次性main流程，不能嵌套spin已被执行器持有的同一节点。
    auto status = rclcpp::spin_until_future_complete(node, future, 2s);
    if (status == rclcpp::FutureReturnCode::SUCCESS) {
      // 只在Future已完成时读取响应；get可能抛出异常，不能把其视为无错误、无阻塞的任意时刻查询。
      auto text = std::to_string(future.get()->sum);
      RCLCPP_INFO(node->get_logger(), "sum=%s", text.c_str());
      exit_code = 0;
    } else {
      RCLCPP_ERROR(node->get_logger(), "sum response timed out or was interrupted");
    }
  }
  // 关闭当前上下文，让执行器退出；确保异步回调不再访问已销毁对象，不能替代业务层故障处理。
  rclcpp::shutdown();
  return exit_code;
}
