#!/usr/bin/env python3
"""Build browser-local content and portable reading exports using only stdlib."""
import json
import re
from pathlib import Path
from book_export import build_book, expanded_markdown
from catalog_mapping import map_entry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
def read(name):
    return json.loads((ROOT / 'source' / f'{name}.json').read_text())
core, eco, community, catalog = (read(n) for n in ('core', 'ecosystem', 'community', 'catalog'))
extra = read('extra')
frontier = read('frontier')
expanded={}
for filename in ('foundation-expanded','engineering-expanded','ecosystem-expanded'):
    path=ROOT/'source'/f'{filename}.json'
    if path.exists():
        for chapter in read(filename)['chapters']:
            expanded[chapter['id']]=chapter

stages = [
    dict(id='foundation',title='基础与环境',description='建立整体模型，跑通第一个节点。'),
    dict(id='communication',title='通信与开发',description='在两种语言和多种配置之间建立对应关系。'),
    dict(id='engineering',title='工程化与运行机制',description='组织并发、测试、网络、安全和可重复部署。'),
    dict(id='model',title='模型、仿真与感知',description='把时间、坐标、机器人描述和观测数据对齐。'),
    dict(id='autonomy',title='控制、导航与操作',description='从底盘接口到自主导航和机械臂任务。'),
    dict(id='advanced',title='嵌入式与前沿生态',description='连接微控制器、多机器人、学习策略与数据流程。'),
]
stage_members = {
 'foundation':['architecture','installation','workspace','graph-cli'],
 'communication':['pubsub','interfaces','services','actions','parameters','launch','qos'],
 'engineering':['executors','lifecycle','composition','time-bag','testing','network','security','performance','deployment','migration'],
 'model':['tf2','eco-tf-frames','eco-model-rviz','eco-gazebo-simulation','eco-perception-pipeline','eco-data-observability'],
 'autonomy':['eco-control-framework','eco-diff-drive-tracks','eco-hardware-integration','eco-slam-mapping','eco-state-estimation','eco-nav2-stack','eco-nav2-task-programming','eco-moveit-planning','eco-manipulation-tasks'],
 'advanced':['eco-microcontrollers','eco-multi-robot','eco-network-security','eco-accelerated-robotics','learning-rl','learning-embodied','learning-policy','cloud-mlops'],
}
resources, aliases, seen_urls = [], {}, {}
for r in core['sources'] + eco['resources'] + community['resources'] + extra['resources'] + frontier['resources']:
    if r['url'].rstrip('/') in seen_urls:
        aliases[r['id']] = seen_urls[r['url'].rstrip('/')]
        continue
    seen_urls[r['url'].rstrip('/')] = r['id']
    verification = r.get('verification') or r.get('verifiedVia') or (r.get('verified') if isinstance(r.get('verified'),str) else '核查情况见版本提示')
    resources.append(dict(id=r['id'],title=r.get('title',r.get('name','')),url=r['url'],sourceUrl=r.get('sourceUrl',''),category=r['category'],version=r['version'],description=r['description'],versionNote=r.get('versionNote',''),verification=verification,checkedAt='2026-11-06',type=r.get('type',r.get('sourceType','作者／维护者资料'))))
def refs(items):
    return list(dict.fromkeys(aliases.get(x,x) for x in items))
lesson_dict = {}
for c in core['chapters'] + eco['chapters'] + extra['chapters'] + frontier['chapters']:
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
lessons=[]
for s in stages:
    for id in stage_members[s['id']]:
        c=lesson_dict[id]
        c['stage']=s['id']
        lessons.append(c)
comparisons=core['comparisons']+extra['comparisons']
related={'publisher':['pubsub'],'callback':['pubsub','executors'],'service':['services'],'actions':['actions'],'params':['parameters'],'launch':['launch'],'executor':['executors'],'composition':['composition'],'build':['workspace'],'qos':['qos'],'velocity':['eco-diff-drive-tracks','eco-hardware-integration'],'description':['eco-model-rviz']}
for c in comparisons:
    c['sourceIds']=refs(c['sourceIds'])
    c['relatedLessons']=related.get(c['id'].replace('compare-',''),[])
for c in catalog:
    c.pop('file',None)
    c['lessons']=map_entry(c)
    assert all(id in lesson_dict for id in c['lessons']),c
catalog.sort(key=lambda c:(c['site'],[int(x) for x in re.findall(r'\d+',c['title'])] or [0]))
for p in extra['projects']:
    p['sourceIds']=refs(p['sourceIds'])
