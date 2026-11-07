"""真实launch_testing：1个active话题合同+1个post-shutdown退出合同。

ReadyToTest只通知框架开始运行测试；业务标记、DDS端点和真实输出分别验证。
所有本地等待基于monotonic秒；测试只使用唯一命名空间的软件Twist和轮速主题。
"""
import json
import math
import os
from pathlib import Path
import sys
import time
import unittest
import uuid

import launch
import launch_ros.actions
import launch_testing
import launch_testing.actions
import launch_testing.asserts
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64MultiArray
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from wheel_reader import decode_pair


def generate_test_description():
    namespace = 'testing_lab_' + uuid.uuid4().hex[:10]
    processor = launch_ros.actions.Node(
        package='learning_testing_lab', executable='wheel_processor', namespace=namespace,
        name='wheel_processor', output='screen',
        parameters=[{'suppress_ready': os.environ.get('TESTING_LAB_READY_FAULT', '0') == '1'}])
    return launch.LaunchDescription([processor, launch_testing.actions.ReadyToTest()]), {
        'processor': processor, 'namespace': namespace}


class TestWheelTopicContract(unittest.TestCase):
    def setUp(self):
        self.context = Context()
        self.context.init(args=[], initialize_logging=False)
        self.node = Node('bounded_wheel_probe', context=self.context,
                         enable_rosout=False, start_parameter_services=False)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.executor.add_node(self.node)
        self.publisher = self.subscription = None

    def tearDown(self):
        # 即便就绪断言失败也执行fixture清理；不把destroy节点当成被测进程已退出。
        self.executor.remove_node(self.node)
        self.executor.shutdown(timeout_sec=0.0)
        if self.publisher is not None:
            self.node.destroy_publisher(self.publisher)
        if self.subscription is not None:
            self.node.destroy_subscription(self.subscription)
        self.node.destroy_node()
        if self.context.ok():
            self.context.shutdown()

    def test_ready_and_known_twist(self, processor, namespace, proc_output):
        # 故障构建隐藏此业务标记，原样测试应在2.5秒后失败；测试不分支放宽预期。
        proc_output.assertWaitFor('WHEEL_PROCESSOR_READY', process=processor, timeout=2.5)
        observed = []
        self.publisher = self.node.create_publisher(Twist, f'/{namespace}/input_twist', 10)
        self.subscription = self.node.create_subscription(
            Float64MultiArray, f'/{namespace}/wheel_rates', lambda msg: observed.append(list(msg.data)), 10)
        endpoint_deadline = time.monotonic() + 4.0
        while self.publisher.get_subscription_count() < 1:
            self.assertLess(time.monotonic(), endpoint_deadline, '被测输入订阅没有就绪')
            self.executor.spin_once(timeout_sec=0.02)
        command = Twist()
        command.linear.x = 0.6   # m/s；软件输入，不是/cmd_vel。
        command.angular.z = 0.5  # rad/s；轮距0.4m，轮半径0.1m。
        deadline, next_send, sent = time.monotonic() + 4.0, 0.0, 0
        while not observed and time.monotonic() < deadline:
            if time.monotonic() >= next_send:
                self.publisher.publish(command)
                sent += 1
                next_send = time.monotonic() + 0.05  # 最多约20Hz，等待真正输出后立即结束。
            self.executor.spin_once(timeout_sec=0.02)
        self.assertTrue(observed, '未收到由真实软件输入触发的轮速输出')
        pair = decode_pair(observed[0])
        self.assertTrue(math.isclose(pair.left_rad_s, 5.0, rel_tol=0.0, abs_tol=1e-12))
        self.assertTrue(math.isclose(pair.right_rad_s, 7.0, rel_tol=0.0, abs_tol=1e-12))
        first_pair = observed[0]
        # 第二种真实输入可发现“节点无视输入，只固定输出5/7”的假实现。先前排队消息
        # 可能晚到，因此等待匹配零输入的输出，不把第一条任意消息当成功。
        observed.clear()
        zero = Twist()
        deadline, next_send = time.monotonic() + 4.0, 0.0
        zero_pair = None
        while time.monotonic() < deadline:
            if time.monotonic() >= next_send:
                self.publisher.publish(zero)
                sent += 1
                next_send = time.monotonic() + 0.05
            self.executor.spin_once(timeout_sec=0.02)
            candidates = [decode_pair(values) for values in observed]
            if any(p.left_rad_s == 0.0 and p.right_rad_s == 0.0 for p in candidates):
                zero_pair = [0.0, 0.0]
                break
        self.assertIsNotNone(zero_pair, '修改软件输入后未得到对应零轮速')
        print('TESTING_LAB_OBSERVATION ' + json.dumps(dict(
            namespace=namespace, input_m_s=0.6, input_rad_s=0.5,
            expected_rad_s=[5.0, 7.0], actual_rad_s=first_pair, zero_actual_rad_s=zero_pair,
            sent_commands=sent, received_messages=len(observed)), ensure_ascii=False), flush=True)
        # 仅供独立父SIGINT清理检查保持真实测试进程存活；正常测试默认0，不改变被测节点逻辑。
        hold_s = float(os.environ.get('TESTING_LAB_PROBE_HOLD_SECONDS', '0'))
        self.assertTrue(math.isfinite(hold_s) and 0.0 <= hold_s <= 5.0)
        end = time.monotonic() + hold_s
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.02)


@launch_testing.post_shutdown_test()
class TestWheelProcessExit(unittest.TestCase):
    def test_process_exits_cleanly(self, proc_info):
        # 框架已关闭被测进程，随后独立检查退出码；active断言通过不是退出证明。
        launch_testing.asserts.assertExitCodes(proc_info, allowable_exit_codes=[0])
