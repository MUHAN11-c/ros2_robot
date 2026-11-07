#!/usr/bin/env python3
"""构建安装描述包，再用真实RSP和tf2检查模型；不启动RViz或仿真器。

输入：本目录完整包、两组轮半径/轮距、有限JointState位置rad。
输出：独立/tmp构建、展开模型、日志、安装指纹与JSON报告。
步骤：复制安装→异目录启动→晚加入固定TF→位置/非法长度/合法仅速度状态→光学轴。
等待用monotonic秒，几何m，时间戳ns；源码SHA是文件身份，TF按语义数值比较。
边界：只验证本例树、数值与正常退出；父中断、GUI、动力学和硬件未覆盖。
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
from inspect_model import inspect_model

HERE = Path(__file__).resolve().parent
HUB = HERE.parents[1]


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--domain-id', type=int, default=219, help='专用本机域，默认219')
    parser.add_argument('--report', type=Path, help='省略则写本次/tmp目录，不覆盖教材证据')
    args = parser.parse_args()
    if not 0 <= args.domain_id <= 232:parser.error('domain-id须在0..232')
    return args


def near(actual, expected):
    if len(actual) != len(expected) or not all(math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9) for a, b in zip(actual, expected)):
        raise AssertionError(f'几何不符：actual={actual}, expected={expected}')


def transform_values(transform):
    t, q = transform.transform.translation, transform.transform.rotation
    return dict(xyzM=[t.x, t.y, t.z], quaternion=[q.x, q.y, q.z, q.w],
                parent=transform.header.frame_id, child=transform.child_frame_id,
                stampNs=transform.header.stamp.sec*10**9+transform.header.stamp.nanosec)


class Lab:
    def __init__(self, output, report):
        self.output, self.report, self.processes = output, report, []
        self.deadline = time.monotonic()+100.0
        self.context = self.executor = self.node = None

    def start(self, label, argv, cwd=None):
        path = self.output/(label+'.log');stream = path.open('wb')
        process = subprocess.Popen(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        record = dict(label=label, argv=argv, cwd=str(cwd or Path.cwd()), pid=process.pid, logFile=str(path), signals=[])
        self.processes.append((process, stream, record));self.report.setdefault('processes', []).append(record)
        return process, record

    def collect(self, process, interrupt=False):
        _, stream, record = next(x for x in self.processes if x[0] is process)
        def send(sig, group=False):
            try:
                # 正常停止只发launch父PID，交由launch转发，避免同时对父子重复INT。
                if group:os.killpg(process.pid, sig)
                else:process.send_signal(sig)
                record['signals'].append(dict(signal=signal.Signals(sig).name, target='group' if group else 'pid'))
            except ProcessLookupError:record.setdefault('signalRaces', []).append(signal.Signals(sig).name)
        if interrupt and process.poll() is None:send(signal.SIGINT)
        try:process.wait(timeout=6.0)
        except subprocess.TimeoutExpired:
            send(signal.SIGTERM, group=True)
            try:process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                send(signal.SIGKILL, group=True);process.wait(timeout=2.0)
        stream.close();raw=Path(record['logFile']).read_bytes();text=raw.decode(errors='replace')
        children = [int(n) for n in re.findall(r'process started with pid \[(\d+)\]', text)]
        record.update(returnCode=process.returncode, logSha256=hashlib.sha256(raw).hexdigest(), logText=text,
                      launchedChildPids=children, allRecordedPidsGone=all(not Path('/proc',str(p)).exists() for p in [process.pid,*children]))
        if len(raw)>2*1024*1024:raise ValueError('教学日志超出2MiB')
        return process.returncode

    def command(self, label, argv, cwd=None):
        process, record = self.start(label, argv, cwd)
        try:process.wait(timeout=min(45.0,max(0.1,self.deadline-time.monotonic())))
        except BaseException:
            self.collect(process, interrupt=True);raise
        self.collect(process)
        return record

    def pump(self, duration):
        until=time.monotonic()+duration
        while time.monotonic()<until:
            if time.monotonic()>self.deadline:raise TimeoutError('总单调软期限')
            self.executor.spin_once(timeout_sec=max(0.0,min(0.02,until-time.monotonic())))

    def wait(self, condition, label, seconds=7.0):
        until=min(self.deadline,time.monotonic()+seconds)
        while not condition():
            if time.monotonic()>=until:raise TimeoutError(label)
            self.pump(0.025)

    def prepare(self):
        package=HERE/'learning_description'
        build=self.command('build', ['colcon','--log-base',str(self.output/'log'),'build','--base-paths',str(package),
                            '--build-base',str(self.output/'build'),'--install-base',str(self.output/'install'),'--merge-install'])
        assert build['returnCode']==0,build['logText']
        share=self.output/'install/share/learning_description'
        installed=[]
        for relative in ['package.xml','urdf/minimal.urdf','urdf/robot.urdf.xacro','launch/model.launch.py']:
            source=package/relative;target=share/relative
            assert target.is_file() and not target.is_symlink() and target.read_bytes()==source.read_bytes()
            installed.append(dict(file=relative,sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
        self.report['installedResources']=dict(share=str(share),normalCopy=True,files=installed)
        minimum=self.command('check_minimal', ['check_urdf',str(share/'urdf/minimal.urdf')]);assert minimum['returnCode']==0
        self.report['minimalModel']=inspect_model(share/'urdf/minimal.urdf')
        for label, args in [('default',[]),('override',['wheel_radius:=0.10','wheel_separation:=0.40'])]:
            target=self.output/(label+'.urdf')
            expanded=self.command('expand_'+label,['xacro',str(share/'urdf/robot.urdf.xacro'),*args,'-o',str(target)])
            checked=self.command('check_'+label,['check_urdf',str(target)])
            assert expanded['returnCode']==checked['returnCode']==0
            info=inspect_model(target)
            assert info['links']==7 and len(info['joints'])==6 and len(info['inertias'])==5
            self.report.setdefault('expandedModels',[]).append(dict(name=label,file=str(target),summary=info))

    def launch_argv(self, args):
        # Shell程序是固定字符串，路径作为位置参数传递并引用，不做字符串拼接执行。
        return ['bash','-c','source "$1" --; cd "$2"; exec ros2 launch learning_description model.launch.py "${@:3}"',
                'model-lab',str(self.output/'install/setup.bash'),str(self.output/'empty-cwd'),*args]

    def runtime(self):
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.signals import SignalHandlerOptions
        from rclpy.time import Time
        from rcl_interfaces.srv import GetParameters
        from sensor_msgs.msg import JointState
        from geometry_msgs.msg import PointStamped
        from tf2_ros import Buffer, TransformListener
        from tf2_geometry_msgs import do_transform_point
        self.context=Context();rclpy.init(context=self.context,signal_handler_options=SignalHandlerOptions.NO)
        self.executor=SingleThreadedExecutor(context=self.context)
        self.node=Node('model_lab_probe',context=self.context);self.executor.add_node(self.node)
        publisher=self.node.create_publisher(JointState,'/model_lab/joint_states',10)
        (self.output/'empty-cwd').mkdir()
        for label,radius,separation,prefix,args in [
                ('default',0.08,0.36,'model/',[]),
                ('override',0.10,0.40,'alternate/',['wheel_radius:=0.10','wheel_separation:=0.40','frame_prefix:=alternate/'])]:
            process,log=self.start('launch_'+label,self.launch_argv(args))
            client=self.node.create_client(GetParameters,'/model_lab/state_publisher/get_parameters')
            self.wait(client.service_is_ready,'状态发布者参数服务未发现')
            request=GetParameters.Request(names=['robot_description','frame_prefix','publish_frequency'])
            future=client.call_async(request);self.wait(future.done,'参数响应未到');response=future.result()
            assert response.values[0].type==4 and response.values[1].string_value==prefix and response.values[2].double_value==20.0
            description=response.values[0].string_value
            received=self.output/(label+'-from-parameter.urdf');received.write_text(description)
            assert inspect_model(received)==self.report['expandedModels'][0 if label=='default' else 1]['summary']
            # 参数响应经RSP执行器处理，故其构造期固定TF已发送；此后才创建Listener。
            # Buffer不绑定node，避免重复案例在同一node自动创建同名tf2_frames服务。
            buffer=Buffer();listener=TransformListener(buffer,self.node,spin_thread=False)
            target=prefix+'base_link';left=prefix+'left_wheel';right=prefix+'right_wheel'
            self.wait(lambda: buffer.can_transform(target,prefix+'laser',Time()),'晚加入固定TF未到')
            self.wait(lambda: buffer.can_transform(target,prefix+'camera_optical_frame',Time()),'光学固定TF未到')
            self.wait(lambda: publisher.get_subscription_count()==1,'JointState实际匹配未完成')
            assert not buffer.can_transform(target,left,Time()) and not buffer.can_transform(target,right,Time())
            footprint=transform_values(buffer.lookup_transform(prefix+'base_footprint',target,Time()))
            near(footprint['xyzM'],[0,0,radius+0.06])
            result=dict(name=label,radiusM=radius,separationM=separation,framePrefix=prefix,
                        lateJoinAfterParameterReply=True,dynamicAbsentBeforeStates=True,
                        footprintToBase=footprint,phases=[],opticalPoints=[])
            self.report.setdefault('runtimeModels',[]).append(result)
            def send(names,positions,velocities=None):
                message=JointState();message.header.stamp=self.node.get_clock().now().to_msg()
                message.name=names;message.position=positions;message.velocity=velocities or []
                publisher.publish(message)
                return message.header.stamp.sec*10**9+message.header.stamp.nanosec
            joint_names=['left_wheel_joint','right_wheel_joint']  # 不加TF frame_prefix。
            def set_angles(angles):
                self.pump(0.07)  # 超过本配置50ms节流间隔；不是用它替代DDS发现。
                sent=send(joint_names,angles)
                def updated():
                    return all(buffer.can_transform(target,f,Time()) and transform_values(buffer.lookup_transform(target,f,Time()))['stampNs']==sent for f in (left,right))
                self.wait(updated,'活动TF未更新到本条JointState时戳')
                values=[transform_values(buffer.lookup_transform(target,f,Time())) for f in (left,right)]
                for i,value in enumerate(values):
                    near(value['xyzM'],[0,(1 if i==0 else -1)*separation/2,-0.06])
                    expected=[0,math.sin(angles[i]/2),0,math.cos(angles[i]/2)]
                    # q与-q表达同一旋转；用绝对点积判定，避免误判符号选择。
                    assert math.isclose(abs(sum(a*b for a,b in zip(value['quaternion'],expected))),1.0,abs_tol=1e-9)
                result['phases'].append(dict(kind='valid_positions',positionsRad=angles,sentStampNs=sent,transforms=values))
                return sent
            initial=set_angles([0.0,0.0])
            if label=='default':
                for kind,positions,velocity,marker in [
                    ('unequal_arrays',[0.25],[], 'ignored an invalid JointState message'),
                    ('velocity_without_position',[],[1.0,1.0], 'whose position member was empty')]:
                    sent=send(joint_names,positions,velocity)
                    self.wait(lambda: marker in Path(log['logFile']).read_text(errors='replace'),'预期拒绝或忽略日志未出现')
                    self.pump(0.25)
                    stamps=[transform_values(buffer.lookup_transform(target,f,Time()))['stampNs'] for f in (left,right)]
                    assert stamps==[initial,initial]
                    result['phases'].append(dict(kind=kind,sentStampNs=sent,logMarker=marker,
                                                  unchangedTfStampsNs=stamps,windowS=0.25))
            set_angles([math.pi/2,-math.pi/4])  # 非法输入后同实例恢复有效状态。
            optical=buffer.lookup_transform(target,prefix+'camera_optical_frame',Time())
            for axis,xyz,expected in [('z',[0,0,1],[1.18,0,0.1]),('x',[1,0,0],[0.18,-1,0.1]),('y',[0,1,0],[0.18,0,-0.9])]:
                point=PointStamped();point.header.frame_id=prefix+'camera_optical_frame'
                point.point.x,point.point.y,point.point.z=map(float,xyz)
                out=do_transform_point(point,optical);actual=[out.point.x,out.point.y,out.point.z];near(actual,expected)
                result['opticalPoints'].append(dict(axis=axis,inputM=xyz,targetFrame=target,outputM=actual,expectedM=expected))
            listener.unregister();self.node.destroy_client(client)
            code=self.collect(process,interrupt=True)
            assert code==0 and log['allRecordedPidsGone'] and len(log['launchedChildPids'])==1
            assert all(s['signal']=='SIGINT' and s['target']=='pid' for s in log['signals'])
            result['passed']=True
            self.wait(lambda: publisher.get_subscription_count()==0,'前个状态节点未从图中消失')
        for label,args,marker in [('negative_radius',['wheel_radius:=-0.08'],'wheel_radius必须在'),
                                  ('nan_separation',['wheel_separation:=nan'],'wheel_separation必须在')]:
            result=self.command('reject_'+label,self.launch_argv(args))
            assert result['returnCode']!=0 and marker in result['logText'] and result['launchedChildPids']==[]
            self.report.setdefault('rejectedLaunchInputs',[]).append(dict(name=label,returnCode=result['returnCode'],marker=marker,nodeStarted=False))

    def close(self):
        for process,_,_ in self.processes:self.collect(process,interrupt=True)
        if self.node:
            self.executor.remove_node(self.node);self.node.destroy_node();self.node=None
        if self.executor:self.executor.shutdown(timeout_sec=2.0)
        if self.context and self.context.ok():self.context.shutdown()
        self.report['cleanup']=dict(allRecordedPidsGone=all(r['allRecordedPidsGone'] for _,_,r in self.processes),
                                    contextValid=self.context.ok() if self.context else False,
                                    escalations=[r['label'] for _,_,r in self.processes if any(s['signal']!='SIGINT' for s in r['signals'])])
        assert self.report['cleanup']['allRecordedPidsGone'] and not self.report['cleanup']['contextValid']


def main():
    args=arguments();output=Path(tempfile.mkdtemp(prefix='ros2-model-lab-'));report_path=args.report or output/'report.json'
    os.environ.update(ROS_DOMAIN_ID=str(args.domain_id),ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',
                      RMW_IMPLEMENTATION='rmw_fastrtps_cpp',ROS_LOG_DIR=str(output/'ros-logs'))
    os.environ.pop('ROS_LOCALHOST_ONLY',None);os.environ.pop('ROS_STATIC_PEERS',None)
    source_files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    report=dict(checkedAt=datetime.now(timezone.utc).isoformat(),passed=False,outputDirectory=str(output),domainId=args.domain_id,
                sourceHashes=[dict(path=p.relative_to(HUB).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(source_files)],
                limits=['本例无GUI、无图像、无物理仿真、无硬件或真实标定；正惯量数值不等于动力学已验证。',
                        '正常子进程退出与PID检查不覆盖父SIGINT/原生挂起；TF静止不证明物理停车。',
                        '复制安装与异目录启动不证明跨机、ABI或依赖闭包；原urdf_tutorial显示命令未运行。'])
    started=time.monotonic();lab=Lab(output,report);code=1
    try:
        report['versions']={name:ET.parse(Path('/opt/ros/jazzy/share')/name/'package.xml').findtext('version')
                            for name in ('robot_state_publisher','xacro','urdf','kdl_parser','rclpy','launch_ros')}
        lab.prepare();lab.runtime();report['passed']=True;code=0
    except KeyboardInterrupt:report['interrupted']=True;code=130
    except Exception:report['error']=traceback.format_exc()
    finally:
        try:lab.close()
        except Exception:report['cleanupError']=traceback.format_exc();report['passed']=False;code=1
        report['durationS']=time.monotonic()-started
        if report_path.exists():
            old=json.loads(report_path.read_text());report['previousAttempts']=old.get('previousAttempts',[])+[{k:v for k,v in old.items() if k!='previousAttempts'}]
        report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],report=str(report_path),durationS=report['durationS'])))
    if report.get('error'):print(report['error'])
    return code


if __name__=='__main__':raise SystemExit(main())
