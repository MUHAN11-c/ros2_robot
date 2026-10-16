/*
    需求：组件化 talker —— 将节点封装为组件(component)，支持动态加载到容器进程。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "rclcpp_components/register_node_macro.hpp"

using namespace std::chrono_literals;

namespace my_component {
// 2.自定义节点类；
class TalkerComponent : public rclcpp::Node {
public:
    explicit TalkerComponent(const rclcpp::NodeOptions & options)
    :Node("talker_component_node_cpp", options){
        RCLCPP_INFO(this->get_logger(), "talker组件被创建了");
        // 创建发布方；
        publisher_ = this->create_publisher<std_msgs::msg::String>("topic", 10);
        // 创建定时器；
        timer_ = this->create_wall_timer(1s, std::bind(&TalkerComponent::on_timer, this));
    }
private:
    void on_timer(){
        auto message = std_msgs::msg::String();
        message.data = "hello component!";
        publisher_->publish(message);
        RCLCPP_INFO(this->get_logger(), "发布:%s", message.data.c_str());
    }
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
};
}  // namespace my_component

// 4.注册组件；
RCLCPP_COMPONENTS_REGISTER_NODE(my_component::TalkerComponent)
