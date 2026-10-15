/*
    需求：Cru 客户端 —— 提交运动控制请求(命令行参数: linear_x angular_z duration)，处理响应。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "my_exer_interfaces/srv/cru.hpp"

using namespace std::chrono_literals;
using Cru = my_exer_interfaces::srv::Cru;

// 3.自定义节点类；
class CruClient: public rclcpp::Node{
public:
    CruClient():Node("cru_client_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"Cru 客户端创建!");
        // 3-1.创建客户端；
        client_ = this->create_client<Cru>("cru");
    }
    // 3-2.等待服务连接；
    bool connect_server(){
        while (!client_->wait_for_service(1s)) {
            if (!rclcpp::ok()) {
                RCLCPP_INFO(this->get_logger(),"客户端退出...");
                return false;
            }
            RCLCPP_INFO(this->get_logger(),"服务连接中，请稍候...");
        }
        return true;
    }
    // 3-3.组织并提交请求数据；
    auto send_request(double linear_x, double angular_z, double duration){
        auto request = std::make_shared<Cru::Request>();
        request->linear_x = linear_x;
        request->angular_z = angular_z;
        request->duration = duration;
        return client_->async_send_request(request);
    }
private:
    rclcpp::Client<Cru>::SharedPtr client_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    if (argc != 4) {
        RCLCPP_INFO(rclcpp::get_logger("rclcpp"),"请提交: linear_x angular_z duration");
        return 1;
    }
    auto client = std::make_shared<CruClient>();
    if (!client->connect_server()) {
        rclcpp::shutdown();
        return 0;
    }
    auto future = client->send_request(atof(argv[1]),atof(argv[2]),atof(argv[3]));
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin_until_future_complete(client,future);
    auto response = future.get();
    RCLCPP_INFO(client->get_logger(),"%s: %s",response->success ? "成功" : "失败",response->message.c_str());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
