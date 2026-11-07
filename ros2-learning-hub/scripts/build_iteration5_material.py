#!/usr/bin/env python3
"""把第5轮rosbag真实报告与独立审查接入两章；构建不运行DDS。

输入：两份通过的报告、全部原创输入指纹与已绑定报告SHA的独立审查。
输出：iteration-5-revisions覆层及原rosbag API表的幂等修订。
原参考源码、旧实验报告和旧注释基线保持独立；源/证据漂移时停止生成。
"""
import hashlib
import json
from pathlib import Path
from build_iteration3_material import load_verified_report

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'validation-evidence'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(title, columns, rows, caption, report):
    if not rows or any(len(row) != len(columns) for row in rows):
        raise ValueError('实验表缺行或列数不一致：' + title)
    return dict(title=title, columns=columns, rows=[[str(x) for x in r] for r in rows], caption=caption,
                evidenceFile=report.relative_to(ROOT).as_posix(), evidenceSha256=digest(report))


def block(filename, explanation):
    return dict(label='bag_labs/' + filename, type='complete',
                language='python' if filename.endswith('.py') else 'yaml',
                sourceFile='examples/bag_labs/' + filename, explanation=explanation)


def main():
    data, files = load_verified_report('bag', 'examples/bag_labs')
    cli, _ = load_verified_report('bag-cli-boundaries', 'examples/bag_labs')
    for path in (ROOT / 'examples/bag_labs').iterdir():
        if path.is_file() and path.suffix in ('.yaml', '.md') and path.relative_to(ROOT).as_posix() not in files:
            raise ValueError('实验输入/说明尚无指纹：' + path.name)
    review_path = EVIDENCE / 'iteration5-bag-source-review.json'
    review = json.loads(review_path.read_text())
    if review.get('approved') is not True:raise ValueError('需要第5轮独立审查通过')
    for name in ('bag-current-validation.json', 'bag-cli-boundaries-current-validation.json'):
        if review.get('reviewedReports', {}).get(name, {}).get('sha256') != digest(EVIDENCE / name):
            raise ValueError('审查未绑定当前报告：' + name)
    resources = review['textbookResources']
    if not {'time-bag', 'eco-data-observability'} <= {l for r in resources for l in r.get('lessons', [])}:
        raise ValueError('缺少对应两章真实主张的一手出处')
    records = {r['name']: r for r in data['recordings']}
    plays = data['playbacks']
    if set(records) != {'system_sqlite', 'sim_mcap', 'late_volatile_mcap'} or len(plays) != 2:
        raise ValueError('运行配置变化，应先核读新范围')
    if not all(r.get('passed') for r in [*records.values(), *plays]) or not cli.get('passed'):
        raise ValueError('不完整的实际运行')
    if data['parameters']['inputCount'] != 6 or data['cleanup']['escalatedSignals']:
        raise ValueError('输入或退出范围变化，先审核正文')
    report = EVIDENCE / 'bag-current-validation.json'
    inp, derived, static = '/bag_lab/input', '/bag_lab/derived', '/bag_lab/static'
    simulation = records['sim_mcap']
    gate_rows = []
    for phase in simulation['beforeClock']:
        sent = phase['sentSequences']
        written = sum(r.get('sequence') in sent for r in simulation['readback']['records'] if r['topic'] == inp)
        gate_rows.append([phase['stage'], '/'.join(map(str, sent)), '/'.join(map(str, phase['dataSubscriptions'])), written])
    gate = table('正值时钟前：数据订阅与最终录入分别查',
                 ['阶段', '发送的input序号', '数据订阅input/derived/static', '最终录到这组input条数'], gate_rows,
                 '两个有限阶段中，三个数据订阅都尚未建立。正值10s后才等匹配并发送0..5，关闭后读回六条；这不是订阅已接收后再丢弃的证明。', report)
    recording_rows = []
    for r in records.values():
        counts = r['readback']['counts']
        recording_rows.append([r['name'], r['storage'], 'ROS软件钟' if r['useSimTime'] else '接收时间',
                               'transient_local' if r['requestCachedStatic'] else 'volatile',
                               counts.get(inp, 0), counts.get(derived, 0), counts.get(static, 0), r['readback']['metadataCount']])
    recording = table('录制读回：缓存请求与消息数',
                      ['场景', '插件', '记录时基', '静态订阅持久性', 'input', 'derived', 'static', '元数据总数'], recording_rows,
                      '每组同样六条位置、六条派生序号，静态状态在录制器前仅发一次且发布者存活。不同时间录制，不作插件速度/大小性能对照。', report)
    play_rows = []
    for p in plays:
        play_rows.append([p['name'], len(p['received'][inp]), len(p['received'][derived]), len(p['received'][static]),
                          p['publishers']['/clock'], len(p['clocksNs']), str(p['observerRosTimeNs']) + ' ns'])
    playback = table('暂停就绪后回放：筛选、来源与ROS时间',
                     ['场景', 'input', 'derived', 'static', '/clock发布者', '观测clock条数', '消费者最终ROS时间'], play_rows,
                     f"Resume前实际等待选定订阅匹配并核唯一来源，暂停数据为零。{len(plays[1]['clocksNs'])}条clock只属于本次40Hz/2倍速的有限运行，不是固定频率或确定性保证。", report)
    fields = data['storageFields']
    field_rows = []
    for name, item in fields['storages'].items():
        sent = item['messages'][0]['publishTimeNs'] if name == 'mcap' else '无单独发送时间列'
        field_rows.append([name, fields['headerNs'], item['readback']['records'][0]['receivedNs'], sent,
                           'topic/bytes/recv三元组'])
    storage_table = table('同一载荷：Header、recv与send的实际保存',
                          ['插件', 'Header ns', 'recv/logTime ns', 'send/publishTime ns', 'Python read_next可见'], field_rows,
                          '四参数Writer显式输入Header=7s、recv=10s、send=9s；SQLite只读schema/数据和MCAP无分块Message字段分别检查。这些时间差不是网络测量。', report)
    validation = ('2026-11-07在本机Jazzy rosbag2 ' + data['versions']['rosbag2_transport'] +
                  '、独立域231/LOCALHOST真实运行：3组CLI录制/关闭读回、2组暂停就绪后CLI回放及双后端显式字段探针通过；' +
                  '原始记录计数13/13/12，筛选回放6/0/0，常规自建节点/进程清理通过。' +
                  '6项帮助/非法参数及相对新路径双后端另验收；失败历史保留。未运行GUI海龟、真实传感器、Foxglove、tracing、压缩/性能/恢复、父中断注入或完整仿真。')
    command = dict(label='运行完整录制/读回/回放实验', language='bash', type='commands', code='''# 输入：Jazzy及两个存储插件；输出在独立/tmp目录，不连接硬件。
source /opt/ros/jazzy/setup.bash
# 正常由有限输入和单调期限退出；外层timeout只作最后防护。
timeout --signal=INT --kill-after=8s 100s python3 examples/bag_labs/record_replay_lab.py
# 用本次报告bagDirectory替换路径；仅只读已停止录制的小包。
python3 examples/bag_labs/inspect_bag.py /tmp/本次实验/sim_mcap --storage mcap
''', explanation='在教材目录执行；依赖、字段单位、输出、失败历史及未覆盖边界见bag_labs/README。默认不覆盖工作区验证报告。')
    revision = dict(meta=dict(iteration='2026-11-07-r5', sourceReviewFile=review_path.relative_to(ROOT).as_posix(),
                              sourceReviewSha256=digest(review_path)), resources=resources, chapters={})
    # 仅修正实际不含--clock的三个命令旁注；保持原有turtlesim练习未运行标记。
    annotated = json.loads((ROOT / 'source/code-annotations.json').read_text())['chapters']
    wrong = '# 重放记录的数据；--clock发布回放时钟，依赖节点需use_sim_time。先停同话题实时发布者，防止双来源混入。'
    correct = '# 重放选定消息；此命令未请求生成/clock。先停同话题实时输入源，避免竞争。'
    def fixed(chapter, position, field='sections'):
        code = annotated[chapter][field][position]['code']
        if code.count(wrong) != 1:raise ValueError('原命令旁注位置变化，应先核读')
        return code.replace(wrong, correct)
    def input_only(code, directory):
        # 原expanded中的一处已筛选，快捷入口尚未筛选；禁止重复追加同一个选项。
        lines = code.splitlines()
        for index, line in enumerate(lines):
            if line.startswith('ros2 bag play ' + directory) and '--topics' not in line:
                lines[index] = line + ' --topics /turtle1/cmd_vel'
        return '\n'.join(lines)
    # 保留前轮真实timer窗口，仅纠正其末段“未录放”的旧本轮措辞。
    clock_paragraphs = list(json.loads((ROOT / 'source/iteration-revisions.json').read_text())['chapters']['time-bag']['appendSections'][0]['paragraphs'])
    clock_paragraphs[-1] = ('海龟练习仍只回放cmd_vel，保留turtlesim为pose唯一来源；GUI流程尚未执行。第5轮下方已用标准合成消息实际录制、读回并筛选回放，验证其自身字段、计数和时钟，不把它称为海龟轨迹或完整算法重现。')
    sources = {}
    for name in ('core', 'ecosystem'):
        for c in json.loads((ROOT / 'source' / (name + '.json')).read_text())['chapters']:
            if c['id'] in ('time-bag', 'eco-data-observability'):sources[c['id']] = c['sourceIds']
    for lesson in sources:
        sources[lesson] = list(dict.fromkeys(sources[lesson] + [r['id'] for r in resources if lesson in r.get('lessons', [])]))
    revision['chapters']['time-bag'] = dict(sourceIds=sources['time-bag'], validation=validation + ' 既有软件clock/timer三阶段结果仍见前轮报告，本轮未重复。',
        commands={'1': dict(code=input_only(fixed('time-bag', '1', 'commands'), 'turtle_session'))},
        sections={
            '1': dict(paragraphs=[
                '消息Header.stamp、录制接收时间与中间件source发送时间是三项不同证据。按本机Linux/Jazzy实现，普通录制取MessageInfo.received_timestamp与source_timestamp；--use-sim-time分支把接收记录时间改为节点ROS时间。录制器不自动解析任意消息Header，也不能据记录起止时刻反推采样同步精度。',
                'use_sim_time是录制节点自己的配置。当前实现先wait_until_started，再建立数据订阅；ROS Clock.started要求当前值严格大于零，所以“收到了首条/clock”若其值恰为零，仍不放行。门前易失样本没有被订阅，之后不会自动补录；仍存活的transient_local发布者则可能在匹配后提供缓存，二者不能混为同一种丢包。']),
            '2': dict(codeBlocks={'0': dict(code=input_only(fixed('time-bag', '2:0'), 'turtle_trial'))}),
            '5': dict(paragraphs=[
                '可复查实验还包括代码提交、软件包/接口版本、参数、地图、标定、启动命令、时钟来源和初始状态。bag不自动封存固件、模型权重、外部服务或随机种子。同主题输入能够重放，不等于整个算法或硬件系统按同样行为重现。',
                '先查实际消息、类型与数量，再查来源/QoS、时钟/TF，最后比较新计算的输出。循环或跳转可令时间倒退，需要按算法合同清理历史状态。旧turtlesim步骤保留为未运行练习；下方软件实验有独立实测证据。']),
            '6': dict(paragraphs=clock_paragraphs)},
        appendSections=[
            dict(title='真实录制：零值clock仍不是已启动时钟', paragraphs=[
                'record_replay_lab启动独立CLI录制器。MCAP软件时间正例先发100/101而不发clock，再只发零clock并发200/201；两个有限阶段数据订阅均为零。正值10秒后等三个数据端点出现，才发送0..5；关闭读回只含这六个input，没有把之前四条补录。',
                '每个有效Header从1000秒按10ms推进，记录ROS时间从10秒按250ms推进；原Header完整保留。此输入故意区分时间，不代表真实传感器存在990秒延迟。等待、总期限与观察窗口用monotonic，不会随软件钟暂停而失去检查。'], tables=[gate]),
            dict(title='筛选回放：让输入与派生输出各有责任', paragraphs=[
                '先关闭录制器、只读检查并销毁全部原发布者，再核图上input/derived/static/clock都没有发布者。播放器start-paused，等待实际订阅匹配与Resume服务，确认暂停未发数据后继续。端点存在、QoS已匹配、已收消息和进程退出分别记录。',
                'SQLite完整回放得到6/6/1，但未加--clock；use_sim_time消费者仍为零，Header不会自动驱动ROS时钟。MCAP只筛选input并显式--clock 40、--rate 2.0，实际收到6/0/0与唯一clock来源。新的计算模块若要重算derived，应自行发布新输出；本实验只验数据责任，不冒称已经运行了该算法。',
                '快照与安装包都标0.26.11，Player会话结束是否取消clock timer仍有补丁差异。这里实际测的是自然退出的CLI，不推广到Player节点保活或嵌入式会话。原始采集clock、播放器产生的clock与外部仿真器也须分开，不能靠选项替你关闭外部来源。'], tables=[playback]),
            dict(title='完整有界录放工程与配置', paragraphs=['下面driver与两份QoS输入直接来自实测源码；只读工具和字段探针在数据诊断章给出，全部同属bag_labs下载目录。'], codeBlocks=[
                block('record_replay_lab.py', '三个录制与两个暂停回放，记录失败、源码指纹和有限清理；父中断注入仍未运行。'),
                block('qos_transient.yaml', '静态状态请求可靠/瞬态本地/深度1，发布者必须实际提供匹配缓存。'),
                block('qos_volatile.yaml', '故意请求易失历史的受控反例；相容不等于请求旧样本。'), command])],
        appendExercises=[
            dict(question='录制器收到值为零的/clock，为什么仍没建立数据订阅？', answer='本版等待Clock.started；当前值须严格大于零才放行。检查源码版本、clock值和实际数据端点，不能只看是否见过一条clock；本实验没有另外注入负时间。'),
            dict(question='Header=1000秒而bag记录时间=10秒，能直接说网络延迟990秒吗？', answer='不能。它们可能来自不同时间域，本实验还故意指定不同值。先说明每个时戳来源/单位/校时条件，再定义可比较的延迟。'),
            dict(question='启用use_sim_time后回放收到带Header消息，ROS时间为何还是零？', answer='Header是消息字段，不会自动发布/clock。需要明确时钟来源及消费者设置；本例未加--clock的回放真实观察ROS时间保持零。'),
            dict(question='重算派生结果时为何只回放input？', answer='避免原bag派生结果与新算法同时占用同名输出。先停止实时输入、筛选需要的主题，再区分参考输出与新结果并按算法合同比较。')])
    revision['chapters']['eco-data-observability'] = dict(sourceIds=sources['eco-data-observability'], validation=validation,
        sections={'2': dict(codeBlocks={'2': dict(code=fixed('eco-data-observability', '2:2'))})},
        appendSections=[
            dict(title='存储实测：两个时间字段不等于Header', paragraphs=[
                'storage_fields把同一bytes写进两个插件：Header=7秒、recv=10秒、send=9秒。MCAP原始Message的logTime/publishTime保存10/9秒；当前SQLite messages只有id/topic_id/timestamp/data，保存接收10秒。格式差别除了性能和工具兼容，还包括这一版本的字段保留能力。',
                'Python SequentialReader.read_next返回topic、bytes、recv三元组，不能凭它声称已经取到send。SQLite用只读SQL另核schema；MCAP只在本例noChunking单消息小文件内按v0结构核字段。普通大bag、分块/压缩仍使用正式库；本例不作通用解析器、磁盘恢复或跨版本schema保证。',
                '这些值由Writer四参数显式指定，其差不是实际网络时延。普通record的RMW source时间也不自动等于传感器Header采样时间，时钟同步、设备驱动与接口合同仍需另查。'], tables=[storage_table]),
            dict(title='缓存反例：QoS相容仍可能没有早先静态样本', paragraphs=[
                '三组录制都在Recorder启动前只发布一次静态String，并保持transient_local发布者存活。两个请求transient_local的正例读回静态1条；volatile反例仍能匹配，却没有请求旧历史，读回静态0条。它不证明MCAP损坏，也不代表真实/tf_static已测试；本例是相同持久性机制的合成状态。',
                '元数据总数分别13/13/12，每主题计数、完整字段与原始载荷SHA分开记录。第一次夹具错误把另一次序列化的SHA当作DDS字节一致性：字段相同而CDR对齐padding不同。现比较完整Header/Point语义；原bag SHA只标识那次字节，显式同一bytes写入的探针才逐字节对照。',
                '另一早期夹具误用了Jazzy不存在的qos_profile_clock名称；改为显式深度1/best_effort后再完整运行。两次失败和清理证据保留，不把它们算作录放功能通过。当前常规八个子进程均退出0且无升级信号；父SIGINT与原生挂起分支仍未注入。'], tables=[recording]),
            dict(title='只读检查与显式字段探针的完整源码', paragraphs=['两个工具无需启动DDS，--help无需ROS导入；双后端探针还实际检查相对新输出路径。计数上限、类型白名单、文件大小与noChunking范围都在源码说明。'], codeBlocks=[
                block('inspect_bag.py', '关闭后只读小包，保留记录时间、全部Point/Header字段及实际载荷SHA；不自动动态导入任意类型。'),
                block('storage_fields.py', '同一序列化bytes的双后端字段探针，输出新目录且显式关闭资源；不是网络延迟实验。'),
                block('mcap_no_chunk.yaml', '只用于单消息字段探针的无分块配置，不是普通录制的性能建议。')])],
        appendExercises=[
            dict(question='MCAP和SQLite都能读回Header，为何仍需单独核send字段？', answer='Header在载荷里；recv/send在存储记录层。当前SQLite表只存recv，MCAP另存publishTime。保留同一消息不代表所有记录层信息都相同。'),
            dict(question='Python read_next返回的第三个整数可以直接称作发送时间吗？', answer='不可以，本机绑定返回recv时间。要核发送字段需对应后端/版本的实际读取接口或明确范围的原始字段检查，且仍不能把它当Header。'),
            dict(question='晚加入volatile录制器与transient_local发布者相容，为什么静态计数仍为零？', answer='相容只说明可通信，不等于订阅请求历史。样本在录制器之前发送、之后未重发，易失请求不会取得旧缓存；先核端点、历史和时间顺序。'),
            dict(question='字段完全相同而两次CDR SHA不同，应先判断消息损坏吗？', answer='先按类型检查全部语义字段及编码。对齐padding可不同；跨序列化比较用字段合同，原字节哈希用于标识实际bytes或验证同一bytes的传输/落盘。')])
    api_path = ROOT / 'source/api-reference.json'
    api = json.loads(api_path.read_text())
    target = next(a for a in api['apiReferences'] if a['id'] == 'api-rosbag-qos')
    target['rows'] = target['rows'][:4] + [
        ['Header.stamp / recv / send', '生产者消息时间字段、接收记录、RMW source记录', '来源不同的整数ns', '本机普通record不解析Header；sim分支改recv为ROS clock。不同时间域不能直接相减称延迟。'],
        ['record --use-sim-time', '录制节点及正值/clock', '开始数据订阅、用ROS时间记录', 'started要求当前值严格大于零；门前volatile数据不补录，历史缓存请求另按QoS核。'],
        ['SequentialWriter.write四参数', 'topic、同一bytes、recv_ns、send_ns', '两个后端实际落盘', '当前MCAP保留logTime/publishTime；SQLite只有接收timestamp。显式输入不是网络测量。'],
        ['SequentialReader.read_next', '已关闭bag与匹配存储插件/类型', '(topic, bytes, recv_ns)', '本机Python绑定不返回send；元数据数量、语义字段、实际bytes身份分别核。']]
    note = '同版快照也可能有补丁差异；本轮实测CLI自然退出，不推广Player保活会话结束后的clock timer行为。'
    if note not in target['notes']:target['notes'].append(note)
    api_path.write_text(json.dumps(api, ensure_ascii=False, indent=2) + '\n')
    destination = ROOT / 'source/iteration-5-revisions.json'
    destination.write_text(json.dumps(revision, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(revision=str(destination), evidenceTables=4, fullSourceFiles=6, newExercises=8), ensure_ascii=False))


if __name__ == '__main__':
    main()
