"""Validate delivered content, exports, code syntax and offline assets."""
import ast
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
sys.path.insert(0,str(ROOT/'scripts'))
from book_export import markdown_table
text=(DIST/'content.js').read_text()
data=json.loads(text.split('window.ROS2Hub = ',1)[1].rsplit(';',1)[0])

class Page(HTMLParser):
    def __init__(self,source):
        super().__init__();self.ids=set();self.hrefs=[];self.assets=[];self.scripts=0;self.feed(source)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if attrs.get('id'):
            assert attrs['id'] not in self.ids,('duplicate anchor',attrs['id'])
            self.ids.add(attrs['id'])
        if tag=='script':self.scripts+=1
        if attrs.get('href'):self.hrefs.append(attrs['href'])
        if attrs.get('src'):self.assets.append(attrs['src'])
        if tag=='link' and attrs.get('rel')=='stylesheet':self.assets.append(attrs['href'])

assert len(data['lessons'])==60
assert data['meta']['expandedChapters']==60
assert data['meta']['plannedMissingChapterIds']==[]
assert data['meta']['annotatedChapters']==44
assert data['meta']['equationCount']==49
assert data['meta']['apiTableCount']==len(data['apiReferences'])
assert 'api-parameter-stages' in {a['id'] for a in data['apiReferences']}
assert {'api-composition-options','api-container-models'} <= {a['id'] for a in data['apiReferences']}
assert {'api-lifecycle-outcomes','api-testing-evidence','api-deployment-boundaries'} <= {a['id'] for a in data['apiReferences']}
assert 'api-model-coordinates' in {a['id'] for a in data['apiReferences']}
assert 'api-drive-feedback' in {a['id'] for a in data['apiReferences']}
assert 'api-gz-sensor-contract' in {a['id'] for a in data['apiReferences']}
assert 'api-nav2-map-planning' in {a['id'] for a in data['apiReferences']}
assert 'api-slam-map-lifecycle' in {a['id'] for a in data['apiReferences']}
assert 'api-nav2-execution' in {a['id'] for a in data['apiReferences']}
assert len({a['id'] for a in data['apiReferences']})==len(data['apiReferences'])
figure_bundle=json.loads((DIST/'preview/figure-data.js').read_text().split('window.PreviewFigureData = ',1)[1].rsplit(';',1)[0])
assert figure_bundle==data['figures'],'交互阅读器图解清单必须与正文和连续版同源'
assert len(data['comparisons'])>=12
assert len(data['resources'])>=132
assert len(data['catalog'])==169
ids={c['id'] for c in data['lessons']}
assert len(ids)==len(data['lessons']),'章节标识不能重复'
new_ids={c['id'] for filename in ('math-foundations','applied-robotics')
         for c in json.loads((ROOT/'source'/f'{filename}.json').read_text())['chapters']}
assert len(new_ids)==16 and new_ids<=ids
source_ids={r['id'] for r in data['resources']}
assert len(source_ids)==len(data['resources'])
checked_codes=0
expected_complete=[]
equations=0
minimum=100000
for c in data['lessons']:
    assert len(c['sections'])>=5,c['id']
    prose=''.join(''.join(s.get('paragraphs',[])+s.get('bullets',[])) for s in c['sections'])
    count=len(re.findall(r'[\u4e00-\u9fff]',prose))
    minimum=min(minimum,count)
    assert count>=(1800 if c['id'] in new_ids else 1200),(c['id'],'not enough explanatory prose',count)
    assert c.get('validation') and c.get('expected') and c.get('pitfalls'),c['id']
    assert set(c['sourceIds'])<=source_ids,c['id']
    assert len(c.get('exercises',[]))>=3,c['id']
    assert all(x['question'] and x['answer'] for x in c['exercises']),c['id']
    assert c.get('workedExample',{}).get('steps'),c['id']
    for s in c['sections']:
        for eq in s.get('equations',[]):
            equations+=1
            assert eq['tex'] and '<math' in eq['mathml'] and eq['explanation'],(c['id'],eq['label'])
            assert eq['symbols'] and all(x['symbol'] and x['meaning'] and x.get('unit') for x in eq['symbols']),(c['id'],eq['label'],'符号与单位缺失')
        for b in s.get('codeBlocks',[]):
            assert b['type'] in ('complete','snippet','commands','concept'),(c['id'],b['type'])
            if b.get('sourceFile'):
                source=ROOT/b['sourceFile']
                assert source.resolve().is_relative_to((ROOT/'examples').resolve()),b['sourceFile']
                assert b['code']==source.read_text() and b['sourceSha256']==hashlib.sha256(source.read_bytes()).hexdigest(),b['sourceFile']
            if b['type']!='complete':continue
            label=c['id']+'/'+b['label']
            if b['language']=='python':ast.parse(b['code'],filename=label)
            elif b['language']=='xml':ET.fromstring(b['code'])
            elif b['language']=='json':json.loads(b['code'])
            elif b['language']=='bash':
                result=subprocess.run(['bash','-n'],input=b['code'],text=True,capture_output=True)
                assert result.returncode==0,(label,result.stderr)
            checked_codes+=1
            expected_complete.append((c['title'],b['label'],b['code']))
