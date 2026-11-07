#!/usr/bin/env python3
"""ROS 2 Jazzy / Nav2 的有界单目标教学客户端，只用于已检查的仿真。

输入：--goal X Y YAW，X/Y 为 --frame 中的米，YAW 为绕 +Z 轴的弧度。
输出：逐行 JSON 协议事件和一条 summary；软件结果不证明物理机器人已停车。
前提：用户先在 RViz 等界面明确设置初始定位，并检查 TF、地图、生命周期与时钟。
本程序不发布 initialpose、不启动 Nav2、不验证目标位于地图自由空间，也不重发目标。
所有等待都由 monotonic 经过时间限制；这是普通操作系统上的软期限，并非硬实时保证。
"""

import argparse
import json
import math
import signal
import sys
import time
import uuid


def positive_seconds(text):
    """解析秒：拒绝 NaN、无穷、零、负数与超过一天的教学配置。"""
    value = float(text)
    if not math.isfinite(value) or not 0.0 < value <= 86400.0:
        raise argparse.ArgumentTypeError('期限须是 (0, 86400] 内的有限秒数')
    return value


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--goal', nargs=3, type=float, required=True,
                        metavar=('X_M', 'Y_M', 'YAW_RAD'))
    parser.add_argument('--frame', default='map', help='目标参考系，默认 map')
    parser.add_argument('--action-name', default='/navigate_to_pose',
                        help='绝对 Action 名；命名空间示例 /robot1/navigate_to_pose')
    parser.add_argument('--sim-time', action='store_true', help='使用 /clock ROS 仿真时间戳')
    parser.add_argument('--clock-timeout', type=positive_seconds, default=5.0,
                        help='等待正的仿真时间上限，单调秒；默认 5')
    parser.add_argument('--server-timeout', type=positive_seconds, default=10.0,
                        help='发现 Action 服务端上限，单调秒；默认 10')
    parser.add_argument('--goal-response-timeout', type=positive_seconds, default=5.0,
                        help='提交后等待目标接受/拒绝应答上限，单调秒；默认 5')
    parser.add_argument('--timeout', type=positive_seconds, default=60.0,
                        help='观察到目标接受后导航期限，单调秒；默认 60')
    parser.add_argument('--cancel-timeout', type=positive_seconds, default=3.0,
                        help='取消服务发现及所有取消应答/重试的合计上限，单调秒；默认 3')
    parser.add_argument('--result-timeout', type=positive_seconds, default=5.0,
                        help='取消阶段后等待结果或终态状态的上限，单调秒；默认 5')
    args = parser.parse_args(argv)
    if not all(math.isfinite(v) for v in args.goal):
        parser.error('目标位置和朝向必须是有限数值，不能为 NaN 或无穷')
    # 这个宽松上限只拦截明显量纲/输入错误，不表示地图范围或导航安全边界。
    if any(abs(v) > 1.0e6 for v in args.goal):
        parser.error('教学输入要求 |X|、|Y|≤10^6 米，|YAW|≤10^6 弧度；请先核对单位')
    if not args.frame or args.frame.startswith('/') or any(c.isspace() for c in args.frame):
        parser.error('TF frame 必须非空、无空白且不以 / 开头，例如 map 或 robot1/map')
    if not args.action_name.startswith('/') or args.action_name.endswith('/'):
        parser.error('action-name 必须是无结尾 / 的绝对名称')
    return args


