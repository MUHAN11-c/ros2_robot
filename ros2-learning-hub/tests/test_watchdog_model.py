"""看门狗数值模型的标准库边界测试；不会导入ROS或连接硬件。"""

import importlib.util
import math
from pathlib import Path
import unittest


MODEL_PATH = Path(__file__).resolve().parents[1] / "examples/offline_labs/watchdog_model.py"
SPEC = importlib.util.spec_from_file_location("watchdog_model", MODEL_PATH)
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


class WatchdogModelTests(unittest.TestCase):
    def test_fresh_requests_keep_value_and_saturate_both_directions(self):
        """正常输入保留原限幅语义，速度单位为m/s。"""
        target = MODEL.accepted_target
        self.assertEqual(target(1.1, 1.0, 0.1), 0.1)
        self.assertEqual(target(1.1, 1.0, -0.1), -0.1)
        self.assertEqual(target(1.1, 1.0, 0.8), 0.2)
        self.assertEqual(target(1.1, 1.0, -0.8), -0.2)
        self.assertEqual(target(1.1, 1.0, 0.1, velocity_limit=0.05), 0.05)

    def test_exact_timeout_boundary_and_next_representable_stale_time(self):
        """age==timeout接受，紧邻的下一个浮点时刻应过期。"""
        target = MODEL.accepted_target
        self.assertEqual(target(1.5, 1.0, 0.1, timeout=0.5), 0.1)
        self.assertEqual(target(math.nextafter(1.5, math.inf), 1.0, 0.1, timeout=0.5), 0.0)

    def test_missing_future_negative_and_expired_timestamps_are_rejected(self):
        target = MODEL.accepted_target
        for now, stamp in ((1.0, None), (1.0, 1.1), (-0.1, 0.0), (1.0, -0.1), (1.5, 1.0)):
            with self.subTest(now=now, stamp=stamp):
                self.assertEqual(target(now, stamp, 0.1), 0.0)

    def test_every_numeric_input_rejects_nan_and_infinity(self):
        """复现并阻止NaN经min/max漏检后输出+0.2的缺陷。"""
        baseline = dict(now=1.1, received_at=1.0, requested=0.1, timeout=0.3, velocity_limit=0.2)
        for field in baseline:
            for invalid in (float("nan"), float("inf"), float("-inf")):
                values = dict(baseline, **{field: invalid})
                with self.subTest(field=field, invalid=repr(invalid)):
                    self.assertEqual(MODEL.accepted_target(**values), 0.0)

    def test_invalid_limits_and_types_are_rejected_without_raising(self):
        baseline = dict(now=1.1, received_at=1.0, requested=0.1, timeout=0.3, velocity_limit=0.2)
        for field in baseline:
            for invalid in (None, True, "0.1", object(), 10 ** 1000):
                values = dict(baseline, **{field: invalid})
                with self.subTest(field=field, type=type(invalid).__name__):
                    self.assertEqual(MODEL.accepted_target(**values), 0.0)
        for field in ("timeout", "velocity_limit"):
            for invalid in (0.0, -0.1):
                with self.subTest(field=field, invalid=invalid):
                    self.assertEqual(MODEL.accepted_target(**dict(baseline, **{field: invalid})), 0.0)

    def test_healthy_input_grid_is_finite_bounded_and_monotone(self):
        """在多组合法周期/限速中核验限幅性质，而非只检查单个示例。"""
        for age in (0.0, 0.125, 0.25):
            for limit in (0.05, 0.2, 1.0):
                outputs = [MODEL.accepted_target(1.0 + age, 1.0, requested, timeout=0.5,
                                                 velocity_limit=limit)
                           for requested in (-2.0, -0.2, -0.1, 0.0, 0.1, 0.2, 2.0)]
                self.assertTrue(all(math.isfinite(value) and -limit <= value <= limit for value in outputs))
                self.assertEqual(outputs, sorted(outputs))

    def test_embedded_demonstration_assertions(self):
        MODEL.run_checks()


if __name__ == "__main__":
    unittest.main(verbosity=2)
