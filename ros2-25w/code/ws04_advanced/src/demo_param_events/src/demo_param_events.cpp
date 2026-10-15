/*
    需求：参数事件 —— 监听节点参数的变化事件并输出。
    说明：本节点同时演示参数的声明与修改，配合另一个终端
          ros2 param set /param_events_node_cpp width 2.0 触发事件回调。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class ParamEvents: public rclcpp::Node{
public:
    ParamEvents():Node("param_events_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"参数事件节点创建!");
        // 3-1.声明参数；
        declare_parameter("width",1.0);
        declare_parameter("height",2.0);
        // 3-2.添加参数事件回调(on_set_parameters_event)；
        auto callback = [this](const std::vector<rclcpp::Parameter> & params)
            -> rcl_interfaces::msg::SetParametersResult
        {
            rcl_interfaces::msg::SetParametersResult result;
            result.successful = true;
            for (const auto & param : params) {
                RCLCPP_INFO(this->get_logger(),"监听到参数修改事件: %s -> %s",
                    param.get_name().c_str(),param.value_to_string().c_str());
            }
            return result;
        };
        on_set_parameters_callback_handle_ = this->add_on_set_parameters_callback(callback);
        // 3-3.监听其他节点参数事件(通过参数事件话题)；
        param_sub_ = this->create_subscription<rcl_interfaces::msg::ParameterEvent>(
            "/parameter_events",10,
            [this](const rcl_interfaces::msg::ParameterEvent::SharedPtr event){
                RCLCPP_INFO(this->get_logger(),"收到参数事件，来自节点:%s",event->node.c_str());
            });
        // 3-4.修改参数以触发事件；
        timer_ = this->create_wall_timer(3s,[this](){
            this->set_parameter(rclcpp::Parameter("width",this->get_parameter("width").as_double() + 1.0));
        });
    }
private:
    rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr on_set_parameters_callback_handle_;
    rclcpp::Subscription<rcl_interfaces::msg::ParameterEvent>::SharedPtr param_sub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<ParamEvents>());
    rclcpp::shutdown();
    return 0;
}