def main(argv=None):
    args = parse_args(argv)
    # 延迟导入让普通 Python 环境仍可查看 --help；实际通信需要 source Jazzy。
    import rclpy
    from action_msgs.msg import GoalStatus, GoalStatusArray
    from action_msgs.srv import CancelGoal
    from nav2_msgs.action import NavigateToPose
    from rclpy.action import ActionClient
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_action_status_default
    from rclpy.signals import SignalHandlerOptions
    from rclpy.validate_full_topic_name import validate_full_topic_name
    from unique_identifier_msgs.msg import UUID

    validate_full_topic_name(args.action_name)
    terminal_names = {
        GoalStatus.STATUS_SUCCEEDED: 'succeeded',
        GoalStatus.STATUS_CANCELED: 'canceled',
        GoalStatus.STATUS_ABORTED: 'aborted',
    }
    # 默认 rclpy SIGINT 会关闭上下文，来不及进行取消协议；改成只记录退出意图。
    # 首次 Ctrl+C 请求有界取消，第二次 Ctrl+C 立即退出等待并报告可能仍在执行。
    stop = {'requested': False, 'force': False}

    def request_stop(signum, _frame):
        if stop['requested']:
            stop['force'] = True
        stop['requested'] = True

    class BoundedNavigation(Node):
        def __init__(self, context):
            super().__init__('bounded_navigation', context=context,
                             parameter_overrides=[Parameter('use_sim_time', value=args.sim_time)])
            self.started = time.monotonic()
            self.goal_uuid = UUID(uuid=list(uuid.uuid4().bytes))  # 本次唯一且非零；发送前就保存。
            self.goal_hex = bytes(self.goal_uuid.uuid).hex()
            self.action = ActionClient(self, NavigateToPose, args.action_name)
            # 公共标准取消服务：无 goal handle 时也能按已保存 UUID 请求取消。
            # 非零 UUID + 零时间戳表示只取消该 UUID，绝不发送“取消所有目标”。
            self.cancel_client = self.create_client(CancelGoal, args.action_name + '/_action/cancel_goal')
            self.status_sub = self.create_subscription(
                GoalStatusArray, args.action_name + '/_action/status', self.on_status,
                qos_profile_action_status_default)
            self.send_future = None
            self.result_future = None
            self.goal_handle = None
            self.response = 'not_sent'
            self.goal_may_exist = False
            self.result_response = None
            self.observed_status = None
            self.cancel_state = 'not_requested'
            self.cancel_attempts = 0
            self.last_feedback = float('-inf')
            self.trigger = 'not_started'

        def emit(self, event, **fields):
            # 每条事件带 UUID 和单调经过秒；节点 ROS 时间只用于消息时间戳。
            print(json.dumps(dict(event=event, goal_uuid=self.goal_hex,
                                  elapsed_s=round(time.monotonic() - self.started, 3), **fields),
                             ensure_ascii=False, allow_nan=False), flush=True)

        def on_status(self, message):
            for item in message.status_list:
                # 只观察自己的目标，忽略历史任务与其他客户端的状态。
                if bytes(item.goal_info.goal_id.uuid) == bytes(self.goal_uuid.uuid):
                    if item.status in terminal_names:
                        self.observed_status = item.status

        def on_feedback(self, message):
            if bytes(message.goal_id.uuid) != bytes(self.goal_uuid.uuid):
                return
            now = time.monotonic()
            if now - self.last_feedback >= 1.0:
                self.last_feedback = now
                distance = float(message.feedback.distance_remaining)
                # 无效反馈只记为空，不能令 JSON NaN 或反馈异常中断取消监督。
                self.emit('feedback', distance_remaining_m=distance if math.isfinite(distance) else None)

        def observe_futures(self):
            # 不调用 Future.result() 等待：仅在 done 后读取，执行器推进发生在 poll 中。
            if self.send_future is not None and self.send_future.done():
                future, self.send_future = self.send_future, None
                try:
                    handle = future.result()
                    if handle is None:
                        raise RuntimeError('目标应答没有 goal handle')
                    self.goal_handle = handle
                    self.response = 'accepted' if handle.accepted else 'rejected'
                    self.emit('goal_response', state=self.response)
                    if handle.accepted:
                        self.result_future = handle.get_result_async()
                    else:
                        self.goal_may_exist = False
                except Exception as exc:
                    self.response = 'unknown'
                    self.emit('goal_response_error', detail=str(exc))
            if self.result_future is not None and self.result_future.done():
                future, self.result_future = self.result_future, None
                try:
                    response = future.result()
                    if response is None:
                        raise RuntimeError('结果应答为空')
                    self.result_response = response
                    self.emit('result_response', status=int(response.status),
                              error_code=int(response.result.error_code),
                              error_msg=response.result.error_msg)
                except Exception as exc:
                    self.emit('result_error', detail=str(exc))

        def terminal(self):
            # GetResult 提供终态和 Nav2 错误详情；status 只证明软件终态，不含完整结果。
            if self.result_response is not None and self.result_response.status in terminal_names:
                return self.result_response.status, 'get_result'
            if self.observed_status in terminal_names:
                return self.observed_status, 'status_topic'
            return None, 'unconfirmed'

        def poll(self, executor, predicate, deadline, stop_early=True):
            """逐次有限 spin；deadline 是绝对 monotonic 秒，不受 /clock 暂停影响。"""
            while True:
                self.observe_futures()
                if predicate():
                    return 'done'
                if stop['force'] or not self.context.ok():
                    return 'interrupted'
                if stop_early and stop['requested']:
                    return 'interrupted'
                remaining_s = deadline - time.monotonic()
                if remaining_s <= 0.0:
                    return 'timeout'
                # 本节点没有长耗时回调。spin_once 的参数限制空闲等待，不抢占回调。
                executor.spin_once(timeout_sec=min(0.05, remaining_s))

        def cancel_and_wait(self, executor):
            self.cancel_state = 'unconfirmed'
            cancel_deadline = time.monotonic() + args.cancel_timeout
            cancel_future = None
            retry_at = time.monotonic()
            self.emit('cancel_phase', timeout_s=args.cancel_timeout)
            while self.context.ok() and not stop['force'] and time.monotonic() < cancel_deadline:
                self.observe_futures()  # 仍接收迟到的接受应答，并取得正常结果 future。
                if self.response == 'rejected' or self.terminal()[0] is not None:
                    if self.cancel_attempts == 0:
                        self.cancel_state = 'not_needed_rejected_or_terminal'
                    break
                now = time.monotonic()
                if cancel_future is None and now >= retry_at and self.cancel_client.service_is_ready():
                    request = CancelGoal.Request()
                    request.goal_info.goal_id = self.goal_uuid
                    # stamp 默认 sec=0/nanosec=0；不要填当前时间扩大到其他旧任务。
                    cancel_future = self.cancel_client.call_async(request)
                    self.cancel_attempts += 1
                    self.emit('cancel_sent', attempt=self.cancel_attempts)
                if cancel_future is not None and cancel_future.done():
                    try:
                        response = cancel_future.result()
                        if response is None:
                            raise RuntimeError('取消应答为空')
                        own = any(bytes(g.goal_id.uuid) == bytes(self.goal_uuid.uuid)
                                  for g in response.goals_canceling)
                        self.emit('cancel_response', return_code=int(response.return_code),
                                  own_goal_canceling=own)
                        if response.return_code == CancelGoal.Response.ERROR_NONE and own:
                            self.cancel_state = 'accepted_not_terminal'
                            break
                        if response.return_code == CancelGoal.Response.ERROR_UNKNOWN_GOAL_ID:
                            # 接受应答丢失时，目标可能尚未注册；只在同一个取消总期限内重试。
                            self.cancel_state = 'unknown_goal_id'
                            cancel_future = None
                            retry_at = now + 0.1
                        else:
                            self.cancel_state = ('already_terminal_unconfirmed'
                                                 if response.return_code == CancelGoal.Response.ERROR_GOAL_TERMINATED
                                                 else 'rejected_or_invalid')
                            break
                    except Exception as exc:
                        self.cancel_state = 'response_error'
                        self.emit('cancel_error', detail=str(exc))
                        break
                executor.spin_once(timeout_sec=min(0.05, max(0.0, cancel_deadline - time.monotonic())))
            # 清理本地 service pending 登记，不等于撤销服务端工作或停止机器人。
            if cancel_future is not None and not cancel_future.done():
                self.cancel_client.remove_pending_request(cancel_future)
                self.cancel_state = 'response_timeout'
            elif self.cancel_state == 'unconfirmed':
                self.cancel_state = 'service_unavailable_or_interrupted'
            self.emit('terminal_wait', timeout_s=args.result_timeout,
                      cancel_state=self.cancel_state)
            self.poll(executor,
                      lambda: self.terminal()[0] is not None or self.response == 'rejected',
                      time.monotonic() + args.result_timeout, stop_early=False)

        def execute(self, executor):
            self.emit('preflight', frame=args.frame, goal_m_m_rad=args.goal,
                      use_sim_time=args.sim_time,
                      initial_pose='用户应在运行前设置；本客户端不发布 initialpose')
            if args.sim_time:
                self.trigger = 'clock_wait'
                reason = self.poll(executor, lambda: self.get_clock().now().nanoseconds > 0,
                                   time.monotonic() + args.clock_timeout)
                if reason != 'done':
                    self.trigger = 'clock_' + reason
                    return self.finish()
            self.trigger = 'server_wait'
            reason = self.poll(executor, self.action.server_is_ready,
                               time.monotonic() + args.server_timeout)
            if reason != 'done':
                self.trigger = 'server_' + reason
                return self.finish()
            if stop['requested']:
                self.trigger = 'interrupted_before_send'
                return self.finish()
            goal = NavigateToPose.Goal()
            goal.pose.header.frame_id = args.frame
            goal.pose.header.stamp = self.get_clock().now().to_msg()
            goal.pose.pose.position.x, goal.pose.pose.position.y = args.goal[:2]
            yaw_rad = math.remainder(args.goal[2], 2.0 * math.pi)
            goal.pose.pose.orientation.z = math.sin(yaw_rad / 2.0)
            goal.pose.pose.orientation.w = math.cos(yaw_rad / 2.0)
            # x/y 姿态分量默认零，sin²+cos²=1；不把 yaw 直接写进 quaternion.z。
            goal.behavior_tree = ''  # 采用当前服务端配置的默认 BT，不跨版本指定 XML。
            self.response = 'unknown'
            self.goal_may_exist = True  # 即便发送过程异常，也不能假定远端没收到。
            self.send_future = self.action.send_goal_async(
                goal, feedback_callback=self.on_feedback, goal_uuid=self.goal_uuid)
            self.emit('goal_sent')
            self.trigger = 'goal_response_wait'
            reason = self.poll(executor, lambda: self.response in ('accepted', 'rejected'),
                               time.monotonic() + args.goal_response_timeout)
            if self.response == 'rejected':
                self.trigger = 'goal_rejected'
                return self.finish()
            if reason != 'done':
                self.trigger = 'goal_response_' + reason
                self.emit('acceptance_unknown', reason=self.trigger,
                          detail='服务端可能已接受；按已知 UUID 有界请求取消，禁止自动重发目标')
            else:
                self.trigger = 'navigation_wait'
                reason = self.poll(executor, lambda: self.terminal()[0] is not None,
                                   time.monotonic() + args.timeout)
                if reason == 'done':
                    self.trigger = 'navigation_terminal'
                    return self.finish()
                self.trigger = 'navigation_' + reason
            self.cancel_and_wait(executor)
            return self.finish()

        def finish(self):
            self.observe_futures()
            status, source = self.terminal()
            name = terminal_names.get(status, 'unknown')
            self.emit('summary', trigger=self.trigger, goal_response=self.response,
                      terminal=name, terminal_source=source, cancel_state=self.cancel_state,
                      cancel_attempts=self.cancel_attempts,
                      nav2_result_available=self.result_response is not None,
                      hardware_stop_verified=False)
            # 非零表示上层不能按“导航成功”继续业务；unknown 特别禁止直接重发。
            if self.response == 'rejected':
                return 2
            if name == 'succeeded' and self.trigger != 'navigation_terminal':
                # 取消/超时与成功可能竞争；记录真实终态，但不冒充期限内业务成功。
                return 6
            return {'succeeded': 0, 'aborted': 3, 'canceled': 4}.get(name, 5)

    context = Context()
    node = executor = None
    previous_handlers = {}
    try:
        rclpy.init(args=[], context=context, signal_handler_options=SignalHandlerOptions.NO)
        node = BoundedNavigation(context)
        executor = SingleThreadedExecutor(context=context)
        executor.add_node(node)
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.signal(signum, request_stop)
        try:
            return node.execute(executor)
        except Exception as exc:
            node.trigger = 'client_exception'
            node.emit('client_error', detail=str(exc))
            if node.goal_may_exist and node.terminal()[0] is None:
                try:
                    node.cancel_and_wait(executor)
                except Exception as cancel_exc:
                    node.emit('cancel_path_error', detail=str(cancel_exc))
            return node.finish()
    finally:
        # 本例单线程、回调短，不启动后台任务。取消不靠销毁对象完成。
        if executor is not None:
            if node is not None:
                executor.remove_node(node)
            executor.shutdown(timeout_sec=0.0)
        if node is not None:
            node.action.destroy()
            node.destroy_node()
        if context.ok():
            rclpy.shutdown(context=context)
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


if __name__ == '__main__':
    sys.exit(main())
