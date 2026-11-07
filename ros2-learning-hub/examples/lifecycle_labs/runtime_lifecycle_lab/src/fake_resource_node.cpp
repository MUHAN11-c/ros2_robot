// 原创LifecycleNode：输入为标准转换请求和故障注入参数；输出为资源快照、回调JSON
// 及两条UInt64诊断序号。序号/资源数/配置代数均无量纲，时间为steady-clock纳秒。
// 假资源只是16字节内存，不模拟真实相机/串口，也不把状态切换当设备停车。
// 单线程执行器串行处理timer、参数与转换服务；所有回调有限且不等待外部硬件。
#include <chrono>
#include <cstdint>
#include <functional>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#include <unistd.h>
#include "rclcpp/rclcpp.hpp"
#include "rclcpp/create_publisher.hpp"
#include "rclcpp_lifecycle/lifecycle_node.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"
#include "std_msgs/msg/u_int64.hpp"
#include "std_srvs/srv/trigger.hpp"

namespace lifecycle_lab {
using Return = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;
using State = rclcpp_lifecycle::State;
using Counter = std_msgs::msg::UInt64;
using Trigger = std_srvs::srv::Trigger;

std::string quoted(const std::string & text) {
  std::ostringstream out; out << '"';
  for (unsigned char c : text) {
    if (c == '\\' || c == '"') {out << '\\' << static_cast<char>(c);}
    else if (c == '\n') {out << "\\n";}
    else {out << static_cast<char>(c);}
  }
  out << '"'; return out.str();
}

class FakeResourceNode : public rclcpp_lifecycle::LifecycleNode {
public:
  FakeResourceNode() : LifecycleNode("fake_resource") {
    // 每个stage最多注入一次；success不会消耗注入机会，允许先建立旧配置再测试失败。
    declare_parameter<std::string>("configure_fault", "success");
    declare_parameter<std::string>("activate_fault", "success");
    declare_parameter<std::string>("deactivate_fault", "success");
    declare_parameter<std::string>("error_result", "success");
    for (const auto & name : {"configure_fault", "activate_fault", "deactivate_fault", "error_result"}) {
      if (!valid_mode(name, get_parameter(name).as_string())) {throw std::invalid_argument("invalid fault mode");}
    }
    validator_ = add_on_set_parameters_callback([](const std::vector<rclcpp::Parameter> & values) {
      rcl_interfaces::msg::SetParametersResult result; result.successful = true;
      for (const auto & value : values) {
        if ((value.get_name() == "configure_fault" || value.get_name() == "activate_fault" ||
             value.get_name() == "deactivate_fault" || value.get_name() == "error_result") &&
            (value.get_type() != rclcpp::ParameterType::PARAMETER_STRING ||
             !valid_mode(value.get_name(), value.as_string()))) {
          result.successful = false; result.reason = "invalid STRING fault mode"; break;
        }
      }
      return result;  // 纯校验，不在这里修改资源或故障计数。
    });
    // 明确选择普通rclcpp::Publisher，而非LifecycleNode成员工厂返回的生命周期发布者。
    ordinary_ = rclcpp::create_publisher<Counter>(*this, "~/ordinary_ticks", rclcpp::QoS(10));
    managed_ = create_publisher<Counter>("~/managed_ticks", rclcpp::QoS(10));
    timer_ = create_wall_timer(std::chrono::milliseconds(50), [this]() {
      ++ticks_;
      Counter message; message.data = ticks_;
      ordinary_->publish(message);
      ++managed_attempts_;
      // 故意在所有状态调用publish：未激活时由LifecyclePublisher自己拒绝发送。
      // 普通timer仍运行，与假资源是否采样、生命周期消息是否发送分别计数。
      managed_->publish(message);
      if (resource_active_) {++resource_work_;}
    });
    snapshot_ = create_service<Trigger>("~/snapshot",
      [this](const std::shared_ptr<Trigger::Request>, std::shared_ptr<Trigger::Response> response) {
        response->success = true; response->message = snapshot_json(true);
      });
    emit("constructed", "constructor", "none");
  }

