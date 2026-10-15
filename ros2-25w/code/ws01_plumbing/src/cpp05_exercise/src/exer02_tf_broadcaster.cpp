/*
    需求：订阅乌龟位姿并转换成坐标系相对关系后发布(动态坐标变换)，乌龟名称由参数 turtle 指定。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.声明并获取参数；
            3-2.创建动态坐标变换广播器；
            3-3.创建乌龟位姿订阅方；
            3-4.回调函数中，获取乌龟位姿并生成相对关系然后发布。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "turtlesim/msg/pose.hpp"
#include "tf2/LinearMath/Quaternion.h"

using std::placeholders::_1;

// 3.自定义节点类；
class Exer02TFBroadcaster: public rclcpp::Node{
public:
    Exer02TFBroadcaster():Node("exer02_tf_broadcaster_node_cpp"){
        // 3-1.声明并获取参数；
        declare_parameter("turtle","t1");
        turtle = get_parameter("turtle").as_string();
        RCLCPP_INFO(this->get_logger(),"广播 %s 的坐标变换!",turtle.c_str());
        // 3-2.创建动态坐标变换广播器；
        broadcaster_ = std::make_shared<tf2_ros::TransformBroadcaster>(this);
        // 3-3.创建乌龟位姿订阅方；
        pose_sub_ = this->create_subscription<turtlesim::msg::Pose>(
            "/" + turtle + "/pose",10,
            std::bind(&Exer02TFBroadcaster::do_pose,this,_1));
    }
private:
    // 3-4.回调函数中，获取乌龟位姿并生成相对关系然后发布；
    void do_pose(const turtlesim::msg::Pose & pose){
        geometry_msgs::msg::TransformStamped ts;
        ts.header.stamp = this->now();
        ts.header.frame_id = "world";
        ts.child_frame_id = turtle;
        ts.transform.translation.x = pose.x;
        ts.transform.translation.y = pose.y;
        ts.transform.translation.z = 0.0;
        tf2::Quaternion qtn;
        qtn.setRPY(0.0,0.0,pose.theta);
        ts.transform.rotation.x = qtn.getX();
        ts.transform.rotation.y = qtn.getY();
        ts.transform.rotation.z = qtn.getZ();
        ts.transform.rotation.w = qtn.getW();
        broadcaster_->sendTransform(ts);
    }
    std::string turtle;
    std::shared_ptr<tf2_ros::TransformBroadcaster> broadcaster_;
    rclcpp::Subscription<turtlesim::msg::Pose>::SharedPtr pose_sub_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<Exer02TFBroadcaster>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
