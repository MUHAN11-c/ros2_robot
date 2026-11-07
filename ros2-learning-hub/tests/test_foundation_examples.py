#!/usr/bin/env python3
"""基础十包的真实 Jazzy 集成测试；不连接设备，不借助 ROS CLI daemon。

执行准备（位于 ros2-learning-hub；安装前缀可以位于任意新电脑路径）：
    source /opt/ros/jazzy/setup.bash
    export FOUNDATION_INSTALL_PREFIX="$PWD/foundation-examples/install"
    source "$FOUNDATION_INSTALL_PREFIX/setup.bash"
    timeout --signal=INT --kill-after=10s 300s /usr/bin/python3 tests/test_foundation_examples.py

输入：已构建并 source 的基础十包，以及受控的小整数、计数目标、gain 参数。
输出：unittest 结果和 validation-evidence/foundation-current-validation.json。
单位：所有等待期限和耗时均为单调时钟秒；计数、gain、示例和均无量纲。
边界：每个测试在独立 worker 进程组中运行；每个 worker 有父进程总期限，
      每次服务/Action/日志等待也有本地期限。清理只针对本测试创建的 PID/进程组。
      默认 ROS 域 211、LOCALHOST、每例唯一命名空间，不停止 daemon 或其他节点。
      launch 仅解析三种前端，不声称已经执行三种 launch 的节点启动过程。
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "foundation-examples"
# 默认值跟随本工作区；当前机器的临时构建路径只通过环境变量传入。
PREFIX = Path(os.environ.get("FOUNDATION_INSTALL_PREFIX", SOURCE / "install")).resolve()
SYSTEM_PYTHON = "/usr/bin/python3"
RESULT_MARKER = "FOUNDATION_WORKER_RESULT="
RECORDS: list[dict] = []
PACKAGES = (
    "learning_boot_cpp", "learning_boot_py", "learning_topic_cpp", "learning_topic_py",
    "learning_interfaces", "learning_count_interfaces", "learning_service_cpp",
    "learning_action_cpp", "learning_params_cpp", "learning_bringup",
)
EXECUTABLES = {
    "learning_boot_cpp": ("hello",), "learning_boot_py": ("hello",),
    "learning_topic_cpp": ("talker", "listener"),
    "learning_topic_py": ("talker", "listener"),
    "learning_service_cpp": ("server", "client"),
    "learning_action_cpp": ("server",), "learning_params_cpp": ("config_node",),
}


def require(condition, description):
    """断言失败保留明确原因；不采用重试降级、静默跳过或只检查日志存在。"""
    if not condition:
        raise AssertionError(description)


def isolated_environment():
    """只改变子进程环境；域可配置，但本地发现范围和测试 RMW 明确固定。"""
    env = dict(os.environ)
    domain = int(env.get("FOUNDATION_TEST_DOMAIN_ID", "211"))
    require(0 <= domain <= 232, "测试 ROS_DOMAIN_ID 必须位于 0..232")
    env.update(
        ROS_DOMAIN_ID=str(domain),
        ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
        ROS_LOCALHOST_ONLY="1",
        RMW_IMPLEMENTATION=env.get("FOUNDATION_TEST_RMW_IMPLEMENTATION", "rmw_fastrtps_cpp"),
        PYTHONUNBUFFERED="1",
        PYTHONDONTWRITEBYTECODE="1",
        RCUTILS_LOGGING_BUFFERED_STREAM="0",
    )
    # 不继承用户对特定远端 ROS peer 的额外发现配置。
    env.pop("ROS_STATIC_PEERS", None)
    return env


def binary(package, executable):
    """取得当前安装产物；文件与执行权限都必须真实存在。"""
    path = PREFIX / "lib" / package / executable
    require(path.is_file() and os.access(path, os.X_OK), f"缺少可执行安装入口：{path}")
    return [str(path)]


def lesson(relative):
    """独立 Python 示例使用系统解释器，避免虚拟环境遮蔽 apt 安装的 ROS 扩展。"""
    path = SOURCE / "lessons" / relative
    require(path.is_file(), f"缺少保留示例：{path}")
    return [SYSTEM_PYTHON, str(path)]


def ros_arguments(namespace):
    """将示例的所有相对名称限制在本例命名空间；不更改任何源码。"""
    return ["--ros-args", "-r", f"__ns:={namespace}"]


class Children:
    """管理 worker 创建的进程与独立日志；所有孩子继承 worker 的进程组。

    worker 父进程可以在总期限到达时杀死整个组，避免额外会话导致孤儿进程。
    正常结束按 SIGINT→SIGTERM→SIGKILL 清理，等待上限依次为 2、2、2 秒。
    """

    def __init__(self, directory, env):
        self.directory = Path(directory)
        self.env = env
        self.items = []

    def start(self, command, label):
        path = self.directory / f"{len(self.items):02d}-{label}.log"
        stream = path.open("w")
        process = subprocess.Popen(command, stdout=stream, stderr=stream, env=self.env)
        item = {"label": label, "command": command, "process": process, "stream": stream,
                "path": path}
        self.items.append(item)
        return item

    @staticmethod
    def text(item):
        item["stream"].flush()
        # 使用独立读描述符，避免seek改变与子进程共享的写入文件偏移。
        return item["path"].read_text(errors="replace")

    def wait_log(self, item, predicate, timeout_s=12.0):
        """只观察指定接收进程的日志，避免把发布日志误当成接收成功。"""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            text = self.text(item)
            if predicate(text):
                return text
            require(item["process"].poll() is None, f"{item['label']} 提前退出：\n{text}")
            time.sleep(0.05)
        raise AssertionError(f"{item['label']} 等待 {timeout_s}s 超时：\n{self.text(item)}")

    def finished(self, item, timeout_s=22.0):
        """单次客户端须在外层期限内退出，超时不会解释为业务成功。"""
        item["process"].wait(timeout=timeout_s)
        return item["process"].returncode, self.text(item)

    @staticmethod
    def stop(item):
        process = item["process"]
        if process.poll() is None:
            for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
                if process.poll() is not None:
                    break
                process.send_signal(sig)
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    continue
        require(process.poll() is not None, f"无法清理本测试进程 PID={process.pid}")

    def close(self):
        """逆序清理孩子并保存完整小日志，文件关闭后临时目录才能删除。"""
        records = []
        for item in reversed(self.items):
            error = None
            try:
                self.stop(item)
            except Exception as exc:
                error = repr(exc)
            records.append({
                "label": item["label"], "command": item["command"],
                "pid": item["process"].pid, "exitCode": item["process"].poll(),
                "cleanupError": error, "log": self.text(item),
            })
            item["stream"].close()
        return list(reversed(records))


@contextlib.contextmanager
def probe(namespace, name="foundation_probe"):
    """每例使用自己的 rclpy Context；上下文有效时才销毁节点和结束通信。"""
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    context = Context()
    rclpy.init(args=[], context=context)
    node = Node(name, namespace=namespace, context=context, enable_rosout=False)
    # 自建Context必须配合同Context的执行器；rclpy.spin_once默认的全局执行器
    # 属于默认Context，不能在这里隐式混用，也不需要启动额外后台线程。
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(node)
    try:
        yield node
    finally:
        executor.remove_node(node)
        executor.shutdown(timeout_sec=1.0)
        node.destroy_node()
        if context.ok():
            rclpy.shutdown(context=context)


def await_future(node, future, timeout_s=5.0):
    """有界推进异步服务；先检查完成和异常，再读取响应。"""
    deadline = time.monotonic() + timeout_s
    while not future.done() and time.monotonic() < deadline:
        require(node.executor is not None, "probe节点缺少同Context执行器")
        node.executor.spin_once(timeout_sec=min(0.1, max(0.0, deadline-time.monotonic())))
    require(future.done(), f"异步响应超过 {timeout_s}s")
    require(future.exception() is None, f"异步响应异常：{future.exception()}")
    return future.result()


def await_condition(node, predicate, timeout_s=5.0):
    """传感器/话题结果等待采用单调时限，不依赖可暂停的 ROS 仿真时钟。"""
    deadline = time.monotonic() + timeout_s
    while not predicate() and time.monotonic() < deadline:
        require(node.executor is not None, "probe节点缺少同Context执行器")
        node.executor.spin_once(timeout_sec=min(0.1, max(0.0, deadline-time.monotonic())))
    require(predicate(), f"观测条件在 {timeout_s}s 内未满足")


def service_ready(node, service_type, name):
    client = node.create_client(service_type, name)
    require(client.wait_for_service(timeout_sec=8.0), f"未发现服务：{name}")
    return client


def inventory(children, namespace):
    """检查十包实际安装索引、全部十个可执行入口和两套生成接口。"""
    from ament_index_python.packages import get_package_prefix
    from rosidl_runtime_py.utilities import get_action, get_message, get_service
    packages = {}
    for package in PACKAGES:
        found = Path(get_package_prefix(package)).resolve()
        require(found == PREFIX, f"{package} 被其他 overlay 遮蔽：{found} != {PREFIX}")
        require((found / "share" / package / "package.xml").is_file(), f"缺少包清单：{package}")
        packages[package] = str(found)
    executables = [binary(package, executable)[0]
                   for package, names in EXECUTABLES.items() for executable in names]
    telemetry = get_message("learning_interfaces/msg/Telemetry")()
    require(set(telemetry.get_fields_and_field_types()) == {
        "header", "left_velocity_rad_s", "right_velocity_rad_s", "valid"}, "Telemetry 字段不符")
    scale = get_service("learning_interfaces/srv/Scale")
    require(set(scale.Request.get_fields_and_field_types()) == {"value", "gain"}, "Scale 请求不符")
    require(set(scale.Response.get_fields_and_field_types()) == {"scaled"}, "Scale 响应不符")
    for name in ("learning_interfaces", "learning_count_interfaces"):
        action = get_action(f"{name}/action/Count")
        require(set(action.Goal.get_fields_and_field_types()) == {"target"}, f"{name} Goal 不符")
        require(set(action.Result.get_fields_and_field_types()) == {"completed"}, f"{name} Result 不符")
        require(set(action.Feedback.get_fields_and_field_types()) == {"current"}, f"{name} Feedback 不符")
        # 显式加载C扩展typesupport；只导入Python类不足以证明本机构建的接口可用于通信。
        action.__class__.__import_type_support__()
        require(action.__class__._TYPE_SUPPORT is not None, f"{name} Action typesupport 未加载")
    boot_logs = {}
    for language, text in (("cpp", "C++ node is ready"), ("py", "Python node is ready")):
        item = children.start(binary(f"learning_boot_{language}", "hello") + ros_arguments(namespace), f"boot-{language}")
        children.wait_log(item, lambda log, expected=text: expected in log, timeout_s=8.0)
        boot_logs[language] = text
    return {"packages": packages, "executableCount": len(executables),
            "executables": executables, "generatedInterfaces": [
                "learning_interfaces/msg/Telemetry", "learning_interfaces/srv/Scale",
                "learning_interfaces/action/Count", "learning_count_interfaces/action/Count"],
            "bootLogs": boot_logs}


def topic_exchange(children, namespace, publisher, subscriber):
    """真实 listener 至少接收三条递增消息；独立日志排除发布端自报成功。"""
    receiver = children.start(binary(f"learning_topic_{subscriber}", "listener") + ros_arguments(namespace), "listener")
    children.start(binary(f"learning_topic_{publisher}", "talker") + ros_arguments(namespace), "talker")
    pattern = rf"received: {'cpp' if publisher == 'cpp' else 'py'} sample=(\d+)"
    log = children.wait_log(receiver, lambda text: len(re.findall(pattern, text)) >= 3)
    samples = [int(x) for x in re.findall(pattern, log)]
    require(all(b > a for a,b in zip(samples, samples[1:])), f"接收序号未递增：{samples}")
    return {"publisher": publisher, "subscriber": subscriber,
            "topic": namespace + "/telemetry", "receivedSequences": samples}


def service_exchange(children, namespace, server_language):
    """保留的客户端实际发送4+8；检查响应12与服务端处理日志。"""
    from example_interfaces.srv import AddTwoInts
    server_cmd = binary("learning_service_cpp", "server") if server_language == "cpp" else lesson("services/server.py")
    client_cmd = lesson("services/client.py") if server_language == "cpp" else binary("learning_service_cpp", "client")
    server = children.start(server_cmd + ros_arguments(namespace), "sum-server")
    with probe(namespace) as node:
        service_ready(node, AddTwoInts, "sum")
        client = children.start(client_cmd + ros_arguments(namespace), "sum-client")
        code, log = children.finished(client, timeout_s=10.0)
        require(code == 0 and "sum=12" in log, f"跨语言服务失败：code={code}\n{log}")
        children.wait_log(server, lambda text: "request handled" in text, timeout_s=2.0)
    return {"server": server_language, "client": "python" if server_language == "cpp" else "cpp",
            "request": {"a": 4, "b": 8}, "response": {"sum": 12}}


def action_exchange(children, namespace, server_language, cancel):
    """成功需最终SUCCEEDED且completed=5；取消需响应接纳和CANCELED两项证据。"""
    from learning_count_interfaces.action import Count
    from rclpy.action import ActionClient
    server_cmd = binary("learning_action_cpp", "server") if server_language == "cpp" else lesson("actions/server.py")
    children.start(server_cmd + ros_arguments(namespace), "count-server")
    with probe(namespace) as node:
        ready = ActionClient(node, Count, "count")
        try:
            require(ready.wait_for_server(timeout_sec=8.0), "Count动作服务端未就绪")
        finally:
            ready.destroy()
        command = lesson("actions/client.py") + (["--cancel"] if cancel else []) + ros_arguments(namespace)
        client = children.start(command, "count-client")
        code, log = children.finished(client, timeout_s=23.0)
        require(code == 0, f"Count客户端退出码={code}\n{log}")
        feedback = [int(x) for x in re.findall(r"current=(\d+)", log)]
        require(feedback and all(b > a for a,b in zip(feedback, feedback[1:])), f"反馈应存在并递增：{log}")
        status = "CANCELED" if cancel else "SUCCEEDED"
        match = re.search(rf"status={status}, completed=(\d+)", log)
        require(match is not None, f"缺少预期动作终态 {status}：{log}")
        completed = int(match.group(1))
        if cancel:
            require("cancel accepted=True" in log, f"未获得取消接纳响应：{log}")
            require(0 <= completed < 10, f"取消时不应完成全部10步：{completed}")
        else:
            require(completed == 5 and feedback[-1] == 5, f"成功时须完成5步：{log}")
    return {"server": server_language, "client": "preserved Python Count client",
            "target": 10 if cancel else 5, "status": status, "completed": completed,
            "feedback": feedback, "cancelResponseAccepted": bool(cancel)}


def parameter_command(language):
    return binary("learning_params_cpp", "config_node") if language == "cpp" else lesson("parameters/config_node.py")


def parameters_dynamic(children, namespace, language):
    """真实远端参数服务：接受有效double，拒绝越界/NaN/Inf/错误类型且保留原值。"""
    from rcl_interfaces.srv import GetParameters, SetParameters
    from rclpy.parameter import Parameter
    from std_msgs.msg import Float64
    children.start(parameter_command(language) + ros_arguments(namespace), "config-node")
    changes = []
    with probe(namespace) as node:
        setter = service_ready(node, SetParameters, "learning_config/set_parameters")
        getter = service_ready(node, GetParameters, "learning_config/get_parameters")
        observed = []
        subscription = node.create_subscription(Float64, "configured_value", lambda m: observed.append(m.data), 10)

        def stored_gain():
            response = await_future(node, getter.call_async(GetParameters.Request(names=["gain"])))
            require(len(response.values) == 1 and response.values[0].type == Parameter.Type.DOUBLE.value, "gain必须仍为double")
            return response.values[0].double_value

        require(stored_gain() == 1.0, "默认gain应为1.0")
        await_condition(node, lambda: any(math.isclose(v, 0.2, abs_tol=1e-12) for v in observed))
        cases = [("valid", 1.5, True), ("too-large", 3.0, False),
                 ("negative", -0.1, False), ("NaN", math.nan, False),
                 ("positive-Inf", math.inf, False), ("negative-Inf", -math.inf, False),
                 ("integer-type", 1, False), ("lower-bound", 0.0, True), ("upper-bound", 2.0, True)]
        expected = 1.0
        for label, value, accepted in cases:
            parameter = Parameter("gain", value=value)
            request = SetParameters.Request(parameters=[parameter.to_parameter_msg()])
            response = await_future(node, setter.call_async(request))
            require(len(response.results) == 1, "单参数请求须有一个结果")
            result = response.results[0]
            require(result.successful == accepted, f"{language} {label}接纳结果错误：{result}")
            if accepted:
                expected = value
            else:
                require(bool(result.reason), f"{label}拒绝须说明原因")
            actual = stored_gain()
            require(math.isfinite(actual) and actual == expected, f"{label}之后gain不应被错误写入：{actual}")
            changes.append({"input": label, "accepted": result.successful,
                            "reason": result.reason, "storedGain": actual})
            if accepted:
                observed.clear()
                await_condition(node, lambda target=0.2*expected: any(math.isclose(v,target,abs_tol=1e-12) for v in observed))
            require(all(math.isfinite(v) for v in observed), "configured_value不能含NaN/Inf")
        node.destroy_subscription(subscription)
    return {"language": language, "changes": changes, "finalGain": expected,
            "verifiedConfiguredOutputs": [0.2, 0.3, 0.0, 0.4]}


def parameters_startup(children, namespace, language):
    """覆盖启动配置；非法值须由gain校验器拒绝，不能仅以任意解析错误冒充验证。"""
    from rcl_interfaces.srv import GetParameters
    outcomes = []
    valid = children.start(parameter_command(language) + ros_arguments(namespace) + ["-p", "gain:=1.25"], "startup-valid")
    with probe(namespace) as node:
        getter = service_ready(node, GetParameters, "learning_config/get_parameters")
        response = await_future(node, getter.call_async(GetParameters.Request(names=["gain"])))
        require(response.values[0].double_value == 1.25, "有效启动gain未生效")
    children.stop(valid)
    outcomes.append({"input": "1.25", "accepted": True, "storedGain": 1.25})
    for index, value in enumerate(("3.0", ".nan")):
        # 每个失败进程另用命名空间，避免DDS中尚未过期的服务发现实体混淆后续例子。
        item = children.start(parameter_command(language) + ros_arguments(f"{namespace}/invalid_{index}") + ["-p", f"gain:={value}"], f"startup-invalid-{index}")
        code, log = children.finished(item, timeout_s=8.0)
        require(code != 0 and "gain must be finite" in log, f"启动{value}须由业务校验拒绝：code={code}\n{log}")
        outcomes.append({"input": value, "accepted": False, "exitCode": code,
                         "reasonContains": "gain must be finite"})
    return {"language": language, "startupOverrides": outcomes}


def parameter_atomicity(children, namespace):
    """独立最小Node证明逐项提交可部分成功，而原子批次失败时均不提交。"""
    from rcl_interfaces.msg import SetParametersResult
    from rclpy.parameter import Parameter
    results = {}
    for atomic in (False, True):
        label = "atomic" if atomic else "individual"
        with probe(namespace, "parameter_" + label) as node:
            node.declare_parameter("alpha", 0.0)
            node.declare_parameter("beta", 0.0)
            callback_batches = []

            def validate(parameters):
                callback_batches.append([p.name for p in parameters])
                return SetParametersResult(successful=all(p.value >= 0.0 for p in parameters),
                                           reason="negative value rejected" if any(p.value < 0.0 for p in parameters) else "")

            node.add_on_set_parameters_callback(validate)
            requested = [Parameter("alpha", value=1.0), Parameter("beta", value=-1.0)]
            if atomic:
                response = node.set_parameters_atomically(requested)
                accepted = [response.successful]
                require(accepted == [False], "原子批次应整体拒绝")
            else:
                accepted = [r.successful for r in node.set_parameters(requested)]
                require(accepted == [True, False], "逐项调用应有两个独立结果")
            stored = [node.get_parameter("alpha").value, node.get_parameter("beta").value]
            require(stored == ([0.0,0.0] if atomic else [1.0,0.0]), f"{label}提交语义不符：{stored}")
            require(callback_batches == ([["alpha","beta"]] if atomic else [["alpha"],["beta"]]),
                    f"验证回调批次不符：{callback_batches}")
            results[label] = {"accepted": accepted, "stored": stored,
                              "callbackParameterBatches": callback_batches}
    return results


def launch_frontends(children, namespace):
    """解析Python/XML/YAML同一描述；不启动demo节点，不将解析通过称为运行通过。"""
    from launch import LaunchContext
    from launch.actions import DeclareLaunchArgument
    from launch.frontend import Parser
    from launch.launch_description_sources import PythonLaunchDescriptionSource
    from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
    from launch_ros.actions import Node
    folder = PREFIX / "share/learning_bringup/launch"
    results = []
    for extension in ("py", "xml", "yaml"):
        path = folder / f"telemetry.launch.{extension}"
        require(path.is_file(), f"launch文件未安装：{path}")
        context = LaunchContext()
        if extension == "py":
            description = PythonLaunchDescriptionSource(str(path)).get_launch_description(context)
        else:
            entity, parser = Parser.load(str(path))
            description = parser.parse_description(entity)
        arguments = [a for a in description.entities if isinstance(a, DeclareLaunchArgument)]
        nodes = [a for a in description.entities if isinstance(a, Node)]
        require(len(description.entities) == 3 and len(arguments) == 1 and len(nodes) == 2,
                f"{extension}应包含1个参数和2个Node动作")
        require(arguments[0].name == "robot_ns", f"{extension}缺少robot_ns参数")
        require(perform_substitutions(context, arguments[0].default_value) == "robot1", "默认命名空间不符")
        # Python前端可保留原始str，XML/YAML前端可生成Substitution列表；
        # 先正规化再求值，不能直接把str逐字符当成Substitution对象。
        entries = [(perform_substitutions(context,normalize_to_list_of_substitutions(n.node_package)),
                    perform_substitutions(context,normalize_to_list_of_substitutions(n.node_executable))) for n in nodes]
        require(entries == [("demo_nodes_cpp","talker"),("demo_nodes_py","listener")],
                f"{extension}启动入口不符：{entries}")
        results.append({"file": str(path), "entities": 3, "argument": "robot_ns",
                        "default": "robot1", "nodeEntries": entries, "parsedOnly": True})
    return {"frontends": results}


CASES = {
    "inventory": (inventory, (), 30.0),
    "topic_cpp_to_python": (topic_exchange, ("cpp", "py"), 22.0),
    "topic_python_to_cpp": (topic_exchange, ("py", "cpp"), 22.0),
    "service_cpp_to_python": (service_exchange, ("cpp",), 25.0),
    "service_python_to_cpp": (service_exchange, ("py",), 25.0),
    "action_cpp_success": (action_exchange, ("cpp", False), 36.0),
    "action_cpp_cancel": (action_exchange, ("cpp", True), 36.0),
    "action_python_success": (action_exchange, ("py", False), 36.0),
    "action_python_cancel": (action_exchange, ("py", True), 36.0),
    "parameters_cpp_dynamic": (parameters_dynamic, ("cpp",), 40.0),
    "parameters_python_dynamic": (parameters_dynamic, ("py",), 40.0),
    "parameters_cpp_startup": (parameters_startup, ("cpp",), 35.0),
    "parameters_python_startup": (parameters_startup, ("py",), 35.0),
    "parameter_api_atomicity": (parameter_atomicity, (), 15.0),
    "launch_frontends": (launch_frontends, (), 15.0),
}


def versions():
    """从实际已source环境读取版本，不把教材标注版本当作运行证据。"""
    info = {"python": sys.version, "pythonExecutable": sys.executable,
            "platform": platform.platform(), "rosDistro": os.environ.get("ROS_DISTRO"),
            "modules": {}, "rosPackages": {}}
    for name in ("rclpy", "launch", "launch_ros", "ament_index_python"):
        try:
            info["modules"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            info["modules"][name] = "未发现Python分发元数据"
    try:
        from ament_index_python.packages import get_package_share_directory
        for name in ("rclcpp", "rclpy", "rmw_fastrtps_cpp", *PACKAGES):
            path = Path(get_package_share_directory(name)) / "package.xml"
            info["rosPackages"][name] = ET.parse(path).getroot().findtext("version")
    except Exception as exc:
        info["environmentError"] = repr(exc)
    return info


def worker(case):
    """执行一个案例并始终输出结构化结果；清理先于结果标记输出。"""
    started = time.monotonic()
    payload = {"case": case, "status": "failed"}
    with tempfile.TemporaryDirectory(prefix="ros2-foundation-test-") as directory:
        env = isolated_environment()
        env["ROS_LOG_DIR"] = str(Path(directory) / "ros-logs")
        # Python内的rclpy/launch也读取该目录，防止向用户~/.ros写日志。
        os.environ.update(env)
        children = Children(directory, env)
        namespace = f"/foundation_validation/p{os.getpid()}/{case}"
        payload["namespace"] = namespace
        try:
            require(os.environ.get("ROS_DISTRO") == "jazzy", "先source /opt/ros/jazzy/setup.bash")
            require(PREFIX.is_dir(), f"安装前缀不存在：{PREFIX}")
            operation, arguments, _ = CASES[case]
            payload["measurements"] = operation(children, namespace, *arguments)
            payload["status"] = "passed"
        except BaseException:
            payload["error"] = traceback.format_exc()
        finally:
            payload["processes"] = children.close()
            if any(p["cleanupError"] or p["exitCode"] is None for p in payload["processes"]):
                payload["status"] = "failed"
                payload["cleanupFailure"] = True
    payload["durationS"] = round(time.monotonic() - started, 6)
    print(RESULT_MARKER + json.dumps(payload, ensure_ascii=False, allow_nan=False), flush=True)
    return 0 if payload["status"] == "passed" else 1


class FoundationExamplesTest(unittest.TestCase):
    """父进程用进程组与总期限包住每例，避免被ROS内部等待拖住整轮验证。"""

    def exercise(self, case):
        started = time.monotonic()
        command = [SYSTEM_PYTHON, str(Path(__file__).resolve()), "--worker", case]
        record = {"case": case, "command": command, "workerDeadlineS": CASES[case][2]}
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=isolated_environment(), start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=CASES[case][2])
        except BaseException as exc:
            # 只操作当前worker的新进程组；绝不按程序名pkill，也不操作用户节点。
            record["outerError"] = repr(exc)
            os.killpg(process.pid, signal.SIGINT)
            try:
                stdout, stderr = process.communicate(timeout=4.0)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate(timeout=3.0)
        record.update(exitCode=process.returncode, stdout=stdout, stderr=stderr,
                      durationS=round(time.monotonic()-started, 6))
        markers = [line[len(RESULT_MARKER):] for line in stdout.splitlines() if line.startswith(RESULT_MARKER)]
        if markers:
            record["result"] = json.loads(markers[-1])
        record["status"] = "passed" if process.returncode == 0 and not record.get("outerError") and record.get("result",{}).get("status") == "passed" else "failed"
        RECORDS.append(record)
        detail = record.get("result",{}).get("error",stderr or record.get("outerError",""))
        self.assertEqual(record["status"], "passed", f"{case}失败；完整证据写入JSON。\n{detail[-2800:]}")


for index, case in enumerate(CASES, 1):
    # 每个案例独立报告；闭包默认参数固定当前case，避免循环变量晚绑定。
    def test_case(self, chosen=case):
        self.exercise(chosen)
    test_case.__doc__ = f"真实ROS基础工程：{case}"
    setattr(FoundationExamplesTest, f"test_{index:02d}_{case}", test_case)


def write_evidence(path, outcome, elapsed_s):
    """保存当前运行、源码摘要和精确范围；失败也写证据，不覆盖为“预计通过”。"""
    source_hashes = []
    for file in sorted(SOURCE.rglob("*")):
        if file.is_file() and "__pycache__" not in file.parts and not {"build","install","log"}.intersection(file.relative_to(SOURCE).parts):
            source_hashes.append({"file": str(file.relative_to(ROOT)),
                                  "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
    env = isolated_environment()
    previous_attempts = []
    if path.is_file():
        previous = json.loads(path.read_text())
        previous_attempts = list(previous.pop("previousAttempts", []))
        # 保留上一轮实际失败日志，不因提高执行权限或修正测试器而抹除历史。
        previous_attempts.append(previous)
    installed_hashes = []
    for package,names in EXECUTABLES.items():
        for name in names:
            file = PREFIX/"lib"/package/name
            if file.is_file():
                installed_hashes.append({"file":str(file),"sha256":hashlib.sha256(file.read_bytes()).hexdigest()})
    evidence = {
        "schemaVersion": 1, "checkedAt": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "verification": "本轮实际运行Jazzy安装产物及保留Python示例；不是计划或迁移前旧日志。",
        "passed": outcome.wasSuccessful(), "testsRun": outcome.testsRun,
        "failures": len(outcome.failures), "errors": len(outcome.errors),
        "durationS": round(elapsed_s,6), "installPrefix": str(PREFIX),
        "executionContext": os.environ.get("FOUNDATION_TEST_EXECUTION_CONTEXT","default-sandbox"),
        "invocation": [SYSTEM_PYTHON, str(Path(__file__).resolve())],
        "environment": {key: env[key] for key in ["ROS_DOMAIN_ID","ROS_AUTOMATIC_DISCOVERY_RANGE","ROS_LOCALHOST_ONLY","RMW_IMPLEMENTATION"]},
        "versions": versions(), "sourceFingerprints": source_hashes,
        "installedExecutableFingerprints": installed_hashes,
        "testScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "previousAttempts": previous_attempts,
        "results": RECORDS,
        "scope": ["十包安装索引、十个可执行入口、四种接口与Action类型支持", "C++/Python话题双向真实接收",
                  "C++/Python服务双向请求4+8=12", "两种Count服务端的成功和取消：使用保留Python客户端",
                  "两种参数节点的动态有限性/范围/类型拒绝、拒绝后保值与输出生效",
                  "两种参数节点有效启动覆盖、越界及NaN启动拒绝", "独立rclpy Node逐项/原子参数提交差异", "Python/XML/YAML launch解析及目标入口核对"],
        "limits": ["本脚本未执行colcon构建；安装产物由主任务在本轮先行构建。",
                   "Action工程没有C++客户端，本轮测试C++与Python服务端配合保留Python客户端；不冒充C++客户端验证。",
                   "三种launch只解析，不证明它们的节点启动或持续通信已运行。",
                   "仅本机LOCALHOST独立ROS域，不验证跨机网络、DDS安全、仿真、驱动、MCU或硬件。",
                   "进程退出码中SIGINT等负值属于测试清理；断言的客户端成功或预期配置失败分别记录。",
                   "固定小规模数值和计数案例不证明任意输入、硬实时期限或设备停车行为。"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2,allow_nan=False)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    parser.add_argument("--evidence", type=Path, default=ROOT/"validation-evidence/foundation-current-validation.json")
    arguments = parser.parse_args()
    if arguments.worker:
        return worker(arguments.worker)
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FoundationExamplesTest)
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    write_evidence(arguments.evidence, outcome, time.monotonic()-started)
    print(f"实际验证记录：{arguments.evidence.resolve()}")
    return 0 if outcome.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
