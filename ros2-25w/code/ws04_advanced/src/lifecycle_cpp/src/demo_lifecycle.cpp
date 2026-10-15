/*
    需求：生命周期节点 —— 节点在配置/激活/待激活/清理/关闭各状态切换时输出日志。
    说明：可通过 ros2 lifecycle set <node> configure/activate/... 驱动状态机。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/lifecycle_node.hpp"
#include "rclcpp_lifecycle/lifecycle_node_impl.hpp"
#include "rclcpp_lifecycle/state.hpp"

// 3.自定义节点类；
class MyNode: public rclcpp_lifecycle::LifecycleNode{
public:
    MyNode():LifecycleNode("my_lifecycle_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"生命周期节点创建!");
    }

    rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn on_configure(const rclcpp_lifecycle::State &)
    {
        //日志输出
        RCLCPP_INFO(this->get_logger(),"节点配置......");
        return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
    }

    rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn on_activate(const rclcpp_lifecycle::State &)
    {
        //日志输出
        RCLCPP_INFO(this->get_logger(),"节点激活------------");
        return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
    }

    rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn on_deactivate(const rclcpp_lifecycle::State &)
    {
        //日志输出
        RCLCPP_INFO(this->get_logger(),"节点待激活+++++++++++++++++++++");
        return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
    }

    rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn on_cleanup(const rclcpp_lifecycle::State &)
    {
        //日志输出
        RCLCPP_INFO(this->get_logger(),"节点清空配置+++++++++++++++++++++");
        return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
    }

    rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn on_shutdown(const rclcpp_lifecycle::State &)
    {
        //日志输出
        RCLCPP_INFO(this->get_logger(),"节点销毁+++++++++++++++++++++");
        return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
    }
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<MyNode>()->get_node_base_interface());
    rclcpp::shutdown();
    return 0;
}
