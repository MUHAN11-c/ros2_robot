import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class SumServer(Node):
    def __init__(self):
        super().__init__('learning_sum_py')
        self.service = self.create_service(AddTwoInts, 'sum', self.on_request)

    def on_request(self, request, response):
        response.sum = request.a + request.b
        self.get_logger().info('request handled')
        return response


def main():
    rclpy.init()
    node = SumServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