data=dict(meta=dict(title='ROS 2 学习图谱',checkedAt='2026-11-06',version='Jazzy',exampleValidation=extra['exampleValidation']),stages=stages,lessons=lessons,comparisons=comparisons,resources=resources,catalog=catalog,projects=extra['projects'],paths=extra['paths'],ecosystems=extra['ecosystems'],issues=extra['issues'],glossary=extra['glossary'],versionNotes=eco['versionNotes']+extra['versionNotes'])
example_files=[]
for file in sorted((ROOT/'examples').rglob('*')):
    if not file.is_file() or any(p in ('__pycache__','build','install','log') or p.endswith('.egg-info') for p in file.parts):continue
    if file.suffix not in ('.py','.cpp','.xml','.yaml','.cfg','.md','.txt') and file.name not in ('CMakeLists.txt','atlas_py','LICENSE'):continue
    lang={'.py':'python','.cpp':'cpp','.xml':'xml','.yaml':'yaml','.cfg':'ini','.md':'markdown'}.get(file.suffix,'text')
    example_files.append(dict(path=file.relative_to(ROOT/'examples').as_posix(),language=lang,code=file.read_text()))
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
source_map={r['id']:r for r in resources}
for collection in (lessons,comparisons,resources,extra['projects']):
    assert len({x['id'] for x in collection})==len(collection),'Duplicate ID'
for c in lessons+comparisons+extra['projects']:
    for id in c['sourceIds']:
        assert id in source_map,(c['id'],id)
for x in extra['paths']+extra['ecosystems']+extra['projects']:
    assert all(id in lesson_dict for id in x['lessons']), x
assert len(lessons)==44
assert len(catalog)==169
OUT.mkdir(exist_ok=True)
(OUT/'content.js').write_text('/* 原创中文综合内容；来源与核查范围见资料库。 */\nwindow.ROS2Hub = '+json.dumps(data,ensure_ascii=False,indent=2)+';\n')
downloads=OUT/'downloads'
downloads.mkdir(exist_ok=True)
(downloads/'sources.json').write_text(json.dumps(dict(checkedAt='2026-11-06',resources=resources,tutorialPages=catalog),ensure_ascii=False,indent=2)+'\n')
md=['# ROS 2 学习图谱','主线：ROS 2 Jazzy / Ubuntu 24.04。资料核对：2026-11-06。',data['meta']['exampleValidation']]
for index,c in enumerate(lessons,1):
    prerequisites=c.get('prerequisites','')
    md.extend([f"## {index}. {c['title']}",c['summary'],'### 学习目标',*['- '+g for g in c['goals']],'### 先修','；'.join(prerequisites) if isinstance(prerequisites,list) else prerequisites,'### 概念',*c['concepts']])
    md.extend(expanded_markdown(c))
    md.append('### 基础验证流程')
    for s in c['steps']:
        if isinstance(s,str): md.append(s)
        else:
            md.extend(['#### '+s['title'],s.get('body','')])
            if s.get('code'): md.extend(['```'+s.get('language','bash'),s['code'],'```'])
    for block in c.get('commands',[]):md.extend(['#### '+block['label'],'```'+block.get('language','bash'),block['code'],'```'])
    md.extend(['### 预期结果',*['- '+x for x in c['expected']],'### 常见问题',*['- '+x for x in c['pitfalls']],'### 练习',c['exercise'],'#### 参考答案',c['exerciseAnswer'],'### 依据'])
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
bib=['# 全部来源目录','核对日期：2026-11-06。网页、官方源码与本地目录核查方式分别记录。']
for r in resources:bib.append(f"- [{r['title']}]({r['url']}) · {r['version']} · {r['verification']}\n  {r['description']}")
bib.append('## 两套教程的全部本地页面索引\n标题和路径由本地文件提取；未逐项联网复测。')
for r in catalog:bib.append(f"- [{r['title']}]({r['url']}) · {r['site']}")
(downloads/'bibliography.md').write_text('\n\n'.join(bib)+'\n')
book_result=build_book(data,OUT)
print(json.dumps(dict(lessons=len(lessons),expandedChapters=data['meta']['expandedChapters'],comparisons=len(comparisons),sources=len(resources),tutorialPages=len(catalog),guideBytes=(downloads/'ros2-learning-guide.md').stat().st_size,**book_result),ensure_ascii=False))
