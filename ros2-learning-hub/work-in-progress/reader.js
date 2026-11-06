/* 阅读版式样稿：复用现有教材数据，不扩写课程内容。 */
(() => {
  'use strict';
  const D = window.ROS2Hub;
  const $ = id => document.getElementById(id);
  const chapters = new Map(D.lessons.map(c => [c.id, c]));
  const sources = new Map(D.resources.map(s => [s.id, s]));
  const icons = {
    search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    book:'<path d="M12 5v15M3 4h5a4 4 0 0 1 4 2 4 4 0 0 1 4-2h5v15h-5a5 5 0 0 0-4 2 5 5 0 0 0-4-2H3Z"/>',
    menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
    down:'<path d="m5 9 7 7 7-7"/>',
    copy:'<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    columns:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 4v16"/>'
  };
  const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || ''}</svg>`;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const inline = value => esc(value).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  const title = value => value.replace(/^\d+[.．]\s*/, '');
  let codeStore = [], groupSequence = 0, currentId = 'pubsub', toastTimer;

  function highlight(raw) {
    const tokens = /(\/\/[^\n]*|#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:from|import|class|def|return|if|else|while|for|void|auto|const|public|private|include|int|True|False|None|new|using|namespace)\b|\b\d+(?:\.\d+)?\b)/g;
    let result='', start=0;
    for (const match of raw.matchAll(tokens)) {
      result += esc(raw.slice(start,match.index));
      const value=match[0], type=/^(\/\/|#)/.test(value)?'comment':/^["']/.test(value)?'string':/^\d/.test(value)?'number':'keyword';
      result += `<span class="token-${type}">${esc(value)}</span>`;
      start=match.index+value.length;
    }
    return result+esc(raw.slice(start));
  }

  function codeBlock(block) {
    const index=codeStore.push(block.code)-1;
    return `<div class="code-example"><div class="code-caption"><span title="${esc(block.label)}">${esc(block.label || block.language)}</span><button class="copy-button" data-copy="${index}" aria-label="复制 ${esc(block.label || block.language)}">${icon('copy')}<span>复制</span></button></div><pre><code>${highlight(block.code)}</code></pre></div>`;
  }

  function implementation(comparison) {
    const group='implementation-'+groupSequence++;
    return `<section class="reading-section" id="writing"><h2>不同写法，同一个接口</h2><p class="comparison-question">${inline(comparison.question)}</p><div class="implementation" id="${group}" style="--variants:${comparison.variants.length}"><div class="implementation-toolbar"><div class="code-tabs" role="tablist" aria-label="实现语言">${comparison.variants.map((v,i)=>`<button role="tab" id="${group}-tab-${i}" aria-controls="${group}-panel-${i}" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-tab="${i}">${esc(v.label)}</button>`).join('')}</div><button class="compare-toggle" aria-pressed="false" data-compare>${icon('columns')}<span>并排对照</span></button></div><div class="implementation-panels">${comparison.variants.map((v,i)=>`<div class="implementation-pane" role="tabpanel" id="${group}-panel-${i}" aria-labelledby="${group}-tab-${i}" ${i?'hidden':''}><div class="language-label">${esc(v.label)}</div>${codeBlock({...v,label:v.label+(v.type==='complete'?' · 完整文件':' · 核心片段')})}<div class="code-explanation">${inline(v.scope)}</div></div>`).join('')}</div></div><ul class="notes">${comparison.notes.map(n=>`<li>${inline(n)}</li>`).join('')}</ul></section>`;
  }

  function section(s,index) {
    return `<section class="reading-section" id="part-${index}"><h2>${esc(title(s.title))}<a class="section-anchor" href="#/${currentId}/section/part-${index}" aria-label="本节链接">#</a></h2>${(s.paragraphs||[]).map(p=>`<p>${inline(p)}</p>`).join('')}${s.bullets?.length?`<ul>${s.bullets.map(x=>`<li>${inline(x)}</li>`).join('')}</ul>`:''}${(s.codeBlocks||[]).map(b=>codeBlock(b)+(b.explanation?`<p class="code-explanation">${inline(b.explanation)}</p>`:'')).join('')}</section>`;
  }

  function tree(c) {
    $('chapter-tree').innerHTML=D.stages.map((stage,i)=>`<details class="tree-stage" ${stage.id===c.stage||i===0?'open':''}><summary>${esc(stage.title)}${icon('down')}</summary>${D.lessons.filter(x=>x.stage===stage.id).map(x=>`<a class="tree-link" href="#/${x.id}" ${x.id===c.id?'aria-current="page"':''}><span>${String(D.lessons.indexOf(x)+1).padStart(2,'0')}</span>${esc(x.title)}</a>`).join('')}</details>`).join('');
  }

  function render() {
    const route=location.hash.replace(/^#\/?/,'').split('/');
    const id=route[0];
    const c=chapters.get(id)||chapters.get('pubsub');currentId=c.id;
    codeStore=[];groupSequence=0;
    const index=D.lessons.indexOf(c),stage=D.stages.find(x=>x.id===c.stage);
    const comparison=D.comparisons.find(x=>x.relatedLessons?.includes(c.id));
    const heading=c.title.replace(/^C\+\+ \/ Python /,'');
    const exercises=[...(c.exercises||[]),{question:c.exercise,answer:c.exerciseAnswer}];
    tree(c);
    $('breadcrumb-stage').textContent=stage.title;
    document.title=heading+' · ROS 2 学习手册 · 版式样稿';
    const x=c.workedExample;
    $('reading').innerHTML=`<article><header class="chapter-header"><div class="chapter-overline">${esc(stage.title)}<span>/ CHAPTER ${String(index+1).padStart(2,'0')}</span></div><h1>${esc(heading)}</h1><p class="chapter-intro">${inline(c.summary)}</p><div class="chapter-meta"><span>ROS 2 Jazzy</span><i></i><span>原理 · 实现 · 动手验证</span></div></header><details class="mini-toc"><summary>${icon('book')}本章学习目标与内容</summary><ul>${c.goals.map(g=>`<li>${inline(g)}</li>`).join('')}</ul><ul>${(c.sections||[]).map((s,i)=>`<li><a href="#part-${i}" data-scroll="part-${i}">${esc(title(s.title))}</a></li>`).join('')}</ul></details>${(c.sections||[]).map((s,i)=>section(s,i)+(i===0&&comparison?implementation(comparison):'')).join('')}${x?`<section class="reading-section"><h2>${esc(x.title)}</h2><p>${inline(x.scenario)}</p><ol>${x.steps.map(s=>`<li>${inline(s)}</li>`).join('')}</ol><div class="learning-goals"><p><strong>预期结果</strong>　${inline(x.result)}</p></div></section>`:''}<section class="reading-section"><h2>动手验证</h2>${c.steps.map(s=>typeof s==='string'?`<p>${inline(s)}</p>`:`<div class="compact-example"><h3>${esc(s.title)}</h3><p>${inline(s.body||'')}</p>${s.code?codeBlock({code:s.code,language:s.language||'bash',label:s.title}):''}</div>`).join('')}${(c.commands||[]).map(codeBlock).join('')}<div class="learning-goals"><p><strong>检查结果</strong>　${c.expected.map(inline).join('；')}</p></div></section><section class="reading-section"><h2>常见问题</h2><ul>${c.pitfalls.map(p=>`<li>${inline(p)}</li>`).join('')}</ul></section><section class="reading-section"><h2>练习与答案</h2><div class="exercise-list">${exercises.map((q,i)=>`<details class="exercise-item"><summary><span>${String(i+1).padStart(2,'0')}</span>${inline(q.question)}</summary><p>${inline(q.answer)}</p></details>`).join('')}</div></section><details class="source-note"><summary>参考出处与版本说明</summary><p>${inline(c.validation||'资料和版本核查范围见正文。')}</p><ul>${c.sourceIds.map(id=>sources.get(id)).filter(Boolean).map(s=>`<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a></li>`).join('')}</ul></details><nav class="chapter-pager" aria-label="相邻章节">${[D.lessons[index-1],D.lessons[index+1]].map((other,i)=>other?`<a href="#/${other.id}"><small>${i?'下一章 →':'← 上一章'}</small>${esc(other.title)}</a>`:'<span></span>').join('')}</nav></article>`;
    window.PreviewFigures?.mount(c);
    document.querySelectorAll('dialog[open]').forEach(d=>d.close());
    setMenu(false);scrollTarget(route);
  }

  function scrollTarget(route){
    const target=route[1]==='figure'?'fig-'+route[2]:route[1]==='section'?route[2]:null;
    requestAnimationFrame(()=>{const node=target&&document.getElementById(target);if(node){node.scrollIntoView({block:'start',behavior:'instant'})}else window.scrollTo({top:0,behavior:'instant'})});
  }

  function selectTab(group,index) {
    group.classList.remove('compare');group.querySelector('[data-compare]').setAttribute('aria-pressed','false');
    group.querySelector('[data-compare] span').textContent='并排对照';
    group.querySelectorAll('[role=tab]').forEach((tab,i)=>{tab.setAttribute('aria-selected',String(i===index));tab.tabIndex=i===index?0:-1});
    group.querySelectorAll('[role=tabpanel]').forEach((panel,i)=>panel.hidden=i!==index);
  }

  function setMenu(open) {
    document.body.classList.toggle('menu-open',open);$('shade').hidden=!open;
    $('menu-button').setAttribute('aria-expanded',String(open));
    if(open)$('sidebar').querySelector('[aria-current=page]')?.focus({preventScroll:true});
  }

  function search() {
    const q=$('search-input').value.trim().toLowerCase();
    const items=q?D.lessons.filter(c=>JSON.stringify(c).toLowerCase().includes(q)):D.lessons.filter(c=>['pubsub','launch','tf2','qos'].includes(c.id));
    $('search-results').innerHTML=items.length?items.slice(0,14).map(c=>`<a class="search-result" href="#/${c.id}"><strong>${esc(c.title)}</strong><small>${esc(c.summary)}</small></a>`).join(''):'<div class="search-empty">没有找到对应内容，试试话题、坐标或 launch。</div>';
  }
  function openSearch() {setMenu(false);$('search-dialog').showModal();search();$('search-input').focus()}
  function toast(message){$('toast').textContent=message;$('toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),1800)}

  document.addEventListener('click',async event=>{
    const el=event.target.closest('button,a');if(!el)return;
    if(el.classList.contains('skip-link')){event.preventDefault();$('reading').focus();return}
    if(el.dataset.close){$(el.dataset.close).close();return}
    if(el.closest('#design-dialog')&&el.tagName==='A')$('design-dialog').close();
    if(el.dataset.scroll){event.preventDefault();$(el.dataset.scroll)?.scrollIntoView();return}
    if(el.dataset.tab!==undefined){selectTab(el.closest('.implementation'),Number(el.dataset.tab));return}
    if(el.hasAttribute('data-compare')){
      const group=el.closest('.implementation'),open=!group.classList.contains('compare');
      if(open){group.classList.add('compare');el.setAttribute('aria-pressed','true');el.querySelector('span').textContent='单栏阅读';group.querySelectorAll('[role=tabpanel]').forEach(p=>p.hidden=false)}
      else selectTab(group,Number(group.querySelector('[aria-selected=true]').dataset.tab));
      return;
    }
    if(el.dataset.copy!==undefined){const raw=codeStore[Number(el.dataset.copy)];try{await navigator.clipboard.writeText(raw);toast('代码已复制')}catch{$('copy-text').value=raw;$('copy-dialog').showModal();$('copy-text').select()}return}
    if(el.classList.contains('search-result')){$('search-dialog').close();if(el.hash==='#/'+currentId)$('reading').focus()}
  });
  document.addEventListener('keydown',event=>{
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();if(!$('search-dialog').open)openSearch();return}
    if(event.key==='Escape'){
      const dialog=document.querySelector('dialog[open]');
      if(dialog){event.preventDefault();dialog.close();return}
      if(document.body.classList.contains('menu-open')){setMenu(false);$('menu-button').focus()}
    }
    if(event.target.matches('[role=tab]')&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
      event.preventDefault();const group=event.target.closest('.implementation'),tabs=[...group.querySelectorAll('[role=tab]')],i=tabs.indexOf(event.target);
      const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
      selectTab(group,next);tabs[next].focus();
    }
    if(event.key==='Tab'&&document.body.classList.contains('menu-open')){
      const items=[...$('sidebar').querySelectorAll('a,button,summary')].filter(x=>x.checkVisibility()),first=items[0],last=items.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
    }
  });
  document.querySelectorAll('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));
  $('search-trigger').addEventListener('click',openSearch);
  $('design-trigger').addEventListener('click',()=>$('design-dialog').showModal());
  $('search-input').addEventListener('input',search);
  $('menu-button').addEventListener('click',()=>setMenu(!document.body.classList.contains('menu-open')));
  $('shade').addEventListener('click',()=>{setMenu(false);$('menu-button').focus()});
  window.addEventListener('hashchange',()=>{const route=location.hash.replace(/^#\/?/,'').split('/');if(route[0]===currentId&&route[1]){document.querySelectorAll('dialog[open]').forEach(d=>d.close());scrollTarget(route)}else render()});
  render();
})();
