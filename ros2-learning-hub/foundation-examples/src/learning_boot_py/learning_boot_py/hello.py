import rclpy
from rclpy.node import Node


def main(args=None):
    rclpy.init(args=args)
    node = Node('learning_hello_py')
    node.get_logger().info('Python node is ready')
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
