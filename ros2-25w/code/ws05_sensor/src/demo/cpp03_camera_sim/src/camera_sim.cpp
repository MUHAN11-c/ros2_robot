/*
    需求：单目相机仿真 —— 周期性组织并发布 Image 消息(模拟黑白条纹图)。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/image.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类；
class CameraSim: public rclcpp::Node{
public:
    CameraSim():Node("camera_sim_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"单目相机仿真节点创建!");
        pub_ = this->create_publisher<sensor_msgs::msg::Image>("image_raw",10);
        timer_ = this->create_wall_timer(100ms,std::bind(&CameraSim::on_timer,this));
    }
private:
    void on_timer(){
        // 1.组织图片基本参数；
        sensor_msgs::msg::Image image;
        image.header.frame_id = "camera";
        image.height = 240;
        image.width = 320;
        image.encoding = "mono8";
        image.is_bigendian = 0;
        image.step = image.width;
        // 2.组织图片数据：黑白条纹；
        image.data.resize(image.height * image.width);
        static bool flip = false;
        for (uint32_t r = 0; r < image.height; ++r) {
            for (uint32_t c = 0; c < image.width; ++c) {
                bool band = ((c / 20) % 2 == 0) ^ flip;
                image.data[r * image.width + c] = band ? 255 : 0;
            }
        }
        flip = !flip;
        image.header.stamp = this->now();
        pub_->publish(image);
    }
    rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<CameraSim>());
    rclcpp::shutdown();
    return 0;
}
