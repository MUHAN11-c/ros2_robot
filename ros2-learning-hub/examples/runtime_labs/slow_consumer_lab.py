#!/usr/bin/env python3
"""用两个独立进程测量慢消费者，而不是让慢回调同时阻塞发布者。

执行：source /opt/ros/jazzy/setup.bash
      timeout --signal=INT --kill-after=8s 90s /usr/bin/python3 slow_consumer_lab.py

输入：本机合成 String(JSON)，字段为来源、无量纲序号、monotonic_ns采样时刻。
输出：四组真实发送/回调事件、纳秒时间、毫秒统计、精确断言及子进程清理证据JSON。
场景：正常处理；80ms处理且订阅深度1；80ms且深度10；深度10加120ms新鲜度门控。
发布端始终在另一个进程中，以稳态timer请求40Hz；报告保留实际节奏，不假定恰好40Hz。
两端都在同一主机。monotonic_ns的起点不能在不同主机间直接比较；也不能与ROS时间混减。
门控只决定是否接受合成结果：开始前预留80ms预算，处理后再核对年龄；不证明硬件停车。
所有ROS导入都在worker函数内；--help和--self-test只使用标准库。
本进程仅监督自己创建的PID；单调软期限之外，外层timeout另防护原生调用卡住。
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
import xml.etree.ElementTree as ET


CASES = ("normal", "slow-depth-1", "slow-depth-10", "slow-gated")
NS_PER_S = 1_000_000_000
NS_PER_MS = 1_000_000
MAX_TIME_NS = (1 << 63) - 1
SLOW_NS = 80 * NS_PER_MS
DRAIN_S = 1.2  # 深度10的80ms工作共约0.8s；多留余量，不以此承诺调度硬上限。
MAX_EVENTS = 2000  # 参数限制最多产生640个样本；上限另防消息/循环逻辑错误。


def require(condition, description):
    """显式断言不会因python -O被关闭；失败时保留报告而不放宽结论。"""
    if not condition:
        raise AssertionError(description)


def age_decision(sample_ns, current_ns, limit_ns):
    """返回年龄判定；纳秒必须是有界整数，bool、浮点NaN/Inf和未来戳均拒绝。

    允许时间0表示同一单调时基起点；过期采用age > limit，所以恰好上界仍有效。
    此函数只判断时间合同，不保证执行器仍在调度检查，更不执行设备安全动作。
    """
    integer = lambda value: type(value) is int and 0 <= value <= MAX_TIME_NS
    if not integer(limit_ns) or limit_ns == 0:
        return {"valid": False, "reason": "invalid_limit", "age_ns": None}
    if not integer(sample_ns) or not integer(current_ns):
        return {"valid": False, "reason": "invalid_time", "age_ns": None}
    if sample_ns > current_ns:
        return {"valid": False, "reason": "future_stamp", "age_ns": None}
    age = current_ns - sample_ns
    return {"valid": True, "reason": "fresh" if age <= limit_ns else "expired",
            "age_ns": age, "within_limit": age <= limit_ns}


def finite_in_range(value, low, high):
    """配置用有限实数；不把bool或NaN当成有效频率/期限。边界两端均包含。"""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and low <= value <= high
    except OverflowError:
        return False  # 巨大Python整数不能转换成有限float，也不接受为教学参数。


def boundary_checks():
    """标准库边界实验：实际运行并保存每一项输入类别、期望与结果。"""
    rows = []
    vectors = [
        ("zero_age", 100, 100, 10, True, "fresh"),
        ("exact_limit", 100, 110, 10, True, "fresh"),
        ("one_ns_expired", 100, 111, 10, True, "expired"),
        ("future_stamp", 111, 110, 10, False, "future_stamp"),
        ("negative_stamp", -1, 110, 10, False, "invalid_time"),
        ("negative_now", 100, -1, 10, False, "invalid_time"),
        ("nan_stamp", float("nan"), 110, 10, False, "invalid_time"),
        ("infinite_now", 100, float("inf"), 10, False, "invalid_time"),
        ("none_stamp", None, 110, 10, False, "invalid_time"),
        ("bool_stamp", True, 110, 10, False, "invalid_time"),
        ("float_nan_limit", 100, 110, float("nan"), False, "invalid_limit"),
        ("negative_limit", 100, 110, -1, False, "invalid_limit"),
        ("zero_limit", 100, 110, 0, False, "invalid_limit"),
        ("too_large_now", 100, MAX_TIME_NS + 1, 10, False, "invalid_time"),
        ("largest_integer", MAX_TIME_NS, MAX_TIME_NS, 10, True, "fresh"),
    ]
    for name, sampled, current, limit, valid, reason in vectors:
        observed = age_decision(sampled, current, limit)
        passed = observed["valid"] == valid and observed["reason"] == reason
        rows.append({"case": name, "inputRepr": [repr(sampled), repr(current), repr(limit)],
                     "expectedValid": valid, "expectedReason": reason,
                     "observed": observed, "passed": passed})
        require(passed, "年龄边界失败：" + name)
    for name, value, expected in [
        ("finite_lower", 25.0, True), ("finite_upper", 80.0, True),
        ("rate_nan", float("nan"), False), ("rate_inf", float("inf"), False),
        ("rate_negative", -1.0, False), ("rate_bool", True, False),
        ("rate_too_large", 81.0, False),
        ("rate_huge_integer", 10 ** 1000, False),
    ]:
        observed = finite_in_range(value, 25.0, 80.0)
        require(observed == expected, "有限参数边界失败：" + name)
        rows.append({"case": name, "inputRepr": repr(value), "expected": expected,
                     "observed": observed, "passed": True})
    return rows


def arguments():
    """先解析--help；没有ROS环境也能了解依赖、单位和实验范围。"""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", choices=("all", *CASES), default="all")
    parser.add_argument("--domain-id", type=int, default=216, help="独立本机ROS域，默认216")
    parser.add_argument("--duration-s", type=float, default=3.0, help="每组实际发布窗口，2..8秒")
    parser.add_argument("--rate-hz", type=float, default=40.0, help="发布timer请求频率，25..80Hz")
    parser.add_argument("--discovery-timeout-s", type=float, default=5.0,
                        help="每个worker发现/匹配的单调软期限，1..15秒")
    parser.add_argument("--max-age-ms", type=float, default=120.0,
                        help="门控结果年龄上限，须大于80且不大于200毫秒")
    parser.add_argument("--report", type=Path,
                        default=Path(__file__).resolve().parents[2]
                        / "validation-evidence/slow-consumer-current-validation.json")
    parser.add_argument("--self-test", action="store_true", help="只运行标准库边界断言")
    # 内部worker入口仍由同一文件提供；父进程传入唯一临时目录，不使用shell拼接命令。
    parser.add_argument("--worker", choices=("producer", "consumer"), help=argparse.SUPPRESS)
    parser.add_argument("--control-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--token", help=argparse.SUPPRESS)
    args = parser.parse_args()
    for key, low, high in [("duration_s", 2.0, 8.0), ("rate_hz", 25.0, 80.0),
                           ("discovery_timeout_s", 1.0, 15.0), ("max_age_ms", 80.0, 200.0)]:
        if not finite_in_range(getattr(args, key), low, high):
            parser.error(f"{key}须为[{low},{high}]内的有限数；单位见帮助")
    if args.max_age_ms <= 80.0:
        parser.error("max-age-ms必须大于固定80ms工作预算，留出正的新鲜度余量")
    if not 0 <= args.domain_id <= 232:
        parser.error("domain-id必须位于0..232")
    if args.worker and (args.case == "all" or args.control_dir is None or not args.token):
        parser.error("内部worker缺少单一场景/临时目录/来源标识")
    return args


def save_json(path, value):
    """同目录临时文件加原子替换，避免另一进程读到写到一半的控制JSON。"""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def package_versions():
    """只读取已安装包元数据，不联网、不安装或修改依赖。"""
    from ament_index_python.packages import get_package_share_directory
    versions = {"rclpy": importlib.metadata.version("rclpy")}
    for name in ("rmw_fastrtps_cpp", "rmw", "std_msgs"):
        package = Path(get_package_share_directory(name)) / "package.xml"
        versions[name] = ET.parse(package).getroot().findtext("version")
    return versions


def worker(args):
    """一个worker只有一个角色；慢sleep不可能阻塞另一个进程的发布timer。"""
    role = args.worker
    control = args.control_dir
    outcome = {"role": role, "case": args.case, "pid": os.getpid(), "ppid": os.getppid(),
               "started_ns": time.monotonic_ns(), "status": "failed", "events": [],
               "cleanup": {}, "assertions": []}
    context = node = executor = timer = None
    exit_code = 1
    try:
        # 延迟导入，父进程监督循环不依赖ROS执行器或/clock。
        import rclpy
        from rclpy.clock import Clock
        from rclpy.clock_type import ClockType
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.qos import (DurabilityPolicy, HistoryPolicy, LivelinessPolicy,
                               QoSProfile, ReliabilityPolicy)
        from std_msgs.msg import String

        outcome["versions"] = package_versions()
        context = Context()
        rclpy.init(args=[], context=context)
        suffix = args.token + "_" + args.case.replace("-", "_")
        node = Node(role + "_" + suffix, context=context)
        executor = SingleThreadedExecutor(context=context)
        executor.add_node(node)
        topic = "/slow_consumer_" + suffix + "/samples"
        depth = 1 if args.case == "slow-depth-1" else 10
        delay_ns = 0 if args.case == "normal" else SLOW_NS
        gated = args.case == "slow-gated"
        limit_ns = round(args.max_age_ms * NS_PER_MS)
        # 明确使用传感器式尽力/易失历史，不用Reliable重传来混淆消费吞吐观察。
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST,
                         depth=10 if role == "producer" else depth,
                         reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE,
                         liveliness=LivelinessPolicy.AUTOMATIC)
        outcome["topic"] = topic
        outcome["declaredQoS"] = {"history": "KEEP_LAST", "depth": qos.depth,
                                  "reliability": "BEST_EFFORT", "durability": "VOLATILE",
                                  "liveliness": "AUTOMATIC"}
        outcome["processingDelayNs"] = delay_ns if role == "consumer" else 0
        outcome["ageLimitNs"] = limit_ns
        outcome["gateApplied"] = gated if role == "consumer" else False

        def spin_slice(deadline_ns):
            # spin_once的等待有界；执行中的回调或原生调用仍可越过此软期限。
            remaining = (deadline_ns - time.monotonic_ns()) / NS_PER_S
            if remaining > 0:
                executor.spin_once(timeout_sec=min(0.025, remaining))

        def wait_matched(entity, count_method):
            deadline_ns = time.monotonic_ns() + round(args.discovery_timeout_s * NS_PER_S)
            while count_method() < 1:
                require(time.monotonic_ns() < deadline_ns, "发现/兼容匹配超过软期限")
                spin_slice(deadline_ns)
            outcome["matchedCount"] = count_method()
            outcome["matched_ns"] = time.monotonic_ns()

        if role == "producer":
            publisher = node.create_publisher(String, topic, qos)
            wait_matched(publisher, publisher.get_subscription_count)
            begin_ns = time.monotonic_ns()
            deadline_ns = begin_ns + round(args.duration_s * NS_PER_S)
            outcome["publishWindowStartNs"] = begin_ns

            def publish_sample():
                sampled = time.monotonic_ns()
                if sampled >= deadline_ns:
                    return
                require(len(outcome["events"]) < MAX_EVENTS, "发布事件超出有界样本上限")
                seq = len(outcome["events"])
                payload = {"schema": 1, "source": args.token, "seq": seq,
                           "sample_ns": sampled}
                publisher.publish(String(data=json.dumps(payload, separators=(",", ":"))))
                # publish返回不代表对端完成处理。此后时刻用于检查发送调用自身耗时。
                outcome["events"].append({"seq": seq, "sample_ns": sampled,
                                          "publish_return_ns": time.monotonic_ns()})

            steady = Clock(clock_type=ClockType.STEADY_TIME)
            timer = node.create_timer(1.0 / args.rate_hz, publish_sample, clock=steady)
            while time.monotonic_ns() < deadline_ns:
                spin_slice(deadline_ns)
            timer.cancel()
            outcome["publishWindowEndNs"] = time.monotonic_ns()
            # 让读端知道产生已结束；writer继续存活，供读端排空已接收队列。
            save_json(control / "producer_done.json", {
                "finished_ns": outcome["publishWindowEndNs"],
                "sent": len(outcome["events"])})
            settle_deadline = time.monotonic_ns() + round((DRAIN_S + 2.0) * NS_PER_S)
            while not (control / "consumer_done.json").exists():
                require(time.monotonic_ns() < settle_deadline, "读端排空未在软期限内结束")
                spin_slice(settle_deadline)
        else:
            def receive(message):
                entered = time.monotonic_ns()
                require(len(outcome["events"]) < MAX_EVENTS, "接收事件超出有界样本上限")
                event = {"callback_enter_ns": entered, "work_started": False}
                try:
                    payload = json.loads(message.data)
                    require(isinstance(payload, dict) and payload.get("schema") == 1,
                            "合成消息schema无效")
                    require(payload.get("source") == args.token, "收到非本次来源的消息")
                    seq = payload.get("seq")
                    require(type(seq) is int and 0 <= seq < MAX_EVENTS, "序号无效")
                    event.update(seq=seq, sample_ns=payload.get("sample_ns"))
                    initial = age_decision(event["sample_ns"], entered, limit_ns)
                    event["age_enter_ns"] = initial["age_ns"]
                    if not initial["valid"]:
                        decision, reason = "rejected_invalid", initial["reason"]
                    elif gated and initial["age_ns"] + delay_ns > limit_ns:
                        # 预留已知的80ms模拟工作预算；跳过旧数据可尽快追上新数据。
                        # 预算不是调度保证，因此处理结束仍必须再次检查。
                        decision, reason = "rejected_before_work", "insufficient_age_budget"
                    else:
                        event["work_started"] = True
                        if delay_ns:
                            time.sleep(delay_ns / NS_PER_S)
                        decision, reason = "accepted", "processed_without_gate"
                    ended = time.monotonic_ns()
                    final = age_decision(event["sample_ns"], ended, limit_ns)
                    if event["work_started"] and gated:
                        if not final["valid"] or not final["within_limit"]:
                            decision, reason = "rejected_after_work", final["reason"]
                        else:
                            reason = "fresh_at_processing_end"
                    event.update(processing_end_ns=ended, age_end_ns=final["age_ns"],
                                 callback_duration_ns=ended - entered,
                                 decision=decision, reason=reason)
                except (ValueError, TypeError, AssertionError) as error:
                    # 非法JSON/字段不进入模拟工作；错误只作为合成数据拒绝，不能放行。
                    ended = time.monotonic_ns()
                    event.update(processing_end_ns=ended,
                                 callback_duration_ns=ended - entered,
                                 decision="rejected_invalid", reason=str(error))
                outcome["events"].append(event)

            subscription = node.create_subscription(String, topic, receive, qos)
            wait_matched(subscription, subscription.get_publisher_count)
            # 同机控制文件只负责结束实验，不负责传递被测样本；样本真实经RMW交付。
            outer_deadline = time.monotonic_ns() + round(
                (args.duration_s + DRAIN_S + args.discovery_timeout_s + 2.0) * NS_PER_S)
            drain_deadline = None
            while True:
                now = time.monotonic_ns()
                require(now < outer_deadline, "消费阶段超过单调总软期限")
                done_file = control / "producer_done.json"
                if drain_deadline is None and done_file.exists():
                    finished = json.loads(done_file.read_text())["finished_ns"]
                    drain_deadline = finished + round(DRAIN_S * NS_PER_S)
                if drain_deadline is not None and now >= drain_deadline:
                    break
                spin_slice(min(outer_deadline, drain_deadline or outer_deadline))
            outcome["drainFinishedNs"] = time.monotonic_ns()
        outcome["status"] = "passed"
        exit_code = 0
    except BaseException:
        outcome["error"] = traceback.format_exc(limit=12)[-8000:]
    finally:
        if role == "consumer":
            save_json(control / "consumer_done.json", {"finished_ns": time.monotonic_ns()})
        # 显式顺序：停止执行器 → 销毁node及其端点 → 关闭本worker的独立Context。
        for name, action in (
            ("executor", lambda: executor.shutdown(timeout_sec=0.5) if executor else None),
            ("node", lambda: node.destroy_node() if node else None),
            ("context", lambda: context.shutdown() if context and context.ok() else None),
        ):
            try:
                action()
                outcome["cleanup"][name] = "completed_or_not_created"
            except BaseException as error:
                outcome["cleanup"][name] = repr(error)
                outcome["status"] = "failed"
                exit_code = 1
        outcome["finished_ns"] = time.monotonic_ns()
        save_json(control / (role + ".json"), outcome)
    return exit_code


def distribution(values):
    """统计保留样本的实际分布；线性插值p95，不把一次结果变成性能保证。"""
    values = sorted(values)
    if not values:
        return {"count": 0}
    position = (len(values) - 1) * 0.95
    lower, upper = math.floor(position), math.ceil(position)
    return {"count": len(values), "min": values[0], "median": statistics.median(values),
            "mean": statistics.fmean(values), "p95": values[lower]
            + (values[upper] - values[lower]) * (position - lower), "max": values[-1]}


def inspect_case(case):
    """只断言明确合同和负载前提，不断言特定丢序号或固定快慢倍率。"""
    producer, consumer = case["workers"]["producer"], case["workers"]["consumer"]
    checks = case["assertions"]

    def verify(name, condition, observed):
        checks.append({"name": name, "passed": bool(condition), "observed": observed})

    sent, received = producer.get("events", []), consumer.get("events", [])
    verify("workers_completed", all(w.get("status") == "passed" for w in (producer, consumer)),
           {w["role"]: w.get("status") for w in (producer, consumer)})
    verify("separate_processes", producer["pid"] != consumer["pid"],
           [producer["pid"], consumer["pid"]])
    verify("worker_pids_owned_by_supervisor", all(
           worker.get("ppid") == case["supervisorPid"] and worker["pid"] == child["pid"]
           for child in case["processes"]
           for worker in [case["workers"][child["role"]]]), case["supervisorPid"])
    verify("both_endpoints_matched", all(w.get("matchedCount", 0) >= 1 for w in (producer, consumer)),
           {w["role"]: w.get("matchedCount", 0) for w in (producer, consumer)})
    verify("sufficient_real_samples", len(sent) >= 20 and len(received) >= 10,
           {"sent": len(sent), "received": len(received)})
    sent_by_seq = {e["seq"]: e["sample_ns"] for e in sent}
    verify("producer_sequence_contiguous", [e["seq"] for e in sent] == list(range(len(sent))), len(sent))
    verify("received_matches_real_send", all(e.get("seq") in sent_by_seq and
           e.get("sample_ns") == sent_by_seq[e["seq"]] for e in received), len(received))
    verify("valid_real_ages", all(e.get("decision") != "rejected_invalid" and
           type(e.get("age_enter_ns")) is int and e["age_enter_ns"] >= 0 and
           type(e.get("age_end_ns")) is int and e["age_end_ns"] >= 0 for e in received),
           sum(e.get("decision") == "rejected_invalid" for e in received))
    verify("timestamp_order", all(type(e.get("sample_ns")) is int and
           e["sample_ns"] <= e["callback_enter_ns"]
           <= e["processing_end_ns"] for e in received), len(received))
    intervals = [(b["sample_ns"] - a["sample_ns"]) / NS_PER_MS for a, b in zip(sent, sent[1:])]
    rate = (len(sent) - 1) * NS_PER_S / (sent[-1]["sample_ns"] - sent[0]["sample_ns"]) if len(sent) > 1 else 0.0
    # 这是实验的过载前提：实际源频率必须高于80ms单回调的约12.5Hz吞吐上界。
    verify("source_really_exceeds_slow_capacity", rate > NS_PER_S / SLOW_NS, rate)
    started = [e for e in received if e.get("work_started")]
    accepted = [e for e in received if e["decision"] == "accepted"]
    if case["name"] != "normal":
        verify("slow_work_at_least_80ms", bool(started) and all(
               e["callback_duration_ns"] >= SLOW_NS for e in started), len(started))
    if case["name"] == "slow-gated":
        limit = consumer["ageLimitNs"]
        verify("accepted_output_not_expired", bool(accepted) and all(
               e["age_end_ns"] <= limit for e in accepted),
               {"accepted": len(accepted), "limitNs": limit})
        verify("gate_actually_rejected_samples", any(
               e["decision"].startswith("rejected_") for e in received),
               sum(e["decision"].startswith("rejected_") for e in received))
    else:
        verify("ungated_does_not_discard_for_age", len(accepted) == len(received), len(accepted))
    if case["name"] == "slow-depth-10":
        verify("ungated_deep_history_produces_expired_outputs", any(
               e["age_end_ns"] > consumer["ageLimitNs"] for e in accepted),
               sum(e["age_end_ns"] > consumer["ageLimitNs"] for e in accepted))
    received_ids = [e.get("seq") for e in received]
    case["measurements"] = {
        "sent": len(sent), "callbacks": len(received), "workStarted": len(started),
        "acceptedSyntheticOutputs": len(accepted),
        "rejectedBeforeWork": sum(e["decision"] == "rejected_before_work" for e in received),
        "rejectedAfterWork": sum(e["decision"] == "rejected_after_work" for e in received),
        "sourceObservedHz": rate, "sourceIntervalMs": distribution(intervals),
        "ageAtCallbackMs": distribution([e["age_enter_ns"] / NS_PER_MS for e in received if e.get("age_enter_ns") is not None]),
        "ageAtProcessingEndMs": distribution([e["age_end_ns"] / NS_PER_MS for e in started if e.get("age_end_ns") is not None]),
        "acceptedAgeAtEndMs": distribution([e["age_end_ns"] / NS_PER_MS for e in accepted]),
        "acceptedBeyondAgeLimit": sum(e["age_end_ns"] > consumer.get("ageLimitNs", 0) for e in accepted),
        "sentButNoCallbackSeqs": [e["seq"] for e in sent if e["seq"] not in set(received_ids)],
        "receivedSeqs": received_ids,
    }
    case["passed"] = all(row["passed"] for row in checks) and all(
        child["reaped"] and child["exitCode"] == 0 for child in case["processes"])


def supervise_case(args, name, directory):
    """父进程不导入ROS；即使消费回调阻塞，也能独立监督两个PID。"""
    token = uuid.uuid4().hex[:12]
    result = {"name": name, "token": token, "supervisorPid": os.getpid(),
              "started_ns": time.monotonic_ns(),
              "workers": {}, "processes": [], "assertions": [], "passed": False}
    env = os.environ.copy()
    env.update(ROS_DOMAIN_ID=str(args.domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
               RMW_IMPLEMENTATION="rmw_fastrtps_cpp", RMW_FASTRTPS_USE_QOS_FROM_XML="0")
    for key in ("ROS_LOCALHOST_ONLY", "ROS_STATIC_PEERS"):
        env.pop(key, None)
    children = []
    try:
        for role in ("consumer", "producer"):
            command = [sys.executable, str(Path(__file__).resolve()), "--worker", role,
                       "--case", name, "--domain-id", str(args.domain_id),
                       "--duration-s", str(args.duration_s), "--rate-hz", str(args.rate_hz),
                       "--discovery-timeout-s", str(args.discovery_timeout_s),
                       "--max-age-ms", str(args.max_age_ms), "--control-dir", str(directory),
                       "--token", token]
            log_path = directory / (role + ".log")
            handle = log_path.open("w", encoding="utf-8")
            process = subprocess.Popen(command, env=env, stdout=handle, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            record = {"role": role, "pid": process.pid, "command": command, "signalsSent": []}
            result["processes"].append(record)
            children.append((process, handle, log_path, record))
        # 含ROS导入、发现、发布、排空和关闭余量；到期后只清理本函数创建的PID。
        budget_s = args.discovery_timeout_s + args.duration_s + DRAIN_S + 5.0
        deadline = time.monotonic() + budget_s
        while any(process.poll() is None for process, *_ in children):
            if time.monotonic() >= deadline:
                result["supervisorError"] = f"超过{budget_s}s父进程软期限"
                break
            time.sleep(0.02)
    except BaseException:
        result["supervisorError"] = traceback.format_exc(limit=8)[-4000:]
    finally:
        for process, handle, log_path, record in children:
            if process.poll() is None:
                process.terminate()
                record["signalsSent"].append("SIGTERM")
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    record["signalsSent"].append("SIGKILL")
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                record["cleanupError"] = "kill后仍未在1s内回收；不能声称已清理"
            handle.close()
            record.update(exitCode=process.poll(), reaped=process.poll() is not None)
            logs = log_path.read_text(errors="replace")
            record.update(log=logs[-8000:], logTruncated=len(logs) > 8000)
            worker_file = directory / (record["role"] + ".json")
            if worker_file.exists():
                result["workers"][record["role"]] = json.loads(worker_file.read_text())
            else:
                result["workers"][record["role"]] = {
                    "role": record["role"], "pid": record["pid"], "status": "missing_report", "events": []}
        result["finished_ns"] = time.monotonic_ns()
    inspect_case(result)
    print(json.dumps({"case": name, "passed": result["passed"],
                      "measurements": result["measurements"]}, ensure_ascii=False), flush=True)
    return result


def main():
    args = arguments()
    if args.self_test:
        print(json.dumps({"passed": True, "boundaryTests": boundary_checks()}, ensure_ascii=False))
        return 0
    if args.worker:
        return worker(args)
    report = {
        "schemaVersion": 1, "checkedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "passed": False, "sourceFile": str(Path(__file__).resolve()),
        "sourceSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "invocation": [sys.executable, *sys.argv], "parentPid": os.getpid(),
        "executionContext": "实际运行；以本次进程/事件和退出状态判断，不由静态源码推断",
        "environment": {"ROS_DOMAIN_ID": str(args.domain_id), "ROS_AUTOMATIC_DISCOVERY_RANGE": "LOCALHOST",
                        "RMW_IMPLEMENTATION": "rmw_fastrtps_cpp", "RMW_FASTRTPS_USE_QOS_FROM_XML": "0"},
        "versions": {"python": sys.version, "platform": platform.platform()},
        "parameters": {"durationS": args.duration_s, "requestedRateHz": args.rate_hz,
                       "slowWorkMs": 80.0, "gateMaxAgeMs": args.max_age_ms,
                       "drainS": DRAIN_S, "discoveryTimeoutS": args.discovery_timeout_s,
                       "publisherDepth": 10, "eventLimitPerWorker": MAX_EVENTS},
        "timeContract": {"clock": "time.monotonic_ns；同一主机两进程共享单调时基",
                         "clockImplementation": time.get_clock_info("monotonic").implementation,
                         "nanosecondFields": ["sample_ns", "callback_enter_ns", "processing_end_ns", "age_enter_ns", "age_end_ns"],
                         "crossHostComparable": False,
                         "ageRule": "0<=sample<=now，整数纳秒；NaN/Inf/bool/负值/超范围拒绝；age<=limit包含上界",
                         "gateRule": "进入时age+80ms预算<=上限才开始；处理结束再次age<=上限才接受合成结果"},
        "boundaryTests": boundary_checks(), "cases": [],
        "limits": [
            "独立进程、同机LOCALHOST/FastDDS、String合成负载；未连接设备或仿真。",
            "采样时刻为发布回调生成合成消息的时刻；不是传感器曝光/硬件采样时刻。",
            "monotonic_ns不能直接跨主机比较，也不能与ROS /clock或日期时间相减。",
            "BEST_EFFORT/KEEP_LAST的丢序号和分布是本次观察，不承诺其他RMW的精确丢序列或固定性能比。",
            "数据年龄只说明该合成样本的新鲜度；门控返回拒绝或不接受结果不证明硬件停车。",
            "所有内部期限均为单调软期限，不能抢占原生调用或已执行回调；父进程及外层timeout另作保护。",
        ],
    }
    try:
        with tempfile.TemporaryDirectory(prefix="ros2-slow-consumer-") as temporary:
            for name in CASES if args.case == "all" else (args.case,):
                directory = Path(temporary) / name
                directory.mkdir()
                report["cases"].append(supervise_case(args, name, directory))
        report["passed"] = all(case["passed"] for case in report["cases"])
        report["summary"] = [{"case": case["name"], "passed": case["passed"],
                              **case["measurements"]} for case in report["cases"]]
        by_name = {case["name"]: case["measurements"] for case in report["cases"]}
        if all(name in by_name for name in CASES):
            report["comparison"] = {
                "observedSourceHz": {name: m["sourceObservedHz"] for name, m in by_name.items()},
                "callbackAgeMeanMs": {name: m["ageAtCallbackMs"].get("mean") for name, m in by_name.items()},
                "acceptedEndAgeP95Ms": {name: m["acceptedAgeAtEndMs"].get("p95") for name, m in by_name.items()},
                "acceptedExpiredCounts": {name: m["acceptedBeyondAgeLimit"] for name, m in by_name.items()},
                "interpretation": "并列比较本次实测分布；不要求固定丢序列或固定倍率。源实际频率独立验证，门控验收看合成结果在处理结束时是否仍未过期。",
            }
    except BaseException:
        report["error"] = traceback.format_exc(limit=12)[-8000:]
    finally:
        report["finishedAt"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        # 报告路径由命令行指定；原始事件已收进报告，临时目录仅保存本次自建子进程IPC。
        save_json(args.report, report)
        print(json.dumps({"passed": report["passed"], "report": str(args.report),
                          "sourceSha256": report["sourceSha256"]}, ensure_ascii=False), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
