// 【中文教学注释】 foundation-examples/src/learning_boot_cpp/src/hello.cpp
// 输入输出：输入是 src 中的包清单、源码和构建配置；输出先是 install 产物，随后才是节点进程的日志。
// 执行顺序与边界：先加载 Jazzy underlay，再构建并 source overlay；包名、安装目标与 console_scripts 必须一致，单个源码文件不能替代整个包。
#include <memory>
#include "rclcpp/rclcpp.hpp"

int main(int argc, char ** argv)
{
  // 初始化进程 ROS 上下文、解析 ROS 参数；必须先于 Node 和通信对象创建。
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("learning_hello_cpp");
  // 记录当前状态/错误供实验核对；printf格式必须匹配传入类型，日志不等于对端已收到数据。
  RCLCPP_INFO(node->get_logger(), "C++ node is ready");
  // 持有节点并进入默认单线程执行器，回调在这里得到执行；返回后才能按退出顺序关闭上下文。
  rclcpp::spin(node);
  // 关闭当前上下文，让执行器退出；确保异步回调不再访问已销毁对象，不能替代业务层故障处理。
  rclcpp::shutdown();
  return 0;
}
