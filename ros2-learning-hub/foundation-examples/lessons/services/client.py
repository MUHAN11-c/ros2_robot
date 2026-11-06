import sys
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


def main():
    rclpy.init()
    node = Node('learning_sum_client_py')
    client = node.create_client(AddTwoInts, 'sum')
    exit_code = 1
    try:
        if not client.wait_for_service(timeout_sec=2.0):
            node.get_logger().error('sum service was not discovered')
        else:
            request = AddTwoInts.Request()
            request.a, request.b = 4, 8
            future = client.call_async(request)
            rclpy.spin_until_future_complete(node, future, timeout_sec=2.0)
            if future.done():
                response = future.result()
                node.get_logger().info(f'sum={response.sum}')
                exit_code = 0
            else:
                node.get_logger().error('sum response timed out')
    except Exception as error:
        node.get_logger().error(f'request failed: {error}')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
