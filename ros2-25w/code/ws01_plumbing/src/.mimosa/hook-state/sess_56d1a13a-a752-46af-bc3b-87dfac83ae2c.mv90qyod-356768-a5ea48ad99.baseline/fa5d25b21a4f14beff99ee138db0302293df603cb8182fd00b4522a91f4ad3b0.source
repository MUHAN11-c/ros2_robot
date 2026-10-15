/*
    需求：向 /spawn 服务发送请求，生成一只新乌龟。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建服务客户端；
            3-2.等待服务连接；
            3-3.组织并提交请求数据；
            3-4.处理响应。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "turtlesim/srv/spawn.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class Exer01Spawn: public rclcpp::Node{
public:
    Exer01Spawn():Node("exer01_spawn_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"乌龟生成客户端创建!");
        // 3-1.创建服务客户端；
        client_ = this->create_client<turtlesim::srv::Spawn>("/spawn");
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
    rclcpp::Client<turtlesim::srv::Spawn>::SharedFuture send_request(){
        auto request = std::make_shared<turtlesim::srv::Spawn::Request>();
        request->x = 3.0;
        request->y = 3.0;
        request->theta = 0.0;
        // 新乌龟名称通过参数获取，默认 t2；
        declare_parameter("turtle_name","t2");
        request->name = get_parameter("turtle_name").as_string();
        RCLCPP_INFO(this->get_logger(),"请求生成乌龟:%s",request->name.c_str());
        return client_->async_send_request(request);
    }
    // 3-4.处理响应；
    void response_callback(rclcpp::Client<turtlesim::srv::Spawn>::SharedFuture future){
        auto response = future.get();
        RCLCPP_INFO(this->get_logger(),"新乌龟名称:%s",response->name.c_str());
    }
private:
    rclcpp::Client<turtlesim::srv::Spawn>::SharedPtr client_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    auto client = std::make_shared<Exer01Spawn>();
    if (!client->connect_server()) {
        rclcpp::shutdown();
        return 0;
    }
    auto future = client->send_request();
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin_until_future_complete(client,future);
    client->response_callback(future);
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
