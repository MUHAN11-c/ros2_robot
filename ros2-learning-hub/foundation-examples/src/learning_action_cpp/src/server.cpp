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
    server_ = rclcpp_action::create_server<Count>(this, "count",
      [this](const rclcpp_action::GoalUUID &, std::shared_ptr<const Count::Goal> goal) {
        if (busy_ || goal->target == 0 || goal->target > 20) {
          return rclcpp_action::GoalResponse::REJECT;
        }
        busy_ = true;
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
      },
      [](const std::shared_ptr<GoalHandle>) {
        return rclcpp_action::CancelResponse::ACCEPT;
      },
      [this](const std::shared_ptr<GoalHandle> handle) {
        active_ = handle;
        completed_ = 0;
      });
    timer_ = create_wall_timer(500ms, [this]() { tick(); });
  }
private:
  void tick()
  {
    if (!active_) {return;}
    if (active_->is_canceling()) {
      auto result = std::make_shared<Count::Result>();
      result->completed = completed_;
      active_->canceled(result);
      active_.reset();
      busy_ = false;
      return;
    }
    ++completed_;
    auto feedback = std::make_shared<Count::Feedback>();
    feedback->current = completed_;
    active_->publish_feedback(feedback);
    if (completed_ >= active_->get_goal()->target) {
      auto result = std::make_shared<Count::Result>();
      result->completed = completed_;
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
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CountServer>());
  rclcpp::shutdown();
  return 0;
}
