"""A single-file, script-free reading edition and a complete chapter-code archive."""
from html import escape
from pathlib import Path
import json
import re
import zipfile
from math_render import equation_html, equation_markdown

def inline(value):
    value=escape(str(value))
    value=re.sub(r'`([^`]+)`',r'<code>\1</code>',value)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',value)

def paragraph(value):
    return '<p>'+inline(value)+'</p>'

def ul(items):
    return '<ul>'+''.join('<li>'+inline(x)+'</li>' for x in items)+'</ul>'

def code(value,language='text',label='',kind='snippet'):
    names={'complete':'完整文件','snippet':'局部片段','commands':'终端命令','concept':'概念示意'}
    return '<figure class="code"><figcaption>'+escape(label)+' · '+escape(language)+' · '+names.get(kind,'局部片段')+'</figcaption><pre><code>'+escape(value)+'</code></pre></figure>'

def expanded_markdown(chapter):
    out=[]
    for s in chapter.get('sections',[]):
        out.extend(['### '+s['title'],*s.get('paragraphs',[]),*['- '+x for x in s.get('bullets',[])]])
        for eq in s.get('equations',[]):out.extend(equation_markdown(eq))
        for b in s.get('codeBlocks',[]):out.extend(['#### '+b['label'],'代码类型：'+b['type'],'```'+b['language'],b['code'],'```',b.get('explanation','')])
    x=chapter.get('workedExample')
    if x:out.extend(['### '+x['title'],x['scenario'],*[f'{i+1}. {s}' for i,s in enumerate(x['steps'])],'验收：'+x['result']])
    for i,x in enumerate(chapter.get('exercises',[]),1):out.extend([f'### 深入练习 {i}',x['question'],'参考答案：'+x['answer']])
    return out

CSS='''
:root{color-scheme:light;--ink:#20372d;--muted:#63756b;--line:#dbe3d7;--paper:#fafbf7;--green:#2e5d47}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;color:var(--ink);background:var(--paper);font:16px/1.9 "Noto Sans CJK SC","Microsoft YaHei",sans-serif}a{color:var(--green);text-underline-offset:3px}h1,h2,h3,h4{line-height:1.5;overflow-wrap:anywhere}.code figcaption{overflow-wrap:anywhere}h1{font:700 42px/1.5 "Noto Serif CJK SC",serif}h2{font-size:30px}h3{font-size:23px;margin-top:38px}h4{font-size:18px;margin-top:24px}p,li{overflow-wrap:anywhere}.cover{max-width:1000px;margin:60px auto;padding:50px;background:#ecf1e7;border:1px solid var(--line)}.kicker{font:12px monospace;letter-spacing:3px;color:#ae603d}.cover p{color:var(--muted)}.book-nav{max-width:1000px;margin:auto;padding:0 50px 45px;columns:2;column-gap:35px}.book-nav a{display:block;text-decoration:none;font-size:13px;padding:7px 0;break-inside:avoid;border-bottom:1px solid var(--line)}main{max-width:1000px;margin:auto;padding:0 50px 60px}.chapter{padding:38px 0 60px;border-top:2px solid var(--green)}.chapter-meta{font-size:12px;color:var(--muted)}.lead{font-size:19px;color:var(--muted)}.goals,.note{padding:20px 25px;background:#eef3e9;border-left:3px solid var(--green);margin:25px 0}.code{margin:25px 0;background:#192b25;color:#e4eee0;border:1px solid #344f3e;border-radius:6px;overflow:hidden}.code figcaption{padding:9px 15px;border-bottom:1px solid #ffffff20;font:11px/1.8 monospace}.code pre{margin:0;overflow:auto;padding:18px;font:12px/1.85 "DejaVu Sans Mono",monospace}.code code{background:none;padding:0;font:inherit;white-space:pre;color:inherit}code{font-family:monospace;background:#e6eddf;padding:2px 4px;border-radius:3px}ul,ol{padding-left:24px}li{margin:8px 0}.explanation{padding-left:20px;border-left:2px solid var(--line);font-size:14px;color:var(--muted)}.exercise{padding:20px 24px;border:1px solid var(--line);margin:20px 0;background:white}.exercise h4{margin-top:0}.answer{font-size:14px;padding:12px 0 0;border-top:1px solid var(--line)}details.sources{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:18px;margin-top:25px}summary{cursor:pointer}.back{font-size:12px;display:block;text-align:right;margin-top:25px}.appendix{margin-top:40px;border-top:2px solid var(--green);padding-top:30px}.source-list{font-size:12px}.source-list li{margin:14px 0}.code-file{margin:22px 0}footer{font-size:12px;color:var(--muted);padding:40px;text-align:center}
@media(max-width:700px){body{font-size:14px}.cover{margin:20px;padding:25px}h1{font-size:31px}h2{font-size:25px}h3{font-size:20px}.book-nav{padding:0 25px 25px;columns:1}main{padding:0 25px 35px}.code pre{font-size:11px}.lead{font-size:16px}}
@media print{@page{size:A4;margin:18mm}.cover{margin:0;padding:20px;break-after:page}.book-nav{columns:1;font-size:10px;break-after:page}main{padding:0}.chapter{break-before:page}body{background:white;font-size:11px}.code{background:#f5f5f5;color:#111;break-inside:avoid;border-color:#ccc}.code pre{white-space:pre-wrap;font-size:8px}.code code{white-space:pre-wrap}.code figcaption{border-color:#ccc}h2{font-size:23px}h3{font-size:17px}.lead{font-size:13px}.back{display:none}.exercise{break-inside:avoid}a{color:inherit;text-decoration:none}}
'''

