#!/usr/bin/env python3
"""复现旧例覆盖盲点、修订策略及原talker集成例；不连接硬件。

输入是本目录可信基线JSON、policy/test文件、已加载Jazzy和launch_test。
输出报告默认/tmp/testing-existing-result.json，保留源码SHA、JUnit及命令日志。
速度单位m/s、策略时间单位整数ns；外层进程保护用monotonic秒。
--help只加载标准库；--unit-only跳过ROS例，但报告显式标出，不当完整验证。
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE_NAMES=('README.md','baseline_sources.json','policy.py','test_policy.py','verify_existing.py')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def run(command, directory, env, timeout_s):
    """每次新建进程组。只在仍运行时发一次INT，再按保护窗口升级TERM/KILL。"""
    start=time.monotonic()
    process=subprocess.Popen(command,cwd=directory,env=env,stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,text=True,start_new_session=True)
    signals=[]
    try:
        output,_=process.communicate(timeout=timeout_s)
    except BaseException:
        for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGKILL):
            if process.poll() is not None:break
            try:os.killpg(process.pid,sig)
            except ProcessLookupError:break
            signals.append(sig.name)
            try:
                process.communicate(timeout=3.0)
                break
            except subprocess.TimeoutExpired:pass
        if process.poll() is None:process.wait(timeout=3.0)
        raise
    return dict(command=command,exitCode=process.returncode,elapsedS=time.monotonic()-start,
                pid=process.pid,signalsSent=signals,reaped=process.poll() is not None,output=output)


def junit(file):
    root=ET.parse(file).getroot()
    # 只计最底层testcase，避免testsuites和testsuite的汇总数重复相加。
    cases=list(root.iter('testcase'))
    return dict(testcases=len(cases),failures=sum(c.find('failure') is not None for c in cases),
                errors=sum(c.find('error') is not None for c in cases),
                skipped=sum(c.find('skipped') is not None for c in cases),xml=file.read_text())


def baseline_gaps(code):
    namespace={}
    exec(compile(code,'trusted_baseline_policy.py','exec'),namespace)
    policy=namespace['select_output']
    checks=[
        ('nonfinite-now',(0.4,100,float('nan'),100),0.0),
        ('nonfinite-last',(0.4,float('nan'),150,100),0.0),
        ('nonfinite-timeout',(0.4,100,150,float('nan')),'ValueError'),
        ('bool-timeout',(0.4,100,150,True),'ValueError'),
        ('bool-speed',(True,100,150,100),0.0),
        ('string-speed',('0.4',100,150,100),0.0)]
    rows=[]
    for name,values,expected in checks:
        try:
            value=policy(*values)
            observed=repr(value)
            matched=expected!='ValueError' and type(value) is not bool and value==expected
        except Exception as error:
            observed=type(error).__name__
            matched=expected=='ValueError' and isinstance(error,ValueError)
        rows.append(dict(case=name,inputRepr=repr(values),expected=str(expected),observed=observed,
                         exposesUncoveredContract=not matched))
    require(all(row['exposesUncoveredContract'] for row in rows),'历史基线表现变化，先核读，不自动改成通过')
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/testing-existing-result.json'))
    parser.add_argument('--unit-only',action='store_true')
    parser.add_argument('--domain-id',type=int,default=230)
    args=parser.parse_args()
    if not 0<=args.domain_id<=232:parser.error('domain-id须在0..232，默认230')
    fixture=json.loads((HERE/'baseline_sources.json').read_text())
    for name,item in fixture['files'].items():
        require(hashlib.sha256(item['code'].encode()).hexdigest()==item['sha256'],'基线文件字节不一致：'+name)
    report=dict(checkedAt='2026-11-07',passed=False,unitOnly=args.unit_only,domain=args.domain_id,
                sourceHashes=[dict(path=(HERE/name).relative_to(ROOT).as_posix(),sha256=sha(HERE/name))
                              for name in SOURCE_NAMES],results={},
                baselineSnippetHashes={name:item['sha256'] for name,item in fixture['files'].items()},
                versions=dict(python=platform.python_version(),pythonExecutable=sys.executable,
                              platform=platform.platform(),pytest=importlib.metadata.version('pytest')))
    for package in ('rclpy','launch_testing','launch_ros'):
        try:report['versions'][package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:report['versions'][package]='not available in current metadata path'
    env=dict(os.environ,ROS_DOMAIN_ID=str(args.domain_id),ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',
             RMW_IMPLEMENTATION='rmw_fastrtps_cpp',PYTHONDONTWRITEBYTECODE='1',RCUTILS_COLORIZED_OUTPUT='0')
    env.pop('ROS_STATIC_PEERS',None);env.pop('ROS_LOCALHOST_ONLY',None)
    try:
        with tempfile.TemporaryDirectory(prefix='ros2-existing-testing-') as folder:
            work=Path(folder);old=work/'baseline';new=work/'revised';old.mkdir();new.mkdir()
            # 将本次ROS/launch日志定向至自有临时目录，避免写到用户的默认ROS目录。
            env['ROS_LOG_DIR']=str(work/'ros-logs')
            report['environment']={key:env[key] for key in ('ROS_DOMAIN_ID','ROS_AUTOMATIC_DISCOVERY_RANGE','RMW_IMPLEMENTATION','ROS_LOG_DIR')}
            for name,item in fixture['files'].items():(old/name).write_text(item['code'])
            result=run([sys.executable,'-m','pytest','-q','test_policy.py','--junitxml',str(old/'pytest.xml')],old,env,20)
            result['junit']=junit(old/'pytest.xml')
            require(result['exitCode']==0 and result['junit']['testcases']==4 and result['junit']['failures']==0,'旧4项没有实际通过')
            report['results']['originalFourTests']=result
            report['results']['coverageGaps']=baseline_gaps(fixture['files']['policy.py']['code'])
            for name in ('policy.py','test_policy.py'):(new/name).write_bytes((HERE/name).read_bytes())
            result=run([sys.executable,'-m','pytest','-q','test_policy.py','--junitxml',str(new/'pytest.xml')],new,env,20)
            result['junit']=junit(new/'pytest.xml')
            require(result['exitCode']==0 and result['junit']['testcases']==31 and result['junit']['failures']==0,'修订策略31项未全部通过')
            report['results']['revisedPolicy']=result
            if not args.unit_only:
                result=run(['launch_test','test_talker.py','--junit-xml',str(old/'launch.xml')],old,env,40)
                result['junit']=junit(old/'launch.xml')
                require(result['exitCode']==0 and result['junit']['testcases']==2 and not result['junit']['failures'] and not result['junit']['errors'],'原talker两阶段集成没有通过')
                report['results']['originalTalker']=result
            report['passed']=True
    except BaseException:
        report['error']=traceback.format_exc()
    report['teachingTables']=[dict(title='同一策略：通过旧测试之后仍需核对输入合同',
        columns=['阶段','实际测试/反例','结果','能说明什么'],rows=[
            ['历史基线pytest','4项','通过' if report['results'].get('originalFourTests',{}).get('exitCode')==0 else '未通过','原4项没有覆盖畸形时戳与期限'],
            ['新增合同反例','6项','暴露原覆盖缺口' if len(report['results'].get('coverageGaps',[]))==6 else '未完成','NaN时戳/期限、bool、字符串另查'],
            ['修订策略pytest','31项','通过' if report['results'].get('revisedPolicy',{}).get('exitCode')==0 else '未通过','整数纳秒、有限速度与配置/数据错误分开'],
            ['原talker launch_test','2项','未运行' if args.unit_only else '通过' if report['results'].get('originalTalker',{}).get('exitCode')==0 else '未通过','实际消息和post-shutdown退出码分别检查']],
        caption='真实pytest/launch_test与JUnit记录；原基线保留在JSON，只作已知缺口对照。31项是本次参数化测试计数，不代表输入全集。')]
    report['teachingValidation']=('旧策略4项通过但6个新合同反例暴露缺口，修订策略31项已实测；'+
        ('本次unit-only未运行talker。' if args.unit_only else '原talker活动/退出2项按本机有限范围实测。')+'无硬件或制动验证。')
    report['teachingCommand']='source /opt/ros/jazzy/setup.bash\n/usr/bin/python3 examples/testing_policy/verify_existing.py --output /tmp/testing-existing-result.json'
    report['teachingCommandNote']='从ros2-learning-hub目录运行；需要pytest、launch_testing、launch_ros、rclpy、std_msgs和demo_nodes_cpp。默认域230/LOCALHOST，子进程保护20或40秒，不当硬实时界限。'
    report['limits']=['只验证列出的有限输入和本机talker软件协议；未运行机器人或安全制动。',
                      '旧4项通过与新增反例暴露缺口可以同时成立；JSON基线不是推荐策略。',
                      '策略不限制速度幅值、不转换时间域、不代替超时节点或设备停止。',
                      '本辅助driver的父中断/挂死保护未另作故障注入；原talker正常退出由post-shutdown例核对。']
    if args.output.exists():
        previous=json.loads(args.output.read_text())
        report['previousAttempts']=[*previous.pop('previousAttempts',[]),previous]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(passed=report['passed'],unitOnly=args.unit_only,report=str(args.output)),ensure_ascii=False))
    if not report['passed']:print(report.get('error',''),file=sys.stderr)
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