assert equations==data['meta']['equationCount']
assert data['meta']['evidenceTableCount']==sum(len(s.get('tables',[])) for c in data['lessons'] for s in c['sections'])==44
# 录包新表必须绑定实际报告；旧快捷命令不应在未带选项时声称产生clock。
bag_report=ROOT/'validation-evidence/bag-current-validation.json'
bag_tables=[t for c in data['lessons'] for s in c['sections'] for t in s.get('tables',[])
            if t.get('evidenceFile')=='validation-evidence/bag-current-validation.json']
assert len(bag_tables)==4 and all(t['evidenceSha256']==hashlib.sha256(bag_report.read_bytes()).hexdigest() for t in bag_tables)
model_tables=[t for c in data['lessons'] for s in c['sections'] for t in s.get('tables',[])
              if t.get('evidenceFile') in ('validation-evidence/model-current-validation.json','validation-evidence/model-boundaries-current-validation.json')]
assert len(model_tables)==4 and all(t['evidenceSha256']==hashlib.sha256((ROOT/t['evidenceFile']).read_bytes()).hexdigest() for t in model_tables)
drive_report=ROOT/'validation-evidence/drive-current-validation.json'
drive=json.loads(drive_report.read_text())
drive_tables=[(c['id'],t) for c in data['lessons'] for s in c['sections'] for t in s.get('tables',[])
              if t.get('evidenceFile')=='validation-evidence/drive-current-validation.json']
assert drive['passed'] and len(drive_tables)==3
assert {chapter for chapter,_ in drive_tables}=={'eco-control-framework','eco-diff-drive-tracks','eco-state-estimation'}
assert all(t['evidenceSha256']==hashlib.sha256(drive_report.read_bytes()).hexdigest() for _,t in drive_tables)
for name,digest in drive['sourceHashes'].items():
    assert hashlib.sha256((ROOT/'examples'/name).read_bytes()).hexdigest()==digest, name
assert drive['handoff']['newRawMessages']==0 and drive['handoff']['newFusedMessages']>=2
sensor_report=ROOT/'validation-evidence/gazebo-sensors-current-validation.json'
sensor=json.loads(sensor_report.read_text())
sensor_tables=[(c['id'],t) for c in data['lessons'] for s in c['sections'] for t in s.get('tables',[])
               if t.get('evidenceFile')=='validation-evidence/gazebo-sensors-current-validation.json']
assert sensor['passed'] and len(sensor_tables)==3
assert {chapter for chapter,_ in sensor_tables}=={'eco-gazebo-simulation','eco-perception-pipeline'}
assert all(t['evidenceSha256']==hashlib.sha256(sensor_report.read_bytes()).hexdigest() for _,t in sensor_tables)
for name,digest in sensor['sourceHashes'].items():
    assert hashlib.sha256((ROOT/'examples/gazebo_labs'/name).read_bytes()).hexdigest()==digest, name
