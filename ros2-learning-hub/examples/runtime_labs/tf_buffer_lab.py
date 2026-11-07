#!/usr/bin/env python3
"""Jazzy tf2 的进程内数值实验：不创建 Node、DDS 端点、仿真或硬件连接。

输入均固定在源码中：平移/点坐标为米，yaw 为绕 +Z 的右手弧度，时间为秒。
实验顺序：非零旋转正变换→逆变换→静态任意时刻→动态插值→latest 对比→失败路径。
默认绝对容差为 1e-9（米/四元数分量）；时间戳以整数纳秒精确比较。
输出每项的输入、预期与实际值；任何断言失败返回非零。--json 输出完整机器可读结果。
--help 仅加载 Python 标准库，实际计算才导入已安装的 ROS Jazzy Python 包。
运行：source /opt/ros/jazzy/setup.bash 后执行 python3 examples/runtime_labs/tf_buffer_lab.py。
"""

import argparse
import json
import math
import sys


def parse_tolerance(text):
    """容差必须是有限正数；不允许用过松容差掩盖米与毫米等量纲错误。"""
    value = float(text)
    if not math.isfinite(value) or not 0.0 < value <= 1.0e-6:
        raise argparse.ArgumentTypeError('atol 必须是 (0, 1e-6] 内的有限正数')
    return value


