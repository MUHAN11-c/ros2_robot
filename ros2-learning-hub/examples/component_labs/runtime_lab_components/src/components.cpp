// 原创教学组件。输入为NodeOptions、参数与专属临时目录的软件门闩；不连接设备。
// Config输出Float64教学速度(m/s)；Slow/Heartbeat输出带PID/TID和稳态纳秒的JSON事件。
// 所有构造函数建立实体后返回，不在加载服务中等待硬件；prepare_unload在本组件
// 默认互斥组中取消timer，驱动收到响应后再请求管理容器卸载。
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>
#include <sys/syscall.h>
#include <unistd.h>
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_components/register_node_macro.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"
#include "std_msgs/msg/float64.hpp"
#include "std_srvs/srv/trigger.hpp"

namespace runtime_lab_components {
namespace {
using Steady = std::chrono::steady_clock;
using Trigger = std_srvs::srv::Trigger;
std::mutex event_mutex;
std::atomic<std::uint64_t> span_sequence{0};

std::int64_t monotonic_ns() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(Steady::now().time_since_epoch()).count();
}
std::string quoted(const std::string & value) {
  // JSON字符串转义；节点名/目录不被直接拼成未转义JSON或shell命令。
  std::ostringstream out; out << '"';
  for (unsigned char c : value) {
    if (c == '"' || c == '\\') {out << '\\' << static_cast<char>(c);}
    else if (c < 0x20) {out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(c) << std::dec;}
    else {out << static_cast<char>(c);}
  }
  out << '"'; return out.str();
}
std::string number(double value) {
  std::ostringstream out; out << std::setprecision(17) << value; return out.str();
}
void event(const std::string & role, const std::string & name, const std::string & kind,
           std::uint64_t span = 0,
           const std::vector<std::pair<std::string, std::string>> & fields = {}) {
  // 同一共享库内的短锁只防止JSON行交错；绝不在锁内等待门闩或执行慢工作。
  std::lock_guard<std::mutex> guard(event_mutex);
  std::cout << "COMPONENT_LAB_EVENT {\"role\":" << quoted(role)
    << ",\"node\":" << quoted(name) << ",\"event\":" << quoted(kind)
    << ",\"span\":" << span << ",\"pid\":" << ::getpid()
    << ",\"tid\":" << ::syscall(SYS_gettid) << ",\"monotonic_ns\":" << monotonic_ns();
  for (const auto & item : fields) {std::cout << ',' << quoted(item.first) << ':' << item.second;}
  std::cout << '}' << std::endl;
}
std::filesystem::path control_directory(rclcpp::Node & node) {
  const auto text = node.declare_parameter<std::string>("control_dir", "");
  const std::filesystem::path directory(text);
  if (!directory.is_absolute() || !std::filesystem::is_directory(directory)) {
    throw std::invalid_argument("control_dir must be an existing absolute private directory");
  }
  return directory;
}
bool flag(const std::filesystem::path & directory, const char * name) {
  return std::filesystem::exists(directory / name);
}
}  // namespace

class ConfigComponent : public rclcpp::Node {
public:
  explicit ConfigComponent(const rclcpp::NodeOptions & options)
  : Node("config_component", options) {
    // 必须把容器提供的options转交Node。静态double声明会先拒绝错误类型；
    // 然后显式检查启动值有限且在[0,2]，不能只对动态更新施加约束。
    const double initial = declare_parameter<double>("gain", 1.0);
    if (!valid(initial)) {throw std::invalid_argument("gain must be finite DOUBLE within [0,2]");}
    validator_ = add_on_set_parameters_callback([](const std::vector<rclcpp::Parameter> & values) {
      rcl_interfaces::msg::SetParametersResult result; result.successful = true;
      for (const auto & value : values) {
        if (value.get_name() == "gain" &&
            (value.get_type() != rclcpp::ParameterType::PARAMETER_DOUBLE || !valid(value.as_double()))) {
          result.successful = false; result.reason = "gain must be finite DOUBLE within [0,2]"; break;
        }
      }
      // 纯校验，不改应用cache/硬件；未知参数是否已声明由Node参数框架处理。
      return result;
    });
    publisher_ = create_publisher<std_msgs::msg::Float64>("~/configured_velocity", 10);
    timer_ = create_wall_timer(std::chrono::milliseconds(100), [this]() {
      std_msgs::msg::Float64 output;
      output.data = 0.2 * get_parameter("gain").as_double();  // 0.2m/s基值×无量纲gain。
      publisher_->publish(output);  // 教学测量输出，不是底盘命令或已停车证明。
    });
    prepare_ = create_service<Trigger>("~/prepare_unload",
      [this](const std::shared_ptr<Trigger::Request>, std::shared_ptr<Trigger::Response> response) {
        timer_->cancel(); response->success = true; response->message = "timer canceled before unload";
      });
    const auto & actual = get_node_options();
    event("config", get_fully_qualified_name(), "constructed", 0,
      {{"gain", number(initial)}, {"use_global_arguments", actual.use_global_arguments() ? "true" : "false"},
       {"use_intra_process_comms", actual.use_intra_process_comms() ? "true" : "false"},
       {"allow_undeclared_parameters", actual.allow_undeclared_parameters() ? "true" : "false"},
       {"automatically_declare_parameters_from_overrides", actual.automatically_declare_parameters_from_overrides() ? "true" : "false"}});
  }
  ~ConfigComponent() override {event("config", get_fully_qualified_name(), "destroyed");}
private:
  static bool valid(double value) {return std::isfinite(value) && value >= 0.0 && value <= 2.0;}
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr validator_;
  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Service<Trigger>::SharedPtr prepare_;
};

