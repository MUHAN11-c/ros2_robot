/*
    需求：坐标点变换监听 —— 订阅 turtle1 坐标系下的坐标点，利用 tf 变换到 world 坐标系并输出。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建 tf 缓存对象与监听器；
            3-2.创建坐标点订阅方；
            3-3.回调中将坐标点从 turtle1 变换到 world 并输出。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/point_stamped.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

using std::placeholders::_1;

// 3.自定义节点类；
class PointListener : public rclcpp::Node {
public:
    PointListener() : Node("point_listener_node_cpp") {
        // 3-1.创建 tf 缓存对象与监听器；
        buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
        listener_ = std::make_shared<tf2_ros::TransformListener>(*buffer_);
        // 3-2.创建坐标点订阅方；
        sub_ = this->create_subscription<geometry_msgs::msg::PointStamped>(
            "/turtle1/point", 10, std::bind(&PointListener::on_point, this, _1));
    }
private:
    // 3-3.回调中将坐标点从 turtle1 变换到 world；
    void on_point(const geometry_msgs::msg::PointStamped::SharedPtr point) {
        try {
            geometry_msgs::msg::PointStamped out;
            tf2::doTransform(*point, out,
                buffer_->lookupTransform("world", point->header.frame_id, tf2::TimePointZero));
            RCLCPP_INFO(this->get_logger(),
                "坐标点(%.2f,%.2f) 变换到 world 系下: (%.2f,%.2f)",
                point->point.x, point->point.y,
                out.point.x, out.point.y);
        } catch (const tf2::TransformException & e) {
            RCLCPP_INFO(this->get_logger(), "变换异常:%s", e.what());
        }
    }
    std::unique_ptr<tf2_ros::Buffer> buffer_;
    std::shared_ptr<tf2_ros::TransformListener> listener_;
    rclcpp::Subscription<geometry_msgs::msg::PointStamped>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<PointListener>());
    rclcpp::shutdown();
    return 0;
}
