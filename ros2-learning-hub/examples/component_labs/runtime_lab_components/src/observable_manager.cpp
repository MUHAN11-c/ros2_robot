// 可观察管理容器：仍使用安装版本的ComponentManager与MultiThreadedExecutor。
// 与官方可执行默认不同：明确打开管理参数服务，并声明管理节点自己的gain。
// 目的是通过真实Get/Describe/SetParameters验证thread_num只读及参数作用对象；
// 三种官方容器调度验收不会用本程序冒充官方默认接口。
#include <iostream>
#include <memory>
#include <stdexcept>
#include <unistd.h>
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_components/component_manager.hpp"

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  int exit_code = 0;
  try {
    rclcpp::NodeOptions options;
    options.start_parameter_services(true).start_parameter_event_publisher(true);
    // 管理类先声明其thread_num（只读范围来自官方类），随后本程序才创建执行器。
    auto manager = std::make_shared<rclcpp_components::ComponentManager>(
      std::weak_ptr<rclcpp::Executor>(), "observable_manager", options);
    const double manager_gain = manager->declare_parameter<double>("gain", 0.5);
    const auto thread_num = manager->get_parameter("thread_num").as_int();
    auto executor = std::make_shared<rclcpp::executors::MultiThreadedExecutor>(
      rclcpp::ExecutorOptions(), static_cast<std::size_t>(thread_num));
    manager->set_executor(executor);
    executor->add_node(manager);
    std::cout << "OBSERVABLE_MANAGER_READY {\"pid\":" << ::getpid()
      << ",\"thread_num\":" << thread_num << ",\"manager_gain\":" << manager_gain
      << ",\"management_parameter_services\":true}" << std::endl;
    executor->spin();
    executor->remove_node(manager);
  } catch (const std::exception & error) {
    std::cerr << "observable manager failed: " << error.what() << std::endl;
    exit_code = 1;
  }
  if (rclcpp::ok()) {rclcpp::shutdown();}
  return exit_code;
}
