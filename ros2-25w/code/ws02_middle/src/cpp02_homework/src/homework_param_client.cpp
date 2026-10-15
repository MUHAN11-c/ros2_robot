/*
    需求：期中大作业 —— 参数服务(C++)：通过参数客户端修改 turtlesim 的背景色(r/g/b)。
*/
#include "rclcpp/rclcpp.hpp"
#include "rcl_interfaces/srv/set_parameters.hpp"
#include "std_srvs/srv/empty.hpp"
#include "rclcpp/parameter_value.hpp"

using namespace std::chrono_literals;

class HomeworkParamClient: public rclcpp::Node{
public:
    HomeworkParamClient():Node("hw_param_client_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"期中大作业-参数服务客户端(C++)");
        set_client_ = this->create_client<rcl_interfaces::srv::SetParameters>("/turtlesim/set_parameters");
        clear_client_ = this->create_client<std_srvs::srv::Empty>("/turtlesim/clear");
    }
    bool connect_server(){
        while (!set_client_->wait_for_service(1s)) {
            if (!rclcpp::ok()) return false;
            RCLCPP_INFO(this->get_logger(),"服务连接中，请稍候...");
        }
        return true;
    }
    void set_background(int r, int g, int b){
        auto request = std::make_shared<rcl_interfaces::srv::SetParameters::Request>();
        rcl_interfaces::msg::Parameter p;
        p.name = "background_r";
        p.value.type = rcl_interfaces::msg::ParameterType::PARAMETER_INTEGER;
        p.value.integer_value = r;
        request->parameters.push_back(p);
        p.name = "background_g";
        p.value.integer_value = g;
        request->parameters.push_back(p);
        p.name = "background_b";
        p.value.integer_value = b;
        request->parameters.push_back(p);

        // 3-2.异步发送请求，回调中处理响应；响应处理完毕后再调用 /clear 让新背景色生效；
        set_client_->async_send_request(request,
            [this](rclcpp::Client<rcl_interfaces::srv::SetParameters>::SharedFuture future){
                for (auto && re : future.get()->results) {
                    RCLCPP_INFO(this->get_logger(),"修改背景色:%s",re.successful ? "成功" : "失败");
                }
                clear_client_->async_send_request(std::make_shared<std_srvs::srv::Empty::Request>());
            });
    }
private:
    rclcpp::Client<rcl_interfaces::srv::SetParameters>::SharedPtr set_client_;
    rclcpp::Client<std_srvs::srv::Empty>::SharedPtr clear_client_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    auto client = std::make_shared<HomeworkParamClient>();
    if (!client->connect_server()) {
        rclcpp::shutdown();
        return 0;
    }
    client->set_background(100,84,105);
    // 4.调用 spin 等待响应回调处理完毕后退出；
    rclcpp::spin(client);
    rclcpp::shutdown();
    return 0;
}
