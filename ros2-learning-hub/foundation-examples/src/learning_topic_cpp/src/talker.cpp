// 【中文教学注释】 foundation-examples/src/learning_topic_cpp/src/talker.cpp
// 输入输出：输入为定时触发或收到的 String 消息；输出为带序号的消息及接收日志，序号无量纲。
// 执行顺序与边界：初始化→创建并持有节点/端点→spin 分发回调→清理；历史深度 10 不是 10 Hz，定时周期以秒或毫秒单独指定。
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
    // 创建指定模板消息类型和话题的发布端；整数10是KeepLast历史条数，不是频率。发布者必须作为成员或其他长寿命对象保留。
    publisher_ = create_publisher<std_msgs::msg::String>("telemetry", 10);
    // 创建墙钟/稳态周期定时器，chrono时长明确单位；回调由执行器调度，不随/clock仿真时钟暂停而自然暂停。
    timer_ = create_wall_timer(500ms, [this]() {
      std_msgs::msg::String message;
      message.data = "cpp sample=" + std::to_string(sequence_++);
      // 提交当前消息给发布端；日志/返回不提供订阅者业务处理确认，端到端行为还取决于QoS、网络和对端执行器。
      publisher_->publish(message);
      // 记录当前状态/错误供实验核对；printf格式必须匹配传入类型，日志不等于对端已收到数据。
      RCLCPP_INFO(get_logger(), "%s", message.data.c_str());
    });
  }
private:
  std::uint64_t sequence_{0};
  // 持久共享句柄维持ROS对象/目标的寿命；智能指针只管理生存期，不自动解决多线程数据竞争。
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  // 初始化进程 ROS 上下文、解析 ROS 参数；必须先于 Node 和通信对象创建。
  rclcpp::init(argc, argv);
  // 持有节点并进入默认单线程执行器，回调在这里得到执行；返回后才能按退出顺序关闭上下文。
  rclcpp::spin(std::make_shared<LearningTalker>());
  // 关闭当前上下文，让执行器退出；确保异步回调不再访问已销毁对象，不能替代业务层故障处理。
  rclcpp::shutdown();
  return 0;
}
