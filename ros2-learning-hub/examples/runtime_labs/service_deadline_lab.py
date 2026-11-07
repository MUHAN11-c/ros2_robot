#!/usr/bin/env python3
"""真实加法服务的发现、超时、迟到应答及本地pending清理实验。

输入：4/8为无量纲整数；所有期限/模拟工作延迟为单调秒，默认独立域221。
输出：每例的发现结果、客户端等待结果、服务端执行事件与清理；失败返回非零。
顺序：父进程探针 → spawn独立服务进程 → 发现/请求/超时 → 继续观察 → 清理。
服务端用有界sleep模拟慢工作，并通过独立IPC报告执行，不向任何设备发命令。
IPC只是观察证据，不是ROS服务自带的反馈/取消通道。两进程的monotonic只在同主机比较。
--help仅用标准库；实际实验需要source ROS2 Jazzy和example_interfaces。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import multiprocessing
import os
from pathlib import Path
import queue
import subprocess
import sys
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[2]


def check(condition, message):
    # 不依赖assert：python -O不能把失败悄悄变成“验证通过”。
    if not condition:
        raise AssertionError(message)


def server_worker(name, delay_s, stop, events):
    """每例仅一个无副作用加法服务；工作后增加的计数只存在于这个测试进程。"""
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from example_interfaces.srv import AddTwoInts
    context = Context()
    node = executor = None
    completed = []
    emitted = 0
    try:
        rclpy.init(args=[], context=context)
        node = Node('delayed_sum_server', context=context)
        executor = SingleThreadedExecutor(context=context)
        executor.add_node(node)

        def respond(request, response):
            events.put(dict(event='server_started', at_s=time.monotonic(), a=request.a, b=request.b))
            time.sleep(delay_s)  # 受控模拟I/O延迟，不能代表计算性能或硬件事务。
            response.sum = request.a + request.b
            completed.append(dict(event='server_completed', at_s=time.monotonic(),
                                  sum=response.sum, executed_count=len(completed)+1))
            events.put(completed[-1])
            return response

        service = node.create_service(AddTwoInts, name, respond)
        events.put(dict(event='server_ready', at_s=time.monotonic(), service=name, delay_s=delay_s))
        # 不在服务回调里查看stop来伪造取消：停止父端等待不等于服务端工作被撤销。
        deadline = time.monotonic()+15.0
        while context.ok() and not stop.is_set() and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.03)
            if len(completed) > emitted:
                # 该次spin返回，服务回调及执行器发送应答路径已结束且未抛异常。
                # 仍不代表客户端已接收或应用已消费应答。
                events.put(dict(event='service_dispatch_returned', at_s=time.monotonic()))
                emitted = len(completed)
        node.destroy_service(service)
    except BaseException:
        events.put(dict(event='server_error', detail=traceback.format_exc()))
        raise
    finally:
        if executor is not None:
            if node is not None:
                executor.remove_node(node)
            executor.shutdown(timeout_sec=0.0)
        if node is not None:
            node.destroy_node()
        if context.ok():
            rclpy.shutdown(context=context)


def run_case(case, original_command=None):
    """单例使用唯一服务名，期限由父进程monotonic推进，不调用嵌套spin辅助函数。"""
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from example_interfaces.srv import AddTwoInts
    started = time.monotonic()
    namespace = '/service_deadline_' + uuid.uuid4().hex[:10]
    name = namespace+'/sum'
    absent = case.endswith('absent')
    original = original_command is not None
    delay_s = 3.0 if original else (0.8 if case.startswith('late') else 0.0)
    spawn = multiprocessing.get_context('spawn')
    events, stop = spawn.Queue(), spawn.Event()
    process = None
    context = Context()
    node = executor = None
    record = dict(case=case, service=name, passed=False, events=[], serverDelay_s=delay_s)

    def drain():
        # 我们控制的worker每例最多数个事件；限制单次读取避免无界生产者拖住监督。
        for _ in range(32):
            try:
                event = events.get_nowait()
            except queue.Empty:
                return
            record['events'].append(event)
            check(event['event'] != 'server_error', event)

    def pump(predicate, timeout_s):
        deadline = time.monotonic()+timeout_s
        while not predicate():
            drain()
            if time.monotonic() >= deadline:
                return False
            executor.spin_once(timeout_sec=min(0.02, max(0.0, deadline-time.monotonic())))
        drain()
        return True

    try:
        rclpy.init(args=[], context=context)
        node = Node('deadline_probe', context=context)
        executor = SingleThreadedExecutor(context=context)
        executor.add_node(node)
        client = node.create_client(AddTwoInts, name)
        if not absent:
            process = spawn.Process(target=server_worker, args=(name, delay_s, stop, events))
            process.start()
            check(pump(lambda: any(e['event']=='server_ready' for e in record['events']), 5.0), '服务进程未准备')
        discovery_at = time.monotonic()
        ready = pump(client.service_is_ready, 0.4 if absent else 3.0)
        record.update(discovered=ready, discoveryElapsed_s=time.monotonic()-discovery_at)
        check(ready != absent, '服务发现与场景不符')
        if original:
            # 运行保留的教学客户端：它们内部发现/应答各2秒，0/1退出码不区分两种失败。
            command = original_command+['--ros-args', '-r', '__ns:='+namespace]
            client_started = time.monotonic()
            cp = subprocess.run(command, capture_output=True, text=True, timeout=8.0)
            record.update(clientExitCode=cp.returncode, clientLog=cp.stdout+cp.stderr,
                          clientFinishedAt_s=time.monotonic(), clientCommand=command,
                          clientElapsed_s=time.monotonic()-client_started, requestSent=not absent,
                          outcome='client_discovery_failed' if absent else 'client_timeout_server_later_completed')
            check(cp.returncode == 1, record['clientLog'])
            check(('was not discovered' if absent else 'response timed out') in record['clientLog'], record['clientLog'])
        elif absent:
            record.update(outcome='discovery_timeout', requestSent=False)
        else:
            request = AddTwoInts.Request()
            request.a, request.b = 4, 8
            sent_at = time.monotonic()
            future = client.call_async(request)
            wait_s = 1.0 if case=='success' else 0.25
            on_time = pump(future.done, wait_s)
            record.update(requestSent=True, sentAt_s=sent_at, responseDeadline_s=wait_s,
                          clientFinishedAt_s=time.monotonic(), responseInWindow=on_time)
            check(on_time == (case=='success'), '应答窗口与受控延迟不符')
            if case=='success':
                check(future.result().sum == 12, '加法响应错误')
                record.update(outcome='success', sum=future.result().sum)
            elif case=='late-kept':
                # 超时只是停止当前等待；保留登记后，继续spin仍能收到迟到应答。
                check(pump(future.done, 3.0), '保留登记后未收到迟到应答')
                check(future.result().sum == 12, '迟到响应数值错误')
                record.update(outcome='timed_out_then_late_response', sum=future.result().sum,
                              lateResponseAt_s=time.monotonic(), futureDone=True)
            else:
                # 清掉本地pending而不取消服务端；继续持有Future用于明确观察。
                client.remove_pending_request(future)
                record['pendingRemovedAt_s'] = time.monotonic()
        if not absent:
            check(pump(lambda: any(e['event']=='service_dispatch_returned' for e in record['events']), 5.0), '未观察到服务端执行完毕')
            completed = [e for e in record['events'] if e['event']=='server_completed']
            check(len(completed)==1 and completed[0]['sum']==12 and completed[0]['executed_count']==1,
                  '一次请求应只在本例服务端完成一次加法')
            if case!='success':
                check(completed[0]['at_s'] > record['clientFinishedAt_s'], '服务端应在客户端结束等待之后完成')
            if case=='late-detached':
                # 给应答路径额外观察窗口；不把这种有限观察扩大成任意网络行为证明。
                observe_end = time.monotonic()+0.25
                pump(lambda: time.monotonic() >= observe_end, 0.4)
                check(not future.done(), '移除pending后不应把迟到应答赋回本Future')
                record.update(outcome='timed_out_pending_removed_server_completed', futureDone=False)
        record['passed'] = True
    finally:
        stop.set()
        if process is not None:
            process.join(timeout=3.0)
            forced = process.is_alive()
            if forced:
                process.terminate()
                process.join(timeout=2.0)
            record['serverCleanup'] = dict(alive=process.is_alive(), exitCode=process.exitcode, forced=forced)
            check(not forced and not process.is_alive() and process.exitcode==0, '测试服务进程未正常清理')
        events.close()
        if executor is not None:
            if node is not None:
                executor.remove_node(node)
            executor.shutdown(timeout_sec=0.0)
        if node is not None:
            node.destroy_node()
        if context.ok():
            rclpy.shutdown(context=context)
        record['totalElapsed_s'] = time.monotonic()-started
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domain', type=int, default=221)
    parser.add_argument('--foundation-prefix', type=Path, help='可选：增加现有基础C++/Python客户端的迟到/缺服务四项检查')
    parser.add_argument('--foundation-source', type=Path, default=ROOT/'foundation-examples')
    parser.add_argument('--output', type=Path, default=ROOT/'validation-evidence/service-deadline-current-validation.json')
    args = parser.parse_args()
    if not 0 <= args.domain <= 232:
        parser.error('教学域须在0..232；默认221需与其他练习隔离')
    os.environ.update(ROS_DOMAIN_ID=str(args.domain), ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',
                      RMW_IMPLEMENTATION='rmw_fastrtps_cpp')
    os.environ.pop('ROS_LOCALHOST_ONLY', None)
    os.environ.pop('ROS_STATIC_PEERS', None)
    cases = [(case, None) for case in ('discovery-absent', 'success', 'late-kept', 'late-detached')]
    if args.foundation_prefix:
        cpp = args.foundation_prefix/'lib/learning_service_cpp/client'
        py = args.foundation_source/'lessons/services/client.py'
        if not cpp.is_file() or not py.is_file():
            parser.error('基础客户端未保存/构建；检查foundation-prefix/source，不跳过断言')
        for language, command in [('cpp', [str(cpp.resolve())]), ('python', [sys.executable, str(py.resolve())])]:
            cases.extend([(language+'-late', command), (language+'-absent', command)])
    report = dict(checkedAt=time.strftime('%Y-%m-%d'), passed=False,
                  sourceSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  domain=args.domain, discovery='LOCALHOST', rmw='rmw_fastrtps_cpp', results=[],
                  limits=['只发送无量纲整数加法与独立IPC观察；无机器人、仿真或设备命令。',
                          '超时清理本地pending不撤销服务端工作；服务本身不提供通用取消。',
                          'monotonic只在同主机两个进程之间比较，软期限不能抢占任意原生阻塞。',
                          '实验退出0表示预期故障断言通过，不表示每个请求业务成功。'])
    if args.foundation_prefix:
        report['foundationInputs'] = [dict(file=str(file.resolve()), sha256=hashlib.sha256(file.read_bytes()).hexdigest())
                                      for file in (cpp, py)]
    try:
        for case, command in cases:
            report['results'].append(run_case(case, command))
        report['rclpyVersion'] = importlib.metadata.version('rclpy')
        report['passed'] = True
    except BaseException:
        report['error'] = traceback.format_exc()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.is_file():
        previous = json.loads(args.output.read_text())
        report['previousAttempts'] = [*previous.pop('previousAttempts', []), previous]
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'], report=str(args.output),
                         cases=[dict(case=r['case'], passed=r['passed'], outcome=r.get('outcome'),
                                     clientExitCode=r.get('clientExitCode')) for r in report['results']]), ensure_ascii=False))
    if not report['passed']:
        print(report['error'], file=sys.stderr)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
