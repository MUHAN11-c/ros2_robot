"""Validate delivered content, exports, code syntax and offline assets."""
import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
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

assert len(data['lessons'])==44
assert data['meta']['expandedChapters']==44
assert len(data['comparisons'])>=12
assert len(data['resources'])>=132
assert len(data['catalog'])==169
ids={c['id'] for c in data['lessons']}
checked_codes=0
minimum=100000
for c in data['lessons']:
    assert len(c['sections'])>=5,c['id']
    prose=''.join(''.join(s.get('paragraphs',[])+s.get('bullets',[])) for s in c['sections'])
    count=len(re.findall(r'[\u4e00-\u9fff]',prose))
    minimum=min(minimum,count)
    assert count>=1200,(c['id'],'not enough explanatory prose',count)
    assert len(c.get('exercises',[]))>=3,c['id']
    assert all(x['question'] and x['answer'] for x in c['exercises']),c['id']
    assert c.get('workedExample',{}).get('steps'),c['id']
    for s in c['sections']:
        for b in s.get('codeBlocks',[]):
            assert b['type'] in ('complete','snippet','commands','concept'),(c['id'],b['type'])
            if b['type']!='complete':continue
            label=c['id']+'/'+b['label']
            if b['language']=='python':ast.parse(b['code'],filename=label)
            elif b['language']=='xml':ET.fromstring(b['code'])
            elif b['language']=='json':json.loads(b['code'])
            elif b['language']=='bash':
                result=subprocess.run(['bash','-n'],input=b['code'],text=True,capture_output=True)
                assert result.returncode==0,(label,result.stderr)
            checked_codes+=1
for c in data['catalog']:assert c.get('lessons') and all(id in ids for id in c['lessons']),c

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
    for section in c['sections']:
        for p in section.get('paragraphs',[]):assert p in guide,(c['id'],'missing Markdown paragraph')
    for exercise in c['exercises']:assert exercise['answer'] in guide,(c['id'],'missing answer')
with zipfile.ZipFile(DIST/'downloads/chapter-code.zip') as archive:
    manifest=json.loads(archive.read('manifest.json'))
    assert len(manifest)==checked_codes
    assert all(x['file'] in archive.namelist() for x in manifest)
with zipfile.ZipFile(ROOT/'deliverables/ros2-learning-hub-offline.zip') as archive:
    names=archive.namelist()
    assert 'ros2-learning-hub/book.html' in names
    assert 'ros2-learning-hub/downloads/atlas_examples.zip' in names
    assert not any('/.openai/' in x or '/.qa/' in x or '/node_modules/' in x for x in names)
    assert archive.testzip() is None
print(json.dumps(dict(passed=True,chapters=len(ids),minimumSectionChineseCharacters=minimum,
                     chapterChineseCharacters=data['meta']['proseChineseCharacters'],
                     exercises=data['meta']['exerciseCount'],codeBlocks=data['meta']['codeBlockCount'],
                     completeCodeFiles=checked_codes,sourceMappings=len(data['catalog'])),ensure_ascii=False))
