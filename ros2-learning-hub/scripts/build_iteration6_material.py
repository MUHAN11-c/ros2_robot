#!/usr/bin/env python3
"""第6轮：从已核实模型/TF与负惯量报告生成正文，不在构建时启动ROS。

输入：通过的两报告、8项原创源/输入指纹、独立approved/报告SHA审查。
输出：最后应用的iteration-6-revisions及幂等模型API。记录数不代替范围审核。
"""
import hashlib
import json
from pathlib import Path
from build_iteration3_material import load_verified_report

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'validation-evidence'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def measured(title,columns,rows,caption,filename='model-current-validation.json'):
    if not rows or any(len(r)!=len(columns) for r in rows):raise ValueError('表格行列不一致')
    path=EVIDENCE/filename
    return dict(title=title,columns=columns,rows=[[str(v) for v in row] for row in rows],caption=caption,
                evidenceFile=path.relative_to(ROOT).as_posix(),evidenceSha256=sha(path))


def source(filename,description):
    suffix=Path(filename).suffix
    language='cmake' if Path(filename).name=='CMakeLists.txt' else 'python' if suffix=='.py' else 'xml'
    return dict(label='model_labs/'+filename,language=language,type='complete',
                sourceFile='examples/model_labs/'+filename,explanation=description)


def vector(values):
    # 浮点旋转产生的1e-16量级余数按显示阈值归零；原始报告和1e-9验收容差分开保留。
    return '['+', '.join('0' if abs(x)<1e-12 else format(x,'.6g') for x in values)+']'


