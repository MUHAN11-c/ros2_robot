#!/usr/bin/env python3
"""Build browser-local content and portable reading exports using only stdlib."""
import json
import re
import argparse
import csv
import hashlib
from pathlib import Path
from book_export import build_book, expanded_markdown
from catalog_mapping import map_entry
from math_render import prepare_equations

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
def read(name):
    return json.loads((ROOT / 'source' / f'{name}.json').read_text())
parser=argparse.ArgumentParser(description='构建自足离线教材、公式、图解与来源附录。')
parser.add_argument('--require-full',action='store_true',help='交付检查：必须具有全部计划新章、来源索引与代码注释')
args=parser.parse_args()
core, eco, community, catalog = (read(n) for n in ('core', 'ecosystem', 'community', 'catalog'))
extra = read('extra')
frontier = read('frontier')
additions=[read(name) for name in ('math-foundations','applied-robotics') if (ROOT/'source'/f'{name}.json').exists()]
annotations=read('code-annotations') if (ROOT/'source/code-annotations.json').exists() else {}
revision_names=('content-revisions','navigation-revision','iteration-revisions','iteration-2-revisions','iteration-3-revisions','iteration-4-revisions','iteration-5-revisions','iteration-6-revisions')
revisions={name:read(name) for name in revision_names if (ROOT/'source'/f'{name}.json').exists()}
api=read('api-reference')['apiReferences'] if (ROOT/'source/api-reference.json').exists() else []
coverage=read('reference-coverage') if (ROOT/'source/reference-coverage.json').exists() else {}
library=read('local-library') if (ROOT/'source/local-library.json').exists() else {}
figures=read('design-figures')['figures']
for figure in figures:
    if figure.get('evidenceFile'):
        evidence=(ROOT/figure['evidenceFile']).resolve(strict=True)
        if not evidence.is_relative_to((ROOT/'validation-evidence').resolve()):raise ValueError('图解数值只绑定验证目录证据')
        if hashlib.sha256(evidence.read_bytes()).hexdigest()!=figure.get('evidenceSha256'):
            raise ValueError('图解绑定的实测已变化，应先核对并重新生成：'+figure['id'])
expanded={}
for filename in ('foundation-expanded','engineering-expanded','ecosystem-expanded'):
    path=ROOT/'source'/f'{filename}.json'
    if path.exists():
        for chapter in read(filename)['chapters']:
            expanded[chapter['id']]=chapter

stages = [
    dict(id='foundation',title='基础与环境',description='建立整体模型，跑通第一个节点。'),
    dict(id='mathematics',title='数学与机器人基础',description='用推导、单位和可运行实验理解几何、估计、优化与控制。'),
    dict(id='communication',title='通信与开发',description='在两种语言和多种配置之间建立对应关系。'),
    dict(id='engineering',title='工程化与运行机制',description='组织并发、测试、网络、安全和可重复部署。'),
    dict(id='model',title='模型、仿真与感知',description='把时间、坐标、机器人描述和观测数据对齐。'),
    dict(id='autonomy',title='控制、导航与操作',description='从底盘接口到自主导航和机械臂任务。'),
    dict(id='advanced',title='嵌入式与前沿生态',description='连接微控制器、多机器人、学习策略与数据流程。'),
]
stage_members = {
 'foundation':['architecture','installation','workspace','graph-cli'],
 'mathematics':['math-linear','math-rigid','math-probability','math-estimation','math-optimization','math-kinematics','math-dynamics','math-control'],
 'communication':['pubsub','interfaces','services','actions','parameters','launch','qos'],
 'engineering':['cpp-engineering','executors','lifecycle','composition','time-bag','testing','network','security','performance','deployment','migration'],
 'model':['tf2','eco-tf-frames','eco-model-rviz','eco-gazebo-simulation','eco-perception-pipeline','eco-data-observability'],
 'autonomy':['eco-control-framework','eco-diff-drive-tracks','eco-hardware-integration','theory-slam','eco-slam-mapping','eco-state-estimation','theory-planning','theory-optimal-control','eco-nav2-stack','eco-nav2-task-programming','project-navigation','eco-moveit-planning','eco-manipulation-tasks','project-manipulation'],
 'advanced':['eco-microcontrollers','eco-multi-robot','eco-network-security','eco-accelerated-robotics','theory-legged','theory-aerial','learning-rl','learning-embodied','learning-policy','cloud-mlops'],
}
resources, aliases, seen_urls = [], {}, {}
new_resources=[r for item in additions for r in item['resources']]
revision_resources=[resource for revision in revisions.values() for resource in revision.get('resources',[])]
for r in core['sources'] + eco['resources'] + community['resources'] + extra['resources'] + frontier['resources'] + new_resources + revision_resources:
    if r['url'].rstrip('/') in seen_urls:
        aliases[r['id']] = seen_urls[r['url'].rstrip('/')]
        continue
    seen_urls[r['url'].rstrip('/')] = r['id']
    verification = r.get('verification') or r.get('verifiedVia') or (r.get('verified') if isinstance(r.get('verified'),str) else '核查情况见版本提示')
    resources.append(dict(id=r['id'],title=r.get('title',r.get('name','')),url=r['url'],sourceUrl=r.get('sourceUrl',''),category=r['category'],version=r['version'],description=r['description'],versionNote=r.get('versionNote',''),verification=verification,checkedAt=r.get('checkedAt','2026-11-07' if r in new_resources else '2026-11-06'),type=r.get('type',r.get('sourceType','作者／维护者资料'))))
