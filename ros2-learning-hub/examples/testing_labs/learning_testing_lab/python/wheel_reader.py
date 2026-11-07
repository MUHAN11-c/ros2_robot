"""下游消息边界：将[左,右]有限轮速rad/s解释为不可变快照，不重复实现差速换算。"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Rates:
    left_rad_s: float
    right_rad_s: float


def decode_pair(values):
    """输入两个实数，输出带单位命名字段；错误长度、bool、字符串和非有限值拒绝。

    校验属于下游数据入口，不把维数相同的其它物理量自动解释为轮速。
    """
    if len(values) != 2:
        raise ValueError('expected exactly [left_rad_s,right_rad_s]')
    if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
        raise ValueError('wheel rates must be finite real values')
    return Rates(float(values[0]), float(values[1]))
