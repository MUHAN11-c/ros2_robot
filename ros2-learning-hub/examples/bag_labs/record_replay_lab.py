#!/usr/bin/env python3
"""有界rosbag2实测：真实CLI录制→关闭读回→停原源→暂停就绪→筛选回放。

输入：合成PointStamped/Int32/缓存String及软件Clock，不接任何设备。
输出：/tmp中新bag、日志、JSON；指定--report才能写工作区验证报告。
顺序：两种时钟/存储正例、缓存QoS反例、两种回放、显式存储字段探针。
单位：point.x为合成米且整数值兼作序号；Header/记录时间ns；等待期限用monotonic秒。
边界：6条有限输入和本机独立域，不能证明磁盘吞吐、多机、真实传感器同步或恢复。
      --help仅用标准库；ROS导入在解析之后。父中断有清理分支，但需单独注入才算验证。
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
HUB = HERE.parents[1]
INPUT, DERIVED, STATIC = '/bag_lab/input', '/bag_lab/derived', '/bag_lab/static'
TOPICS = (INPUT, DERIVED, STATIC)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--domain-id', type=int, default=231, help='本例专用域0..232，默认231')
    parser.add_argument('--report', type=Path, help='JSON报告；省略则写本次/tmp目录')
    parser.add_argument('--total-timeout-s', type=float, default=75.0, help='总软期限秒，范围30..180')
    options = parser.parse_args()
    if not 0 <= options.domain_id <= 232:parser.error('domain-id须在0..232')
    if not 30 <= options.total_timeout_s <= 180:parser.error('总软期限须在30..180秒')
    return options


class Experiment:
    """显式Context/Executor；只管理本实例创建的节点和进程组。"""
    def __init__(self, options, report, output):
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.signals import SignalHandlerOptions
        self.rclpy, self.report, self.output = rclpy, report, output
        self.deadline = time.monotonic() + options.total_timeout_s
        self.context = Context()
        # Python父进程保留KeyboardInterrupt；自建Context不隐式装全局ROS信号处理器。
        rclpy.init(context=self.context, signal_handler_options=SignalHandlerOptions.NO)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.nodes, self.processes = [], []

    def node(self, name, simulation=False):
        from rclpy.node import Node
        from rclpy.parameter import Parameter
        node = Node(name, context=self.context,
                    parameter_overrides=[Parameter('use_sim_time', value=simulation)])
        self.executor.add_node(node)
        self.nodes.append(node)
        return node

    def destroy(self, node):
        self.executor.remove_node(node)
        node.destroy_node()
        self.nodes.remove(node)

    def pump(self, seconds):
        """外层只用单调时间，/clock零值或暂停不会冻结验收等待。"""
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            if time.monotonic() >= self.deadline:raise TimeoutError('实验总软期限到达')
            # 防止临界时刻负数被解释为无限等待，所有spin均保持非负有界。
            self.executor.spin_once(timeout_sec=max(0.0, min(0.02, until - time.monotonic())))

    def wait(self, condition, label, seconds=8.0):
        until = min(self.deadline, time.monotonic() + seconds)
        while not condition():
            if time.monotonic() >= until:raise TimeoutError(label)
            self.pump(0.025)

    def start(self, name, argv):
        """直接argv，不经shell；输出落本例文件，不用PIPE造成缓冲阻塞。"""
        path = self.output / (name + '.log')
        stream = path.open('wb')
        process = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        item = dict(name=name, argv=argv, pid=process.pid, signals=[], logFile=str(path))
        self.processes.append((process, stream, item))
        self.report.setdefault('processes', []).append(item)
        return process

    def stop(self, process, graceful=True):
        """已有退出不补信号；先对本次独立进程组发一次INT，再有界升级并记录。"""
        _, stream, item = next(p for p in self.processes if p[0] is process)
        def send(sig):
            # poll与kill之间进程可能自然退出；该竞态不应跳过其余资源清理。
            try:
                os.killpg(process.pid, sig)
                item['signals'].append(signal.Signals(sig).name)
            except ProcessLookupError:
                item.setdefault('signalRaces', []).append(signal.Signals(sig).name)
        if process.poll() is None and graceful:
            send(signal.SIGINT)
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            send(signal.SIGTERM)
            try:process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                send(signal.SIGKILL)
                process.wait(timeout=2.0)
        stream.close()
        log = Path(item['logFile']).read_bytes()
        item.update(returnCode=process.returncode, logBytes=len(log), logSha256=hashlib.sha256(log).hexdigest(),
                    logTail=log[-16000:].decode(errors='replace'), pidGone=not Path('/proc', str(process.pid)).exists())
        if len(log) > 4 * 1024 * 1024:raise ValueError('日志超出教学大小上限')
        return process.returncode

    def close(self):
        for process, _, _ in self.processes:
            self.stop(process)
        for node in list(self.nodes):self.destroy(node)
        self.executor.shutdown(timeout_sec=2.0)
        if self.context.ok():self.context.shutdown()
        self.report['cleanup'] = dict(nodesRemaining=len(self.nodes), contextValid=self.context.ok(),
            processPidsGone=all(p[2].get('pidGone') for p in self.processes),
            escalatedSignals=[p[2]['name'] for p in self.processes if any(s != 'SIGINT' for s in p[2]['signals'])])
        assert self.report['cleanup']['processPidsGone'] and not self.context.ok()

    def record(self, name, storage, simulation, cached):
        from geometry_msgs.msg import PointStamped
        from std_msgs.msg import Int32, String
        from rosgraph_msgs.msg import Clock
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
        from inspect_bag import read_closed_bag

        source = self.node('bag_lab_source_' + name)
        reliable = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)
        transient = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                               durability=DurabilityPolicy.TRANSIENT_LOCAL)
        data_pub = source.create_publisher(PointStamped, INPUT, reliable)
        output_pub = source.create_publisher(Int32, DERIVED, reliable)
        static_pub = source.create_publisher(String, STATIC, transient)
        clock_pub = source.create_publisher(Clock, '/clock', reliable) if simulation else None
        # 在录制器存在之前只发布一次；仍持有发布者，transient缓存才有提供者。
        static_pub.publish(String(data='calibration:v1'))
        self.pump(0.12)
        target = self.output / name
        qos = HERE / ('qos_transient.yaml' if cached else 'qos_volatile.yaml')
        argv = ['ros2', 'bag', 'record', '--storage', storage, '--output', str(target),
                '--node-name', 'bag_lab_recorder', '--disable-keyboard-controls', '--max-cache-size', '0',
                '--qos-profile-overrides-path', str(qos)]
        if simulation:argv.append('--use-sim-time')
        argv += ['--topics', *TOPICS]
        process = self.start(name, argv)
        result = dict(name=name, storage=storage, useSimTime=simulation, requestCachedStatic=cached,
                      bagDirectory=str(target), beforeClock=[], expectedInputFields={})
        self.report.setdefault('recordings', []).append(result)

        def publish(sequence):
            # Header从1000秒开始，每序号增加10ms；与记录用的10秒软件钟故意不同。
            stamp_ns = 1000 * 10**9 + sequence * 10_000_000
            message = PointStamped()
            message.header.frame_id = 'synthetic_frame'
            message.header.stamp.sec, message.header.stamp.nanosec = divmod(stamp_ns, 10**9)
            message.point.x = float(sequence)
            data_pub.publish(message)
            output_pub.publish(Int32(data=sequence))
            # DDS序列化的对齐padding不具有消息字段语义；不另序列化后误比原始SHA。
            return dict(headerNs=stamp_ns, frameId=message.header.frame_id,
                        xM=message.point.x, yM=message.point.y, zM=message.point.z)

        def clock(ns):
            value = Clock()
            value.clock.sec, value.clock.nanosec = divmod(ns, 10**9)
            clock_pub.publish(value)

        if simulation:
            self.wait(lambda: clock_pub.get_subscription_count() >= 1, '录制器/clock订阅未发现')
            for stage, value, sentinels in [('no_clock', None, [100, 101]), ('zero_clock', 0, [200, 201])]:
                if value is not None:
                    for _ in range(4):clock(value);self.pump(0.03)
                for sequence in sentinels:publish(sequence);self.pump(0.10)
                counts = [p.get_subscription_count() for p in (data_pub, output_pub, static_pub)]
                result['beforeClock'].append(dict(stage=stage, sentSequences=sentinels, dataSubscriptions=counts))
                assert counts == [0, 0, 0], '正值clock前不应已建立数据订阅；按实际版本重查'
            # 只有正值才令ROS Clock.started成立；等待数据端点，而不只看一条日志。
            until = time.monotonic() + 8.0
            while min(p.get_subscription_count() for p in (data_pub, output_pub, static_pub)) < 1:
                if time.monotonic() >= until:raise TimeoutError('正值clock后数据端点未发现')
                clock(10 * 10**9)
                self.pump(0.05)
        else:
            self.wait(lambda: min(p.get_subscription_count() for p in (data_pub, output_pub, static_pub)) >= 1,
                      '普通录制数据端点未发现')
        for sequence in range(6):
            if simulation:
                for _ in range(3):clock(10 * 10**9 + sequence * 250_000_000);self.pump(0.025)
            result['expectedInputFields'][str(sequence)] = publish(sequence)
            self.pump(0.12)
        self.pump(0.30)
        assert process.poll() is None, '录制器在主动停止前意外退出'
        code = self.stop(process)
        assert code in (0, 130), f'录制关闭异常退出{code}'
        self.destroy(source)  # 回放前销毁原发布者；后续还核图上端点为零。
        bag = read_closed_bag(target, storage)
        result['readback'] = bag
        expected = {INPUT: 6, DERIVED: 6}
        if cached:expected[STATIC] = 1
        assert bag['counts'] == expected
        assert bag['metadataCount'] == len(bag['records']) == sum(expected.values())
        for topic in TOPICS:assert bag['metadataTopics'].get(topic, 0) == expected.get(topic, 0)
        assert [r['data'] for r in bag['records'] if r['topic'] == DERIVED] == list(range(6))
        assert [r['data'] for r in bag['records'] if r['topic'] == STATIC] == (['calibration:v1'] if cached else [])
        inputs = [r for r in bag['records'] if r['topic'] == INPUT]
        assert [r['sequence'] for r in inputs] == list(range(6))
        for item in inputs:
            assert all(item[key] == value for key, value in result['expectedInputFields'][str(item['sequence'])].items())
            assert item['receivedNs'] != item['headerNs']
            if simulation:assert item['receivedNs'] == 10 * 10**9 + item['sequence'] * 250_000_000
            else:assert item['receivedNs'] > 1_000_000_000 * 10**9
        # info是真实CLI运行；仅作元数据交叉检查，不把文字输出当载荷一致性证明。
        info = self.start(name + '_info', ['ros2', 'bag', 'info', str(target)])
        self.wait(lambda: info.poll() is not None, 'bag info未退出')
        assert self.stop(info, graceful=False) == 0
        result['passed'] = True
        return result

    def replay(self, recording, filtered, with_clock):
        from geometry_msgs.msg import PointStamped
        from std_msgs.msg import Int32, String
        from rosgraph_msgs.msg import Clock
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
        from rosbag2_interfaces.srv import Resume

        name = 'play_filtered_clock' if filtered else 'play_all_no_clock'
        observer = self.node('bag_lab_observer_' + name, simulation=True)
        self.wait(lambda: all(observer.count_publishers(t) == 0 for t in (*TOPICS, '/clock')),
                  '回放前仍存在原输入或clock发布者')
        received, clocks = {t: [] for t in TOPICS}, []
        def on_input(message):
            received[INPUT].append(dict(sequence=int(message.point.x),
                headerNs=message.header.stamp.sec * 10**9 + message.header.stamp.nanosec,
                frameId=message.header.frame_id, xM=message.point.x, yM=message.point.y, zM=message.point.z))
        reliable = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)
        transient = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        subscriptions = {
            INPUT: observer.create_subscription(PointStamped, INPUT, on_input, reliable),
            DERIVED: observer.create_subscription(Int32, DERIVED, lambda m: received[DERIVED].append(m.data), reliable),
            STATIC: observer.create_subscription(String, STATIC, lambda m: received[STATIC].append(m.data), transient)}
        clock_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        clock_subscription = observer.create_subscription(Clock, '/clock',
            lambda m: clocks.append(m.clock.sec * 10**9 + m.clock.nanosec), clock_qos)
        assert observer.get_clock().now().nanoseconds == 0
        argv = ['ros2', 'bag', 'play', recording['bagDirectory'], '--start-paused',
                '--disable-keyboard-controls', '--qos-profile-overrides-path', str(HERE / 'qos_transient.yaml'),
                '--wait-for-all-acked', '1000']
        if with_clock:argv += ['--clock', '40', '--rate', '2.0']
        if filtered:argv += ['--topics', INPUT]
        process = self.start(name, argv)
        services = []
        def ready():
            nonlocal services
            services = [n for n, types in observer.get_service_names_and_types() if 'rosbag2_interfaces/srv/Resume' in types]
            selected = [INPUT] if filtered else list(TOPICS)
            return (len(services) == 1 and observer.count_publishers(INPUT) == 1
                    and all(subscriptions[t].get_publisher_count() == 1 for t in selected)
                    and (not with_clock or clock_subscription.get_publisher_count() == 1))
        self.wait(ready, '暂停播放器的端点或Resume服务未就绪')
        self.pump(0.25)
        assert all(not r for r in received.values()), '暂停期间不应已重发数据'
        endpoints = {t: observer.count_publishers(t) for t in (*TOPICS, '/clock')}
        assert endpoints[DERIVED] == (0 if filtered else 1)
        assert endpoints[STATIC] == (0 if filtered else 1)
        assert endpoints['/clock'] == (1 if with_clock else 0)
        matched = {t: subscriptions[t].get_publisher_count() for t in TOPICS}
        client = observer.create_client(Resume, services[0])
        self.wait(lambda: client.service_is_ready(), 'Resume客户端尚未发现服务')
        future = client.call_async(Resume.Request())
        self.wait(future.done, 'Resume应答未到')
        assert future.exception() is None
        self.wait(lambda: process.poll() is not None, '回放未自然结束', seconds=12.0)
        assert self.stop(process, graceful=False) == 0
        self.pump(0.25)
        assert [r['sequence'] for r in received[INPUT]] == list(range(6))
        assert received[DERIVED] == ([] if filtered else list(range(6)))
        assert received[STATIC] == ([] if filtered else ['calibration:v1'])
        for item in received[INPUT]:
            assert all(item[key] == value for key, value in recording['expectedInputFields'][str(item['sequence'])].items())
        now = observer.get_clock().now().nanoseconds
        if with_clock:
            assert clocks and 10 * 10**9 <= now < 12 * 10**9
        else:assert clocks == [] and now == 0, 'Header有时间不等于节点自动收到/clock'
        result = dict(name=name, filterInputOnly=filtered, generatedClock=with_clock, pausedDataCount=0,
                      publishers=endpoints, matchedSubscriptionsAtResume=matched,
                      received=received, clocksNs=clocks, observerRosTimeNs=now,
                      passed=True)
        self.report.setdefault('playbacks', []).append(result)
        self.destroy(observer)


def main():
    options = arguments()
    output = Path(tempfile.mkdtemp(prefix='ros2-bag-lab-'))
    report_path = options.report or output / 'report.json'
    # 仅更改本进程及其子进程的发现环境，不记录全部用户环境。
    os.environ.update(ROS_DOMAIN_ID=str(options.domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',
                      RMW_IMPLEMENTATION='rmw_fastrtps_cpp', ROS_LOG_DIR=str(output / 'ros-logs'))
    os.environ.pop('ROS_LOCALHOST_ONLY', None)
    report = dict(checkedAt=datetime.now(timezone.utc).isoformat(), passed=False, outputDirectory=str(output),
                  environment={k: os.environ[k] for k in ('ROS_DOMAIN_ID', 'ROS_AUTOMATIC_DISCOVERY_RANGE', 'RMW_IMPLEMENTATION')},
                  python=platform.python_version(), parameters=dict(inputCount=6, clockStepNs=250_000_000),
                  sourceHashes=[dict(path=p.relative_to(HUB).as_posix(), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                                for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in ('.py', '.yaml', '.md')],
                  limits=['本机有限合成输入，无真实采集、GUI海龟或完整仿真。',
                          '不是吞吐/压缩/磁盘恢复、网络校时、跨机或安全证明。',
                          '存储字段探针为显式Writer输入；send/source时间不是Header采样时间或已测网络时延。',
                          '父SIGINT/原生挂起清理分支尚未注入；常规子进程退出与节点清理另列。'])
    started, experiment, code = time.monotonic(), None, 1
    try:
        report['versions'] = {name: ET.parse(Path('/opt/ros/jazzy/share') / name / 'package.xml').findtext('version')
                              for name in ('rosbag2_transport', 'rosbag2_py', 'ros2bag', 'rosbag2_storage_mcap', 'rosbag2_storage_sqlite3', 'rclpy')}
        experiment = Experiment(options, report, output)
        normal = experiment.record('system_sqlite', 'sqlite3', False, True)
        simulation = experiment.record('sim_mcap', 'mcap', True, True)
        experiment.record('late_volatile_mcap', 'mcap', False, False)
        experiment.replay(normal, filtered=False, with_clock=False)
        experiment.replay(simulation, filtered=True, with_clock=True)
        from storage_fields import probe
        report['storageFields'] = probe(output / 'storage_fields')
        report['passed'], code = True, 0
    except KeyboardInterrupt:
        report['interrupted'], code = True, 130
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if experiment:
            try:experiment.close()
            except Exception:
                report['cleanupError'] = traceback.format_exc()
                report['passed'], code = False, 1
        report['durationS'] = time.monotonic() - started
        if report_path.exists():
            old = json.loads(report_path.read_text())
            report['previousAttempts'] = old.get('previousAttempts', []) + [{k: v for k, v in old.items() if k != 'previousAttempts'}]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=report['passed'], report=str(report_path), durationS=report['durationS'],
                         recordings=len(report.get('recordings', [])), playbacks=len(report.get('playbacks', [])))), flush=True)
    if report.get('error'):print(report['error'])
    return code


if __name__ == '__main__':
    raise SystemExit(main())
