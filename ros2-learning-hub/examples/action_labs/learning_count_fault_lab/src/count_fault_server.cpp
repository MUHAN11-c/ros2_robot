// 原创 Count 故障注入服务端，仅用于无物理副作用的隔离实验。
// 输入：target为无量纲整数1..20；abort_after为计数步数，0默认关闭；step_seconds单位秒。
// 输出：反馈current、结果completed和通用Action终态；原因只写COUNT_LAB_EVENT日志，不扩展Result。
// 执行顺序：单线程接纳→定时推进/检查取消→反馈→可选abort→正常success→释放busy。
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "learning_count_interfaces/action/count.hpp"

using Count = learning_count_interfaces::action::Count;
using GoalHandle = rclcpp_action::ServerGoalHandle<Count>;

std::string uuid_hex(const rclcpp_action::GoalUUID & id)
{
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (auto byte : id) {out << std::setw(2) << static_cast<unsigned int>(byte);}
  return out.str();
}

class CountFaultServer : public rclcpp::Node
{
public:
  CountFaultServer()
  : Node("count_fault_cpp", rclcpp::NodeOptions().start_parameter_services(false))
  {
    // 参数只在启动时读取。0表示永不注入故障；禁止含糊的负数、过大步数或非有限周期。
    const auto configured = declare_parameter<std::int64_t>("abort_after", 0);
    step_seconds_ = declare_parameter<double>("step_seconds", 0.15);
    if (configured < 0 || configured > 20 || !std::isfinite(step_seconds_) ||
      step_seconds_ < 0.02 || step_seconds_ > 2.0)
    {
      throw std::invalid_argument("abort_after must be 0..20; step_seconds finite in [0.02,2]");
    }
    abort_after_ = static_cast<std::uint32_t>(configured);
    server_ = rclcpp_action::create_server<Count>(this, "count",
      [this](const rclcpp_action::GoalUUID & uuid, std::shared_ptr<const Count::Goal> goal) {
        if (goal->target < 1 || goal->target > 20) {
          emit("goal_rejected", uuid_hex(uuid), goal->target, 0, "invalid_target_range");
          return rclcpp_action::GoalResponse::REJECT;
        }
        if (busy_) {
          emit("goal_rejected", uuid_hex(uuid), goal->target, 0, "busy");
          return rclcpp_action::GoalResponse::REJECT;
        }
        busy_ = true;
        emit("goal_accepted", uuid_hex(uuid), goal->target, 0, "accepted");
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
      },
      [this](const std::shared_ptr<GoalHandle> handle) {
        emit("cancel_accepted", uuid_hex(handle->get_goal_id()), handle->get_goal()->target,
          completed_, "cancel_request_accepted_not_terminal");
        return rclcpp_action::CancelResponse::ACCEPT;
      },
      [this](const std::shared_ptr<GoalHandle> handle) {
        active_ = handle;
        completed_ = 0;
      });
    const auto period = std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::duration<double>(step_seconds_));
    timer_ = create_wall_timer(period, [this]() {tick();});
    emit("ready", "", 0, 0, "configuration_loaded");
  }

private:
  void emit(const std::string & event, const std::string & uuid, std::uint32_t target,
    std::uint32_t completed, const std::string & reason)
  {
    // 所有字符串为本例固定常量或十六进制UUID，没有任意输入字符串的JSON转义问题。
    std::ostringstream out;
    out << "{\"event\":\"" << event << "\",\"goal_uuid\":\"" << uuid <<
      "\",\"target\":" << target << ",\"completed\":" << completed <<
      ",\"reason\":\"" << reason << "\",\"abort_after\":" << abort_after_ <<
      ",\"step_seconds\":" << step_seconds_ << "}";
    RCLCPP_INFO(get_logger(), "COUNT_LAB_EVENT %s", out.str().c_str());
  }

  void finish(const std::string & state, const std::string & reason)
  {
    auto result = std::make_shared<Count::Result>();
    result->completed = completed_;
    const auto uuid = uuid_hex(active_->get_goal_id());
    const auto target = active_->get_goal()->target;
    if (state == "ABORTED") {active_->abort(result);}
    else if (state == "CANCELED") {active_->canceled(result);}
    else {active_->succeed(result);}
    emit(state, uuid, target, completed_, reason);
    active_.reset();
    busy_ = false;
    emit("busy_released", uuid, target, completed_, "slot_released_after_terminal");
  }

  void tick()
  {
    if (!active_) {return;}
    // 取消是任务在步边界观察到的状态。接受取消本身不等于已经CANCELED或硬件停车。
    if (active_->is_canceling()) {finish("CANCELED", "cancel_observed_at_step_boundary"); return;}
    ++completed_;
    auto feedback = std::make_shared<Count::Feedback>();
    feedback->current = completed_;
    active_->publish_feedback(feedback);
    emit("feedback", uuid_hex(active_->get_goal_id()), active_->get_goal()->target,
      completed_, "step_completed");
    // 第N步完成、发布反馈后再注入故障；target==N时故障优先于正常成功。
    // target<N会先成功，便于用后续短目标验证busy释放；默认N=0不会abort。
    if (abort_after_ > 0 && completed_ >= abort_after_) {
      finish("ABORTED", "configured_abort_after_step");
    } else if (completed_ >= active_->get_goal()->target) {
      finish("SUCCEEDED", "target_reached");
    }
  }

  // 当前main使用单线程执行器，回调串行访问这些字段；换成可重入并发需重新设计同步。
  bool busy_{false};
  std::uint32_t completed_{0}, abort_after_{0};
  double step_seconds_{0.15};
  std::shared_ptr<GoalHandle> active_;
  rclcpp_action::Server<Count>::SharedPtr server_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  int code = 0;
  try {rclcpp::spin(std::make_shared<CountFaultServer>());}
  catch (const std::exception & error) {
    RCLCPP_ERROR(rclcpp::get_logger("count_fault_cpp"), "startup/runtime failure: %s", error.what());
    code = 2;
  }
  if (rclcpp::ok()) {rclcpp::shutdown();}
  return code;
}
