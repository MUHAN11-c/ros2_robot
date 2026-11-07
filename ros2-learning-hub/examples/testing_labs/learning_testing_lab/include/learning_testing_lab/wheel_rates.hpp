// 输入：车体前向速度m/s、偏航角速度rad/s、左右轮距m、轮半径m。
// 输出：左/右轮角速度rad/s。约定正yaw左转，左右轮速度差为yaw*track。
// 模型：平面差速、纯滚动、相同轮半径；没有限幅、打滑或硬件制动保证。
#pragma once
#include <cmath>
#include <stdexcept>

namespace learning_testing_lab
{
struct WheelRates {double left_rad_s; double right_rad_s;};

inline WheelRates wheel_rates(double forward_m_s, double yaw_rad_s,
  double track_m, double radius_m)
{
  if (!std::isfinite(forward_m_s) || !std::isfinite(yaw_rad_s) ||
    !std::isfinite(track_m) || !std::isfinite(radius_m) || track_m <= 0.0 || radius_m <= 0.0)
  {
    throw std::invalid_argument("finite velocities and positive finite geometry required");
  }
  WheelRates out{(forward_m_s - yaw_rad_s * track_m / 2.0) / radius_m,
    (forward_m_s + yaw_rad_s * track_m / 2.0) / radius_m};
  if (!std::isfinite(out.left_rad_s) || !std::isfinite(out.right_rad_s)) {
    throw std::overflow_error("wheel rate overflow");
  }
  return out;
}
}  // namespace learning_testing_lab