def refs(items):
    return list(dict.fromkeys(aliases.get(x,x) for x in items))
lesson_dict = {}
for c in core['chapters'] + eco['chapters'] + extra['chapters'] + frontier['chapters'] + [c for item in additions for c in item['chapters']]:
    c=dict(c)
    c.update(expanded.get(c['id'],{}))
    c['goals']=c.get('goals',c.get('objectives',[]))
    c['summary']=c.get('summary') or c['concepts'][0]
    c['sourceIds']=refs(c['sourceIds'])
    c['version']=c.get('version','Jazzy 主线')
    c['exerciseAnswer']=c.get('exerciseAnswer',c.get('exercise_answer',c.get('answer','')))
    if isinstance(c['exerciseAnswer'],list):
        c['exerciseAnswer']='\n\n'.join(c['exerciseAnswer'])
    if not c['exerciseAnswer']:
        raise ValueError('Missing exercise answer: '+c['id'])
    c['minutes']=max(25,min(75,15+len(c.get('sections',[]))*6))
    lesson_dict[c['id']]=c
# 注释覆层保持正文源结构稳定；所有展示、Markdown 和下载包使用同一份注释代码。
for chapter_id,patch in annotations.get('chapters',{}).items():
    c=lesson_dict[chapter_id]
    for position,block in patch.get('sections',{}).items():
        si,bi=map(int,position.split(':'))
        if block.get('originalSha256'):assert hashlib.sha256(c['sections'][si]['codeBlocks'][bi]['code'].encode()).hexdigest()==block['originalSha256'],(chapter_id,position,'注释位置已漂移')
        c['sections'][si]['codeBlocks'][bi].update(block)
    for field in ('steps','commands'):
        for position,block in patch.get(field,{}).items():
            if block.get('originalSha256'):assert hashlib.sha256(c[field][int(position)]['code'].encode()).hexdigest()==block['originalSha256'],(chapter_id,field,position,'注释位置已漂移')
            c[field][int(position)].update(block)


def apply_content_revision(revision):
    """按独立审查修正明确位置，不覆盖未涉及的段落或代码。

    注释层先应用，审查层随后修正实际语义；最后才准备公式、图解和导出。
    每次构建均从原始JSON重读，因此追加内容不会在多次构建时重复累积。
    """
    meta=revision.get('meta',{})
    if meta.get('sourceReviewFile'):
        review=(ROOT/meta['sourceReviewFile']).resolve(strict=True)
        if not review.is_relative_to((ROOT/'validation-evidence').resolve()):
            raise ValueError('独立审查记录越出验证目录')
        if hashlib.sha256(review.read_bytes()).hexdigest()!=meta.get('sourceReviewSha256'):
            raise ValueError('独立审查记录已变化，应重新核对并生成对应正文素材')
    for chapter_id,patch in revision.get('chapters',{}).items():
        chapter=lesson_dict[chapter_id]
        for field,value in patch.items():
            if field not in ('sections','steps','commands','appendSections','appendExercises','appendExpected','appendPitfalls'):chapter[field]=refs(value) if field=='sourceIds' else value
        for position,section_patch in patch.get('sections',{}).items():
            section=chapter['sections'][int(position)]
            for field,value in section_patch.items():
                if field not in ('codeBlocks','appendParagraphs','prependCodeBlocks','appendCodeBlocks'):section[field]=value
            section.setdefault('paragraphs',[]).extend(section_patch.get('appendParagraphs',[]))
            for block_index,block_patch in section_patch.get('codeBlocks',{}).items():section['codeBlocks'][int(block_index)].update(block_patch)
            section['codeBlocks']=section_patch.get('prependCodeBlocks',[])+section.get('codeBlocks',[])+section_patch.get('appendCodeBlocks',[])
        for field in ('steps','commands'):
            for position,block_patch in patch.get(field,{}).items():
                index=int(position)
                if field=='steps' and isinstance(block_patch,str):
                    # 纯文字步骤整体替换；带代码的步骤和终端命令仍逐字段修订。
                    chapter[field][index]=block_patch
                else:
                    if not isinstance(chapter[field][index],dict) or not isinstance(block_patch,dict):
                        raise ValueError('步骤/命令修订类型不一致：'+chapter_id+'/'+field+'/'+position)
                    chapter[field][index].update(block_patch)
        for source_field,target_field in (('appendSections','sections'),('appendExercises','exercises'),('appendExpected','expected'),('appendPitfalls','pitfalls')):
            chapter.setdefault(target_field,[]).extend(patch.get(source_field,[]))


