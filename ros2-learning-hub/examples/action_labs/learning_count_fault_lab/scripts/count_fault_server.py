#!/usr/bin/env python3
"""Jazzy Count纯计数故障服务端，默认不故障，不连接硬件。

输入：Count.target无量纲整数1..20；启动参数abort_after为0..20步，0关闭故障；
step_seconds为[0.02,2]内有限秒数，默认0.15秒。N步反馈后触发ABORTED(completed=N)，
故障优先于恰好同一步的成功；target<N仍成功。Result依然只有completed，原因写独立UUID日志。
例如：count_fault_py --ros-args -p abort_after:=6 -p step_seconds:=0.15。
--help仅导入标准库；ROS参数与namespace remap原样交给rclpy。
"""
import argparse
import json
import math
import threading
import time


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    _args, ros_args = parser.parse_known_args(argv)  # --help在ROS导入之前退出。
    import rclpy
    from learning_count_interfaces.action import Count
    from rclpy.action import ActionServer, CancelResponse, GoalResponse
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
    from rclpy.node import Node

    class CountFaultServer(Node):
        def __init__(self):
            super().__init__('count_fault_py', start_parameter_services=False)
            self.abort_after = self.declare_parameter('abort_after', 0).value
            self.step_seconds = self.declare_parameter('step_seconds', 0.15).value
            if type(self.abort_after) is not int or not 0 <= self.abort_after <= 20:
                raise ValueError('abort_after必须是0..20的整数步数，0关闭故障')
            if (type(self.step_seconds) is not float or not math.isfinite(self.step_seconds)
                    or not 0.02 <= self.step_seconds <= 2.0):
                raise ValueError('step_seconds必须是[0.02,2]内有限DOUBLE秒数')
            self.lock = threading.Lock()
            self.log_lock = threading.Lock()
            self.busy = False
            self.group = ReentrantCallbackGroup()
            self.server = ActionServer(self, Count, 'count', self.execute,
                                       goal_callback=self.on_goal, cancel_callback=self.on_cancel,
                                       handle_accepted_callback=self.on_accepted,
                                       callback_group=self.group)
            self.emit('ready', None, 0, 0, 'configuration_loaded')

        def emit(self, event, goal_uuid, target, completed, reason):
            # 两个工作线程共用stdout；独立日志锁防止两条JSON交错，不与busy锁构成反向持锁。
            with self.log_lock:
                print('COUNT_LAB_EVENT ' + json.dumps(dict(
                    event=event, goal_uuid=goal_uuid, target=int(target),
                    completed=None if completed is None else int(completed),
                    reason=reason, abort_after=self.abort_after, step_seconds=self.step_seconds),
                    ensure_ascii=False, allow_nan=False), flush=True)

        @staticmethod
        def uuid(handle):
            return bytes(handle.goal_id.uuid).hex()

        def on_goal(self, goal):
            with self.lock:
                if not 1 <= goal.target <= 20:
                    # Python公开goal_callback只收到Goal，不提供请求UUID；不能编造UUID。
                    self.emit('goal_rejected', None, goal.target, 0, 'invalid_target_range')
                    return GoalResponse.REJECT
                if self.busy:
                    self.emit('goal_rejected', None, goal.target, 0, 'busy')
                    return GoalResponse.REJECT
                self.busy = True
            return GoalResponse.ACCEPT

        def on_accepted(self, handle):
            # 接受后公开handle才提供UUID；把执行交回ActionServer的执行任务。
            self.emit('goal_accepted', self.uuid(handle), handle.request.target, 0, 'accepted')
            handle.execute()

        def on_cancel(self, handle):
            # 该接纳回调不持有执行回调的可靠进度快照，不能以0冒充当前completed。
            # null表示此日志事件未提供进度；真正completed来自反馈及最终Result。
            self.emit('cancel_accepted', self.uuid(handle), handle.request.target, None,
                      'cancel_request_accepted_not_terminal')
            return CancelResponse.ACCEPT

        def execute(self, handle):
            result = Count.Result()
            goal_uuid, target = self.uuid(handle), handle.request.target
            try:
                for current in range(1, target + 1):
                    # 仅模拟软件耗时，秒为单调经过时间；不是设备控制周期或硬实时承诺。
                    time.sleep(self.step_seconds)
                    if not self.context.ok():
                        self.emit('shutdown_without_protocol_guarantee', goal_uuid, target,
                                  result.completed, 'context_shutdown')
                        return result
                    if handle.is_cancel_requested:
                        handle.canceled()
                        self.emit('CANCELED', goal_uuid, target, result.completed,
                                  'cancel_observed_at_step_boundary')
                        return result
                    result.completed = current
                    feedback = Count.Feedback()
                    feedback.current = current
                    handle.publish_feedback(feedback)
                    self.emit('feedback', goal_uuid, target, current, 'step_completed')
                    if self.abort_after > 0 and current >= self.abort_after:
                        # 常规Python执行模式：设置通用终态，再返回原Count.Result，不重复填新结果字段。
                        handle.abort()
                        self.emit('ABORTED', goal_uuid, target, result.completed,
                                  'configured_abort_after_step')
                        return result
                handle.succeed()
                self.emit('SUCCEEDED', goal_uuid, target, result.completed, 'target_reached')
                return result
            finally:
                # 所有返回路径都释放占用。锁只保护短更新，不跨sleep或网络等待。
                with self.lock:
                    self.busy = False
                self.emit('busy_released', goal_uuid, target, result.completed,
                          'slot_released_after_execution_exit')

    rclpy.init(args=ros_args)
    node = executor = None
    try:
        node = CountFaultServer()
        executor = MultiThreadedExecutor(num_threads=2)
        executor.add_node(node)
        try:
            executor.spin()
        except (KeyboardInterrupt, ExternalShutdownException):
            pass
    finally:
        if executor is not None:
            executor.shutdown(timeout_sec=3.0)
        if node is not None:
            node.server.destroy()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
