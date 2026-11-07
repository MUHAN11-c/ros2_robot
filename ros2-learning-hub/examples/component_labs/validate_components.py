#!/usr/bin/env python3
"""真实Jazzy组件配置/容器调度验收；--help不依赖ROS。

先构建runtime_lab_components并source安装前缀，再运行：
  COMPONENT_LABS_INSTALL_PREFIX=/tmp/ros2-component-labs/install \
    timeout --signal=INT --kill-after=10s 180s /usr/bin/python3 validate_components.py \
      --report /tmp/component-labs-local-result.json

输入：原创Config组件、私有/tmp软件门闩和官方三个容器；不接设备或仿真。
输出：参数/加载响应、Float64速度(m/s)、PID/TID/monotonic纳秒/span及JSON证据。
每例独立worker进程组；服务等待是monotonic软期限，父进程另有总期限保护。
清理只使用本例保存的PID/进程组；先prepare_unload取消组件timer再按实际ID卸载。
官方容器管理参数服务默认关闭；readonly通过显式开启服务的observable_manager
验收，不把等待服务超时当拒绝证据。其他NodeOptions默认值不随extra任意键设置。
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
MARKER="COMPONENT_DRIVER_RESULT="
EVENT="COMPONENT_LAB_EVENT "
CASES=("standalone_config","component_parameters","container_single","container_mt","container_isolated")


def require(condition,message):
    if not condition:
        raise AssertionError(message)


def arguments():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--install-prefix",type=Path,default=Path(os.environ.get("COMPONENT_LABS_INSTALL_PREFIX",HERE/"install")))
    parser.add_argument("--build-root",type=Path,help="可选/tmp构建根目录，仅用于读取本轮colcon日志")
    parser.add_argument("--domain-id",type=int,default=225)
    parser.add_argument("--hold-s",type=float,default=0.35,help="slow开始后保持的软件门闩窗口，秒")
    parser.add_argument("--timeout-s",type=float,default=5.0,help="服务/消息/事件软等待，秒")
    parser.add_argument("--worker-timeout-s",type=float,default=30.0,help="父进程包住每例的期限")
    parser.add_argument("--case",choices=("all",*CASES),default="all")
    parser.add_argument("--report",type=Path,default=HUB/"validation-evidence/component-labs-current-validation.json")
    parser.add_argument("--worker",choices=CASES,help=argparse.SUPPRESS)
    result=parser.parse_args()
    for value in (result.hold_s,result.timeout_s,result.worker_timeout_s):
        if not math.isfinite(value) or value<=0:
            parser.error("所有时间须为有限正秒数")
    if not 0<=result.domain_id<=232 or not 0.15<=result.hold_s<=1.0:
        parser.error("域须位于0..232，hold-s须位于[0.15,1.0]，低于2秒回调保护上限")
    if result.worker_timeout_s<4*result.timeout_s+5:
        parser.error("worker期限至少覆盖4倍软等待及5秒清理余量")
    result.install_prefix=result.install_prefix.resolve()
    return result


def environment(options):
    env=dict(os.environ)
    env.pop("ROS_LOCALHOST_ONLY",None)
    env.pop("ROS_STATIC_PEERS",None)
    env.update(ROS_DOMAIN_ID=str(options.domain_id),ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
               RMW_IMPLEMENTATION="rmw_fastrtps_cpp",PYTHONUNBUFFERED="1",PYTHONDONTWRITEBYTECODE="1")
    return env


class Processes:
    """孩子继承worker进程组；父级超时时能整体清理，正常只给自有PID发信号。"""
    def __init__(self,directory):
        self.directory=Path(directory)
        self.items=[]

    def start(self,command,label):
        path=self.directory/f"{len(self.items):02d}-{label}.log"
        stream=path.open("w")
        process=subprocess.Popen(command,stdout=stream,stderr=stream,env=dict(os.environ))
        item={"command":command,"label":label,"process":process,"stream":stream,"path":path}
        self.items.append(item)
        return item

    @staticmethod
    def text(item):
        return item["path"].read_text(errors="replace")

    def events(self,item):
        parsed=[]
        for line in self.text(item).splitlines():
            if EVENT in line:
                parsed.append(json.loads(line.split(EVENT,1)[1]))
        return parsed

    def stop(self,item):
        process=item["process"]
        if process.poll() is None:
            try:process.send_signal(signal.SIGINT)
            except ProcessLookupError:pass
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:process.kill()
                except ProcessLookupError:pass
                process.wait(timeout=3)

    def close(self):
        records=[]
        for item in reversed(self.items):
            error=None
            try:
                self.stop(item)
            except BaseException:
                error=traceback.format_exc()
            records.append({"label":item["label"],"command":item["command"],
                "pid":item["process"].pid,"exitCode":item["process"].poll(),
                "cleanupError":error,"log":self.text(item),"events":self.events(item)})
            item["stream"].close()
        return list(reversed(records))


class Probe:
    """同Context执行器有界推进；所有订阅回调只是追加小数值，不阻塞。"""
    def __init__(self,namespace,options):
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        self.rclpy=rclpy
        self.options=options
        self.context=Context()
        rclpy.init(args=[],context=self.context)
        self.node=Node("component_probe",namespace=namespace,context=self.context,enable_rosout=False)
        self.executor=SingleThreadedExecutor(context=self.context)
        self.executor.add_node(self.node)
        self.clients={}
        self.samples={}
        self.subscriptions=[]

    def until(self,predicate,message,timeout=None):
        end=time.monotonic()+(self.options.timeout_s if timeout is None else timeout)
        while not predicate() and time.monotonic()<end:
            self.executor.spin_once(timeout_sec=min(0.02,max(0,end-time.monotonic())))
        require(predicate(),message)

    def call(self,kind,name,request):
        key=(kind,name)
        if key not in self.clients:
            self.clients[key]=self.node.create_client(kind,name)
        client=self.clients[key]
        require(client.wait_for_service(timeout_sec=self.options.timeout_s),f"服务未发现：{name}")
        future=client.call_async(request)
        self.until(future.done,f"服务响应软期限到达：{name}")
        require(future.exception() is None,f"服务异常：{future.exception()}")
        return future.result()

    def get(self,node,names):
        from rcl_interfaces.srv import GetParameters
        return self.call(GetParameters,node+"/get_parameters",GetParameters.Request(names=names)).values

    def set(self,node,name,value):
        from rcl_interfaces.srv import SetParameters
        from rclpy.parameter import Parameter
        request=SetParameters.Request(parameters=[Parameter(name,value=value).to_parameter_msg()])
        return self.call(SetParameters,node+"/set_parameters",request).results[0]

    def output(self,node,expected):
        from std_msgs.msg import Float64
        if node not in self.samples:
            self.samples[node]=[]
            self.subscriptions.append(self.node.create_subscription(Float64,node+"/configured_velocity",
                lambda message,key=node:self.samples[key].append(message.data),10))
        self.samples[node].clear()
        self.until(lambda:any(math.isclose(v,expected,abs_tol=1e-12) for v in self.samples[node]),
                   f"{node}未观察到{expected}m/s")
        require(all(math.isfinite(v) for v in self.samples[node]),"发布结果含非有限数")
        return list(self.samples[node])

    def close(self):
        self.executor.remove_node(self.node)
        stopped=self.executor.shutdown(timeout_sec=1)
        self.node.destroy_node()
        if self.context.ok():
            self.rclpy.shutdown(context=self.context)
        return {"executorStopped":bool(stopped),"contextOkAfterCleanup":self.context.ok()}


def binary(options,name):
    path=options.install_prefix/"lib/runtime_lab_components"/name
    require(path.is_file() and os.access(path,os.X_OK),f"尚未构建安装：{path}")
    return str(path)


def start_container(options,processes,namespace,executable,observable=False):
    from ament_index_python.packages import get_package_prefix
    path=(binary(options,"observable_manager") if observable else
          str(Path(get_package_prefix("rclcpp_components"))/"lib/rclcpp_components"/executable))
    command=[path,"--ros-args","-r","__node:=manager","-r",f"__ns:={namespace}"]
    if executable=="component_container_mt" or observable:
        command.extend(["-p","thread_num:=2"])
    if observable:
        command.extend(["-p","gain:=1.8"])
    return processes.start(command,"container"),namespace+"/manager"


def component_call(probe,manager,operation,request):
    from composition_interfaces.srv import LoadNode,ListNodes,UnloadNode
    kind={"load":LoadNode,"list":ListNodes,"unload":UnloadNode}[operation]
    return probe.call(kind,manager+"/_container/"+{"load":"load_node","list":"list_nodes","unload":"unload_node"}[operation],request)


def load(probe,manager,plugin,name,namespace,parameters=None,extras=None):
    from composition_interfaces.srv import LoadNode
    from rclpy.parameter import Parameter
    request=LoadNode.Request(package_name="runtime_lab_components",
        plugin_name="runtime_lab_components::"+plugin,node_name=name,node_namespace=namespace,
        parameters=[Parameter(key,value=value).to_parameter_msg() for key,value in (parameters or {}).items()],
        extra_arguments=[Parameter(key,value=value).to_parameter_msg() for key,value in (extras or {}).items()])
    return component_call(probe,manager,"load",request)


def listed(probe,manager):
    from composition_interfaces.srv import ListNodes
    response=component_call(probe,manager,"list",ListNodes.Request())
    require(len(response.full_node_names)==len(response.unique_ids),"ListNodes名称/ID长度不符")
    return dict(zip(response.full_node_names,response.unique_ids))


def unload(probe,manager,name,uid):
    from composition_interfaces.srv import UnloadNode
    from std_srvs.srv import Trigger
    # 先在组件自身互斥组内取消timer，避免把任意运行中卸载包装成安全保证。
    ready=probe.call(Trigger,name+"/prepare_unload",Trigger.Request())
    require(ready.success,"组件未进入可卸载教学状态")
    response=component_call(probe,manager,"unload",UnloadNode.Request(unique_id=uid))
    require(response.success,f"卸载实际ID={uid}失败：{response.error_message}")
    return {"node":name,"id":uid,"prepared":ready.success,"unloaded":response.success}


def standalone(options,processes,probe,namespace,record):
    node=namespace+"/standalone"
    child=processes.start([binary(options,"config_node"),"--ros-args","-r","__node:=standalone",
        "-r",f"__ns:={namespace}","-p","gain:=1.5"],"standalone")
    initial=probe.get(node,["gain"])[0]
    require(initial.type==3 and initial.double_value==1.5,"独立入口gain覆盖不符")
    samples=probe.output(node,0.3)
    changes=[]
    expected_gain=1.5
    for label,value,accepted in [("valid",1.2,True),("too-large",3.0,False),("negative",-0.1,False),
                                 ("NaN",math.nan,False),("positive-Inf",math.inf,False),
                                 ("negative-Inf",-math.inf,False),("integer",1,False),("string","bad",False),
                                 ("lower-bound",0.0,True),("upper-bound",2.0,True),("restore",1.2,True)]:
        outcome=probe.set(node,"gain",value)
        require(outcome.successful==accepted,f"动态{label}接纳结果不符：{outcome}")
        if accepted:expected_gain=value
        gain=probe.get(node,["gain"])[0].double_value
        require(gain==expected_gain and math.isfinite(gain),f"动态{label}改变了应保存的值：{gain}")
        observed=probe.output(node,0.2*expected_gain) if accepted else None
        changes.append({"input":label,"accepted":outcome.successful,"reason":outcome.reason,
                        "storedGain":gain,"observedAfterAccepted":observed})
    final=probe.output(node,0.24)
    record.update(node=node,pid=child["process"].pid,initialGain=1.5,initialOutputMps=0.3,
                  observedInitial=samples,dynamic=changes,observedAfterDynamic=final)


def parameter_components(options,processes,probe,namespace,record):
    from rcl_interfaces.srv import DescribeParameters
    child,manager=start_container(options,processes,namespace,"observable",observable=True)
    manager_values=probe.get(manager,["gain","thread_num"])
    require(manager_values[0].double_value==1.8 and manager_values[1].integer_value==2,"管理参数启动覆盖不符")
    descriptor=probe.call(DescribeParameters,manager+"/describe_parameters",DescribeParameters.Request(names=["thread_num"])).descriptors[0]
    require(descriptor.read_only,"thread_num描述符必须只读")
    rejected=probe.set(manager,"thread_num",1)  # 1在合法范围内，排除“越界”作为拒绝原因。
    require(not rejected.successful and probe.get(manager,["thread_num"])[0].integer_value==2,"只读thread_num未被拒绝或值改变")
    configs=[]
    ids={}
    def good(label,params,extras,gain,unknown=False):
        response=load(probe,manager,"ConfigComponent",label,namespace+"/nodes",params,extras)
        require(response.success,f"有效组件{label}加载失败：{response.error_message}")
        values=probe.get(response.full_node_name,["gain"])
        require(len(values)==1 and values[0].type==3 and values[0].double_value==gain,"组件生效gain不符")
        unknown_values=[]
        if unknown:
            from rcl_interfaces.srv import ListParameters
            # 严格GetParameters遇未声明名会捕获异常并给空values；不能从
            # get_parameter_or/allow_undeclared的fallback推导逐项NOT_SET。
            unknown_values=probe.get(response.full_node_name,["typo_gain"])
            require(len(unknown_values)==0,"本版C++未知参数Get应返回空values")
            listing=probe.call(ListParameters,response.full_node_name+"/list_parameters",
                ListParameters.Request(prefixes=[],depth=0))
            require("typo_gain" not in listing.result.names,"未知覆盖不应自动成为已声明参数")
            dynamic_unknown=probe.set(response.full_node_name,"typo_gain",1.1)
            require(not dynamic_unknown.successful,"未声明参数动态设置应拒绝")
        else:
            dynamic_unknown=None
        observed=probe.output(response.full_node_name,0.2*gain)
        ids[response.full_node_name]=response.unique_id
        configs.append({"label":label,"node":response.full_node_name,"id":response.unique_id,
            "parameters":params,"extraArguments":extras,"gain":gain,"outputMps":0.2*gain,
            "observed":observed,"unknownGetValuesCount":len(unknown_values) if unknown else None,
            "unknownGetRepresentation":"empty values; C++ undeclared exception caught by service" if unknown else None,
            "dynamicUnknownAccepted":None if dynamic_unknown is None else dynamic_unknown.successful,
            "dynamicUnknownReason":None if dynamic_unknown is None else dynamic_unknown.reason})
        return response.full_node_name
    default=good("default_config",{}, {},1.0)
    local=good("local_config",{"gain":1.5},{"use_intra_process_comms":True},1.5)
    good("forward_config",{}, {"forward_global_arguments":True},1.8)
    good("forward_local",{"gain":1.5},{"forward_global_arguments":True},1.5)
    good("typo_config",{"typo_gain":1.9},{},1.0,unknown=True)
    good("unknown_extra",{"typo_gain":1.9},{"automatically_declare_parameters_from_overrides":True,
         "allow_undeclared_parameters":True},1.0,unknown=True)
    changed=probe.set(manager,"gain",1.2)
    require(changed.successful,"管理节点自身gain修改失败")
    require(probe.get(default,["gain"])[0].double_value==1.0 and probe.get(local,["gain"])[0].double_value==1.5,
            "管理节点gain不应自动传播到已有组件")
    # 转发的是Context全局CLI参数，不是管理参数服务当前值1.2。
    good("forward_after_manager_change",{}, {"forward_global_arguments":True},1.8)
    invalid=[]
    for label,value in [("out_of_range",3.0),("wrong_type","bad"),("nonfinite",math.nan)]:
        response=load(probe,manager,"ConfigComponent",label,namespace+"/nodes",{"gain":value})
        require(not response.success and bool(response.error_message),f"非法{label}未产生明确加载失败")
        current=listed(probe,manager)
        require(current==ids and child["process"].poll() is None,"失败构造后管理节点或已有组件受影响")
        invalid.append({"input":label,"loadSuccess":response.success,"error":response.error_message,
                        "existingListUnchanged":True})
    wrong_extra=load(probe,manager,"ConfigComponent","wrong_extra_type",namespace+"/nodes",
                     extras={"forward_global_arguments":"bad"})
    require(not wrong_extra.success and "boolean" in wrong_extra.error_message,
            "已识别extra的错误类型必须被明确拒绝")
    require(listed(probe,manager)==ids and child["process"].poll() is None,"错误extra影响已有组件")
    invalid.append({"input":"wrong_extra_type","source":"extra_arguments",
        "loadSuccess":wrong_extra.success,"error":wrong_extra.error_message,"existingListUnchanged":True})
    events=processes.events(child)
    constructs={e["node"]:e for e in events if e["role"]=="config" and e["event"]=="constructed"}
    for entry in configs:
        options_event=constructs[entry["node"]]
        require(not options_event["allow_undeclared_parameters"] and not options_event["automatically_declare_parameters_from_overrides"],
                "标准extra不应启用任意NodeOptions setter")
        require(options_event["use_global_arguments"]==entry["extraArguments"].get("forward_global_arguments",False),"forward选项未生效")
        entry["actualNodeOptions"]=options_event
    removed=[unload(probe,manager,name,uid) for name,uid in ids.items()]
    require(listed(probe,manager)=={},"卸载后列表不为空")
    record.update(manager=manager,managerPid=child["process"].pid,managerStartupGain=1.8,
        managerGainAfterChange=1.2,managementParameterServicesExplicitlyEnabled=True,
        threadNum={"startup":2,"readOnly":descriptor.read_only,"attemptedValue":1,
            "dynamicAccepted":rejected.successful,"reason":rejected.reason,
            "range":[{"from":r.from_value,"to":r.to_value} for r in descriptor.integer_range]},
        configurations=configs,invalidConstruction=invalid,unload=removed,listEmptyAfterUnload=True)


def scheduling(options,processes,probe,namespace,case,directory,record):
    name={"container_single":"component_container","container_mt":"component_container_mt",
          "container_isolated":"component_container_isolated"}[case]
    child,manager=start_container(options,processes,namespace,name)
    control=Path(directory)/"gates";control.mkdir()
    heartbeat=load(probe,manager,"HeartbeatComponent","heartbeat",namespace+"/nodes",{"control_dir":str(control)})
    slow=load(probe,manager,"SlowComponent","slow",namespace+"/nodes",{"control_dir":str(control),"cap_s":2.0})
    require(heartbeat.success and slow.success,"调度组件加载失败")
    probe.until(lambda:any(e["event"]=="timer_ready" for e in processes.events(child)),"heartbeat未先证明timer可运行")
    # 观察实际管理服务图；源码明确默认关闭，不能把参数服务等待超时当只读拒绝。
    services=probe.node.get_service_names_and_types_by_node("manager",namespace)
    parameter_services=[s for s,_ in services if any(s.endswith("/"+suffix) for suffix in ["get_parameters","set_parameters","describe_parameters"])]
    require(not parameter_services,"当前官方默认管理参数服务与预期不符，需报告而非假定")
    (control/"start_slow").touch()
    probe.until(lambda:any(e["role"]=="slow" and e["event"]=="start" for e in processes.events(child)),"slow未进入真实回调")
    begin=time.monotonic()
    (control/"heartbeat_enabled").touch()
    deadline=begin+options.hold_s
    while time.monotonic()<deadline:
        probe.executor.spin_once(timeout_sec=min(0.02,max(0,deadline-time.monotonic())))
    hold_elapsed=time.monotonic()-begin
    held_events=processes.events(child)
    require(not any(e["role"]=="slow" and e["event"]=="end" for e in held_events),"slow提前由保护上限释放")
    held_heartbeats=[e for e in held_events if e["role"]=="heartbeat" and e["event"]=="start"]
    if case=="container_single":
        require(not held_heartbeats,"单线程slow窗口中不应执行heartbeat")
    else:
        require(bool(held_heartbeats),"mt/isolated在受控窗口未观察到heartbeat重叠")
    (control/"release_slow").touch()
    probe.until(lambda:any(e["role"]=="slow" and e["event"]=="end" for e in processes.events(child)),"slow释放后未结束")
    probe.until(lambda:any(e["role"]=="heartbeat" and e["event"]=="end" for e in processes.events(child)),"heartbeat释放后未运行")
    removed=[unload(probe,manager,r.full_node_name,r.unique_id) for r in [heartbeat,slow]]
    require(listed(probe,manager)=={},"调度组件卸载后列表不为空")
    events=processes.events(child)
    spans={}
    for e in events:
        if e["event"] in ["start","end"]:
            spans.setdefault(e["span"],{})[e["event"]]=e
    require(all(set(s)=={"start","end"} for s in spans.values()),"时间线span不成对")
    slow_span=next(s for s in spans.values() if s["start"]["role"]=="slow")
    require(slow_span["end"]["released_by_driver"],"slow不是由驱动释放")
    hb_spans=[s for s in spans.values() if s["start"]["role"]=="heartbeat"]
    overlap=[s for s in hb_spans if s["start"]["monotonic_ns"]<slow_span["end"]["monotonic_ns"] and
             s["end"]["monotonic_ns"]>slow_span["start"]["monotonic_ns"]]
    require((len(overlap)==0)==(case=="container_single"),"span交叠与调度配置不符")
    pid=child["process"].pid
    require(all(e["pid"]==pid for e in events),"组件不是同一实际容器PID")
    hb_threads=sorted({s["start"]["tid"] for s in hb_spans})
    slow_tid=slow_span["start"]["tid"]
    if case=="container_single":
        require(hb_threads==[slow_tid],"单线程组件callback线程应相同")
        first=hb_spans[0]["start"]
        require(first["expected_call_ns"]<slow_span["end"]["monotonic_ns"],"负例缺少已到期timer证据")
    if case=="container_isolated":
        require(len(hb_threads)==1 and hb_threads[0]!=slow_tid,"isolated默认每组件ST专属线程未观察到")
    ordering=[]
    for s in spans.values():ordering.extend([(s["start"]["monotonic_ns"],1),(s["end"]["monotonic_ns"],-1)])
    active=maximum=0
    for _,delta in sorted(ordering,key=lambda x:(x[0],x[1])):
        active+=delta;maximum=max(maximum,active)
    require(maximum==(1 if case=="container_single" else 2),"业务回调最大并发不符")
    record.update(executable=name,pid=pid,manager=manager,defaultManagementParameterServices=False,
        observedManagerServices=services,threadNumStartupArgument=2 if case=="container_mt" else None,
        holdWindowRequestedS=options.hold_s,holdWindowActualS=hold_elapsed,
        slowDurationS=(slow_span["end"]["monotonic_ns"]-slow_span["start"]["monotonic_ns"])/1e9,
        slowTid=slow_tid,heartbeatTids=hb_threads,heartbeatCount=len(hb_spans),
        heartbeatDuringSlow=len(overlap),maxConcurrency=maximum,rawEvents=events,
        spans=list(spans.values()),unload=removed,listEmptyAfterUnload=True)


def versions():
    from ament_index_python.packages import get_package_share_directory
    values={"python":sys.version,"pythonExecutable":sys.executable,"platform":platform.platform(),
        "rosDistro":os.environ.get("ROS_DISTRO"),"rclpy":importlib.metadata.version("rclpy"),"packages":{}}
    for name in ["runtime_lab_components","rclcpp","rclcpp_components","composition_interfaces","rmw_fastrtps_cpp"]:
        values["packages"][name]=ET.parse(Path(get_package_share_directory(name))/"package.xml").getroot().findtext("version")
    return values


def worker(options):
    record={"case":options.worker,"passed":False,"pid":os.getpid()}
    began=time.monotonic()
    with tempfile.TemporaryDirectory(prefix="ros2-component-lab-") as directory:
        env=environment(options)
        os.environ.pop("ROS_LOCALHOST_ONLY",None);os.environ.pop("ROS_STATIC_PEERS",None)
        os.environ.update(env);os.environ["ROS_LOG_DIR"]=str(Path(directory)/"ros-logs")
        processes=Processes(directory);probe=None
        namespace=f"/component_lab/p{os.getpid()}/{options.worker}"
        try:
            record["versions"]=versions()
            probe=Probe(namespace,options)
            measurements={}
            if options.worker=="standalone_config":standalone(options,processes,probe,namespace,measurements)
            elif options.worker=="component_parameters":parameter_components(options,processes,probe,namespace,measurements)
            else:scheduling(options,processes,probe,namespace,options.worker,directory,measurements)
            record["measurements"]=measurements
            record["passed"]=True
        except BaseException:
            record["error"]=traceback.format_exc()
        finally:
            record["processes"]=processes.close()
            if probe is not None:record["probeCleanup"]=probe.close()
            if any(p["cleanupError"] or p["exitCode"] is None for p in record["processes"]):record["passed"]=False
    record["durationS"]=time.monotonic()-began
    print(MARKER+json.dumps(record,ensure_ascii=False,allow_nan=False),flush=True)
    return 0 if record["passed"] else 1


def run_worker(options,case):
    command=["/usr/bin/python3",str(Path(__file__).resolve()),"--worker",case,
        "--install-prefix",str(options.install_prefix),"--domain-id",str(options.domain_id),
        "--hold-s",str(options.hold_s),"--timeout-s",str(options.timeout_s),
        "--worker-timeout-s",str(options.worker_timeout_s)]
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        env=environment(options),start_new_session=True)
    error=None;started=time.monotonic();interrupted=False;fatal=False
    try:
        stdout,stderr=p.communicate(timeout=options.worker_timeout_s)
    except BaseException as exc:
        # KeyboardInterrupt及其它异常都先清理本例新进程组，再交给main停止或报告；
        # 不能让已start_new_session的worker在父driver退出后留在后台。
        error=repr(exc)
        interrupted=isinstance(exc,KeyboardInterrupt)
        fatal=not isinstance(exc,subprocess.TimeoutExpired)
        try:os.killpg(p.pid,signal.SIGINT)
        except ProcessLookupError:pass
        try:stdout,stderr=p.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            stdout,stderr=p.communicate(timeout=3)
    results=[line[len(MARKER):] for line in stdout.splitlines() if line.startswith(MARKER)]
    result=json.loads(results[-1]) if results else None
    return {"case":case,"command":command,"workerDeadlineS":options.worker_timeout_s,
        "exitCode":p.returncode,"outerError":error,"interrupted":interrupted,"fatalOuterError":fatal,
        "stdout":stdout,"stderr":stderr,
        "result":result,"durationS":time.monotonic()-started,
        "passed":p.returncode==0 and error is None and result is not None and result["passed"]}


def tables(results):
    by={r["case"]:r["result"]["measurements"] for r in results if r["passed"]}
    config=[];containers=[]
    if "standalone_config" in by:
        s=by["standalone_config"];config.append(["独立Config入口","CLI gain=1.5",s["initialGain"],s["initialOutputMps"],"真实Float64接收"])
        config.append(["独立动态校验","越界/NaN/±Inf/整数/字符串",1.2,0.24,"拒绝后保留合法值"])
        config.append(["gain两端点","依次设置0.0与2.0","0 / 2","0 / 0.4","接受并实际观察两端输出"])
    if "component_parameters" in by:
        p=by["component_parameters"]
        for c in p["configurations"]:
            config.append([c["label"],"LoadNode参数/extra见原始记录",c["gain"],c["outputMps"],
                           "typo未声明/动态拒绝" if c["dynamicUnknownAccepted"] is False else "加载/数值通过"])
        for bad in p["invalidConstruction"]:config.append([bad["input"],
            "非法extra类型" if bad.get("source")=="extra_arguments" else "非法gain构造",
            "未创建","无组件输出","加载拒绝，已有列表不变"])
    for case in ["container_single","container_mt","container_isolated"]:
        if case in by:
            c=by[case];containers.append([c["executable"],c["pid"],c["slowTid"],", ".join(map(str,c["heartbeatTids"])),
                c["heartbeatDuringSlow"],c["maxConcurrency"],"默认管理参数服务关闭；readonly另由observable_manager验收"])
    return [{"id":"config","columns":["场景","配置入口","生效gain","输出m/s","实际结果"],"rows":config,
             "caption":"同一Config类的独立入口与动态装载；数值来自真实参数服务和Float64接收。管理参数、Context全局CLI与LoadNode.parameters分开验证。"},
            {"id":"containers","columns":["官方容器","PID","slow线程ID","heartbeat线程ID","slow内heartbeat","最大业务并发","管理接口/只读作用范围"],
             "rows":containers,"caption":"官方三个容器同一软件门闩负载实测。isolated仍为同PID、默认每组件ST执行器；mt显式thread_num=2。只断言重叠，不保证精确频率。"}]


def main():
    options=arguments()
    if options.worker:return worker(options)
    def terminate_as_interrupt(signum,frame):
        raise KeyboardInterrupt(f"parent received signal {signum}")
    signal.signal(signal.SIGTERM,terminate_as_interrupt)
    began=time.monotonic();results=[]
    for case in (CASES if options.case=="all" else [options.case]):
        r=run_worker(options,case);results.append(r)
        print(case+": "+("PASS" if r["passed"] else "FAIL"),flush=True)
        if r["result"] and not r["passed"]:print(r["result"].get("error",""),file=sys.stderr)
        if r["interrupted"] or r["fatalOuterError"]:break
    sources=[{"path":str(p.relative_to(HUB)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(HERE.rglob("*")) if p.is_file() and (p.suffix in [".cpp",".py",".xml"] or p.name=="CMakeLists.txt")]
    report={"schemaVersion":1,"checkedAt":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "passed":all(r["passed"] for r in results),"interrupted":any(r["interrupted"] for r in results),
        "durationS":time.monotonic()-began,
        "parameters":{k:str(v) if isinstance(v,Path) else v for k,v in vars(options).items() if k not in ["worker","report"]},
        "environment":{"ROS_DOMAIN_ID":str(options.domain_id),"ROS_AUTOMATIC_DISCOVERY_RANGE":"LOCALHOST", "RMW_IMPLEMENTATION":"rmw_fastrtps_cpp","ROS_LOCALHOST_ONLY":"unset","ROS_STATIC_PEERS":"unset"},
        "results":results,"sourceHashes":sources,"teachingTables":tables(results),
        "scope":"真实原创C++组件、官方single/mt/isolated与显式开启管理参数服务的原创wrapper；本机软件实验，无仿真/硬件。",
        "limits":["标准容器默认关闭管理参数服务；readonly拒绝来自observable_manager真实Describe/Set接口，不能混称标准容器参数接口。",
            "mt本轮显式2线程，不把文档固定4线程写成默认；isolated默认每组件ST，本轮不测试--use_multi_threaded_executor分支。",
            "forward_global_arguments只控制Context全局ROS CLI；不会屏蔽已进入LoadNode.parameters的值。",
            "未知extra键被忽略属于记录的实现行为，不是可用的NodeOptions setter或未来版本保证。",
            "sleep和/tmp门闩是模拟IO；只比较业务span重叠，不推导CPU加速、严格实时期限、零复制或故障隔离。",
            "本例只做先取消timer再卸载的受控路径，不证明任意持有外部线程/资源组件可安全动态卸载。"]}
    if options.build_root:
        folder=options.build_root/"log/latest_build/runtime_lab_components"
        report["buildEvidence"]={"root":str(options.build_root),"logs":{
            p.name:p.read_text(errors="replace") for p in folder.glob("*.log") if p.name in ["command.log","stdout_stderr.log","stderr.log"]}}
    if options.report.is_file():
        old=json.loads(options.report.read_text());history=old.pop("previousAttempts",[]);report["previousAttempts"]=[*history,old]
    options.report.parent.mkdir(parents=True,exist_ok=True)
    options.report.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"passed":report["passed"],"report":str(options.report.resolve())},ensure_ascii=False))
    return 130 if report["interrupted"] else (0 if report["passed"] else 1)


if __name__=="__main__":sys.exit(main())
