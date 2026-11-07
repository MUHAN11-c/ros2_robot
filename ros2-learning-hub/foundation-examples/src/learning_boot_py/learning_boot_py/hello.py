# 【中文教学注释】 foundation-examples/src/learning_boot_py/learning_boot_py/hello.py
# 输入输出：输入是 src 中的包清单、源码和构建配置；输出先是 install 产物，随后才是节点进程的日志。
# 执行顺序与边界：先加载 Jazzy underlay，再构建并 source overlay；包名、安装目标与 console_scripts 必须一致，单个源码文件不能替代整个包。
import rclpy
from rclpy.node import Node


# 程序入口按本章顺序组织资源；本例仅在 __main__ 下运行，import 时不应启动节点或连接硬件。
def main(args=None):
    # 初始化当前进程的 ROS 上下文并解析传入 ROS 参数；在创建节点/端点之前调用。
    rclpy.init(args=args)
    # 创建并持有节点对象；本进程退出前应显式 destroy_node，创建节点本身不会自动处理回调。
    node = Node('learning_hello_py')
    # 输出可观测日志用于核对状态；日志成功写出不等于对端收到消息或任务执行成功。
    node.get_logger().info('Python node is ready')
    try:
        # 进入执行器事件循环，定时器、订阅、服务和 Future 回调在这里才被推进；通常阻塞到中断或上下文关闭。
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 显式释放节点所属端点与定时器；应在相关执行器不再访问节点后执行。
        node.destroy_node()
        # 检查 ROS 上下文仍有效，避免退出流程重复 shutdown；它不表示节点业务健康。
        if rclpy.ok():
            # 关闭本进程 ROS 上下文；先停止执行器、销毁端点/节点，再在上下文仍有效时调用。
            rclpy.shutdown()


if __name__ == '__main__':
    main()
