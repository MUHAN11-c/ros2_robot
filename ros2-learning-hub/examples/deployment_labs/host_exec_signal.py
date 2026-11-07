#!/usr/bin/env python3
"""原安装产物的宿主source+exec+SIGTERM正例；不运行副本或Docker。

输入：显式underlay/overlay入口、Config可执行及预期SHA；这些都应来自可信本机记录。
输出：同一PID已成为指定ELF、合成节点ready、子进程快照、一次TERM、exit0及原始日志。
所有期限为monotonic秒。只清理本程序创建的PID；默认报告/tmp/host-exec-signal.json。
--help只用标准库。节点只输出合成Float64教学速度，不发送任何设备命令。
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def file_sha(path):
    # 只对三个显式可信文件计算SHA；节点文件限制64MiB，不递归扫描目录。
    resolved = path.resolve(strict=True)
    require(resolved.is_file() and resolved.stat().st_size <= 64 * 1024 * 1024, "文件不存在或超过64MiB")
    return hashlib.sha256(resolved.read_bytes()).hexdigest()


def children_of(pid):
    """仅枚举本次PID自己的task目录，检查所有线程的孩子，最多128个task。"""
    tasks = []
    with os.scandir(f"/proc/{pid}/task") as entries:
        for entry in entries:
            require(len(tasks) < 128, "本例task数量超过128，停止检查")
            tasks.append(Path(entry.path))
    children = set()
    for task in tasks:
        try:
            data = (task / "children").read_text()
        except FileNotFoundError:
            continue
        require(len(data) <= 4096, "子进程列表超过有界范围")
        children.update(int(value) for value in data.split())
    return sorted(children)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--underlay-setup", type=Path, required=True)
    parser.add_argument("--overlay-setup", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--domain-id", type=int, default=226)
    parser.add_argument("--timeout-s", type=float, default=8.0)
    parser.add_argument("--report", type=Path, default=Path("/tmp/host-exec-signal.json"))
    args = parser.parse_args()
    if not math.isfinite(args.timeout_s) or not 1 <= args.timeout_s <= 20:
        parser.error("timeout-s须为[1,20]有限秒数")
    if not 0 <= args.domain_id <= 232 or not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256):
        parser.error("domain-id须在0..232，expected-sha256须为64个小写十六进制字符")
    report_path = args.report.absolute()
    require(report_path.parent.resolve(strict=True).is_relative_to(Path("/tmp")), "报告只能另存/tmp")
    require(file_sha(args.executable) == args.expected_sha256, "原安装可执行SHA与明确预期不同")
    result = {"schemaVersion": 1, "checkedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
              "passed": False, "invocation": [sys.executable, *sys.argv], "signalsSent": [],
              "expectedExecutable": str(args.executable), "expectedSha256": args.expected_sha256,
              "underlaySetup": str(args.underlay_setup), "underlaySetupSha256": file_sha(args.underlay_setup),
              "overlaySetup": str(args.overlay_setup), "overlaySetupSha256": file_sha(args.overlay_setup),
              "containerExecuted": False, "copiedArtifactExecuted": False}
    child = None
    with tempfile.TemporaryDirectory(prefix="deployment-host-signal-") as temporary:
        log_path = Path(temporary) / "node.log"
        with log_path.open("w") as stream:
            try:
                env = dict(os.environ)
                # 环境入口自己建立ROS路径，避免当前终端的旧overlay意外补齐缺失项。
                for key in ("AMENT_PREFIX_PATH", "CMAKE_PREFIX_PATH", "COLCON_PREFIX_PATH",
                            "PYTHONPATH", "LD_LIBRARY_PATH", "COLCON_CURRENT_PREFIX", "AMENT_CURRENT_PREFIX"):
                    env.pop(key, None)
                env.update(ROS_DOMAIN_ID=str(args.domain_id), ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
                           RMW_IMPLEMENTATION="rmw_fastrtps_cpp", ROS_LOG_DIR=str(Path(temporary) / "ros-log"))
                env.pop("ROS_LOCALHOST_ONLY", None); env.pop("ROS_STATIC_PEERS", None)
                command = ["/bin/bash", "--noprofile", "--norc", str(HERE / "host_entrypoint.sh"),
                           str(args.underlay_setup.resolve()), str(args.overlay_setup.resolve()),
                           str(args.executable.absolute()), "--ros-args", "-r", "__node:=host_exec_probe",
                           "-r", f"__ns:=/deployment_signal_{os.getpid()}", "-p", "gain:=1.0"]
                # 新会话使读者Ctrl+C后仍能由finally按保存的PID清理，不波及其他ROS进程。
                child = subprocess.Popen(command, stdout=stream, stderr=stream, env=env, start_new_session=True)
                result.update(command=command, pid=child.pid, environment={key: env[key] for key in
                    ("ROS_DOMAIN_ID", "ROS_AUTOMATIC_DISCOVERY_RANGE", "RMW_IMPLEMENTATION")})
                deadline = time.monotonic() + args.timeout_s
                events = []
                while time.monotonic() < deadline:
                    require(child.poll() is None, "节点就绪前已退出")
                    require(log_path.stat().st_size <= 65536, "日志超过64KiB上限")
                    for line in log_path.read_text(errors="replace").splitlines():
                        if "COMPONENT_LAB_EVENT " in line:
                            events.append(json.loads(line.split("COMPONENT_LAB_EVENT ", 1)[1]))
                    if any(e["event"] == "constructed" and e["role"] == "config" for e in events):
                        break
                    time.sleep(0.02)
                else:
                    raise AssertionError("未在单调软期限内观察到合成Config节点ready")
                observed_exe = Path(os.readlink(f"/proc/{child.pid}/exe"))
                require(os.path.samefile(observed_exe, args.executable), "原shell PID没有变成指定节点ELF")
                require(any(e["pid"] == child.pid for e in events), "节点日志PID与父启动PID不符")
                descendants = children_of(child.pid)
                require(not descendants, "此直接exec正例不应有子进程")
                result.update(observedExecutable=str(observed_exe),
                              observedExecutableSha256=file_sha(observed_exe),
                              samePidBecameNode=True, childrenBeforeSignal=descendants)
                sent_at = time.monotonic()
                child.send_signal(signal.SIGTERM)  # 只给这个PID发一次TERM；不是终端进程组Ctrl+C。
                result["signalsSent"].append("SIGTERM")
                child.wait(timeout=3.0)
                result.update(exitCode=child.returncode, signalToExitS=time.monotonic() - sent_at,
                              pidAbsentAfterReap=not Path(f"/proc/{child.pid}").exists())
                require(child.returncode == 0 and result["pidAbsentAfterReap"], "原节点未正常exit0并回收")
                require(file_sha(args.executable) == args.expected_sha256, "实验改变了原安装文件")
                result["passed"] = True
            except BaseException:
                result["error"] = traceback.format_exc(limit=10)[-6000:]
            finally:
                if child is not None and child.poll() is None:
                    # 已发TERM的进程不再重复TERM；先等有限窗口，必要时仅对自建PID升级KILL。
                    if "SIGTERM" not in result["signalsSent"]:
                        child.terminate(); result["signalsSent"].append("SIGTERM_cleanup")
                    try:
                        child.wait(timeout=2.0)
                    except (subprocess.TimeoutExpired, KeyboardInterrupt):
                        child.kill(); result["signalsSent"].append("SIGKILL_cleanup")
                        child.wait(timeout=2.0)
                result["reaped"] = child is not None and child.poll() is not None
        data = log_path.read_bytes()
        result.update(log=data[:65536].decode(errors="replace"), logTruncated=len(data) > 65536,
                      logSha256=hashlib.sha256(data).hexdigest())
    result["sourceHashes"] = [{"file": name, "sha256": file_sha(HERE / name)}
                               for name in ("host_exec_signal.py", "host_entrypoint.sh")]
    result["limits"] = ["只对原安装Config合成节点做宿主exec/TERM检查；未运行副本或Docker。",
                        "同PID/无子进程为本次观测，不等于任意入口或ros2 run包装都会转发TERM。",
                        "exit0和进程回收不证明设备停车；本例没有设备命令。"]
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"passed": result["passed"], "pid": result.get("pid"),
                      "exitCode": result.get("exitCode"), "report": str(report_path)}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
