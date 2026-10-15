/*
    需求：Nav 动作客户端 —— 提交目标点(命令行参数: x y)，处理连续反馈与最终响应。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "my_exer_interfaces/action/nav.hpp"

using Nav = my_exer_interfaces::action::Nav;
using GoalHandleNav = rclcpp_action::ClientGoalHandle<Nav>;
using namespace std::chrono_literals;
using std::placeholders::_1;
using std::placeholders::_2;

// 3.自定义节点类；
class NavClient: public rclcpp::Node{
public:
    NavClient():Node("nav_client_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"Nav 动作客户端创建!");
        // 3-1.创建动作客户端；
        client_ = rclcpp_action::create_client<Nav>(this,"nav");
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
    void send_goal(double x, double y){
        auto goal = Nav::Goal();
        goal.goal.x = x;
        goal.goal.y = y;
        RCLCPP_INFO(this->get_logger(),"发送导航目标:(%.2f,%.2f)",x,y);
        auto send_goal_options = rclcpp_action::Client<Nav>::SendGoalOptions();
        send_goal_options.goal_response_callback =
            std::bind(&NavClient::goal_response_callback,this,_1);
        send_goal_options.feedback_callback =
            std::bind(&NavClient::feedback_callback,this,_1,_2);
        send_goal_options.result_callback =
            std::bind(&NavClient::result_callback,this,_1);
        client_->async_send_goal(goal,send_goal_options);
    }
private:
    // Jazzy 起目标响应回调直接接收 GoalHandle 共享指针（Humble 为 shared_future，需 .get()）；
    void goal_response_callback(GoalHandleNav::SharedPtr goal_handle){
        if (!goal_handle) {
            RCLCPP_INFO(this->get_logger(),"目标被服务端拒绝!");
        } else {
            RCLCPP_INFO(this->get_logger(),"目标被接受，开始导航...");
        }
    }
    void feedback_callback(GoalHandleNav::SharedPtr goal_handle, const std::shared_ptr<const Nav::Feedback> feedback){
        (void)goal_handle;
        RCLCPP_INFO(this->get_logger(),"连续反馈，剩余距离:%.2f",feedback->remaining);
    }
    void result_callback(const GoalHandleNav::WrappedResult & result){
        if (result.code == rclcpp_action::ResultCode::SUCCEEDED) {
            RCLCPP_INFO(this->get_logger(),"导航完成!");
        } else {
            RCLCPP_INFO(this->get_logger(),"导航失败!");
        }
    }
    rclcpp_action::Client<Nav>::SharedPtr client_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    if (argc != 3) {
        RCLCPP_INFO(rclcpp::get_logger("rclcpp"),"请提交目标点: x y");
        return 1;
    }
    auto client = std::make_shared<NavClient>();
    if (!client->connect_server()) {
        rclcpp::shutdown();
        return 0;
    }
    client->send_goal(atof(argv[1]),atof(argv[2]));
    rclcpp::spin(client);
    rclcpp::shutdown();
    return 0;
}
