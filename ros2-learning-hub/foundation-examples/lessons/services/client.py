# 【中文教学注释】 foundation-examples/lessons/services/client.py
# 输入输出：输入为 AddTwoInts 请求中的两个小整数；输出为 sum 响应和成功/失败退出码，无物理单位。
# 执行顺序与边界：先发现服务再发请求；Future 返回不等于响应已完成，等待超时不会撤销服务端已经发生的业务副作用。
import sys
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


# 程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。
def main():
    # 初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。
    rclpy.init()
    # 创建并持有节点对象；本进程退出前应显式 destroy_node，创建节点本身不会自动处理回调。
    node = Node('learning_sum_client_py')
    # 创建服务客户端，接口类型和服务名须与服务端一致；此调用不保证服务已经发现。
    client = node.create_client(AddTwoInts, 'sum')
    exit_code = 1
    try:
        # 只等待服务发现，timeout_sec 单位为秒；返回 False 应走失败分支，发现成功不保证随后请求一定成功。
        if not client.wait_for_service(timeout_sec=2.0):
            # 输出可观测日志用于核对状态；日志成功写出不等于对端收到消息或任务执行成功。
            node.get_logger().error('sum service was not discovered')
        else:
            request = AddTwoInts.Request()
            request.a, request.b = 4, 8
            # 提交请求并立即返回 Future；仍需执行器处理响应，保存 Future 才能关联完成、异常与超时。
            future = client.call_async(request)
            # 在一次性 main 流程中分发回调直到 Future 完成或 timeout_sec 秒到期；不能原样嵌套到已 spin 的同一节点回调中。
            rclpy.spin_until_future_complete(node, future, timeout_sec=2.0)
            # 先检查 Future 是否已经结束；完成仍可能包含异常，需要与 result()/exception() 的错误处理配合。
            if future.done():
                # 提取已经完成的异步结果；可能抛出传输/服务异常，不能把未完成 Future 的结果当作有效 Response。
                response = future.result()
                node.get_logger().info(f'sum={response.sum}')
                exit_code = 0
            else:
                node.get_logger().error('sum response timed out')
    except Exception as error:
        node.get_logger().error(f'request failed: {error}')
    finally:
        # 显式释放节点所属端点与定时器；应在相关执行器不再访问节点后执行。
        node.destroy_node()
        # 检查 ROS 上下文仍有效，避免退出流程重复 shutdown；它不表示节点业务健康。
        if rclpy.ok():
            # 关闭本进程 ROS 上下文；先停止执行器、销毁端点/节点，再在上下文仍有效时调用。
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
