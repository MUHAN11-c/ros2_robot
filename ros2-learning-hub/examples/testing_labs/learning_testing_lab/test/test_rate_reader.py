"""7个pytest案例：1个已知消息+6个公开消息边界；不生成ROS通信或重复C++算法。"""
import math
import pytest
from wheel_reader import decode_pair


def test_known_pair_has_explicit_left_right_units():
    pair = decode_pair([5.0, 7.0])
    assert (pair.left_rad_s, pair.right_rad_s) == (5.0, 7.0)


@pytest.mark.parametrize('bad', [[], [1.0], [1.0, 2.0, 3.0],
                                [math.nan, 1.0], [math.inf, 1.0], [True, 1.0]])
def test_malformed_or_nonfinite_pair_is_rejected(bad):
    with pytest.raises(ValueError):
        decode_pair(bad)
