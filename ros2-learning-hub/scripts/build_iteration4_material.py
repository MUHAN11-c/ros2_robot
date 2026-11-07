#!/usr/bin/env python3
"""把第4轮四份已审查报告接入生命周期、测试与部署章节。

输入：报告、源码SHA与对应approved审查；输出最后应用的第4覆层和API表。
时间单位、测试数和状态值来自各自报告，不把CLI聚合数量冒充独立用例。
构建时不运行ROS、不复制安装产物、不访问网络；源码/报告变化先重新核读。
"""
import hashlib
import json
from pathlib import Path
from build_iteration3_material import load_verified_report

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'validation-evidence'
ASSETS={'lifecycle':'examples/lifecycle_labs','testing-labs':'examples/testing_labs',
        'deployment':'examples/deployment_labs','testing-existing':'examples/testing_policy'}


def measured(data,name):
    file=EVIDENCE/(name+'-current-validation.json')
    tables=[]
    default_titles={'testing-labs':['受控就绪失败与CLI退出码','测试注册与细分结果的实际数量']}
    for index,original in enumerate(data['teachingTables']):
        item={key:original[key] for key in ('columns','rows','caption')}
        item['title']=original.get('title') or default_titles.get(name,[name+'实测表']*len(data['teachingTables']))[index]
        if not item['rows'] or any(len(row)!=len(item['columns']) for row in item['rows']):
            raise ValueError('教学表格不完整：'+name)
        item['rows']=[[format(value,'.6g') if isinstance(value,float) else str(value) for value in row] for row in item['rows']]
        if any(isinstance(value,float) for row in original['rows'] for value in row):
            item['caption']+=' 小数显示6位有效数字，完整数值保留在报告。'
        item.update(evidenceFile=file.relative_to(ROOT).as_posix(),evidenceSha256=hashlib.sha256(file.read_bytes()).hexdigest())
        tables.append(item)
    return tables


def blocks(records,prefix,exclude=()):
    result=[]
    for name,file in sorted(records.items()):
        if not name.startswith(prefix+'/') or file.name in exclude:continue
        language='cmake' if file.name=='CMakeLists.txt' else 'dockerfile' if file.name=='Dockerfile' else {
            '.py':'python','.cpp':'cpp','.hpp':'cpp','.h':'cpp','.xml':'xml','.json':'json',
            '.yaml':'yaml','.cmake':'cmake','.sh':'bash','.bash':'bash'}.get(file.suffix)
        if not language:continue
        description='完整原创文件与报告指纹同源，依赖及复现顺序见同目录README；输入、单位、保护期限和清理范围见中文注释。'
        if file.name=='baseline_sources.json':description='历史基线输入数据，保留原策略的已知合同缺口，只用于反例对照；推荐策略为同目录policy.py。'
        result.append(dict(label=Path(name).relative_to('examples').as_posix(),language=language,type='complete',sourceFile=name,explanation=description))
    return result


def command(data):
    return dict(label='按本轮已记录命令复现',language='bash',type='commands',
                code=data['teachingCommand'],explanation=data['teachingCommandNote'])


def exercise(question,answer):
    return dict(question=question,answer=answer)


