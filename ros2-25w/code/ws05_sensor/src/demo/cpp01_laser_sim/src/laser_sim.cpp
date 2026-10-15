/*
    需求：单线激光雷达仿真 —— 周期性组织并发布 LaserScan 消息(模拟正前方障碍物)。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.组织点云基本参数；
            3-2.创建定时器；
            3-3.定时器回调中，设置扫描点参数并发布。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class LaserSim: public rclcpp::Node{
public:
    LaserSim():Node("laser_sim_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"单线激光雷达仿真节点创建!");
        // 3-1.组织点云基本参数；
        scan_.header.frame_id = "laser";
        scan_.angle_min = -M_PI;
        scan_.angle_max = M_PI;
        scan_.angle_increment = M_PI / 180.0; // 1度一个点；
        scan_.time_increment = 0.0;
        scan_.scan_time = 0.1;
        scan_.range_min = 0.15;
        scan_.range_max = 12.0;
        // 3-2.创建定时器；
        timer_ = this->create_wall_timer(100ms,std::bind(&LaserSim::on_timer,this));
        // 3-3.发布方；
        pub_ = this->create_publisher<sensor_msgs::msg::LaserScan>("scan",10);
    }
private:
    // 3-4.设置扫描点参数并发布；
    void on_timer(){
        size_t count = (scan_.angle_max - scan_.angle_min) / scan_.angle_increment;
        scan_.ranges.assign(count,INFINITY);
        scan_.intensities.assign(count,0.0);
        // 模拟正前方 2m 处的障碍物(角度 0 附近)；
        double distance = 2.0 + 0.2 * std::sin(this->now().seconds());
        for (size_t i = 0; i < count; ++i) {
            double angle = scan_.angle_min + i * scan_.angle_increment;
            if (std::abs(angle) < 0.05) {
                scan_.ranges[i] = distance;
                scan_.intensities[i] = 100.0;
            }
        }
        scan_.header.stamp = this->now();
        pub_->publish(scan_);
    }
    rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
    sensor_msgs::msg::LaserScan scan_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<LaserSim>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
