"""注入整数纳秒时刻的教学输出策略，不连接ROS或车辆。

输入：speed为内置int/float速度，单位m/s，bool不作速度；last_seen_ns为
同一时基中的整数纳秒或None，now_ns为整数纳秒，timeout_ns为正整数纳秒。
输出：有效命令返回有限float速度；缺失、格式错误、未来或过期观测返回0.0。
非法timeout属于配置错误，抛ValueError；不将float纳秒先舍入成整数。
执行顺序：验证配置→验证数据类型/有限性→精确整数年龄→包含等号的边界判断。
本函数不访问时钟、限幅或控制设备；调用者负责时间来源相容与速度幅值合同。
"""
import math


def select_output(speed, last_seen_ns, now_ns, timeout_ns):
    """age==timeout仍有效，age>timeout或负年龄归零。

    纳秒整数可很大，Python整数相减不经过float，避免丢掉一个纳秒的边界。
    允许带符号整数时基，含义由调用者定义；不据正负号猜测不同时间域。
    """
    if type(timeout_ns) is not int or timeout_ns <= 0:
        raise ValueError('timeout_ns must be a positive integer number of nanoseconds')
    # bool是int的子类，但不是本合同中的时刻或速度，因此使用明确内置类型。
    if type(now_ns) is not int or type(last_seen_ns) is not int:
        return 0.0
    if type(speed) not in (int, float):
        return 0.0
    try:
        value = float(speed)
    except OverflowError:
        # 任意大整数不是可传递的有限DOUBLE速度；保持拒绝输出的策略。
        return 0.0
    if not math.isfinite(value):
        return 0.0
    age_ns = now_ns - last_seen_ns
    if age_ns < 0 or age_ns > timeout_ns:
        return 0.0
    return value
