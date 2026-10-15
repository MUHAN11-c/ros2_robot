/*
    需求：读取磁盘文件中的消息并回放。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建一个回放对象；
            3-2.设置被读取的文件；
            3-3.读消息；
            3-4.关闭文件。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "rosbag2_cpp/reader.hpp"
#include "geometry_msgs/msg/twist.hpp"

// 3.自定义节点类；
class SimpleBagPlay: public rclcpp::Node{
public:
    SimpleBagPlay():Node("simple_bag_play_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"消息回放对象创建!");
        // 3-1.创建一个回放对象；
        reader_ = std::make_unique<rosbag2_cpp::Reader>();
        // 3-2.设置被读取的文件；
        reader_->open("ros2bag/demo01_bag");
        // 3-3.读消息；
        while (rclcpp::ok() && reader_->has_next()) {
            auto msg = reader_->read_next<geometry_msgs::msg::Twist>();
            // Jazzy 起 read_next 按值返回消息；Humble 返回 shared_ptr（写作 msg->）；
            RCLCPP_INFO(this->get_logger(),"读取消息:(%.2f,%.2f)",msg.linear.x,msg.angular.z);
            // 按照录制时的频率回放；
            rclcpp::sleep_for(std::chrono::milliseconds(200));
        }
        // 3-4.关闭文件。
        reader_->close();
    }
private:
    std::unique_ptr<rosbag2_cpp::Reader> reader_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<SimpleBagPlay>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
