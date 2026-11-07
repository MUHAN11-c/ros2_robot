// 【中文教学注释】 foundation-examples/src/learning_action_cpp/src/server.cpp
// 输入输出：输入为 Count 目标 target 或取消请求；输出为 current 反馈、completed 结果及终态，计数无量纲。
// 执行顺序与边界：服务端接受 1..20 且同一时刻只运行一个目标；每步约 0.5 秒。取消请求被接受与任务已取消是两个事件，共享 busy 状态按线程模型保护。
#include <chrono>
#include <cstdint>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "learning_count_interfaces/action/count.hpp"
using namespace std::chrono_literals;
using Count = learning_count_interfaces::action::Count;
using GoalHandle = rclcpp_action::ServerGoalHandle<Count>;

class CountServer : public rclcpp::Node
{
public:
  CountServer() : Node("learning_count_cpp")
  {
    // 创建动作服务端并分别注册目标接纳、取消、已接受目标处理；三个阶段构成状态机而非一次同步服务。
    server_ = rclcpp_action::create_server<Count>(this, "count",
      // 持久共享句柄维持ROS对象/目标的寿命；智能指针只管理生存期，不自动解决多线程数据竞争。
      [this](const rclcpp_action::GoalUUID &, std::shared_ptr<const Count::Goal> goal) {
        if (busy_ || goal->target == 0 || goal->target > 20) {
          // 拒绝忙碌或target超出1..20的目标；拒绝后不能继续把该目标当作已接受任务执行。
          return rclcpp_action::GoalResponse::REJECT;
        }
        // 更新本例单任务占用标记；当前默认单线程串行访问，换多线程/可重入组后需额外同步。
        busy_ = true;
        // 确认目标被接受并可进入执行；本例先置busy防止另一个目标同时占用单任务状态。
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
      },
      [](const std::shared_ptr<GoalHandle>) {
        // 同意进入取消流程；最终还必须由任务循环检查is_canceling并设置canceled终态。
        return rclcpp_action::CancelResponse::ACCEPT;
      },
      [this](const std::shared_ptr<GoalHandle> handle) {
        active_ = handle;
        completed_ = 0;
      });
    // 创建墙钟/稳态周期定时器，chrono时长明确单位；回调由执行器调度，不随/clock仿真时钟暂停而自然暂停。
    timer_ = create_wall_timer(500ms, [this]() { tick(); });
  }
private:
  void tick()
  {
    if (!active_) {return;}
    // 在短执行步之间检查取消；需要继续spin以接收取消请求，不能靠接受请求自动打断长阻塞调用。
    if (active_->is_canceling()) {
      auto result = std::make_shared<Count::Result>();
      result->completed = completed_;
      // 把目标置为CANCELED并附上已完成步数；随后释放活动目标，不能再将其succeed。
      active_->canceled(result);
      // 释放本节点持有的活动目标引用；必须先写入终态，reset本身不会替代动作协议的成功/取消通知。
      active_.reset();
      busy_ = false;
      return;
    }
    ++completed_;
    auto feedback = std::make_shared<Count::Feedback>();
    feedback->current = completed_;
    // 发布无量纲进度current，不结束任务；对象仅描述本步反馈，不表示任务最终成功。
    active_->publish_feedback(feedback);
    if (completed_ >= active_->get_goal()->target) {
      auto result = std::make_shared<Count::Result>();
      result->completed = completed_;
      // 只有计数达到目标才进入SUCCEEDED并返回Result；此后释放目标句柄并恢复接纳状态。
      active_->succeed(result);
      active_.reset();
      busy_ = false;
    }
  }
  bool busy_{false};
  std::uint32_t completed_{0};
  std::shared_ptr<GoalHandle> active_;
  rclcpp_action::Server<Count>::SharedPtr server_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  // 初始化进程 ROS 上下文、解析 ROS 参数；必须先于 Node 和通信对象创建。
  rclcpp::init(argc, argv);
  // 持有节点并进入默认单线程执行器，回调在这里得到执行；返回后才能按退出顺序关闭上下文。
  rclcpp::spin(std::make_shared<CountServer>());
  // 关闭当前上下文，让执行器退出；确保异步回调不再访问已销毁对象，不能替代业务层故障处理。
  rclcpp::shutdown();
  return 0;
}
