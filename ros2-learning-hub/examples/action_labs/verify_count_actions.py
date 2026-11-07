#!/usr/bin/env python3
"""原Count两语言服务端及独立故障扩展的隔离验收，不启动机器人或仿真。

输入：已source的Jazzy/基础安装、--foundation-prefix、独立--build-root；计数均无量纲。
输出：每例目标UUID、反馈、状态、completed、取消响应、服务端原始日志和SHA验证报告。
所有等待以monotonic秒计。父进程限制worker总时长，worker限制每次发现/应答/结果；
只清理自己创建的PID/进程组，不终止ROS daemon或其他节点。拒绝目标不请求GetResult。
--help只用标准库；--build只构建新learning_count_fault_lab，不构建/改动原基础10包。
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MARKER = 'COUNT_WORKER_RESULT='
CASES = {
    f'{language}_{kind}_{scenario}': (language, kind, scenario)
    for language in ('cpp', 'py')
    for kind, scenarios in (
        ('original', ('busy_cancel_recovery', 'busy_complete_recovery', 'invalid_bounds')),
        ('extended', ('fault_disabled', 'abort_and_recovery')))
    for scenario in scenarios
}


def require(condition, description):
    """显式断言不受python -O影响，失败必须保留上下文，不能静默跳过或重发目标。"""
    if not condition:
        raise AssertionError(description)


def seconds(text):
    value = float(text)
    if not math.isfinite(value) or not 0.0 < value <= 600.0:
        raise argparse.ArgumentTypeError('期限必须是(0,600]内有限秒数')
    return value


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def environment(domain_id):
    env = dict(os.environ)
    env.update(ROS_DOMAIN_ID=str(domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',
               RMW_IMPLEMENTATION='rmw_fastrtps_cpp', PYTHONUNBUFFERED='1',
               PYTHONDONTWRITEBYTECODE='1', RCUTILS_COLORIZED_OUTPUT='0',
               RCUTILS_LOGGING_BUFFERED_STREAM='0')
    env.pop('ROS_STATIC_PEERS', None)
    env.pop('ROS_LOCALHOST_ONLY', None)
    return env


def server_events(text):
    events = []
    for line in text.splitlines():
        if 'COUNT_LAB_EVENT ' in line:
            try:
                events.append(json.loads(line.split('COUNT_LAB_EVENT ', 1)[1]))
            except ValueError as error:
                events.append(dict(event='unparsed_log', raw=line, parseError=str(error)))
    return events


def stop_own_group(process):
    """停止本程序start_new_session创建的组；处理清理期间再次Ctrl+C，保留原始输出。"""
    signals_sent = []
    for sig, wait_s in ((signal.SIGINT, 5.0), (signal.SIGTERM, 2.0), (signal.SIGKILL, 2.0)):
        signals_sent.append(sig.name)
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        try:
            # worker收到组INT后要先等待server自己的首次INT清理，不能被父级2秒窗口抢先TERM。
            output, _ = process.communicate(timeout=wait_s)
            return output, signals_sent
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            # 每次等待仍有上限；第二次Ctrl+C不会跳过剩余的强制清理阶段。
            continue
    output, _ = process.communicate(timeout=1.0)
    return output, signals_sent


class Children:
    """server继承worker的进程组；父进程仍能在worker挂起时清理整组自建子进程。"""
    def __init__(self, directory, env):
        self.directory, self.env, self.items = Path(directory), env, []

    def start(self, command):
        path = self.directory / 'server.log'
        stream = path.open('w')
        process = subprocess.Popen(command, stdout=stream, stderr=stream, env=self.env)
        item = dict(command=command, path=path, stream=stream, process=process)
        self.items.append(item)
        return item

    @staticmethod
    def text(item):
        item['stream'].flush()
        return item['path'].read_text(errors='replace')

    def close(self, group_sigint_already_sent=False):
        records = []
        for item in reversed(self.items):
            process, signals = item['process'], []
            initial_wait_s = 0.0
            if group_sigint_already_sent and process.poll() is None:
                # 父driver的killpg已同时给worker和server发送INT。此时马上再send_signal(INT)
                # 会把一次Ctrl+C变成双INT，打断Python server正在进行的executor.shutdown/join。
                initial_wait_s = 2.0
                try:
                    process.wait(timeout=initial_wait_s)
                except subprocess.TimeoutExpired:
                    pass
            sequence = ((signal.SIGTERM, signal.SIGKILL) if group_sigint_already_sent else
                        (signal.SIGINT, signal.SIGTERM, signal.SIGKILL))
            for sig in sequence:
                if process.poll() is not None:
                    break
                try:
                    process.send_signal(sig)
                except ProcessLookupError:
                    pass
                signals.append(sig.name)
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    pass
            log = self.text(item)
            records.append(dict(command=item['command'], pid=process.pid,
                                exitCode=process.poll(), signalsSent=signals,
                                priorGroupSigint=group_sigint_already_sent,
                                initialWaitForAlreadySignaledServer_s=initial_wait_s,
                                reaped=process.poll() is not None, log=log,
                                logSha256=hashlib.sha256(log.encode()).hexdigest(),
                                events=server_events(log)))
            item['stream'].close()
        return list(reversed(records))


@contextmanager
def probe(namespace, domain_id):
    """仅worker加载ROS。单线程客户端只做短回调，不在回调里同步等待缺失的协议事件。"""
    from action_msgs.msg import GoalStatus, GoalStatusArray
    from learning_count_interfaces.action import Count
    from rclpy.action import ActionClient
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import qos_profile_action_status_default
    from unique_identifier_msgs.msg import UUID

    names = {GoalStatus.STATUS_UNKNOWN: 'UNKNOWN', GoalStatus.STATUS_ACCEPTED: 'ACCEPTED',
             GoalStatus.STATUS_EXECUTING: 'EXECUTING', GoalStatus.STATUS_CANCELING: 'CANCELING',
             GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED', GoalStatus.STATUS_CANCELED: 'CANCELED',
             GoalStatus.STATUS_ABORTED: 'ABORTED'}
    require(set(Count.Result.get_fields_and_field_types()) == {'completed'}, 'Count.Result只应包含completed')
    context = Context()
    context.init(args=[], domain_id=domain_id, initialize_logging=False)
    node = executor = client = None

    class Probe:
        def __init__(self):
            self.start = time.monotonic()
            self.goals, self.handles, self.results = {}, {}, {}
            self.cleanup = {}

        def now(self):
            return round(time.monotonic() - self.start, 6)

        def feedback(self, message):
            key = bytes(message.goal_id.uuid).hex()
            if key in self.goals:
                self.goals[key]['feedback'].append(dict(current=int(message.feedback.current), at_s=self.now()))

        def status(self, message):
            for item in message.status_list:
                key = bytes(item.goal_info.goal_id.uuid).hex()
                if key in self.goals:
                    events = self.goals[key]['statusEvents']
                    if not events or events[-1]['code'] != item.status:
                        events.append(dict(code=int(item.status), name=names[item.status], at_s=self.now()))

        def wait(self, predicate, limit_s, description):
            deadline = time.monotonic() + limit_s
            while context.ok():
                if predicate():
                    return
                remaining = deadline - time.monotonic()
                require(remaining > 0.0, f'{description} 超过{limit_s}个单调秒')
                executor.spin_once(timeout_sec=min(0.02, remaining))
            raise RuntimeError(description + '期间Context关闭')

        def drain(self, duration_s=0.08):
            deadline = time.monotonic() + duration_s
            while context.ok() and time.monotonic() < deadline:
                executor.spin_once(timeout_sec=min(0.02, max(0.0, deadline - time.monotonic())))

        def send(self, target, label):
            # 在发送前保存非零UUID。每次只提交一次；不能用重试掩盖busy释放失败。
            goal_uuid = UUID(uuid=list(uuid.uuid4().bytes))
            key = bytes(goal_uuid.uuid).hex()
            record = dict(uuid=key, label=label, target=target, submittedAt_s=self.now(),
                          accepted=None, feedback=[], statusEvents=[], resultRequested=False,
                          result=None, terminalStatus=None, cancelResponse=None)
            self.goals[key] = record
            future = client.send_goal_async(Count.Goal(target=target), self.feedback, goal_uuid=goal_uuid)
            self.wait(future.done, 4.0, '目标应答')
            handle = future.result()
            require(handle is not None, '目标应答缺handle')
            record.update(accepted=bool(handle.accepted), responseAt_s=self.now())
            if handle.accepted:
                self.handles[key] = handle
                self.results[key] = handle.get_result_async()
                record['resultRequested'] = True
            return record

        def rejected(self, record):
            require(record['accepted'] is False, f'应拒绝目标：{record}')
            self.drain()
            require(not record['resultRequested'] and record['result'] is None, '拒绝不能伪造执行Result')
            require(not record['feedback'] and not record['statusEvents'], '拒绝目标不应出现执行反馈/GoalStatus')
            # ROS2没有REJECTED GoalStatus枚举；这里只记录SendGoal accepted=false。

        def first_feedback(self, record):
            self.wait(lambda: len(record['feedback']) >= 1, 4.0, '首条反馈')
            require(not self.results[record['uuid']].done(), '发送busy目标前首目标必须仍在执行')

        def cancel(self, record):
            future = self.handles[record['uuid']].cancel_goal_async()
            self.wait(future.done, 3.0, '取消应答')
            response = future.result()
            ids = [bytes(g.goal_id.uuid).hex() for g in response.goals_canceling]
            record['cancelResponse'] = dict(returnCode=int(response.return_code), goalsCanceling=ids,
                                            at_s=self.now())
            require(response.return_code == 0 and record['uuid'] in ids, '取消应答须明确包含本UUID')
            # 取消受理仍不是CANCELED。这个实验保留足够计数余量，再独立检查最终结果。

        def terminal(self, record, expected, completed=None):
            future = self.results[record['uuid']]
            self.wait(future.done, 12.0, '执行结果')
            response = future.result()
            require(response is not None, '结果Future没有响应')
            status = names[response.status]
            record.update(terminalStatus=status, terminalCode=int(response.status),
                          result=dict(completed=int(response.result.completed)), resultAt_s=self.now())
            require(status == expected, f'期望{expected}，实际{status}')
            if completed is not None:
                require(record['result']['completed'] == completed, f'completed应为{completed}')
            self.wait(lambda: any(e['name'] == status for e in record['statusEvents']), 2.0, '同UUID终态状态话题')
            self.drain()  # 让已排队反馈完成，再检查递增与最后一步。
            values = [e['current'] for e in record['feedback']]
            require(values == list(range(1, record['result']['completed'] + 1)), f'反馈与completed不符：{record}')

    obj = Probe()
    try:
        node = Node('count_action_probe', namespace=namespace, context=context,
                    enable_rosout=False, start_parameter_services=False)
        executor = SingleThreadedExecutor(context=context)
        executor.add_node(node)
        client = ActionClient(node, Count, 'count')
        node.create_subscription(GoalStatusArray, 'count/_action/status', obj.status,
                                 qos_profile_action_status_default)
        obj.wait(client.server_is_ready, 8.0, 'Action服务发现')
        yield obj
    finally:
        if client is not None:
            client.destroy()
        if executor is not None:
            if node is not None:
                executor.remove_node(node)
            executor.shutdown(timeout_sec=0.0)
        if node is not None:
            node.destroy_node()
        if context.ok():
            context.shutdown()
        obj.cleanup = dict(clientDestroyed=client is not None, nodeDestroyed=node is not None,
                           contextShutdown=not context.ok())


def worker(args):
    language, kind, scenario = CASES[args.worker]
    namespace = f'/count_lab_{os.getpid()}_{args.worker}'
    env = environment(args.domain_id)
    os.environ.update(env)  # 在任何ROS导入前固定本worker的发现环境。
    report = dict(id=args.worker, language=language, implementation=kind, scenario=scenario,
                  namespace=namespace, passed=False, goals=[], serverProcesses=[], error=None)
    probe_obj = None
    interrupted_in_worker = False
    with tempfile.TemporaryDirectory(prefix='count-action-') as directory:
        env['ROS_LOG_DIR'] = str(Path(directory) / 'ros-log')
        children = Children(directory, env)
        if kind == 'original':
            command = ([str(args.foundation_prefix / 'lib/learning_action_cpp/server')] if language == 'cpp'
                       else [sys.executable, str(ROOT / 'foundation-examples/lessons/actions/server.py')])
        else:
            name = 'count_fault_cpp' if language == 'cpp' else 'count_fault_py'
            command = [str(args.fault_prefix / 'lib/learning_count_fault_lab' / name)]
        command += ['--ros-args', '-r', f'__ns:={namespace}']
        if scenario == 'abort_and_recovery':
            command += ['-p', 'abort_after:=6', '-p', 'step_seconds:=0.2']
        server = children.start(command)
        try:
            with probe(namespace, args.domain_id) as p:
                probe_obj = p
                if scenario == 'invalid_bounds':
                    for target in (0, 21):
                        p.rejected(p.send(target, f'invalid_{target}'))
                elif scenario == 'fault_disabled':
                    first = p.send(8, 'default_fault_disabled')
                    require(first['accepted'], '默认无故障目标应接受')
                    p.terminal(first, 'SUCCEEDED', 8)
                    report['primaryUuid'] = first['uuid']
                else:
                    first_target = 12 if scenario == 'busy_cancel_recovery' else (4 if kind == 'original' else 10)
                    first = p.send(first_target, 'first_long')
                    require(first['accepted'], '首目标应接受')
                    p.first_feedback(first)
                    second = p.send(3, 'second_legal_while_busy')
                    p.rejected(second)
                    report['busySubmissionCondition'] = '首目标已有反馈、结果Future未完成；第二目标target=3合法'
                    if scenario == 'busy_cancel_recovery':
                        p.cancel(first)
                        p.terminal(first, 'CANCELED')
                        require(1 <= first['result']['completed'] < 12, '中途取消应只完成部分计数')
                    elif scenario == 'busy_complete_recovery':
                        p.terminal(first, 'SUCCEEDED', 4)
                    else:
                        p.terminal(first, 'ABORTED', 6)
                    recovery = p.send(2, 'recovery_once')
                    require(recovery['accepted'], '首目标终态后新合法目标应接受；不自动重试')
                    p.terminal(recovery, 'SUCCEEDED', 2)
                    report.update(primaryUuid=first['uuid'], busyRejectedUuid=second['uuid'],
                                  recoveryUuid=recovery['uuid'])

                # 只从服务端日志独立验证故障原因；绝不向只有completed的Result编造reason字段。
                events = server_events(children.text(server))
                if kind == 'extended':
                    if scenario == 'fault_disabled':
                        require(any(e['event'] == 'ready' and e['abort_after'] == 0 for e in events), '默认abort_after须为0')
                    else:
                        first_id = report['primaryUuid']
                        proof = [e for e in events if e['event'] == 'ABORTED' and e['goal_uuid'] == first_id]
                        require(len(proof) == 1 and proof[0]['completed'] == 6 and
                                proof[0]['reason'] == 'configured_abort_after_step', '缺少独立ABORTED原因日志')
                        require(any(e['event'] == 'goal_rejected' and e['target'] == 3 and e['reason'] == 'busy'
                                    for e in events), '缺少扩展服务端busy日志')
                        report['abortReasonLog'] = proof[0]
                        report['rejectionLogCorrelation'] = (
                            'C++公开goal回调含UUID，可精确关联' if language == 'cpp' else
                            'Python公开goal回调不含UUID；隔离命名空间内唯一target=3拒绝按顺序关联，日志UUID为null')
                else:
                    report['reasonBoundary'] = '原服务端没有结构化原因日志；busy由合法目标和已执行首目标的受控条件推断，Result无reason字段。'
                report['passed'] = True
        except (Exception, KeyboardInterrupt) as error:
            interrupted_in_worker = isinstance(error, KeyboardInterrupt)
            report.update(error=repr(error), traceback=traceback.format_exc())
        finally:
            if probe_obj is not None:
                report['goals'] = list(probe_obj.goals.values())
                report['probeCleanup'] = probe_obj.cleanup
            report['serverProcesses'] = children.close(group_sigint_already_sent=interrupted_in_worker)
            if not all(s['reaped'] for s in report['serverProcesses']):
                report.update(passed=False, error='未能清理本worker创建的服务端')
    print(MARKER + json.dumps(report, ensure_ascii=False, allow_nan=False), flush=True)
    return 0 if report['passed'] else 1


def sources():
    paths = sorted(p for p in HERE.rglob('*') if p.is_file() and p.suffix in ('.py', '.cpp', '.xml', '.txt', '.md'))
    paths += [ROOT / 'foundation-examples/lessons/actions/server.py',
              ROOT / 'foundation-examples/src/learning_action_cpp/src/server.cpp',
              ROOT / 'foundation-examples/src/learning_count_interfaces/action/Count.action']
    return [dict(path=p.relative_to(ROOT).as_posix(), sha256=file_sha(p)) for p in paths]


def teaching_table(cases):
    rows = []
    for case in cases:
        goals = {g['uuid']: g for g in case['goals']}
        first = goals.get(case.get('primaryUuid'))
        recovery = goals.get(case.get('recoveryUuid'))
        first_text = (f"{first['terminalStatus']} / {first['result']['completed']}" if first and first['result'] else '无执行Result')
        rejected = [str(g['target']) for g in goals.values() if g['accepted'] is False]
        rejection = ('target=' + '/'.join(rejected) + '；accepted=false（无Result）') if rejected else '本例未安排拒绝'
        restored = (f"{recovery['terminalStatus']} / {recovery['result']['completed']}" if recovery else '本例未安排恢复目标')
        rows.append([f"{case['language']} {case['implementation']} / {case['scenario']}",
                     first_text, rejection, restored])
    return dict(caption='实际隔离Count协议结果；completed无量纲，拒绝不是执行终态；不表示硬件停车。',
                columns=['实现/主场景', '首目标 status / completed', 'busy/非法拒绝', '后续恢复 status / completed'], rows=rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--foundation-prefix', type=Path,
                        default=Path(os.environ.get('FOUNDATION_INSTALL_PREFIX', ROOT / 'foundation-examples/install')))
    parser.add_argument('--build-root', type=Path, default=Path('/tmp/ros2-hub-count-action-lab'))
    parser.add_argument('--fault-prefix', type=Path, default=None)
    parser.add_argument('--build', action='store_true', help='只colcon构建新增包；要求已source基础接口安装')
    parser.add_argument('--domain-id', type=int, default=227)
    parser.add_argument('--case', action='append', choices=tuple(CASES), default=[])
    parser.add_argument('--case-timeout', type=seconds, default=25.0, help='每worker父进程保护秒数，默认25')
    parser.add_argument('--total-timeout', type=seconds, default=180.0, help='全部worker总保护秒数，默认180')
    parser.add_argument('--output', type=Path, default=Path('/tmp/count-action-rerun.json'),
                        help='报告另存路径，默认/tmp/count-action-rerun.json，不覆盖教材绑定证据')
    parser.add_argument('--worker', choices=tuple(CASES), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)  # --help无需ROS、已构建接口或本机临时目录。
    if not 0 <= args.domain_id <= 232:
        parser.error('domain-id必须在0..232，选择无其他应用的独立域')
    args.foundation_prefix = args.foundation_prefix.resolve()
    args.build_root = args.build_root.resolve()
    args.fault_prefix = (args.fault_prefix or args.build_root / 'install').resolve()
    if args.worker:
        return worker(args)

    before = sources()
    report = dict(validatedAt=datetime.now(timezone.utc).isoformat(), passed=False,
                  sourceHashes=before, cases=[], build=None, teachingTables=[],
                  environment=dict(domainId=args.domain_id, discoveryRange='LOCALHOST', rmw='rmw_fastrtps_cpp'),
                  parentProtection=dict(caseTimeout_s=args.case_timeout, totalTimeout_s=args.total_timeout),
                  originalFoundationRebuilt=False, originalSourcesUnchanged=None)
    current_process = None
    try:
        if args.build:
            command = ['colcon', '--log-base', str(args.build_root / 'log'), 'build',
                       '--base-paths', str(HERE / 'learning_count_fault_lab'),
                       '--build-base', str(args.build_root / 'build'), '--install-base', str(args.fault_prefix),
                       '--merge-install', '--symlink-install', '--packages-select', 'learning_count_fault_lab']
            build = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=100.0)
            report['build'] = dict(command=command, cwd=str(ROOT), exitCode=build.returncode,
                                   stdout=build.stdout, stderr=build.stderr)
            require(build.returncode == 0, '新增包构建失败：' + build.stdout + build.stderr)
        artifacts = [args.foundation_prefix / 'lib/learning_action_cpp/server',
                     ROOT / 'foundation-examples/lessons/actions/server.py',
                     args.fault_prefix / 'lib/learning_count_fault_lab/count_fault_cpp',
                     args.fault_prefix / 'lib/learning_count_fault_lab/count_fault_py', Path(sys.executable)]
        report['artifacts'] = [dict(path=str(p), sha256=file_sha(p), bytes=p.stat().st_size,
                                    kind='Python source/installed script' if p.suffix == '.py' or p.name == 'count_fault_py' else 'executable')
                               for p in artifacts]
        report['execution'] = dict(command=[sys.executable, *sys.argv], pythonVersion=platform.python_version(),
                                    foundationPrefix=str(args.foundation_prefix), faultPrefix=str(args.fault_prefix))
        versions = subprocess.run(['dpkg-query', '-W', 'ros-jazzy-rclpy', 'ros-jazzy-rclcpp',
                                   'ros-jazzy-rclcpp-action', 'ros-jazzy-action-msgs'], capture_output=True, text=True)
        report['packageVersions'] = dict(line.split('\t', 1) for line in versions.stdout.splitlines() if '\t' in line)
        started = time.monotonic()
        for name in args.case or CASES:
            remaining = args.total_timeout - (time.monotonic() - started)
            require(remaining > 0, '总保护期限到达')
            command = [sys.executable, str(Path(__file__).resolve()), '--worker', name,
                       '--foundation-prefix', str(args.foundation_prefix), '--fault-prefix', str(args.fault_prefix),
                       '--domain-id', str(args.domain_id)]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, env=environment(args.domain_id), start_new_session=True)
            current_process = process
            signals_sent = []
            protection_reason = None
            try:
                output, _ = process.communicate(timeout=min(args.case_timeout, remaining))
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
                protection_reason = ('parent_keyboard_interrupt' if isinstance(error, KeyboardInterrupt)
                                     else 'parent_worker_timeout')
                output, signals_sent = stop_own_group(process)
            matches = [line[len(MARKER):] for line in output.splitlines() if line.startswith(MARKER)]
            case = json.loads(matches[-1]) if matches else dict(id=name, passed=False, goals=[], error='worker没有完整结果')
            case['worker'] = dict(command=command, pid=process.pid, exitCode=process.returncode,
                                  parentSignals=signals_sent, reaped=process.poll() is not None,
                                  protectionReason=protection_reason,
                                  extraOutput='\n'.join(line for line in output.splitlines() if not line.startswith(MARKER)))
            if signals_sent:
                case.update(passed=False, error=f'{protection_reason}；不能作为业务终态')
            report['cases'].append(case)
            require(not signals_sent, f'{name}触发父进程保护({protection_reason})：{case}')
            print(f"{name}: {'通过' if case['passed'] and process.returncode == 0 else '失败'}", flush=True)
            require(case['passed'] and process.returncode == 0, f'{name}失败：{case.get("error")}')
            current_process = None
        report['passed'] = True
    except (Exception, KeyboardInterrupt) as error:
        report.update(error=repr(error), traceback=traceback.format_exc())
    finally:
        # 覆盖communicate以外的意外退出窗口；不能因父进程Ctrl+C留下独立会话的worker。
        if current_process is not None and current_process.poll() is None:
            output, signals_sent = stop_own_group(current_process)
            report['emergencyWorkerCleanup'] = dict(pid=current_process.pid,
                                                    signalsSent=signals_sent,
                                                    exitCode=current_process.poll(), output=output)
        report['originalSourcesUnchanged'] = all(file_sha(ROOT / item['path']) == item['sha256'] for item in before)
        report['teachingTables'] = [teaching_table(report['cases'])]
        report['summary'] = dict(mainCases=len(report['cases']), passedCases=sum(c['passed'] for c in report['cases']),
                                goals=sum(len(c['goals']) for c in report['cases']),
                                serverProcessesReaped=all(s['reaped'] for c in report['cases'] for s in c.get('serverProcesses', [])),
                                workersReaped=all(c['worker']['reaped'] for c in report['cases']))
        report['limits'] = [
            '所有Count目标、故障和恢复均为纯计数协议实验，没有机器人、仿真或物理停车验证。',
            'SendGoal拒绝只有accepted=false，没有REJECTED GoalStatus或执行Result。',
            '取消受理、最终状态和物理停止不同；中途取消场景保留足够目标余量，未泛化为取消竞态总会CANCELED。',
            'Result只有completed；扩展故障原因独立保存在UUID服务端日志，不是新增Result字段。',
            '源码与临时二进制SHA分别记录；原基础包复用已有安装，没有在本轮重编。',
            '本轮取消业务终态实测只针对原C++/Python服务端；扩展取消路径未加入十组主场景，不能当已验证。']
        report['teachingValidation'] = (
            f"本轮实际构建独立故障扩展包，执行{len(report['cases'])}组隔离Count协议场景。"
            '原C++/Python服务端保持原样；记录UUID、反馈、状态、completed、取消响应和清理。'
            '扩展故障默认关闭，显式abort_after=6时按独立服务端日志核对原因。'
            '只验证软件Action协议，不涉及仿真、硬件或物理停车；是否通过以各case及passed字段为准。')
        command = [sys.executable, 'examples/action_labs/verify_count_actions.py', '--build',
                   '--foundation-prefix', str(args.foundation_prefix), '--build-root', str(args.build_root),
                   '--fault-prefix', str(args.fault_prefix), '--domain-id', str(args.domain_id),
                   '--case-timeout', str(args.case_timeout), '--total-timeout', str(args.total_timeout),
                   '--output', '/tmp/count-action-rerun.json']
        for selected in args.case:
            command += ['--case', selected]
        report['teachingCommand'] = (
            '# 从ros2-learning-hub目录执行；基础接口及原C++server须已按基础章构建。\n'
            'source /opt/ros/jazzy/setup.bash\nsource ' + shlex.quote(str(args.foundation_prefix / 'setup.bash')) +
            '\n' + shlex.join(command))
        report['teachingCommandNote'] = (
            'build-root/fault-prefix为本例专属/tmp产物，foundation-prefix为已存在的基础安装；换机需先重建基础依赖并替换路径。'
            '内部发现/目标/取消/结果使用monotonic软期限，父进程另有限制；清理只针对自建PID/进程组。'
            '拒绝没有执行Result，取消受理不保证所有竞态最终CANCELED。')
        if args.output.exists():
            try:
                previous = json.loads(args.output.read_text())
                report['priorAttempts'] = previous.get('priorAttempts', []) + [
                    dict(validatedAt=previous.get('validatedAt'), passed=previous.get('passed'),
                         summary=previous.get('summary'), error=previous.get('error'),
                         cases=previous.get('cases'), sourceHashes=previous.get('sourceHashes'),
                         build=previous.get('build'), lifecycleValidation=previous.get('lifecycleValidation'),
                         lifecycleReviewNote=(
                             '旧生命周期检查只证明进程消失；原始记录保留。若父组INT与worker追加INT同时出现，'
                             '会打断server首次shutdown/join，不能当成正常单次INT关闭证据。'
                             if previous.get('lifecycleValidation') else None))]
            except (ValueError, OSError):
                report['priorAttempts'] = [{'note': '原输出不能解析；未将其作为通过证据'}]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        print('报告：' + str(args.output), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
