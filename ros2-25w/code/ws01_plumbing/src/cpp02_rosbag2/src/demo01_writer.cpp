/*
    需求：以编码形式录制 /turtle1/cmd_vel 话题消息并写入磁盘文件。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建一个录制对象；
            3-2.设置被录制的文件；
            3-3.读消息(创建订阅方)；
            3-4.写入文件。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "rosbag2_cpp/writer.hpp"
#include "geometry_msgs/msg/twist.hpp"

using std::placeholders::_1;

// 3.自定义节点类；
class SimpleBagRecorder: public rclcpp::Node{
public:
    SimpleBagRecorder():Node("simple_bag_recorder_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"消息录制对象创建!");
        // 3-1.创建一个录制对象；
        writer_ = std::make_unique<rosbag2_cpp::Writer>();
        // 3-2.设置被录制的文件；
        writer_->open("ros2bag/demo01_bag");
        // 3-3.读消息(创建订阅方)；
        sub_ = this->create_subscription<geometry_msgs::msg::Twist>("/turtle1/cmd_vel",10,
            std::bind(&SimpleBagRecorder::sub_callback,this,_1));
    }
private:
    // 3-4.写入文件；
    void sub_callback(const geometry_msgs::msg::Twist::SharedPtr msg){
        writer_->write(*msg,"/turtle1/cmd_vel",this->now());
    }
    std::unique_ptr<rosbag2_cpp::Writer> writer_;
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<SimpleBagRecorder>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
