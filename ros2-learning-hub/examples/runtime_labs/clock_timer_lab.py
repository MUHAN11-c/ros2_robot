#!/usr/bin/env python3
"""真实 rclpy 软件时钟实验：比较 ROS timer 与显式 STEADY timer。

准备与执行（--help 不需要 ROS，不会导入 rclpy）：
    source /opt/ros/jazzy/setup.bash
    timeout --signal=INT --kill-after=5s 25s /usr/bin/python3 clock_timer_lab.py

输入：手动生成的 rosgraph_msgs/Clock，单位为秒/纳秒；不启动仿真器。
输出：三个有限观察窗口内的回调计数、时间值、断言和版本/源码摘要JSON。
过程：等待本例发布者/订阅者发现 → 未收到clock → 设置正值并排空跳变事件
      → 正值暂停 → 逐步推进 → 清理timer、节点、执行器、Context。
意义：单调年龄计算不保证检查回调仍可调度；检查timer若依赖暂停的ROS时间，
      基于该timer的看门狗也会停止检查。本例所有阶段由单调外层等待推进。
边界：本机独立ROS域、LOCALHOST，只发布软件/clock，不发布任何设备命令。
      回调只计数，20ms有界spin不逐帧打印；外层timeout另防护原生调用卡住。
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import inspect
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo


def arguments():
    """仅用标准库解析参数，让没有source ROS的机器也能查看帮助。"""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain-id", type=int, default=223, help="独立ROS域，默认223")
    parser.add_argument("--period-s", type=float, default=0.1, help="两timer周期，秒，默认0.1")
    parser.add_argument("--window-s", type=float, default=0.8, help="每观察窗口墙上经过秒数，默认0.8")
    parser.add_argument("--step-s", type=float, default=0.05, help="推进阶段每条clock增加的ROS秒数")
    parser.add_argument("--publish-interval-s", type=float, default=0.04, help="推进clock的单调经过秒间隔")
    parser.add_argument("--total-timeout-s", type=float, default=15.0, help="单调总软期限，秒")
    parser.add_argument("--report", type=Path,
                        default=Path(__file__).resolve().parents[2]/"validation-evidence/clock-timer-current-validation.json",
                        help="结构化实际结果路径；失败也写入")
    result = parser.parse_args()
    values = [result.period_s,result.window_s,result.step_s,result.publish_interval_s,result.total_timeout_s]
    if not all(math.isfinite(value) and value > 0 for value in values):
        parser.error("所有时间参数必须是有限正数，单位秒")
    if not 0 <= result.domain_id <= 232:
        parser.error("domain-id须位于0..232")
    if result.period_s < 0.05 or result.publish_interval_s < 0.02:
        parser.error("教学实验限制timer至少50ms、发布间隔至少20ms，避免高频忙循环")
    if result.window_s < 3*result.period_s:
        parser.error("观察窗口至少为三个timer周期")
    if result.step_s > result.period_s:
        parser.error("clock推进步长不得超过timer周期，便于观察逐步推进")
    if round(result.step_s*1_000_000_000) < 1:
        parser.error("clock推进步长换算后至少为1ns")
    if result.total_timeout_s < 3*result.window_s+3.0:
        parser.error("总期限须给三个窗口及设置/清理留下至少三秒余量")
    return result


def check(condition, description):
    """断言物理语义，失败保留计数；不缩小断言来掩盖未观测到的行为。"""
    if not condition:
        raise AssertionError(description)


def run(options, report):
    """所有ROS导入都放在帮助解析之后；本函数只持有本例创建的资源。"""
    import rclpy
    from rclpy.clock import Clock as RclpyClock
    from rclpy.clock_type import ClockType
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
    from rclpy.time_source import TimeSource
    from rclpy.timer import Timer
    from rosgraph_msgs.msg import Clock as ClockMessage
    from ament_index_python.packages import get_package_share_directory

    started = time.monotonic()
    deadline = started+options.total_timeout_s
    context = Context()
    executor = None
    source = None
    target = None
    counters = {"ros":0,"steady":0}
    events = {"ros":[],"steady":[]}
    publication_count = 0
    software_time_ns = 10_000_000_000  # 正值暂停设为10s，与主机实际日期时间无关。
    report["versions"] = {"python":sys.version,"pythonExecutable":sys.executable,
                          "platform":platform.platform(),"rosDistro":os.environ.get("ROS_DISTRO"),
                          "rclpy":importlib.metadata.version("rclpy"),"packages":{}}
    for name in ("rclpy","rclcpp","rmw_fastrtps_cpp","rosgraph_msgs"):
        package = Path(get_package_share_directory(name))/"package.xml"
        report["versions"]["packages"][name] = ET.parse(package).getroot().findtext("version")
    # 运行库源码可能与下载快照提交不同；直接记录本次实际导入文件的摘要。
    report["runtimeSourceFingerprints"] = []
    for cls in (Node,RclpyClock,Timer,SingleThreadedExecutor,TimeSource):
        path = Path(inspect.getsourcefile(cls)).resolve()
        report["runtimeSourceFingerprints"].append({"api":cls.__name__,"file":str(path),
                                                   "sha256":hashlib.sha256(path.read_bytes()).hexdigest()})

    def spin_once(until):
        # timeout_sec只约束等待就绪；本例回调均为短计数，另有进程级timeout兜底。
        now=time.monotonic()
        check(now < deadline,"单调外层等待达到总期限")
        remaining = min(until,deadline)-now
        if remaining <= 0:
            # 正常阶段窗口刚好结束，不把微秒级检查竞争误报为总期限故障。
            return
        executor.spin_once(timeout_sec=min(0.02,remaining))

    def wait_for(predicate, timeout_s, label):
        end = min(time.monotonic()+timeout_s,deadline)
        while not predicate() and time.monotonic() < end:
            spin_once(end)
        check(predicate(),f"{label}在{timeout_s}s内未满足")

    def publish_clock(value_ns):
        nonlocal publication_count
        message = ClockMessage()
        message.clock.sec,message.clock.nanosec = divmod(value_ns,1_000_000_000)
        publisher.publish(message)
        publication_count += 1

    def observe(name, advance=False, window_s=None):
        """记录首尾而不要求精确tick数；正值暂停期不再发送任何clock消息。"""
        nonlocal software_time_ns
        beginning = time.monotonic()
        end = beginning+(options.window_s if window_s is None else window_s)
        check(end < deadline,f"{name}开始前总时间预算不足")
        counts_before = counters.copy()
        ros_before = target.get_clock().now().nanoseconds
        sent_before = publication_count
        next_publish = beginning
        while time.monotonic() < end:
            now = time.monotonic()
            if advance and now >= next_publish:
                software_time_ns += round(options.step_s*1_000_000_000)
                publish_clock(software_time_ns)
                # 不追赶堆积的“欠发消息”，避免调度迟到后形成发布突发。
                next_publish = now+options.publish_interval_s
            spin_once(end)
        result = {"name":name,"requestedWindowS":end-beginning,
                  "actualElapsedS":time.monotonic()-beginning,
                  "rosTimeStartNs":ros_before,"rosTimeEndNs":target.get_clock().now().nanoseconds,
                  "countsBefore":counts_before,"countsAfter":counters.copy(),
                  "delta":{key:counters[key]-counts_before[key] for key in counters},
                  "clockMessagesPublished":publication_count-sent_before}
        return result

    try:
        rclpy.init(args=[],context=context)
        namespace=f"/clock_timer_lab/p{os.getpid()}"
        source=Node("software_clock_source",namespace=namespace,context=context,enable_rosout=False)
        target=Node("timer_probe",namespace=namespace,context=context,enable_rosout=False,
                    parameter_overrides=[Parameter("use_sim_time",value=True)])
        check(target.get_parameter("use_sim_time").value is True,"use_sim_time未生效")
        # Jazzy没有统一导出的qos_profile_clock快捷常量；显式列出与
        # TimeSource订阅相容的KeepLast 1、BestEffort、Volatile合同。
        clock_qos=QoSProfile(depth=1,history=HistoryPolicy.KEEP_LAST,
                             reliability=ReliabilityPolicy.BEST_EFFORT,
                             durability=DurabilityPolicy.VOLATILE)
        publisher=source.create_publisher(ClockMessage,"/clock",clock_qos)
        report["clockQoS"]={"history":"KEEP_LAST","depth":1,
                            "reliability":"BEST_EFFORT","durability":"VOLATILE"}
        # 保留时钟对象引用；STEADY_TIME不是SYSTEM_TIME，也不会被/clock覆盖。
        steady_clock=RclpyClock(clock_type=ClockType.STEADY_TIME)

        def count(kind):
            counters[kind]+=1
            events[kind].append({"monotonicElapsedS":time.monotonic()-started,
                                 "rosTimeNs":target.get_clock().now().nanoseconds})

        target.create_timer(options.period_s,lambda:count("ros"))
        target.create_timer(options.period_s,lambda:count("steady"),clock=steady_clock)
        # 显式Context必须与Node/Executor一致，避免默认全局执行器的隐式依赖。
        executor=SingleThreadedExecutor(context=context)
        executor.add_node(source)
        executor.add_node(target)
        wait_for(lambda:publisher.get_subscription_count() >= 1,5.0,"/clock订阅发现")
        check(target.count_publishers("/clock") == 1,"该独立域存在额外/clock发布者，无法归因")
        check(target.get_clock().now().nanoseconds == 0,"尚未发布clock时ROS时间应为0")
        report["namespace"]=namespace
        report["useSimTime"]=True
        report["clockTopic"]="/clock"
        report["phases"]=[]

        missing=observe("clock-not-received")
        report["phases"].append(missing)
        check(missing["delta"]["ros"] == 0 and missing["delta"]["steady"] >= 1,
              f"clock未到时计数不符：{missing}")
        check(missing["rosTimeStartNs"] == missing["rosTimeEndNs"] == 0,"未到阶段ROS时间不应推进")

        # BestEffort不承诺单包必达，故在有界设置阶段重复同一正值，直到真实订阅生效。
        activation_started=time.monotonic()
        activation_end=min(activation_started+3.0,deadline)
        next_send=0.0
        before_activation=publication_count
        while target.get_clock().now().nanoseconds != software_time_ns and time.monotonic() < activation_end:
            if time.monotonic() >= next_send:
                publish_clock(software_time_ns)
                next_send=time.monotonic()+0.05
            spin_once(activation_end)
        check(target.get_clock().now().nanoseconds == software_time_ns,"正值/clock未被实际接收")
        report["positiveClockActivation"]={"valueNs":software_time_ns,
            "messagesPublished":publication_count-before_activation,
            "actualElapsedS":time.monotonic()-activation_started}
        # 跳变可能使某次timer已就绪；先有限排空，再观察真正稳定暂停窗口。
        report["settling"]=observe("settle-positive-clock",window_s=max(0.25,2*options.period_s))
        paused=observe("positive-clock-paused")
        report["phases"].append(paused)
        check(paused["delta"]["ros"] == 0 and paused["delta"]["steady"] >= 1,
              f"正值暂停时计数不符：{paused}")
        check(paused["rosTimeStartNs"] == paused["rosTimeEndNs"] == software_time_ns,
              "正值暂停阶段ROS时间应保持同一正值")

        advancing=observe("clock-advancing",advance=True)
        report["phases"].append(advancing)
        check(advancing["delta"]["ros"] >= 1 and advancing["delta"]["steady"] >= 1,
              f"clock推进时两个计时器都应前进：{advancing}")
        check(advancing["rosTimeEndNs"] > advancing["rosTimeStartNs"],"推进阶段未实际收到新clock")
        report["assertions"]={"noClockRosStoppedSteadyProgressed":True,
                              "positivePauseRosStoppedSteadyProgressed":True,
                              "advancingClockBothProgressed":True}
        report["passed"]=True
    except BaseException:
        report["passed"]=False
        report["error"]=traceback.format_exc()
    finally:
        cleanup=[]
        if executor is not None:
            try:
                for node in (target,source):
                    if node is not None:
                        executor.remove_node(node)
                check(executor.shutdown(timeout_sec=2.0),"执行器未在2s内清理")
                cleanup.append("executor stopped")
            except BaseException:
                report["passed"]=False
                cleanup.append(traceback.format_exc())
        for node in (target,source):
            if node is not None:
                node.destroy_node()
        if context.ok():
            rclpy.shutdown(context=context)
        report["cleanup"]={"steps":cleanup,"nodesDestroyed":True,"contextOkAfterCleanup":context.ok()}
        report["totalElapsedS"]=time.monotonic()-started
        report["clockMessagesPublished"]=publication_count
        report["timerCounts"]=counters
        report["events"]=events


def main():
    options=arguments()
    # 只采用Jazzy发现范围配置，不同时保留会覆盖它的旧LOCALHOST变量。
    previous_localhost=os.environ.pop("ROS_LOCALHOST_ONLY",None)
    os.environ.pop("ROS_STATIC_PEERS",None)
    os.environ.update(ROS_DOMAIN_ID=str(options.domain_id),
                      ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",RMW_IMPLEMENTATION="rmw_fastrtps_cpp")
    report={"schemaVersion":1,"checkedAt":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
            "passed":False,"script":str(Path(__file__).resolve()),
            "invocation":[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],
            "scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "parameters":{key:value for key,value in vars(options).items() if key != "report"},
            "environment":{"ROS_DOMAIN_ID":os.environ["ROS_DOMAIN_ID"],
                           "ROS_AUTOMATIC_DISCOVERY_RANGE":"LOCALHOST",
                           "RMW_IMPLEMENTATION":"rmw_fastrtps_cpp","ROS_LOCALHOST_ONLY":"unset",
                           "legacyLocalhostVariableWasPresent":previous_localhost is not None},
            "scope":"真实rclpy与软件/clock实验，没有启动仿真器、没有硬件或设备命令。",
            "limits":["计数只证明本机有限窗口的触发条件，不是精确频率、硬实时或任意负载保证。",
                      "正值设置后的跳变结算窗口与正式暂停窗口分开，不把一次跳变回调当持续推进。",
                      "仅软件ROS时间；use_sim_time参数名不表示本轮已经启动仿真。",
                      "单调软期限不能打断任意原生阻塞调用；执行命令另用进程级timeout。"]}
    with tempfile.TemporaryDirectory(prefix="ros2-clock-timer-lab-") as directory:
        os.environ["ROS_LOG_DIR"]=directory
        try:
            run(options,report)
        except BaseException:
            report["passed"]=False
            report["error"]=traceback.format_exc()
    options.report.parent.mkdir(parents=True,exist_ok=True)
    if options.report.is_file():
        previous=json.loads(options.report.read_text())
        history=previous.pop("previousAttempts",[])
        report["previousAttempts"]=[*history,previous]
    options.report.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    summary={"passed":report["passed"],"report":str(options.report.resolve()),
             "phases":[{"name":p["name"],"delta":p["delta"]} for p in report.get("phases",[])]}
    print(json.dumps(summary,ensure_ascii=False))
    if not report["passed"]:
        print(report.get("error","清理阶段失败，见JSON"),file=sys.stderr)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
