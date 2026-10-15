/*
    需求：订阅机器人速度指令并输出(话题订阅)。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"

using std::placeholders::_1;

// 3.自定义节点类；
class SubVel: public rclcpp::Node{
public:
    SubVel():Node("sub_vel_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"速度订阅方创建!");
        // 3-1.创建订阅方；
        sub_ = this->create_subscription<geometry_msgs::msg::Twist>("cmd_vel",10,
            std::bind(&SubVel::sub_callback,this,_1));
    }
private:
    // 3-2.处理订阅到的速度指令；
    void sub_callback(const geometry_msgs::msg::Twist::SharedPtr msg){
        RCLCPP_INFO(this->get_logger(),"订阅的速度: linear=%.2f, angular=%.2f",msg->linear.x,msg->angular.z);
    }
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<SubVel>());
    rclcpp::shutdown();
    return 0;
}
