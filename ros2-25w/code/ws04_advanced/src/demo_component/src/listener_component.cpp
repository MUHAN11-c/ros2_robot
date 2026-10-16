/*
    需求：组件化 listener —— 将订阅节点封装为组件(component)。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "rclcpp_components/register_node_macro.hpp"

using std::placeholders::_1;

namespace my_component {
// 2.自定义节点类(组件)；
class ListenerComponent : public rclcpp::Node {
public:
    explicit ListenerComponent(const rclcpp::NodeOptions & options)
    :Node("listener_component_node_cpp", options){
        // 创建订阅方；
        subscription_ = this->create_subscription<std_msgs::msg::String>("topic",10,
            std::bind(&ListenerComponent::topic_callback,this,_1));
        RCLCPP_INFO(this->get_logger(),"listener组件被创建了");
    }
private:
    // 3.处理订阅到的消息；
    void topic_callback(const std_msgs::msg::String & msg) const{
        RCLCPP_INFO(this->get_logger(),"订阅的消息：'%s'",msg.data.c_str());
    }
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
};
}  // namespace my_component

// 4.注册组件；
RCLCPP_COMPONENTS_REGISTER_NODE(my_component::ListenerComponent)