for revision in revisions.values():apply_content_revision(revision)
# 新实验以文件为唯一代码源，正文与源码包自动同步，不维护手工复制的第二份代码。
for chapter in lesson_dict.values():
    for section in chapter.get('sections',[]):
        for table in section.get('tables',[]):
            if not table.get('columns') or not table.get('rows') or any(len(row)!=len(table['columns']) for row in table['rows']):
                raise ValueError('正文数据表列数不一致：'+chapter['id'])
            if table.get('evidenceFile'):
                evidence=(ROOT/table['evidenceFile']).resolve(strict=True)
                if not evidence.is_relative_to((ROOT/'validation-evidence').resolve()):raise ValueError('实验数据表只读取验证记录')
                if hashlib.sha256(evidence.read_bytes()).hexdigest()!=table['evidenceSha256']:
                    raise ValueError('实验记录已变化，需重新核对正文数据表：'+table['title'])
        for block in section.get('codeBlocks',[]):
            if not block.get('sourceFile'):continue
            file=(ROOT/block['sourceFile']).resolve(strict=True)
            if not file.is_relative_to((ROOT/'examples').resolve()):raise ValueError('教学源码必须来自原创examples目录')
            block['code']=file.read_text()
            block['sourceSha256']=hashlib.sha256(file.read_bytes()).hexdigest()
lessons=[]
for s in stages:
    for id in stage_members[s['id']]:
        if id not in lesson_dict:continue
        c=lesson_dict[id]
        c['stage']=s['id']
        lessons.append(c)
comparisons=core['comparisons']+extra['comparisons']
related={'publisher':['pubsub'],'callback':['pubsub','executors'],'service':['services'],'actions':['actions'],'params':['parameters'],'launch':['launch'],'executor':['executors'],'composition':['composition'],'build':['workspace'],'qos':['qos'],'velocity':['eco-diff-drive-tracks','eco-hardware-integration'],'description':['eco-model-rviz']}
for c in comparisons:
    c['sourceIds']=refs(c['sourceIds'])
    c['relatedLessons']=related.get(c['id'].replace('compare-',''),[])
    patch=annotations.get('comparisons',{}).get(c['id'],{})
    for position,variant in patch.get('variants',{}).items():
        if variant.get('originalSha256'):assert hashlib.sha256(c['variants'][int(position)]['code'].encode()).hexdigest()==variant['originalSha256'],(c['id'],position,'对照注释位置已漂移')
        c['variants'][int(position)].update(variant)
    if patch.get('notes'):c['notes']=list(dict.fromkeys(c['notes']+patch['notes']))
for c in catalog:
    c.pop('file',None)
    c['lessons']=map_entry(c)
    assert all(id in lesson_dict for id in c['lessons']),c
catalog.sort(key=lambda c:(c['site'],[int(x) for x in re.findall(r'\d+',c['title'])] or [0]))
for p in extra['projects']:
    p['sourceIds']=refs(p['sourceIds'])
