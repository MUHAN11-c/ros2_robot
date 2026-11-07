// SPDX-License-Identifier: Apache-2.0
// 【中文教学注释】 examples/src/atlas_cpp/src/listener.cpp
// 输入输出：输入为定时触发或收到的 String 消息；输出为带序号的消息及接收日志，序号无量纲。
// 执行顺序与边界：初始化→创建并持有节点/端点→spin 分发回调→清理；历史深度 10 不是 10 Hz，定时周期以秒或毫秒单独指定。
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class Listener : public rclcpp::Node {
public:
  Listener() : Node("atlas_listener_cpp") {
    // 将消息类型、话题、QoS和回调绑定，保存订阅句柄；回调运行线程由执行器/回调组决定，不由lambda写法决定。
    subscription_ = create_subscription<std_msgs::msg::String>(
      // 持久共享句柄维持ROS对象/目标的寿命；智能指针只管理生存期，不自动解决多线程数据竞争。
      "chatter", 10, [this](std_msgs::msg::String::ConstSharedPtr message) {
        // 记录当前状态/错误供实验核对；printf格式必须匹配传入类型，日志不等于对端已收到数据。
        RCLCPP_INFO(get_logger(), "RECEIVED %s", message->data.c_str());
      });
  }
private:
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
};
int main(int argc, char **argv) {
  // 初始化进程 ROS 上下文、解析 ROS 参数；必须先于 Node 和通信对象创建。
  rclcpp::init(argc, argv);
  // 持有节点并进入默认单线程执行器，回调在这里得到执行；返回后才能按退出顺序关闭上下文。
  rclcpp::spin(std::make_shared<Listener>());
  // 关闭当前上下文，让执行器退出；确保异步回调不再访问已销毁对象，不能替代业务层故障处理。
  rclcpp::shutdown();
  return 0;
}
