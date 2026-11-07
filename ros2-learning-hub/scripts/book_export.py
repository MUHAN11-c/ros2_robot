"""A single-file, script-free reading edition and a complete chapter-code archive."""
from html import escape
from pathlib import Path
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from math_render import equation_html, equation_markdown
from local_editions import inline_local_figures


def section_title(title):
    """旧稿有些标题带手写节号；统一从最终顺序生成章号和节号。"""
    return re.sub(r'^\d+[.．]\s*', '', title).strip()


def section_heading(level, title, anchor=None, number=None):
    identifier = f' id="{escape(anchor, quote=True)}"' if anchor else ''
    prefix = f'<span class="section-number">{escape(number)}</span> ' if number else ''
    return f'<h{level}{identifier}>{prefix}{escape(title)}</h{level}>'


def chapter_toc(entries):
    """使用本章已渲染标题的锚点和编号生成原生折叠目录。"""
    def links(items):
        rows = []
        for anchor, title, number, children in items:
            label = escape(f'{number}　{title}' if number else title)
            rows.append(f'<li><a href="#{escape(anchor, quote=True)}">{label}</a>{links(children)}</li>')
        return '<ul>' + ''.join(rows) + '</ul>' if rows else ''
    return '<details class="book-chapter-toc"><summary>本章目录</summary>' + links(entries) + '</details>'


def local_book_html(html, chapter_id):
    """把单章文件嵌入全书。小节链接随章加前缀，正文标题统一下移一级。"""
    def namespaced(anchor):
        # 正式阅读器从 part-0 开始，连续版历史深链接从 part-1 开始。
        anchor = re.sub(r'^part-(\d+)(?=-|$)', lambda match: f'part-{int(match[1]) + 1}', anchor)
        return f'chapter-{chapter_id}-{anchor}'

    def adjust_tag(match):
        tag = re.sub(r'^(</?h)([1-5])(?=[\s>])', lambda heading: heading[1] + str(int(heading[2]) + 1), match[0])
        tag = re.sub(r'\sid="([a-zA-Z0-9_-]+)"', lambda attr: f' id="{namespaced(attr[1])}"', tag)
        return re.sub(r'\shref="#([a-zA-Z0-9_-]+)"', lambda attr: f' href="#{namespaced(attr[1])}"', tag)

    return re.sub(r'<\/?[a-zA-Z](?:[^<>"\']|"[^"]*"|\'[^\']*\')*>', adjust_tag, html)


def api_html(item, anchor=None, number=None):
    """将章节内 API 对照输出为静态表格，不依赖 JavaScript。"""
    return ('<section class="api-reference'+(' experiment-table' if item.get('evidenceFile') else '')+'">'+section_heading(4,item['title'],anchor,number)+'<div class="table-scroll"><table><thead><tr>'
            + ''.join('<th>'+inline(x)+'</th>' for x in item['columns'])+'</tr></thead><tbody>'
            + ''.join('<tr>'+''.join('<td>'+inline(x)+'</td>' for x in row)+'</tr>' for row in item['rows'])
            + '</tbody></table></div>'+ul(item.get('notes', []))+'</section>')