validation_text='已在本机分轮构建通信2包、基础10包及动作/组件/生命周期/测试/模型各1包。数值、协议、录放、模型TF、注册测试与宿主审计按记录输入验证；GUI、Docker、完整仿真与硬件未运行。具体证据与未覆盖分支见VALIDATION.md。'
data=dict(meta=dict(title='ROS 2 学习图谱',checkedAt='2026-11-07',version='Jazzy',exampleValidation=validation_text),stages=stages,lessons=lessons,comparisons=comparisons,resources=resources,catalog=catalog,projects=extra['projects'],paths=extra['paths'],ecosystems=extra['ecosystems'],issues=extra['issues'],glossary=extra['glossary'],versionNotes=eco['versionNotes']+extra['versionNotes'],coverage=coverage,library=library,apiReferences=api,figures=figures)
for c in lessons:
    c['apiReferences']=[item for item in api if c['id'] in item['lessons']]
    c['figures']=[dict(id=item['id'],file=item['file'],alt=item['alt'],caption=item['caption'],afterSection=p['afterSection']) for item in figures for p in item['placements'] if p['chapter']==c['id']]
data['meta']['equationCount']=prepare_equations(lessons)
data['meta']['apiTableCount']=len(api)
data['meta']['evidenceTableCount']=sum(len(s.get('tables',[])) for c in lessons for s in c['sections'])
data['meta']['coverageDocuments']=len(coverage.get('entries',[]))
data['meta']['annotatedChapters']=len(annotations.get('chapters',{}))
data['meta']['plannedMissingChapterIds']=[id for members in stage_members.values() for id in members if id not in lesson_dict]
stages[:]=[stage for stage in stages if any(c['stage']==stage['id'] for c in lessons)]
example_files=[]
for file in sorted((ROOT/'examples').rglob('*')):
    if not file.is_file() or any(p in ('__pycache__','build','install','log') or p.endswith('.egg-info') for p in file.parts):continue
    if file.suffix not in ('.py','.cpp','.hpp','.h','.xml','.urdf','.xacro','.yaml','.json','.cfg','.md','.txt','.cmake','.sh','.bash','.msg','.srv','.action') and file.name not in ('CMakeLists.txt','atlas_py','LICENSE'):continue
    lang='cmake' if file.name=='CMakeLists.txt' else {'.py':'python','.cpp':'cpp','.hpp':'cpp','.h':'cpp','.xml':'xml','.urdf':'xml','.xacro':'xml','.yaml':'yaml','.json':'json','.cfg':'ini','.md':'markdown','.cmake':'cmake','.sh':'bash','.bash':'bash'}.get(file.suffix,'text')
    example_files.append(dict(path=file.relative_to(ROOT/'examples').as_posix(),language=lang,code=file.read_text()))
for file in sorted((ROOT/'foundation-examples').rglob('*')):
    if not file.is_file() or any(p in ('__pycache__','build','install','log') or p.endswith('.egg-info') for p in file.parts):continue
    if file.suffix not in ('.py','.cpp','.hpp','.h','.xml','.yaml','.json','.cfg','.md','.txt','.cmake','.sh','.bash','.msg','.srv','.action') and file.name not in ('CMakeLists.txt','LICENSE'):continue
    lang='cmake' if file.name=='CMakeLists.txt' else {'.py':'python','.cpp':'cpp','.hpp':'cpp','.h':'cpp','.xml':'xml','.yaml':'yaml','.json':'json','.cfg':'ini','.md':'markdown','.cmake':'cmake','.sh':'bash','.bash':'bash'}.get(file.suffix,'text')
    example_files.append(dict(path='foundation/'+file.relative_to(ROOT/'foundation-examples').as_posix(),language=lang,code=file.read_text()))
data['exampleFiles']=example_files
data['meta']['expandedChapters']=sum(bool(c.get('sections')) for c in lessons)
data['meta']['exerciseCount']=sum(1+len(c.get('exercises',[])) for c in lessons)
def prose_text(c):
    parts=[c['title'],c['summary'],*c['goals'],*c['concepts'],*c['expected'],*c['pitfalls'],c['exercise'],c['exerciseAnswer']]
    for s in c.get('sections',[]):
        parts.extend([s['title'],*s.get('paragraphs',[]),*s.get('bullets',[])])
        parts.extend(b.get('explanation','') for b in s.get('codeBlocks',[]))
    for x in c.get('exercises',[]):parts.extend([x['question'],x['answer']])
    x=c.get('workedExample')
    if x:parts.extend([x['title'],x['scenario'],*x['steps'],x['result']])
    return '\n'.join(parts)
