/* 独立设计审查版：只读复用 ../dist 教材，所有学习记录写入自己的 storage key。
 * 渲染顺序：读取/约束数据 → 路由与正文 → 注册上下文实验 → 恢复锚点/对话框。
 * 不连接 ROS 或外部服务。未来组件的连接与数据生命周期由 labs.js 适配层负责。
 */
(() => {
  'use strict';
  const D=window.ROS2Hub,L=window.NarukamiLogic,V=window.NarukamiVisuals,M=window.NarukamiEditor,R=window.NarukamiVisualEditor,F=window.NarukamiFileStore,A=window.NarukamiAssets.assets;
  const $=id=>document.getElementById(id),E=L.esc,I=L.inline;
  const chapters=new Map(D.lessons.map(c=>[c.id,c])),sources=new Map(D.resources.map(r=>[r.id,r]));
  const KEY='ros2-narukami-design-review-v1',ids=[...chapters.keys()];
  const icons={search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',home:'<path d="m3 10 9-7 9 7v10H4V10m5 10v-7h6v7"/>',book:'<path d="M12 5v16M3 4h5a4 4 0 0 1 4 2 4 4 0 0 1 4-2h5v16h-5a5 5 0 0 0-4 2 5 5 0 0 0-4-2H3Z"/>',orbit:'<ellipse cx="12" cy="12" rx="9" ry="4" transform="rotate(-35 12 12)"/><circle cx="12" cy="12" r="3"/><path d="m17 4 2-1"/>',pen:'<path d="m15 4 5 5M4 20l5-1L21 7l-5-5L4 14v6Zm0 0 5-1-5-5"/>',folder:'<path d="M3 6h7l2 3h9v11H3V6Z"/>',image:'<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="2"/><path d="m3 17 6-5 4 4 3-3 5 5"/>',grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',moon:'<path d="M20 15a9 9 0 0 1-11-11 9 9 0 1 0 11 11Z"/>',sun:'<circle cx="12" cy="12" r="4"/><path d="M12 1v2m0 18v2M1 12h2m18 0h2M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2"/>',menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h1M3 12h1M3 18h1"/>',star:'<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9L12 3Z"/>',check:'<circle cx="12" cy="12" r="9"/><path d="m7.5 12 3 3 6-6"/>',download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',copy:'<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>'};
  const icon=name=>`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${icons[name]||icons.book}</svg>`;
  let state,storageAvailable=true,activeChapter='',noteChapter='',toastTimer,noteTimer,codeStore=[],comparisonSequence=0,searchKind='全部',searchActive=0,wideReturn=null;
  let directoryHandle=null,fileSaving=false,editEpoch=0;
  const diskEditions=window.ROS2LocalEditions||F.empty();
  let viewMode='read',draftChapter='',draftTimer,draftUndo=null,visualSession=null,sourceBaseline='',pendingPosition=null,pendingLabs=[];
  try{state=L.sanitize(JSON.parse(localStorage.getItem(KEY)||localStorage.getItem('ros2-atlas-v1')||'null'),ids);}catch{state=L.sanitize(null,ids);}
  // 磁盘教材是可跨浏览器恢复的持久来源；只保留比磁盘保存时间更新的浏览器修改。
  for(const [id,record] of Object.entries(diskEditions.chapters)){
    if(!chapters.has(id))continue;
    const newest=Math.max(Date.parse(state.drafts[id]?.updatedAt)||0,Date.parse(state.visualDrafts[id]?.updatedAt)||0);
    if(newest>Date.parse(record.savedAt))continue;
    const restored=L.sanitize({drafts:record.document.markdownDraft?{[id]:record.document.markdownDraft}:{},visualDrafts:record.document.visualDraft?{[id]:record.document.visualDraft}:{}},ids);
    delete state.drafts[id];delete state.visualDrafts[id];
    if(restored.drafts[id])state.drafts[id]=restored.drafts[id];if(restored.visualDrafts[id])state.visualDrafts[id]=restored.visualDrafts[id];
  }
  const date=iso=>new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(iso));
  function save(){try{localStorage.setItem(KEY,JSON.stringify(state));storageAvailable=true;}catch{storageAvailable=false;}return storageAvailable;}
  function toast(message,artwork){if(artwork)$('toast').innerHTML=art(artwork,'toast-emoji')+'<span>'+E(message)+'</span>';else $('toast').textContent=message;$('toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),2800);}
  function download(name,text,type='text/plain;charset=utf-8'){const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);}
  function asset(id){return A.find(a=>a.id===id);}
  function art(id,className='',alt){const a=asset(id);return a?`<img class="${className}" src="${E(a.file)}" alt="${E(alt??a.title)}" decoding="async">`:'';}
  const categoryNames = {illustration: '插画', avatar: '头像', sticker: '贴纸'};
  const heading=(kicker,title,description)=>`<header class="page-header"><div class="eyebrow">${E(kicker)}</div><h1>${E(title)}</h1><p>${I(description)}</p></header>`;
  const list=items=>`<ul>${items.map(x=>`<li>${I(x)}</li>`).join('')}</ul>`;
  const noteEntries=()=>Object.entries(state.notes).filter(([,n])=>n.text.trim()).sort((a,b)=>b[1].updatedAt.localeCompare(a[1].updatedAt));
  const empty=(title,text,image='mascot-wave',action='')=>`<div class="empty-state">${art(image)||'<span class="empty-illustration">✿</span>'}<div><h3>${E(title)}</h3><p>${I(text)}</p>${action}</div></div>`;
  function setTheme(theme){state.theme=theme;document.body.dataset.theme=theme;save();renderCompanion();document.querySelectorAll('[data-action="theme"]').forEach(b=>b.innerHTML=icon(theme==='dark'?'sun':'moon'));}
  function renderCompanion() {
    const greeting = state.theme === 'dark' ? '紫樱 · 静夜阅读' : '紫樱 · 陪你学习';
    $('companion').innerHTML = art('mascot-avatar', '', '') + `<span>
      <strong>${greeting}</strong>
      ${state.done.length} / ${D.lessons.length} 章已完成 · ${noteEntries().length} 篇笔记
    </span>`;
    $('companion').title = `${greeting} · ${state.done.length} / ${D.lessons.length} 章已完成 · ${noteEntries().length} 篇笔记`;
  }
  function menu(open){const mobile=matchMedia('(max-width:800px)').matches;$('sidebar').inert=mobile&&!open;if(mobile)$('sidebar').setAttribute('aria-hidden',String(!open));else $('sidebar').removeAttribute('aria-hidden');document.body.classList.toggle('menu-open',open);$('mobile-shade').hidden=!open;$('menu-button').setAttribute('aria-expanded',String(open));if(open)$('sidebar').querySelector('[aria-current=page],summary')?.focus({preventScroll:true});}
  function localSourceLink(source) {
    if (window.ROS2Environment?.workspace !== true || !source.localPath) return '';
    return ` · <a class="local-source-link" href="../dist/index.html#/source/${encodeURIComponent(source.localPath)}">本地原文</a>`;
  }
  const studySections = new Set(['api-details', 'worked-example', 'practice', 'pitfalls', 'exercises', 'sources']);
  const outlineLabels = {comparison: '实现对照', study: '配套学习'};
  function headingText(heading) {
    const label = heading.cloneNode(true);
    label.querySelectorAll('.section-anchor').forEach(anchor => anchor.remove());
    return label.textContent.replace(/\s+/g, ' ').trim();
  }
  function chapterSections() {
    // 标题和顺序取自当前正文。主小节独立编号，表格、图解与步骤沿用所在小节的层级。
    const article = $('reading').querySelector('article');
    if (!article || !activeChapter) return [];
    const chapterNumber = D.lessons.indexOf(chapters.get(activeChapter)) + 1;
    const draft = article.querySelector(':scope > .draft-content');
    const nodes = draft ? draft.children : article.querySelectorAll(':scope > .reading-section[id], :scope > .source-note[id]');
    const childSelector = ':scope > h3, :scope > .static-figure > h3, :scope > .lab-card > .lab-summary h3';
    const sections = [];
    let part = 0;
    const addChild = (parent, heading) => {
      const index = parent.children.length + 1;
      if (!heading.id) {
        let id = `${parent.id}-sub-${index}`;
        // Markdown 草稿可以指定锚点，自动生成的图解锚点需要避开这些名字。
        while (article.querySelector('#' + CSS.escape(id))) id += '-copy';
        heading.id = id;
      }
      const number = parent.number ? `${parent.number}.${index}` : '';
      if (number) heading.dataset.sectionNumber = number;
      parent.children.push({id: heading.id, title: headingText(heading) || '未命名小节', number});
    };
    for (const node of nodes) {
      if (draft && !node.matches('h2[id]')) {
        const parent = sections.at(-1);
        const heading = node.matches('h3') ? node : node.querySelector(':scope > h3, :scope > .lab-summary h3');
        if (parent && heading) addChild(parent, heading);
        continue;
      }
      const heading = draft ? node : node.querySelector(':scope > h2, :scope > summary');
      const number = /^part-\d+$/.test(node.id) ? `${chapterNumber}.${++part}` : '';
      if (number) heading.dataset.sectionNumber = number;
      const group = node.id.startsWith('writing-') ? 'comparison' : studySections.has(node.id) ? 'study' : '';
      const section = {id: node.id, title: headingText(heading) || '未命名小节', number, group, children: []};
      sections.push(section);
      if (!draft) for (const child of node.querySelectorAll(childSelector)) addChild(section, child);
    }
    return sections;
  }
  function chapterOutline(sections, currentId) {
    const renderEntry = ({id, title, number, children}) => {
      const current = id === currentId ? ' aria-current="location"' : '';
      const index = number ? `<span class="outline-index">${number}</span>` : '<span class="outline-index" aria-hidden="true">·</span>';
      const branch = children?.length ? `<ul class="outline-children">${children.map(renderEntry).join('')}</ul>` : '';
      return `<li><a href="#/${encodeURIComponent(activeChapter)}/section/${encodeURIComponent(id)}" data-section-id="${E(id)}"${current}>${index}<span class="outline-label">${E(title)}</span></a>${branch}</li>`;
    };
    // 只合并相邻的同类条目，目录保留正文阅读顺序和原有锚点。
    const groups = [];
    for (const section of sections) {
      const previous = groups.at(-1);
      if (section.group && previous?.kind === section.group) previous.sections.push(section);
      else groups.push({kind: section.group, sections: [section]});
    }
    return groups.map(({kind, sections: entries}) => {
      const items = entries.map(renderEntry).join('');
      if (!kind) return items;
      const label = outlineLabels[kind];
      return `<li class="outline-group" data-outline-group="${kind}"><span class="outline-caption" aria-hidden="true">${label}</span><ul aria-label="${label}">${items}</ul></li>`;
    }).join('');
  }
  function currentChapterTitle(chapter) {
    return $('reading').querySelector('article h1')?.textContent.trim() || chapter.title;
  }
  function syncChapterTitle(title) {
    $('breadcrumb').lastElementChild.title = title;
    document.title = title + ' · 鸣神 ROS 2 学习手册';
  }
  function markTreeSection(id) {
    const navigation = $('chapter-tree');
    for (const link of navigation.querySelectorAll('.tree-section-list a')) {
      if (link.dataset.sectionId === id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
    const selected = navigation.querySelector('.tree-subtree[open] [aria-current=location]');
    const chapterLink = navigation.querySelector('.tree-link[aria-current=page]');
    const current = selected || chapterLink;
    if (!current?.getClientRects().length) return;
    const firstSection = navigation.querySelector('.tree-subtree[open] a');
    const viewport = navigation.getBoundingClientRect();
    const bottom = (selected || firstSection || current).getBoundingClientRect().bottom;
    const chapterTop = chapterLink.getBoundingClientRect().top;
    // 目录区域能容纳时，保留当前章标题和目标条目之间的上下文。
    const top = bottom - chapterTop <= viewport.height ? chapterTop : current.getBoundingClientRect().top;
    if (top < viewport.top) navigation.scrollTop += top - viewport.top;
    else if (bottom > viewport.bottom) navigation.scrollTop += Math.min(bottom - viewport.bottom, top - viewport.top);
  }
  function tree(chapter,collapse=false){
    const navigation = $('chapter-tree');
    const opened = new Set(collapse ? [] : [...navigation.querySelectorAll('.tree-stage[open]')].map(node => node.dataset.stage));
    const previous = navigation.querySelector('.tree-subtree');
    const sections = chapter ? chapterSections() : [];
    const title = chapter ? currentChapterTitle(chapter) : '';
    if (chapter) syncChapterTitle(title);
    const entryCount = sections.reduce((count, section) => count + 1 + section.children.length, 0);
    const expanded = previous?.dataset.chapter !== chapter?.id || previous?.open;
    const items = chapterOutline(sections);
    navigation.innerHTML = D.stages.map((stage, index) => {
      const lessons = D.lessons.filter(lesson => lesson.stage === stage.id);
      const open = chapter?.stage === stage.id || opened.has(stage.id) || (!chapter && index === 0);
      const links = lessons.map(lesson => {
        const current = lesson.id === chapter?.id;
        const number = String(D.lessons.indexOf(lesson) + 1).padStart(2, '0');
        const done = state.done.includes(lesson.id) ? '<span class="tree-check">✓</span>' : '';
        const link = `<a class="tree-link" href="#/${lesson.id}" ${current ? 'aria-current="page"' : ''}><span class="num">${number}</span><span class="tree-title">${E(current ? title : lesson.title)}</span>${done}</a>`;
        if (!current || !sections.length) return link;
        return `<div class="tree-chapter">${link}<details class="tree-subtree" data-chapter="${lesson.id}" ${expanded ? 'open' : ''}><summary>本章小节<small>${entryCount} 项</small></summary><ul class="section-outline tree-section-list">${items}</ul></details></div>`;
      });
      return `<details class="tree-stage" data-stage="${stage.id}" ${open ? 'open' : ''}><summary>${E(stage.title)}<small>${lessons.length}</small></summary>${links.join('')}</details>`;
    }).join('');
    document.querySelectorAll('.site-nav a').forEach(a=>{const selected=a.hash===(location.hash.split('?')[0]||'#/home')||(a.hash==='#/courses'&&chapter);if(selected)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
    const topLink=document.querySelector('.site-nav [aria-current=page]');if(topLink){const nav=topLink.parentElement;const box=topLink.getBoundingClientRect(),frame=nav.getBoundingClientRect();if(box.left<frame.left)nav.scrollLeft-=frame.left-box.left;if(box.right>frame.right)nav.scrollLeft+=box.right-frame.right;}
    const {parts} = route();
    markTreeSection(parts[1] === 'section' ? parts[2] : null);
    renderCompanion();
  }
  function highlighter(code){const pattern=/(\/\/[^\n]*|#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:from|import|class|def|return|if|else|while|for|void|auto|const|public|private|include|int|True|False|None|new|using|namespace|try|finally|except)\b|\b\d+(?:\.\d+)?\b)/g;let result='',last=0;for(const match of String(code).matchAll(pattern)){result+=E(code.slice(last,match.index));const token=match[0],type=/^(\/\/|#)/.test(token)?'comment':/^["']/.test(token)?'string':/^\d/.test(token)?'number':'keyword';result+=`<span class="token-${type}">${E(token)}</span>`;last=match.index+token.length;}return result+E(code.slice(last));}
  function codeBlock(block){const index=codeStore.push(block.code||'')-1;return `<div class="code-example" data-language="${E(block.language||'')}"><div class="code-caption"><span><span class="code-kind">${E(({file:'完整文件',commands:'终端命令',snippet:'局部片段',concept:'概念示意'})[block.type]||block.type||block.language||'示例')}</span>${E(block.label||block.language||'代码')}</span><button class="copy-button" data-copy="${index}">${icon('copy')}复制</button></div><pre><code>${highlighter(block.code||'')}</code></pre>${block.explanation?`<div class="code-explanation">${I(block.explanation)}</div>`:''}</div>`;}
  function table(t){return `<div class="table-wrap"><table><thead><tr>${t.columns.map(x=>`<th>${E(x)}</th>`).join('')}</tr></thead><tbody>${t.rows.map(row=>`<tr>${row.map(x=>`<td>${I(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${t.caption?`<p class="table-caption">${I(t.caption)}</p>`:''}${t.notes?.length?`<div class="small-note">${list(t.notes)}</div>`:''}`;}
  function equation(eq){return `<figure class="equation"><figcaption>${E(eq.label||'公式')}</figcaption><div class="math-scroll">${eq.mathml||E(eq.tex)}</div><p>${I(eq.explanation||'')}</p>${eq.symbols?.length?table({columns:['符号','含义','单位 / 维度'],rows:eq.symbols.map(s=>[s.symbol,s.meaning,s.unit||'—'])}):''}<details><summary>查看公式源码</summary><pre>${E(eq.tex)}</pre></details></figure>`;}
  function comparison(item){const n=comparisonSequence++;return `<section class="reading-section" id="writing-${E(item.id)}"><h2>${E(item.title)}</h2><p>${I(item.question)}</p><div class="implementation" style="--variants:${item.variants.length}" data-comparison="${n}"><div class="implementation-toolbar"><div class="code-tabs" role="tablist" aria-label="实现语言">${item.variants.map((v,i)=>`<button role="tab" id="cmp-${n}-tab-${i}" aria-controls="cmp-${n}-pane-${i}" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-code-tab="${i}">${E(v.label)}</button>`).join('')}</div><button class="compare-toggle" aria-pressed="false" data-compare>并排对照</button></div><div class="implementation-panels">${item.variants.map((v,i)=>`<div class="implementation-pane" role="tabpanel" id="cmp-${n}-pane-${i}" aria-labelledby="cmp-${n}-tab-${i}" ${i?'hidden':''}><div class="pane-name">${E(v.label)}</div>${codeBlock({...v,type:'示例实现',explanation:v.scope})}</div>`).join('')}</div></div><div class="implementation-notes">${list(item.notes||[])}</div></section>`;}
  function section(title,id,body){return `<section class="reading-section" id="${id}"><h2>${E(title)}<a class="section-anchor" href="#/${activeChapter}/section/${id}" aria-label="链接到${E(title)}">#</a></h2>${body}</section>`;}
  function figureMarkup(f,interactive=true,withId=true){
    if(interactive&&f.id==='tf2-static')return V.card('tf2-transform','transform','同一个点，两种坐标表达');
    if(interactive&&f.id==='robot-static')return V.card('robot-model','robot','从关节角到末端位置');
    return `<figure class="static-figure" ${withId?`id="fig-${f.id}"`:''}><h3>${E(f.title)}</h3><a href="../dist/${E(f.file)}" target="_blank" rel="noopener"><img src="../dist/${E(f.file)}" alt="${E(f.alt||f.title)}" loading="lazy"></a><figcaption>${I(f.caption||'')}</figcaption></figure>`;
  }
  function figuresFor(c,index){return (D.figures||[]).filter(f=>f.placements?.some(p=>p.chapter===c.id&&p.afterSection===index)).map(f=>figureMarkup(f)).join('');}
  function chapter(c){
    activeChapter=c.id;state.last=c.id;save();
    const body=state.drafts[c.id]?draftPage(c):originalChapter(c);
    return viewMode==='edit'?editChapter(c,body):body;
  }
  function originalChapter(c){
    const index=D.lessons.indexOf(c),stage=D.stages.find(s=>s.id===c.stage),apis=D.apiReferences.filter(a=>a.lessons.includes(c.id));
    let body=`<article><header class="chapter-header"><div class="eyebrow">${E(stage.title)} <span> / CHAPTER ${String(index+1).padStart(2,'0')}</span></div><h1>${E(c.title)}</h1><p class="chapter-intro">${I(c.summary)}</p><div class="chapter-meta"><span>${E(c.version)}</span><i class="dot"></i><span>原理 · API · 实验 · 答案</span><i class="dot"></i><span>本地离线教材</span></div><div class="chapter-actions"><button data-study="star" aria-pressed="${state.stars.includes(c.id)}">${icon('star')}<span>${state.stars.includes(c.id)?'已收藏':'收藏本章'}</span></button><button data-study="done" aria-pressed="${state.done.includes(c.id)}">${icon('check')}<span>${state.done.includes(c.id)?'已完成':'标记完成'}</span></button><button data-action="note">${icon('pen')}写笔记</button><button data-action="export-chapter">${icon('download')}下载本章</button></div></header><details class="chapter-summary"><summary>读完这一章，你将理解</summary>${list(c.goals||[])}</details>`;
    if(c.prerequisites?.length)body+=`<p class="small-note"><strong>开始之前</strong>　${I(Array.isArray(c.prerequisites)?c.prerequisites.join('；'):c.prerequisites)}</p>`;
    body+=section('建立整体认识','overview',(c.concepts||[]).map(x=>`<p>${I(x)}</p>`).join(''));
    for(const [i,s] of c.sections.entries()){
      body+=section(s.title.replace(/^\d+[.．]\s*/,''),'part-'+i,(s.paragraphs||[]).map(p=>`<p>${I(p)}</p>`).join('')+(s.bullets?.length?list(s.bullets):'')+(s.equations||[]).map(equation).join('')+(s.tables||[]).map(t=>`<h3>${E(t.title)}</h3>`+table(t)).join('')+(s.codeBlocks||[]).map(codeBlock).join('')+figuresFor(c,i));
      if(i===0)body+=D.comparisons.filter(x=>x.relatedLessons?.includes(c.id)).map(comparison).join('');
    }
    if(apis.length)body+=section('API 对照与调用边界','api-details',apis.map(a=>`<h3>${E(a.title)}</h3>`+table(a)).join(''));
    const x=c.workedExample;if(x)body+=section(x.title,'worked-example',`<p>${I(x.scenario)}</p><ol>${x.steps.map(s=>`<li>${I(s)}</li>`).join('')}</ol><div class="inline-notice"><strong>结果与验收</strong>　${I(x.result)}</div>`);
    body+=section('动手验证','practice',c.steps.map((s,i)=>typeof s==='string'?`<p>${I(s)}</p>`:`<h3>${E(s.title||`步骤 ${i+1}`)}</h3><p>${I(s.body||'')}</p>${s.code?codeBlock({...s,label:s.label||s.title,type:s.type||'commands'}):''}`).join('')+(c.commands||[]).map(codeBlock).join('')+`<div class="inline-notice"><strong>检查结果</strong>　${c.expected.map(I).join('；')}</div>`);
    body+=section('常见问题与边界','pitfalls',list(c.pitfalls||[]));
    const exercises=c.exercises?.length?c.exercises:[{question:c.exercise,answer:c.exerciseAnswer}];
    body+=section('练习与答案','exercises',exercises.map((q,i)=>`<details class="exercise-item"><summary><span data-edit-decoration>${String(i+1).padStart(2,'0')}</span><span class="exercise-question">${I(q.question)}</span></summary><p>${I(q.answer||'')}</p></details>`).join(''));
    body+=`<button class="chapter-note-link" data-action="note"><span>${icon('pen')}　把这一章整理成自己的理解</span><span>${state.notes[c.id]?.text.trim()?'继续写笔记':'写下第一条笔记'} →</span></button><details class="source-note" id="sources"><summary>参考出处、版本与验证范围</summary><p>${I(c.validation||D.meta.exampleValidation)}</p><ul>${c.sourceIds.map(id=>sources.get(id)).filter(Boolean).map(r=>`<li>${E(r.title)} · ${E(r.version)}<br>${I(r.verification||'')}　<a href="${E(L.safeUrl(r.url))}" target="_blank" rel="noopener noreferrer">原始出处 ↗</a>${localSourceLink(r)}</li>`).join('')}</ul><a href="../dist/index.html#/coverage">查看正式教材的参考对应表 ↗</a></details><nav class="chapter-pager" aria-label="相邻章节">${[D.lessons[index-1],D.lessons[index+1]].map((other,i)=>other?`<a href="#/${other.id}"><small>${i?'下一章 →':'← 上一章'}</small>${E(other.title)}</a>`:'<span></span>').join('')}</nav></article>`;
    return body;
  }
  function studyActions(c){
    return `<div class="chapter-actions"><button data-study="star" aria-pressed="${state.stars.includes(c.id)}">${icon('star')}<span>${state.stars.includes(c.id)?'已收藏':'收藏本章'}</span></button><button data-study="done" aria-pressed="${state.done.includes(c.id)}">${icon('check')}<span>${state.done.includes(c.id)?'已完成':'标记完成'}</span></button><button data-action="note">${icon('pen')}写笔记</button><button data-action="export-chapter">${icon('download')}下载本章</button></div>`;
  }
  /* 公式仅复用教材中已有的 MathML；新增公式显示 TeX 源码。
   * 图解只接受本地教材清单路径，编辑预览用静态回退图，阅读模式再挂载交互实验。
   */
  function draftDocument(markdown,interactive=false){
    const usedFigures=new Set();
    return M.render(markdown,{
      code:codeBlock,
      math:tex=>{const eq=D.lessons.flatMap(c=>c.sections.flatMap(s=>s.equations||[])).find(e=>e.tex.trim()===tex.trim());return eq?.mathml?`<div class="math-scroll draft-math" data-tex="${E(tex)}">${eq.mathml}</div>`:'';},
      figure:path=>{const f=D.figures.find(f=>'../dist/'+f.file===path);if(!f)return '';const first=!usedFigures.has(f.id);usedFigures.add(f.id);return figureMarkup(f,interactive&&first,first);}
    });
  }
  function draftPage(c){
    const index=D.lessons.indexOf(c);
    return `<article class="chapter-draft"><div class="draft-notice"><span>${icon('pen')} ${storageAvailable?'正在阅读本地草稿 · '+date(state.drafts[c.id].updatedAt):'当前草稿尚未持久保存 · 请先导出'}</span><button data-action="edit-chapter">继续编辑 →</button></div>${studyActions(c)}<div class="draft-content">${draftDocument(state.drafts[c.id].markdown,true)}</div><nav class="chapter-pager" aria-label="相邻章节">${[D.lessons[index-1],D.lessons[index+1]].map((other,i)=>other?`<a href="#/${other.id}"><small>${i?'下一章 →':'← 上一章'}</small>${E(other.title)}</a>`:'<span></span>').join('')}</nav></article>`;
  }
  function fileMatches(id){const saved=diskEditions.chapters[id]?.document;return !!saved&&F.encoded(saved.markdownDraft)===F.encoded(state.drafts[id]||null)&&F.encoded(saved.visualDraft)===F.encoded(state.visualDrafts[id]||null);}
  function editChapter(c,body){
    draftChapter=c.id;
    const hasDraft=!!state.drafts[c.id]||!!state.visualDrafts[c.id];
    return `<section class="visual-edit-shell"><div class="visual-editor-bar" aria-label="正文编辑工具"><div class="visual-editor-status"><strong>${icon('pen')} 直接编辑正文</strong><span id="draft-status" role="status">${storageAvailable?'点击文字即可修改 · 浏览器暂存':'存储不可用，请导出草稿'}</span><span id="draft-count"></span></div><div class="visual-editor-tools"><button data-visual-format="strong" title="选中文字后加粗"><strong>B</strong><span class="sr-only">加粗</span></button><button data-visual-format="code" title="选中文字后标为行内代码">&lt;/&gt;<span class="sr-only">行内代码</span></button><button data-action="visual-undo" title="撤销 · Ctrl / Cmd + Z">撤销</button><button data-action="visual-redo" title="重做 · Ctrl / Cmd + Shift + Z">重做</button><span class="tool-divider"></span><button class="save-textbook-button" data-action="save-textbook">保存到教材</button><button data-action="file-help" title="更换教材目录或使用本机编辑服务">保存位置</button><button data-action="open-source">Markdown 源码</button><button data-action="export-chapter">导出</button><button data-action="restore-chapter" ${hasDraft?'':'disabled'}>恢复原文</button><button data-action="undo-restore" ${draftUndo?.id===c.id?'':'hidden'}>撤销恢复</button></div></div><p id="file-save-status" class="file-save-status" role="status">${fileMatches(c.id)?'教材文件已保存 · '+date(diskEditions.chapters[c.id].savedAt):'尚未写入教材文件 · Ctrl / Cmd + S 保存到教材'}</p><p class="visual-editor-help">点击段落、标题、列表、表格或代码直接修改。选中文字可加粗或标为代码；公式与图解保留原显示。</p><div id="visual-document">${body}</div></section>`;
  }
  function mountDocument(){
    const container=$('reading').querySelector('article');if(!activeChapter||!container)return;
    const source=state.drafts[activeChapter]?.markdown??chapterMarkdown(chapters.get(activeChapter));
    visualSession=R.mount({container,base:R.fingerprint(source),draft:state.visualDrafts[activeChapter],editable:viewMode==='edit',renderCode:highlighter,onChange:()=>{
      editEpoch++;$('draft-status').textContent='正在暂存…';if($('file-save-status'))$('file-save-status').textContent='有修改尚未写入教材文件';clearTimeout(draftTimer);draftTimer=setTimeout(flushDraft,450);
    }});
    if(viewMode==='edit')$('draft-count').textContent=visualSession.count?'已修改 '+visualSession.count+' 处':'';
    if(visualSession.stale)container.insertAdjacentHTML('beforebegin','<p class="draft-notice">这份排版草稿对应另一版正文，仍保留在学习记录中，可导出备份。当前显示现有正文。</p>');
    else if(visualSession.count&&viewMode==='read'&&!$('reading').querySelector('.draft-notice'))container.insertAdjacentHTML('beforebegin',`<div class="draft-notice"><span>${fileMatches(activeChapter)?'正在阅读已保存的本地教材':storageAvailable?'正在阅读本地排版草稿':'当前草稿尚未持久保存 · 请先导出'}</span><button data-action="edit-chapter">继续编辑 →</button></div>`);
  }
  function flushDraft(){
    clearTimeout(draftTimer);
    if(!visualSession?.editable||!draftChapter)return;
    const snapshot=visualSession.snapshot(),size=Object.values(snapshot.fields).reduce((total,text)=>total+text.length,0);
    if(size>500000){$('draft-status').textContent='修改超过50万字符，请先导出；本次修改尚未保存';return;}
    if(visualSession.dirty){
      const old=state.visualDrafts[draftChapter];
      if(Object.keys(snapshot.fields).length){
        if(!old||old.base!==snapshot.base||JSON.stringify(old.fields)!==JSON.stringify(snapshot.fields))state.visualDrafts[draftChapter]={...snapshot,updatedAt:new Date().toISOString()};
      }else delete state.visualDrafts[draftChapter];
      const chapterTitle = currentChapterTitle(chapters.get(draftChapter));
      $('chapter-tree').querySelector('[aria-current=page] .tree-title').textContent = chapterTitle;
      syncChapterTitle(chapterTitle);
      const entries = chapterSections().flatMap(section => [section, ...section.children]);
      const titles = new Map(entries.map(({id, title}) => [id, title]));
      for (const link of $('chapter-tree').querySelectorAll('.tree-section-list a')) {
        const label = link.querySelector('.outline-label');
        const title = titles.get(link.dataset.sectionId);
        if (title && title !== label.textContent) label.textContent = title;
      }
    }
    const ok=save();
    $('draft-status').textContent=ok?'已暂存到浏览器 · '+date(new Date().toISOString()):'浏览器暂存失败，请保存到教材或导出';
    $('draft-count').textContent=visualSession.count?'已修改 '+visualSession.count+' 处':'';
    document.querySelector('[data-action="restore-chapter"]').disabled=!state.visualDrafts[draftChapter]&&!state.drafts[draftChapter];
  }
  function currentMarkdown(){
    const container=$('reading').querySelector('article');
    if(visualSession?.count&&container)return R.toMarkdown(container,{figure:id=>{const f=D.figures.find(f=>f.id===({'tf2-transform':'tf2-static','robot-model':'robot-static'})[id]);return f?'!['+f.title+'](../dist/'+f.file+')':'';}});
    return state.drafts[activeChapter]?.markdown??chapterMarkdown(chapters.get(activeChapter));
  }
  function rememberPosition(){
    if(!activeChapter)return;
    const nodes=[...$('reading').querySelectorAll('.reading-section[id], h3[id], .draft-heading[id], .source-note[id], details[data-lab]')];
    const anchor=nodes.filter(node=>node.getBoundingClientRect().top<160).at(-1)||nodes[0];
    pendingLabs=[...$('reading').querySelectorAll('details[data-lab][open]')].map(node=>node.dataset.lab);
    pendingPosition={chapter:activeChapter,id:anchor?.id,top:anchor?.getBoundingClientRect().top,scroll:scrollY};
  }
  function stopDocument(){visualSession?.destroy();visualSession=null;}
  function setViewMode(mode){
    rememberPosition();flushDraft();viewMode=mode==='edit'?'edit':'read';
    if(viewMode==='edit'&&!activeChapter){location.hash='#/'+(state.last||'tf2');return;}
    render();
  }
  function openSource(){
    flushDraft();sourceBaseline=currentMarkdown();$('chapter-source').value=sourceBaseline;
    $('source-status').textContent='关闭后返回正文；点击应用保存源码修改。';$('source-dialog').showModal();$('chapter-source').focus();
  }
  /* 文件版保存不依赖 localStorage。HTML只保留教材块，图解使用本地静态回退图；
   * 网页重开后用磁盘中的原位修改恢复交互排版，章节HTML/Markdown也可独立阅读。
   */
  function exportDocument(container){
    const clone=container.cloneNode(true);
    for(const lab of clone.querySelectorAll('.lab-card')){
      const id=({'tf2-transform':'tf2-static','robot-model':'robot-static'})[lab.dataset.lab];
      const figure=D.figures.find(f=>f.id===id),holder=document.createElement('div');
      holder.innerHTML=figure?figureMarkup(figure,false):'';lab.replaceWith(...holder.childNodes);
    }
    clone.querySelectorAll('.chapter-actions,.chapter-pager,.chapter-note-link,.draft-notice,.implementation-toolbar,.section-anchor,button,svg').forEach(node=>node.remove());
    for(const node of clone.querySelectorAll('[data-edit-key]')){
      if(node.tagName==='CODE')node.textContent=node.textContent;
      else node.innerHTML=R.safeInline(node.innerHTML);
    }
    const allowed=new Set('class id href src alt title width height open colspan rowspan display xmlns mathvariant mathsize mathcolor stretchy fence separator form accent accentunder columnalign rowalign columnspacing rowspacing encoding aria-label'.split(' '));
    for(const node of clone.querySelectorAll('*'))for(const attribute of [...node.attributes])if(!allowed.has(attribute.name))node.removeAttribute(attribute.name);
    return clone.innerHTML;
  }
  function textbookPayload(){
    flushDraft();const c=chapters.get(activeChapter),current=$('reading').querySelector('article');
    const previousStore=codeStore,previousSequence=comparisonSequence;
    let original;
    try{codeStore=[];comparisonSequence=0;const holder=document.createElement('div');holder.innerHTML=originalChapter(c);original={title:c.title,html:exportDocument(holder.querySelector('article')),markdown:chapterMarkdown(c),markdownDraft:null,visualDraft:null};}
    finally{codeStore=previousStore;comparisonSequence=previousSequence;}
    return {chapterId:c.id,baseChapter:c,expectedRevision:diskEditions.chapters[c.id]?.revision??null,
      original,document:{title:current.querySelector('h1')?.textContent||c.title,html:exportDocument(current),markdown:currentMarkdown(),markdownDraft:state.drafts[c.id]||null,visualDraft:state.visualDrafts[c.id]||null}};
  }
  async function directoryCache(value,write=false){
    try{
      const db=await new Promise((resolve,reject)=>{const request=indexedDB.open('ros2-textbook-directory-v1',1);request.onupgradeneeded=()=>request.result.createObjectStore('handles');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});
      try{return await new Promise((resolve,reject)=>{const transaction=db.transaction('handles',write?'readwrite':'readonly'),store=transaction.objectStore('handles'),request=write?store.put(value,'root'):store.get('root');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});}finally{db.close();}
    }catch{return null;}
  }
  directoryCache().then(handle=>{if(!directoryHandle)directoryHandle=handle;});
  async function chooseDirectory(){
    if(typeof window.showDirectoryPicker!=='function'){if(!$('file-help-dialog').open)$('file-help-dialog').showModal();return false;}
    try{directoryHandle=await window.showDirectoryPicker({id:'ros2-textbook',mode:'readwrite'});await directoryCache(directoryHandle,true);if($('file-help-dialog').open)$('file-help-dialog').close();if($('file-save-status'))$('file-save-status').textContent='已选择 '+directoryHandle.name+' · 点击“保存到教材”写入';return true;}
    catch(error){if(error.name==='AbortError')toast('已取消选择，修改仍暂存在浏览器。');else{toast('未取得目录写入权限，请使用本机编辑服务。');if(!$('file-help-dialog').open)$('file-help-dialog').showModal();}return false;}
  }
  async function saveTextbook(){
    if(!activeChapter||fileSaving)return;
    const payload=textbookPayload(),id=activeChapter,epoch=editEpoch;fileSaving=true;
    document.querySelectorAll('[data-action=save-textbook]').forEach(button=>button.disabled=true);
    const status=message=>{if(activeChapter===id&&$('file-save-status'))$('file-save-status').textContent=message;};
    try{
      let result;
      if(window.NarukamiEditorService?.enabled){
        status('正在备份原文并写入教材…');
        const response=await fetch('/api/textbook/save',{method:'POST',headers:{'Content-Type':'application/json','X-Textbook-Token':window.NarukamiEditorService.token},body:JSON.stringify(payload)});
        result=await response.json();if(!response.ok||!result.saved)throw new Error(result.error||'教材文件未保存');
      }else{
        if(!directoryHandle&&!await chooseDirectory())return;
        if(directoryHandle.queryPermission&&await directoryHandle.queryPermission({mode:'readwrite'})!=='granted'&&await directoryHandle.requestPermission({mode:'readwrite'})!=='granted')throw new Error('目录写入权限未授予，教材文件未修改。');
        status('正在备份原文并写入教材…');
        const task=()=>F.commit(F.directoryIO(directoryHandle),payload);
        result=navigator.locks?await navigator.locks.request('ros2-textbook-local-save',task):await task();
      }
      diskEditions.chapters[id]=result.record;
      status(epoch===editEpoch?'已写入教材文件 · '+date(result.record.savedAt)+' · 原文与历史在 backups/local-edits/':'上一版已写入教材，还有修改待保存。');
      toast(result.unchanged?'教材文件已是最新版本。':'教材文件已保存，原文备份已保留。');
    }catch(error){status('未写入教材：'+error.message);toast('教材未保存：'+error.message);}
    finally{fileSaving=false;document.querySelectorAll('[data-action=save-textbook]').forEach(button=>button.disabled=false);}
  }
  function teaser(id,kind,title,text,href){return `<a class="visual-teaser" href="${href}"><div class="teaser-image">${V.preview(kind)}</div><div class="teaser-body"><small>0${id} / INTERACTIVE</small><h3>${title}</h3><p>${text}</p><span class="text-link">打开交互笔记 →</span></div></a>`;}
  function home() {
    const last = chapters.get(state.last) || chapters.get('tf2') || D.lessons[0];
    return `<section class="home-hero">
      <div class="hero-copy">
        <div class="eyebrow"><span>✿</span> A NOTEBOOK FOR YOUR ROBOTICS JOURNEY</div>
        <h1>从原理到实践，<br>读懂 <em>ROS 2</em>。</h1>
        <p class="hero-description">把概念、公式与代码放在同一页。<br>用一张图理解变化，用一篇笔记留下收获。</p>
        <div class="button-row">
          <a class="button" href="#/${last.id}">继续学习 ${icon('arrow')}</a>
          <a class="button secondary" href="#/courses">浏览全书目录</a>
        </div>
      </div>
      <figure class="hero-figure">
        <div class="hero-visual">${art('mascot-hero', 'hero-mascot', '抱着书的紫樱')}</div>
        <figcaption class="hero-caption"><span><i></i>紫樱 · 樱机实验室</span><a href="#/gallery">素材与出处 ↗</a></figcaption>
      </figure>
    </section>
    <div class="home-stats">
      <div><strong>${D.lessons.length}</strong><span>教程章节</span></div>
      <div><strong>${D.meta.equationCount}</strong><span>原理公式</span></div>
      <div><strong>${D.meta.exerciseCount}</strong><span>练习与答案</span></div>
      <div><strong>16</strong><span>图解与实验</span></div>
    </div>
    <a class="continue-row" href="#/${last.id}">
      <span class="continue-icon">${icon('book')}</span>
      <div><small>${state.last ? '继续上次的阅读' : '从一篇交互笔记开始'}</small><strong>${E(last.title)}</strong></div>
      <span class="arrow">→</span>
    </a>
    <div class="section-title"><h2>循着目录，一步一步来</h2><a href="#/courses">展开全书目录 →</a></div>
    <div class="stage-grid">${D.stages.map((stage, index) => `<a class="stage-card" href="#/courses/${stage.id}">
      <span>0${index + 1}</span><div><h3>${E(stage.title)}</h3><p>${E(stage.description)}</p></div>
      <small>${D.lessons.filter(chapter => chapter.stage === stage.id).length} 章</small>
    </a>`).join('')}</div>
    <div class="section-title"><h2>把抽象的概念，变成看得见的变化</h2><a href="#/visuals">全部图解 →</a></div>
    <div class="visual-grid">
      ${teaser(1, 'transform', '同一个点，两种坐标表达', '调节旋转和平移，观察坐标与公式如何对应。', '#/tf2/figure/tf2-transform?open=1')}
      ${teaser(2, 'robot', '从关节角到末端位置', '转动视角与关节，理解连杆和局部坐标系。', '#/eco-model-rviz/figure/robot-model?open=1')}
    </div>
    <div class="section-title"><h2>留一点空间，写下自己的理解</h2><a href="#/notes">我的笔记 →</a></div>
    ${noteEntries().length ? noteCards(noteEntries().slice(0, 2)) : empty(
      '第一篇笔记，从一个小问题开始',
      '读到不确定的地方，打开“本章笔记”。理解、疑问与实验结果，都可以留在这里。',
      'mascot-wave', `<a class="text-link" href="#/${last.id}?note=1">去这一章写笔记 →</a>`
    )}`;
  }
  function courses(stageId='',query=''){const filtered=D.lessons.filter(c=>(!stageId||c.stage===stageId)&&(!query||(c.title+' '+c.summary).toLowerCase().includes(query.toLowerCase())));return heading('THE TABLE OF CONTENTS','全书目录','从基础环境到机器人应用。按阶段连续学习，也可以直接找到眼前需要的知识点。')+`<div class="filter-bar"><input id="course-query" type="search" aria-label="筛选章节" placeholder="查找章节，例如：坐标、参数、控制…" value="${E(query)}"><label>阶段<select id="course-stage"><option value="">全部阶段</option>${D.stages.map(s=>`<option value="${s.id}" ${s.id===stageId?'selected':''}>${E(s.title)}</option>`).join('')}</select></label></div><p class="count-line">${filtered.length} 章 · ${state.done.length} 章已完成 · ${state.stars.length} 章已收藏</p><div id="course-results">${courseRows(filtered)}</div>`;}
  function courseRows(items){return D.stages.filter(s=>items.some(c=>c.stage===s.id)).map(s=>`<section class="course-stage" id="stage-${s.id}"><h2>${E(s.title)}</h2><p>${E(s.description)}</p>${items.filter(c=>c.stage===s.id).map(c=>`<a class="course-row" href="#/${c.id}"><span>${String(D.lessons.indexOf(c)+1).padStart(2,'0')}</span><div><h3>${E(c.title)}</h3><p>${E(c.summary.slice(0,100))}</p></div><small>${state.done.includes(c.id)?'✓ 已完成':state.stars.includes(c.id)?'☆ 已收藏':'阅读 →'}</small></a>`).join('')}</section>`).join('')||empty('没有匹配的章节','换一个关键词，或选择“全部阶段”。','mascot-guide');}
  function noteCards(entries){return entries.map(([id,note])=>`<article class="note-card"><div class="note-meta"><span>${E(D.stages.find(s=>s.id===chapters.get(id).stage).title)}</span><time datetime="${note.updatedAt}">${date(note.updatedAt)}</time></div><h2><a href="#/${id}">${E(chapters.get(id).title)}</a></h2><p>${E(note.text.slice(0,200))}${note.text.length>200?'…':''}</p><a class="text-link" href="#/${id}?note=1">继续编辑 →</a><a class="text-link" href="#/${id}">返回正文</a></article>`).join('');}
  function notes(){return heading('YOUR OWN UNDERSTANDING','我的笔记','把知识整理成自己的语言。笔记和学习记录保存在当前浏览器，随时可以导出备份。')+`<div class="button-row"><button class="button secondary" data-action="export-backup">${icon('download')}导出笔记、草稿与进度</button><button class="button secondary" data-action="import-backup">导入备份</button><a class="button secondary" href="#/saved">查看收藏与进度</a></div><p class="small-note">审查版使用独立存储。导入兼容旧进度文件；合并时保留同章较新的笔记和正文草稿。</p><div class="filter-bar"><input id="notes-query" type="search" placeholder="搜索自己的理解、疑问和实验记录…" aria-label="搜索章节笔记"></div><p class="count-line" id="notes-count">${noteEntries().length} 篇章节笔记</p><div id="notes-results">${noteEntries().length?noteCards(noteEntries()):empty('还没有写下笔记','打开任意章节，点击“本章笔记”。文字会自动保存，也可以用 Markdown 整理。','mascot-wave','<a class="text-link" href="#/tf2?note=1">从坐标变换开始 →</a>')}</div>`;}
  function saved(){return heading('BOOKMARKS & PROGRESS','收藏与阅读进度',`${state.done.length} / ${D.lessons.length} 章已完成。完成标记由你自己决定，阅读次数不会自动代表掌握程度。`)+`<div class="button-row"><a class="button secondary" href="#/notes">打开我的笔记</a><button class="button secondary" data-action="export-backup">导出学习记录</button></div><div class="section-title"><h2>收藏的章节</h2><span>${state.stars.length} CHAPTERS</span></div>${state.stars.length?courseRows(D.lessons.filter(c=>state.stars.includes(c.id))):empty('把想反复阅读的章节收在这里','在章节标题下点击“收藏本章”，下一次就能更快找到。','mascot-badge')}<div class="section-title"><h2>已完成的章节</h2></div>${state.done.length?courseRows(D.lessons.filter(c=>state.done.includes(c.id))):'<p class="small-note">每读懂一章，再给自己一个完成标记。</p>'}`;}
  function visuals(){return heading('SEE HOW IT WORKS','图解与交互实验','图解紧邻它解释的知识点。先看关系，再调参数，让文字、公式和变化彼此对应。')+`<div class="visual-grid">${teaser(1,'transform','坐标变换实验','m / ° · 平移、旋转、公式和坐标结果','#/tf2/figure/tf2-transform?open=1')}${teaser(2,'robot','机器人几何模型','局部关节轴 · 连杆 · 末端位置','#/eco-model-rviz/figure/robot-model?open=1')}</div><div class="section-title"><h2>正文中的图解</h2><span>${D.figures.length} FIGURES</span></div><div class="visual-grid">${D.figures.map(f=>`<a class="visual-teaser" href="#/${f.placements[0].chapter}/figure/${f.id}"><div class="teaser-image"><img src="../dist/${E(f.file)}" alt="${E(f.alt||f.title)}" loading="lazy"></div><div class="teaser-body"><small>CONTEXTUAL DIAGRAM</small><h3>${E(f.title)}</h3><p>${E(f.caption?.slice(0,90)||'')}</p><span class="text-link">在正文中阅读 →</span></div></a>`).join('')}</div>`;}
  function gallery() {
    const categories = Object.entries(categoryNames).map(([id, name]) => `<option value="${id}">${name}</option>`);
    const placements = [...new Set(A.flatMap(asset => asset.placements))];
    return heading('SAKURABOT LAB', '紫樱素材画廊', '浏览樱机实验室吉祥物的读书插画、头像和贴纸。点开每张图可查看出处、尺寸与页面用途。') + `
      <div class="filter-bar">
        <label>类别<select id="asset-category"><option value="">全部类别</option>${categories.join('')}</select></label>
        <label>用途<select id="asset-placement"><option value="">全部用途</option>${placements.map(placement => `<option>${E(placement)}</option>`).join('')}</select></label>
      </div>
      <p class="count-line" id="asset-count"></p>
      <div class="gallery-grid" id="asset-grid"></div>
      <p class="small-note" style="margin-top:25px">每张图都保留仓库原文件与 SHA256。<a class="text-link" href="ASSET_SOURCES.md">素材来源说明 ↗</a></p>`;
  }
  function filterGallery() {
    const category = $('asset-category').value;
    const placement = $('asset-placement').value;
    const items = A.filter(asset => (!category || asset.category === category) && (!placement || asset.placements.includes(placement)));
    $('asset-count').textContent = `显示 ${items.length} / ${A.length} 张 · 点击查看出处与裁切效果`;
    $('asset-grid').innerHTML = items.map(asset => `<button class="asset-card" data-asset="${E(asset.id)}">
      <div class="asset-thumb"><img src="${E(asset.file)}" alt="${E(asset.title)}" loading="lazy"></div>
      <div class="asset-info">
        <small>${categoryNames[asset.category]}</small><strong>${E(asset.title)}</strong>
        <span>${asset.width} × ${asset.height} · ${E(asset.placements.join(' / '))}</span>
      </div>
    </button>`).join('') || '<p class="small-note">没有同时符合这些条件的素材。试试只选一个条件。</p>';
  }
  function openAsset(id) {
    const selected = asset(id);
    if (!selected) return;
    const file = E(selected.file);
    $('asset-title').textContent = selected.title;
    $('asset-detail').innerHTML = `<div class="asset-detail-grid">
      <div class="asset-original"><img src="${file}" alt="${E(selected.title)}"></div>
      <div class="asset-metadata"><span class="pill">紫樱 · 樱机实验室</span><dl>
        <dt>素材类型 / 原始尺寸</dt><dd>${categoryNames[selected.category]} · ${selected.width} × ${selected.height}</dd>
        <dt>页面用途</dt><dd>${E(selected.placements.join('、'))}</dd>
        <dt>头像与横幅裁切示意</dt><dd class="crop-previews"><img src="${file}" alt="圆形裁切示意"><img src="${file}" alt="横幅裁切示意"></dd>
        <dt>仓库来源</dt><dd><a href="${E(L.safeUrl(selected.sourceUrl))}" target="_blank" rel="noopener noreferrer">${E(selected.author)} · 查看历史文件 ↗</a></dd>
        <dt>素材许可</dt><dd>${E(selected.rights)}</dd>
        <dt>本地文件 SHA256</dt><dd><code>${E(selected.sha256)}</code></dd>
      </dl><a class="button secondary" href="${file}" download>下载历史素材 ${icon('download')}</a></div>
    </div>`;
    $('asset-dialog').showModal();
  }
  function resources(){return heading('REFERENCE & PRACTICE','资料与工程','正文学习、原创工程与上游原文各有入口。版本、来源和实际验证范围继续独立记录。')+`<div class="button-row"><a class="button secondary" href="#/api">API 对照</a><a class="button secondary" href="#/compare">不同写法对照</a><a class="button secondary" href="../dist/index.html#/examples">完整示例工程 ↗</a><a class="button secondary" href="../dist/index.html#/projects">综合实践 ↗</a></div><div class="section-title"><h2>离线下载与工程</h2></div>${[['../dist/book.html','连续阅读与打印','单文件教材，关闭 JavaScript 也能阅读。'],['../dist/downloads/ros2-learning-guide.md','完整 Markdown 教材','正文、公式、代码、实测表与参考来源。'],['../dist/downloads/atlas_examples.zip','原创示例工程','通信、数学应用及各轮实验；运行环境见工程 README。'],['../dist/downloads/foundation_examples.zip','基础 ROS 2 工程','10个基础包及独立许可证、验证说明。'],['../dist/downloads/validation-evidence.zip','实验与验证记录','实测输入和范围，不将未运行部分标为通过。']].map(([url,title,text])=>`<a class="course-row" href="${url}"><span>↗</span><div><h3>${title}</h3><p>${text}</p></div>${icon('download')}</a>`).join('')}<div class="section-title"><h2>参考来源</h2><span>${D.resources.length} RECORDS</span></div><div class="filter-bar"><input id="resource-query" type="search" aria-label="筛选参考资料" placeholder="搜索包、工具、版本或出处…"></div><div id="resource-results">${resourceRows(D.resources)}</div><div class="inline-notice"><strong>本地原文元数据</strong>　搜索包含 ${window.ROS2LocalDocuments.length} 份文档的标题与路径；原文读取仍由正式站的本机白名单服务提供。<br><a class="text-link" href="../dist/index.html#/library">打开正式站本地原文入口 ↗</a></div><details class="resource-row" id="document-metadata"><summary id="document-metadata-title">本地原文元数据</summary><div id="resource-document-results"></div></details>`;}
  function resourceRows(items){return items.map(r=>`<details class="resource-row"><summary>${E(r.title)}<span class="pill">${E(r.version)}</span></summary><p>${I(r.description||'')}</p><p class="small-note">${I(r.verification||'')}</p><a href="${E(L.safeUrl(r.url))}" target="_blank" rel="noopener noreferrer">原始出处 ↗</a></details>`).join('')||'<p class="small-note">没有匹配资料。</p>';}
  function review(){const screenshots=window.NarukamiReviewEvidence?.screenshots||[];return heading('DESIGN REVIEW / 01','一起审查这份学习笔记站','从真实阅读路径开始，看看目录是否好找、正文是否舒服，以及图解和笔记是否出现在需要的地方。')+`<div class="review-intro"><span class="review-symbol">✿</span><div><h2 style="font-size:18px;margin:0">樱粉浅色与夜紫深色</h2><p>两栏文档 · ${D.lessons.length}章现有教材 · ${A.length}张紫樱素材 · 阅读 / 编辑模式 · 两种交互实验</p><a class="text-link" href="ASSET_SOURCES.md">素材来源说明 ↗</a>　<a class="text-link" href="README.md">样稿使用说明 ↗</a></div></div><div class="section-title"><h2>按六个场景看一遍</h2><button class="text-link" data-action="theme">切换浅色 / 深色 ↔</button></div><div class="review-list">${[
      ['首页与目录','学习目录占满左列，其他入口集中在顶部单行；核对吉祥物比例、配色与章节层级。',[['#/home','学习首页'],['#/courses','全书目录']]],
      ['章节阅读与编辑','右上角切换阅读与编辑模式，直接在当前排版中修改文字、表格和代码，核对自动保存、阅读恢复与可选源码入口。',[['#/tf2','坐标变换章'],['#/eco-model-rviz','模型章'],['#/math-rigid','公式与推导']]],
      ['搜索与定位','关键词命中后，直接到达对应小节；空态也有清晰提示。',[['#/home?search=坐标','搜索命中'],['#/home?search=没有这个词xyz','搜索空态']]],
      ['章节笔记','边读边写，切换预览，刷新后恢复，并导出自己的记录。',[['#/tf2?note=1','打开笔记抽屉'],['#/notes','笔记列表']]],
      ['交互实验','从正文展开，调节参数；宽屏与复位都有明确的返回路径。',[['#/tf2/figure/tf2-transform?open=1','二维坐标实验'],['#/eco-model-rviz/figure/robot-model?open=1','机器人几何模型']]],
      ['紫樱素材','按类别或用途筛选，查看历史素材、裁切效果与仓库出处。',[['#/gallery','素材画廊']]]
    ].map(([title,text,links])=>`<section class="review-item"><div><h3>${title}</h3><p>${text}</p><div class="review-links">${links.map(([url,label])=>`<a href="${url}">${label} ↗</a>`).join('')}</div></div></section>`).join('')}</div><div class="section-title"><h2>多尺寸审查截图</h2><span>1440 / 390 / 320 PX</span></div>${screenshots.length?`<div class="screenshot-grid">${screenshots.map(s=>`<a class="screenshot-card" href="${E(s.file)}" target="_blank" rel="noopener"><img src="${E(s.file)}" alt="${E(s.title)}" loading="lazy"><span>${E(s.title)} ↗</span></a>`).join('')}</div>`:'<p class="small-note">截图由浏览器验收生成，完成后会在这里列出。</p>'}<div class="section-title"><h2>为后续 Web 可视化预留的位置</h2></div><div class="adapter-list">${[['SceneView','URDF、TF、轨迹与点云的空间显示'],['ImageView','相机图像与深度图'],['SeriesPlot','状态量、误差与时间曲线'],['GraphView','节点、话题及通信关系']].map(([title,text])=>`<div><h3>${title}</h3><p>${text}</p><span class="pill">接口预留 · 尚未接入</span></div>`).join('')}</div><p class="small-note" style="margin-top:20px">本页为独立设计审查样稿。当前交互使用本地教学数据；未启动 ROS、机器人、相机或实时连接。素材与样稿代码的许可分别记录。</p>`;}
  /* 搜索只索引可读字段，避免把报告哈希、内部JSON键名当正文；原文只索引元数据。 */
  const searchRecords=[];
  for(const c of D.lessons){
    searchRecords.push({title:c.title,text:c.summary,kind:'教材',chapter:c.title,href:'#/'+c.id});
    for(const [i,s]of c.sections.entries()){
      searchRecords.push({title:s.title,text:[...(s.paragraphs||[]),...(s.bullets||[])].join(' '),kind:'教材',chapter:c.title,href:`#/${c.id}/section/part-${i}`});
      for(const b of s.codeBlocks||[])searchRecords.push({title:b.label||s.title,text:b.code+' '+(b.explanation||''),kind:'代码 / API',chapter:c.title,href:`#/${c.id}/section/part-${i}`});
      for(const eq of s.equations||[])searchRecords.push({title:eq.label,text:eq.tex+' '+eq.explanation,kind:'教材',chapter:c.title,href:`#/${c.id}/section/part-${i}`});
      for(const t of s.tables||[])searchRecords.push({title:t.title,text:[...t.columns,...t.rows.flat(),t.caption||''].join(' '),kind:'教材',chapter:c.title,href:`#/${c.id}/section/part-${i}`});
    }
    searchRecords.push({title:c.title+' · 动手验证',text:[...c.steps.map(s=>typeof s==='string'?s:[s.title,s.body,s.code].filter(Boolean).join(' ')),...(c.commands||[]).map(b=>b.code),...(c.expected||[])].join(' '),kind:'教材',chapter:c.title,href:`#/${c.id}/section/practice`});
    searchRecords.push({title:c.title+' · 整体认识',text:(c.concepts||[]).join(' '),kind:'教材',chapter:c.title,href:`#/${c.id}/section/overview`});
    searchRecords.push({title:c.title+' · 常见问题',text:(c.pitfalls||[]).join(' '),kind:'教材',chapter:c.title,href:`#/${c.id}/section/pitfalls`});
    for(const q of c.exercises||[])searchRecords.push({title:q.question,text:q.answer,kind:'教材',chapter:c.title,href:`#/${c.id}/section/exercises`});
    if(c.workedExample)searchRecords.push({title:c.workedExample.title,text:[c.workedExample.scenario,...c.workedExample.steps,c.workedExample.result].join(' '),kind:'教材',chapter:c.title,href:`#/${c.id}/section/worked-example`});
  }
  D.apiReferences.forEach(a=>searchRecords.push({title:a.title,text:JSON.stringify([a.columns,a.rows,a.notes]),kind:'代码 / API',chapter:chapters.get(a.lessons[0])?.title,href:`#/${a.lessons[0]}/section/api-details`}));
  D.comparisons.forEach(c=>searchRecords.push({title:c.title,text:c.question+' '+c.variants.map(v=>v.code).join(' '),kind:'代码 / API',chapter:'不同写法对照',href:'#/compare/'+c.id}));
  D.figures.forEach(f=>searchRecords.push({title:f.title,text:f.caption||'',kind:'图解',chapter:chapters.get(f.placements[0].chapter)?.title,href:`#/${f.placements[0].chapter}/figure/${f.id}`}));
  searchRecords.push({title:'二维坐标变换交互实验 tf2',text:'平移 旋转 坐标 p_B R theta',kind:'图解',chapter:'tf2',href:'#/tf2/figure/tf2-transform?open=1'},{title:'三关节机器人几何模型',text:'关节角 末端 局部坐标 URDF',kind:'图解',chapter:'机器人模型',href:'#/eco-model-rviz/figure/robot-model?open=1'});
  D.resources.forEach(r=>searchRecords.push({title:r.title,text:[r.description,r.version,r.category].join(' '),kind:'资料',chapter:'参考来源',href:'#/resources?query='+encodeURIComponent(r.title)}));
  window.ROS2LocalDocuments.forEach(d=>searchRecords.push({title:d.title,text:d.path+' '+d.branch,kind:'资料',chapter:'原文元数据 · '+d.snapshot,href:'#/resources?query='+encodeURIComponent(d.title)+'&metadata=1',metadata:true}));
  function allSearchRecords(){return [...Object.entries(state.visualDrafts).map(([id,draft])=>({title:chapters.get(id).title+' · 排版草稿',text:Object.entries(draft.fields).map(([key,text])=>key.endsWith('-code')?text:R.plainText(text)).join(' '),kind:'教材',chapter:'本地排版草稿',href:'#/'+id})),...Object.entries(state.drafts).map(([id,draft])=>({title:chapters.get(id).title+' · 本地正文草稿',text:draft.markdown,kind:'教材',chapter:'本地草稿',href:'#/'+id})),...noteEntries().map(([id,note])=>({title:chapters.get(id).title+' · 我的笔记',text:note.text,kind:'笔记',chapter:'个人记录',href:'#/'+id+'?note=1'})),...searchRecords];}
  function search(){const q=$('search-input').value.trim();let items=q?L.search(allSearchRecords(),q,searchKind):searchRecords.filter(r=>r.kind==='图解').slice(-2).concat(D.lessons.slice(0,3).map(c=>({title:c.title,text:c.summary,chapter:'推荐起点',kind:'教材',href:'#/'+c.id})));if(!q&&searchKind!=='全部')items=items.filter(r=>r.kind===searchKind);searchActive=0;
    $('search-results').innerHTML=items.length?`<div class="search-summary">${q?`找到 ${items.length} 项，先显示前 ${Math.min(40,items.length)} 项`:'从一个知识点开始，或直接输入关键词'}</div>`+items.slice(0,40).map((r,i)=>`<a class="search-result" href="${E(r.href)}" ${i===0?'data-active="true"':''}><small><span class="kind">${E(r.kind)}</span>${E(r.chapter||'')}</small><strong>${L.highlight(r.title,q)}</strong><p>${L.highlight(r.snippet||r.text?.slice(0,150)||'',q)}</p></a>`).join(''):empty('还没有找到这个知识点','试试“坐标”“rclcpp”“QoS”或换成更短的关键词。','mascot-guide');
    $('search-filters').innerHTML=['全部','教材','代码 / API','图解','笔记','资料'].map(k=>`<button data-search-kind="${k}" aria-pressed="${k===searchKind}">${k}</button>`).join('');}
  function openSearch(query=''){flushDraft();menu(false);searchKind='全部';$('search-input').value=query;search();$('search-dialog').showModal();$('search-input').focus();}
  function flushNote(){clearTimeout(noteTimer);if(!noteChapter)return;const text=$('note-editor').value;if(text.trim())state.notes[noteChapter]={text,updatedAt:new Date().toISOString()};else delete state.notes[noteChapter];const ok=save();$('note-status').textContent=ok?'已保存 · '+new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date()):'未持久保存，请先导出备份';$('note-count').textContent=text.length+' 字';$('note-dot').hidden=!state.notes[activeChapter]?.text.trim();renderCompanion();}
  function noteMode(mode){document.querySelectorAll('[data-note-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.noteMode===mode)));$('note-editor').hidden=mode==='preview';$('note-preview').hidden=mode!=='preview';if(mode==='preview')$('note-preview').innerHTML=L.markdown($('note-editor').value)||'<p class="muted">写下第一句话，就能在这里看到预览。</p>';}
  function openNote(id=activeChapter){if(!chapters.has(id))return;menu(false);noteChapter=id;$('note-chapter').textContent=chapters.get(id).title;$('note-editor').value=state.notes[id]?.text||'';$('note-count').textContent=$('note-editor').value.length+' 字';$('note-status').textContent=storageAvailable?'自动保存到当前浏览器':'存储不可用，请导出备份';noteMode('edit');$('note-dialog').showModal();$('note-editor').focus();}
  function openToc() {
    const {parts} = route();
    const currentId = parts[1] === 'section' ? parts[2] : null;
    $('toc-list').innerHTML = `<ul class="section-outline">${chapterOutline(chapterSections(), currentId)}</ul>`;
    $('toc-dialog').showModal();
    const current = $('toc-list').querySelector('[aria-current=location]');
    current?.scrollIntoView({block: 'nearest', behavior: 'instant'});
    current?.focus({preventScroll: true});
  }
  /* 整个挂载容器随宽屏移动，保留事件委托与闭包引用；不能只移动它的子节点。 */
  function closeWide(){if(wideReturn){if(wideReturn.placeholder.isConnected){wideReturn.placeholder.replaceWith(wideReturn.host);V.resize(wideReturn.id);}wideReturn=null;}}
  function openWide(button){const card=button.closest('.lab-card');if(!card)return;const host=card.querySelector('.lab-host'),placeholder=document.createComment('实验原位置');host.before(placeholder);wideReturn={host,id:card.dataset.lab,placeholder};$('wide-title').textContent=card.querySelector('h3').textContent;$('wide-body').append(host);$('wide-dialog').showModal();V.resize(card.dataset.lab);}
  function route(){try{const [hash,query='']=location.hash.replace(/^#\/?/,'').split('?'),parts=hash.split('/').map(decodeURIComponent),head=parts[0]||'home';if(head==='lesson')parts.shift();return {view:chapters.has(parts[0])?'chapter':head,id:chapters.has(parts[0])?parts[0]:parts.slice(1).join('/'),parts,query:new URLSearchParams(query)};}catch{return {view:'home',id:'',parts:[],query:new URLSearchParams()};}}
  function goToAnchor(r) {
    const isSection = r.parts[1] === 'section';
    let id = isSection ? r.parts[2] : r.parts[1] === 'figure' ? 'fig-' + r.parts[2] : null;
    if (id === 'fig-tf2-static') id = 'fig-tf2-transform';
    if (id === 'fig-robot-static') id = 'fig-robot-model';
    const reading = $('reading');
    const target = id && reading.querySelector('#' + CSS.escape(id));
    reading.querySelector('.matched-section')?.classList.remove('matched-section');
    markTreeSection(isSection && target ? id : null);
    if (!target) {
      window.scrollTo({top: 0, behavior: 'instant'});
      return;
    }
    if (target.matches('details') && (isSection || r.query.get('open') === '1')) target.open = true;
    // API 等分组的首个子标题紧跟主标题。定位时保留这一行上下文，当前条目仍是子标题。
    const start = target.matches('h3') && target.previousElementSibling?.matches('h2') ? target.previousElementSibling : target;
    start.scrollIntoView({block: 'start', behavior: 'instant'});
    const editorBar = reading.querySelector('.visual-editor-bar');
    if (editorBar && isSection) {
      const overlap = editorBar.getBoundingClientRect().bottom + 12 - start.getBoundingClientRect().top;
      if (overlap > 0) window.scrollBy({top: -overlap, behavior: 'instant'});
    }
    target.classList.add('matched-section');
  }
  function navigate() {
    const r = route();
    // 同章定位只移动阅读位置，保留正文节点、编辑状态和已打开的实验。
    if (r.view === 'chapter' && r.id === activeChapter && r.parts[1] === 'section' &&
        !r.query.toString() && document.body.dataset.mode === viewMode) {
      for (const dialog of document.querySelectorAll('dialog[open]')) dialog.close();
      closeWide();
      menu(false);
      goToAnchor(r);
      return;
    }
    render();
  }
  function render(){
    flushDraft();stopDocument();if($('note-dialog').open)flushNote();for(const dialog of document.querySelectorAll('dialog[open]'))dialog.close();closeWide();V.disposeAll();noteChapter='';draftChapter='';activeChapter='';codeStore=[];comparisonSequence=0;const r=route();let html,title;if(r.view!=='chapter')viewMode='read';
    if(r.view==='chapter'){
      const c=chapters.get(r.id);html=chapter(c);title=c.title;
      const stage = D.stages.find(item => item.id === c.stage);
      $('breadcrumb').innerHTML = `<a class="brand-crumb" href="#/home">学习手册</a><span class="sep brand-sep">/</span><span>${E(stage.title)}</span><span class="sep">/</span><span title="${E(c.title)}">第 ${D.lessons.indexOf(c) + 1} 章</span>`;
    }
    else{const renderers={home:['开始学习',home],courses:['全书目录',()=>courses(r.id)],notes:['我的笔记',notes],saved:['收藏与进度',saved],visuals:['图解与实验',visuals],gallery:['紫樱素材画廊',gallery],resources:['资料与工程',resources],review:['设计审查台',review],api:['API 对照',()=>heading('API REFERENCE','API 对照与边界','单位、输入输出、寿命和调用边界，与教材原始验证范围一同查阅。')+D.apiReferences.map(a=>`<section class="reading-section"><h2>${E(a.title)}</h2>${table(a)}<a class="text-link" href="#/${a.lessons[0]}/section/api-details">返回所属章节 →</a></section>`).join('')],compare:['不同写法对照',()=>heading('IMPLEMENTATION NOTES','不同写法对照','在同一个任务背景下，比较语言、API与执行边界。')+D.comparisons.filter(c=>!r.id||c.id===r.id).map(comparison).join('')]};const selected=renderers[r.view]||renderers.home;title=selected[0];html=selected[1]();$('breadcrumb').innerHTML=`<a href="#/home">学习手册</a><span class="sep">/</span><span>${E(title)}</span>`;}
    $('reading').innerHTML=html;document.title=title+' · 鸣神 ROS 2 学习手册';document.body.dataset.mode=viewMode;$('view-mode').value=viewMode;$('toc-trigger').hidden=!activeChapter;$('note-trigger').hidden=!activeChapter;$('note-dot').hidden=!state.notes[activeChapter]?.text.trim();menu(false);mountDocument();tree(chapters.get(activeChapter));
    for(const details of document.querySelectorAll('details[data-lab]'))details.addEventListener('toggle',()=>{if(details.open&&!details.querySelector('.lab-body'))V.mount(details.dataset.lab,details.querySelector('.lab-host'));else if(!details.open)V.dispose(details.dataset.lab);});
    if(pendingPosition?.chapter===activeChapter)for(const id of pendingLabs){const details=document.querySelector(`details[data-lab="${id}"]`);if(details){details.open=true;V.mount(id,details.querySelector('.lab-host'));}}pendingLabs=[];
    if(r.view==='gallery')filterGallery();if(r.view==='resources'){if(r.query.has('query'))$('resource-query').value=r.query.get('query');filterResources();}
    if(r.query.has('theme'))setTheme(r.query.get('theme')==='dark'?'dark':'light');
    requestAnimationFrame(()=>{if(pendingPosition?.chapter===activeChapter){const target=pendingPosition.id&&$(pendingPosition.id);if(target)window.scrollBy({top:target.getBoundingClientRect().top-pendingPosition.top,behavior:'instant'});else window.scrollTo({top:pendingPosition.scroll,behavior:'instant'});pendingPosition=null;}else{pendingPosition=null;goToAnchor(r);}if(r.view==='resources'&&r.query.get('metadata')==='1')$('document-metadata').scrollIntoView({block:'start',behavior:'instant'});if(r.query.get('note')==='1')openNote();if(r.query.has('search'))openSearch(r.query.get('search'));});
  }
  function selectCodeTab(group,index){group.classList.remove('compare');group.querySelector('[data-compare]').setAttribute('aria-pressed','false');group.querySelector('[data-compare]').textContent='并排对照';group.querySelectorAll('[role=tab]').forEach((t,i)=>{t.setAttribute('aria-selected',String(i===index));t.tabIndex=i===index?0:-1;});group.querySelectorAll('[role=tabpanel]').forEach((p,i)=>p.hidden=i!==index);}
  function filterCourses(){const q=$('course-query').value.toLowerCase(),stage=$('course-stage').value,items=D.lessons.filter(c=>(!stage||c.stage===stage)&&(c.title+' '+c.summary).toLowerCase().includes(q));$('course-results').innerHTML=courseRows(items);document.querySelector('.count-line').textContent=items.length+' 章 · '+state.done.length+' 章已完成 · '+state.stars.length+' 章已收藏';}
  function filterResources(){
    const q=$('resource-query').value.trim().toLowerCase();
    $('resource-results').innerHTML=resourceRows(D.resources.filter(r=>[r.title,r.description,r.version,r.category].join(' ').toLowerCase().includes(q)));
    const documents=window.ROS2LocalDocuments.filter(d=>!q||[d.title,d.path,d.branch,d.snapshot].join(' ').toLowerCase().includes(q));
    $('document-metadata-title').textContent=`本地原文元数据 · ${documents.length} 项${documents.length>60?'，先显示60项':''}`;
    $('document-metadata').open=!!q&&documents.length>0;
    $('resource-document-results').innerHTML=documents.slice(0,60).map(d=>`<section class="resource-row"><strong>${E(d.title)}</strong><p class="small-note">${E(d.snapshot)} · ${E(d.branch)} · ${E(d.format)}</p><p><code>${E(d.path)}</code></p><a href="../dist/index.html#/library">在正式教材中查看原文入口 ↗</a></section>`).join('')||'<p class="small-note">没有匹配的原文元数据。</p>';
  }
  function markdownTable(t){const cell=x=>String(x??'').replace(/\|/g,'\\|').replace(/\r?\n/g,'<br>');return ['| '+t.columns.map(cell).join(' | ')+' |','| '+t.columns.map(()=>'---').join(' | ')+' |',...t.rows.map(row=>'| '+row.map(cell).join(' | ')+' |')].join('\n');}
  /* 原文与草稿共用 Markdown 导出。保留来源、验证边界、符号单位、图解和稳定小节标记。
   * 围栏长度大于源码内连续反引号，防止示例自身的围栏提前结束代码块。
   */
  function chapterMarkdown(c){
    const out=['# '+c.title,c.summary];
    const title=(text,id,level=2)=>{if(id)out.push('<!-- section:'+id+' -->');out.push('#'.repeat(level)+' '+text);};
    const fence=b=>{const longest=Math.max(0,...[...(b.code||'').matchAll(/`+/g)].map(m=>m[0].length));const mark='`'.repeat(Math.max(3,longest+1));return mark+(b.language||'')+'\n'+(b.code||'')+'\n'+mark;};
    const exportTable=t=>{out.push(markdownTable(t));if(t.caption)out.push(t.caption);out.push(...(t.notes||[]).map(n=>'- '+n));};
    title('阅读目标','goals');out.push(...(c.goals||[]).map(x=>'- '+x));
    if(c.prerequisites?.length){title('开始之前','prerequisites');out.push(Array.isArray(c.prerequisites)?c.prerequisites.join('；'):c.prerequisites);}
    title('建立整体认识','overview');out.push(...c.concepts||[]);
    for(const [i,s] of c.sections.entries()){
      title(s.title.replace(/^\d+[.．]\s*/,''),'part-'+i);
      out.push(...s.paragraphs||[],...(s.bullets||[]).map(x=>'- '+x));
      for(const eq of s.equations||[]){
        title(eq.label||'公式',null,3);out.push('$$\n'+eq.tex+'\n$$',eq.explanation||'');
        if(eq.symbols?.length)exportTable({columns:['符号','含义','单位 / 维度'],rows:eq.symbols.map(x=>[x.symbol,x.meaning,x.unit||'—'])});
      }
      for(const t of s.tables||[]){if(t.title)title(t.title,null,3);exportTable(t);}
      for(const b of s.codeBlocks||[]){title(b.label||b.language||'代码',null,3);out.push(fence(b),b.explanation||'');}
      for(const f of D.figures.filter(f=>f.placements?.some(p=>p.chapter===c.id&&p.afterSection===i)))out.push('!['+(f.title+' '+(f.caption||'')).replace(/\]/g,')')+'](../dist/'+f.file+')');
      if(i===0)for(const comparison of D.comparisons.filter(x=>x.relatedLessons?.includes(c.id))){
        title(comparison.title,'writing-'+comparison.id);out.push(comparison.question);
        for(const v of comparison.variants){title(v.label,null,3);out.push(fence(v),v.scope||'');}
        out.push(...comparison.notes||[]);
      }
    }
    const apis=D.apiReferences.filter(a=>a.lessons.includes(c.id));
    if(apis.length){title('API 对照与调用边界','api-details');for(const a of apis){title(a.title,null,3);exportTable(a);}}
    if(c.workedExample){const x=c.workedExample;title(x.title,'worked-example');out.push(x.scenario,x.steps.map((s,i)=>(i+1)+'. '+s).join('\n'),'**结果与验收**　'+x.result);}
    title('动手验证','practice');
    for(const [i,s] of c.steps.entries()){if(typeof s==='string')out.push(s);else{title(s.title||'步骤 '+(i+1),null,3);out.push(s.body||'');if(s.code)out.push(fence(s));}}
    out.push(...(c.commands||[]).map(fence));title('检查结果',null,3);out.push(...(c.expected||[]).map(x=>'- '+x));
    title('常见问题与边界','pitfalls');out.push(...(c.pitfalls||[]).map(x=>'- '+x));
    title('练习与答案','exercises');
    for(const [i,q] of (c.exercises?.length?c.exercises:[{question:c.exercise,answer:c.exerciseAnswer}]).entries()){title((i+1)+'. '+q.question,null,3);out.push(q.answer||'');}
    title('参考出处、版本与验证范围','sources');out.push(c.validation||D.meta.exampleValidation);
    for(const r of c.sourceIds.map(id=>sources.get(id)).filter(Boolean))out.push('- ['+r.title+']('+r.url+') · '+r.version+' · '+(r.verification||''));
    return out.filter(x=>x!==undefined&&x!==null).join('\n\n')+'\n';
  }
  document.addEventListener('click',async event=>{
    const b=event.target.closest('button,a');if(!b)return;
    if(b.dataset.close){$(b.dataset.close).close();return;}
    if(b.classList.contains('skip-link')){event.preventDefault();$('reading').focus();return;}
    if(b.dataset.asset){openAsset(b.dataset.asset);return;}
    if(b.dataset.searchKind){searchKind=b.dataset.searchKind;search();return;}
    if(b.dataset.noteMode){noteMode(b.dataset.noteMode);return;}
    if(b.dataset.visualFormat){if(!visualSession?.format(b.dataset.visualFormat))toast('请先在同一段内选中文字。');return;}
    if(b.hasAttribute('data-lab-wide')){openWide(b);return;}
    if(b.dataset.copy!==undefined){const raw=b.closest('.code-example')?.querySelector('pre code')?.textContent??codeStore[Number(b.dataset.copy)];try{await navigator.clipboard.writeText(raw);toast('代码已复制');}catch{$('copy-text').value=raw;$('copy-dialog').showModal();$('copy-text').select();}return;}
    if(b.dataset.codeTab!==undefined){selectCodeTab(b.closest('.implementation'),Number(b.dataset.codeTab));return;}
    if(b.hasAttribute('data-compare')){const group=b.closest('.implementation'),open=!group.classList.contains('compare');if(open){group.classList.add('compare');b.setAttribute('aria-pressed','true');b.textContent='标签阅读';group.querySelectorAll('[role=tabpanel]').forEach(p=>p.hidden=false);}else selectCodeTab(group,Number(group.querySelector('[aria-selected=true]').dataset.codeTab));return;}
    if(b.dataset.study){const key=b.dataset.study==='star'?'stars':'done';state[key]=state[key].includes(activeChapter)?state[key].filter(id=>id!==activeChapter):[...state[key],activeChapter];save();b.setAttribute('aria-pressed',String(state[key].includes(activeChapter)));b.querySelector('span').textContent=key==='stars'?(state[key].includes(activeChapter)?'已收藏':'收藏本章'):(state[key].includes(activeChapter)?'已完成':'标记完成');tree(chapters.get(activeChapter));if(key==='done'&&state.done.includes(activeChapter))toast('又理解了一章，记得留下自己的收获。','mascot-complete');return;}
    const action=b.dataset.action;
    if(action==='edit-chapter'){setViewMode('edit');return;}
    if(action==='visual-undo'){visualSession?.undo();return;}
    if(action==='visual-redo'){visualSession?.redo();return;}
    if(action==='save-textbook'){await saveTextbook();return;}
    if(action==='file-help'){$('file-help-dialog').showModal();return;}
    if(action==='choose-textbook-directory'){await chooseDirectory();return;}
    if(action==='open-source'){openSource();return;}
    if(action==='apply-source'){
      const markdown=$('chapter-source').value;
      if(markdown!==sourceBaseline){editEpoch++;rememberPosition();flushDraft();stopDocument();state.drafts[activeChapter]={markdown,updatedAt:new Date().toISOString()};delete state.visualDrafts[activeChapter];save();$('source-dialog').close();render();toast(storageAvailable?'源码修改已应用。':'修改已应用，尚未持久保存，请导出。');}
      else $('source-dialog').close();return;
    }
    if(action==='restore-chapter'){
      editEpoch++;rememberPosition();flushDraft();draftUndo={id:activeChapter,markdown:state.drafts[activeChapter],visual:state.visualDrafts[activeChapter]};stopDocument();delete state.drafts[activeChapter];delete state.visualDrafts[activeChapter];save();render();toast(diskEditions.chapters[activeChapter]?'当前正文已恢复原文，保存到教材后更新文件。':'已恢复教材原文，可撤销这次恢复。');return;
    }
    if(action==='undo-restore'&&draftUndo?.id===activeChapter){editEpoch++;rememberPosition();flushDraft();stopDocument();if(draftUndo.markdown)state.drafts[activeChapter]=draftUndo.markdown;if(draftUndo.visual)state.visualDrafts[activeChapter]=draftUndo.visual;draftUndo=null;save();render();toast('已恢复刚才的草稿。');return;}
    if(action==='search')openSearch();if(action==='menu')menu(!document.body.classList.contains('menu-open'));if(action==='collapse-tree')tree(chapters.get(activeChapter),true);if(action==='theme')setTheme(state.theme==='dark'?'light':'dark');if(action==='toc')openToc();if(action==='note')openNote();
    if(action==='export-backup'||action==='export-draft-transfer'){flushDraft();download('narukami-notes-backup.json',JSON.stringify(state,null,2),'application/json');}if(action==='import-backup')$('backup-input').click();if(action==='export-note'){flushNote();download(noteChapter+'-笔记.md','# '+chapters.get(noteChapter).title+'\n\n'+$('note-editor').value);}
    if(action==='export-chapter'){flushDraft();download(activeChapter+'.md',currentMarkdown());}
    if (b.closest('.tree-section-list, #toc-list')) {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      if ($('toc-dialog').open) $('toc-dialog').close();
      if (document.body.classList.contains('menu-open')) {
        menu(false);
        $('reading').focus({preventScroll: true});
      }
      if (b.hash === location.hash) {
        event.preventDefault();
        goToAnchor(route());
      }
      return;
    }
    if(b.classList.contains('search-result')){if(viewMode==='edit'){flushDraft();viewMode='read';if(b.hash===location.hash)render();}for(const d of document.querySelectorAll('dialog[open]'))d.close();if(b.hash===location.hash)setTimeout(()=>goToAnchor(route()),0);}
  });
  document.addEventListener('input',event=>{const id=event.target.id;if(id==='chapter-source')$('source-status').textContent='源码有未应用的修改。';if(id==='search-input')search();if(id==='note-editor'){$('note-status').textContent='正在保存…';$('note-count').textContent=event.target.value.length+' 字';clearTimeout(noteTimer);noteTimer=setTimeout(flushNote,450);}if(id==='course-query')filterCourses();if(id==='resource-query')filterResources();if(id==='notes-query'){const q=event.target.value.toLowerCase(),items=noteEntries().filter(([id,n])=>(chapters.get(id).title+' '+n.text).toLowerCase().includes(q));$('notes-count').textContent=items.length+' 篇章节笔记';$('notes-results').innerHTML=items.length?noteCards(items):empty('没有匹配的笔记','试试另一种表达，或者先去章节里写下新的理解。','mascot-tip');}});
  document.addEventListener('change',async event=>{const id=event.target.id;if(id==='view-mode'){setViewMode(event.target.value);return;}if(id==='course-stage')filterCourses();if(['asset-category','asset-placement'].includes(id))filterGallery();if(id==='backup-input'&&event.target.files[0]){try{const file=event.target.files[0];if(file.size>10*1024*1024)throw new Error('备份超过10 MiB，请选择较小的记录文件。');const raw=JSON.parse(await file.text());flushDraft();if($('note-dialog').open)flushNote();state=L.mergeBackup(state,raw,ids);stopDocument();draftChapter='';save();setTheme(state.theme);render();toast(storageAvailable?'笔记、草稿与进度已合并导入':'已读取备份，存储不可用，请再次导出保存');}catch(error){toast(error instanceof SyntaxError?'无法解析 JSON，当前记录保持原样。':error.message);}finally{event.target.value='';}}});
  document.addEventListener('keydown',event=>{
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'&&$('source-dialog').open){event.preventDefault();document.querySelector('[data-action=apply-source]').click();return;}
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'&&viewMode==='edit'&&!document.querySelector('dialog[open]')){event.preventDefault();saveTextbook();return;}
    const typing=/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)||document.activeElement?.isContentEditable;
    // type=search的原生Escape会先清空输入；显式关闭modal，保持各协议与设备的退出行为一致。
    if(event.key==='Escape'&&!event.isComposing){const dialog=[...document.querySelectorAll('dialog[open]')].at(-1);if(dialog){event.preventDefault();dialog.close();return;}}
    if(((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k')||(event.key==='/'&&!typing)){event.preventDefault();if(!$('search-dialog').open&&!document.querySelector('dialog[open]'))openSearch();return;}
    if($('search-dialog').open&&['ArrowDown','ArrowUp','Enter'].includes(event.key)){const results=[...$('search-results').querySelectorAll('.search-result')];if(!results.length)return;event.preventDefault();if(event.key==='Enter'){results[searchActive].click();return;}searchActive=(searchActive+(event.key==='ArrowDown'?1:-1)+results.length)%results.length;results.forEach((r,i)=>r.dataset.active=String(i===searchActive));results[searchActive].scrollIntoView({block:'nearest'});return;}
    if(event.key==='Escape'&&document.body.classList.contains('menu-open')&&!document.querySelector('dialog[open]')){menu(false);$('menu-button').focus();}
    if(event.target.matches('[role=tab]')&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const group=event.target.closest('.implementation'),tabs=[...group.querySelectorAll('[role=tab]')],current=tabs.indexOf(event.target),next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(current+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;selectCodeTab(group,next);tabs[next].focus();}
    if(event.key==='Tab'&&document.body.classList.contains('menu-open')&&!document.querySelector('dialog[open]')){const nodes=[...$('sidebar').querySelectorAll('a,button,summary')].filter(x=>x.getClientRects().length),first=nodes[0],last=nodes.at(-1);if(event.shiftKey&&event.target===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&event.target===last){event.preventDefault();first.focus();}}
  });
  document.addEventListener('pointerdown',event=>{if(event.target.closest('[data-visual-format], [data-action=visual-undo], [data-action=visual-redo]'))event.preventDefault();});
  $('mobile-shade').addEventListener('click',()=>{menu(false);$('menu-button').focus();});$('note-dialog').addEventListener('close',flushNote);$('wide-dialog').addEventListener('close',closeWide);window.addEventListener('pagehide',()=>{flushDraft();stopDocument();if($('note-dialog').open)flushNote();V.disposeAll();});window.addEventListener('hashchange',navigate);matchMedia('(max-width:800px)').addEventListener('change',()=>menu(false));
  document.querySelectorAll('[data-icon]').forEach(el=>{if(el.tagName==='A'){const text=el.childNodes[0];el.insertAdjacentHTML('afterbegin',icon(el.dataset.icon));}else el.innerHTML=icon(el.dataset.icon);});
  setTheme(state.theme);render();
  /* 只读诊断入口，供浏览器验收核对索引与组件数量，不暴露修改正式站记录的能力。 */
  window.NarukamiReview={searchRecords:()=>allSearchRecords().length,stats:()=>({chapters:D.lessons.length,notes:noteEntries().length,drafts:new Set([...Object.keys(state.drafts),...Object.keys(state.visualDrafts)]).size,mode:viewMode,assets:A.length,...V.stats()}),storageKey:KEY};
})();
