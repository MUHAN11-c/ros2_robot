# SPDX-License-Identifier: Apache-2.0
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


def main(args=None):
    rclpy.init(args=args)
    node = Node('atlas_add_client_py')
    client = node.create_client(AddTwoInts, 'add_two_ints')
    status = 1
    try:
        if not client.wait_for_service(timeout_sec=5.0):
            node.get_logger().error('Service unavailable after 5 seconds')
        else:
            request = AddTwoInts.Request()
            request.a, request.b = 7, 5
            future = client.call_async(request)
            rclpy.spin_until_future_complete(node, future, timeout_sec=5.0)
            if future.done() and future.exception() is None:
                node.get_logger().info(f'SUM={future.result().sum}')
                status = 0
            else:
                future.cancel()
                node.get_logger().error('Request timed out or failed')
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return status


if __name__ == '__main__':
    raise SystemExit(main())