  ~FakeResourceNode() override {
    timer_->cancel();
    resource_active_ = false;
    managed_->on_deactivate();
    pending_.reset(); resource_.reset();
    emit("destroyed", "destructor", "none");
  }

private:
  struct FakeHandle {
    std::uint64_t id;
    std::vector<std::uint8_t> bytes = std::vector<std::uint8_t>(16);
    std::function<void(std::uint64_t)> on_release;
    FakeHandle(std::uint64_t value, std::function<void(std::uint64_t)> callback)
    : id(value), on_release(std::move(callback)) {}
    ~FakeHandle() noexcept {
      // 所有权由unique_ptr释放；计数先更新，诊断日志异常不从析构函数逃逸。
      try {on_release(id);} catch (...) {}
    }
  };

  static bool valid_mode(const std::string & name, const std::string & mode) {
    if (name == "error_result") {return mode == "success" || mode == "failure" || mode == "error" || mode == "throw";}
    return mode == "success" || mode == "failure_once" || mode == "error_once" || mode == "throw_once";
  }

  std::unique_ptr<FakeHandle> candidate() {
    const auto id = ++next_resource_id_;
    auto value = std::make_unique<FakeHandle>(id, [this](std::uint64_t released_id) {
      ++released_; --live_;
      emit("resource_released", "resource", "none", released_id);
    });
    ++allocated_; ++live_;
    emit("resource_acquired", "resource", "none", id);
    return value;
  }

  std::string take_fault(const std::string & stage) {
    const auto mode = get_parameter(stage + "_fault").as_string();
    if (mode == "success" || consumed_[stage]) {return "success";}
    consumed_[stage] = true;
    return mode;
  }

  Return finish(const std::string & callback, Return result) {
    const auto label = result == Return::SUCCESS ? "SUCCESS" : result == Return::FAILURE ? "FAILURE" : "ERROR";
    emit("callback_return", callback, label);
    return result;
  }

  Return fault_return(const std::string & callback, const std::string & mode) {
    if (mode == "throw_once") {
      emit("callback_throw", callback, "THROW_STD_RUNTIME_ERROR");
      throw std::runtime_error("intentional lifecycle software fault in " + callback);
    }
    return finish(callback, mode == "failure_once" ? Return::FAILURE : Return::ERROR);
  }

  Return on_configure(const State & previous) override {
    ++configure_calls_; emit("callback_enter", "configure", "none", 0, previous.id());
    auto temporary = candidate();
    const auto mode = take_fault("configure");
    if (mode == "failure_once") {
      // 事务失败：候选先释放，旧committed_version不动；不提交半成品。
      temporary.reset(); return finish("configure", Return::FAILURE);
    }
    if (mode != "success") {
      // ERROR/异常示范把部分资源显式交给on_error清理，便于实测其释放责任。
      pending_ = std::move(temporary); return fault_return("configure", mode);
    }
    resource_ = std::move(temporary);
    ++committed_version_;
    resource_active_ = false;
    return finish("configure", Return::SUCCESS);
  }

  Return on_activate(const State & previous) override {
    ++activate_calls_; emit("callback_enter", "activate", "none", 0, previous.id());
    if (!resource_) {return finish("activate", Return::ERROR);}
    const auto mode = take_fault("activate");
    if (mode != "success") {return fault_return("activate", mode);}
    // 覆写activate时调用基类，才会激活已注册的LifecyclePublisher。
    LifecycleNode::on_activate(previous);
    resource_active_ = true;
    return finish("activate", Return::SUCCESS);
  }

  Return on_deactivate(const State & previous) override {
    ++deactivate_calls_; emit("callback_enter", "deactivate", "none", 0, previous.id());
    const auto mode = take_fault("deactivate");
    if (mode != "success") {return fault_return("deactivate", mode);}
    LifecycleNode::on_deactivate(previous);
    resource_active_ = false;
    return finish("deactivate", Return::SUCCESS);
  }

  Return on_cleanup(const State & previous) override {
    ++cleanup_calls_; emit("callback_enter", "cleanup", "none", 0, previous.id());
    stop_and_release();
    return finish("cleanup", Return::SUCCESS);
  }

  Return on_shutdown(const State & previous) override {
    ++shutdown_calls_; emit("callback_enter", "shutdown", "none", 0, previous.id());
    stop_and_release();
    // 普通诊断timer按本实验合同继续运行，直到进程退出；finalized不等于销毁。
    return finish("shutdown", Return::SUCCESS);
  }

