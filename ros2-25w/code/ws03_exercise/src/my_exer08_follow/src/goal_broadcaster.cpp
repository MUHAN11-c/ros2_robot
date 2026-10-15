/*
    需求：车辆跟随 —— 发布目标坐标系。
         周期性以发布方所在位置为原点，广播 goal→base_footprint 的相对关系，
         使 follower 节点可以计算与目标的相对位姿并跟随。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/static_transform_broadcaster.h"
#include "geometry_msgs/msg/transform_stamped.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class GoalBroadcaster: public rclcpp::Node{
public:
    GoalBroadcaster():Node("goal_broadcaster_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"目标坐标系广播方创建!");
        broadcaster_ = std::make_shared<tf2_ros::StaticTransformBroadcaster>(this);
        // 目标点通过参数设置；
        declare_parameter("goal_x",1.0);
        declare_parameter("goal_y",1.0);
        timer_ = this->create_wall_timer(1s,std::bind(&GoalBroadcaster::on_timer,this));
    }
private:
    void on_timer(){
        geometry_msgs::msg::TransformStamped ts;
        ts.header.stamp = this->now();
        ts.header.frame_id = "goal";
        ts.child_frame_id = "base_footprint";
        ts.transform.translation.x = get_parameter("goal_x").as_double();
        ts.transform.translation.y = get_parameter("goal_y").as_double();
        ts.transform.rotation.w = 1.0;
        broadcaster_->sendTransform(ts);
    }
    std::shared_ptr<tf2_ros::StaticTransformBroadcaster> broadcaster_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<GoalBroadcaster>());
    rclcpp::shutdown();
    return 0;
}
