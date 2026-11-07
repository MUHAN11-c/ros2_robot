#!/usr/bin/env python3
"""将第3轮动作/组件的已运行报告接入教材，不在构建时运行ROS。

输入是两份报告、报告绑定的原创源码以及独立源码审查；输出是最后应用的
iteration-3-revisions.json和幂等更新的API表。表格数值及单位来自原始报告。
源码或证据改变时停止生成，先重新审查；临时安装目录不是教材重建依赖。
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'validation-evidence'


def load_verified_report(name, prefix):
    """只接受通过的完整运行，核对源文件而非依赖/tmp中的旧二进制。"""
    path = EVIDENCE/(name+'-current-validation.json')
    data = json.loads(path.read_text())
    if data.get('passed') is not True:
        raise ValueError('需要通过的实际运行：'+name)
    records = data.get('sourceHashes', [])
    if not records:
        raise ValueError('缺少源码指纹：'+name)
    actual = {}
    for record in records:
        source = (ROOT/record['path']).resolve(strict=True)
        if not source.is_relative_to(ROOT) or not source.is_file():
            raise ValueError('源码越出教材目录：'+record['path'])
        if hashlib.sha256(source.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('源码变化，需要重新运行与审查：'+record['path'])
        actual[source.relative_to(ROOT).as_posix()] = source
    # 任何新增可执行源码也必须进入证据；不能默默把未跑过的新文件加入完整代码。
    for source in (ROOT/prefix).rglob('*'):
        if any(part in ('__pycache__','build','install','log') or part.startswith('.') for part in source.relative_to(ROOT/prefix).parts):
            continue
        if source.is_file() and (source.suffix in ('.py','.cpp','.hpp','.h','.xml','.cmake') or source.name=='CMakeLists.txt'):
            if source.relative_to(ROOT).as_posix() not in actual:
                raise ValueError('新增源码尚无运行指纹：'+str(source))
    return data, actual


def measured_tables(data, name, expected):
    """表格只复制已审核报告的教学摘要，保留完整事件的SHA出处。"""
    path = EVIDENCE/(name+'-current-validation.json')
    tables = data['teachingTables']
    if len(tables)!=expected:
        raise ValueError('主表数量变化，需要重新审查正文：'+name)
    result = []
    titles={'count-action':['Count协议的拒绝、终态与恢复'],
            'component-labs':['组件配置与加载的实际结果','官方三种容器的实际调度']}
    for index,original in enumerate(tables):
        item = {key:original[key] for key in ('columns','rows','caption')}
        item['title']=original.get('title') or titles[name][index]
        if not item['rows'] or any(len(row)!=len(item['columns']) for row in item['rows']):
            raise ValueError('表格缺行或列数不一致：'+name)
        # 教学表避免把0.30000000000000004当成重要差异；原始浮点数仍在绑定报告中。
        item['rows']=[[format(cell,'.6g') if isinstance(cell,float) else str(cell) for cell in row] for row in item['rows']]
        if any(isinstance(cell,float) for row in original['rows'] for cell in row):
            item['caption']+=' 表内小数按6位有效数字显示，原始报告保留实际浮点值。'
        item.update(evidenceFile=path.relative_to(ROOT).as_posix(),
                    evidenceSha256=hashlib.sha256(path.read_bytes()).hexdigest())
        result.append(item)
    return result


def source_blocks(records, prefix):
    blocks = []
    for name, file in sorted(records.items()):
        if not name.startswith(prefix+'/'):
            continue
        language = 'cmake' if file.name=='CMakeLists.txt' else {'.py':'python','.cpp':'cpp','.hpp':'cpp','.h':'cpp','.xml':'xml','.cmake':'cmake'}.get(file.suffix)
        if language:
            blocks.append(dict(label=Path(name).relative_to('examples').as_posix(), language=language,
                               type='complete', sourceFile=name,
                               explanation='本文件与报告绑定的原创工程同源；输入、单位、默认参数、执行顺序及关闭边界见中文注释。请按配套README构建并加载环境。'))
    return blocks


def command(label, code, explanation):
    return dict(label=label,language='bash',type='commands',code=code,explanation=explanation)


def editorial_patch():
    """修正既有快捷区的Fibonacci/Count字段混淆，不改第三方源码。"""
    return dict(
        expected=['能分清目标接纳、current反馈与最终status/completed，并按UUID对应同一目标。',
                  '忙碌目标拒绝后，首目标取消或自然完成仍可接收新的合法目标。',
                  '显式故障得到ABORTED与实际完成步数，后续短目标成功；物理停止另需执行端证据。'],
        commands={
            '0':dict(label='补充：官方Fibonacci演示依赖（未运行）',
                     code='# 本段安装官方Fibonacci演示，字段为order/sequence；本章Count主体另按下方完整工程复现。\n# 输入软件包名，输出安装的节点及接口；首次安装需要软件源，不属于离线阅读。\nsudo apt install ros-jazzy-action-tutorials-py',
                     explanation='官方补充演示的安装命令仅核对；本轮Count实测不依赖已启动Fibonacci服务端。'),
            '1':dict(label='补充终端A：官方Fibonacci服务端（未运行）',
                     code='# 每个终端先加载Jazzy环境；此服务端持续运行，Ctrl+C结束。\n# Goal使用order，Feedback/Result使用sequence；不要把Count的target/completed字段代入。\nsource /opt/ros/jazzy/setup.bash\nros2 run action_tutorials_py fibonacci_action_server',
                     explanation='官方Fibonacci入口仅核对；动作名称和类型以本次查询为准。'),
            '2':dict(label='补充终端B：检查官方Fibonacci类型并发目标（未运行）',
                     code='# 已启动补充演示后，先查动作类型，再读接口字段；这些补充命令未计入Count实测。\nsource /opt/ros/jazzy/setup.bash\nros2 action list -t\nros2 action info /fibonacci\nros2 interface show action_tutorials_interfaces/action/Fibonacci\n# order=5无量纲；先看接纳响应，再看sequence反馈与最终status/result。\nros2 action send_goal /fibonacci action_tutorials_interfaces/action/Fibonacci "{order: 5}" --feedback',
                     explanation='Fibonacci和Count各用自己的接口合同；本章新增Count实验的UUID、拒绝与终态证据单独保存。')},
        steps={
            '0':'先构建本章learning_count_interfaces与C++服务端，在每个运行终端加载同一安装环境；完整文件和命令见正文。',
            '1':'分别运行一个C++或Python Count服务端，先验证目标范围、成功和取消；每次只保留一个同名服务端。',
            '2':'用第3轮验收脚本观察忙碌拒绝、首目标结束与后续合法目标恢复；通过UUID区分目标，拒绝目标没有自己的执行结果。',
            '3':'再运行显式开启故障注入的扩展示例，核对ABORTED与completed，并检查后续短目标成功；普通基础服务端没有被偷偷加上故障。'})


def primary_sources(review):
    """从定点审查取真实固定URL；版本差异保留，不声称整包字节相同。"""
    records={item['id']:item for item in review['sourceRecords']}
    descriptions={
        'manager':('组件加载选项的官方实现','parameters、remap及已实现extra键，构造失败与加载响应。'),
        'manager-default':('组件管理节点的默认选项','管理参数服务与参数事件发布默认关闭，区别加载组件自身选项。'),
        'options':('NodeOptions的参数与全局选项','自动声明、允许未声明和全局参数转发的声明与默认边界。'),
        'release-mt':('安装对应版本的多线程容器入口','实际读取thread_num并创建共享多线程执行器。'),
        'release-isolated':('安装对应版本的isolated容器入口','默认每组件单线程执行器，额外模式开关与外层管理执行器。'),
        'cpp-parameter-service':('严格参数服务的整批查询错误处理','GetParameters遇未声明/未初始化异常的响应，不把空列表当逐项NOT_SET。'),
        'rcl-state-map':('Action目标的底层状态转换','取消中可继续成功、失败或取消；通用终态与业务结果分开解释。')}
    result=[]
    for key,(title,description) in descriptions.items():
        record=records[key]
        if not record.get('url') or not record.get('commit') or not record.get('sha256'):
            raise ValueError('一手出处缺少固定URL/提交/SHA：'+key)
        result.append(dict(id='iter3-'+key,title=title,url=record['url'],sourceUrl=record['url'],
                           category='源码与版本核查',version='Jazzy / 固定提交 '+record['commit'][:12],
                           description=description,checkedAt='2026-11-07',type='官方源码',
                           verification='已读固定一手源码；安装版本、快照、在线发布标签及逐文件SHA差异见iteration3-source-review.json，不把局部相同扩为整个版本相同。'))
    return result


def update_api_tables():
    path = ROOT/'source/api-reference.json'
    data = json.loads(path.read_text())
    additions = [
        dict(id='api-composition-options', title='组件配置：NodeOptions、加载参数与管理节点', lessons=['composition','parameters','deployment'],
             columns=['入口或选项','作用对象','调用/检查顺序','重要边界'], rows=[
                 ['NodeOptions构造并转交Node','当前被创建的节点','构造参数→Node基类→declare_parameter→读取有效值','同一个类的独立入口和组件入口都应转交选项；构造中不spin或无限等待。'],
                 ['LoadNode.parameters','本次加载的组件','发送有类型Parameter→构建parameter_overrides→组件声明读取','给管理节点传-p gain不等于给每个组件传gain；名称/命名空间与参数服务按返回值检查。'],
                 ['LoadNode.extra_arguments','标准manager支持的装载开关','核对固定版本create_node_options实现','本轮实现映射use_intra_process_comms和forward_global_arguments；任意NodeOptions setter不自动成为可用extra键。'],
                 ['forward_global_arguments','组件是否采用进程全局ROS参数','默认false，明确选择后才转发','全局节点重命名/参数可能影响组件；实验默认不启用，不把管理节点参数等同加载请求。'],
                 ['未声明参数与自动声明','组件自身参数策略','显式declare gain并验证有限DOUBLE；未知项另查','NodeOptions默认自动声明关闭；声明前的override、已声明参数、运行时set是不同阶段。'],
                 ['管理节点参数服务','ComponentManager自身','先确认参数服务实际存在，再用远程API','本机官方默认关闭管理参数服务；专用observable_manager显式开启，不能冒充官方可执行默认接口。']],
             notes=['本轮ConfigComponent与管理节点/容器对照按报告实测；接口只证明列出的有限输入。自动声明选项本身不替代业务校验。',
                    '上游教程文字与固定实现存在版本描述差异；执行器默认与参数入口按固定源码、安装版本及实际结果说明。']),
        dict(id='api-container-models', title='三种容器：执行器边界、进程边界与thread_num', lessons=['composition','executors','deployment','performance'],
             columns=['模型','执行资源','可启动配置','需要单独验证的边界'], rows=[
                 ['component_container','共享SingleThreadedExecutor','本次实际容器名与组件加载ID','一个长回调会占用该执行线程，管理请求也可能被延迟。'],
                 ['component_container_mt','共享MultiThreadedExecutor','本轮显式thread_num=2','线程数不是并发保证；仍受回调组、锁与负载影响。不是固定4线程。'],
                 ['component_container_isolated默认','每组件独立SingleThreadedExecutor及线程','本轮默认模式；管理节点另由外层执行器推进','组件仍同PID/地址空间；隔开执行器不隔离内存破坏或进程崩溃。'],
                 ['isolated的--use_multi_threaded_executor','每组件改用MultiThreadedExecutor','仅按固定源码核对该开关','本轮三容器时间线没有把此额外模式计为已运行。'],
                 ['thread_num只读参数','管理节点声明，mt入口读取','在启动时覆盖；运行时拒绝另用可观察管理入口验收','官方管理参数服务默认关闭；read_only不代表启动override也被拒绝，更不是动态线程池重配。']],
             notes=['本轮记录PID、线程和受控span；sleep/等待演示资源许可，不是实时频率、CPU独占或性能倍数证明。',
                    '卸载前取消组件自己的timer/工作并回收资源；请求已返回与任意设备处于安全状态不能画等号。'])]
    ids = {item['id']:index for index,item in enumerate(data['apiReferences'])}
    for item in additions:
        if item['id'] in ids:data['apiReferences'][ids[item['id']]]=item
        else:data['apiReferences'].append(item)
    action = next(item for item in data['apiReferences'] if item['id']=='api-action-state')
    rows = [row for row in action['rows'] if row[0] not in ('服务端终态','拒绝目标')]
    rows += [
        ['拒绝目标','GoalResponse::REJECT','GoalResponse.REJECT','accepted=false表示未接纳；不存在本次目标的已执行Result，不能把拒绝包装成ABORTED。'],
        ['服务端终态','succeed/canceled/abort(result)','succeed/canceled/abort后返回Result','终态status与Count.completed分别验收；Count没有原因字段，本轮故障原因由服务端独立日志记录。']]
    action['rows']=rows
    note='第3轮Count实验覆盖忙碌拒绝、结束后恢复及显式故障ABORTED；只用Python探针检查两种服务端，不代表已验证C++客户端或硬件停车。'
    action['notes']=list(dict.fromkeys([*action['notes'],note]))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    action, action_files = load_verified_report('count-action','examples/action_labs')
    component, component_files = load_verified_report('component-labs','examples/component_labs')
    action_tables = measured_tables(action,'count-action',1)
    component_tables = measured_tables(component,'component-labs',2)
    if len(action_tables[0]['rows'])!=10 or len(component_tables[1]['rows'])!=3:
        raise ValueError('正文需要10组Count和3种官方容器，不能用子集替代')
    review = EVIDENCE/'iteration3-source-review.json'
    if not review.is_file():
        raise ValueError('缺少第3轮独立源码/版本审查')
    review_data=json.loads(review.read_text())
    if review_data.get('approved') is not True:
        raise ValueError('独立审查尚未按明确范围通过，不能把文件存在当作通过')
    for name in ('count-action','component-labs'):
        filename=name+'-current-validation.json'
        record=review_data.get('reviewedReports',{}).get(filename,{})
        if record.get('sha256')!=hashlib.sha256((EVIDENCE/filename).read_bytes()).hexdigest():
            raise ValueError('当前报告未得到对应审查，不能复用旧结论：'+filename)
    revision = dict(meta=dict(iteration='2026-11-07-r3',sourceReviewFile=review.relative_to(ROOT).as_posix(),
                              sourceReviewSha256=hashlib.sha256(review.read_bytes()).hexdigest()),resources=primary_sources(review_data),chapters={})
    # 后面的正文只在两份完整报告通过并核对源码之后产生，避免提前宣传计划结果。
    patch = editorial_patch()
    patch.update(appendSections=[dict(title='忙碌拒绝、受控失败与恢复要形成协议闭环', paragraphs=[
        '新增action_labs沿用learning_count_interfaces的Count：target、current和completed均为无量纲计数。先对原有C++/Python服务端分别验证长目标期间第二个合法目标被拒绝，再分别走首目标取消与自然结束，最后重新发送合法目标成功，确认接纳状态恢复。每个目标用UUID区分，不能把上一个目标的反馈或取消应答当成本次结果。',
        '拒绝只发生在接纳阶段，accepted=false的目标没有开始执行，也没有自己的completed结果。GoalStatus没有REJECTED枚举；对未知UUID查得UNKNOWN及默认字段也不能解释为completed=0的业务失败。ABORTED是已接纳目标的失败终态，可以只有0步或部分业务进度；本例在第6步故障另按实际结果记录。验收分别保存接纳Future、反馈、取消应答和最终status/completed；一次Future完成不能替代其余阶段。',
        '取消应答列出目标UUID，也不强制最终一定是CANCELED。固定状态机允许CANCELING继续到SUCCEEDED、ABORTED或CANCELED，临近完成时可能发生竞态。本轮受控取消例留出剩余工作以验收CANCELED，通用客户端仍以最终status为准，不能把这种场景约束推广为协议保证。',
        '原有基础Count服务端保持原样。独立扩展包增加显式abort_after故障参数，默认关闭；达到受控计数后调用abort并释放busy，后续较短目标成功。两种语言都保留相同接口，故障仅影响合成内存计数，不操作设备。',
        'Count.Result只有completed字段，不包含原因字符串。通用ABORTED状态与完成数量来自ROS结果，具体注入原因来自服务端独立日志，二者不能混成接口字段。拒绝/取消/失败都不能证明真实电机停车；这个例子也没有验证客户端消失后任意任务的恢复策略。'], tables=action_tables),
        dict(title='Count扩展工程与有界验收的完整文件', paragraphs=[
            '以下代码与下载工程同源。先按action_labs/README构建独立扩展包并加载基础接口和新安装前缀，再运行验收；原有基础10包没有被覆盖。报告保存每例输入、UUID、状态、源码与二进制指纹和退出清理。',
            '内部等待使用单调软期限；无法抢占任意原生阻塞，父进程/外层保护另设。脚本只回收自己创建的进程，不结束其他ROS节点；两种服务端依次启动，避免同名来源不明。'],codeBlocks=source_blocks(action_files,'examples/action_labs'))],
        appendExercises=[
            dict(question='第二个目标accepted=false后，应该等待它的ABORTED结果吗？',answer='不应该。该目标没有被接纳或执行，不存在它的执行Result。应记录拒绝，并继续按第一个目标的UUID处理其反馈、取消与终态。'),
            dict(question='为何只测试busy拒绝还不能证明状态恢复正确？',answer='首目标结束后busy可能没有释放。应分别覆盖取消和自然终态，再发送新的合法目标并确认成功，才能证明这些路径允许继续服务。'),
            dict(question='Count的ABORTED结果能直接解释具体故障原因吗？',answer='通用status只能给出失败终态，completed是进度；本接口没有原因字段。注入原因要从独立日志核对，真实接口可另设计错误码和说明，不能把日志冒称Result字段。'),
            dict(question='故障参数默认关闭后，如何证明没有改坏正常合同？',answer='对扩展示例显式检查默认配置的成功路径，再启用受控故障检查ABORTED，并用后续短目标验证busy释放；原基础服务端也继续单独验收。'),
            dict(question='取消应答列出目标UUID后，最后为何仍可能SUCCEEDED？',answer='临近完成存在竞态，固定状态机也允许CANCELING转到SUCCEEDED或ABORTED。应以最终status为准；受控实验留出剩余工作得到CANCELED，不构成通用协议保证。'),
            dict(question='取消接纳和最终CANCELED都到了，是否足以证明硬件已停？',answer='只能证明该软件动作按协议进入取消终态。本例没有硬件；真实系统仍需执行端状态、驱动反馈或独立安全机制证明物理结果。')],
        appendPitfalls=['官方Fibonacci补充命令使用order/sequence，本章Count使用target/current/completed；字段与类型应成对核对。'])
    revision['chapters']['actions']=patch
    revision['chapters']['composition']=dict(appendSections=[
        dict(title='同一配置类：独立入口、组件参数与管理节点参数', paragraphs=[
            'component_labs提供完整runtime_lab_components包。ConfigComponent接收NodeOptions并转交Node，显式声明有限DOUBLE gain，无量纲、范围[0,2]；私有话题~/configured_velocity输出0.2m/s乘gain的Float64，完整话题名按本次节点名展开。独立入口和动态加载使用同一个类，合法gain=1.5应得到约0.3m/s。',
            '加载请求parameters只作用于本次组件的参数override，组件声明时读取它；容器管理节点自己的gain和组件gain是不同对象。查询本次LoadNode返回的full_node_name、unique_id，再在该节点下get/set或卸载。无效构造加载失败时不获得一个成功运行的组件，已有组件及管理容器应仍可工作。',
            '显式转发也不是复制管理节点的当前参数。本轮进程全局CLI给gain=1.8，管理节点后续改成1.2；默认组件仍取自身默认1.0，显式forward的新组件读取全局CLI的1.8，加载请求再给本地1.5时又覆盖为1.5。参数来源、覆盖顺序和运行时节点状态要分开记录。',
            'extra_arguments属于manager明确实现的装载开关。本轮固定实现只映射use_intra_process_comms与forward_global_arguments，未知键不能自动变成NodeOptions setter。默认不转发进程全局ROS参数；允许未声明参数、自动声明override和显式declare是不同策略，不能靠拼一个extra键宣称已启用。',
            '本轮严格组件对未知参数的GetParameters查询返回空values；整批查询可能失败，不能解释成逐项NOT_SET或gain=0。先用ListParameters确认声明，再分开查询合法参数并检查返回长度，运行时set未知项的拒绝另记。固定C++与Python严格参数服务都有整批失败分支；allow_undeclared与get_parameter_or另按配置/API理解。Python这个远程服务分支只核源码，未计入本轮组件实测。',
            '官方ComponentManager默认关闭管理节点自己的参数服务和参数事件发布；这不等于加载的组件也关闭参数服务。专用observable_manager显式开启管理参数服务，用来验收管理gain与只读thread_num，其可观察入口与官方标准可执行明确分别记录。'], tables=[component_tables[0]]),
        dict(title='shared single、shared mt与per-component executor的实际区别', paragraphs=[
            '同一SlowComponent与HeartbeatComponent分别加载到三种官方容器。记录PID、线程ID、回调开始/结束稳态时戳和慢回调窗口内heartbeat；相同进程内的时戳可比较，不使用节点图数量推断并发。受控等待让回调保持活跃，但不是CPU负载基准或硬实时证明。',
            '默认component_container共享单线程执行器；component_container_mt共享多线程执行器，本轮显式thread_num=2，不把旧教程文字中的4当固定线程数。默认component_container_isolated为每组件建立单线程执行器和线程，管理节点由外层执行器推进；--use_multi_threaded_executor额外模式仅核源码，没有混入本次三容器实测。',
            'isolated中的两个组件仍共享PID、地址空间和进程故障边界。它隔开执行资源，不会让堆破坏、进程崩溃或CPU资源自动隔离。需要进程故障隔离时仍应选择独立进程并验证恢复链。',
            'thread_num在管理节点声明为只读，mt入口在启动时读取；启动override和运行时修改是两条路径。官方默认管理参数服务关闭，不能把远程get/set超时当作参数拒绝；本轮使用显式开启服务的可观察入口核对描述与运行时拒绝。卸载前先停止组件自己的周期工作，回收动作按自己的所有权执行。'], tables=[component_tables[1]]),
        dict(title='完整组件包与复现脚本', paragraphs=[
            '按component_labs/README从独立目录构建包，加载本机安装前缀，再运行脚本。以下完整文件自动取自已实测源码；CMake注册、插件名、独立入口和加载命令应一起使用，不能只复制节点类而省略包描述。',
            '构造失败、参数拒绝、动态卸载和线程清理属于不同验收阶段。报告保留有限输入与事件；本轮没有测零复制、DDS共享内存、容器崩溃恢复、跨机或硬件性能。'],codeBlocks=source_blocks(component_files,'examples/component_labs'))],
        steps={'0':'先按component_labs/README构建原创组件包，在各终端加载安装环境，检查注册类型与包前缀。',
               '1':'对照同一ConfigComponent的独立入口和加载参数，检查实际节点名、gain与m/s输出；管理节点参数另查。',
               '2':'用实际返回ID检查、拒绝无效配置并卸载；先停止组件自己的周期工作，再观察资源清理。',
               '3':'分别运行三种官方容器记录PID/线程/span；只读参数使用显式开启管理参数服务的入口验收，不把默认服务缺失当拒绝。'},
        appendExpected=['独立入口与加载gain=1.5的组件得到约0.3m/s；非法构造失败后已有组件仍可查询和卸载。',
                        '从PID/线程和受控时间线区分三种容器，运行时只读拒绝使用真实参数响应确认。'],
        appendPitfalls=['标准管理节点默认没有参数服务，远程参数调用超时不能当作read_only拒绝证据。',
                        'LoadNode.extra_arguments只映射实现支持的键；未知自动声明选项不构成实际启用。',
                        'isolated默认每组件单线程执行器，组件仍共享进程地址空间和故障边界。'],
        appendExercises=[
            dict(question='给管理节点-p gain:=1.5，能证明新加载组件的gain也是1.5吗？',answer='不能。管理节点参数与LoadNode.parameters属于不同节点和入口。查询加载返回的完整组件名，在组件上检查gain与输出；显式启用全局参数转发是另一项配置。'),
            dict(question='给extra_arguments写automatically_declare_parameters_from_overrides=true一定生效吗？',answer='不能。标准manager只映射它明确支持的extra键；NodeOptions完整API不等于加载服务暴露的选项集合。要核该版本create_node_options，并检查实际声明的参数。'),
            dict(question='一次查询gain和未知名后收到空values，能用下标0继续读取gain吗？',answer='不能。严格参数服务可能整批失败，应检查返回长度、先核对已声明列表并分开查询合法名。空列表也不是gain=0或逐项NOT_SET；该行为由配置/API决定，不能只按语言猜测。'),
            dict(question='同PID的两个组件在isolated不同线程执行，能否分别承受一个组件进程崩溃？',answer='不能。它们没有变成两个进程，仍共享地址空间及进程生死。专属执行器减少调度耦合，不隔离内存破坏或进程终止。'),
            dict(question='thread_num是read_only，为何启动时还能设成2？',answer='声明时应用启动override，read_only主要约束后续参数修改。mt入口启动读取该值创建线程池；拒绝动态修改不是动态重建线程池。'),
            dict(question='官方容器ros2 param get超时，可以记为thread_num拒绝吗？',answer='不可以。应先查管理参数服务是否存在；本机默认关闭。只有收到实际设置响应且原因/状态符合，才能记为拒绝；本轮另用显式开启服务的管理入口验收。'),
            dict(question='非法gain的组件加载失败，为什么还检查已有组件与后续卸载？',answer='失败响应只说明这次构造未成功。已有实例、管理服务及资源回收仍可能受影响，需分别查询并卸载实际成功ID，形成完整配置与生命周期验收。')])
    # 具体验证摘要与复现命令在核读最终报告后补充，避免先写未经观察的数量。
    revision['chapters']['actions']['validation']=action['teachingValidation']
    revision['chapters']['composition']['validation']=component['teachingValidation']
    revision['chapters']['actions']['sourceIds']=['core-action-interface','core-cpp-action','core-py-action','core-action-demo-entry','iter3-rcl-state-map']
    revision['chapters']['composition']['sourceIds']=['core-composition','core-composable','core-executors',
        *['iter3-'+key for key in ('manager','manager-default','options','release-mt','release-isolated','cpp-parameter-service')]]
    for name,report in [('actions',action),('composition',component)]:
        revision['chapters'][name]['appendSections'][-1]['codeBlocks'].append(
            command('按本轮报告复现',report['teachingCommand'],report['teachingCommandNote']))
    target=ROOT/'source/iteration-3-revisions.json'
    target.write_text(json.dumps(revision,ensure_ascii=False,indent=2)+'\n')
    update_api_tables()
    print(json.dumps({'chapters':2,'evidenceTables':3,'completeSourceFiles':len(source_blocks(action_files,'examples/action_labs'))+len(source_blocks(component_files,'examples/component_labs'))},ensure_ascii=False))


if __name__=='__main__':
    main()