data['meta']['proseChineseCharacters']=sum(len(re.findall(r'[\u4e00-\u9fff]',prose_text(c))) for c in lessons)
data['meta']['codeBlockCount']=sum(len(c.get('commands',[]))+sum(1 for s in c['steps'] if isinstance(s,dict) and s.get('code'))+sum(len(s.get('codeBlocks',[])) for s in c.get('sections',[])) for c in lessons)+sum(len(c['variants']) for c in comparisons)
depth=dict(checkedAt='2026-11-07',scopeClaim='以下记录本站实际编写的章节范围，不表示原始资料逐段收录。第三方页面的核读/对应深度另见 reference-coverage.json。',
           chapters=[dict(id=c['id'],title=c['title'],scope=c['summary'],sectionTitles=[s['title'] for s in c['sections']],
                          sectionProseChineseCharacters=len(re.findall(r'[\u4e00-\u9fff]',''.join(p for s in c['sections'] for p in s.get('paragraphs',[])+s.get('bullets',[])))),
                          equations=sum(len(s.get('equations',[])) for s in c['sections']),
                          exercises=1+len(c.get('exercises',[])),validation=c['validation']) for c in lessons])
(ROOT/'source/topic-depth.json').write_text(json.dumps(depth,ensure_ascii=False,indent=2)+'\n')
source_map={r['id']:r for r in resources}
for collection in (lessons,comparisons,resources,extra['projects']):
    assert len({x['id'] for x in collection})==len(collection),'Duplicate ID'
for c in lessons+comparisons+extra['projects']:
    for id in c['sourceIds']:
        assert id in source_map,(c['id'],id)
for x in extra['paths']+extra['ecosystems']+extra['projects']:
    assert all(id in lesson_dict for id in x['lessons']), x
assert len(lessons)>=44
assert len(catalog)==169
if args.require_full:
    assert len(lessons)==60 and not data['meta']['plannedMissingChapterIds'],'扩展章节不完整'
    assert coverage.get('entries') and library.get('snapshots'),'缺少真实覆盖或本地资料索引'
    assert len(annotations.get('chapters',{}))==44,'既有章节代码注释尚未完成'
    assert (ROOT/'source/iteration-revisions.json').is_file(),'缺少迭代修订与真实API实验'
    assert (ROOT/'source/iteration-2-revisions.json').is_file(),'缺少第2轮真实实验与正文表格'
    assert (ROOT/'source/iteration-3-revisions.json').is_file(),'缺少第3轮动作/组件实测与独立审查'
    assert (ROOT/'source/iteration-4-revisions.json').is_file(),'缺少第4轮生命周期/测试/部署及独立审查'
    assert (ROOT/'source/iteration-5-revisions.json').is_file(),'缺少第5轮rosbag录放/存储实测及独立审查'
    assert (ROOT/'source/iteration-6-revisions.json').is_file(),'缺少第6轮模型/TF与数值边界实测及独立审查'
OUT.mkdir(exist_ok=True)
(OUT/'content.js').write_text('/* 原创中文综合内容；来源与核查范围见资料库。 */\nwindow.ROS2Hub = '+json.dumps(data,ensure_ascii=False,indent=2)+';\n')
# 正式阅读器沿用图解模块，必须与正文/连续版使用同一份清单，避免新图只在book出现。
(OUT/'preview').mkdir(exist_ok=True)
(OUT/'preview/figure-data.js').write_text('/* 正式构建同步的原创图解清单；来源为source/design-figures.json。 */\nwindow.PreviewFigureData = '+json.dumps(figures,ensure_ascii=False,indent=2)+';\n')
downloads=OUT/'downloads'
downloads.mkdir(exist_ok=True)
(downloads/'sources.json').write_text(json.dumps(dict(checkedAt='2026-11-07',resources=resources,tutorialPages=catalog,coverage=coverage,localLibrary=library,authoredScope=depth),ensure_ascii=False,indent=2)+'\n')
(downloads/'local-library.json').write_text(json.dumps(library,ensure_ascii=False,indent=2)+'\n')
# 本地文档只发布标题与路径，不把第三方正文复制进统一许可的教材数据。
documents=[]
document_csv=ROOT/'references/documents.csv'
if document_csv.exists():
    with document_csv.open(newline='') as stream:
        for row in csv.DictReader(stream):
            absolute=(ROOT/'references'/row['local_path']).resolve()
            if not absolute.is_relative_to(ROOT.parent):raise ValueError('文档索引越出工作区')
            documents.append(dict(snapshot=row['snapshot'],branch=row['branch'],format=row['format'].lstrip('.'),title=row['title'],path=absolute.relative_to(ROOT.parent).as_posix()))
