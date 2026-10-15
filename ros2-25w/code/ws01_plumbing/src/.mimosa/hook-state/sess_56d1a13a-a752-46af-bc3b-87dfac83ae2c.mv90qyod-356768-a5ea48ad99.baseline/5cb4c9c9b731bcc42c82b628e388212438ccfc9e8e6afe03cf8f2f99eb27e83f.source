/*
    需求：监听两只乌龟的坐标变换，计算 turtle2 与 turtle1 的相对位姿，
         生成速度指令控制 turtle2 朝向 turtle1(乌龟跟随)。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.声明并获取参数(父坐标系与子坐标系)；
            3-2.创建tf缓存对象；
            3-3.创建tf监听器；
            3-4.创建速度发布方；
            3-5.创建一个定时器，实现坐标的变换，并且生成速度指令并发布。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class Exer03TFListener: public rclcpp::Node{
public:
    Exer03TFListener():Node("exer03_tf_listener_node_cpp"){
        // 3-1.声明并获取参数(父坐标系与子坐标系)；
        // 声明参数服务；
        declare_parameter("father_frame","t2");
        declare_parameter("child_frame","turtle1");
        father_frame = this->get_parameter("father_frame").as_string();
        child_frame = this->get_parameter("child_frame").as_string();
        // 3-2.创建tf缓存对象；
        buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
        // 3-3.创建tf监听器；
        listener_ = std::make_shared<tf2_ros::TransformListener>(*buffer_);
        // 3-4.创建速度发布方；
        cmd_pub_ = this->create_publisher<geometry_msgs::msg::Twist>("/" + father_frame + "/cmd_vel",10);
        // 3-5.创建一个定时器，实现坐标的变换，并且生成速度指令并发布。
        timer_ = this->create_wall_timer(1s,std::bind(&Exer03TFListener::on_timer,this));
    }
private:
    void on_timer(){
        try
        {
            // 1.查询相对关系；
            auto ts = buffer_->lookupTransform(father_frame,child_frame,tf2::TimePointZero);
            // 2-1.定义速度指令；
            geometry_msgs::msg::Twist twist;
            // 2-2.计算规则：
            //     ts 中包含两个坐标系的 x、y、z 与朝向；
            //     线速度 = 系数 * 开平方(x² + y²)；
            //     角速度 = 系数 * 反正切(y / x)；
            twist.linear.x = 0.5 * sqrt(pow(ts.transform.translation.x,2) + pow(ts.transform.translation.y,2));
            twist.linear.y = 0.0;
            twist.linear.z = 0.0;
            twist.angular.x = 0.0;
            twist.angular.y = 0.0;
            twist.angular.z = 1.0 * atan2(ts.transform.translation.y,ts.transform.translation.x);
            cmd_pub_->publish(twist);
        }
        catch(const tf2::LookupException& e)
        {
            RCLCPP_INFO(this->get_logger(),"异常提示:%s",e.what());
        }
    }
    std::string father_frame;
    std::string child_frame;
    std::unique_ptr<tf2_ros::Buffer> buffer_;
    std::shared_ptr<tf2_ros::TransformListener> listener_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_pub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<Exer03TFListener>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
