#!/usr/bin/env python3
"""Count验收父进程真实SIGINT清理检查；不把进程终止当成Action取消或硬件停车。

输入：已有十组协议报告、基础/扩展安装前缀。仅本程序创建driver→worker→server。
执行：等待扩展Python服务端实际发布第一步反馈，再只向driver发SIGINT，核对其清理子组。
输出：把独立lifecycleValidation加入指定报告；主场景表仍为十组，不新增取消业务覆盖声明。
本检查依赖Linux /proc，help只用标准库；没有导入ROS。所有等待为monotonic秒。
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE = 'py_extended_abort_and_recovery'


def require(condition, description):
    if not condition:
        raise AssertionError(description)


def exists(pid):
    # 保留僵尸也算未完成回收；检查要求/proc项真正消失，不只看状态不是running。
    return pid is not None and Path(f'/proc/{pid}').exists()


def children(pid):
    try:
        return [int(x) for x in Path(f'/proc/{pid}/task/{pid}/children').read_text().split()]
    except FileNotFoundError:
        return []


def commandline(pid):
    try:
        return Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    except FileNotFoundError:
        return []


def parse_events(text):
    events = []
    for line in text.splitlines():
        if 'COUNT_LAB_EVENT ' in line:
            try:
                events.append(json.loads(line.split('COUNT_LAB_EVENT ', 1)[1]))
            except ValueError:
                pass  # 仍在写入的末行稍后重读；原始快照会保存在结果中。
    return events


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--foundation-prefix', type=Path, required=True)
    parser.add_argument('--fault-prefix', type=Path, default=Path('/tmp/ros2-hub-count-action-lab/install'))
    parser.add_argument('--report', type=Path, default=Path('/tmp/count-action-rerun.json'),
                        help='已有通过的十组协议报告；读者应使用/tmp副本')
    parser.add_argument('--domain-id', type=int, default=227)
    args = parser.parse_args(argv)
    report = json.loads(args.report.read_text())
    require(report['passed'] and report['summary']['mainCases'] == 10, '先完成十组协议实验')
    for source in report['sourceHashes']:
        actual = hashlib.sha256((ROOT / source['path']).read_bytes()).hexdigest()
        require(actual == source['sha256'], '源码变化后必须先重跑主实验：' + source['path'])

    check = dict(id='parent_sigint_reaps_owned_worker_and_server', passed=False,
                 validatedAt=datetime.now(timezone.utc).isoformat(),
                 method='Linux/proc直接父子关系及server日志首步反馈；只向driver PID发送SIGINT',
                 driverPid=None, workerPid=None, serverPid=None, emergencySignals=[])
    driver = None
    with tempfile.TemporaryDirectory(prefix='count-interrupt-') as directory:
        temporary_report = Path(directory) / 'interrupted-driver-report.json'
        command = [sys.executable, str(HERE / 'verify_count_actions.py'),
                   '--foundation-prefix', str(args.foundation_prefix.resolve()),
                   '--fault-prefix', str(args.fault_prefix.resolve()), '--domain-id', str(args.domain_id),
                   '--case', CASE, '--case-timeout', '25', '--output', str(temporary_report)]
        check['driverCommand'] = command
        try:
            # driver有自己的组；它再创建独立会话worker。该结构复现真实Ctrl+C保护缺口。
            driver = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, start_new_session=True)
            check['driverPid'] = driver.pid
            deadline = time.monotonic() + 10.0
            snapshot = None
            while time.monotonic() < deadline:
                require(driver.poll() is None, 'driver在触发中断前已退出')
                for candidate in children(driver.pid):
                    if b'--worker' in commandline(candidate) and CASE.encode() in commandline(candidate):
                        check['workerPid'] = candidate
                worker_pid = check['workerPid']
                if worker_pid is not None:
                    for candidate in children(worker_pid):
                        if any(b'count_fault_py' in token for token in commandline(candidate)):
                            check['serverPid'] = candidate
                if check['serverPid'] is not None:
                    try:
                        log_path = Path(os.readlink(f"/proc/{check['serverPid']}/fd/1"))
                        snapshot = log_path.read_text(errors='replace')
                    except (FileNotFoundError, PermissionError):
                        snapshot = None
                    if snapshot:
                        events = parse_events(snapshot)
                        feedback = [e for e in events if e['event'] == 'feedback']
                        terminal = [e for e in events if e['event'] in ('ABORTED', 'CANCELED', 'SUCCEEDED')]
                        if feedback and not terminal:
                            check['firstFeedbackBeforeInterrupt'] = feedback[0]
                            check['serverLogBeforeInterrupt'] = snapshot
                            break
                time.sleep(0.02)
            else:
                raise AssertionError('十秒内未观察到真实执行中的首步反馈')
            require(all(exists(check[key]) for key in ('driverPid', 'workerPid', 'serverPid')),
                    '触发前driver/worker/server应同时存在')
            sent_at = time.monotonic()
            driver.send_signal(signal.SIGINT)  # 只向父driver发，不能由测试控制器代替它清理worker。
            output, _ = driver.communicate(timeout=14.0)
            check.update(driverExitCode=driver.returncode, driverOutput=output,
                         shutdownElapsed_s=round(time.monotonic() - sent_at, 6))
            require(driver.returncode != 0, '有意中断不能报告协议验收成功')
            interrupted = json.loads(temporary_report.read_text())
            check['interruptedDriverReport'] = interrupted
            require(not interrupted['passed'] and len(interrupted['cases']) == 1, '应保存未完成场景而非伪造成功')
            case = interrupted['cases'][0]
            require(case['worker']['protectionReason'] == 'parent_keyboard_interrupt', '未进入实际父SIGINT保护分支')
            require(case['worker']['parentSignals'] and case['worker']['reaped'], '缺少自建worker组清理证据')
            require(case['probeCleanup']['contextShutdown'], 'worker专属Context未关闭')
            require(all(s['reaped'] for s in case['serverProcesses']), 'worker未回收其server')
            require(len(case['serverProcesses']) == 1, '本场景应只有一个自建server')
            server = case['serverProcesses'][0]
            require(server['priorGroupSigint'], 'worker应识别server已收到同组SIGINT')
            require(not server['signalsSent'], '普通单次父INT不应被worker重复发送或立即升级')
            require(server['exitCode'] == 0, 'server首次SIGINT清理应正常退出')
            require('KeyboardInterrupt' not in server['log'] and 'Traceback' not in server['log'],
                    '不应有第二次INT打断shutdown/join的异常栈')
            check['singleSigintShutdown'] = dict(
                parentGroupSignals=case['worker']['parentSignals'],
                workerAdditionalSignals=server['signalsSent'],
                initialServerGrace_s=server['initialWaitForAlreadySignaledServer_s'],
                serverExitCode=server['exitCode'], serverShutdownTraceback=False)
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and any(exists(check[k]) for k in ('driverPid', 'workerPid', 'serverPid')):
                time.sleep(0.02)
            absence = {key: not exists(check[key]) for key in ('driverPid', 'workerPid', 'serverPid')}
            check['procEntriesAbsentAfterParentCleanup'] = absence
            require(all(absence.values()), '父保护返回后仍存在自建进程或僵尸')
            check['passed'] = True
        except (Exception, KeyboardInterrupt) as error:
            check.update(error=repr(error), traceback=traceback.format_exc())
        finally:
            # 仅失败时应急清理已记录的自建组。用到此退路不能冒充driver保护通过。
            for key in ('workerPid', 'driverPid'):
                pid = check[key]
                if exists(pid) or (key == 'workerPid' and exists(check['serverPid'])):
                    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
                        try:
                            os.killpg(pid, sig)
                            check['emergencySignals'].append(dict(groupLeaderPid=pid, signal=sig.name))
                        except ProcessLookupError:
                            break
                        time.sleep(0.2)
                        if not exists(pid):
                            break
            if driver is not None and driver.poll() is None:
                driver.wait(timeout=3.0)
            if check['emergencySignals']:
                check['passed'] = False
    check['limits'] = [
        '这是进程生命周期/SIGINT清理验证，十组协议表仍保持原结果。',
        '中断时未证明目标获得任何业务终态，不把服务端退出当取消完成或硬件停车。',
        '扩展服务端取消路径没有作为业务成功/取消主场景实测；中途取消主场景只覆盖原两语言。']
    report['lifecycleValidation'] = check
    report['passed'] = report['passed'] and check['passed']
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(id=check['id'], passed=check['passed'],
                          workerPid=check['workerPid'], serverPid=check['serverPid'],
                          procEntriesAbsent=check.get('procEntriesAbsentAfterParentCleanup'),
                          emergencySignals=check['emergencySignals']), ensure_ascii=False))
    return 0 if check['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
