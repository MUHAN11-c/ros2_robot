/*
    需求：GNSS 案例 —— 订阅 NavSatFix(经纬度) 数据，以首个坐标为原点，
          组织成 Path 并发布(便于在 rviz2 中查看轨迹)。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.Path 数据组织之标头；
            3-2.Path 数据组织之坐标系；
            3-3.Path 数据组织之原点确定；
            3-4.Path 数据组织之经纬度。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/nav_sat_fix.hpp"
#include "nav_msgs/msg/path.hpp"
#include "cmath"

using std::placeholders::_1;

// 3.自定义节点类；
class Gnss2Path: public rclcpp::Node{
public:
    Gnss2Path():Node("gnss_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"GNSS 案例节点创建!");
        // 3-1.订阅 GNSS 数据；
        gnss_sub_ = this->create_subscription<sensor_msgs::msg::NavSatFix>("fix",10,
            std::bind(&Gnss2Path::gnss_callback,this,_1));
        // 3-2.发布轨迹；
        path_pub_ = this->create_publisher<nav_msgs::msg::Path>("gnss_path",10);
        path_.header.frame_id = "map";
        has_origin_ = false;
    }
private:
    void gnss_callback(const sensor_msgs::msg::NavSatFix::SharedPtr fix){
        // 3-3.原点确定(以首个有效坐标为原点)；
        if (!has_origin_) {
            if (fix->status.status < 0 || std::abs(fix->latitude) < 1e-9) {
                return;
            }
            origin_lat_ = fix->latitude;
            origin_lon_ = fix->longitude;
            has_origin_ = true;
            RCLCPP_INFO(this->get_logger(),"定位原点:(%.6f,%.6f)",origin_lat_,origin_lon_);
        }
        // 3-4.经纬度 -> 平面坐标(米)，等距圆柱近似；
        double dlat = fix->latitude - origin_lat_;
        double dlon = fix->longitude - origin_lon_;
        double x = dlon * 111319.49079327358 * std::cos(origin_lat_ * M_PI / 180.0);
        double y = dlat * 111319.49079327358;

        geometry_msgs::msg::PoseStamped pose;
        pose.header.frame_id = "map";
        pose.header.stamp = this->now();
        pose.pose.position.x = x;
        pose.pose.position.y = y;
        path_.poses.push_back(pose);
        path_.header.stamp = this->now();
        path_pub_->publish(path_);
    }
    rclcpp::Subscription<sensor_msgs::msg::NavSatFix>::SharedPtr gnss_sub_;
    rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
    nav_msgs::msg::Path path_;
    bool has_origin_;
    double origin_lat_ = 0.0;
    double origin_lon_ = 0.0;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<Gnss2Path>());
    rclcpp::shutdown();
    return 0;
}
