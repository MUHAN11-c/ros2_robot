import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from learning_count_interfaces.action import Count


class CountServer(Node):
    def __init__(self):
        super().__init__('learning_count_py')
        self.lock = threading.Lock()
        self.busy = False
        self.group = ReentrantCallbackGroup()
        self.server = ActionServer(
            self, Count, 'count', self.execute,
            goal_callback=self.on_goal,
            cancel_callback=self.on_cancel,
            callback_group=self.group)

    def on_goal(self, goal):
        with self.lock:
            if self.busy or not 1 <= goal.target <= 20:
                return GoalResponse.REJECT
            self.busy = True
        return GoalResponse.ACCEPT

    def on_cancel(self, goal_handle):
        return CancelResponse.ACCEPT

    def execute(self, goal_handle):
        result = Count.Result()
        try:
            for current in range(1, goal_handle.request.target + 1):
                if not rclpy.ok():
                    return result
                time.sleep(0.5)
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    return result
                result.completed = current
                feedback = Count.Feedback()
                feedback.current = current
                goal_handle.publish_feedback(feedback)
            goal_handle.succeed()
            return result
        finally:
            with self.lock:
                self.busy = False


def main():
    rclpy.init()
    node = CountServer()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
