/*
    需求：发布速度指令，控制机器人作圆周运动，并支持动态调参。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.声明并获取参数(动态调参)；
            3-2.创建速度发布方；
            3-3.创建定时器，在定时器回调函数中组织并发布速度指令。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class PubVel: public rclcpp::Node{
public:
    PubVel():Node("pub_vel_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"发布速度指令，控制机器人作圆周运动!");
        // 3-1.声明并获取参数(动态调参)；
        declare_parameter("linear_x",1.0);
        declare_parameter("angular_z",1.0);
        // 3-2.创建速度发布方；
        pub_ = this->create_publisher<geometry_msgs::msg::Twist>("cmd_vel",10);
        // 3-3.创建定时器，在定时器回调函数中组织并发布速度指令。
        timer_ = this->create_wall_timer(100ms,std::bind(&PubVel::on_timer,this));
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
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<PubVel>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
