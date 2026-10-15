/*
    需求：订阅机器人的里程计消息，生成并发布路径（Path）消息。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.订阅里程计消息；
            3-2.发布轨迹消息。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "nav_msgs/msg/path.hpp"

using std::placeholders::_1;

// 3.自定义节点类；
class Odom2Path: public rclcpp::Node{
public:
    Odom2Path():Node("odom2path_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"odom2path 节点创建!");
        // 3-1.订阅里程计消息；
        odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>("odom",10,
            std::bind(&Odom2Path::odom_callback,this,_1));
        // 3-2.发布轨迹消息。
        path_pub_ = this->create_publisher<nav_msgs::msg::Path>("path",10);
        // 初始化 path 的坐标系；
        path_.header.frame_id = "odom";
    }
private:
    void odom_callback(const nav_msgs::msg::Odometry::SharedPtr odom){
        // 将当前位姿追加到轨迹(Path 中元素为 PoseStamped，需附带坐标系与时间戳)；
        geometry_msgs::msg::PoseStamped ps;
        ps.header.frame_id = "odom";
        ps.header.stamp = odom->header.stamp;
        ps.pose = odom->pose.pose;
        path_.poses.push_back(ps);
        // 发布轨迹消息；
        path_.header.stamp = this->now();
        path_pub_->publish(path_);
    }
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
    nav_msgs::msg::Path path_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<Odom2Path>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