capture=next(f for f in data['figures'] if f['id']=='gazebo-sensor-captures')
assert capture['evidenceSha256']==hashlib.sha256(sensor_report.read_bytes()).hexdigest()
image_nodes=ET.parse(DIST/capture['file']).getroot().findall('.//{http://www.w3.org/2000/svg}image')
assert len(image_nodes)==2
for node,name in zip(image_nodes,('camera.png','edges.png')):
    raw=base64.b64decode(node.attrib['href'].removeprefix('data:image/png;base64,'),validate=True)
    assert hashlib.sha256(raw).hexdigest()==sensor['camera']['imageSha256'][name]
assert next(r for r in data['resources'] if r['id']=='sensor-bridge-config')['localPath'].endswith('/ros_gz_bridge/README.md')
nav_report=ROOT/'validation-evidence/nav2-planning-current-validation.json'
nav_portable=ROOT/'validation-evidence/nav2-planning-portable-current-validation.json'
nav_run,nav_unpack=(json.loads(path.read_text()) for path in (nav_report,nav_portable))
assert nav_run['passed'] and nav_unpack['passed'] and nav_run['domainId']!=nav_unpack['domainId']
assert nav_run['sourceHashes']==nav_unpack['sourceHashes']
for name,digest in nav_run['sourceHashes'].items():
    assert hashlib.sha256((ROOT/'examples'/name).read_bytes()).hexdigest()==digest,name
with zipfile.ZipFile(DIST/'downloads/atlas_examples.zip') as archived_examples:
    for name,digest in nav_run['sourceHashes'].items():
        assert hashlib.sha256(archived_examples.read('atlas_examples/'+name)).hexdigest()==digest,name
nav_tables=[(c['id'],t) for c in data['lessons'] for s in c['sections'] for t in s.get('tables',[])
            if t.get('evidenceFile')=='validation-evidence/nav2-planning-current-validation.json']
assert len(nav_tables)==4 and {chapter for chapter,_ in nav_tables}=={'eco-nav2-stack','eco-state-estimation','eco-nav2-task-programming'}
assert all(t['evidenceSha256']==hashlib.sha256(nav_report.read_bytes()).hexdigest() for _,t in nav_tables)
nav_figure=next(f for f in data['figures'] if f['id']=='nav2-costmap-planning')
assert nav_figure['evidenceSha256']==hashlib.sha256(nav_report.read_bytes()).hexdigest()
assert {p['chapter'] for p in nav_figure['placements']}=={'eco-nav2-stack','theory-planning'}
assert nav_run['costmap']['isPathValid']=={'static':True,'oldAfterMarking':False,'detour':True}
assert nav_run['costmap']['oldPathNewLethalCellIndices'] and not nav_run['costmap']['detourRejectedCells']
for key,details in nav_run['costmap']['snapshots'].items():
    capture_path=ROOT/'validation-evidence/nav2-grid-captures'/details['file']
    assert hashlib.sha256(capture_path.read_bytes()).hexdigest()==details['sha256']
    assert capture_path.stat().st_size==nav_run['costmap']['size'][0]*nav_run['costmap']['size'][1],key
slam_revision=json.loads((ROOT/'source/slam-mapping-revision.json').read_text())['meta']
slam_report=ROOT/slam_revision['report']
slam_run,slam_unpack=(json.loads(path.read_text()) for path in (slam_report,ROOT/slam_revision['portableReport']))
assert slam_run['passed'] and slam_unpack['passed'] and slam_run['domainId']!=slam_unpack['domainId']
slam_tables=[(c['id'],t) for c in data['lessons'] for s in c['sections'] for t in s.get('tables',[])
             if t.get('evidenceFile')==slam_revision['report']]
assert len(slam_tables)==5 and {chapter for chapter,_ in slam_tables}=={'eco-slam-mapping','theory-slam','eco-state-estimation'}
assert all(t['evidenceSha256']==hashlib.sha256(slam_report.read_bytes()).hexdigest() for _,t in slam_tables)
for name,digest in slam_revision['captureHashes'].items():
    assert hashlib.sha256((ROOT/'validation-evidence/slam-mapping-captures'/name).read_bytes()).hexdigest()==digest,name
