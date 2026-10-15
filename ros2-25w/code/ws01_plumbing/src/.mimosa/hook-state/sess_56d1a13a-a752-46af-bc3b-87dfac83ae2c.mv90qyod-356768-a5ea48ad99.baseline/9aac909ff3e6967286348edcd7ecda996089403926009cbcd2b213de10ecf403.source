/*
    需求：ROS2 快速体验 —— HelloWorld(C++)。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"

// 3.自定义节点类；
class HelloWorld: public rclcpp::Node{
public:
    HelloWorld():Node("hello_world_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"Hello World!(C++)");
    }
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<HelloWorld>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
