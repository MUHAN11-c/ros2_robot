// 覆盖层(overlay)演示：同名包 demo01_hello_world 的「修改版」
// 后 source 的工作空间会覆盖先 source 的工作空间中的同名包
#include "rclcpp/rclcpp.hpp"

int main(int argc, char ** argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("hello_world_node_cpp");
    RCLCPP_INFO(node->get_logger(), "Hello from OVERLAY workspace!（覆盖层版本）");
    rclcpp::shutdown();
    return 0;
}