assert hashlib.sha256((ROOT/slam_revision['finding']).read_bytes()).hexdigest()==slam_revision['findingSha256']
for run in (slam_run,slam_unpack):
    assert run['artifacts']['rasterCompared']['changedCells']==0 and run['restore']['compared']['changedCells']==0
    assert run['restore']['graph']['mappingNodes']==37 and run['restore']['continuedGraph']['mappingNodes']==41
    local=run['localization']
    assert local['rollingMapCompared']['changedCells']==8 and local['clearedMapCompared']['changedCells']==0
    assert local['rollingCellTransitions']=={'0→100':2,'-1→100':4,'-1→0':2} and local['originalGraphFilesIntact']
assert slam_run['sourceHashes']==slam_unpack['sourceHashes']
examples_archive=DIST/'downloads/atlas_examples.zip'
with zipfile.ZipFile(examples_archive) as archived_examples:
    for name,digest in slam_run['sourceHashes'].items():
        assert hashlib.sha256(archived_examples.read('atlas_examples/'+name)).hexdigest()==digest,name
slam_figure=next(f for f in data['figures'] if f['id']=='slam-mapping-trajectory')
assert slam_figure['evidenceSha256']==hashlib.sha256(slam_report.read_bytes()).hexdigest()
assert hashlib.sha256((DIST/slam_figure['file']).read_bytes()).hexdigest()==slam_figure['assetSha256']
assert {p['chapter'] for p in slam_figure['placements']}=={'eco-slam-mapping','theory-slam'}
exec_meta=json.loads((ROOT/'source/nav2-execution-revision.json').read_text())['meta']
exec_report=ROOT/exec_meta['report']
exec_run,exec_unpack=(json.loads(path.read_text()) for path in (exec_report,ROOT/exec_meta['portableReport']))
assert exec_run['passed'] and exec_unpack['passed'] and exec_run['domainId']!=exec_unpack['domainId']
assert exec_run['sourceHashes']==exec_unpack['sourceHashes']
assert hashlib.sha256(examples_archive.read_bytes()).hexdigest()==exec_unpack['sourceArchive']['sha256']
with zipfile.ZipFile(examples_archive) as archived_examples:
    assert len(archived_examples.namelist())==exec_unpack['sourceArchive']['files']
    for name,digest in exec_run['sourceHashes'].items():
        assert hashlib.sha256(archived_examples.read('atlas_examples/'+name)).hexdigest()==digest,name
for run in (exec_run,exec_unpack):
    assert run['map']['dataSha256']==slam_run['mapping']['learnedMap']['dataSha256']
    assert run['map']['comparedRaw'] and run['map']['receivedBytes']==13426
    expected={'arrival':(4,0),'cancel':(5,0),'outside_map':(6,204),'invalid_controller':(6,101),'restored_controller':(4,0)}
    assert {name:(stage['status'],stage['errorCode']) for name,stage in run['scenarios'].items()}==expected
    stopped=run['scenarios']['cancel']
    assert stopped['cancelingIds']==[stopped['uuid']] and 0.0<stopped['travelAfterCancelM']<0.42
    assert stopped['truthStop']['stillFromNs']>stopped['resultRosNs']
    assert run['scenarios']['arrival']['yawErrorRad']<0.28
for name,digest in exec_meta['captureHashes'].items():
    assert hashlib.sha256((ROOT/'validation-evidence/nav2-execution-captures'/name).read_bytes()).hexdigest()==digest,name