def run_lab(atol=1.0e-9):
    # 这些依赖由 Jazzy 的 rclpy、geometry_msgs、tf2_ros_py、tf2_geometry_msgs 提供。
    # 故意不调用 rclpy.init()，也不创建 Node、TransformListener 或广播/订阅端点。
    # Buffer.set_transform* 直接向本进程的缓存写入合成数据，不会发布 /tf 或 /tf_static。
    from geometry_msgs.msg import PointStamped, TransformStamped
    from rclpy.clock import ClockType
    from rclpy.duration import Duration
    from rclpy.time import Time
    from tf2_geometry_msgs import do_transform_point
    from tf2_ros import Buffer, ExtrapolationException, LookupException

    results = []

    def query_time(seconds):
        """把给定秒数转换为 ROS 时间类型；0 在 tf2 查询中具有 latest 特殊含义。"""
        return Time(seconds=seconds, clock_type=ClockType.ROS_TIME)

    def transform(parent, child, stamp_s, translation_m, yaw_rad):
        """输出 parent←child 的 TransformStamped：把 child 坐标中的数据变到 parent。

        translation_m 是 child 原点在 parent 中的位置，yaw_rad 是 child 相对 parent
        的方向。平面四元数为 (0,0,sin(yaw/2),cos(yaw/2))，不把欧拉角塞进 z 字段。
        """
        msg = TransformStamped()
        msg.header.frame_id = parent
        msg.child_frame_id = child
        msg.header.stamp = query_time(stamp_s).to_msg()
        msg.transform.translation.x, msg.transform.translation.y, msg.transform.translation.z = translation_m
        msg.transform.rotation.z = math.sin(yaw_rad / 2.0)
        msg.transform.rotation.w = math.cos(yaw_rad / 2.0)
        return msg

    def point(frame, xyz_m, stamp_s):
        """输出带源坐标系与采样时刻的点；消息本身不会因改 frame_id 自动变换数值。"""
        msg = PointStamped()
        msg.header.frame_id = frame
        msg.header.stamp = query_time(stamp_s).to_msg()
        msg.point.x, msg.point.y, msg.point.z = xyz_m
        return msg

    def xyz(msg):
        return [msg.point.x, msg.point.y, msg.point.z]

    def translation(msg):
        return [msg.transform.translation.x, msg.transform.translation.y, msg.transform.translation.z]

    def quaternion(msg):
        q = msg.transform.rotation
        return [q.x, q.y, q.z, q.w]

    def stamp_ns(header):
        # 时间戳比较使用整数；1 秒=10^9 纳秒，不把浮点时间误差混入数值容差。
        return header.stamp.sec * 1_000_000_000 + header.stamp.nanosec

    def close_vector(actual, expected, label):
        """只用绝对容差；输入量级固定且小，避免相对容差掩盖固定的几何偏差。"""
        assert len(actual) == len(expected), label + ' 维数不同'
        assert all(math.isfinite(v) for v in actual), label + ' 出现非有限值'
        for i, (got, wanted) in enumerate(zip(actual, expected)):
            assert math.isclose(got, wanted, rel_tol=0.0, abs_tol=atol), (
                f'{label}[{i}]: actual={got!r}, expected={wanted!r}, atol={atol}')

    def same_rotation(actual_q, expected_q, label):
        """q 与 -q 表示同一旋转；比较时允许整体变号，同时检查单位长度。"""
        q = actual_q
        if sum(a * e for a, e in zip(q, expected_q)) < 0.0:
            q = [-v for v in q]
        close_vector(q, expected_q, label)
        assert math.isclose(sum(v * v for v in actual_q), 1.0, rel_tol=0.0, abs_tol=atol)

    # 一、带 +90° 非零旋转的静态外参，避免“方向反了只需平移取负”的错误直觉。
    # 输入：laser 原点在 base_link 中为 (0.2,0,0.3)m，laser +X 指向 base_link +Y。
    # 手算：Rz(π/2)·(1,0,0)+(0.2,0,0.3)=(0.2,1,0.3)m。
    static_buffer = Buffer()
    static_buffer.set_transform_static(
        transform('base_link', 'laser', 123.0, (0.2, 0.0, 0.3), math.pi / 2.0),
        'tf_buffer_lab_static')
    laser_point = point('laser', (1.0, 0.0, 0.0), 10.5)
    forward_tf = static_buffer.lookup_transform('base_link', 'laser', query_time(10.5))
    base_point = do_transform_point(laser_point, forward_tf)
    close_vector(xyz(base_point), [0.2, 1.0, 0.3], '静态正向点')
    assert base_point.header.frame_id == 'base_link'
    assert forward_tf.header.frame_id == 'base_link' and forward_tf.child_frame_id == 'laser'
    results.append(dict(
        id='static_forward_direction_rotation', passed=True,
        input=dict(source='laser', target='base_link', point_m=[1.0, 0.0, 0.0],
                   translation_m=[0.2, 0.0, 0.3], yaw_rad=math.pi / 2.0, query_s=10.5),
        expected_point_m=[0.2, 1.0, 0.3], actual_point_m=xyz(base_point)))

    # 二、逆变换必须使用 R^T 和 -R^T·t。本例逆平移是 (0,0.2,-0.3)m，
    # 与直接把 t 取负得到 (-0.2,0,-0.3)m 不同；把刚才的目标点变回源应恢复原值。
    inverse_tf = static_buffer.lookup_transform('laser', 'base_link', query_time(10.5))
    restored = do_transform_point(base_point, inverse_tf)
    close_vector(translation(inverse_tf), [0.0, 0.2, -0.3], '旋转后的逆平移')
    close_vector(xyz(restored), [1.0, 0.0, 0.0], '正逆组合恢复源点')
    same_rotation(quaternion(inverse_tf), [0.0, 0.0, -math.sqrt(0.5), math.sqrt(0.5)], '逆旋转')
    assert restored.header.frame_id == 'laser'
    results.append(dict(
        id='static_inverse_nonzero_rotation', passed=True,
        expected_inverse_translation_m=[0.0, 0.2, -0.3],
        actual_inverse_translation_m=translation(inverse_tf),
        expected_restored_point_m=[1.0, 0.0, 0.0], actual_restored_point_m=xyz(restored),
        actual_inverse_quaternion_xyzw=quaternion(inverse_tf)))

    # 三、静态缓存的几何关系对所有查询时刻相同，而不是只在发布 stamp=123 秒有效。
    # 0 秒使用 latest 特殊查询；其余非零时刻分别在发布时刻前后。不是在等待真实时间。
    static_queries = []
    for seconds in (0.0, 1.0, 10.5, 1_000_000.0):
        tf_msg = static_buffer.lookup_transform('base_link', 'laser', query_time(seconds))
        out = do_transform_point(laser_point, tf_msg)
        close_vector(xyz(out), [0.2, 1.0, 0.3], '静态任意时刻')
        static_queries.append(dict(query_s=seconds, actual_point_m=xyz(out),
                                   returned_transform_stamp_ns=stamp_ns(tf_msg.header)))
    results.append(dict(id='static_arbitrary_query_times', passed=True,
                        published_stamp_s=123.0, queries=static_queries,
                        expected_point_m=[0.2, 1.0, 0.3]))

    # 四、动态缓存只写两条合成变换。显式保留20秒历史，两个样本相隔2秒，均在缓存内。
    # t=10s: 平移0m、yaw=0；t=12s: 平移(2,0,0)m、yaw=π/2。
    # t=11s 的平移线性插值为(1,0,0)m，最短弧四元数插值为 yaw=π/4。
    # 对 sensor 中(1,0,0)m，手算 base 中为(1+√0.5,√0.5,0)m。
    dynamic_buffer = Buffer(cache_time=Duration(seconds=20.0))
    for seconds, x_m, yaw_rad in ((10.0, 0.0, 0.0), (12.0, 2.0, math.pi / 2.0)):
        dynamic_buffer.set_transform(
            transform('base_dynamic', 'sensor', seconds, (x_m, 0.0, 0.0), yaw_rad),
            'tf_buffer_lab_dynamic')
    measured_point = point('sensor', (1.0, 0.0, 0.0), 11.0)
    sampled_tf = dynamic_buffer.lookup_transform(
        'base_dynamic', 'sensor', Time.from_msg(measured_point.header.stamp))
    sampled_point = do_transform_point(measured_point, sampled_tf)
    sampled_expected = [1.0 + math.sqrt(0.5), math.sqrt(0.5), 0.0]
    close_vector(translation(sampled_tf), [1.0, 0.0, 0.0], '动态平移插值')
    same_rotation(quaternion(sampled_tf), [0.0, 0.0, math.sin(math.pi / 8.0), math.cos(math.pi / 8.0)],
                  '动态旋转插值')
    close_vector(xyz(sampled_point), sampled_expected, '采样时刻插值点')
    assert stamp_ns(sampled_tf.header) == 11_000_000_000
    results.append(dict(
        id='dynamic_translation_rotation_interpolation', passed=True,
        input=dict(sample_times_s=[10.0, 12.0], sample_x_m=[0.0, 2.0],
                   sample_yaw_rad=[0.0, math.pi / 2.0], query_s=11.0, point_m=[1.0, 0.0, 0.0]),
        expected_translation_m=[1.0, 0.0, 0.0], actual_translation_m=translation(sampled_tf),
        expected_point_m=sampled_expected, actual_point_m=xyz(sampled_point),
        actual_quaternion_xyzw=quaternion(sampled_tf)))

    # 五、同一个11秒观测如果错误地用Time(0)，得到的是最新12秒的变换。
    # 此处故意比较“正确按采样时刻”与“换成latest”的数值；不把后者冒充有效测量。
    # do_transform_point 输出的 header 来自变换，因此也记录查询返回的时刻以暴露错位。
    latest_tf = dynamic_buffer.lookup_transform('base_dynamic', 'sensor', query_time(0.0))
    latest_point = do_transform_point(measured_point, latest_tf)
    close_vector(xyz(latest_point), [2.0, 1.0, 0.0], 'latest点')
    assert stamp_ns(latest_tf.header) == 12_000_000_000
    difference_m = math.sqrt(sum((a - b) ** 2 for a, b in zip(xyz(latest_point), xyz(sampled_point))))
    assert math.isclose(difference_m, math.sqrt(2.0) - 1.0, rel_tol=0.0, abs_tol=atol)
    assert difference_m > 0.4  # 本固定算例约0.414m；要求明显大于浮点容差。
    results.append(dict(
        id='latest_differs_from_sampling_time', passed=True,
        measurement_stamp_s=11.0, sampled_transform_stamp_ns=stamp_ns(sampled_tf.header),
        latest_transform_stamp_ns=stamp_ns(latest_tf.header),
        expected_latest_point_m=[2.0, 1.0, 0.0], actual_latest_point_m=xyz(latest_point),
        sampled_point_m=xyz(sampled_point), point_difference_m=difference_m,
        expected_point_difference_m=math.sqrt(2.0) - 1.0,
        limitation='latest 不等于当前系统日期时间，也不等于原观测采样时刻；多段链还受共同可用时间约束。'))

    def expect_failure(case_id, source, seconds, exception_class):
        """无阻塞timeout的查询必须立即返回或抛异常；只接受要求的明确异常类型。"""
        try:
            dynamic_buffer.lookup_transform('base_dynamic', source, query_time(seconds))
        except exception_class as error:
            results.append(dict(id=case_id, passed=True, query_s=seconds, source=source,
                                expected_exception=exception_class.__name__,
                                actual_exception=type(error).__name__, message=str(error)))
        else:
            raise AssertionError(case_id + ' 未按预期失败')

    # 六、可用历史只有10~12秒：9秒不是“多等一会就必然有”的历史，13秒尚无新数据。
    # 缺frame是名字不存在；它与已存在frame但查询时刻不在历史范围内是不同错误。
    expect_failure('past_extrapolation', 'sensor', 9.0, ExtrapolationException)
    expect_failure('future_extrapolation', 'sensor', 13.0, ExtrapolationException)
    expect_failure('missing_frame', 'missing_sensor', 11.0, LookupException)

    assert len(results) == 8 and all(item['passed'] for item in results)
    return dict(
        lab='tf_buffer_lab', passed=True, checks=len(results),
        units=dict(position='m', angle='rad', time='s', timestamp='整数ns', quaternion='无量纲，x/y/z/w'),
        absolute_tolerance=atol, relative_tolerance=0.0, results=results,
        scope='固定合成数据的进程内Jazzy Buffer与几何运算；未调用rclpy.init，未创建Node或通信端点。',
        not_verified=['TransformListener与执行器调度', 'DDS或网络传输', '跨进程静态TF晚加入QoS',
                      '阻塞TF等待的超时行为', '完整机器人TF树、外参标定、仿真与硬件'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='将完整结果作为一个JSON对象写到标准输出')
    parser.add_argument('--atol', type=parse_tolerance, default=1.0e-9,
                        help='有限正绝对容差，默认1e-9，上限1e-6；不改变固定数据')
    args = parser.parse_args(argv)  # --help 在此退出，尚未导入任何ROS模块。
    if not __debug__:
        print('本实验依赖数值assert，请使用普通python3，不能启用-O/PYTHONOPTIMIZE。', file=sys.stderr)
        return 2
    try:
        result = run_lab(args.atol)
    except ImportError as error:
        print('缺少ROS依赖：先安装Jazzy相应包并 source /opt/ros/jazzy/setup.bash。' + str(error), file=sys.stderr)
        return 2
    except AssertionError as error:
        print('数值断言失败：' + str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        for item in result['results']:
            print(f"通过 {item['id']}: " + json.dumps(item, ensure_ascii=False, allow_nan=False))
        print(f"全部{result['checks']}项通过，绝对容差={args.atol}。仅进程内计算，未验证ROS通信或硬件。")
    return 0


if __name__ == '__main__':
    sys.exit(main())