  Return on_error(const State & previous) override {
    ++error_calls_; emit("callback_enter", "error", "none", 0, previous.id());
    stop_and_release();
    const auto mode = get_parameter("error_result").as_string();
    if (mode == "throw") {
      emit("callback_throw", "error", "THROW_STD_RUNTIME_ERROR");
      throw std::runtime_error("intentional std::exception in on_error after cleanup");
    }
    return finish("error", mode == "success" ? Return::SUCCESS : mode == "failure" ? Return::FAILURE : Return::ERROR);
  }

  void stop_and_release() {
    // 生命周期状态不会代替资源释放；错误路径也显式撤销生命周期发布者激活状态。
    resource_active_ = false; managed_->on_deactivate();
    pending_.reset(); resource_.reset();
  }

  std::string snapshot_json(bool include_matches = false) const {
    std::ostringstream out;
    out << "{\"state_id\":" << static_cast<int>(get_current_state().id())
      << ",\"state_label\":" << quoted(get_current_state().label())
      << ",\"resource_live\":" << live_ << ",\"allocated\":" << allocated_ << ",\"released\":" << released_
      << ",\"resource_id\":" << (resource_ ? resource_->id : 0)
      << ",\"pending_id\":" << (pending_ ? pending_->id : 0)
      << ",\"committed_version\":" << committed_version_
      << ",\"resource_active\":" << (resource_active_ ? "true" : "false")
      << ",\"publisher_active\":" << (managed_->is_activated() ? "true" : "false")
      << ",\"timer_ticks\":" << ticks_ << ",\"managed_attempts\":" << managed_attempts_
      << ",\"resource_work\":" << resource_work_ << ",\"configure_calls\":" << configure_calls_
      << ",\"activate_calls\":" << activate_calls_ << ",\"deactivate_calls\":" << deactivate_calls_
      << ",\"cleanup_calls\":" << cleanup_calls_ << ",\"shutdown_calls\":" << shutdown_calls_
      << ",\"error_calls\":" << error_calls_;
    if (include_matches) {
      out << ",\"ordinary_subscribers\":" << ordinary_->get_subscription_count()
        << ",\"managed_subscribers\":" << managed_->get_subscription_count();
    }
    out << '}'; return out.str();
  }

  void emit(const std::string & kind, const std::string & callback, const std::string & result,
            std::uint64_t resource_id = 0, unsigned int previous_state = 0) const {
    const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::steady_clock::now().time_since_epoch()).count();
    std::ostringstream out;
    out << "LIFECYCLE_LAB_EVENT {\"event\":" << quoted(kind) << ",\"callback\":" << quoted(callback)
      << ",\"callback_result\":" << quoted(result) << ",\"pid\":" << ::getpid()
      << ",\"monotonic_ns\":" << ns << ",\"resource_event_id\":" << resource_id
      << ",\"previous_state_id\":" << previous_state << ",\"snapshot\":" << snapshot_json() << '}';
    std::cout << out.str() << std::endl;
  }

  // 计数先声明、unique_ptr后声明，析构时资源回调仍可访问有效计数；析构函数另显式释放。
  std::uint64_t next_resource_id_{0}, allocated_{0}, released_{0}, live_{0}, committed_version_{0};
  std::uint64_t ticks_{0}, managed_attempts_{0}, resource_work_{0};
  std::uint64_t configure_calls_{0}, activate_calls_{0}, deactivate_calls_{0}, cleanup_calls_{0}, shutdown_calls_{0}, error_calls_{0};
  bool resource_active_{false};
  std::unordered_map<std::string, bool> consumed_;
  std::unique_ptr<FakeHandle> resource_, pending_;
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr validator_;
  rclcpp::Publisher<Counter>::SharedPtr ordinary_;
  rclcpp_lifecycle::LifecyclePublisher<Counter>::SharedPtr managed_;
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Service<Trigger>::SharedPtr snapshot_;
};
}  // namespace lifecycle_lab

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  int code = 0;
  try {
    auto node = std::make_shared<lifecycle_lab::FakeResourceNode>();
    rclcpp::executors::SingleThreadedExecutor executor;
    executor.add_node(node->get_node_base_interface());
    executor.spin();
    executor.remove_node(node->get_node_base_interface());
  } catch (const std::exception & error) {
    std::cerr << "fake_resource_node failed: " << error.what() << std::endl; code = 1;
  }
  if (rclcpp::ok()) {rclcpp::shutdown();}
  return code;
}
