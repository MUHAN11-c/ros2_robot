/*
    需求：提交目标值到服务端，处理连续反馈与最终响应。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建动作客户端；
            3-2.等待服务连接；
            3-3.发送目标；
            3-4.处理目标响应(是否被接受)；
            3-5.处理连续反馈；
            3-6.处理最终响应。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "base_interfaces_demo/action/progress.hpp"

using Progress = base_interfaces_demo::action::Progress;
using GoalHandleProgress = rclcpp_action::ClientGoalHandle<Progress>;
using namespace std::placeholders;
using namespace std::chrono_literals;

// 3.自定义节点类；
class ProgressActionClient: public rclcpp::Node{
public:
    ProgressActionClient():Node("progress_action_client_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"动作通信客户端创建!");
        // 3-1.创建动作客户端；
        client_ = rclcpp_action::create_client<Progress>(this,"get_sum");
    }
    // 3-2.等待服务连接；
    bool connect_server(){
        while (!client_->wait_for_action_server(1s)) {
            if (!rclcpp::ok()) {
                RCLCPP_INFO(this->get_logger(),"客户端退出...");
                return false;
            }
            RCLCPP_INFO(this->get_logger(),"服务连接中，请稍候...");
        }
        return true;
    }
    // 3-3.发送目标；
    void send_goal(int64_t num){
        // 组织目标值；
        auto goal = Progress::Goal();
        goal.num = num;
        RCLCPP_INFO(this->get_logger(),"发送目标值:%ld",num);
        // 异步发送，设置回调；
        auto send_goal_options = rclcpp_action::Client<Progress>::SendGoalOptions();
        send_goal_options.goal_response_callback =
            std::bind(&ProgressActionClient::goal_response_callback,this,_1);
        send_goal_options.feedback_callback =
            std::bind(&ProgressActionClient::feedback_callback,this,_1,_2);
        send_goal_options.result_callback =
            std::bind(&ProgressActionClient::result_callback,this,_1);
        client_->async_send_goal(goal,send_goal_options);
    }
private:
    // 3-4.处理目标响应(是否被接受)；
    // Jazzy 起目标响应回调直接接收 GoalHandle 共享指针（Humble 为 shared_future，需 .get()）；
    void goal_response_callback(GoalHandleProgress::SharedPtr goal_handle){
        if (!goal_handle) {
            RCLCPP_INFO(this->get_logger(),"目标被服务端拒绝了!");
        } else {
            RCLCPP_INFO(this->get_logger(),"目标被服务端接受，请等待连续反馈与最终响应!");
        }
    }
    // 3-5.处理连续反馈；
    void feedback_callback(GoalHandleProgress::SharedPtr goal_handle, const std::shared_ptr<const Progress::Feedback> feedback){
        (void)goal_handle;
        RCLCPP_INFO(this->get_logger(),"收到连续反馈:%.2f",feedback->progress);
    }
    // 3-6.处理最终响应；
    void result_callback(const GoalHandleProgress::WrappedResult & result){
        if (result.code == rclcpp_action::ResultCode::SUCCEEDED) {
            RCLCPP_INFO(this->get_logger(),"最终响应结果:%ld",result.result->sum);
        } else {
            RCLCPP_INFO(this->get_logger(),"任务执行失败!");
        }
    }
    rclcpp_action::Client<Progress>::SharedPtr client_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    if (argc != 2) {
        RCLCPP_INFO(rclcpp::get_logger("rclcpp"),"请提交一个大于等于1的整型数据!");
        return 1;
    }
    int64_t num = atol(argv[1]);
    auto client = std::make_shared<ProgressActionClient>();
    if (!client->connect_server()) {
        rclcpp::shutdown();
        return 0;
    }
    client->send_goal(num);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(client);
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
