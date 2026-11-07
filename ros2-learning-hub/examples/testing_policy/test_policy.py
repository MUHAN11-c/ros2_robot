"""按输入合同验证策略；pytest参数化项会分别计入实际XML测试数。

速度单位m/s，时刻/期限为整数纳秒。无需ROS、真实sleep或设备。
期望来自数据合同：非法配置抛异常，非法运行数据归零；不复写函数内部计算。
"""
import pytest
from policy import select_output


def test_fresh_command():
    assert select_output(0.4, 100, 150, 100) == 0.4
    assert select_output(1, 100, 150, 100) == 1.0


def test_timeout_boundary():
    # 相差一个纳秒的两项能区分 > 与 >= 的边界错误。
    assert select_output(0.4, 100, 200, 100) == 0.4
    assert select_output(0.4, 100, 201, 100) == 0.0


def test_missing_and_future_sample():
    assert select_output(0.4, None, 150, 100) == 0.0
    assert select_output(0.4, 200, 150, 100) == 0.0
    # 有符号时基也按相同整数年龄合同处理，不强行转成日期或ROS时间。
    assert select_output(0.4, -200, -100, 100) == 0.4


@pytest.mark.parametrize('speed', [float('nan'), float('inf'), -float('inf'), True, None, '0.4'])
def test_invalid_runtime_speed(speed):
    assert select_output(speed, 100, 150, 100) == 0.0


@pytest.mark.parametrize('field', ['last_seen_ns', 'now_ns'])
@pytest.mark.parametrize('invalid', [True, 150.0, float('nan'), float('inf'), '150', None])
def test_invalid_runtime_timestamp(field, invalid):
    values = dict(speed=0.4, last_seen_ns=100, now_ns=150, timeout_ns=100)
    values[field] = invalid
    assert select_output(**values) == 0.0


@pytest.mark.parametrize('timeout', [0, -1, True, 100.0, float('nan'), float('inf'), '100', None])
def test_invalid_timeout_is_configuration_error(timeout):
    with pytest.raises(ValueError):
        select_output(0.4, 100, 150, timeout)


def test_large_integer_timestamp_keeps_one_ns_boundary():
    # 转float会丢精度的整数时戳，仍应分清恰好期限与超一个纳秒。
    origin = 10**1000
    assert select_output(0.4, origin, origin + 100, 100) == 0.4
    assert select_output(0.4, origin, origin + 101, 100) == 0.0


def test_unrepresentable_integer_speed_is_rejected():
    assert select_output(10**1000, 100, 150, 100) == 0.0
