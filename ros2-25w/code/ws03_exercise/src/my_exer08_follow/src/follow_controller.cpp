/*
    需求：车辆跟随 —— 订阅坐标变换(base_footprint→goal 逆变换)，
          根据与目标的相对位姿生成速度指令，控制车辆跟随目标点。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"
#include "geometry_msgs/msg/twist.hpp"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class FollowController: public rclcpp::Node{
public:
    FollowController():Node("follow_controller_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"车辆跟随控制方创建!");
        // 创建tf缓存与监听器；
        buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
        listener_ = std::make_shared<tf2_ros::TransformListener>(*buffer_);
        // 速度发布方；
        vel_pub_ = this->create_publisher<geometry_msgs::msg::Twist>("cmd_vel",10);
        // 定时器；
        timer_ = this->create_wall_timer(100ms,std::bind(&FollowController::on_timer,this));
    }
private:
    void on_timer(){
        try
        {
            // 查询 goal 坐标系下 base_footprint 的位置(即目标在车体系下的相对位姿)；
            auto ts = buffer_->lookupTransform("base_footprint","goal",tf2::TimePointZero);
            geometry_msgs::msg::Twist twist;
            double dx = ts.transform.translation.x;
            double dy = ts.transform.translation.y;
            double dist = std::sqrt(dx*dx + dy*dy);
            // 距离小于阈值则停车；
            if (dist > 0.2) {
                twist.linear.x = 0.3 * std::min(dist,1.0);
                twist.angular.z = 1.0 * std::atan2(dy,dx);
            }
            vel_pub_->publish(twist);
        }
        catch(const tf2::LookupException& e)
        {
            RCLCPP_INFO(this->get_logger(),"异常提示:%s",e.what());
        }
    }
    std::unique_ptr<tf2_ros::Buffer> buffer_;
    std::shared_ptr<tf2_ros::TransformListener> listener_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr vel_pub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<FollowController>());
    rclcpp::shutdown();
    return 0;
}
