#!/usr/bin/env python3
"""Jazzy执行器/回调组的受控时间线，以及真实client Future完成回调实验。

运行（--help不需要ROS导入）：
    source /opt/ros/jazzy/setup.bash
    timeout --signal=INT --kill-after=5s 100s /usr/bin/python3 executor_group_lab.py

输入：稳态timer、受控Event门闩、AddTwoInts请求4+8；无硬件或仿真。
输出：三组矩阵与一个Future场景的原始monotonic时间线、线程ID、并发数及JSON证据。
单位：所有周期/观察窗口/期限均为秒；heartbeat、并发数与整数和均无量纲。
矩阵：单线程+分组；两线程+同互斥组；两线程+分互斥组。
慢回调先设置started，再等待release；协调线程看到started后才启用heartbeat。
负例还检查heartbeat的timer已经ready，避免把“尚未开始”误当串行证据。
Event.wait模拟释放GIL的IO等待，不测量或宣称纯Python CPU计算加速。
Future场景使用真实Client.call_async；完成回调等待时，再触发与client同组的timer。
这只验证固定版本的generic Task路径，不把它泛化为所有语言/Action/未来版本。
每例在新进程组中运行，父进程有限等待并只清理自己的组；软期限不能抢占任意
长原生调用，所以示例回调有门闩上限，命令另用进程级timeout兜底。
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import inspect
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo


ROOT=Path(__file__).resolve().parents[2]
MARKER="EXECUTOR_GROUP_RESULT="
CASES=("single_thread_distinct_groups","two_threads_same_group",
       "two_threads_distinct_groups","client_future_continuation")


def require(condition,description):
    if not condition:
        raise AssertionError(description)


def arguments():
    """先解析纯标准库参数；有限性与相对预算在创建ROS资源前检查。"""
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case",choices=("all",*CASES),default="all")
    parser.add_argument("--domain-id",type=int,default=219)
    parser.add_argument("--period-s",type=float,default=0.02,help="稳态heartbeat周期，至少0.01秒")
    parser.add_argument("--observe-s",type=float,default=0.35,help="门闩未释放时的有限观察窗口")
    parser.add_argument("--start-timeout-s",type=float,default=3.0,help="开始/完成事件及发现等待期限")
    parser.add_argument("--callback-cap-s",type=float,default=5.0,help="回调Event.wait的最大秒数")
    parser.add_argument("--cleanup-timeout-s",type=float,default=3.0)
    parser.add_argument("--worker-timeout-s",type=float,default=20.0,help="父进程包住每例的总期限")
    parser.add_argument("--report",type=Path,default=ROOT/"validation-evidence/executor-group-current-validation.json")
    parser.add_argument("--worker",choices=CASES,help=argparse.SUPPRESS)
    options=parser.parse_args()
    values=[options.period_s,options.observe_s,options.start_timeout_s,
            options.callback_cap_s,options.cleanup_timeout_s,options.worker_timeout_s]
    if not all(math.isfinite(x) and x>0 for x in values):
        parser.error("所有时间参数必须是有限正秒数")
    if not 0<=options.domain_id<=232:
        parser.error("domain-id须位于0..232")
    if options.period_s<0.01 or options.observe_s<3*options.period_s:
        parser.error("周期至少10ms，观察窗口至少三个周期")
    if options.callback_cap_s<options.observe_s+1.0:
        parser.error("回调保护上限至少比观察窗口长1s")
    minimum=2*options.start_timeout_s+options.callback_cap_s+2*options.cleanup_timeout_s+1.0
    if options.worker_timeout_s<minimum:
        parser.error(f"worker期限至少{minimum}s，须覆盖事件/门闩及清理预算")
    return options


def environment(domain):
    """显式用Jazzy发现范围；不继承旧localhost开关或静态远端peer。"""
    env=dict(os.environ)
    env.pop("ROS_LOCALHOST_ONLY",None)
    env.pop("ROS_STATIC_PEERS",None)
    env.update(ROS_DOMAIN_ID=str(domain),ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
               RMW_IMPLEMENTATION="rmw_fastrtps_cpp",PYTHONUNBUFFERED="1",
               PYTHONDONTWRITEBYTECODE="1")
    return env


def ros_modules():
    """仅worker运行时才导入ROS；父进程负责外层保护与证据输出。"""
    import rclpy
    from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
    from rclpy.clock import Clock
    from rclpy.clock_type import ClockType
    from rclpy.context import Context
    from rclpy.executors import Executor,MultiThreadedExecutor,SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.task import Future
    from example_interfaces.srv import AddTwoInts
    return SimpleNamespace(**locals())


class Timeline:
    """短锁只保护时间线/计数，不在持锁时等待门闩或执行模拟IO。"""
    def __init__(self):
        self.origin=time.monotonic()
        self.lock=threading.Lock()
        self.events=[]
        self.active={}
        self.maximum=0
        self.next_span=0

    def enter(self,callback,**fields):
        with self.lock:
            self.next_span+=1
            span=self.next_span
            self.active[span]=callback
            self.maximum=max(self.maximum,len(self.active))
            self.events.append({"event":"start","span":span,"callback":callback,
                "monotonicS":time.monotonic(),"elapsedS":time.monotonic()-self.origin,
                "threadId":threading.get_ident(),"nativeThreadId":threading.get_native_id(),
                "activeCallbacks":list(self.active.values()),**fields})
            return span

    def leave(self,span):
        with self.lock:
            callback=self.active.pop(span)
            self.events.append({"event":"end","span":span,"callback":callback,
                "monotonicS":time.monotonic(),"elapsedS":time.monotonic()-self.origin,
                "threadId":threading.get_ident(),"nativeThreadId":threading.get_native_id(),
                "activeCallbacks":list(self.active.values())})

    def has(self,callback):
        with self.lock:
            return callback in self.active.values()

    def snapshot(self):
        with self.lock:
            return {"events":list(self.events),"maxConcurrency":self.maximum,
                    "activeCallbacksAtEnd":list(self.active.values())}


class Resources:
    """同Context的Node与Executor；只有本类创建的spin线程和线程池被清理。"""
    def __init__(self,modules,options,threads,case):
        self.m=modules
        self.o=options
        self.threads=threads
        self.context=modules.Context()
        self.nodes=[]
        self.timers=[]
        self.release_events=[]
        self.spin_errors=[]
        self.baseline_threads={t.ident for t in threading.enumerate()}
        modules.rclpy.init(args=[],context=self.context)
        self.executor=(modules.SingleThreadedExecutor(context=self.context) if threads==1 else
                       modules.MultiThreadedExecutor(num_threads=threads,context=self.context))
        self.namespace=f"/executor_group_lab/p{os.getpid()}/{case}"
        self.thread=threading.Thread(target=self._spin,name="lab-executor-spin",daemon=False)

    def node(self,name):
        node=self.m.Node(name,namespace=self.namespace,context=self.context,enable_rosout=False)
        self.nodes.append(node)
        self.executor.add_node(node)
        return node

    def timer(self,node,period,callback,group):
        # STEADY时钟避免软件/clock缺失或暂停影响这里的调度对照。
        clock=self.m.Clock(clock_type=self.m.ClockType.STEADY_TIME)
        timer=node.create_timer(period,callback,callback_group=group,clock=clock,autostart=False)
        self.timers.append(timer)
        return timer

    def _spin(self):
        try:
            self.executor.spin()
        except BaseException:
            self.spin_errors.append(traceback.format_exc())

    def start(self):
        self.thread.start()

    def arm(self,timer):
        # 从协调线程启用原先取消的timer后显式唤醒等待集；不依赖刚好另有事件。
        timer.reset()
        self.executor.wake()

    def close(self):
        """先解除本例所有门闩，再停调度/回收线程，最后销毁节点及Context。"""
        cleanup={"errors":[],"spinThreadJoined":False,"executorShutdownReturned":False}
        for event in self.release_events:
            event.set()
        for timer in self.timers:
            try:
                timer.cancel()
            except BaseException:
                cleanup["errors"].append(traceback.format_exc())
        try:
            # MTE的线程池join可能超出软timeout；回调均有本例可释放的门闩，
            # 外层worker进程保护仍保留，不能把此参数当作原生调用抢占器。
            if self.threads==1:
                stopped=self.executor.shutdown(timeout_sec=self.o.cleanup_timeout_s)
            else:
                stopped=self.executor.shutdown(timeout_sec=self.o.cleanup_timeout_s,wait_for_threads=True)
            cleanup["executorShutdownReturned"]=bool(stopped)
            if self.thread.ident is not None:
                self.thread.join(timeout=self.o.cleanup_timeout_s)
            cleanup["spinThreadJoined"]=not self.thread.is_alive()
        except BaseException:
            cleanup["errors"].append(traceback.format_exc())
        # 不在仍运行的线程下销毁ROS实体；这种失败交由父进程外层保护处理。
        if cleanup["spinThreadJoined"] and cleanup["executorShutdownReturned"]:
            for node in self.nodes:
                self.executor.remove_node(node)
                node.destroy_node()
            if self.context.ok():
                self.m.rclpy.shutdown(context=self.context)
        cleanup["contextOkAfterCleanup"]=self.context.ok()
        cleanup["remainingNewPythonThreads"]=[{"name":t.name,"ident":t.ident}
            for t in threading.enumerate() if t.ident not in self.baseline_threads]
        cleanup["spinErrors"]=list(self.spin_errors)
        return cleanup


def matrix(modules,options,case,record):
    """受控观察：先证明慢回调正在执行，再使heartbeat ready，最后释放慢工作。"""
    threads=1 if case.startswith("single") else 2
    separate=case!="two_threads_same_group"
    resources=Resources(modules,options,threads,case)
    timeline=Timeline()
    record.update(threads=threads,groupLayout="distinct MutuallyExclusive" if separate else "same MutuallyExclusive",
                  namespace=resources.namespace,slowWork="Event.wait：释放GIL的模拟IO门闩，不是CPU基准")
    started=threading.Event()
    release=threading.Event()
    finished=threading.Event()
    heartbeat_any=threading.Event()
    heartbeat_inside=threading.Event()
    resources.release_events.append(release)
    counts={"heartbeat":0,"heartbeatWhileSlow":0}
    cap_expired=[]
    try:
        node=resources.node("matrix_probe")
        slow_group=modules.MutuallyExclusiveCallbackGroup()
        heartbeat_group=modules.MutuallyExclusiveCallbackGroup() if separate else slow_group

        def slow():
            slow_timer.cancel()  # 一次性慢回调，不让周期重入混入本实验。
            span=timeline.enter("slow")
            started.set()
            try:
                if not release.wait(timeout=options.callback_cap_s):
                    cap_expired.append(True)
            finally:
                timeline.leave(span)
                finished.set()

        def heartbeat():
            inside=timeline.has("slow")
            span=timeline.enter("heartbeat",slowWasActiveAtEntry=inside)
            try:
                # 计数只有heartbeat这个写入者；协调线程在事件后读取快照。
                counts["heartbeat"]+=1
                if inside:
                    counts["heartbeatWhileSlow"]+=1
                    heartbeat_inside.set()
                heartbeat_any.set()
            finally:
                timeline.leave(span)

        slow_timer=resources.timer(node,options.period_s,slow,slow_group)
        heartbeat_timer=resources.timer(node,options.period_s,heartbeat,heartbeat_group)
        resources.start()
        resources.arm(slow_timer)
        require(started.wait(options.start_timeout_s),"未观察到真实slow回调开始")
        begin=time.monotonic()
        resources.arm(heartbeat_timer)  # 明确在slow开始之后启用。
        observed=heartbeat_inside.wait(options.observe_s)
        # 正例也保持同样完整观察窗口，避免把更短的慢工作混入三配置对照。
        # Event.wait是协调门闩等待；接受判据仍是事件/并发关系，不是睡眠猜测。
        remaining=begin+options.observe_s-time.monotonic()
        if remaining>0:
            release.wait(timeout=remaining)
        end=time.monotonic()
        held=timeline.has("slow") and not finished.is_set()
        snapshot=dict(counts)
        ready=heartbeat_timer.is_ready()
        record["heldWindow"]={"startMonotonicS":begin,"endMonotonicS":end,
            "maximumObservationS":options.observe_s,"actualElapsedS":end-begin,
            "slowStillActive":held,"heartbeatObservedInside":observed,
            "heartbeatTimerReadyAtWindowEnd":ready,"countsAtWindowEnd":snapshot,
            "spinThreadAlive":resources.thread.is_alive()}
        require(held and resources.thread.is_alive(),"观察窗口结束前slow或执行器已经退出，负例不能归因")
        if threads==2 and separate:
            require(observed and snapshot["heartbeatWhileSlow"]>=1,"分组双线程未在受控窗口观察到重叠；保留原始负载证据")
        else:
            require(not observed and snapshot["heartbeat"]==0,"串行配置在slow门闩持有期间执行了heartbeat")
            require(ready,"负例的heartbeat尚未ready，不能证明被线程/组约束阻塞")
        release.set()
        require(finished.wait(options.start_timeout_s),"释放门闩后slow未结束")
        require(heartbeat_any.wait(options.start_timeout_s),"释放后heartbeat仍未实际执行")
        heartbeat_timer.cancel()
        require(not cap_expired,"慢回调由保护上限而非协调线程释放，实验无效")
        record["counts"]=dict(counts)
        record["assertions"]={"controlledSlowStart":True,"heldWindowValid":True,
            "expectedOverlap":threads==2 and separate,"observedOverlap":observed,
            "heartbeatEventuallyRan":True,"callbackCapExpired":False}
        record["passed"]=True
    except BaseException:
        record["error"]=traceback.format_exc()
    finally:
        record["cleanup"]=resources.close()
        record["timeline"]=timeline.snapshot()
        maximum=record["timeline"]["maxConcurrency"]
        expected_max=2 if threads==2 and separate else 1
        if maximum!=expected_max or record["timeline"]["activeCallbacksAtEnd"]:
            record["passed"]=False
            record["concurrencyAssertionError"]={"expectedMax":expected_max,"actualMax":maximum}


def client_continuation(modules,options,record):
    """真实client Future：done持有门闩期间，同client互斥组的timer能否进入。"""
    resources=Resources(modules,options,2,"client_future_continuation")
    timeline=Timeline()
    done_started=threading.Event()
    done_release=threading.Event()
    done_finished=threading.Event()
    holder_started=threading.Event()
    holder_release=threading.Event()
    holder_finished=threading.Event()
    resources.release_events.extend([done_release,holder_release])
    details={"responseSum":None,"holderWhileDone":False,"callbackCapExpired":False,
             "holderCapExpired":False}
    record.update(threads=2,namespace=resources.namespace,
                  futureKind="真实Client.call_async(AddTwoInts)，不是手动set_result的Future",
                  phaseTimes={})
    try:
        server_node=resources.node("sum_server")
        client_node=resources.node("client_and_timer")
        client_group=modules.MutuallyExclusiveCallbackGroup()

        def respond(request,response):
            span=timeline.enter("server")
            try:
                response.sum=request.a+request.b
                return response
            finally:
                timeline.leave(span)

        server=server_node.create_service(modules.AddTwoInts,"sum",respond)
        client=client_node.create_client(modules.AddTwoInts,"sum",callback_group=client_group)

        def holder():
            holder_timer.cancel()
            inside=timeline.has("done")
            span=timeline.enter("same_client_group_timer",doneWasActiveAtEntry=inside)
            try:
                details["holderWhileDone"]=inside
                # 当前timer确实占住client的同一个互斥组，generic done仍在另一线程等待。
                details["groupAllowsClientWhileTimerActive"]=client_group.can_execute(client)
                holder_started.set()
                # timer也维持一个受控长回调；两线程均只等协调线程解除门闩，
                # 期间不再依赖任何响应handler，不能把等待响应死锁混入结论。
                if not holder_release.wait(timeout=options.callback_cap_s):
                    details["holderCapExpired"]=True
            finally:
                timeline.leave(span)
                holder_finished.set()

        holder_timer=resources.timer(client_node,options.period_s,holder,client_group)
        require(client.callback_group is holder_timer.callback_group is client_group,"client/timer没有绑定同一个组")
        resources.start()
        require(client.wait_for_service(timeout_sec=options.start_timeout_s),"未发现本例服务")
        request=modules.AddTwoInts.Request(a=4,b=8)
        record["phaseTimes"]["requestSubmittedMonotonicS"]=time.monotonic()
        future=client.call_async(request)
        record["futureDoneAtRegistration"]=future.done()

        def done(completed_future):
            span=timeline.enter("done")
            try:
                require(completed_future.done() and completed_future.exception() is None,"完成回调收到异常/未完成Future")
                details["responseSum"]=completed_future.result().sum
                record["phaseTimes"]["doneStartedWithResultMonotonicS"]=time.monotonic()
                done_started.set()
                if not done_release.wait(timeout=options.callback_cap_s):
                    details["callbackCapExpired"]=True
            finally:
                timeline.leave(span)
                done_finished.set()

        future.add_done_callback(done)
        require(done_started.wait(options.start_timeout_s),"真实client Future未触发done回调")
        require(details["responseSum"]==12,"真实服务响应必须为12")
        # Future完成只证明响应值已经交付；handler可能还未执行finally释放组。
        # 明确等到组可接纳client，才启用同组timer；此时没有其他本例实体运行。
        free_deadline=time.monotonic()+options.start_timeout_s
        while not client_group.can_execute(client):
            remaining=free_deadline-time.monotonic()
            require(remaining>0,"响应值已交付但client组未在期限内释放")
            done_release.wait(timeout=min(0.01,remaining))
        record["phaseTimes"]["responseGroupFreeMonotonicS"]=time.monotonic()
        require(timeline.has("done"),"等待响应组释放期间done已经退出")
        begin=time.monotonic()
        record["phaseTimes"]["sameGroupTimerEnabledMonotonicS"]=begin
        resources.arm(holder_timer)  # 仅在done已经进入并持有门闩后启用。
        observed=holder_started.wait(options.observe_s)
        remaining=begin+options.observe_s-time.monotonic()
        if remaining>0:
            done_release.wait(timeout=remaining)
        end=time.monotonic()
        record["heldWindow"]={"startMonotonicS":begin,"endMonotonicS":end,
            "maximumObservationS":options.observe_s,"actualElapsedS":end-begin,
            "doneStillActive":timeline.has("done"),"sameGroupTimerObserved":observed}
        require(observed and details["holderWhileDone"] and timeline.has("done"),
                "未可靠观察到done与client同组timer重叠；不得宣称generic Task边界已实测")
        require(details["groupAllowsClientWhileTimerActive"] is False,"timer执行时应占住client互斥组")
        require(timeline.has("same_client_group_timer"),"同组timer应仍由协调门闩保持活跃")
        record["phaseTimes"]["bothActiveObservedMonotonicS"]=time.monotonic()
        done_release.set()
        holder_release.set()
        require(done_finished.wait(options.start_timeout_s),"释放后done未退出")
        require(holder_finished.wait(options.start_timeout_s),"同组timer未退出")
        require(not details["callbackCapExpired"] and not details["holderCapExpired"],
                "回调靠保护上限自动退出，不能用作受控重叠证据")
        record["assertions"]={"actualServiceSum12":True,"clientAndTimerSameGroup":True,
            "responseHandlerGroupReleasedBeforeTimerEnabled":True,
            "genericDoneOverlappedSameGroupTimer":True,"bothCallbacksHeldByControlledGates":True,
            "mutualExclusionStillAppliesToClientEntity":True}
        record["passed"]=True
    except BaseException:
        record["error"]=traceback.format_exc()
        record["partialConclusion"]="本例未通过时只保留源码解释与原始轨迹；不把generic Task场景算作已验证。"
    finally:
        record["details"]=details
        record["cleanup"]=resources.close()
        record["timeline"]=timeline.snapshot()
        if record["timeline"]["activeCallbacksAtEnd"] or record["timeline"]["maxConcurrency"]<2:
            record["passed"]=False


def provenance(modules):
    """记录实际运行Python库源码的精确范围，不混同下载快照与apt二进制版本。"""
    from ament_index_python.packages import get_package_share_directory
    result={"versions":{"python":sys.version,"pythonExecutable":sys.executable,
            "platform":platform.platform(),"rosDistro":os.environ.get("ROS_DISTRO"),
            "rclpy":importlib.metadata.version("rclpy"),"packages":{}},"runtimeSource":[]}
    for package in ("rclpy","rclcpp","rmw_fastrtps_cpp","example_interfaces"):
        file=Path(get_package_share_directory(package))/"package.xml"
        result["versions"]["packages"][package]=ET.parse(file).getroot().findtext("version")
    APIs=[(modules.Future._schedule_or_invoke_done_callbacks,"Future完成后有executor时排generic Task"),
          (modules.Future.add_done_callback,"已完成Future也可立即调用或排Task，依是否关联executor"),
          (modules.Executor.create_task,"generic Task不附带ROS source_entity回调组"),
          (modules.Executor._take_client,"真实响应先关联executor，再完成Future"),
          (modules.Executor._make_handler,"ROS实体handler另行执行组beginning/ending检查"),
          (modules.MutuallyExclusiveCallbackGroup,"互斥许可只覆盖归属于本组的实体执行")]
    for api,claim in APIs:
        file=Path(inspect.getsourcefile(api)).resolve()
        lines,start=inspect.getsourcelines(api)
        result["runtimeSource"].append({"api":api.__qualname__,"file":str(file),
            "sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
            "lineStart":start,"lineEnd":start+len(lines)-1,"explanation":claim})
    manifest=ROOT/"references/manifest.json"
    if manifest.is_file():
        snapshots=json.loads(manifest.read_text())["snapshots"]
        snapshot=next(s for s in snapshots if s["sourceId"]=="ros2--rclpy" and s["ref"]=="jazzy")
        result["pinnedReference"]={"commit":snapshot["commit"],
            "root":str(ROOT/"references"/snapshot["localPath"]),
            "note":"下载快照是解释依据；本次行为以runtimeSource和实际版本为准。"}
    return result


def worker(options):
    """worker内部ROS日志写临时目录，结束清理后只输出一条结构化时间线。"""
    record={"case":options.worker,"passed":False,"pid":os.getpid(),
            "scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix="ros2-executor-group-") as directory:
        env=environment(options.domain_id)
        os.environ.pop("ROS_LOCALHOST_ONLY",None)
        os.environ.pop("ROS_STATIC_PEERS",None)
        os.environ.update(env)
        os.environ["ROS_LOG_DIR"]=directory
        try:
            modules=ros_modules()
            record["provenance"]=provenance(modules)
            if options.worker=="client_future_continuation":
                client_continuation(modules,options,record)
            else:
                matrix(modules,options,options.worker,record)
            cleanup=record["cleanup"]
            require(cleanup["spinThreadJoined"] and cleanup["executorShutdownReturned"],"执行器线程没有干净退出")
            require(not cleanup["contextOkAfterCleanup"] and not cleanup["remainingNewPythonThreads"],"上下文或新Python线程未清理")
            require(not cleanup["errors"] and not cleanup["spinErrors"],"清理或spin出现异常")
        except BaseException:
            record["passed"]=False
            record["workerError"]=traceback.format_exc()
    record["durationS"]=time.monotonic()-started
    print(MARKER+json.dumps(record,ensure_ascii=False,allow_nan=False),flush=True)
    return 0 if record["passed"] else 1


def child_arguments(options,case):
    command=["/usr/bin/python3",str(Path(__file__).resolve()),"--worker",case]
    for field in ("domain_id","period_s","observe_s","start_timeout_s",
                  "callback_cap_s","cleanup_timeout_s","worker_timeout_s"):
        command.extend(["--"+field.replace("_","-"),str(getattr(options,field))])
    return command


def run_child(options,case):
    """每个worker新建进程组；超时信号只发给这个组，不按进程名清理。"""
    command=child_arguments(options,case)
    started=time.monotonic()
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        text=True,env=environment(options.domain_id),start_new_session=True)
    outer_error=None
    interrupted=False
    try:
        stdout,stderr=process.communicate(timeout=options.worker_timeout_s)
    except (subprocess.TimeoutExpired,KeyboardInterrupt) as error:
        outer_error=repr(error)
        interrupted=isinstance(error,KeyboardInterrupt)
        try:
            os.killpg(process.pid,signal.SIGINT)
        except ProcessLookupError:
            pass
        try:
            stdout,stderr=process.communicate(timeout=3.0)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
            stdout,stderr=process.communicate(timeout=3.0)
    lines=[line[len(MARKER):] for line in stdout.splitlines() if line.startswith(MARKER)]
    result=json.loads(lines[-1]) if lines else None
    record={"case":case,"command":command,"workerDeadlineS":options.worker_timeout_s,
        "exitCode":process.returncode,"stdout":stdout,"stderr":stderr,"result":result,
        "outerError":outer_error,"interrupted":interrupted,"durationS":time.monotonic()-started}
    record["passed"]=process.returncode==0 and outer_error is None and result is not None and result["passed"]
    return record


def main():
    options=arguments()
    if options.worker:
        return worker(options)
    cases=CASES if options.case=="all" else (options.case,)
    started=time.monotonic()
    records=[]
    for case in cases:
        record=run_child(options,case)
        records.append(record)
        print(f"{case}: {'PASS' if record['passed'] else 'FAIL'}",flush=True)
        if record["interrupted"]:
            break
    report={"schemaVersion":1,"checkedAt":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "passed":len(records)==len(cases) and all(r["passed"] for r in records),
        "script":str(Path(__file__).resolve()),"scriptSha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "invocation":[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],
        "parameters":{key:value for key,value in vars(options).items() if key not in ("report","worker")},
        "environment":{"ROS_DOMAIN_ID":str(options.domain_id),"ROS_AUTOMATIC_DISCOVERY_RANGE":"LOCALHOST",
                       "RMW_IMPLEMENTATION":"rmw_fastrtps_cpp","ROS_LOCALHOST_ONLY":"unset","ROS_STATIC_PEERS":"unset"},
        "casesRequested":list(cases),"results":records,"durationS":time.monotonic()-started,
        "scope":"真实Jazzy/rclpy调度；稳态timer与真实AddTwoInts服务。无设备、硬件或仿真。",
        "interpretation":["负例确认slow已开始、heartbeat已ready且门闩仍持有；零heartbeat由执行资源/组约束观察得到。",
                          "Event.wait是释放GIL的模拟IO等待；并发证据不表示纯Python CPU任务加速。",
                          "client Future场景仅在实际重叠断言通过时计为完成；不以源码推断替代运行证据。"],
        "limits":["只断言这些受控回调的并发关系，不保证精确频率、严格实时期限或任意负载调度。",
                  "时间线只统计本实验业务回调，不统计DDS后台线程或所有内部响应handler。",
                  "回调组不是保护任意线程/Task共享数据的通用锁，仍需显式状态同步。",
                  "Future结论属于记录的rclpy实现；不泛化为所有Action、C++ continuation或后续版本。",
                  "软期限不能抢占长原生调用；每例父进程期限与外部timeout分别保护退出。"]}
    if options.report.is_file():
        previous=json.loads(options.report.read_text())
        history=previous.pop("previousAttempts",[])
        report["previousAttempts"]=[*history,previous]
    options.report.parent.mkdir(parents=True,exist_ok=True)
    options.report.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"passed":report["passed"],"report":str(options.report.resolve())},ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__=="__main__":
    sys.exit(main())
