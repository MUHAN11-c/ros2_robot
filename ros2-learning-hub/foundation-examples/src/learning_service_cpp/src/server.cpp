#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "example_interfaces/srv/add_two_ints.hpp"
using Add = example_interfaces::srv::AddTwoInts;

class SumServer : public rclcpp::Node
{
public:
  SumServer() : Node("learning_sum_cpp")
  {
    service_ = create_service<Add>("sum",
      [this](std::shared_ptr<Add::Request> request,
             std::shared_ptr<Add::Response> response) {
        response->sum = request->a + request->b;
        RCLCPP_INFO(get_logger(), "request handled");
      });
  }
private:
  rclcpp::Service<Add>::SharedPtr service_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<SumServer>());
  rclcpp::shutdown();
  return 0;
}
