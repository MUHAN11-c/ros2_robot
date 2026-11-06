import argparse
import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from learning_count_interfaces.action import Count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cancel', action='store_true')
    options, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    node = Node('learning_count_client')
    client = ActionClient(node, Count, 'count')
    cancel_timer = None
    try:
        if not client.wait_for_server(timeout_sec=2.0):
            node.get_logger().error('count action server was not discovered')
            return 1
        goal = Count.Goal()
        goal.target = 10 if options.cancel else 5

        def on_feedback(message):
            node.get_logger().info(f'current={message.feedback.current}')

        accepted_future = client.send_goal_async(goal, feedback_callback=on_feedback)
        rclpy.spin_until_future_complete(node, accepted_future, timeout_sec=2.0)
        if not accepted_future.done():
            node.get_logger().error('goal response timed out')
            return 1
        handle = accepted_future.result()
        if not handle.accepted:
            node.get_logger().error('goal rejected')
            return 1
        result_future = handle.get_result_async()

        def on_cancel_response(future):
            response = future.result()
            node.get_logger().info(f'cancel accepted={bool(response.goals_canceling)}')

        def request_cancel():
            cancel_timer.cancel()
            future = handle.cancel_goal_async()
            future.add_done_callback(on_cancel_response)

        if options.cancel:
            cancel_timer = node.create_timer(2.0, request_cancel)
        rclpy.spin_until_future_complete(node, result_future, timeout_sec=15.0)
        if not result_future.done():
            node.get_logger().error('result timed out')
            return 1
        wrapped = result_future.result()
        labels = {
            GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
            GoalStatus.STATUS_CANCELED: 'CANCELED',
            GoalStatus.STATUS_ABORTED: 'ABORTED',
        }
        status = labels.get(wrapped.status, str(wrapped.status))
        node.get_logger().info(f'status={status}, completed={wrapped.result.completed}')
        expected = GoalStatus.STATUS_CANCELED if options.cancel else GoalStatus.STATUS_SUCCEEDED
        return 0 if wrapped.status == expected else 1
    except Exception as error:
        node.get_logger().error(f'action failed: {error}')
        return 1
    finally:
        if cancel_timer is not None:
            cancel_timer.cancel()
        client.destroy()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
