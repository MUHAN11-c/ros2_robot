// 【中文教学注释】 foundation-examples/src/learning_service_cpp/src/server.cpp
// 输入输出：输入为 AddTwoInts 请求中的两个小整数；输出为 sum 响应和成功/失败退出码，无物理单位。
// 执行顺序与边界：先发现服务再发请求；Future 返回不等于响应已完成，等待超时不会撤销服务端已经发生的业务副作用。
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"
using Add = example_interfaces::srv::AddTwoInts;

class SumServer : public rclcpp::Node
{
public:
  SumServer() : Node("learning_sum_cpp")
  {
    // 创建AddTwoInts服务并持有服务句柄；回调填入本次Response，在响应返回前应完成短计算而不长期阻塞执行器。
    service_ = create_service<Add>("sum",
      // 持久共享句柄维持ROS对象/目标的寿命；智能指针只管理生存期，不自动解决多线程数据竞争。
      [this](std::shared_ptr<Add::Request> request,
             std::shared_ptr<Add::Response> response) {
        // 对本例小整数相加并写入Response；AddTwoInts字段为有符号64位数，生产输入还需独立处理溢出。
        response->sum = request->a + request->b;
        // 记录当前状态/错误供实验核对；printf格式必须匹配传入类型，日志不等于对端已收到数据。
        RCLCPP_INFO(get_logger(), "request handled");
      });
  }
private:
  rclcpp::Service<Add>::SharedPtr service_;
};

int main(int argc, char ** argv)
{
  // 初始化进程 ROS 上下文、解析 ROS 参数；必须先于 Node 和通信对象创建。
  rclcpp::init(argc, argv);
  // 持有节点并进入默认单线程执行器，回调在这里得到执行；返回后才能按退出顺序关闭上下文。
  rclcpp::spin(std::make_shared<SumServer>());
  // 关闭当前上下文，让执行器退出；确保异步回调不再访问已销毁对象，不能替代业务层故障处理。
  rclcpp::shutdown();
  return 0;
}