def api_tables():
    file=ROOT/'source/api-reference.json';data=json.loads(file.read_text())
    additions=[
        dict(id='api-lifecycle-outcomes',title='生命周期：回调返回、请求应答、状态与资源',lessons=['lifecycle','eco-nav2-stack','deployment'],
             columns=['阶段','回调/协议','需要查询的证据','本轮范围'],rows=[
                 ['configure','SUCCESS→inactive；FAILURE→unconfigured','GetState、候选资源释放与可再次配置','假资源完整往返和配置失败后重试；不打开设备。'],
                 ['activate','SUCCESS→active；FAILURE→inactive','发布者is_activated、资源快照与新消息','失败保留已配置资源，再激活成功。'],
                 ['ERROR/受控异常','进入errorprocessing并调用on_error','原始转换应答与最终恢复状态分别查','on_error SUCCESS恢复unconfigured，原ChangeState仍可能false。'],
                 ['on_error','SUCCESS→unconfigured；FAILURE/ERROR→finalized','GetTransitionGraph、回调事件和清理结果','标准异常转换路径按本机实现实测；不推广任意崩溃。'],
                 ['LifecyclePublisher','is_activated控制发送','有限窗口内新序号、发布者状态','普通timer与普通诊断发布仍可运行，业务工作需显式门控。'],
                 ['shutdown/finalized','生命周期终结，不等于ROS Context已关闭','同实例可用转换、资源与普通接口','本例finalized后仍有普通诊断，直至进程退出。']],
             notes=['成功返回、最终状态、消息与资源是不同证据；状态标签不会自动处理任意文件、线程或设备。',
                    '本轮没有穷尽cleanup/shutdown各失败返回、未知原生异常、跨节点管理器或硬件状态。']),
        dict(id='api-testing-evidence',title='测试入口：就绪、执行、XML与验收',lessons=['testing','workspace','deployment'],
             columns=['入口','实际含义','需保留的证据','误读边界'],rows=[
                 ['ReadyToTest','允许活动测试开始','另等业务消息/状态/明确就绪','不等于ROS发现或应用已经就绪。'],
                 ['colcon test默认','运行已注册测试','命令RC、CTest输出、细分JUnit','本机受控断言失败仍可RC0，不能单用它验收。'],
                 ['--return-code-on-test-failure','让已记录测试失败影响CLI状态','与同次XML失败原因、数量对应','参数行为按安装版本与插件核对；缺结果另查。'],
                 ['colcon test-result','汇总现有结果','本次新生成路径、失败/错误/跳过与预期数','空目录也可能CLI0；旧XML和零用例不是功能通过。'],
                 ['CTest包装与细分JUnit','不同层次的结果','包装项与真正testcase分别统计','3注册、13细分、16聚合不是三套独立功能覆盖。'],
                 ['post_shutdown_test','进程关闭后的测试阶段','被测进程退出码与回收','消息正例和正常退出都不证明硬件或任意中断清理。']],
             notes=['受控失败应匹配预期业务断言；NoMatchingProcess等夹具错误不能冒充缺READY反例。',
                    '旧4项测试通过与新合同反例暴露缺口可同时成立；测试数量不能替代输入范围。']),
        dict(id='api-deployment-boundaries',title='部署清单：链接、环境、进程与容器边界',lessons=['deployment','workspace','composition'],
             columns=['对象','记录什么','可以证明什么','仍需另证'],rows=[
                 ['安装前缀','普通文件SHA、链接文本/目标与边界','本次输入的内容与外部依赖','保留symlink复制后仍可能依赖原source/build/underlay。'],
                 ['环境与包','显式allowlist、目标包及underlay来源','本次可追溯配置','环境清单不是依赖闭包或包源锁文件。'],
                 ['校验/归档','同范围文件和链接逐项比对','传输/复制保持哪些字节与指向','不证明迁移、ABI、硬件或实际可运行。'],
                 ['shell source+exec','实际PID、可执行映射与信号退出','宿主正例的进程替换/TERM处理','exec ros2 run替换的是CLI；容器PID1和叶子节点分别查。'],
                 ['Docker默认CMD','镜像内固定前缀的直接节点入口','代码静态结构及预期信号路径','本轮无Docker命令，镜像构建、docker stop与跨容器通信未运行。']],
             notes=['本轮审计只读显式前缀/允许路径并有扫描上限，不扫描用户凭据或无限展开链接。',
                    '宿主exec信号正例与Docker验收分开；安装复制副本未执行，更未冒称跨机成功。'])]
    indices={item['id']:i for i,item in enumerate(data['apiReferences'])}
    for item in additions:
        if item['id'] in indices:data['apiReferences'][indices[item['id']]]=item
        else:data['apiReferences'].append(item)
    file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    reports={};files={}
    for name,prefix in ASSETS.items():
        reports[name],files[name]=load_verified_report(name,prefix)
        for file in (ROOT/prefix).rglob('*'):
            if any(part.startswith('.') or part in ('__pycache__','build','install','log') for part in file.relative_to(ROOT/prefix).parts):continue
            if file.is_file() and (file.suffix in ('.json','.yaml','.sh','.bash') or file.name=='Dockerfile') and file.relative_to(ROOT).as_posix() not in files[name]:
                raise ValueError('运行输入/脚本尚无对应指纹：'+str(file))
    if reports['testing-existing'].get('unitOnly') is not False:
        raise ValueError('原例报告必须包含实际ROS集成，不能用unit-only替代')
    review_file=EVIDENCE/'iteration4-source-review.json';review=json.loads(review_file.read_text())
    if review.get('approved') is not True:raise ValueError('第4轮独立审查尚未通过')
    for name in ASSETS:
        filename=name+'-current-validation.json'
        expected=review.get('reviewedReports',{}).get(filename,{}).get('sha256')
        if expected!=hashlib.sha256((EVIDENCE/filename).read_bytes()).hexdigest():
            raise ValueError('审查未绑定当前报告：'+filename)
    resources=review['textbookResources']
    cited_lessons={lesson for item in resources for lesson in item.get('lessons',[])}
    if not {'lifecycle','testing','deployment'}<=cited_lessons or any(not item.get('url') or not item.get('id') for item in resources):
        raise ValueError('关键一手出处须对应三章真实主张，不以链接条数替代支持范围')
    sources={'lifecycle':['core-lifecycle','core-demos'],'testing':['core-testing','core-colcon','core-doctor'],
             'deployment':['extra-docker','eco-rosdistro']}
    for item in resources:
        for lesson in item.get('lessons',[]):
            if lesson in sources:sources[lesson].append(item['id'])
    revision=dict(meta=dict(iteration='2026-11-07-r4',sourceReviewFile=review_file.relative_to(ROOT).as_posix(),
                            sourceReviewSha256=hashlib.sha256(review_file.read_bytes()).hexdigest()),
                  resources=resources,chapters={})
    lifecycle=reports['lifecycle'];testing=reports['testing-labs'];deployment=reports['deployment'];legacy=reports['testing-existing']
    revision['chapters']['lifecycle']=dict(sourceIds=sources['lifecycle'],validation=lifecycle['teachingValidation'],appendSections=[
        dict(title='假资源实测：回调返回不等于最终恢复状态',paragraphs=[
            '新增lifecycle_labs以真实LifecycleNode管理合成资源，不打开硬件。configure先申请候选资源，校验成功再提交；FAILURE释放本次候选并保留历史配置代数，重新配置可以成功。资源快照、回调事件和GetState分别读取，不能只凭一条成功日志判断资源已提交。',
            'ERROR或受控标准异常进入错误处理。on_error返回SUCCESS可恢复unconfigured，但最初ChangeState仍可能报告false；恢复成功与原请求成功是不同结果。handler返回FAILURE、ERROR或本例受控异常时走finalized，具体路径以安装版本和实际GetTransitionGraph为准。',
            'activate FAILURE后回到inactive，仍持有已配置资源；错误处理或shutdown则由本例显式撤销发布者与资源。状态机不负责释放你的任意外部资源，也不会自动回滚应用的副作用。本轮非法转换用label请求并查询可用label，没有把任意numeric id的行为算入已测范围。'],tables=measured(lifecycle,'lifecycle')),
        dict(title='普通回调、发布门控与进程生死分别观察',paragraphs=[
            '本例构造时创建50ms普通timer，持续递增无量纲序号并发布普通诊断；LifecyclePublisher按实际激活状态发送受管输出。inactive或unconfigured时普通计数继续，有限窗口内受管新消息为零；active窗口两种消息都能观察。请求周期和一次窗口计数不等于实时频率保证。',
            'finalized终结的是本实例的生命周期转换。本例普通timer、快照服务和Context仍可存在，直到进程被关闭；同实例不能再次configure，需要管理者销毁并新建。不要把生命周期shutdown、ROS Context关闭、操作系统进程退出或设备停车当同一事件。',
            '转换响应到达与DDS中旧样本排空也不同。脚本用序号和有限观察窗口记录新消息，并将资源清理、回调关闭及父进程中断作为各自范围，不把“未看到”扩为任意负载下永远没有。']),
        dict(title='生命周期完整工程与复现',paragraphs=['完整CMake/package、节点和driver与实测指纹一致；按README构建独立包，不覆盖已有示例。'],codeBlocks=blocks(files['lifecycle'],ASSETS['lifecycle'])+[command(lifecycle)])],appendExercises=[
            exercise('on_error恢复到了unconfigured，原ChangeState=false是否矛盾？','不矛盾。原转换失败与后续错误恢复分别记结果；查询最终状态、回调事件和资源，不能用一个success布尔替代全部证据。'),
            exercise('inactive普通tick继续增长能证明停用失败吗？','不能。普通timer和诊断未必受生命周期自动控制，应按节点合同另行取消或门控；受管发布者与资源状态分别检查。'),
            exercise('configure失败后为什么还再次configure并核资源计数？','状态回到unconfigured不证明候选资源已释放；重试、申请/释放次数与配置代数能发现旧占用或部分提交。'),
            exercise('finalized后进程仍在运行，能原地再次configure吗？','不能把进程存在当作生命周期重新可用；本实例协议已终结。需要销毁重建，普通接口是否还活另按实现观察。'),
            exercise('LifecyclePublisher停发是否自动停止采样线程？','不会。发布门控与普通回调/资源工作是不同机制；停止工作与等待线程退出必须由实现负责。'),
            exercise('0.3秒内没看到新消息能证明所有网络下永远停发吗？','不能。结论限定输入、序号筛选、观察窗口和中间件；残留样本、调度和跨机条件需要另测。')])

    policy_blocks={'0':dict(label='testing_policy/policy.py',sourceFile='examples/testing_policy/policy.py',
                           explanation='严格整数纳秒与有限速度的修订策略；非法配置抛ValueError，非法运行观测归零，幅值及时基来源由调用者约束。'),
                   '1':dict(label='testing_policy/test_policy.py',sourceFile='examples/testing_policy/test_policy.py',
                           explanation='31项参数化测试以本次JUnit为准，包含一个纳秒边界、畸形类型和大整数精度；不把有限样本称全集覆盖。')}
    revision['chapters']['testing']=dict(sourceIds=sources['testing'],validation=legacy['teachingValidation']+' '+testing['teachingValidation'],sections={
        '1':dict(paragraphs=[
            '策略速度单位m/s，时刻和期限单位ns。修订合同限定内置整数纳秒，bool不作时刻；正整数期限是配置，非法时抛ValueError。缺失、格式错误、未来或过期运行观测返回0.0；速度需为可表示的有限int/float，bool及字符串不作速度。',
            'age==timeout仍有效，超过一个纳秒才归零。整数相减保留精度，不先转float或舍入；带符号同一时基也按整数年龄处理。函数不识别不同时间域、不限制速度幅值，更不证明真实制动。旧4项通过而NaN时戳/期限绕过比较的基线已保留，新增31项验证明确合同。'],codeBlocks=policy_blocks),
        '2':dict(appendParagraphs=['这里保留的原talker完整文件已在本机域230/LOCALHOST实际运行：活动阶段观察消息，post-shutdown核退出，两项通过。它使用固定命名空间，只按独立专用域范围验收；下方新包再演示完整注册与受控失败。']),
        '5':dict(paragraphs=[
            '关键路径应验证缺失输入、参数非法、消息过期、进程退出和时间异常，故障要对应具体断言。先用假设备或受控输入明确预期，再核失败原因，不能把任意异常都当预期反例。',
            '旧原例和新增注册包的实际运行分开记录，数值、消息、就绪、XML与退出分别验收。源码能解析或构建成功不能替代这些行为证据；本轮没有硬件或安全制动测试。'])},appendSections=[
        dict(title='旧测试全过，为什么新反例仍暴露缺口？',paragraphs=[
            '第3轮原policy的四项pytest先实际通过。它只对speed做有限性检查，NaN的now/last/timeout参与比较时，两边判断都可能为false，于是过期判断没有阻断输出；bool和字符串也没有完整输入策略。六个新合同反例保留原表现，说明绿色数量必须结合输入范围。',
            '新policy按显式合同验证配置与运行数据；31项和原talker两阶段分别保存JUnit。基线JSON用于反例，不能当推荐策略；修订31项同样不代表任意速度、时钟或设备已验证。'],tables=measured(legacy,'testing-existing'),
             codeBlocks=blocks(files['testing-existing'],ASSETS['testing-existing'],exclude=('policy.py','test_policy.py'))+[command(legacy)]),
        dict(title='完整注册包：业务就绪、受控失败与结果清单',paragraphs=[
            '新增testing_labs是独立ament_cmake包，以差速轮速合同、消息解释和真实软件进程验证gtest、pytest与launch_testing的分工。输入速度/角速度和几何单位在源码中定义，实测话题输出与改零输入分别检查；不是只复制实现公式再比较一次。',
            'ReadyToTest只放行测试阶段，业务就绪需要实际条件。受控变体保留启动标记而隐藏READY，确保失败来自预期就绪断言；早期NoMatchingProcess夹具错误与修正过程原样保存，未冒充同一种业务失败。',
            '本机正常注册3个CTest，细分JUnit为4+7+2=13；test-result还汇总3个包装项，显示16。一次内部失败也可被包装层再次计数。把注册、细分和聚合分开，不能把16称为16种独立功能验证。',
            '受控缺READY时默认colcon test可退出0，但同次细分XML失败、test-result退出1；启用return-code-on-test-failure后测试CLI也退出1。空结果查询CLI0仍没有执行证据，验收需要本次新XML、预期数量及失败/错误/跳过，不单看一行finished。'],tables=measured(testing,'testing-labs')),
        dict(title='完整测试工程与构建/运行命令',paragraphs=['正常与故障变体使用各自/tmp构建和结果目录，保留日志/版本/清理，最后的正常结果与故障结果不覆盖混用。'],codeBlocks=blocks(files['testing-labs'],ASSETS['testing-labs'])+[command(testing)])],appendExercises=[
            exercise('四项测试通过后，为何NaN时戳仍可能让旧策略输出速度？','旧测试未覆盖该输入，NaN比较不按普通大小关系进入过期分支。先定义整数纳秒合同，再验证非法运行数据与非法配置的各自策略。'),
            exercise('3注册、13细分、16聚合能相加成32个用例吗？','不能。这些是结果层次的重复包装，应保留注册项和真实testcase的对应关系；聚合不是新增覆盖。'),
            exercise('缺READY反例因NoMatchingProcess异常失败，能算就绪断言有效吗？','不能。那是夹具没有匹配到进程，需独立启动标记与正确目标，再证明预期业务断言失败。'),
            exercise('默认colcon test为0，test-result为1，该采用哪个作验收？','结合当次XML、预期数量和失败原因。可启用return-code-on-test-failure让CLI反映失败，但仍检查无结果、跳过和旧XML。'),
            exercise('空结果目录查询返回0，是否已经通过？','没有测试执行证据，应按预期用例数拒绝验收。CLI正常返回只说明查询本身完成。'),
            exercise('为什么旧talker正例与新注册包分别记录？','旧文件验证的是它自己的消息和退出路径；新包验证注册、物理合同和受控失败。一个通过不能替代另一个源码/配置的行为。')])

    annotated=json.loads((ROOT/'source/code-annotations.json').read_text())['chapters']['deployment']['sections']['2:0']['code']
    old='CMD ["ros2", "run", "hub_component", "hub_talker_node"]'
    if annotated.count(old)!=1:raise ValueError('Docker原始CMD已变化，先核对覆层位置')
    docker=annotated.replace(old,'# 镜像内使用固定merge-install前缀，直接启动CMake生成的节点入口。\n# shell exec后是节点本身；本例Docker镜像尚未构建，停机仍需按下方计划验收。\nCMD ["/work/install/lib/hub_component/hub_talker_node"]')
    entrypoint='''#!/usr/bin/env bash
# 输入：可信的ROS/应用setup脚本与命令argv；两个绝对前缀是Dockerfile内约定。
# 输出：exec目标的stdout/stderr和退出状态；不构建镜像或产生归档摘要。
# 顺序：启用错误退出→加载ROS underlay→加载应用overlay→替换当前shell。
# source末尾的--传给setup脚本，避免它把应用argv当作自身选项；返回后原argv保留。
set -e
source /opt/ros/jazzy/setup.bash --
source /work/install/setup.bash --
# exec只替换成指定命令；默认CMD直接到节点，自定义包装器的信号合同需另验收。
# Docker构建/停机未运行，宿主source+exec正例的范围独立记录。
exec "$@"
'''
    revision['chapters']['deployment']=dict(sourceIds=sources['deployment'],validation=deployment['teachingValidation'],sections={
        '2':dict(codeBlocks={'0':dict(code=docker,explanation='完整教学Dockerfile使用镜像内固定/work/install前缀与直接节点CMD；没有把宿主exec测试当Docker构建/停机已通过。'),
                             '1':dict(code=entrypoint,explanation='入口只加载可信环境并exec命令，输出来自目标stdout/stderr与退出状态；镜像内路径前提和自定义包装器信号边界已写明。')}),
        '3':dict(paragraphs=[
            '镜像标签可能变化，应记录实际仓库摘要、平台、后续apt来源与最终产物。固定基础摘要也没有自动固定所有软件包解析；保留结果、包清单和配置能说明运行的具体输入。',
            '下列Docker步骤仍待执行，需核对PID1、叶子节点、停止信号、退出码与资源。exec通用命令只替换到该命令；默认CMD已直达固定前缀的节点。宿主source+exec正例单独实测，不能替代Docker内运行、跨容器或硬件验收。'])},appendSections=[
        dict(title='安装目录审计：复制成功不等于自包含',paragraphs=[
            '新增deployment_labs只读显式安装前缀，记录普通文件SHA、符号链接文本/目标、允许路径边界和包来源。只收集有限环境allowlist，不扫描家目录或凭据；扫描数量、文件大小和链接解析有上限，未展开部分明确列出。',
            '真实symlink-install前缀及保留链接的自建/tmp副本分别审计。副本可保持文件SHA和链接文本一致，却仍指向原source、build和underlay；原目录存在时看起来正常，不代表复制到另一台机器仍可用。本轮没有移走原目录，也没有执行复制产物。',
            '安装文件齐全、依赖闭包、ABI、架构、驱动和运行配置是不同证据。审计器输出是可追溯清单，不是可运行性认证；Docker示例采用正常merge-install，也仍要考虑underlay和动态库。'],tables=measured(deployment,'deployment')),
        dict(title='入口与信号：宿主正例和Docker计划分开',paragraphs=[
            'entrypoint先加载ROS与应用环境，再exec默认节点。直接节点正例跟踪同一PID完成shell到可执行的替换，只向该PID发送TERM，核对退出和后代；该结果限定本机原安装前缀，复制产物没有运行。',
            'exec ros2 run替换的是CLI，叶子节点仍由它创建。终端Ctrl+C进程组与Docker发给PID1的停机信号不同，固定CLI源码中未见TERM转发不能替代实际容器实验；这里通过直接默认CMD减少一层包装，保留Docker未验证边界。',
            '如果自定义命令重新引入包装器，应明确其信号、等待与清理合同。进程退出也不证明设备停车；镜像归档校验与宿主TERM正例不扩大为跨机部署或真实驱动已验收。']),
        dict(title='只读审计与宿主信号实验的完整文件',paragraphs=['按README指定目标前缀和允许根，仅操作自建/tmp副本；不要把工作区中的开发链接当发布工件。'],codeBlocks=blocks(files['deployment'],ASSETS['deployment'])+[command(deployment)])],appendExercises=[
            exercise('复制install后SHA相同，为什么换机仍可能失败？','保留的链接仍可外指原source/build/underlay，当前机器可能偶然满足它们；还要核对依赖、ABI、配置并实际运行。'),
            exercise('环境allowlist和包版本清单等于完整锁文件吗？','不等于。它记录本次可见输入，未自动固定软件源、依赖闭包、编译选项、驱动和平台。'),
            exercise('exec ros2 run后PID1一定是叶子节点吗？','exec替换到ROS CLI，节点通常由CLI另建；需要直接入口或明确信号转发方案，并核对真实PID与退出。'),
            exercise('宿主TERM正例能证明docker stop已完成清理吗？','不能。Docker的PID1、命名空间、停机超时和资源边界不同，本轮Docker未运行，需独立验收。'),
            exercise('为什么审计副本保留外链而不先删原source/build？','为了只读证明依赖关系，避免破坏原工作空间。外链存在已足以说明不是自包含，运行迁移另设环境。'),
            exercise('检查器达到扫描上限后可以输出完整清单吗？','不能，应标出未扫描/未哈希范围及原因。部分清点不是全部依赖或可运行性证明。')])
    target=ROOT/'source/iteration-4-revisions.json'
    target.write_text(json.dumps(revision,ensure_ascii=False,indent=2)+'\n')
    api_tables()
    print(json.dumps({'chapters':3,'evidenceTables':sum(len(reports[name]['teachingTables']) for name in ASSETS)},ensure_ascii=False))


if __name__=='__main__':main()
