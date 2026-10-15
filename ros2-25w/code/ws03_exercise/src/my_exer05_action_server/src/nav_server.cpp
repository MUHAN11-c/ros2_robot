/*
    需求：Nav 动作服务端 —— 解析客户端提交的目标点，控制小车驶向目标，
          过程中周期性发布剩余距离(连续反馈)，到达后响应执行结果。
    说明：剩余距离通过目标点和里程计坐标计算(订阅 /odom)。
*/
// 1.包含头文件；
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "my_exer_interfaces/action/nav.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "cmath"

using Nav = my_exer_interfaces::action::Nav;
using GoalHandleNav = rclcpp_action::ServerGoalHandle<Nav>;
using std::placeholders::_1;
using std::placeholders::_2;

// 3.自定义节点类；
class NavServer: public rclcpp::Node{
public:
    NavServer():Node("nav_server_node_cpp"){
        RCLCPP_INFO(this->get_logger(),"Nav 动作服务端创建!");
        // 3-1.创建动作服务端(处理请求数据: 判断是否执行)；
        server_ = rclcpp_action::create_server<Nav>(
            this,"nav",
            std::bind(&NavServer::handle_goal,this,_1,_2),
            std::bind(&NavServer::handle_cancel,this,_1),
            std::bind(&NavServer::handle_accepted,this,_1)
        );
        // 3-2.速度指令发布方与里程计订阅方；
        vel_pub_ = this->create_publisher<geometry_msgs::msg::Twist>("cmd_vel",10);
        odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>("odom",10,
            std::bind(&NavServer::odom_callback,this,_1));
        // 3-3.声明运动参数(线速度上限、到达阈值)；
        declare_parameter("linear",0.5);
        declare_parameter("tolerance",0.1);
    }
private:
    void odom_callback(const nav_msgs::msg::Odometry::SharedPtr odom){
        odom_ = odom;
    }
    // 处理请求数据(解析目标值，判断是否要执行)；
    rclcpp_action::GoalResponse handle_goal(const rclcpp_action::GoalUUID & uuid, std::shared_ptr<const Nav::Goal> goal){
        (void)uuid;
        RCLCPP_INFO(this->get_logger(),"接收到导航目标点:(%.2f,%.2f)",goal->goal.x,goal->goal.y);
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
    }
    // 处理取消请求；
    rclcpp_action::CancelResponse handle_cancel(const std::shared_ptr<GoalHandleNav> goal_handle){
        (void)goal_handle;
        return rclcpp_action::CancelResponse::ACCEPT;
    }
    void handle_accepted(const std::shared_ptr<GoalHandleNav> goal_handle){
        // 生成连续反馈以及最终响应 (子线程单独实现)
        std::thread{std::bind(&NavServer::execute,this,_1),goal_handle}.detach();
    }
    // 主逻辑：生成连续反馈与最终响应；
    void execute(std::shared_ptr<GoalHandleNav> goal_handle){
        // 1.生成连续反馈
        // 1-1.循环中发布剩余距离,循环体有休眠时间;
        // 1-2.剩余距离怎么计算? 订闭里程计 (通过目标点和里程计坐标计算剩余距离) 。
        rclcpp::Rate rate(1.0);
        double tolerance = get_parameter("tolerance").as_double();
        while (rclcpp::ok())
        {
            // 计算剩余距离
            double remaining = 0.0;
            if (odom_ != nullptr) {
                double dx = goal_handle->get_goal()->goal.x - odom_->pose.pose.position.x;
                double dy = goal_handle->get_goal()->goal.y - odom_->pose.pose.position.y;
                remaining = std::sqrt(dx * dx + dy * dy);
            }
            // zu zhi 反馈消息；
            auto feedback = std::make_shared<Nav::Feedback>();
            feedback->remaining = remaining;
            goal_handle->publish_feedback(feedback);
            RCLCPP_INFO(this->get_logger(),"剩余距离:%.2f",remaining);
            // 到达目标点则退出循环；
            if (remaining <= tolerance) {
                break;
            }
            // 简单比例控制: 朝向目标并前进；
            geometry_msgs::msg::Twist twist;
            double linear = get_parameter("linear").as_double();
            twist.linear.x = std::min(linear,remaining);
            vel_pub_->publish(twist);

            rate.sleep();
        }
        // 停车；
        vel_pub_->publish(geometry_msgs::msg::Twist());
        // 2.生成最终响应结果。
        auto result = std::make_shared<Nav::Result>();
        result->reached = true;
        result->distance = 0.0;
        goal_handle->succeed(result);
        RCLCPP_INFO(this->get_logger(),"到达目标点，导航完成!");
    }
    rclcpp_action::Server<Nav>::SharedPtr server_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr vel_pub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    nav_msgs::msg::Odometry::SharedPtr odom_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<NavServer>());
    rclcpp::shutdown();
    return 0;
}
