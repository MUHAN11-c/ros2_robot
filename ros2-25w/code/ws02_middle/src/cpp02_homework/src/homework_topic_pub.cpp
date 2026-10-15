/*
    需求：期中大作业 —— 话题通信(C++)：发布速度指令控制乌龟作圆周运动，支持动态调参。
*/
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"

using namespace std::chrono_literals;

class HomeworkTopicPub: public rclcpp::Node{
public:
    HomeworkTopicPub():Node("hw_pub_vel_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"发布速度指令，控制机器人作圆周运动!");
        // 1.声明并获取参数(动态调参)；
        declare_parameter("linear_x",1.0);
        declare_parameter("angular_z",1.0);
        // 2.创建速度发布方；
        pub_ = this->create_publisher<geometry_msgs::msg::Twist>("/t1/cmd_vel",10);
        // 3.创建定时器，在定时器回调函数中组织并发布速度指令。
        timer_ = this->create_wall_timer(100ms,std::bind(&HomeworkTopicPub::on_timer,this));
    }
private:
    void on_timer(){
        geometry_msgs::msg::Twist twist;
        twist.linear.x = get_parameter("linear_x").as_double();
        twist.angular.z = get_parameter("angular_z").as_double();
        pub_->publish(twist);
    }
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<HomeworkTopicPub>());
    rclcpp::shutdown();
    return 0;
}
