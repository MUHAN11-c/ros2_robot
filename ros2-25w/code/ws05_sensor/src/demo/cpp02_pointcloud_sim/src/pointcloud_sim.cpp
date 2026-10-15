/*
    需求：多线激光雷达仿真 —— 周期性组织并发布 PointCloud2 消息(模拟一圈点云)。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "sensor_msgs/point_cloud2_iterator.hpp"
#include "cmath"

using namespace std::chrono_literals;

// 3.自定义节点类；
class PointCloudSim: public rclcpp::Node{
public:
    PointCloudSim():Node("pointcloud_sim_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"多线激光雷达仿真节点创建!");
        pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>("point_cloud",10);
        timer_ = this->create_wall_timer(100ms,std::bind(&PointCloudSim::on_timer,this));
    }
private:
    void on_timer(){
        // 1.组织点云基本参数(x/y/z 三个字段)；
        sensor_msgs::msg::PointCloud2 cloud;
        cloud.header.frame_id = "laser";
        cloud.height = 1;
        // 2.组织点云数据：一圈 360 个点，半径 2m；
        sensor_msgs::PointCloud2Modifier modifier(cloud);
        modifier.setPointCloud2FieldsByString(1,"xyz");
        const size_t count = 360;
        modifier.resize(count);
        sensor_msgs::PointCloud2Iterator<float> iter_x(cloud,"x");
        sensor_msgs::PointCloud2Iterator<float> iter_y(cloud,"y");
        sensor_msgs::PointCloud2Iterator<float> iter_z(cloud,"z");
        double radius = 2.0 + 0.2 * std::sin(this->now().seconds());
        for (size_t i = 0; i < count; ++i, ++iter_x, ++iter_y, ++iter_z) {
            double theta = i * M_PI / 180.0;
            *iter_x = static_cast<float>(radius * std::cos(theta));
            *iter_y = static_cast<float>(radius * std::sin(theta));
            *iter_z = 0.0f;
        }
        cloud.header.stamp = this->now();
        pub_->publish(cloud);
    }
    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<PointCloudSim>());
    rclcpp::shutdown();
    return 0;
}
