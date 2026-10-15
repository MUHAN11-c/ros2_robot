/*
    需求：订阅学生信息并输出。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建订阅方；
            3-2.解析并输出学生消息。
        4.调用spin函数，并传入节点对象指针；
        5.资源释放。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "base_interfaces_demo/msg/student.hpp"

// 3.自定义节点类；
class ListenerStu: public rclcpp::Node{
public:
    ListenerStu():Node("listenerstu_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"学生消息订阅方创建!");
        // 3-1.创建订阅方；
        subscription_ = this->create_subscription<base_interfaces_demo::msg::Student>("chatter_stu",10,
            std::bind(&ListenerStu::topic_callback,this,std::placeholders::_1));
    }
private:
    // 3-2.解析并输出学生消息。
    void topic_callback(const base_interfaces_demo::msg::Student & stu) const{
        RCLCPP_INFO(this->get_logger(),"订阅的消息:{%s,%d,%.2f}",stu.name.c_str(),stu.age,stu.height);
    }
    rclcpp::Subscription<base_interfaces_demo::msg::Student>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针。
    rclcpp::spin(std::make_shared<ListenerStu>());
    // 5.资源释放；
    rclcpp::shutdown();
    return 0;
}
