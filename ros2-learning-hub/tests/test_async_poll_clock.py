#!/usr/bin/env python3
"""实际验证教材AsyncPoll在缺失/暂停ROS时钟下仍可推进服务软期限。

输入：已source的Jazzy与examples/runtime_labs/async_poll.py；仅使用教学加法服务。
输出：三个场景的JSON证据；每段外层等待最多5个monotonic秒，失败抛断言。
故障注入：创建真实服务端点但不把服务节点加入执行器，使请求已发现却不应答。
边界：本机单进程，未启动仿真/硬件；不证明任意负载下两秒硬截止或网络故障恢复。
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/runtime_labs/async_poll.py'


def main():
    os.environ.update(ROS_DOMAIN_ID='215', ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',
                      RMW_IMPLEMENTATION='rmw_fastrtps_cpp')
    os.environ.pop('ROS_LOCALHOST_ONLY', None)
    os.environ.pop('ROS_STATIC_PEERS', None)
    import rclpy
    from rclpy.clock import ClockType
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from example_interfaces.srv import AddTwoInts
    from rosgraph_msgs.msg import Clock

    spec = importlib.util.spec_from_file_location('lesson_async_poll', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # 模块导入不启动节点；只实例化下方明确指定的教学类。
    records = []
    for name, paused, reply in [('no-clock-timeout', False, False),
                                ('paused-clock-timeout', True, False),
                                ('paused-clock-response', True, True)]:
        namespace = '/async_clock_' + uuid.uuid4().hex[:10]
        rclpy.init(args=['--ros-args', '-p', 'use_sim_time:=true', '-r', '__ns:='+namespace])
        node = module.AsyncPoll()
        server = Node('controlled_add_server')
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        calls = []

        def handle(request, response):
            calls.append([request.a, request.b])
            response.sum = request.a + request.b
            return response

        service = server.create_service(AddTwoInts, 'add_two_ints', handle)
        clock = server.create_publisher(Clock, '/clock', 10)
        if reply:
            executor.add_node(server)  # 对照组允许服务回调实际执行。
        try:
            if paused:
                deadline = time.monotonic()+5.0
                while node.get_clock().now().nanoseconds == 0:
                    assert time.monotonic() < deadline, '未收到受控/clock'
                    message = Clock()
                    message.clock.sec = 1
                    clock.publish(message)
                    executor.spin_once(timeout_sec=0.05)
                # 此后不再推进clock；固定正值区分“未初始化”与“已暂停”。
            ros_before = node.get_clock().now().nanoseconds
            assert ros_before == (1_000_000_000 if paused else 0)
            assert node.timer.clock.clock_type == ClockType.STEADY_TIME
            deadline = time.monotonic()+5.0
            while node.pending is None:
                assert time.monotonic() < deadline, '未发起加法请求'
                executor.spin_once(timeout_sec=0.05)
            pending = node.pending
            sent_at = node.sent_at
            deadline = time.monotonic()+5.0
            while node.pending is pending:
                assert time.monotonic() < deadline, '请求未有界结束'
                executor.spin_once(timeout_sec=0.05)
            age_s = time.monotonic()-sent_at
            if reply:
                assert pending.done() and pending.result().sum == 12
                assert calls == [[7, 5]]
            else:
                assert not pending.done(), '故障端未调度，不能凭空得到服务结果'
                assert calls == []
                assert 2.0 <= age_s < 4.0, age_s
            assert node.get_clock().now().nanoseconds == ros_before, 'ROS时钟应保持停止'
            records.append(dict(case=name, passed=True, rosTime_ns=ros_before,
                                requestAge_s=round(age_s, 6), serverCallbackCalls=len(calls),
                                requestFutureDone=pending.done(), pendingCleared=node.pending is None))
        finally:
            executor.remove_node(node)
            if reply:
                executor.remove_node(server)
            executor.shutdown(timeout_sec=0.0)
            server.destroy_service(service)
            server.destroy_node()
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
    report = dict(checkedAt='2026-11-07', passed=True, source='examples/runtime_labs/async_poll.py',
                  sourceSha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  testSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), domain=215,
                  discovery='LOCALHOST', rmw='rmw_fastrtps_cpp', results=records,
                  limits=['软件/clock与真实ROS服务的受控实验，不是仿真或硬件验收。',
                          '服务超时是单调经过时间加STEADY轮询的软期限，仍受执行器调度影响。',
                          '本地pending清理不取消远端服务计算；本例只对无副作用整数加法演示重试。'])
    (ROOT/'validation-evidence/async-poll-clock-current-validation.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
