"""纯标准库看门狗模型：拒绝非有限/无效输入，输出合法目标或模型拒绝值0。

输入：同一单调时基下、相对实验起点的非负秒值 now/received_at；
      请求速度 requested（m/s）、正超时 timeout（s）、正限速 velocity_limit（m/s）。
输出：[-velocity_limit, velocity_limit] 内的有限速度（m/s）；无效输入统一返回0.0。
顺序：类型与有限性检查 → 时长/限速有效性 → 时间先后与年龄 → 限幅。
边界：received_at=None、NaN、Inf、非法类型、未来戳、过期值均拒绝。
这只是离线数值模型；返回0不证明消息已发送、电机已制动或真实机器人已停稳。
"""

import math


def _finite_number(value):
    """只接收可表示为有限实数的int/float；拒绝bool和隐式字符串转换。"""
    # bool虽是int子类，却不是本模型认可的时间/速度输入。
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except (TypeError, ValueError, OverflowError):
        # 特别大的Python整数转换为浮点时也可能溢出，应按拒绝处理而非崩溃。
        return False


def accepted_target(now, received_at, requested, timeout=0.3, velocity_limit=0.2):
    """返回新鲜请求的限幅速度，否则返回模型拒绝值0.0。

    received_at与now必须取自同一单调时钟，并转换为相对实验起点的秒值。
    age==timeout在本模型中仍接受；浮点边界按实际比较结果处理，设备侧可选
    整数tick/纳秒表示来避免小数秒的舍入歧义，但应另行设计时钟回绕策略。
    """
    values = (now, received_at, requested, timeout, velocity_limit)
    if not all(_finite_number(value) for value in values):
        return 0.0
    # 本模型规定相对起点的非负时间、严格正的有效期和限速。
    if now < 0.0 or received_at < 0.0 or timeout <= 0.0 or velocity_limit <= 0.0:
        return 0.0
    # 先比较先后，不能把未来时间戳当成“比新鲜更好”的数据。
    if received_at > now:
        return 0.0
    age = now - received_at
    # 即使各时间值有限，仍显式核对差值，避免后续替换数值类型时漏掉溢出。
    if not _finite_number(age) or age > timeout:
        return 0.0
    # 仅在所有验证通过后限幅，防止min/max对NaN的比较语义产生意外正速度。
    return max(-velocity_limit, min(velocity_limit, requested))


def run_checks():
    """运行不连接ROS或硬件的真实边界断言。"""
    assert accepted_target(1.0, None, 0.1) == 0.0
    assert accepted_target(1.1, 1.0, 0.1) == 0.1
    assert accepted_target(1.5, 1.0, 0.1) == 0.0
    assert accepted_target(1.1, 1.0, 0.8) == 0.2
    assert accepted_target(1.1, 1.0, -0.8) == -0.2
    # 这里用二进制可精确表达的0.5s测试包含上边界，再测试紧邻的过期值。
    assert accepted_target(1.5, 1.0, 0.1, timeout=0.5) == 0.1
    assert accepted_target(math.nextafter(1.5, math.inf), 1.0, 0.1, timeout=0.5) == 0.0
    assert accepted_target(1.0, 1.1, 0.1) == 0.0
    assert accepted_target(1.1, 1.0, 0.1, timeout=0.0) == 0.0
    assert accepted_target(1.1, 1.0, 0.1, velocity_limit=-0.2) == 0.0
    for invalid in (float("nan"), float("inf"), float("-inf")):
        assert accepted_target(1.1, 1.0, invalid) == 0.0
        assert accepted_target(invalid, 1.0, 0.1) == 0.0
        assert accepted_target(1.1, invalid, 0.1) == 0.0
        assert accepted_target(1.1, 1.0, 0.1, timeout=invalid) == 0.0
        assert accepted_target(1.1, 1.0, 0.1, velocity_limit=invalid) == 0.0
    print("离线看门狗模型有限性、时间边界及限幅断言通过；未验证硬件停车。")


if __name__ == "__main__":
    run_checks()
