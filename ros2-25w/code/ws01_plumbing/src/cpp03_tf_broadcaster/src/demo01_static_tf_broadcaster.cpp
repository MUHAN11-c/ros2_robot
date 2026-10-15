/*
    需求：发布两个坐标系之间的相对关系(静态坐标变换)。
         依赖命令行参数传入：x y z 欧拉角roll pitch pitch 父坐标系id 子坐标系id。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建广播对象；
            3-2.组织并发布数据。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/static_transform_broadcaster.h"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "tf2/LinearMath/Quaternion.h"

// 3.自定义节点类；
class TFStaticBroadcaster: public rclcpp::Node{
public:
    TFStaticBroadcaster(char * argv[]):Node("tf_static_broadcaster_node_cpp"){
        // 3-1.创建广播对象；
        // tf2_ros::StaticTransformBroadcaster
        broadcaster_ = std::make_shared<tf2_ros::StaticTransformBroadcaster>(this);
        // 3-2.组织并发布数据。
        pub_static_tf(argv);
    }
private:
    void pub_static_tf(char * argv[]){
        // 组织消息；
        geometry_msgs::msg::TransformStamped transform;
        transform.header.stamp = this->now();
        // 父坐标系；
        transform.header.frame_id = argv[7];
        // 子坐标系；
        transform.child_frame_id = argv[8];
        // 设置偏移量；
        transform.transform.translation.x = atof(argv[1]);
        transform.transform.translation.y = atof(argv[2]);
        transform.transform.translation.z = atof(argv[3]);
        // 根据欧拉角获取四元数；
        tf2::Quaternion qtn;
        qtn.setRPY(atof(argv[4]),atof(argv[5]),atof(argv[6]));
        transform.transform.rotation.x = qtn.getX();
        transform.transform.rotation.y = qtn.getY();
        transform.transform.rotation.z = qtn.getZ();
        transform.transform.rotation.w = qtn.getW();
        // 发布
        broadcaster_->sendTransform(transform);
    }
    std::shared_ptr<tf2_ros::StaticTransformBroadcaster> broadcaster_;
};

int main(int argc, char ** argv)
{
    // 传入参数解析：x y z roll pitch yaw father child，共8个参数+程序名+1；
    if (argc != 9) {
        RCLCPP_INFO(rclcpp::get_logger("rclcpp"),"请传入 x y z roll pitch yaw 父坐标系id 子坐标系id!");
        return 1;
    }
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<TFStaticBroadcaster>(argv));
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
