// 4个gtest案例来自外部几何合同和手算值，不从实现返回值反推“正确答案”。
// 所有角速度rad/s；浮点绝对容差1e-12。纯算法不启动ROS节点。
#include <limits>
#include <gtest/gtest.h>
#include "learning_testing_lab/wheel_rates.hpp"
using learning_testing_lab::wheel_rates;

TEST(WheelContract, StraightLineHasEqualWheelRates)
{
  // 每秒0.6米、半径0.1米→每轮6rad/s；轮距不会改变直行对称性。
  const auto out = wheel_rates(0.6, 0.0, 0.4, 0.1);
  EXPECT_NEAR(out.left_rad_s, 6.0, 1e-12);
  EXPECT_NEAR(out.right_rad_s, 6.0, 1e-12);
}
TEST(WheelContract, PureLeftRotationHasOppositeRates)
{
  // yaw=0.5、轮距0.4：轮缘线速度为±0.1m/s，所以左右为-1/+1rad/s。
  const auto out = wheel_rates(0.0, 0.5, 0.4, 0.1);
  EXPECT_NEAR(out.left_rad_s, -1.0, 1e-12);
  EXPECT_NEAR(out.right_rad_s, 1.0, 1e-12);
}
TEST(WheelContract, CombinedMotionMatchesHandCalculatedOracle)
{
  // 0.6m/s直行叠加±0.1m/s轮缘速度，除以0.1m得5/7rad/s。
  const auto out = wheel_rates(0.6, 0.5, 0.4, 0.1);
  EXPECT_NEAR(out.left_rad_s, 5.0, 1e-12);
  EXPECT_NEAR(out.right_rad_s, 7.0, 1e-12);
}
TEST(WheelContract, InvalidGeometryNonfiniteAndOverflowAreRejected)
{
  EXPECT_THROW(wheel_rates(0.6, 0.0, 0.4, 0.0), std::invalid_argument);
  EXPECT_THROW(wheel_rates(0.6, 0.0, -0.4, 0.1), std::invalid_argument);
  EXPECT_THROW(wheel_rates(std::numeric_limits<double>::quiet_NaN(), 0.0, 0.4, 0.1), std::invalid_argument);
  EXPECT_THROW(wheel_rates(1e308, 0.0, 0.4, 0.1), std::overflow_error);
}
