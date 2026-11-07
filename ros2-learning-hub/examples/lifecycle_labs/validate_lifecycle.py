#!/usr/bin/env python3
"""真实rclcpp_lifecycle假资源验收；--help先用标准库，不需要ROS。

在教材根目录构建并source后：
  LIFECYCLE_LABS_INSTALL_PREFIX=/tmp/ros2-lifecycle-labs/install \
    timeout --signal=INT --kill-after=10s 180s /usr/bin/python3 \
    examples/lifecycle_labs/validate_lifecycle.py --report /tmp/lifecycle-local-result.json

输入：标准生命周期服务、有限STRING故障参数与软件假资源；无硬件/仿真。
输出：ChangeState响应、GetState、回调返回/异常、资源快照与两条话题的有限窗口。
普通计数与LifecyclePublisher使用同一序号，按窗口开始snapshot边界过滤旧DDS消息。
每例新worker进程组，父进程另设总期限；软服务期限不能抢占长原生调用。
清理只处理保存的自有PID/组；收到组SIGINT后先等孩子结束，不重复发送SIGINT。
默认报告在/tmp；维护者须显式指定教材绑定报告，避免读者覆盖已审核证据。
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

HERE=Path(__file__).resolve().parent
HUB=HERE.parents[1]
MARKER="LIFECYCLE_DRIVER_RESULT="
EVENT="LIFECYCLE_LAB_EVENT "
PLANS={
 "normal_roundtrip":{},
 "configure_failure_retry":{},
 "activate_failure_retry":{"activate_fault":"failure_once"},
 "configure_error_recover":{"configure_fault":"error_once","error_result":"success"},
 "configure_exception_recover":{"configure_fault":"throw_once","error_result":"success"},
 "configure_error_handler_failure":{"configure_fault":"error_once","error_result":"failure"},
 "configure_error_handler_error":{"configure_fault":"error_once","error_result":"error"},
 "configure_and_handler_exception":{"configure_fault":"throw_once","error_result":"throw"},
 "activate_error_recover":{"activate_fault":"error_once","error_result":"success"},
 "deactivate_error_recover":{"deactivate_fault":"error_once","error_result":"success"},
}


def require(condition,message):
    if not condition:raise AssertionError(message)


def arguments():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--install-prefix",type=Path,default=Path(os.environ.get("LIFECYCLE_LABS_INSTALL_PREFIX",HERE/"install")))
    parser.add_argument("--build-root",type=Path)
    parser.add_argument("--domain-id",type=int,default=229)
    parser.add_argument("--window-s",type=float,default=0.3,help="每个消息窗口经过秒数，至少3个50ms周期")
    parser.add_argument("--timeout-s",type=float,default=4.0,help="服务/发现软期限，秒")
    parser.add_argument("--worker-timeout-s",type=float,default=25.0)
    parser.add_argument("--case",choices=("all",*PLANS),default="all")
    parser.add_argument("--report",type=Path,default=Path('/tmp/lifecycle-local-result.json'))
    parser.add_argument("--worker",choices=PLANS,help=argparse.SUPPRESS)
    options=parser.parse_args()
    for value in (options.window_s,options.timeout_s,options.worker_timeout_s):
        if not math.isfinite(value) or value<=0:parser.error("所有时间必须为有限正秒数")
    if not 0<=options.domain_id<=232:parser.error("domain-id须位于0..232")
    if not 0.15<=options.window_s<=1.0:parser.error("window-s须在[0.15,1.0]内")
    if options.worker_timeout_s<max(4*options.timeout_s+3,8*options.window_s+5):
        parser.error("worker期限须覆盖发现/状态/观察与清理预算")
    options.install_prefix=options.install_prefix.resolve()
    return options


def environment(options):
    env=dict(os.environ);env.pop("ROS_LOCALHOST_ONLY",None);env.pop("ROS_STATIC_PEERS",None)
    env.update(ROS_DOMAIN_ID=str(options.domain_id),ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
               RMW_IMPLEMENTATION="rmw_fastrtps_cpp",PYTHONUNBUFFERED="1",PYTHONDONTWRITEBYTECODE="1")
    return env


class NativeProcess:
    def __init__(self,command,directory):
        self.command=command;self.path=Path(directory)/"native.log";self.stream=self.path.open("w")
        # 继承worker的进程组，父driver超时可以处理整个自有组。
        self.process=subprocess.Popen(command,stdout=self.stream,stderr=self.stream,env=dict(os.environ))

    def text(self):return self.path.read_text(errors="replace")

    def events(self):
        return [json.loads(line.split(EVENT,1)[1]) for line in self.text().splitlines() if EVENT in line]

    def close(self,group_already_signaled=False):
        sent=[];p=self.process
        if p.poll() is None and group_already_signaled:
            # 组SIGINT已覆盖C++孩子；先等其正常收尾，不能再盲发第二次SIGINT。
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:pass
        if p.poll() is None and not group_already_signaled:
            try:p.send_signal(signal.SIGINT);sent.append("SIGINT")
            except ProcessLookupError:pass
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:pass
        if p.poll() is None:
            try:p.kill();sent.append("SIGKILL")
            except ProcessLookupError:pass
            p.wait(timeout=3)
        result={"command":self.command,"pid":p.pid,"exitCode":p.returncode,
                "groupAlreadySignaled":group_already_signaled,"signalsSentByWorker":sent,
                "log":self.text(),"events":self.events()}
        self.stream.close();return result


class Probe:
    def __init__(self,options,node_name,namespace):
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.signals import SignalHandlerOptions
        from std_msgs.msg import UInt64
        from lifecycle_msgs.msg import TransitionEvent
        self.rclpy=rclpy;self.options=options;self.target=node_name
        self.context=Context()
        # 自建Context默认就不安装ROS信号处理器，显式NO写清所有权：Python
        # KeyboardInterrupt由worker捕获；C++孩子仍会收到同组SIGINT并自行收尾。
        rclpy.init(args=[],context=self.context,signal_handler_options=SignalHandlerOptions.NO)
        self.node=Node("lifecycle_probe",namespace=namespace,context=self.context,enable_rosout=False)
        self.executor=SingleThreadedExecutor(context=self.context);self.executor.add_node(self.node)
        self.clients={};self.ordinary=[];self.managed=[];self.transitions=[];self.subscriptions=[]
        for label,store in [("ordinary_ticks",self.ordinary),("managed_ticks",self.managed)]:
            self.subscriptions.append(self.node.create_subscription(UInt64,node_name+"/"+label,
                lambda msg,dest=store:dest.append({"sequence":msg.data,"receivedMonotonicS":time.monotonic()}),10))
        def transition(message):
            self.transitions.append({"transitionId":message.transition.id,"label":message.transition.label,
                "from":message.start_state.id,"to":message.goal_state.id,
                "receivedMonotonicS":time.monotonic()})
        self.subscriptions.append(self.node.create_subscription(TransitionEvent,node_name+"/transition_event",transition,100))

    def until(self,predicate,message,timeout=None):
        end=time.monotonic()+(self.options.timeout_s if timeout is None else timeout)
        while not predicate() and time.monotonic()<end:
            self.executor.spin_once(timeout_sec=min(0.02,max(0,end-time.monotonic())))
        require(predicate(),message)

    def call(self,kind,suffix,request):
        key=(kind,suffix)
        if key not in self.clients:self.clients[key]=self.node.create_client(kind,self.target+"/"+suffix)
        client=self.clients[key]
        require(client.wait_for_service(timeout_sec=self.options.timeout_s),"服务未发现："+suffix)
        future=client.call_async(request);self.until(future.done,"响应软期限到达："+suffix)
        require(future.exception() is None,"服务异常："+str(future.exception()))
        return future.result()

    def snapshot(self):
        from std_srvs.srv import Trigger
        result=self.call(Trigger,"snapshot",Trigger.Request());require(result.success,"snapshot失败")
        value=json.loads(result.message)
        require(value["allocated"]-value["released"]==value["resource_live"],"资源账本不平")
        return value

    def state(self):
        from lifecycle_msgs.srv import GetState
        value=self.call(GetState,"get_state",GetState.Request()).current_state
        return {"id":value.id,"label":value.label}

    def graph(self,suffix="get_transition_graph"):
        from lifecycle_msgs.srv import GetAvailableTransitions
        return [{"id":t.transition.id,"label":t.transition.label,"from":t.start_state.id,"to":t.goal_state.id}
            for t in self.call(GetAvailableTransitions,suffix,GetAvailableTransitions.Request()).available_transitions]

    def set_mode(self,name,value):
        from rcl_interfaces.srv import SetParameters
        from rclpy.parameter import Parameter
        response=self.call(SetParameters,"set_parameters",SetParameters.Request(
            parameters=[Parameter(name,value=value).to_parameter_msg()])).results[0]
        require(response.successful,"故障模式参数设置失败："+response.reason)

    def change(self,label,expected_state,expected_success,records):
        from lifecycle_msgs.srv import ChangeState
        from lifecycle_msgs.msg import Transition
        before_state=self.state();before=self.snapshot();available=self.graph("get_available_transitions")
        began=time.monotonic()
        # label优先于id；非法label在服务入口明确返回false，不碰旧实现的无效numeric分支。
        response=self.call(ChangeState,"change_state",ChangeState.Request(transition=Transition(label=label)))
        after_state=self.state();after=self.snapshot()
        result={"requestLabel":label,"requestId":0,"responseSuccess":response.success,
            "beforeState":before_state,"afterState":after_state,"before":before,"after":after,
            "availableBefore":available,"elapsedS":time.monotonic()-began}
        records.append(result)
        require(response.success==expected_success,f"{label}服务success不符：{result}")
        require(after_state["id"]==expected_state and after["state_id"]==expected_state,
                f"{label}最终状态不符：{result}")
        return result

    def window(self,label,managed_expected,records):
        # 两个DDS发布端均已发现/匹配，负例不能用“还没发现订阅”冒充门控。
        self.until(lambda:(lambda s:s["ordinary_subscribers"]>=1 and s["managed_subscribers"]>=1)(self.snapshot()),
                   "两条诊断发布端尚未匹配订阅")
        before=self.snapshot();boundary=before["timer_ticks"];began=time.monotonic();end=began+self.options.window_s
        while time.monotonic()<end:
            self.executor.spin_once(timeout_sec=min(0.02,max(0,end-time.monotonic())))
        ended=time.monotonic();elapsed=ended-began;after=self.snapshot()
        # 同时限定接收经过时间与源序号：窗口后的RPC推进可能又处理一些消息，
        # 它们保留在原始记录里，但不混入本窗口的消息计数。
        ordinary=[m for m in self.ordinary if m["sequence"]>boundary and began<=m["receivedMonotonicS"]<=ended]
        managed=[m for m in self.managed if m["sequence"]>boundary and began<=m["receivedMonotonicS"]<=ended]
        result={"label":label,"requestedWindowS":self.options.window_s,"actualElapsedS":elapsed,
            "startMonotonicS":began,"endMonotonicS":ended,
            "boundarySequence":boundary,"before":before,"after":after,
            "timerTickDelta":after["timer_ticks"]-before["timer_ticks"],
            "publishAttemptDelta":after["managed_attempts"]-before["managed_attempts"],
            "ordinaryNewMessages":ordinary,"managedNewMessages":managed,
            "ordinaryCount":len(ordinary),"managedCount":len(managed),"managedExpected":managed_expected}
        records.append(result)
        require(result["timerTickDelta"]>=1 and ordinary,"普通timer/普通话题在窗口内未推进")
        require(result["publishAttemptDelta"]>=1,"没有实际尝试生命周期publish，负例无效")
        require(after["publisher_active"]==managed_expected,"发布者激活标志与预期不符")
        require(bool(managed)==managed_expected,"生命周期新消息门控不符："+str(result))
        if not managed_expected:require(after["resource_work"]==before["resource_work"],"停用资源仍在做业务工作")
        return result

    def close(self):
        self.executor.remove_node(self.node);stopped=self.executor.shutdown(timeout_sec=1)
        self.node.destroy_node()
        if self.context.ok():self.rclpy.shutdown(context=self.context)
        return {"executorStopped":bool(stopped),"contextOkAfterCleanup":self.context.ok()}


def exercise(options,case,probe,native,record):
    changes=[];windows=[];record.update(changes=changes,windows=windows)
    probe.until(lambda:probe.state()["id"]==1,"节点初态不是unconfigured")
    graph=probe.graph();record["runtimeTransitionGraph"]=graph
    error_edges={item["id"]:item for item in graph if item["id"] in [60,61,62]}
    require({i:error_edges[i]["to"] for i in [60,61,62]}=={60:1,61:4,62:4},"运行SDK on_error图映射不符")
    require(all(e["from"]==15 for e in error_edges.values()),"on_error边起点应为errorprocessing")
    record["errorHandlerGraphEdges"]=list(error_edges.values())

    def change(label,state,success=True):return probe.change(label,state,success,changes)
    def window(label,active=False):return probe.window(label,active,windows)
    def released():
        s=probe.snapshot();require(s["resource_live"]==0 and s["resource_id"]==0 and s["pending_id"]==0,"资源未完全释放")
        require(not s["resource_active"] and not s["publisher_active"],"资源或发布者仍激活")
        return s
    def finish_from_inactive():
        change("cleanup",1);released();change("shutdown",4);released()
    def recovered_round():
        change("configure",2);change("activate",3);window("recovered_active",True)
        change("deactivate",2);finish_from_inactive()

    if case=="normal_roundtrip":
        initial=probe.snapshot();illegal=change("activate",1,False)
        require(illegal["after"]["activate_calls"]==initial["activate_calls"],"非法activate竟调用了回调")
        window("unconfigured")
        change("configure",2);configured=probe.snapshot()
        require(configured["resource_live"]==1 and configured["committed_version"]==1,"configure未提交完整资源")
        window("inactive_after_configure")
        change("activate",3);window("active",True)
        change("deactivate",2);window("inactive_after_deactivate")
        change("cleanup",1);released();window("unconfigured_after_cleanup")
        change("configure",2);require(probe.snapshot()["committed_version"]==2,"cleanup后未能重配")
        change("activate",3);change("deactivate",2);change("cleanup",1);released()
        change("shutdown",4);released();window("finalized_diagnostic_still_runs")
        last=change("configure",4,False)
        require(last["after"]["configure_calls"]==last["before"]["configure_calls"],"finalized竟再次configure")
        require(probe.graph("get_available_transitions")==[],"finalized仍广告转换")
        record["focus"]={"originalCallback":"SUCCESS roundtrip","responseSuccess":True,"stateAfter":4,
                         "resourceLiveAfter":0,"sameInstanceReconfigured":True,"finalizedConfigureRejected":True}
    elif case=="configure_failure_retry":
        change("configure",2);change("cleanup",1);old=probe.snapshot()
        require(old["committed_version"]==1 and old["resource_live"]==0,"没有建立旧配置快照")
        probe.set_mode("configure_fault","failure_once")
        failure=change("configure",1,False);after=failure["after"]
        require(after["committed_version"]==old["committed_version"] and after["resource_live"]==0,"FAILURE未保留旧配置/释放候选")
        require(after["allocated"]==old["allocated"]+1 and after["released"]==old["released"]+1,"部分资源未成对释放")
        require(after["error_calls"]==0,"预期FAILURE不应进入on_error")
        retry=change("configure",2)
        require(retry["after"]["committed_version"]==2,"FAILURE后同实例重试失败")
        window("retry_inactive");finish_from_inactive()
        record["focus"]={"originalCallback":"configure FAILURE","responseSuccess":False,"stateAfter":1,
            "errorHandler":"not called","resourceLiveAfter":0,"oldVersionPreserved":1,"retryVersion":2}
    elif case=="activate_failure_retry":
        change("configure",2);before=probe.snapshot();failure=change("activate",2,False)
        require(failure["after"]["resource_id"]==before["resource_id"] and failure["after"]["error_calls"]==0,"activate FAILURE不应换资源或调用on_error")
        window("activation_failure_inactive");change("activate",3);window("activation_retry_active",True)
        change("deactivate",2);finish_from_inactive()
        record["focus"]={"originalCallback":"activate FAILURE","responseSuccess":False,"stateAfter":2,
            "errorHandler":"not called","resourceLiveAfter":1,"resourcePreserved":True}
    else:
        plan=PLANS[case];stage=next(k.replace("_fault","") for k in plan if k.endswith("_fault"))
        if stage in ["activate","deactivate"]:change("configure",2)
        if stage=="deactivate":change("activate",3);window("active_before_deactivate_error",True)
        terminal=plan["error_result"]!="success"
        outcome=change(stage,4 if terminal else 1,False);after=released()
        require(after["error_calls"]==1,"ERROR处理不应缺失或递归重入on_error")
        event_list=native.events();entry=[e for e in event_list if e["event"]=="callback_enter" and e["callback"]=="error"]
        require(len(entry)==1 and entry[0]["snapshot"]["resource_live"]>=1,"on_error未真实接管部分/已提交资源")
        original="THROW_STD_RUNTIME_ERROR" if plan[stage+"_fault"]=="throw_once" else "ERROR"
        require(any(e["callback"]==stage and e["callback_result"]==original for e in event_list),"缺少原始回调ERROR/异常证据")
        handler="THROW_STD_RUNTIME_ERROR" if plan["error_result"]=="throw" else plan["error_result"].upper()
        require(any(e["callback"]=="error" and e["callback_result"]==handler for e in event_list),"缺少on_error返回/异常证据")
        window("post_error_finalized" if terminal else "post_error_unconfigured")
        record["focus"]={"originalCallback":stage+" "+original,"responseSuccess":outcome["responseSuccess"],
            "stateAfter":outcome["afterState"]["id"],"errorHandler":handler,"resourceLiveAfter":after["resource_live"],
            "onErrorCalls":1,"resourceBeforeHandler":entry[0]["snapshot"]}
        if terminal:
            denied=change("configure",4,False)
            require(denied["after"]["configure_calls"]==denied["before"]["configure_calls"],"错误finalized仍执行configure")
        else:recovered_round()
    record["finalSnapshot"]=probe.snapshot()
    require(record["finalSnapshot"]["resource_live"]==0,"场景结束时假资源未释放")
    record["ordinaryMessages"]=probe.ordinary;record["managedMessages"]=probe.managed
    record["transitionEvents"]=probe.transitions


def versions():
    from ament_index_python.packages import get_package_share_directory
    result={"python":sys.version,"pythonExecutable":sys.executable,"platform":platform.platform(),
            "rosDistro":os.environ.get("ROS_DISTRO"),"rclpy":importlib.metadata.version("rclpy"),"packages":{}}
    for name in ["runtime_lifecycle_lab","rclcpp_lifecycle","lifecycle_msgs","rcl_lifecycle","rclcpp","rmw_fastrtps_cpp"]:
        result["packages"][name]=ET.parse(Path(get_package_share_directory(name))/"package.xml").getroot().findtext("version")
    return result


def worker(options):
    record={"case":options.worker,"passed":False,"faultParameters":PLANS[options.worker]};began=time.monotonic()
    with tempfile.TemporaryDirectory(prefix="ros2-lifecycle-lab-") as directory:
        env=environment(options);os.environ.pop("ROS_LOCALHOST_ONLY",None);os.environ.pop("ROS_STATIC_PEERS",None)
        os.environ.update(env);os.environ["ROS_LOG_DIR"]=str(Path(directory)/"ros-logs")
        namespace=f"/lifecycle_lab/p{os.getpid()}/{options.worker}";fqn=namespace+"/fake_resource"
        probe=None;native=None;interrupted=False
        try:
            record["versions"]=versions();record["node"]=fqn
            probe=Probe(options,fqn,namespace)
            executable=options.install_prefix/"lib/runtime_lifecycle_lab/fake_resource_node"
            require(executable.is_file(),"请先构建安装原创包："+str(executable))
            command=[str(executable),"--ros-args","-r",f"__ns:={namespace}"]
            for key,value in PLANS[options.worker].items():command.extend(["-p",f"{key}:={value}"])
            native=NativeProcess(command,directory);exercise(options,options.worker,probe,native,record)
            record["passed"]=True
        except BaseException as exc:
            interrupted=isinstance(exc,KeyboardInterrupt)
            record["workerInterrupted"]=interrupted
            record["error"]=traceback.format_exc()
        finally:
            # KeyboardInterrupt并不要求context.ok变false；不能因此误补第二次SIGINT。
            signaled=interrupted or (probe is not None and not probe.context.ok())
            if native is not None:record["nativeProcess"]=native.close(group_already_signaled=signaled)
            if probe is not None:record["probeCleanup"]=probe.close()
            if native is not None and record["nativeProcess"]["exitCode"]!=0:record["passed"]=False
    record["durationS"]=time.monotonic()-began
    print(MARKER+json.dumps(record,ensure_ascii=False,allow_nan=False),flush=True)
    return 0 if record["passed"] else 1


def run_worker(options,case):
    command=["/usr/bin/python3",str(Path(__file__).resolve()),"--worker",case,
        "--install-prefix",str(options.install_prefix),"--domain-id",str(options.domain_id),
        "--window-s",str(options.window_s),"--timeout-s",str(options.timeout_s),"--worker-timeout-s",str(options.worker_timeout_s)]
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        env=environment(options),start_new_session=True);started=time.monotonic();error=None;interrupted=False;fatal=False
    try:stdout,stderr=process.communicate(timeout=options.worker_timeout_s)
    except BaseException as exc:
        error=repr(exc);interrupted=isinstance(exc,KeyboardInterrupt);fatal=not isinstance(exc,subprocess.TimeoutExpired)
        try:os.killpg(process.pid,signal.SIGINT)
        except ProcessLookupError:pass
        try:stdout,stderr=process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            stdout,stderr=process.communicate(timeout=3)
    lines=[line[len(MARKER):] for line in stdout.splitlines() if line.startswith(MARKER)]
    result=json.loads(lines[-1]) if lines else None
    return {"case":case,"command":command,"exitCode":process.returncode,"outerError":error,
        "interrupted":interrupted,"fatalOuterError":fatal,"stdout":stdout,"stderr":stderr,"result":result,
        "workerDeadlineS":options.worker_timeout_s,"durationS":time.monotonic()-started,
        "passed":process.returncode==0 and error is None and result is not None and result["passed"]}


def tables(results):
    rows=[];gating=[]
    labels={1:"unconfigured",2:"inactive",3:"active",4:"finalized"}
    for item in results:
        if not item["passed"]:continue
        value=item["result"];focus=value["focus"]
        rows.append([item["case"],focus["originalCallback"],focus["responseSuccess"],
            labels[focus["stateAfter"]],focus.get("errorHandler","not called"),focus["resourceLiveAfter"]])
        if item["case"]=="normal_roundtrip":
            # 主路径的合法转换与两个非法请求分行，避免把整个场景混称success=true。
            rows[-1][0]="normal_roundtrip：合法往返/重配"
            for title,transition in [("未配置时activate",value["changes"][0]),
                                     ("finalized后configure",value["changes"][-1])]:
                rows.append([title,"callback not invoked",transition["responseSuccess"],
                    labels[transition["afterState"]["id"]],"not called",transition["after"]["resource_live"]])
            for window in value["windows"]:
                gating.append([window["label"],labels[window["after"]["state_id"]],window["timerTickDelta"],
                    window["publishAttemptDelta"],window["ordinaryCount"],window["managedCount"],window["after"]["resource_live"]])
    return [{"id":"transitions","title":"回调返回、服务响应、最终状态与资源","columns":["场景","原回调","ChangeState.success","落点","on_error","当时存活资源"],
             "rows":rows,"caption":"每行聚焦故障发生后的实际落点；恢复场景随后另做重配与shutdown。原ERROR经on_error SUCCESS恢复，也不使原转换响应变true。"},
            {"id":"gating","title":"普通timer和生命周期发布者分别验收","columns":["窗口","ROS状态","timer新增tick","managed尝试","普通新增消息","managed新增消息","存活资源"],
             "rows":gating,"caption":"同一序号与接收经过时间共同限定窗口，过滤旧DDS消息；发布端先匹配订阅。窗口长度记录在输入和原始数据中，不是精确频率或实时保证；finalized诊断timer继续是本例明确选择。"}]


def main():
    options=arguments()
    if options.worker:return worker(options)
    def stop_signal(signum,frame):raise KeyboardInterrupt(f"parent signal {signum}")
    signal.signal(signal.SIGTERM,stop_signal)
    started=time.monotonic();results=[]
    for case in (PLANS if options.case=="all" else [options.case]):
        result=run_worker(options,case);results.append(result)
        print(case+": "+("PASS" if result["passed"] else "FAIL"),flush=True)
        if not result["passed"] and result["result"]:print(result["result"].get("error",""),file=sys.stderr)
        if result["interrupted"] or result["fatalOuterError"]:break
    source_hashes=[{"path":str(p.relative_to(HUB)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(HERE.rglob("*")) if p.is_file() and (p.suffix in [".cpp",".py",".xml"] or p.name=="CMakeLists.txt")]
    report={"schemaVersion":1,"checkedAt":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "passed":all(r["passed"] for r in results),"interrupted":any(r["interrupted"] for r in results),
        "durationS":time.monotonic()-started,"sourceHashes":source_hashes,"results":results,
        "parameters":{key:str(value) if isinstance(value,Path) else value for key,value in vars(options).items() if key not in ["worker","report"]},
        "environment":{"ROS_DOMAIN_ID":str(options.domain_id),"ROS_AUTOMATIC_DISCOVERY_RANGE":"LOCALHOST","RMW_IMPLEMENTATION":"rmw_fastrtps_cpp","ROS_LOCALHOST_ONLY":"unset","ROS_STATIC_PEERS":"unset"},
        "teachingTables":tables(results),
        "teachingValidation":"真实原创rclcpp_lifecycle软件假资源实验；分别检查生命周期响应/状态、回调事件、资源账本、普通timer和LifecyclePublisher消息，未连接硬件或仿真。",
        "teachingCommand":"""# 在ros2-learning-hub目录执行；报告另存/tmp，不覆盖教材绑定证据。
