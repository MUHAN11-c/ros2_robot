/*
    需求：解析客户端提交的两个整数，并组织响应，将求和结果响应给客户端。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建服务端；
            3-2.编写回调函数处理请求并产生响应。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "base_interfaces_demo/srv/add_ints.hpp"

using AddInts = base_interfaces_demo::srv::AddInts;
using namespace std::placeholders;

// 3.自定义节点类；
class AddIntsServer: public rclcpp::Node{
public:
    AddIntsServer():Node("add_ints_server_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"服务端节点创建!");
        // 3-1.创建服务端；
        server_ = this->create_service<AddInts>("add_ints",std::bind(&AddIntsServer::add,this,_1,_2));
    }
private:
    // 3-2.编写回调函数处理请求并产生响应；
    void add(const AddInts::Request::SharedPtr req, const AddInts::Response::SharedPtr res){
        res->sum = req->num1 + req->num2;
        RCLCPP_INFO(this->get_logger(),"%d + %d = %d",req->num1, req->num2, res->sum);
    }
    rclcpp::Service<AddInts>::SharedPtr server_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<AddIntsServer>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
