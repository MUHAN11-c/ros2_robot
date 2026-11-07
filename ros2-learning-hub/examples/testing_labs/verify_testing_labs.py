#!/usr/bin/env python3
"""独立ament测试包的真实build/test/test-result与失败/中断验收。

--help只使用标准库。默认报告写/tmp，构建也在专属/tmp目录，不覆盖教材绑定证据。
3个CTest注册项对应4个gtest、7个pytest、2个launch unittest，共13个细分JUnit案例。
受控就绪故障必须产生实际失败XML；默认colcon退出0不能替代XML数量/失败检查。
全部等待以monotonic秒计，Linux /proc和子收割器只跟踪/回收本驱动创建的进程树。
"""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKAGE = 'learning_testing_lab'
EXPECTED = {'test_wheel_math.gtest.xml': 4, 'test_rate_reader.xunit.xml': 7,
            'test_wheel_launch.xunit.xml': 2}


def require(condition, message):
    if not condition:
        raise AssertionError(message)  # 不依赖assert关键字，python -O不会悄悄关闭验收。


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def process_info(pid):
    try:
        raw = Path(f'/proc/{pid}/stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        return dict(pid=pid, state=fields[0], ppid=int(fields[1]), pgid=int(fields[2]),
                    session=int(fields[3]), startTicks=int(fields[19]),
                    command=[x.decode(errors='replace') for x in Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0') if x])
    except (FileNotFoundError, ProcessLookupError):
        return None


def child_pids(pid):
    try:
        return [int(v) for v in Path(f'/proc/{pid}/task/{pid}/children').read_text().split()]
    except FileNotFoundError:
        return []


def isolated_environment(domain_id):
    env = dict(os.environ)
    env.update(ROS_DOMAIN_ID=str(domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',
               RMW_IMPLEMENTATION='rmw_fastrtps_cpp', PYTHONUNBUFFERED='1',
               PYTHONDONTWRITEBYTECODE='1', RCUTILS_COLORIZED_OUTPUT='0')
    env.pop('ROS_LOCALHOST_ONLY', None)
    env.pop('ROS_STATIC_PEERS', None)
    return env


def with_setup(env, setup):
    # shell只接收固定代码和位置参数，路径不拼接成shell代码；返回环境仅留在内存，不写凭据。
    result = subprocess.run(['bash', '-c', 'source "$1"\nenv -0', 'testing-env', str(setup)],
                            env=env, capture_output=True, check=True)
    return dict(entry.split('=', 1) for entry in result.stdout.decode().split('\0') if '=' in entry)


class Commands:
    """每条命令独立会话。/proc按父子关系登记身份，必要时只给仍匹配startTicks的自建PID发信号。"""
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.records = []
        # Linux子收割器只影响当前驱动，使被中断的colcon/launch孤儿可由本驱动waitpid回收。
        require(sys.platform.startswith('linux'), '该进程清理夹具需要Linux /proc')
        libc = ctypes.CDLL(None, use_errno=True)
        require(libc.prctl(36, 1, 0, 0, 0) == 0, 'PR_SET_CHILD_SUBREAPER失败')

    @staticmethod
    def observe(root_pid, tracked):
        queue = [root_pid] + list(tracked)
        visited = set()
        while queue:
            pid = queue.pop()
            if pid in visited:
                continue
            visited.add(pid)
            info = process_info(pid)
            if info is None:
                continue
            if pid in tracked and tracked[pid]['startTicks'] != info['startTicks']:
                continue  # PID已复用，不碰无关进程。
            tracked.setdefault(pid, info)
            queue.extend(child_pids(pid))

    @staticmethod
    def reap_and_remaining(process, tracked):
        process.poll()  # 根Popen由它自己wait，避免与waitpid竞争。
        remaining = []
        for pid, identity in tracked.items():
            if pid != process.pid:
                try:
                    os.waitpid(pid, os.WNOHANG)  # 只收割已被本驱动接管的自建后代。
                except ChildProcessError:
                    pass
            info = process_info(pid)
            if info and info['startTicks'] == identity['startTicks']:
                remaining.append(info)
        return remaining

    def run(self, command, env, label, timeout_s=80.0):
        path = self.root / f'{len(self.records):02d}-{label}.log'
        tracked, signals_sent = {}, []
        interrupted = timed_out = False
        start = time.monotonic()
        stream = path.open('w')
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream, stderr=stream,
                                   start_new_session=True)
        try:
            while process.poll() is None:
                self.observe(process.pid, tracked)
                if time.monotonic() - start >= timeout_s:
                    timed_out = True
                    break
                time.sleep(0.03)
        except KeyboardInterrupt:
            interrupted = True
        finally:
            self.observe(process.pid, tracked)
            if process.poll() is None:
                # 先只向colcon/命令根PID发一次INT，让其测试框架关闭fixture；不向同组重复INT。
                process.send_signal(signal.SIGINT)
                signals_sent.append(dict(pid=process.pid, signal='SIGINT', reason='interrupt_or_timeout'))
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                self.observe(process.pid, tracked)
                if not self.reap_and_remaining(process, tracked):
                    break
                time.sleep(0.03)
            # launch子进程可能另建会话，因此以本次登记的PID身份为依据，而不误杀其他组。
            for sig in (signal.SIGTERM, signal.SIGKILL):
                remaining = self.reap_and_remaining(process, tracked)
                if not remaining:
                    break
                for info in reversed(remaining):
                    try:
                        os.kill(info['pid'], sig)
                        signals_sent.append(dict(pid=info['pid'], signal=sig.name, reason='owned_descendant_fallback'))
                    except ProcessLookupError:
                        pass
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline and self.reap_and_remaining(process, tracked):
                    time.sleep(0.03)
            process.wait(timeout=1.0)
            stream.close()
        remaining = self.reap_and_remaining(process, tracked)
        record = dict(label=label, command=command, cwd=str(ROOT), exitCode=process.returncode,
                      elapsed_s=round(time.monotonic() - start, 6), interrupted=interrupted, timedOut=timed_out,
                      rootPid=process.pid, ownedProcesses=list(tracked.values()), signalsSent=signals_sent,
                      remainingProcesses=remaining, allOwnedProcessesReaped=not remaining,
                      log=path.read_text(errors='replace'))
        record['logSha256'] = hashlib.sha256(record['log'].encode()).hexdigest()
        self.records.append(record)
        return record


def test_command(root, strict=False):
    command = ['colcon', '--log-base', str(root / 'log-test'), 'test',
               '--base-paths', str(HERE / PACKAGE), '--build-base', str(root / 'build'),
               '--install-base', str(root / 'install'), '--merge-install', '--packages-select', PACKAGE,
               '--executor', 'sequential', '--event-handlers', 'console_direct+']
    if strict:
        command.append('--return-code-on-test-failure')
    return command


def xml_snapshot(root):
    directory = root / 'build' / PACKAGE / 'test_results' / PACKAGE
    files = []
    for name, expected_count in EXPECTED.items():
        path = directory / name
        require(path.is_file(), '缺少预期JUnit结果：' + str(path))
        text = path.read_text()
        xml = ET.fromstring(text)
        cases = list(xml.iter('testcase'))
        require(len(cases) == expected_count, f'{name}应有{expected_count}例，实际{len(cases)}；不能接受零测试')
        failures = sum(c.find('failure') is not None for c in cases)
        errors = sum(c.find('error') is not None for c in cases)
        skipped = sum(c.find('skipped') is not None for c in cases)
        files.append(dict(path=str(path), name=name, expectedCases=expected_count, cases=len(cases),
                          failures=failures, errors=errors, skipped=skipped,
                          testcaseNames=[c.attrib.get('name') for c in cases],
                          sha256=sha(path), xml=text))
    return dict(files=files, junitCases=sum(f['cases'] for f in files),
                failures=sum(f['failures'] for f in files), errors=sum(f['errors'] for f in files),
                skipped=sum(f['skipped'] for f in files))


def phase(commands, root, env, label, strict, expected_failures):
    for name in EXPECTED:
        (root / 'build' / PACKAGE / 'test_results' / PACKAGE / name).unlink(missing_ok=True)
    test = commands.run(test_command(root, strict), env, label + '-test', 60.0)
    result = commands.run(['colcon', '--log-base', str(root / 'log-result'),
                           'test-result', '--test-result-base', str(root / 'build'), '--verbose'],
                          env, label + '-result', 15.0)
    summary = re.search(r'Summary: (\d+) tests, (\d+) errors, (\d+) failures?, (\d+) skipped', result['log'])
    require(summary is not None, '无法解析本机test-result汇总，应核读原始输出')
    cli_summary = dict(zip(('tests', 'errors', 'failures', 'skipped'), map(int, summary.groups())))
    snapshot = xml_snapshot(root)
    expected_test_exit = 1 if strict and expected_failures else 0
    require(test['exitCode'] == expected_test_exit, f'{label}的colcon test退出码与安装版本合同不符')
    require(result['exitCode'] == (1 if expected_failures else 0), f'{label}的test-result退出码不符')
    require(snapshot['junitCases'] == 13 and snapshot['failures'] == expected_failures and
            snapshot['errors'] == snapshot['skipped'] == 0, f'{label}的XML数量或失败分类不符')
    require(test['allOwnedProcessesReaped'] and result['allOwnedProcessesReaped'], '测试fixture留下进程')
    launch_log = root / 'build' / PACKAGE / 'launch_test/test_wheel_launch.txt'
    observation = []
    for line in launch_log.read_text(errors='replace').splitlines():
        if 'TESTING_LAB_OBSERVATION ' in line:
            observation.append(json.loads(line.split('TESTING_LAB_OBSERVATION ', 1)[1]))
    if expected_failures == 0:
        require(observation and len(observation[-1]['actual_rad_s']) == 2 and
                all(math.isclose(v, e, rel_tol=0.0, abs_tol=1e-12)
                    for v, e in zip(observation[-1]['actual_rad_s'], [5.0, 7.0])),
                '缺少真实话题输入输出证据')
    else:
        require(not observation, '故障应在业务ready前失败，不能假装完成话题验证')
    return dict(label=label, strictFlag=strict, expectedFailures=expected_failures,
                test=test, testResult=result, testResultCliSummary=cli_summary, xml=snapshot, observations=observation,
                acceptance=('预期故障已被测试捕获；该配置没有通过软件测试' if expected_failures else '软件测试通过'),
                launchLog=launch_log.read_text(errors='replace'), passed=True)


def technical_references():
    paths = [
        (ROOT / 'references/sources/official-core/ros2--launch/jazzy--ede227f7d0d0/launch_testing_ament_cmake/cmake/add_launch_test.cmake',
         '固定Jazzy：add_launch_test注册CTest、TIMEOUT秒及xunit结果路径；未把固定提交当成本机安装版本。'),
        (ROOT / 'references/sources/official-docs/ros2--ros2_documentation/jazzy--929e37c4c6d0/source/Tutorials/Intermediate/Testing/Integration.rst',
         '官方Jazzy教程：ReadyToTest、active/post-shutdown、独立ROS域和CTest注册。'),
        (Path('/usr/lib/python3/dist-packages/colcon_cmake/task/cmake/test.py'),
         '本机colcon-cmake：CTest return8表示测试失败，触发TestFailure事件而非任务错误。'),
        (Path('/usr/lib/python3/dist-packages/colcon_core/verb/test.py'),
         '本机colcon-core：--return-code-on-test-failure将TestFailure事件映射到命令非零。'),
        (Path('/usr/lib/python3/dist-packages/colcon_test_result/verb/test_result.py'),
         '本机colcon-test-result：聚合错误/失败决定退出1；没有结果也可能退出0，必须另查期望数量。'),
        (Path('/opt/ros/jazzy/share/ament_cmake_pytest/cmake/ament_add_pytest_test.cmake'),
         '本机ament：pytest结果文件及测试依赖/注册；注册包装项与内部案例分开计数。')]
    return [dict(path=str(path), sha256=sha(path), observation=note, verification='只读一手源码/文档')
            for path, note in paths]


def source_hashes():
    return [dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p))
            for p in sorted(HERE.rglob('*')) if p.is_file() and p.suffix in ('.py', '.cpp', '.hpp', '.xml', '.txt', '.md')]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', type=Path, default=Path('/tmp/ros2-hub-testing-labs'))
    parser.add_argument('--output', type=Path, default=Path('/tmp/testing-labs-rerun.json'))
    parser.add_argument('--domain-id', type=int, default=231)
    parser.add_argument('--interrupt-worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    require(0 <= args.domain_id <= 232, 'domain-id必须为0..232')
    args.build_root = args.build_root.resolve()
    env = isolated_environment(args.domain_id)
    env['ROS_LOG_DIR'] = str(args.build_root / 'ros-log')
    commands = Commands(args.build_root / ('interrupt-logs' if args.interrupt_worker else 'driver-logs'))
    report = dict(validatedAt=datetime.now(timezone.utc).isoformat(), passed=False,
                  sourceHashes=source_hashes(), phases=[], builds=[], expectedCTestRegistrations=3,
                  expectedJUnitCases=13, domainId=args.domain_id, discoveryRange='LOCALHOST',
                  rmw='rmw_fastrtps_cpp', subreaperEnabled=True)
    versions = subprocess.run(['dpkg-query', '-W', 'ros-jazzy-ament-cmake-gtest',
                               'ros-jazzy-ament-cmake-pytest', 'ros-jazzy-launch-testing',
                               'ros-jazzy-launch-testing-ament-cmake', 'ros-jazzy-launch-testing-ros',
                               'ros-jazzy-rclpy', 'ros-jazzy-rclcpp', 'python3-pytest',
                               'python3-colcon-core', 'python3-colcon-cmake', 'python3-colcon-test-result',
                               'libgtest-dev'], capture_output=True, text=True, timeout=10.0)
    report['installedPackages'] = dict(line.split('\t', 1) for line in versions.stdout.splitlines() if '\t' in line)
    report['technicalReferences'] = technical_references()
    report['pythonVersion'] = platform.python_version()
    try:
        good = args.build_root / 'good'
        if args.interrupt_worker:
            worker_env = with_setup(env, good / 'install/setup.bash')
            worker_env['TESTING_LAB_PROBE_HOLD_SECONDS'] = '4'
            record = commands.run(test_command(good, True), worker_env, 'interrupted-real-test', 45.0)
            report.update(interruptedCommand=record, interrupted=record['interrupted'])
            require(record['interrupted'], '生命周期worker必须真的收到父SIGINT')
            require(record['allOwnedProcessesReaped'], '中断后遗留自建测试进程')
        else:
            variants = {}
            for name, fault in [('good', False), ('missing_ready', True)]:
                root = args.build_root / name
                command = ['colcon', '--log-base', str(root / 'log-build'), 'build',
                           '--base-paths', str(HERE / PACKAGE), '--build-base', str(root / 'build'),
                           '--install-base', str(root / 'install'), '--merge-install', '--symlink-install',
                           '--packages-select', PACKAGE, '--cmake-args', '-DBUILD_TESTING=ON',
                           '-DTESTING_LAB_READY_FAULT=' + ('ON' if fault else 'OFF')]
                build = commands.run(command, env, name + '-build', 100.0)
                report['builds'].append(build)
                require(build['exitCode'] == 0 and build['allOwnedProcessesReaped'], name + '构建失败')
                listing = commands.run(['ctest', '--test-dir', str(root / 'build' / PACKAGE), '--show-only=json-v1'],
                                       env, name + '-registered', 15.0)
                ctest = json.loads(listing['log'])
                require({x['name'] for x in ctest['tests']} == {'test_wheel_math', 'test_rate_reader', 'test_wheel_launch'},
                        'CTest没有注册预期三项，不能接受零测试')
                binary = root / 'install/lib' / PACKAGE / 'wheel_processor'
                report.setdefault('artifacts', []).append(dict(variant=name, path=str(binary), sha256=sha(binary)))
                report.setdefault('ctestRegistrations', {})[name] = ctest
                variants[name] = dict(root=root, env=with_setup(env, root / 'install/setup.bash'))
            report['phases'].append(phase(commands, **variants['good'], label='good_default', strict=False, expected_failures=0))
            report['phases'].append(phase(commands, **variants['missing_ready'], label='fault_default', strict=False, expected_failures=1))
            report['phases'].append(phase(commands, **variants['missing_ready'], label='fault_strict', strict=True, expected_failures=1))
            # 本例生命周期检查另外运行真实集成测试并中断；之后正常严格测试恢复最终XML。
            report['lifecycleValidation'] = interrupt_probe(args, env)
            require(report['lifecycleValidation']['passed'], '父SIGINT测试进程清理失败')
            report['phases'].append(phase(commands, **variants['good'], label='good_final_strict', strict=True, expected_failures=0))
            empty = args.build_root / 'empty-results'
            empty.mkdir(parents=True, exist_ok=True)
            empty_result = commands.run(['colcon', '--log-base', str(args.build_root / 'log-empty-result'),
                                         'test-result', '--test-result-base', str(empty), '--verbose'],
                                        env, 'empty-results', 10.0)
            report['zeroTestGuard'] = dict(command=empty_result, actualXmlFiles=list(map(str, empty.rglob('*.xml'))),
                                           meetsExpectedCount=False, acceptance='拒绝验收：0份结果不是13例通过')
            require(empty_result['exitCode'] == 0 and not list(empty.rglob('*.xml')), '零结果示例行为不同，需重新核对')
            report['passed'] = True
    except (Exception, KeyboardInterrupt) as error:
        report.update(error=repr(error), traceback=traceback.format_exc())
        snapshots = {}
        for name in ('good', 'missing_ready'):
            paths = args.build_root / name / 'build' / PACKAGE / 'test_results' / PACKAGE
            snapshots[name] = [dict(path=str(p), sha256=sha(p), xml=p.read_text()) for p in paths.glob('*.xml')]
        report['unexpectedXmlSnapshots'] = snapshots
    finally:
        report['commands'] = commands.records
        report['sourcesUnchanged'] = all(sha(ROOT / s['path']) == s['sha256'] for s in report['sourceHashes'])
        report['cleanupPassed'] = all(r['allOwnedProcessesReaped'] for r in commands.records)
        report['teachingTables'] = [dict(caption='本机真实colcon/JUnit结果；13个细分案例与3个CTest注册项分开计数。',
            columns=['阶段', 'JUnit案例/失败', 'colcon test退出码', 'test-result退出码', '判定'],
            rows=[[p['label'], f"{p['xml']['junitCases']} / {p['xml']['failures']}",
                   str(p['test']['exitCode']), str(p['testResult']['exitCode']), p['acceptance']]
                  for p in report['phases']]),
            dict(caption='预期注册数必须与XML一致；数量不是每条测试内部assert的条数。',
                 columns=['层次', 'CTest注册项', '细分JUnit案例'],
                 rows=[['gtest物理合同', 'test_wheel_math', '4'],
                       ['pytest消息边界', 'test_rate_reader', '7'],
                       ['launch真实话题/退出', 'test_wheel_launch', '2']])]
        if report.get('zeroTestGuard'):
            report['teachingTables'][0]['rows'].append(['empty_results', '0 / 未执行', '未运行test',
                str(report['zeroTestGuard']['command']['exitCode']), '拒绝验收：没有预期结果'])
        report['teachingValidation'] = (
            '独立ament_cmake包真实构建；gtest4、pytest7、launch active/post-shutdown各1，共13个细分JUnit案例。'
            '受控缺失业务ready保持相同注册数量但实际失败；比较默认/严格colcon退出码与test-result。'
            '使用软件Twist输入和5/7rad/s手算值，不运行仿真或硬件；是否通过以passed和各阶段原始XML为准。')
        report['teachingCommand'] = ('source /opt/ros/jazzy/setup.bash\n' + shlex.join([
            sys.executable, 'examples/testing_labs/verify_testing_labs.py', '--build-root', str(args.build_root),
            '--domain-id', str(args.domain_id), '--output', '/tmp/testing-labs-rerun.json']))
        report['teachingCommandNote'] = ('从ros2-learning-hub运行；构建、故障版、日志在专属/tmp目录。'
            '报告另存/tmp不覆盖教材证据；只清理本驱动创建且startTicks匹配的进程。'
            'colcon退出0与零测试都不能独立证明通过；案例XML数量和失败数必须核对。')
        report['limits'] = ['只验证本机软件计算、消息合同和测试夹具，不验证机器人控制或硬件停车。',
                            '受控故障是缺失业务就绪标记，未声称实际测试了所有启动故障或网络故障。',
                            'Linux子收割器和/proc用于自建进程清理；没有终止ROS daemon或无关节点。']
        if args.output.exists():
            previous = json.loads(args.output.read_text())
            report['priorAttempts'] = previous.get('priorAttempts', []) + [{
                'validatedAt': previous.get('validatedAt'), 'passed': previous.get('passed'),
                'error': previous.get('error'), 'phases': previous.get('phases'),
                'commands': previous.get('commands'), 'sourceHashes': previous.get('sourceHashes'),
                'lifecycleValidation': previous.get('lifecycleValidation'),
                'unexpectedXmlSnapshots': previous.get('unexpectedXmlSnapshots')}]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        print('报告：' + str(args.output), flush=True)
    if args.interrupt_worker:
        return 130 if report.get('interrupted') and report['cleanupPassed'] else 1
    return 0 if report['passed'] and report['cleanupPassed'] else 1


def interrupt_probe(args, env):
    """仅给自建driver发SIGINT；独立检查真实wheel进程消失，控制器退路清理不能算通过。"""
    record = dict(passed=False, emergencySignals=[])
    with tempfile.TemporaryDirectory(prefix='testing-interrupt-') as directory:
        output_path = Path(directory) / 'worker.json'
        command = [sys.executable, str(Path(__file__).resolve()), '--interrupt-worker',
                   '--build-root', str(args.build_root), '--domain-id', str(args.domain_id),
                   '--output', str(output_path)]
        driver = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, start_new_session=True)
        record.update(command=command, driverPid=driver.pid)
        observed = {}
        try:
            deadline = time.monotonic() + 15.0
            while time.monotonic() < deadline:
                Commands.observe(driver.pid, observed)
                apps = [p for p in observed.values() if any(Path(v).name == 'wheel_processor' for v in p['command'])]
                log_path = args.build_root / 'good/build' / PACKAGE / 'launch_test/test_wheel_launch.txt'
                text = log_path.read_text(errors='replace') if log_path.exists() else ''
                lines = [line.split('TESTING_LAB_OBSERVATION ', 1)[1] for line in text.splitlines()
                         if 'TESTING_LAB_OBSERVATION ' in line]
                if apps and lines:
                    measurement = json.loads(lines[-1])
                    matches = [p for p in apps if measurement['namespace'] in ' '.join(p['command'])]
                    if matches:
                        record.update(applicationPid=matches[-1]['pid'], observationBeforeInterrupt=measurement)
                        break
                require(driver.poll() is None, '中断探针driver提前退出')
                time.sleep(0.03)
            else:
                raise AssertionError('没有观察到本轮真实话题结果及存活进程')
            driver.send_signal(signal.SIGINT)
            text, _ = driver.communicate(timeout=15.0)
            result = json.loads(output_path.read_text())
            record.update(exitCode=driver.returncode, driverOutput=text, workerReport=result)
            require(driver.returncode == 130 and result.get('interrupted'), '必须真实进入父SIGINT分支')
            require(result['cleanupPassed'], '子driver清理失败')
            require(process_info(record['applicationPid']) is None and process_info(driver.pid) is None,
                    '被测进程或driver尚未回收')
            record['passed'] = True
        except (Exception, KeyboardInterrupt) as error:
            record.update(error=repr(error), traceback=traceback.format_exc())
        finally:
            Commands.observe(driver.pid, observed)
            for identity in list(observed.values())[::-1]:
                current = process_info(identity['pid'])
                if current and current['startTicks'] == identity['startTicks']:
                    try:
                        os.kill(identity['pid'], signal.SIGKILL)
                        record['emergencySignals'].append(identity['pid'])
                    except ProcessLookupError:
                        pass
            if driver.poll() is None:
                driver.wait(timeout=3.0)
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                remaining = []
                for identity in observed.values():
                    try:
                        os.waitpid(identity['pid'], os.WNOHANG)
                    except ChildProcessError:
                        pass
                    current = process_info(identity['pid'])
                    if current and current['startTicks'] == identity['startTicks']:
                        remaining.append(current)
                if not remaining:
                    break
                time.sleep(0.03)
            record['remainingProcessesAfterControllerCleanup'] = remaining
            if record['emergencySignals']:
                record['passed'] = False
    return record


if __name__ == '__main__':
    sys.exit(main())
