/*
    需求：Cru 服务端 —— 解析客户端提交的运动控制请求，控制机器人运动指定时长后响应结果。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "my_exer_interfaces/srv/cru.hpp"
#include "geometry_msgs/msg/twist.hpp"

using namespace std::chrono_literals;
using std::placeholders::_1;
using std::placeholders::_2;
using Cru = my_exer_interfaces::srv::Cru;

// 3.自定义节点类；
class CruServer: public rclcpp::Node{
public:
    CruServer():Node("cru_server_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"Cru 服务端创建!");
        // 3-1.创建服务端；
        server_ = this->create_service<Cru>("cru",std::bind(&CruServer::cru,this,_1,_2));
        // 速度指令发布方(控制底盘)；
        vel_pub_ = this->create_publisher<geometry_msgs::msg::Twist>("cmd_vel",10);
    }
private:
    // 3-2.回调函数处理请求并产生响应；
    void cru(const Cru::Request::SharedPtr req, const Cru::Response::SharedPtr res){
        RCLCPP_INFO(this->get_logger(),"收到请求: linear=%.2f angular=%.2f duration=%.1f",
            req->linear_x,req->angular_z,req->duration);
        geometry_msgs::msg::Twist twist;
        twist.linear.x = req->linear_x;
        twist.angular.z = req->angular_z;
        rclcpp::Rate rate(10.0);
        int count = static_cast<int>(req->duration * 10);
        for (int i = 0; i < count && rclcpp::ok(); i++) {
            vel_pub_->publish(twist);
            rate.sleep();
        }
        // 停车；
        geometry_msgs::msg::Twist stop;
        vel_pub_->publish(stop);
        res->success = true;
        res->message = "运动执行完成";
        RCLCPP_INFO(this->get_logger(),"%s",res->message.c_str());
    }
    rclcpp::Service<Cru>::SharedPtr server_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr vel_pub_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<CruServer>());
    rclcpp::shutdown();
    return 0;
}