(OUT/'reference-data.js').write_text('/* 原始资料文件元数据；正文与许可独立保存。 */\nwindow.ROS2LocalDocuments = '+json.dumps(documents,ensure_ascii=False,separators=(',',':'))+';\n')
md=['# ROS 2 学习图谱','主线：ROS 2 Jazzy / Ubuntu 24.04。资料核对：2026-11-07。',data['meta']['exampleValidation']]
for index,c in enumerate(lessons,1):
    prerequisites=c.get('prerequisites','')
    md.extend([f"## {index}. {c['title']}",c['summary'],'### 学习目标',*['- '+g for g in c['goals']],'### 先修','；'.join(prerequisites) if isinstance(prerequisites,list) else prerequisites,'### 概念',*c['concepts']])
    md.extend(expanded_markdown(c))
    for comparison in comparisons:
        if c['id'] in comparison.get('relatedLessons',[]):
            md.extend(['### '+comparison['title'],comparison['question']])
            for v in comparison['variants']:md.extend(['#### '+v['label'],v['scope'],'```'+v['language'],v['code'],'```'])
            md.extend(comparison['notes'])
    md.append('### 基础验证流程')
    for s in c['steps']:
        if isinstance(s,str): md.append(s)
        else:
            md.extend(['#### '+s['title'],s.get('body','')])
            if s.get('code'): md.extend(['```'+s.get('language','bash'),s['code'],'```'])
    for block in c.get('commands',[]):md.extend(['#### '+block['label'],'```'+block.get('language','bash'),block['code'],'```'])
    md.extend(['### 预期结果',*['- '+x for x in c['expected']],'### 常见问题',*['- '+x for x in c['pitfalls']],'### 练习',c['exercise'],'#### 参考答案',c['exerciseAnswer'],'### 验证范围',c['validation'],'### 依据'])
    md.extend(f"- [{source_map[id]['title']}]({source_map[id]['url']})" for id in c['sourceIds'])
md.append('## 不同写法对照')
for c in comparisons:
    md.extend(['### '+c['title'],c['question']])
    for v in c['variants']:md.extend(['#### '+v['label'],v['scope'],'```'+v['language'],v['code'],'```'])
    md.extend(c['notes'])
    md.extend(f"- [{source_map[id]['title']}]({source_map[id]['url']})" for id in c['sourceIds'])
md.append('## 综合项目')
for p in data['projects']:
    md.extend(['### '+p['title'],p['summary'],*[f'{i+1}. {s}' for i,s in enumerate(p['milestones'])],'```bash',p['code'],'```',p['note']])
md.append('## 完整教学工程文件')
for f in example_files:
    fence='`'*max(3,1+max((len(x) for x in re.findall(r'`+',f['code'])),default=0))
    md.extend(['### '+f['path'],fence+f['language'],f['code'],fence])
md.append('## 全部来源目录')
for r in resources:md.append(f"- [{r['title']}]({r['url']}) · {r['version']} · {r['verification']}")
md.append('## 两套教程与本书的主题对应关系')
for r in catalog:md.append('- '+r['title']+' → '+ ' / '.join(lesson_dict[id]['title'] for id in r['lessons'])+' · [原出处]('+r['url']+')')
(downloads/'ros2-learning-guide.md').write_text('\n\n'.join(md)+'\n')
bib=['# 全部来源目录','核对日期：2026-11-07。网页、官方源码与本地目录核查方式分别记录。']
for r in resources:bib.append(f"- [{r['title']}]({r['url']}) · {r['version']} · {r['verification']}\n  {r['description']}")
bib.append('## 两套教程的全部本地页面索引\n标题和路径由本地文件提取；未逐项联网复测。')
for r in catalog:bib.append(f"- [{r['title']}]({r['url']}) · {r['site']}")
bib.extend(['## 三套教程的真实内容对应',coverage.get('meta',{}).get('scopeClaim','')])
for entry in coverage.get('entries',[]):bib.append(f"- {entry['site']} · {entry['title']} · {entry['kind']} · {entry['depth']} · {entry['reviewLevel']} · {entry['file']}")
(downloads/'bibliography.md').write_text('\n\n'.join(bib)+'\n')
book_result=build_book(data,OUT)
print(json.dumps(dict(lessons=len(lessons),expandedChapters=data['meta']['expandedChapters'],comparisons=len(comparisons),sources=len(resources),tutorialPages=len(catalog),guideBytes=(downloads/'ros2-learning-guide.md').stat().st_size,**book_result),ensure_ascii=False))
