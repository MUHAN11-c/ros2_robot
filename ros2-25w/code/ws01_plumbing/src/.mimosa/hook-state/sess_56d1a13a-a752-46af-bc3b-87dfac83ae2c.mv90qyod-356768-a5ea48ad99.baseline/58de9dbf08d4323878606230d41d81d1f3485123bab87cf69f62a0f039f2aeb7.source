/*
    需求：解析客户端提交的目标值，循环累加并发布连续反馈，最终响应求和结果。
    流程：
        1.包含头文件；
        2.初始化 ROS2 客户端；
        3.自定义节点类；
            3-1.创建动作服务端；
            3-2.处理请求数据(解析目标值，判断是否要执行)；
            3-3.生成连续反馈与最终响应(回调函数)。
        4.调用spin函数，并传入节点对象指针；
        5.释放资源。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "base_interfaces_demo/action/progress.hpp"

using Progress = base_interfaces_demo::action::Progress;
using GoalHandleProgress = rclcpp_action::ServerGoalHandle<Progress>;
using namespace std::placeholders;

// 3.自定义节点类；
class ProgressActionServer: public rclcpp::Node{
public:
    ProgressActionServer():Node("progress_action_server_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"动作通信服务端创建!");
        // 3-1.创建动作服务端；
        server_ = rclcpp_action::create_server<Progress>(
            this,
            "get_sum",
            std::bind(&ProgressActionServer::handle_goal,this,_1,_2),
            std::bind(&ProgressActionServer::handle_cancel,this,_1),
            std::bind(&ProgressActionServer::handle_accepted,this,_1)
        );
    }
private:
    // 3-2.处理请求数据(解析目标值，判断是否要执行)；
    rclcpp_action::GoalResponse handle_goal(const rclcpp_action::GoalUUID & uuid, std::shared_ptr<const Progress::Goal> goal){
        (void)uuid;
        RCLCPP_INFO(this->get_logger(),"接收到客户端请求，目标值:%ld",goal->num);
        if (goal->num >= 1) {
            return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
        }
        return rclcpp_action::GoalResponse::REJECT;
    }
    // 处理取消请求；
    rclcpp_action::CancelResponse handle_cancel(const std::shared_ptr<GoalHandleProgress> goal_handle){
        (void)goal_handle;
        RCLCPP_INFO(this->get_logger(),"接受到取消请求");
        return rclcpp_action::CancelResponse::ACCEPT;
    }
    void handle_accepted(const std::shared_ptr<GoalHandleProgress> goal_handle){
        // 生成连续反馈以及最终响应(子线程单独实现)；
        std::thread{std::bind(&ProgressActionServer::execute,this,_1),goal_handle}.detach();
    }
    // 3-3.生成连续反馈与最终响应(回调函数)；
    void execute(std::shared_ptr<GoalHandleProgress> goal_handle){
        // 1.生成连续反馈；
        int64_t num = goal_handle->get_goal()->num;
        int64_t sum = 0;
        auto feedback = std::make_shared<Progress::Feedback>();
        feedback->progress = 0.0;
        rclcpp::Rate rate(1.0);
        for (int64_t i = 1; i <= num; i++) {
            sum += i;
            double progress = i / (double)num; // 计算进度
            feedback->progress = progress;
            goal_handle->publish_feedback(feedback);
            RCLCPP_INFO(this->get_logger(),"连续反馈中，进度:%.2f",progress);
            rate.sleep();
        }
        // 2.生成最终响应结果。
        if (rclcpp::ok())
        {
            auto result = std::make_shared<Progress::Result>();
            result->sum = sum;
            goal_handle->succeed(result);
            RCLCPP_INFO(this->get_logger(),"最终结果:%ld",sum);
        }
    }
    rclcpp_action::Server<Progress>::SharedPtr server_;
};

int main(int argc, char ** argv)
{
    // 2.初始化 ROS2 客户端；
    rclcpp::init(argc,argv);
    // 4.调用spin函数，并传入节点对象指针；
    rclcpp::spin(std::make_shared<ProgressActionServer>());
    // 5.释放资源；
    rclcpp::shutdown();
    return 0;
}
