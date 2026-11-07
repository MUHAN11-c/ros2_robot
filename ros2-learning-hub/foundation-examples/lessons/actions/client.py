# 【中文教学注释】 foundation-examples/lessons/actions/client.py
# 输入输出：输入为 Count 目标 target 或取消请求；输出为 current 反馈、completed 结果及终态，计数无量纲。
# 执行顺序与边界：服务端接受 1..20 且同一时刻只运行一个目标；每步约 0.5 秒。取消请求被接受与任务已取消是两个事件，共享 busy 状态按线程模型保护。
import argparse
import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from learning_count_interfaces.action import Count


# 程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cancel', action='store_true')
    options, ros_args = parser.parse_known_args()
    # 初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。
    rclpy.init(args=ros_args)
    # 创建并持有节点对象；本进程退出前应显式 destroy_node，创建节点本身不会自动处理回调。
    node = Node('learning_count_client')
    # 建立 Count 动作客户端，名称和 Action 类型须匹配服务端；对象保留至取消/结果处理结束。
    client = ActionClient(node, Count, 'count')
    cancel_timer = None
    try:
        # 等待动作服务端发现，timeout_sec 以秒计；True 只说明发现条件满足，不代表目标已被接受。
        if not client.wait_for_server(timeout_sec=2.0):
            # 输出可观测日志用于核对状态；日志成功写出不等于对端收到消息或任务执行成功。
            node.get_logger().error('count action server was not discovered')
            return 1
        goal = Count.Goal()
        goal.target = 10 if options.cancel else 5

        def on_feedback(message):
            node.get_logger().info(f'current={message.feedback.current}')

        # 异步发送目标并接入反馈回调；此 Future 返回目标接纳句柄，最终任务结果要另用 get_result_async。
        accepted_future = client.send_goal_async(goal, feedback_callback=on_feedback)
        # 在一次性 main 流程中分发回调直到 Future 完成或 timeout_sec 秒到期；不能原样嵌套到已 spin 的同一节点回调中。
        rclpy.spin_until_future_complete(node, accepted_future, timeout_sec=2.0)
        # 先检查 Future 是否已经结束；完成仍可能包含异常，需要与 result()/exception() 的错误处理配合。
        if not accepted_future.done():
            node.get_logger().error('goal response timed out')
            return 1
        # 提取已经完成的异步结果；可能抛出传输/服务异常，不能把未完成 Future 的结果当作有效 Response。
        handle = accepted_future.result()
        if not handle.accepted:
            node.get_logger().error('goal rejected')
            return 1
        # 在目标已接受后申请结果 Future；结果包装中同时包含终态 status 和业务 result。
        result_future = handle.get_result_async()

        def on_cancel_response(future):
            response = future.result()
            node.get_logger().info(f'cancel accepted={bool(response.goals_canceling)}')

        def request_cancel():
            # 取消当前定时器/Future的本地后续触发；取消本地对象不必然撤销已经发给远端的业务。
            cancel_timer.cancel()
            # 异步请求取消；取消响应只说明是否进入取消流程，仍要等待最终 CANCELED/其他终态。
            future = handle.cancel_goal_async()
            # 注册 Future 完成回调；这不保证开启新线程，完成回调应检查异常且尽快返回。
            future.add_done_callback(on_cancel_response)

        if options.cancel:
            # 定时周期单位为秒，回调由执行器调度而非自动新建独占线程；使用节点时钟，仿真时间暂停可能影响触发。
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
        # 显式释放节点所属端点与定时器；应在相关执行器不再访问节点后执行。
        node.destroy_node()
        # 检查 ROS 上下文仍有效，避免退出流程重复 shutdown；它不表示节点业务健康。
        if rclpy.ok():
            # 关闭本进程 ROS 上下文；先停止执行器、销毁端点/节点，再在上下文仍有效时调用。
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