for name,digest in exec_meta['findingHashes'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
exec_tables=[t for c in data['lessons'] for s in c['sections'] for t in s.get('tables',[]) if t.get('evidenceFile')==exec_meta['report']]
assert len(exec_tables)==5 and all(t['evidenceSha256']==hashlib.sha256(exec_report.read_bytes()).hexdigest() for t in exec_tables)
exec_figure=next(f for f in data['figures'] if f['id']=='nav2-execution-stop')
assert exec_figure['evidenceSha256']==hashlib.sha256(exec_report.read_bytes()).hexdigest()
assert hashlib.sha256((DIST/exec_figure['file']).read_bytes()).hexdigest()==exec_figure['assetSha256']
assert {p['chapter'] for p in exec_figure['placements']}=={'eco-nav2-stack','eco-nav2-task-programming'}
model=next(c for c in data['lessons'] if c['id']=='eco-model-rviz')
model_blocks=[b for s in model['sections'] for b in s.get('codeBlocks',[])]+[s for s in model['steps'] if isinstance(s,dict)]
assert not any('xacro robot.urdf.xacro' in b.get('code','') for b in model_blocks),'正文与快捷步骤都不能引用未提供的Xacro'
for extension in ('minimal.urdf','robot.urdf.xacro'):
    example=next(f for f in data['exampleFiles'] if f['path']=='model_labs/learning_description/urdf/'+extension)
    assert example['language']=='xml' and example['code']==(ROOT/'examples'/example['path']).read_text()
for chapter in data['lessons']:
    blocks=chapter.get('commands',[])+[b for s in chapter['sections'] for b in s.get('codeBlocks',[])]
    for block in blocks:
        lines=block.get('code','').splitlines()
        for index,line in enumerate(lines):
            if line.startswith('ros2 bag play') and '--clock' not in line:
                assert '--clock发布回放时钟' not in '\n'.join(lines[max(0,index-1):index]),(chapter['id'],line)
            if line.startswith('ros2 bag play turtle_'):
                assert line.count('--topics')==1 and '--topics /turtle1/cmd_vel' in line,(chapter['id'],line)
for a in data['apiReferences']:
    assert a['lessons'] and set(a['lessons'])<=ids,a['id']
    assert a['rows'] and all(len(row)==len(a['columns']) for row in a['rows']),a['id']
for c in data['comparisons']:
    assert len(c['variants'])>=2 and c['relatedLessons'],c['id']
    assert set(c['relatedLessons'])<=ids,c['id']
    assert all(re.search(r'[\u4e00-\u9fff]',v['code']) for v in c['variants']),(c['id'],'对照缺少中文注释')
for c in data['catalog']:assert c.get('lessons') and all(id in ids for id in c['lessons']),c

# 站内正文、独立源码和章节下载必须使用同一个已核查版本。
nav=(ROOT/'examples/navigation/bounded_navigation.py').read_text()
for chapter_id in ('eco-nav2-task-programming','project-navigation'):
    blocks=[b for c in data['lessons'] if c['id']==chapter_id for s in c['sections'] for b in s.get('codeBlocks',[]) if b['label']=='bounded_navigation.py']
    assert len(blocks)==1 and blocks[0]['type']=='complete' and blocks[0]['code']==nav,chapter_id
assert hashlib.sha256(nav.encode()).hexdigest()==json.loads((ROOT/'source/navigation-revision.json').read_text())['meta']['codeSha256']
assert len(data['coverage']['entries'])==627
for entry in data['coverage']['entries']:
    assert set(entry['relatedLessons'])<=ids,entry['id']
    assert entry.get('depthReason') and entry.get('reviewLevel'),entry['id']
    assert (ROOT.parent/(entry.get('file') or entry['localPath'])).is_file(),entry['id']
assert len(data['library']['repositories'])==110 and len(data['library']['snapshots'])==162
for snapshot in data['library']['snapshots']:
    assert (ROOT.parent/snapshot['localPath']).is_dir(),snapshot['id']
    assert (ROOT.parent/snapshot['entryPath']).is_file(),snapshot['id']

book=Page((DIST/'book.html').read_text())
assert book.scripts==0,'reading edition must not require JavaScript'
assert not book.assets,'reading edition must be a self-contained file'
for href in book.hrefs:
    if href.startswith('#'):assert href[1:] in book.ids,href
assert all('chapter-'+id in book.ids for id in ids)
shell=Page((DIST/'index.html').read_text())
for asset in shell.assets:
    assert not re.match(r'https?://|//',asset),('remote dependency',asset)
    assert (DIST/asset).is_file(),asset
guide=(DIST/'downloads/ros2-learning-guide.md').read_text()
for c in data['lessons']:
    assert c['validation'] in guide,(c['id'],'missing Markdown validation scope')
    for table in c.get('apiReferences',[]):assert markdown_table(table) in guide,(c['id'],'broken API Markdown table')
    for section in c['sections']:
        for table in section.get('tables',[]):
            assert markdown_table(table) in guide,(c['id'],'broken experiment Markdown table')
            assert hashlib.sha256((ROOT/table['evidenceFile']).read_bytes()).hexdigest()==table['evidenceSha256']
        for p in section.get('paragraphs',[]):assert p in guide,(c['id'],'missing Markdown paragraph')
    for exercise in c['exercises']:assert exercise['answer'] in guide,(c['id'],'missing answer')
# 录制输出与实时海龟输出不能被快捷回放同时混到同一pose话题。
bag=next(c for c in data['lessons'] if c['id']=='time-bag')
for code in [b['code'] for b in bag['commands']]+[b['code'] for s in bag['sections'] for b in s.get('codeBlocks',[])]:
    for line in code.splitlines():
        if line.startswith('ros2 bag play turtle_session'):assert '--topics /turtle1/cmd_vel' in line,line
with zipfile.ZipFile(DIST/'downloads/chapter-code.zip') as archive:
    manifest=json.loads(archive.read('manifest.json'))
    assert len(manifest)==checked_codes
    assert all(x['file'] in archive.namelist() for x in manifest)
    for item,(chapter,label,code) in zip(manifest,expected_complete):
        assert item['chapter']==chapter and item['label']==label,item
        assert archive.read(item['file']).decode()==code,('章节下载与正文代码不一致',chapter,label)
    for item in manifest:
        if item.get('label')=='bounded_navigation.py':assert archive.read(item['file']).decode()==nav
for name,prefix in [('atlas_examples.zip','atlas_examples'),('foundation_examples.zip','foundation_examples')]:
    with zipfile.ZipFile(DIST/'downloads'/name) as archive:
        assert f'{prefix}/README.md' in archive.namelist()
        source_root=ROOT/('examples' if name=='atlas_examples.zip' else 'foundation-examples')
        assert archive.read(f'{prefix}/LICENSE')==(source_root/'LICENSE').read_bytes(),'独立工程下载应携带自身许可证'
        assert archive.testzip() is None
        assert not any('/build/' in x or '/install/' in x or '/__pycache__/' in x for x in archive.namelist())
        if name=='atlas_examples.zip':
            for chapter in data['lessons']:
                for section in chapter['sections']:
                    for block in section.get('codeBlocks',[]):
                        if block.get('sourceFile'):
                            relative=Path(block['sourceFile']).relative_to('examples')
                            assert archive.read((Path(prefix)/relative).as_posix()).decode()==block['code'],('工程ZIP与正文不同源',relative)
with zipfile.ZipFile(ROOT/'deliverables/ros2-learning-hub-offline.zip') as archive:
    names=archive.namelist()
    assert 'ros2-learning-hub/book.html' in names
    assert 'ros2-learning-hub/downloads/atlas_examples.zip' in names
    assert 'ros2-learning-hub/downloads/foundation_examples.zip' in names
    assert 'ros2-learning-hub/downloads/validation-evidence.zip' in names
    assert '{workspace:false}' in archive.read('ros2-learning-hub/environment.js').decode()
    assert not any('/.openai/' in x or '/.qa/' in x or '/node_modules/' in x for x in names)
    assert archive.testzip() is None
    # 检查当前正式产物都已重打包，防止正文更新后仍交付旧 ZIP。
    for name in names:
        relative=Path(name).relative_to('ros2-learning-hub')
        if relative.as_posix()!='environment.js':assert archive.read(name)==(DIST/relative).read_bytes(),('stale archive',name)
archive_path=ROOT/'deliverables/ros2-learning-hub-offline.zip'
assert hashlib.sha256(archive_path.read_bytes()).hexdigest()==(ROOT/'deliverables/SHA256SUMS').read_text().split()[0]
print(json.dumps(dict(passed=True,chapters=len(ids),minimumSectionChineseCharacters=minimum,
                     chapterChineseCharacters=data['meta']['proseChineseCharacters'],
                     exercises=data['meta']['exerciseCount'],codeBlocks=data['meta']['codeBlockCount'],
                     completeCodeFiles=checked_codes,sourceMappings=len(data['catalog'])),ensure_ascii=False))