source /opt/ros/jazzy/setup.bash
colcon --log-base /tmp/ros2-lifecycle-labs/log build --base-paths examples/lifecycle_labs/runtime_lifecycle_lab --build-base /tmp/ros2-lifecycle-labs/build --install-base /tmp/ros2-lifecycle-labs/install --merge-install --symlink-install
source /tmp/ros2-lifecycle-labs/install/setup.bash
LIFECYCLE_LABS_INSTALL_PREFIX=/tmp/ros2-lifecycle-labs/install timeout --signal=INT --kill-after=10s 180s /usr/bin/python3 examples/lifecycle_labs/validate_lifecycle.py --build-root /tmp/ros2-lifecycle-labs --report /tmp/lifecycle-local-result.json""",
        "teachingCommandNote":"源码路径相对教材根目录；构建和新报告放/tmp。服务期限依赖执行器推进，不能抢占长原生回调；worker与外层timeout另保护退出。普通诊断timer全状态持续是本例合同，不代表业务资源应继续运行。",
        "limits":["本例仅内存假资源和std::runtime_error注入，不证明设备打开/线程停止/物理停车。",
            "没有覆盖cleanup/deactivate/shutdown所有FAILURE/ERROR分支、任意非std异常、bad_alloc或进程崩溃恢复。",
            "窗口只证明所列匹配条件和序号范围中的新增消息；不保证精确频率或硬实时期限。",
            "资源释放由本例回调/析构显式实现，生命周期状态机不自动替应用回滚外部资源。",
            "shutdown到finalized后本例进程及普通诊断接口仍在；同实例不能重新configure，重建实例另属进程管理。"]}
    if options.build_root:
        logs=options.build_root/"log/latest_build/runtime_lifecycle_lab"
        report["buildEvidence"]={"root":str(options.build_root),"logs":{p.name:p.read_text(errors="replace") for p in logs.glob("*.log") if p.name in ["command.log","stdout_stderr.log","stderr.log"]}}
    if options.report.is_file():
        old=json.loads(options.report.read_text());history=old.pop("previousAttempts",[]);report["previousAttempts"]=[*history,old]
    options.report.parent.mkdir(parents=True,exist_ok=True)
    options.report.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"passed":report["passed"],"report":str(options.report.resolve())},ensure_ascii=False))
    return 130 if report["interrupted"] else (0 if report["passed"] else 1)


if __name__=="__main__":sys.exit(main())