def build_book(data,out):
    sources={r['id']:r for r in data['resources']}
    chunks=['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ROS 2 综合离线教材 · 完整连续阅读版</title><style>'+CSS+'</style></head><body>']
    chunks.append('<header class="cover" id="contents"><div class="kicker">ROS 2 / THE COMPLETE LEARNING TEXTBOOK</div><h1>ROS 2 综合学习教材</h1><p>Jazzy · Ubuntu 24.04 · 2026-11-06</p><p>按章理解原理、创建文件、执行实验、解释结果与排查问题。这个单文件包含完整正文、代码和答案；关闭网络仍可阅读，无需 JavaScript。</p><p>外部链接仅为出处。软件安装、源码下载和首次依赖准备仍需要已有离线软件源或联网环境。</p><p><a href="index.html">返回交互教材</a> · 浏览器 Ctrl/Cmd+F 全文查找 · 打印为纸质讲义</p></header>')
    chunks.append('<nav class="book-nav" aria-label="全书目录">'+''.join(f'<a href="#chapter-{c["id"]}">{i+1:02d} · {escape(c["title"])}</a>' for i,c in enumerate(data['lessons']))+'<a href="#comparisons">附录 A · 全部不同写法对照</a><a href="#projects">附录 B · 五个综合项目</a><a href="#examples">附录 C · 完整示例工程文件</a><a href="#bibliography">附录 D · 全部参考来源</a></nav><main>')
    for i,c in enumerate(data['lessons'],1):
        chunks.append(f'<article class="chapter" id="chapter-{c["id"]}"><div class="kicker">CHAPTER {i:02d}</div><h2>{escape(c["title"])}</h2><p class="lead">{inline(c["summary"])}</p><p class="chapter-meta">{escape(c.get("version","Jazzy"))} · {escape(c.get("validation","资料核对；具体运行结果需另行验证"))}</p><div class="goals"><strong>学习目标</strong>{ul(c["goals"])}</div>')
        prerequisites=c.get('prerequisites','')
        if prerequisites:chunks.append('<h3>开始之前</h3>'+paragraph('；'.join(prerequisites) if isinstance(prerequisites,list) else prerequisites))
        chunks.append('<h3>建立整体认识</h3>'+''.join(paragraph(p) for p in c['concepts']))
        for j,s in enumerate(c.get('sections',[]),1):
            chunks.append(f'<section id="chapter-{c["id"]}-part-{j}"><h3>{j}. {escape(s["title"])}</h3>'+''.join(paragraph(p) for p in s.get('paragraphs',[]))+ul(s.get('bullets',[])))
            chunks.extend(equation_html(eq) for eq in s.get('equations',[]))
            for b in s.get('codeBlocks',[]):chunks.append(code(b['code'],b['language'],b['label'],b['type'])+'<div class="explanation">'+paragraph(b.get('explanation',''))+'</div>')
            for fig in data.get('figures',[]):
                if any(p['chapter']==c['id'] and p['afterSection']==j-1 for p in fig.get('placements',[])):
                    chunks.append(book_figure(fig,out,c['id']))
            chunks.append('</section>')
        x=c.get('workedExample')
        if x:chunks.append('<h3>'+escape(x['title'])+'</h3>'+paragraph(x['scenario'])+'<ol>'+''.join('<li>'+inline(s)+'</li>' for s in x['steps'])+'</ol><div class="note"><strong>结果与验收</strong>'+paragraph(x['result'])+'</div>')
        chunks.append('<h3>基础验证流程</h3>')
        for s in c['steps']:
            if isinstance(s,str):chunks.append(paragraph(s))
            else:
                chunks.append('<h4>'+escape(s['title'])+'</h4>'+paragraph(s.get('body','')))
                if s.get('code'):chunks.append(code(s['code'],s.get('language','bash'),s['title'],s.get('type','commands')))
        for b in c.get('commands',[]):chunks.append(code(b['code'],b.get('language','bash'),b['label'],b.get('type','commands')))
        chunks.append('<div class="note"><strong>预期现象</strong>'+ul(c['expected'])+'</div><h3>常见问题</h3>'+ul(c['pitfalls']))
        exercises=[*c.get('exercises',[]),dict(question=c['exercise'],answer=c['exerciseAnswer'])]
        chunks.append('<h3>练习与参考答案</h3>')
        for j,x in enumerate(exercises,1):chunks.append(f'<section class="exercise"><h4>练习 {j}</h4>{paragraph(x["question"])}<div class="answer"><strong>参考答案</strong>{paragraph(x["answer"])}</div></section>')
        chunks.append('<details class="sources"><summary>本章出处与延伸阅读（联网可访问）</summary><ul>'+''.join(f'<li><a href="{escape(sources[id]["url"],quote=True)}">{escape(sources[id]["title"])}</a> · {escape(sources[id]["version"])}</li>' for id in c['sourceIds'])+'</ul></details><a class="back" href="#contents">返回全书目录 ↑</a></article>')
    chunks.append('<section class="appendix" id="comparisons"><h2>附录 A · 全部不同写法对照</h2>')
    for c in data['comparisons']:
        chunks.append('<h3>'+escape(c['title'])+'</h3>'+paragraph(c['question']))
        for v in c['variants']:chunks.append('<h4>'+escape(v['label'])+'</h4>'+paragraph(v.get('scope',''))+code(v['code'],v['language'],v['label'],v.get('type','snippet')))
        chunks.append(ul(c['notes']))
    chunks.append('</section><section class="appendix" id="projects"><h2>附录 B · 综合项目</h2>')
    for p in data['projects']:chunks.append('<h3>'+escape(p['title'])+'</h3>'+paragraph(p['summary'])+'<ol>'+''.join('<li>'+inline(x)+'</li>' for x in p['milestones'])+'</ol>'+code(p['code'],'bash','项目检查','commands')+paragraph(p['note']))
    chunks.append('</section><section class="appendix" id="examples"><h2>附录 C · 完整教学工程文件</h2>'+paragraph(data['meta']['exampleValidation']))
    for f in data.get('exampleFiles',[]):chunks.append('<section class="code-file"><h3>'+escape(f['path'])+'</h3>'+code(f['code'],f['language'],f['path'],'complete')+'</section>')
    chunks.append('</section><section class="appendix" id="bibliography"><h2>附录 D · 全部参考来源</h2><ol class="source-list">')
    for r in data['resources']:chunks.append('<li><a href="'+escape(r['url'],quote=True)+'">'+escape(r['title'])+'</a> · '+escape(r['version'])+paragraph(r['description'])+paragraph('核查方式：'+r['verification'])+'</li>')
    chunks.append('</ol><h3>两套教程的全部已有页面</h3><p>目录从已克隆源码提取，列出169页；外部网页未逐项联网复测。</p><ul class="source-list">')
    for r in data['catalog']:chunks.append('<li>'+escape(r['title'])+' · '+ ' / '.join('<a href="#chapter-'+id+'">离线对应章节</a>' for id in r.get('lessons',[]))+' · <a href="'+escape(r['url'],quote=True)+'">原出处</a></li>')
    chunks.append('</ul></section></main><footer>ROS 2 综合学习教材 · 原创综合说明 · 资料版本与来源见各章</footer></body></html>')
    (out/'book.html').write_text('\n'.join(chunks))
    manifest=[]
    with zipfile.ZipFile(out/'downloads/chapter-code.zip','w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('README.txt','本包保存详细教材标注为完整文件的代码。完整文件不等于完整项目；包依赖、文件安装位置、启动顺序与验证步骤见对应章节。普通片段未放入本包。\n')
        for c in data['lessons']:
            count=0
            for s in c.get('sections',[]):
                for b in s.get('codeBlocks',[]):
                    if b.get('type')!='complete':continue
                    count+=1
                    suffix={'cpp':'cpp','c++':'cpp','python':'py','yaml':'yaml','xml':'xml','cmake':'cmake','bash':'sh','json':'json'}.get(b['language'],'txt')
                    safe_name=f'{c["id"]}/{count:02d}.{suffix}'
                    archive.writestr(safe_name,b['code']+'\n')
                    manifest.append(dict(file=safe_name,chapter=c['title'],label=b['label'],explanation=b.get('explanation','')))
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    return dict(bookBytes=(out/'book.html').stat().st_size,completeCodeFiles=len(manifest))
