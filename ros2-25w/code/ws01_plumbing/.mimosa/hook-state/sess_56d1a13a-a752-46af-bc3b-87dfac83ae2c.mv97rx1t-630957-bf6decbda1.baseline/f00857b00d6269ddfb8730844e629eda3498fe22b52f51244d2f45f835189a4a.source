/*
    需求：以某个固定频率发送文本"hello world!"，文本后缀编号，每发送一条消息，编号递增1。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建消息发布方；
            3-2.创建定时器；
            3-3.组织并发布消息。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class Talker: public rclcpp::Node{
public:
    Talker():Node("talker_node_cpp"),count_(0){
        RCLCPP_INFO(this->get_logger(),"发布节点创建!");
        // 3-1.创建消息发布方；
        publisher_ = this->create_publisher<std_msgs::msg::String>("chatter",10);
        // 3-2.创建定时器；
        timer_ = this->create_wall_timer(1s,std::bind(&Talker::on_timer,this));
    }
private:
    void on_timer(){
        // 3-3.组织并发布消息。
        auto message = std_msgs::msg::String();
        message.data = "hello world!" + std::to_string(count_++);
        RCLCPP_INFO(this->get_logger(),"发布方发布的消息:%s",message.data.c_str());
        publisher_->publish(message);
    }
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
    size_t count_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针。
    rclcpp::spin(std::make_shared<Talker>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