def book_figure(item, out, chapter_id, anchor, number):
    """内嵌原创 SVG，给每次出现的定义和引用加唯一前缀。

    同图跨章复用时，marker、clipPath 和无障碍名称不能误引其他章的 ID。
    只嵌入项目原创图形目录；原始 SVG 结构与中文图注均保留。
    """
    file = (out/item['file']).resolve()
    if not file.is_relative_to((out/'preview/figures').resolve()):
        raise ValueError('图解文件必须位于原创图形目录')
    raw = file.read_text()
    ET.fromstring(raw)
    if '<script' in raw or re.search(r'\bon\w+\s*=', raw):
        raise ValueError('连续教材不嵌入可执行 SVG')
    prefix = 'book-'+chapter_id+'-'+item['id']
    identifiers = re.findall(r'\bid="([^"]+)"', raw)
    for identifier in identifiers:
        raw = raw.replace('id="'+identifier+'"', 'id="'+prefix+'-'+identifier+'"')
        raw = raw.replace('url(#'+identifier+')', 'url(#'+prefix+'-'+identifier+')')
        raw = raw.replace('href="#'+identifier+'"', 'href="#'+prefix+'-'+identifier+'"')
    raw = re.sub(r'aria-labelledby="([^"]+)"', lambda m: 'aria-labelledby="'+' '.join(prefix+'-'+x if x in identifiers else x for x in m[1].split())+'"', raw)
    raw = re.sub(r'<\?xml[^>]*\?>', '', raw)
    return '<figure class="book-figure">'+section_heading(4,item['title'],anchor,number)+raw+'<figcaption>'+escape(item['caption'])+'</figcaption></figure>'

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
    for index,s in enumerate(chapter.get('sections',[])):
        out.extend(['### '+s['title'],*s.get('paragraphs',[]),*['- '+x for x in s.get('bullets',[])]])
        for eq in s.get('equations',[]):out.extend(equation_markdown(eq))
        for table in s.get('tables',[]):
            out.extend(['#### '+table['title'],markdown_table(table)])
            out.append(table.get('caption',''))
        for b in s.get('codeBlocks',[]):out.extend(['#### '+b['label'],'代码类型：'+b['type'],'```'+b['language'],b['code'],'```',b.get('explanation','')])
        for figure in chapter.get('figures', []):
            if figure['afterSection'] == index:
                out.extend(['!['+figure['alt']+'](../'+figure['file']+')',figure['caption']])
    for item in chapter.get('apiReferences', []):
        out.extend(['### '+item['title'],markdown_table(item)])
        out.extend(item.get('notes', []))
    x=chapter.get('workedExample')
    if x:out.extend(['### '+x['title'],x['scenario'],*[f'{i+1}. {s}' for i,s in enumerate(x['steps'])],'验收：'+x['result']])
    for i,x in enumerate(chapter.get('exercises',[]),1):out.extend([f'### 深入练习 {i}',x['question'],'参考答案：'+x['answer']])
    return out


def markdown_table(item):
    """一个表格作为单一Markdown块输出，标题/分隔行/数据行之间不能插入空行。"""
    def row(cells):
        return '| '+' | '.join(str(cell).replace('|','\\|').replace('\n','<br>') for cell in cells)+' |'
    return '\n'.join([row(item['columns']),row(['---']*len(item['columns'])),*[row(cells) for cells in item['rows']]])

CSS='''
:root{color-scheme:light;--ink:#20372d;--muted:#63756b;--line:#dbe3d7;--paper:#fafbf7;--green:#2e5d47}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;color:var(--ink);background:var(--paper);font:16px/1.9 "Noto Sans CJK SC","Microsoft YaHei",sans-serif}a{color:var(--green);text-underline-offset:3px}h1,h2,h3,h4{line-height:1.5;overflow-wrap:anywhere}.code figcaption{overflow-wrap:anywhere}h1{font:700 42px/1.5 "Noto Serif CJK SC",serif}h2{font-size:30px}h3{font-size:23px;margin-top:38px}h4{font-size:18px;margin-top:24px}p,li{overflow-wrap:anywhere}.cover{max-width:1000px;margin:60px auto;padding:50px;background:#ecf1e7;border:1px solid var(--line)}.kicker{font:12px monospace;letter-spacing:3px;color:#ae603d}.cover p{color:var(--muted)}.book-nav{max-width:1000px;margin:auto;padding:0 50px 45px;columns:2;column-gap:35px}.book-nav a{display:block;text-decoration:none;font-size:13px;padding:7px 0;break-inside:avoid;border-bottom:1px solid var(--line)}main{max-width:1000px;margin:auto;padding:0 50px 60px}.chapter{padding:38px 0 60px;border-top:2px solid var(--green)}.chapter-meta{font-size:12px;color:var(--muted)}.lead{font-size:19px;color:var(--muted)}.goals,.note{padding:20px 25px;background:#eef3e9;border-left:3px solid var(--green);margin:25px 0}.code{margin:25px 0;background:#192b25;color:#e4eee0;border:1px solid #344f3e;border-radius:6px;overflow:hidden}.code figcaption{padding:9px 15px;border-bottom:1px solid #ffffff20;font:11px/1.8 monospace}.code pre{margin:0;overflow:auto;padding:18px;font:12px/1.85 "DejaVu Sans Mono",monospace}.code code{background:none;padding:0;font:inherit;white-space:pre;color:inherit}code{font-family:monospace;background:#e6eddf;padding:2px 4px;border-radius:3px}ul,ol{padding-left:24px}li{margin:8px 0}.explanation{padding-left:20px;border-left:2px solid var(--line);font-size:14px;color:var(--muted)}.exercise{padding:20px 24px;border:1px solid var(--line);margin:20px 0;background:white}.exercise h4{margin-top:0}.answer{font-size:14px;padding:12px 0 0;border-top:1px solid var(--line)}details.sources{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:18px;margin-top:25px}summary{cursor:pointer}.back{font-size:12px;display:block;text-align:right;margin-top:25px}.appendix{margin-top:40px;border-top:2px solid var(--green);padding-top:30px}.source-list{font-size:12px}.source-list li{margin:14px 0}.code-file{margin:22px 0}footer{font-size:12px;color:var(--muted);padding:40px;text-align:center}
@media(max-width:700px){body{font-size:14px}.cover{margin:20px;padding:25px}h1{font-size:31px}h2{font-size:25px}h3{font-size:20px}.book-nav{padding:0 25px 25px;columns:1}main{padding:0 25px 35px}.code pre{font-size:11px}.lead{font-size:16px}}
@media print{@page{size:A4;margin:18mm}.cover{margin:0;padding:20px;break-after:page}.book-nav{columns:1;font-size:10px;break-after:page}main{padding:0}.chapter{break-before:page}body{background:white;font-size:11px}.code{background:#f5f5f5;color:#111;break-inside:avoid;border-color:#ccc}.code pre{white-space:pre-wrap;font-size:8px}.code code{white-space:pre-wrap}.code figcaption{border-color:#ccc}h2{font-size:23px}h3{font-size:17px}.lead{font-size:13px}.back{display:none}.exercise{break-inside:avoid}a{color:inherit;text-decoration:none}}
'''