class SlowComponent : public rclcpp::Node {
public:
  explicit SlowComponent(const rclcpp::NodeOptions & options) : Node("slow_component", options) {
    directory_ = control_directory(*this);
    const double cap = declare_parameter<double>("cap_s", 2.0);
    if (!std::isfinite(cap) || cap < 0.5 || cap > 5.0) {throw std::invalid_argument("cap_s must be finite within [0.5,5] seconds");}
    cap_s_ = cap;
    timer_ = create_wall_timer(std::chrono::milliseconds(20), [this]() {
      if (fired_ || !flag(directory_, "start_slow")) {return;}
      fired_ = true;
      const auto span = ++span_sequence;
      event("slow", get_fully_qualified_name(), "start", span);
      const auto deadline = Steady::now() + std::chrono::duration<double>(cap_s_);
      // 私有/tmp文件只是跨进程软件门闩。sleep模拟等待IO，既不是计算基准，
      // 也不能被ROS取消请求抢占；每5ms检查释放、Context与有限保护期限。
      while (!flag(directory_, "release_slow") && rclcpp::ok(get_node_base_interface()->get_context()) && Steady::now() < deadline) {
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
      }
      const bool released = flag(directory_, "release_slow");
      timer_->cancel();
      event("slow", get_fully_qualified_name(), "end", span, {{"released_by_driver", released ? "true" : "false"}});
    });
    prepare_ = create_service<Trigger>("~/prepare_unload",
      [this](const std::shared_ptr<Trigger::Request>, std::shared_ptr<Trigger::Response> response) {
        timer_->cancel(); response->success = true;
      });
    event("slow", get_fully_qualified_name(), "constructed");
  }
  ~SlowComponent() override {event("slow", get_fully_qualified_name(), "destroyed");}
private:
  std::filesystem::path directory_;
  double cap_s_{2.0};
  bool fired_{false};  // 仅在本节点默认互斥组内读写，不供外部线程直接修改。
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Service<Trigger>::SharedPtr prepare_;
};

class HeartbeatComponent : public rclcpp::Node {
public:
  explicit HeartbeatComponent(const rclcpp::NodeOptions & options) : Node("heartbeat_component", options) {
    directory_ = control_directory(*this);
    timer_ = create_wall_timer(std::chrono::milliseconds(20), [this](const rclcpp::TimerInfo & info) {
      if (!ready_recorded_) {
        ready_recorded_ = true;
        event("heartbeat", get_fully_qualified_name(), "timer_ready");
      }
      if (!flag(directory_, "heartbeat_enabled")) {return;}
      const auto span = ++span_sequence;
      event("heartbeat", get_fully_qualified_name(), "start", span,
        {{"expected_call_ns", std::to_string(info.expected_call_time.nanoseconds())},
         {"actual_call_ns", std::to_string(info.actual_call_time.nanoseconds())}});
      ++count_;
      event("heartbeat", get_fully_qualified_name(), "end", span, {{"count", std::to_string(count_)}});
    });
    prepare_ = create_service<Trigger>("~/prepare_unload",
      [this](const std::shared_ptr<Trigger::Request>, std::shared_ptr<Trigger::Response> response) {
        timer_->cancel(); response->success = true;
      });
    event("heartbeat", get_fully_qualified_name(), "constructed");
  }
  ~HeartbeatComponent() override {event("heartbeat", get_fully_qualified_name(), "destroyed");}
private:
  std::filesystem::path directory_;
  bool ready_recorded_{false};
  std::uint64_t count_{0};
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Service<Trigger>::SharedPtr prepare_;
};
}  // namespace runtime_lab_components

RCLCPP_COMPONENTS_REGISTER_NODE(runtime_lab_components::ConfigComponent)
RCLCPP_COMPONENTS_REGISTER_NODE(runtime_lab_components::SlowComponent)
RCLCPP_COMPONENTS_REGISTER_NODE(runtime_lab_components::HeartbeatComponent)