def main():
    data,files=load_verified_report('model','examples/model_labs')
    # 边界报告只调用两份Python，整包源码由主运行报告覆盖，不把二者范围混用。
    boundary=json.loads((EVIDENCE/'model-boundaries-current-validation.json').read_text())
    if boundary.get('passed') is not True or not boundary.get('sourceHashes'):
        raise ValueError('需要通过的边界实测及指纹')
    for record in boundary['sourceHashes']:
        path=(ROOT/record['path']).resolve(strict=True)
        if not path.is_relative_to((ROOT/'examples/model_labs').resolve()) or sha(path)!=record['sha256']:
            raise ValueError('边界脚本已变化，需要重新验收：'+record['path'])
    for p in (ROOT/'examples/model_labs').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.relative_to(ROOT).as_posix() not in files:
            raise ValueError('新增模型/说明未被运行指纹覆盖：'+str(p))
    review_path=EVIDENCE/'iteration6-model-source-review.json';review=json.loads(review_path.read_text())
    if review.get('approved') is not True:raise ValueError('需要第6轮独立审查通过')
    for name in ('model-current-validation.json','model-boundaries-current-validation.json'):
        if review.get('reviewedReports',{}).get(name,{}).get('sha256')!=sha(EVIDENCE/name):
            raise ValueError('审查尚未绑定当前报告：'+name)
    resources=review['textbookResources']
    if not {'eco-model-rviz','eco-tf-frames'}<={l for r in resources for l in r.get('lessons',[])}:
        raise ValueError('缺少对应两章主张的一手依据')
    runtime=data['runtimeModels']
    if len(runtime)!=2 or not all(r.get('passed') for r in runtime) or data['cleanup']['escalations']:
        raise ValueError('配置或退出路径变化，应先审核正文')
    dimensions=[]
    for r,expanded in zip(runtime,data['expandedModels']):
        summary=expanded['summary'];types=[j['type'] for j in summary['joints']]
        dimensions.append([r['name'],r['radiusM'],r['separationM'],r['footprintToBase']['xyzM'][2],
                           summary['links'],types.count('fixed'),types.count('continuous'),len(summary['inertias'])])
    config_table=measured('两种配置：同一安装模型的尺寸与结构',
        ['配置','半径m','轮距m','base高度m','link','fixed','continuous','惯量实体'],dimensions,
        '普通复制安装资源逐字节核对；从空当前目录通过安装share启动。根与光学frame不赋刚体质量，两个配置均有五个假设实体惯量。不是实测机械尺寸或动力学。')
    state_rows=[]
    for r in runtime:
        for p in r['phases']:
            state_rows.append([r['name'],p['kind'],vector(p['positionsRad']) if 'positionsRad' in p else '非法长度' if p['kind']=='unequal_arrays' else '合法velocity-only，position空',
                               '更新到本条输入时戳' if 'transforms' in p else f"{p['windowS']}s内时戳未变",
                               '几何与旋转通过' if 'transforms' in p else p['logMarker']])
    state_table=measured('关节状态：位置、非法长度与仅速度消息',
        ['模型','输入阶段','位置rad','TF时戳','附加证据'],state_rows,
        '默认两位置阶段、一非法长度、一合法velocity-only；覆盖两位置阶段。拒绝/跳过有RSP日志；有限窗口TF未更新不等于物理停车。20Hz是节流上限，不是缺状态时自动发TF。')
    negative=boundary['negativeInertia']['commands']
    if negative['urdfParser']['returnCode']!=0 or negative['numericInspector']['returnCode']!=1:
        raise ValueError('负惯量反例结果已变，应更新解释而非沿用旧结论')
    inertia_table=measured('同一负惯量文件：结构通过仍需数值验收',
        ['检查入口','本次退出码','实际观察','能支持的结论'],[
            ['check_urdf',negative['urdfParser']['returnCode'],'语法/树可解析','没有证明惯量正定或物理参数可信'],
            ['inspect_model.py',negative['numericInspector']['returnCode'],'拒绝left_wheel负Iyy','本例对角惯量正值检查有效，非一般动力学验证']],
        '只改默认展开文件的left_wheel Iyy为-0.00064 kg*m²，保持其他内容；完整命令、输出与夹具SHA另存边界报告。',
        'model-boundaries-current-validation.json')
    optical_table=measured('光学单位点转到base_link：含安装平移',
        ['光学点沿轴','输入点m','base_link输出m','手算期望m'],
        [[p['axis'],vector(p['inputM']),vector(p['outputM']),vector(p['expectedM'])] for p in runtime[0]['opticalPoints']],
        't=[0.18,0,0.1]m，rpy=(-π/2,0,-π/2)rad；两配置共六点实际通过。显示把绝对值<1e-12m归零，原始报告保留浮点余数，验收绝对容差1e-9m。')
    validation=('2026-11-07在Jazzy RSP '+data['versions']['robot_state_publisher']+'/xacro '+data['versions']['xacro']+
                '、独立域219/LOCALHOST实际构建安装一个描述包，从异目录启动默认/覆盖配置并检查真实TF。'+
                '参数回应后晚加入固定边、六个JointState阶段、两配置六光学点、两个非法launch拒绝、原最小URDF解析及负惯量反例通过。'+
                '未运行RViz/urdf_tutorial GUI、真实相机、动力学/仿真/硬件、父中断或非零活动joint origin旋转反例；根惯量局限按源码核对。')
    revision=dict(meta=dict(iteration='2026-11-07-r6',sourceReviewFile=review_path.relative_to(ROOT).as_posix(),sourceReviewSha256=sha(review_path)),
                  resources=resources,chapters={})
    eco=json.loads((ROOT/'source/ecosystem.json').read_text())
    sources={c['id']:list(c['sourceIds']) for c in eco['chapters'] if c['id'] in ('eco-model-rviz','eco-tf-frames')}
    for lesson in sources:
        sources[lesson]=list(dict.fromkeys(sources[lesson]+[r['id'] for r in resources if lesson in r.get('lessons',[])]))
    expand='''# 在教材目录运行。Xacro输入已随工程下载，不再引用缺失文件。
source /opt/ros/jazzy/setup.bash
# m/rad/kg为模型单位；展开只产生普通URDF，不自动验证本例所有物理合同。
xacro examples/model_labs/learning_description/urdf/robot.urdf.xacro > /tmp/learning_robot.urdf
# 语法/树与数值各自检查；check_urdf为0不等于惯量已经合格。
check_urdf /tmp/learning_robot.urdf
python3 examples/model_labs/inspect_model.py /tmp/learning_robot.urdf
'''
    command=dict(label='完整无GUI模型验收',language='bash',type='commands',code='''# 输入：完整描述包和Jazzy依赖；输出到每次新建的/tmp目录，不接设备。
source /opt/ros/jazzy/setup.bash
# 普通复制安装、展开/解析、安装异目录启动、真实TF、错误输入与正常收尾。
timeout --signal=INT --kill-after=8s 120s python3 examples/model_labs/validate_model.py
''',explanation='依赖和手动构建见model_labs/README；默认不覆盖教材绑定证据。外层timeout不是已做父中断注入的证明。')
    revision['chapters']['eco-model-rviz']=dict(sourceIds=sources['eco-model-rviz'],validation=validation,
        steps={'2':dict(code=expand,body='Xacro已提供在完整model_labs包中；在教材目录使用明确源路径，展开、结构解析与限定数值自检分别核对。')},sections={
        '2':dict(paragraphs=[
            '原最小robot.urdf仍只含车体和固定雷达，用于分离显示、资源和TF问题，没有提供完整惯性、车轮或控制。其同源minimal.urdf现已用check_urdf实际解析；原urdf_tutorial/RViz显示命令未执行。后文新增完整参数化包与无GUI TF验收，不把解析通过扩成显示或物理仿真通过。',
            '几何使用米，颜色值在零到一之间。此最小雷达几何中心与link原点重合，joint origin是安装位姿。使用mesh时还需安装资源；新包先用盒体/圆柱，让加载与轴向不依赖外部网格。'],codeBlocks={'0':dict(sourceFile='examples/model_labs/learning_description/urdf/minimal.urdf')}),
        '3':dict(appendParagraphs=['未安装urdf_tutorial时，可先用后文自己的完整资源包检查TF；该入口不启GUI，也不隐式启动joint_state_publisher。不能据TF数值通过声称已经在RViz看到模型。']),
        '4':dict(codeBlocks={'0':dict(code=expand,explanation='所用Xacro文件已提供；安装副本的默认/覆盖展开与check_urdf均实际执行，源码路径便捷命令和数值检查保持同一文件内容。')})},
        appendSections=[
            dict(title='完整参数化模型：先把几何与惯量放在同一约定',paragraphs=[
                'learning_description提供七link、四fixed和两continuous关节。默认半径0.08m、轮距0.36m，覆盖0.10/0.40m另验收；base高度按r+0.06计算，车轮中心在base中为[0,±轮距/2,-0.06]。默认值仅在Xacro定义，launch空值沿用，再检查展开值的有限范围。Xacro本身只展开，不代替模型语义或控制参数验收。',
                '五个实体采用假设均匀盒体/圆柱的质量和对角惯量，惯性原点在其几何中心。车轮visual/collision的圆柱由Z转到Y，轴向惯量相应放在Iyy；不能只转外观却保留错误惯量轴。数值正定、主惯量三角关系和check_urdf分别检查，仍没有测真实质量、接触或仿真稳定性。',
                'base_footprint和camera_optical_frame仅表达参考坐标，没有实体质量。当前KDL对根inertia会警告并继续，但不按普通刚体根使用它；本例用空参考根连接有惯量base_link。根惯量警告只核实现，本轮没有再运行该反例。'],tables=[config_table]),
            dict(title='固定边、关节状态与节流频率分开看',paragraphs=[
                'driver先获取真实RSP参数响应，之后才创建Listener，实际获得构造时已发送的固定边；活动轮子尚无有效JointState，所以动态边不存在。20Hz参数是回调发布节流上限，不是定时生成未知关节位置。RSP按收到的位置算运动学，不从velocity或目标命令积分轮子位置。',
                'TF帧前缀model/、alternate/只加到父子frame；发送的关节键仍为left_wheel_joint/right_wheel_joint。本例launch约束前缀格式，RSP本身是直接拼接，不能默认它替任意字符串补斜杠。活动轴在joint局部坐标中，两轮均为+Y；镜像安装位置不自动反转状态符号。',
                '默认先验证0/0rad，再发送两种不同输入：name/position不等长是非法长度；position空且velocity等长是协议允许的velocity-only，只是RSP无法用它计算位置。两种日志分别确认拒绝/跳过，0.25s窗口内TF时戳维持旧值，随后π/2、-π/4的位置输入在同实例恢复并得到期望旋转。该有限观察不证明物理停车，也不穷尽输入边界。活动joint origin旋转均为零；非零origin对局部轴的复合仅按KDL源码/手算解释。'],tables=[state_table]),
            dict(title='结构检查通过后，再做物理数值检查',paragraphs=[
                '边界夹具只把left_wheel Iyy改为负值。真正check_urdf仍返回0，标准库数值自检返回1并指出质量/惯量须正且有限。这说明语法/树可解析与物理数值合格是不同层次；不能从一个“Successfully Parsed”推断模型已适合仿真。',
                'inspect_model限定小型普通URDF、盒体/圆柱与对角惯量，检查正值、有限值、轴向和树；它不是通用URDF解析器、碰撞检测器或任意非对角惯量特征值工具。对角主惯量满足关系也不能替代真实质量、单位、惯性原点或机械标定验证。'],tables=[inertia_table]),
            dict(title='完整包与异目录启动：验证安装资源而非当前目录',paragraphs=[
                'CMake普通复制urdf与launch进share，排除Python缓存，不使用symlink-install。driver核安装文件字节一致，并从空当前目录启动；launch通过ament索引定位安装Xacro，robot_description显式强制字符串类型。该证据解决当前目录依赖，不扩大成跨机依赖闭包或GUI资源显示。'],codeBlocks=[
                    source('learning_description/package.xml','资源包构建/运行依赖分开，许可证独立保留。'),
                    source('learning_description/CMakeLists.txt','正常复制安装URDF与launch，避免缓存与源码软链接。'),
                    source('learning_description/urdf/robot.urdf.xacro','完整默认/覆盖模型；单位、几何轴与惯量假设见中文注释。'),
                    source('learning_description/launch/model.launch.py','仅启动RSP，参数有限范围在创建节点前核验；不生成JointState或GUI。'),
                    source('inspect_model.py','标准库小型数值自检，范围明确，与真正check_urdf分工。'),
                    source('validate_model.py','实际构建/安装/TF/位置、非法长度与仅速度输入driver；父中断未注入。'),command])],
        appendExercises=[
            dict(question='publish_frequency=20，为什么活动车轮TF仍不存在？',answer='没有有效关节位置时RSP不会生成这条活动变换。频率用于回调发布节流，不是自动模拟关节运动；先核JointState位置、名字、时间戳和匹配。'),
            dict(question='TF叫model/left_wheel，JointState也要改成model/left_wheel_joint吗？',answer='本例不需要。frame_prefix只加TF frame，URDF与JointState关节键保持原名；若改关节名字，必须一起改模型和所有状态/控制引用。'),
            dict(question='check_urdf为0，能证明负惯量被排除吗？',answer='不能。本轮同一负Iyy文件被check_urdf解析通过，却被数值自检拒绝。语法树、物理参数与仿真/硬件分别验收。'),
            dict(question='车轮圆柱外观从Z轴转向Y轴，惯量也应如何处理？',answer='在本例均匀圆柱且惯性系与link重合的假设下，轴向项放Iyy，另外两项为横向惯量。外观旋转不自动改惯量，任意旋转张量需按RIRᵀ转换。')])
    revision['chapters']['eco-tf-frames']=dict(sourceIds=sources['eco-tf-frames'],validation=validation+' 本章原静态广播CLI/view_frames流程未运行，新增证据来自完整RSP模型。',appendSections=[
        dict(title='用真实光学frame检查三个基轴与原点',paragraphs=[
            '新增模型的camera_link采用X前/Y左/Z上；光学frame采用Z前/X右/Y下。固定rpy=(-π/2,0,-π/2)rad后，三个光学基轴在base中分别朝-Y、-Z、+X。joint origin给出父到关节安装关系，运动轴定义在joint局部系；非零安装旋转会改变轴在父系的表达，不能只看axis文字三个数。',
            '下表是三个相距光学原点1m的点，变换到base_link时还加相机安装平移[0.18,0,0.1]m。点与自由方向向量不同：方向只旋转，点还平移。默认和覆盖模型共六点由实际RSP、DDS与tf2检查，1e-16量级余数在原报告保留，不当成轴向错误。',
            '这里的base_footprint只是平地几何参考，没有自动获得odom/map位姿；模型发布者也不提供定位。可把固定边晚加入、活动状态、外部定位和真实图像分开验收。本轮活动origin为零，没有把非零origin的旋转轴复合或真实相机标定冒称实测。'],tables=[optical_table])],appendExercises=[
            dict(question='光学点[0,0,1]变到base为何是[1.18,0,0.1]而不是[1,0,0]？',answer='它是从光学原点出发的点，先旋转为base的+X，再加安装平移[0.18,0,0.1]m；只有自由方向向量才不加原点平移。'),
            dict(question='joint axis=[0,1,0]能不看origin就断言父系+Y是转轴吗？',answer='不能。axis在joint局部系，非零origin旋转会改变父系表达。本轮两个活动origin旋转为零；一般关系按KDL源码和旋转复合处理，不扩大本轮实测。'),
            dict(question='获得base_footprint到全部link的TF就有全局定位了吗？',answer='没有。这只是模型内部运动学树；odom/map到机器人参考系还需要对应定位/里程计来源、时戳与唯一发布责任。'),
            dict(question='拿到有效位置之前静态TF已出现，为什么不是节点启动顺序错误？',answer='固定关节在RSP构造期发布且可按瞬态历史供晚加入者；活动关节依赖有效位置。应分别核固定边、匹配状态、消息与时间，不能要求它们同一时刻出现。')])
    api_path=ROOT/'source/api-reference.json';api=json.loads(api_path.read_text())
    addition=dict(id='api-model-coordinates',title='模型接口：结构、状态、TF与物理数值',lessons=['eco-model-rviz','eco-tf-frames'],
        columns=['对象','输入/单位','输出或语义','必须另核的边界'],rows=[
            ['joint origin / axis','xyz m、rpy rad、局部轴单位向量','安装变换先于局部关节运动','本例活动origin旋转0；一般轴按安装旋转变到父系，不能只读axis数值。'],
            ['JointState.position','RSP需位置与name等长；转动rad/平移m','算活动TF，保留输入时戳并受节流','协议允许velocity-only，但RSP会跳过无位置输入；不自动积分速度，名称/来源/日志另核。'],
            ['frame_prefix','直接前缀字符串','只拼接TF父子frame','不改URDF/JointState键，也不自动补斜杠；本例launch另约束格式。'],
            ['固定/活动TF','robot_description与有效关节位置','固定边可晚加入；活动边依赖状态','20Hz不是自动生成运动；不提供odom/map定位或物理状态保证。'],
            ['check_urdf / 数值检查','展开URDF、质量kg、惯量kg*m²','结构解析与明确数值合同分别输出','本例负Iyy可解析却数值失败；无GUI、无碰撞/动力学实测。'],
            ['camera optical frame','Z前/X右/Y下，安装平移m','点旋转加平移，方向仅旋转','有TF不等于相机标定或图像正确；本例只检查软件单位点。']],
        notes=['模型树、TF数值、显示资源、动力学与硬件是不同证据。','安装与参考xacro同版仍可能有动态arg名补丁差异；本例用字面arg名，不推广未测功能。'])
    indices={a['id']:i for i,a in enumerate(api['apiReferences'])}
    if addition['id'] in indices:api['apiReferences'][indices[addition['id']]]=addition
    else:api['apiReferences'].append(addition)
    api_path.write_text(json.dumps(api,ensure_ascii=False,indent=2)+'\n')
    dest=ROOT/'source/iteration-6-revisions.json';dest.write_text(json.dumps(revision,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(revision=str(dest),newTables=4,newCompleteFiles=6,newExercises=8)))


if __name__=='__main__':main()