def build_book(data,out):
    sources={r['id']:r for r in data['resources']}
    extra_css='''
    .equation{margin:24px 0;padding:20px;border:1px solid var(--line);background:#f0f5eb;border-radius:6px}.equation figcaption{font-weight:650}.equation p{font-size:13px}.math-scroll,.table-scroll{max-width:100%;overflow-x:auto}.math-scroll{padding:20px 0}.math-scroll math{min-width:max-content}table{border-collapse:collapse;width:100%;font-size:12px}td,th{border:1px solid var(--line);padding:9px;vertical-align:top;text-align:left}th{background:#e8efe2}td{overflow-wrap:anywhere}.api-reference table{min-width:600px}.symbol-table td:first-child{min-width:80px}.formula-source{font-size:11px}.formula-source pre{white-space:pre-wrap;overflow-wrap:anywhere}.book-figure{margin:30px 0;padding:15px;border:1px solid var(--line);border-radius:6px;background:white}.book-figure h4{margin:0 0 14px}.book-figure>svg{display:block;width:100%;height:auto;max-height:550px}.book-figure figcaption{font-size:12px;color:var(--muted);margin-top:15px}.api-reference h4{font-size:17px}@media(max-width:600px){.equation{padding:12px}.book-figure{padding:10px}.api-reference table{font-size:11px}}@media print{.api-reference table{min-width:0;font-size:8px}.equation,.book-figure{break-inside:avoid}.formula-source{display:none}}
    '''
    extra_css += '''
    :is(.book-chapter-toc,.saved-chapter-toc){margin:24px 0;padding:12px 16px;border:1px solid var(--line);border-radius:6px;background:white;font-size:14px}
    :is(.book-chapter-toc,.saved-chapter-toc) summary{font-weight:650;color:var(--green)}
    :is(.book-chapter-toc,.saved-chapter-toc) ul{margin:8px 0;padding-inline-start:20px}
    .section-number{font:600 .75em monospace;color:var(--green);white-space:nowrap}
    .saved-chapter-toc .outline-index{margin-inline-end:.5em}
    .saved-chapter-toc .outline-caption{font-weight:650}
    .local-edition [data-section-number]::before{content:attr(data-section-number);font:600 .75em monospace;color:var(--green);margin-inline-end:.5em}
    @media print{:is(.book-chapter-toc,.saved-chapter-toc){display:none}}
    '''
    chunks=['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ROS 2 综合离线教材 · 完整连续阅读版</title><style>'+CSS+extra_css+'</style></head><body>']
    chunks.append('<header class="cover" id="contents"><div class="kicker">ROS 2 / THEORY INTO PRACTICE</div><h1>ROS 2 综合学习教材</h1><p>Jazzy · Ubuntu 24.04 · '+escape(data['meta']['checkedAt'])+'</p><p>按章理解原理、比较 API、创建文件、执行实验、解释结果与排查问题。这个单文件包含正文、公式、静态图解、代码和答案；关闭网络仍可阅读，无需 JavaScript。</p><p>软件环境与原始参考仓库保持独立。构建、数值、仿真和实机验证范围见各章与下载包记录。</p><p><a href="index.html">返回交互教材</a> · 浏览器 Ctrl/Cmd+F 全文查找 · 打印为纸质讲义</p></header>')
    chunks.append('<nav class="book-nav" aria-label="全书目录">'+''.join(f'<a href="#chapter-{c["id"]}">{i+1:02d} · {escape(c["title"])}</a>' for i,c in enumerate(data['lessons']))+'<a href="#comparisons">附录 A · 全部不同写法对照</a><a href="#projects">附录 B · 五个综合项目</a><a href="#examples">附录 C · 完整示例工程文件</a><a href="#bibliography">附录 D · 全部参考来源</a></nav><main>')
    for i,c in enumerate(data['lessons'],1):
        local = data.get('localEditions',{}).get('chapters',{}).get(c['id'])
        if local:
            body = inline_local_figures(local_book_html(local['document']['html'], c['id']), out.parent, data)
            chunks.append(f'<article class="chapter local-edition" id="chapter-{c["id"]}"><p class="chapter-meta">本地教材修订 · '+escape(local['savedAt'])+'</p>'+body+'<a class="back" href="#contents">返回全书目录 ↑</a></article>')
            continue
        prefix = 'chapter-' + c['id']
        entries = []
        def heading(title, slug, children=()):
            anchor = prefix + '-' + slug
            entries.append((anchor, title, None, children))
            return section_heading(3, title, anchor)
        chunks.append(f'<article class="chapter" id="{prefix}"><div class="kicker">CHAPTER {i:02d}</div><h2>{escape(c["title"])}</h2><p class="lead">{inline(c["summary"])}</p><p class="chapter-meta">{escape(c.get("version","Jazzy"))} · {escape(c.get("validation","资料核对；具体运行结果需另行验证"))}</p><div class="goals"><strong>学习目标</strong>{ul(c["goals"])}</div>')
        toc_index = len(chunks)
        chunks.append('')
        prerequisites=c.get('prerequisites','')
        if prerequisites:chunks.append('<h3>开始之前</h3>'+paragraph('；'.join(prerequisites) if isinstance(prerequisites,list) else prerequisites))
        chunks.append(heading('建立整体认识','overview')+''.join(paragraph(p) for p in c['concepts']))
        for j,s in enumerate(c.get('sections',[]),1):
            anchor = f'{prefix}-part-{j}'
            title, number, children = section_title(s['title']), f'{i}.{j}', []
            entries.append((anchor, title, number, children))
            chunks.append(f'<section id="{anchor}">'+section_heading(3,title,number=number)+''.join(paragraph(p) for p in s.get('paragraphs',[]))+ul(s.get('bullets',[])))
            chunks.extend(equation_html(eq) for eq in s.get('equations',[]))
            for table in s.get('tables',[]):
                item_index = len(children) + 1
                child_id, child_number = f'{anchor}-sub-{item_index}', f'{number}.{item_index}'
                children.append((child_id, table['title'], child_number, ()))
                chunks.append(api_html(dict(table,notes=[table['caption']] if table.get('caption') else []),child_id,child_number))
            for b in s.get('codeBlocks',[]):chunks.append(code(b['code'],b['language'],b['label'],b['type'])+'<div class="explanation">'+paragraph(b.get('explanation',''))+'</div>')
            for fig in data.get('figures',[]):
                if any(p['chapter']==c['id'] and p['afterSection']==j-1 for p in fig.get('placements',[])):
                    item_index = len(children) + 1
                    child_id, child_number = f'{anchor}-sub-{item_index}', f'{number}.{item_index}'
                    children.append((child_id, fig['title'], child_number, ()))
                    chunks.append(book_figure(fig,out,c['id'],child_id,child_number))
            chunks.append('</section>')
            if j == 1:
                for comparison in data['comparisons']:
                    if c['id'] in comparison.get('relatedLessons', []):
                        chunks.append(heading(comparison['title'],'writing-'+comparison['id'])+paragraph(comparison['question']))
                        for variant in comparison['variants']:
                            chunks.append('<h4>'+escape(variant['label'])+'</h4>'+code(variant['code'],variant['language'],variant['label'],variant.get('type','snippet'))+paragraph(variant.get('scope','')))
                        chunks.append(ul(comparison.get('notes', [])))
        apis = [item for item in data.get('apiReferences', []) if c['id'] in item['lessons']]
        if apis:
            children = [(f'{prefix}-api-details-sub-{j}', item['title'], None, ()) for j, item in enumerate(apis, 1)]
            chunks.append(heading('API 对照与调用边界','api-details',children))
            chunks.extend(api_html(item, child[0]) for item, child in zip(apis, children))
        x=c.get('workedExample')
        if x:chunks.append(heading(x['title'],'worked-example')+paragraph(x['scenario'])+'<ol>'+''.join('<li>'+inline(s)+'</li>' for s in x['steps'])+'</ol><div class="note"><strong>结果与验收</strong>'+paragraph(x['result'])+'</div>')
        children = []
        chunks.append(heading('动手验证','practice',children))
        for j,s in enumerate(c['steps'],1):
            if isinstance(s,str):chunks.append(paragraph(s))
            else:
                anchor = f'{prefix}-practice-sub-{len(children) + 1}'
                title = s.get('title') or f'步骤 {j}'
                children.append((anchor, title, None, ()))
                chunks.append(section_heading(4,title,anchor)+paragraph(s.get('body','')))
                if s.get('code'):chunks.append(code(s['code'],s.get('language','bash'),title,s.get('type','commands')))
        for b in c.get('commands',[]):chunks.append(code(b['code'],b.get('language','bash'),b['label'],b.get('type','commands')))
        chunks.append('<div class="note"><strong>预期现象</strong>'+ul(c['expected'])+'</div>'+heading('常见问题与边界','pitfalls')+ul(c['pitfalls']))
        exercises=[*c.get('exercises',[]),dict(question=c['exercise'],answer=c['exerciseAnswer'])]
        chunks.append(heading('练习与答案','exercises'))
        for j,x in enumerate(exercises,1):chunks.append(f'<section class="exercise"><h4>练习 {j}</h4>{paragraph(x["question"])}<div class="answer"><strong>参考答案</strong>{paragraph(x["answer"])}</div></section>')
        entries.append((prefix+'-sources','参考出处、版本与验证范围',None,()))
        chunks.append(f'<details class="sources" id="{prefix}-sources"><summary>参考出处、版本与验证范围</summary><ul>'+''.join(f'<li><a href="{escape(sources[id]["url"],quote=True)}">{escape(sources[id]["title"])}</a> · {escape(sources[id]["version"])}</li>' for id in c['sourceIds'])+'</ul></details><a class="back" href="#contents">返回全书目录 ↑</a></article>')
        chunks[toc_index] = chapter_toc(entries)
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
    chunks.append('</ol><h3>既有教程主题对应</h3><p>下列为原有两套教程的主题映射。三套教程的覆盖等级与缺失目标另见交互版对应表和来源 JSON；主题映射不代表逐段整合。</p><ul class="source-list">')
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
                    match=re.match(r'([A-Za-z0-9_./-]+)',b['label'])
                    candidate=match[1] if match else ''
                    if candidate and ('..' not in Path(candidate).parts) and not candidate.startswith('/') and ('.' in Path(candidate).name or Path(candidate).name=='Dockerfile'):
                        safe_name=f'{c["id"]}/{candidate}'
                    else:safe_name=f'{c["id"]}/{count:02d}.{suffix}'
                    if safe_name in archive.namelist():safe_name=f'{c["id"]}/{count:02d}-{Path(safe_name).name}'
                    # 保留正文源码字节；已带末尾换行的完整文件不再额外追加。
                    archive.writestr(safe_name,b['code'])
                    manifest.append(dict(file=safe_name,chapter=c['title'],label=b['label'],explanation=b.get('explanation','')))
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    return dict(bookBytes=(out/'book.html').stat().st_size,completeCodeFiles=len(manifest))
