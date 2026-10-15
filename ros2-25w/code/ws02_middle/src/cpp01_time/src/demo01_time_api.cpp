/*
    需求：演示 ROS2 时间相关 API —— Time、Duration、Rate 与运算。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.Time；
            3-2.Duration；
            3-3.Rate；
            3-4.运算(加/减/比较)。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class TimeDemo: public rclcpp::Node{
public:
    TimeDemo():Node("time_api_node_cpp"){
        // 3-1.Time；
        rclcpp::Time t1 = this->now();
        RCLCPP_INFO(this->get_logger(),"当前时刻:%.5f",t1.seconds());
        rclcpp::Time t2(1,500000000); // 1.5s
        RCLCPP_INFO(this->get_logger(),"t2:%.2f",t2.seconds());

        // 3-2.Duration；
        rclcpp::Duration d1 = 3s;
        rclcpp::Duration d2(2,0);
        RCLCPP_INFO(this->get_logger(),"d1 = %.2f s, d2 = %.2f s",d1.seconds(),d2.seconds());

        // 3-3.运算；
        auto t3 = t1 + d1;
        RCLCPP_INFO(this->get_logger(),"t1 + 3s = %.5f",t3.seconds());
        auto d3 = d1 - d2;
        RCLCPP_INFO(this->get_logger(),"d1 - d2 = %.2f s",d3.seconds());
        RCLCPP_INFO(this->get_logger(),"d1 > d2 ? %s",(d1 > d2 ? "true" : "false"));

        // 3-4.Rate(周期性休眠)；
        rclcpp::Rate rate(1.0); // 1Hz
        for (int i = 0; i < 3; i++) {
            RCLCPP_INFO(this->get_logger(),"Rate 循环 %d",i);
            rate.sleep();
        }
    }
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<TimeDemo>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
