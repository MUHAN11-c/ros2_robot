/*
    需求：编写参数服务客户端，远程操作其他节点参数(增删改查)。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建参数客户端；
            3-2.等待服务连接；
            3-3.增；
            3-4.查；
            3-5.改；
            3-6.删。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class ParamClient: public rclcpp::Node{
public:
    ParamClient():Node("param_client_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"参数客户端创建了!");
        // 3-1.创建参数客户端；
        param_client_ = std::make_shared<rclcpp::AsyncParametersClient>(this,"param_server_node_cpp");
    }
    // 3-2.等待服务连接；
    bool connect_server(){
        while (!param_client_->wait_for_service(1s)) {
            if (!rclcpp::ok()) {
                RCLCPP_INFO(this->get_logger(),"客户端退出...");
                return false;
            }
            RCLCPP_INFO(this->get_logger(),"服务连接中，请稍候...");
        }
        return true;
    }
    // 3-3.增(远程设置参数)；
    void set_param(){
        RCLCPP_INFO(this->get_logger(),"-------------增-------------");
        auto response = param_client_->set_parameters({rclcpp::Parameter("username","tom")});
        // 等待结果并打印；
        if (rclcpp::spin_until_future_complete(shared_from_this(),response) == rclcpp::FutureReturnCode::SUCCESS) {
            for (auto && re : response.get()) {
                RCLCPP_INFO(this->get_logger(),"添加参数结果：%s",re.successful ? "成功" : "失败");
            }
        } else {
            RCLCPP_INFO(this->get_logger(),"请求失败...");
        }
    }
    // 3-4.查(远程获取参数)；
    void get_param(){
        RCLCPP_INFO(this->get_logger(),"-------------查-------------");
        auto response = param_client_->get_parameters({"username"});
        if (rclcpp::spin_until_future_complete(shared_from_this(),response) == rclcpp::FutureReturnCode::SUCCESS) {
            for (auto && re : response.get()) {
                RCLCPP_INFO(this->get_logger(),"'%s' = %s",re.get_name().c_str(),re.value_to_string().c_str());
            }
        } else {
            RCLCPP_INFO(this->get_logger(),"请求失败...");
        }
    }
    // 3-5.改；
    void update_param(){
        RCLCPP_INFO(this->get_logger(),"-------------改-------------");
        auto response = param_client_->set_parameters({rclcpp::Parameter("username","jerry")});
        if (rclcpp::spin_until_future_complete(shared_from_this(),response) == rclcpp::FutureReturnCode::SUCCESS) {
            for (auto && re : response.get()) {
                RCLCPP_INFO(this->get_logger(),"修改参数结果：%s",re.successful ? "成功" : "失败");
            }
        } else {
            RCLCPP_INFO(this->get_logger(),"请求失败...");
        }
    }
    // 3-6.删(将未声明参数设置为删除状态需要服务端允许)；
    void del_param(){
        RCLCPP_INFO(this->get_logger(),"-------------删-------------");
        auto response = param_client_->set_parameters({rclcpp::Parameter("username","")});
        if (rclcpp::spin_until_future_complete(shared_from_this(),response) == rclcpp::FutureReturnCode::SUCCESS) {
            for (auto && re : response.get()) {
                RCLCPP_INFO(this->get_logger(),"删除参数结果：%s",re.successful ? "成功" : "失败");
            }
        } else {
            RCLCPP_INFO(this->get_logger(),"请求失败...");
        }
    }
private:
    rclcpp::AsyncParametersClient::SharedPtr param_client_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    auto client = std::make_shared<ParamClient>();
    if (!client->connect_server()) {
        rclcpp::shutdown();
        return 0;
    }
    client->set_param();
    client->get_param();
    client->update_param();
    client->get_param();
    // 4.调用spin函数，并传入节点对象指针；
    // rclcpp::spin(client);
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
