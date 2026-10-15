/*
    需求：演示进程内通信(intra-process)——同一进程内的发布方与订阅方，
          消息不经过 DDS 中间序列化，直接在进程内传递。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类(发布方/订阅方)，通过 NodeOptions 开启进程内通信；
        4.创建单线程执行器，将两个节点集成到同一进程并执行；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

using namespace std::chrono_literals;

// 3.自定义节点类(发布方)；
class MinimalPublisher : public rclcpp::Node
{
public:
    explicit MinimalPublisher(const rclcpp::NodeOptions & options)
    : Node("intra_pub_node_cpp", options){
        publisher_ = this->create_publisher<std_msgs::msg::String>("chatter",10);
        timer_ = this->create_wall_timer(1s,std::bind(&MinimalPublisher::on_timer,this));
    }
private:
    void on_timer(){
        auto message = std_msgs::msg::String();
        message.data = "hello intra process!";
        RCLCPP_INFO(this->get_logger(),"发布:%s",message.data.c_str());
        publisher_->publish(message);
    }
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
};

// 自定义节点类(订阅方)；
class MinimalSubscriber : public rclcpp::Node
{
public:
    explicit MinimalSubscriber(const rclcpp::NodeOptions & options)
    : Node("intra_sub_node_cpp", options){}
private:
    // 订阅方通过参数指定创建(见 main)，回调处理订阅到的消息；
    void topic_callback(const std_msgs::msg::String & msg) const{
        RCLCPP_INFO(this->get_logger(),"订阅的消息：'%s'",msg.data.c_str());
    }
public:
    void setup(){
        subscription_ = this->create_subscription<std_msgs::msg::String>("chatter",10,
            std::bind(&MinimalSubscriber::topic_callback,this,std::placeholders::_1));
    }
private:
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ros2 客户端；
    rclcpp::init(argc,argv);
    // 4.核心：将发布方对象和订阅方对象集成到同一进程；
    // 4-1.节点设置：开启进程内通信；
    rclcpp::NodeOptions options;
    options.use_intra_process_comms(true);
    // 4-2.创建一个进程执行器
    rclcpp::executors::SingleThreadedExecutor executor;
    // 4-3.创建节点对象并添加进进程执行器
    auto pub = std::make_shared<MinimalPublisher>(options);
    auto sub = std::make_shared<MinimalSubscriber>(options);
    sub->setup();
    executor.add_node(pub);
    executor.add_node(sub);
    RCLCPP_INFO(rclcpp::get_logger("main"),"节点已加入执行器，开始 spin");
    // 4-4.执行器执行
    executor.spin();
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
