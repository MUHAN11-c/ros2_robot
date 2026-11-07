#!/usr/bin/env python3
"""用真实 rclpy 端点验证 QoS 合同；不会连接机器人。

输入：--case 选择场景，--domain 选择独立ROS域，--timeout为每个等待阶段的单调秒。
输出：JSON包含声明/发现元数据、匹配数、发送值和收到值；断言失败返回非零。
单位：Int32样本仅为无量纲标记41/42/99/序号；depth是条数，所有期限单位为秒。
执行顺序：固定本机发现与RMW → 建立独立Context → 每例建立两个节点 → 断言 → 销毁。
范围：单进程两个节点经RMW通信，未启用进程内优化；不证明跨进程/跨机网络质量。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import time
import uuid


CASES = (
    'reliability-mismatch', 'reliability-fixed', 'reliable-to-best-effort',
    'durability-mismatch', 'transient-history', 'volatile-late', 'writer-recreated',
)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('all', *CASES), default='all')
    parser.add_argument('--domain', type=int, default=213)
    parser.add_argument('--timeout', type=float, default=5.0)
    parser.add_argument('--output', type=Path, help='可选JSON报告路径；不会覆盖任何ROS配置')
    args = parser.parse_args()
    if not 0 <= args.domain <= 232:
        parser.error('教学域编号必须在0..232；请选没有其他练习的域')
    if not math.isfinite(args.timeout) or not 0.5 <= args.timeout <= 30.0:
        parser.error('每阶段期限必须是[0.5,30]内的有限秒数')
    return args


def main():
    if not __debug__:
        raise RuntimeError('本实验用assert检查证据，不能使用-O关闭断言')
    args = arguments()
    # 只改变本进程环境；不停止daemon，不访问或修改用户持久配置。
    os.environ['ROS_DOMAIN_ID'] = str(args.domain)
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    os.environ.pop('ROS_LOCALHOST_ONLY', None)  # 避免旧变量覆盖Jazzy的发现范围配置。
    os.environ['RMW_IMPLEMENTATION'] = 'rmw_fastrtps_cpp'
    os.environ.pop('ROS_STATIC_PEERS', None)
    # 延迟导入：没有ROS的电脑仍能查看--help；实际实验需要source Jazzy。
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import (
        DurabilityPolicy, HistoryPolicy, LivelinessPolicy, QoSProfile,
        QoSCompatibility, ReliabilityPolicy, qos_check_compatible,
    )
    from std_msgs.msg import Int32

    def profile(reliable=True, durable=False):
        # 明确关键策略；整型QoS=1仅设置历史深度，不会自动变成尽力或持久化。
        return QoSProfile(
            history=HistoryPolicy.KEEP_LAST, depth=1,
            reliability=ReliabilityPolicy.RELIABLE if reliable else ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL if durable else DurabilityPolicy.VOLATILE,
            liveliness=LivelinessPolicy.AUTOMATIC,
        )

    def describe(qos):
        return dict(reliability=qos.reliability.name, durability=qos.durability.name,
                    history=qos.history.name, depth=qos.depth)

    context = Context()
    rclpy.init(args=[], context=context)
    records = []
    try:
        for case in CASES if args.case == 'all' else (args.case,):
            started = time.monotonic()
            token = uuid.uuid4().hex[:10]
            topic = '/qos_contract_' + token  # 每例唯一名称，隔离旧节点和CLI观察者。
            writer = Node('qos_writer_' + token, context=context)
            reader = Node('qos_reader_' + token, context=context)
            executor = SingleThreadedExecutor(context=context)
            executor.add_node(writer)
            executor.add_node(reader)
            sent, received = [], []
            offered = profile(reliable=case not in ('reliability-mismatch', 'reliability-fixed'),
                              durable=case in ('transient-history', 'writer-recreated'))
            requested = profile(reliable=case not in ('reliability-fixed', 'reliable-to-best-effort'),
                                durable=case in ('durability-mismatch', 'transient-history', 'writer-recreated'))
            publisher = writer.create_publisher(Int32, topic, offered)
            compatibility, reason = qos_check_compatible(offered, requested)

            def spin_until(predicate, label):
                # 期限用monotonic；spin只处理短回调，不在回调中递归spin或睡眠。
                deadline = time.monotonic() + args.timeout
                while not predicate():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise AssertionError(f'{case}: {label}在{args.timeout}s内未成立')
                    executor.spin_once(timeout_sec=min(0.03, remaining))

            def observe_for(seconds, publish=None):
                # 负向断言限定观察窗口，不能把“暂时没收到”说成任意时间永远不会收到。
                deadline = time.monotonic() + seconds
                next_publish = time.monotonic()
                while time.monotonic() < deadline:
                    now = time.monotonic()
                    if publish is not None and now >= next_publish:
                        publish()
                        # 约33Hz的有限测试负载；不能因spin立即处理回调便无界快速发布。
                        next_publish = now + 0.03
                    wait = min(0.03, max(0.0, deadline-time.monotonic()))
                    if publish is not None:
                        wait = min(wait, max(0.0, next_publish-time.monotonic()))
                    executor.spin_once(timeout_sec=wait)

            def send(value):
                message = Int32()
                message.data = value
                publisher.publish(message)
                sent.append(value)

            try:
                late = case in ('transient-history', 'volatile-late', 'writer-recreated')
                if late:
                    assert publisher.get_subscription_count() == 0
                    send(41)
                    send(42)  # depth=1应仅留42；两个旧值均不在订阅创建之后补发。
                if case == 'writer-recreated':
                    # 销毁拥有缓存的旧writer，再创建空缓存的新writer；节点名相同不延续缓存。
                    assert writer.destroy_publisher(publisher)
                    publisher = writer.create_publisher(Int32, topic, offered)
                subscription = reader.create_subscription(
                    Int32, topic, lambda msg: received.append(msg.data), requested)
                spin_until(lambda: len(reader.get_publishers_info_by_topic(topic)) == 1
                           and len(writer.get_subscriptions_info_by_topic(topic)) == 1,
                           '两个端点在ROS图中均被发现')
                actual_offered = reader.get_publishers_info_by_topic(topic)[0].qos_profile
                actual_requested = writer.get_subscriptions_info_by_topic(topic)[0].qos_profile
                # 图查询可返回history=UNKNOWN/depth=0，表示这部分元数据不可用。
                # 不把它当“真实深度为0”；reliability/durability必须与显式合同一致。
                for discovered, declared in ((actual_offered, offered), (actual_requested, requested)):
                    assert discovered.reliability == declared.reliability
                    assert discovered.durability == declared.durability
                mismatch = case in ('reliability-mismatch', 'durability-mismatch')
                if mismatch:
                    assert compatibility == QoSCompatibility.ERROR, reason
                    # 有发现证据、明确策略冲突、持续发送和零匹配，共同解释无数据。
                    observe_for(0.6, lambda: send(len(sent)))
                    assert sent and not received
                    assert publisher.get_subscription_count() == 0
                    assert subscription.get_publisher_count() == 0
                else:
                    assert compatibility != QoSCompatibility.ERROR, reason
                    spin_until(lambda: publisher.get_subscription_count() == 1
                               and subscription.get_publisher_count() == 1, '端点成功匹配')
                    if case == 'transient-history':
                        # 等待旧样本时不再publish；排除靠周期重发而非历史交付的伪证明。
                        spin_until(lambda: 42 in received, '晚加入获得历史值42')
                        assert sent == [41, 42] and received == [42]
                    elif case in ('volatile-late', 'writer-recreated'):
                        # 标记99证明新链路正常；旧值42未到才具有可解释的历史边界意义。
                        observe_for(0.6, lambda: send(99))
                        assert 99 in received and 41 not in received and 42 not in received
                    else:
                        # 只需递增且去重后至少三条；不把有限本机成功率当可靠性的全局证明。
                        observe_for(0.6, lambda: send(len(sent)))
                        assert len(set(received)) >= 3
                        assert received == sorted(received)
                records.append(dict(case=case, passed=True, elapsed_s=round(time.monotonic()-started, 6),
                                    topic=topic, declaredOffered=describe(offered), declaredRequested=describe(requested),
                                    discoveredOffered=describe(actual_offered), discoveredRequested=describe(actual_requested),
                                    compatibility=compatibility.name, compatibilityReason=reason,
                                    discoveredPublishers=1, discoveredSubscriptions=1,
                                    matchedSubscriptions=publisher.get_subscription_count(),
                                    matchedPublishers=subscription.get_publisher_count(), sent=sent, received=received))
            finally:
                # 先让执行器不再调度两个节点，再释放端点；只清理本例创建的对象。
                executor.remove_node(reader)
                executor.remove_node(writer)
                executor.shutdown(timeout_sec=0.0)
                reader.destroy_node()
                writer.destroy_node()
    finally:
        if context.ok():
            rclpy.shutdown(context=context)
    report = dict(checkedAt=time.strftime('%Y-%m-%d'), passed=True, sourceFile=Path(__file__).name,
                  sourceSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  rclpyVersion=importlib.metadata.version('rclpy'),
                  domain=args.domain, rmw='rmw_fastrtps_cpp', discovery='LOCALHOST',
                  processCount=1, nodeCountPerCase=2, results=records,
                  limits=['单进程本机ROS端点实验，未验证跨进程/跨机网络、性能或硬实时。',
                          '未运行机器人、传感器或执行器；负向观察窗口为0.6秒。',
                          '发现元数据可能缺少history/depth；本例用预发布41/42的实际交付检验有限历史行为。',
                          '不兼容事件回调支持随RMW而异，本例不把日志或事件是否出现作为唯一断言。'])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
