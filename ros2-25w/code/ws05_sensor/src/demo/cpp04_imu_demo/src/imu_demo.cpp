/*
    需求：IMU 案例 —— 订阅 IMU 数据，输出四元数姿态、角速度与线加速度。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"

using std::placeholders::_1;

// 3.自定义节点类；
class ImuDemo: public rclcpp::Node{
public:
    ImuDemo():Node("imu_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"IMU 案例节点创建!");
        // 3-1.订阅 IMU 数据；
        imu_sub_ = this->create_subscription<sensor_msgs::msg::Imu>("imu",10,
            std::bind(&ImuDemo::imu_callback,this,_1));
    }
private:
    // 3-2.处理并输出 IMU 数据；
    void imu_callback(const sensor_msgs::msg::Imu::SharedPtr imu){
        RCLCPP_INFO(this->get_logger(),"---------IMU 数据---------");
        RCLCPP_INFO(this->get_logger(),"姿态四元数:(%.2f,%.2f,%.2f,%.2f)",
            imu->orientation.w,imu->orientation.x,imu->orientation.y,imu->orientation.z);
        RCLCPP_INFO(this->get_logger(),"角速度:(%.2f,%.2f,%.2f) rad/s",
            imu->angular_velocity.x,imu->angular_velocity.y,imu->angular_velocity.z);
        RCLCPP_INFO(this->get_logger(),"线加速度:(%.2f,%.2f,%.2f) m/s^2",
            imu->linear_acceleration.x,imu->linear_acceleration.y,imu->linear_acceleration.z);
    }
    rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr imu_sub_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<ImuDemo>());
    rclcpp::shutdown();
    return 0;
}
