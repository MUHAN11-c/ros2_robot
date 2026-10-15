/*
    需求：订阅广播方发布的两个坐标系相对关系，并转换坐标点。
         坐标点(相机坐标系下) x=1.0 y=2.0 z=3.0，被转换到 laser 坐标系下输出。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建tf缓存对象；
            3-2.创建tf监听器；
            3-3.编写坐标点发布方；
            3-4.创建一个定时器，实现坐标的转换，并且生成速度指令并发布。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"
#include "geometry_msgs/msg/point_stamped.hpp"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class TFListener: public rclcpp::Node{
public:
    TFListener():Node("tf_listener_node_cpp"){
        // 3-1.创建tf缓存对象；
        buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
        // 3-2.创建tf监听器；
        listener_ = std::make_shared<tf2_ros::TransformListener>(*buffer_);
        // 3-3.编写坐标点发布方(相机坐标系下的坐标点)；
        point_sub_ = this->create_subscription<geometry_msgs::msg::PointStamped>("point",10,
            std::bind(&TFListener::point_callback,this,std::placeholders::_1));
        // 3-4.创建一个定时器，实现坐标系的转换；
        timer_ = this->create_wall_timer(1s,std::bind(&TFListener::on_timer,this));
    }
private:
    void on_timer(){
        //实现坐标系转换
        try
        {
            // geometry_msgs::msg::TransformStamped
            // lookupTransform(const std::string &target_frame,
            // const std::string &source_frame,
            // const tf2::TimePoint &time)
            auto ts = buffer_->lookupTransform("camera","laser",tf2::TimePointZero);
            RCLCPP_INFO(this->get_logger(),"-----------转换完成的坐标帧信息-----------");
            RCLCPP_INFO(this->get_logger(),
                "新坐标帧:父坐标系:%s,子坐标系:%s,偏移量(%.2f,%.2f,%.2f)",
                ts.header.frame_id.c_str(),// camera
                ts.child_frame_id.c_str(),// laser
                ts.transform.translation.x,
                ts.transform.translation.y,
                ts.transform.translation.z
            );
        }
        catch(const tf2::LookupException& e)
        {
            RCLCPP_INFO(this->get_logger(),"异常提示:%s",e.what());
        }
    }
    void point_callback(const geometry_msgs::msg::PointStamped::SharedPtr point){
        try
        {
            auto point_transformed = buffer_->transform(*point,"laser");
            RCLCPP_INFO(this->get_logger(),"转换前坐标:(%.2f,%.2f,%.2f)，转换后坐标:(%.2f,%.2f,%.2f)",
                point->point.x,point->point.y,point->point.z,
                point_transformed.point.x,point_transformed.point.y,point_transformed.point.z);
        }
        catch(const tf2::LookupException& e)
        {
            RCLCPP_INFO(this->get_logger(),"异常提示:%s",e.what());
        }
    }
    std::unique_ptr<tf2_ros::Buffer> buffer_;
    std::shared_ptr<tf2_ros::TransformListener> listener_;
    rclcpp::Subscription<geometry_msgs::msg::PointStamped>::SharedPtr point_sub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char const *argv[])
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<TFListener>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
