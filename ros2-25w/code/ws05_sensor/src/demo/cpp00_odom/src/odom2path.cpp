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
#include "cmath"
#include "limits"

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
        // 1.获取当前坐标点与轨迹中最后一个坐标点的距离数据
        //   （轨迹为空时距离取无穷大，首点直接入轨迹——即课程 BUG 修复后的写法）；
        double distance = std::numeric_limits<double>::infinity();
        if (!path_.poses.empty()) {
            double x = odom->pose.pose.position.x;
            double y = odom->pose.pose.position.y;
            double last_x = path_.poses.back().pose.position.x;
            double last_y = path_.poses.back().pose.position.y;
            distance = std::sqrt(std::pow(x - last_x, 2) + std::pow(y - last_y, 2));
        }
        // 2.距离大于 0.5 米，才将当前坐标点添加进轨迹；
        if (distance > 0.5) {
            geometry_msgs::msg::PoseStamped ps;
            ps.header.frame_id = "odom";
            ps.header.stamp = odom->header.stamp;
            ps.pose = odom->pose.pose;
            path_.poses.push_back(ps);
            RCLCPP_INFO(this->get_logger(),"轨迹点入轨(%.2f,%.2f)，累计 %zu 个点",
                ps.pose.position.x, ps.pose.position.y, path_.poses.size());
            // 3.发布轨迹消息；
            path_.header.stamp = this->now();
            path_pub_->publish(path_);
        }
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
