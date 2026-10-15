/*
    需求：以固定频率发布学生信息。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建发布方；
            3-2.创建定时器；
            3-3.组织并发布学生消息。
        4.调用spin函数，并传入节点对象指针；
        5.资源释放。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "base_interfaces_demo/msg/student.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class TalkerStu: public rclcpp::Node{
public:
    TalkerStu():Node("talkerstu_node_cpp"),age_(6){
        RCLCPP_INFO(this->get_logger(),"学生消息发布方创建!");
        // 3-1.创建发布方；
        publisher_ = this->create_publisher<base_interfaces_demo::msg::Student>("chatter_stu",10);
        // 3-2.创建定时器；
        timer_ = this->create_wall_timer(500ms,std::bind(&TalkerStu::on_timer,this));
    }
private:
    void on_timer(){
        // 3-3.组织并发布学生消息。
        auto stu = base_interfaces_demo::msg::Student();
        stu.name = "huluwa";
        stu.age = age_++;
        stu.height = 2.2;
        RCLCPP_INFO(this->get_logger(),"发布的消息:{%s,%d,%.2f}",stu.name.c_str(),stu.age,stu.height);
        publisher_->publish(stu);
    }
    rclcpp::Publisher<base_interfaces_demo::msg::Student>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
    int32_t age_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针。
    rclcpp::spin(std::make_shared<TalkerStu>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
