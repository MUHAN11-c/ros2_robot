/* 中文离线教材阅读器：旧路由、学习记录与正文共用同一内容源。 */
(() => {
  'use strict';
  const D = window.ROS2Hub, L = window.HubLogic, $ = id => document.getElementById(id);
  if (!D || !L) { $('reading').textContent = '教材数据未加载，请确认文件完整后重新打开。'; return; }
  const chapters = new Map(D.lessons.map(c => [c.id, c]));
  const sources = new Map(D.resources.map(s => [s.id, s]));
  const esc = value => String(value ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const inline = value => esc(value).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  const list = items => `<ul>${(items || []).map(x => `<li>${inline(x)}</li>`).join('')}</ul>`;
  const icons = {search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',book:'<path d="M12 5v15M3 4h5a4 4 0 0 1 4 2 4 4 0 0 1 4-2h5v15h-5a5 5 0 0 0-4 2 5 5 0 0 0-4-2H3Z"/>',menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',down:'<path d="m5 9 7 7 7-7"/>',copy:'<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',columns:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 4v16"/>'};
  const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || ''}</svg>`;
  let state, codeStore = [], sequence = 0, currentId = '', currentRoute = '', toastTimer, storageWarned = false;
  try { state = L.sanitizeState(JSON.parse(localStorage.getItem('ros2-atlas-v1') || 'null'), [...chapters.keys()]); }
  catch { state = L.sanitizeState(null, [...chapters.keys()]); }
  const views = new Set(['home','courses','compare','api','examples','projects','resources','coverage','library','source','ecosystem','troubleshoot','saved','downloads','about']);

  function save() {
    try { localStorage.setItem('ros2-atlas-v1', JSON.stringify(state)); }
    catch { if (!storageWarned) { storageWarned = true; toast('浏览器存储不可用，本次进度仍可导出备份。'); } }
    updateProgress();
  }
  function toast(message) { $('toast').textContent = message; $('toast').classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2600); }
  function updateProgress() { const node = $('reading-progress'); if (node) node.textContent = `${state.done.length} / ${D.lessons.length} 章已完成`; }
  function download(name, text, type = 'text/plain;charset=utf-8') {
    const url = URL.createObjectURL(new Blob([text], {type})), anchor = document.createElement('a');
    anchor.href = url; anchor.download = name; document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function localHref(path) {
    // 原始资料在工作区内独立保存：文件协议直接定位，本地服务使用只读白名单路由。
    if (location.protocol === 'file:') return new URL('../../' + path, location.href).href;
    return '/local/' + String(path).split('/').map(encodeURIComponent).join('/');
  }
  const context = () => ({D, state, chapters, sources, esc, inline, list, codeBlock, implementation, equation, apiTable, localHref, download, toast});

  function highlight(raw) {
    const pattern = /(\/\/[^\n]*|#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:from|import|class|def|return|if|else|while|for|void|auto|const|public|private|include|int|True|False|None|new|using|namespace|try|finally|except)\b|\b\d+(?:\.\d+)?\b)/g;
    let result = '', start = 0;
    for (const match of raw.matchAll(pattern)) {
      result += esc(raw.slice(start, match.index));
      const value = match[0], type = /^(\/\/|#)/.test(value) ? 'comment' : /^["']/.test(value) ? 'string' : /^\d/.test(value) ? 'number' : 'keyword';
      result += `<span class="token-${type}">${esc(value)}</span>`; start = match.index + value.length;
    }
    return result + esc(raw.slice(start));
  }
  function codeBlock(block) {
    const raw = String(block.code || ''), index = codeStore.push(raw) - 1;
    const kind = {complete:'完整文件', snippet:'局部片段', commands:'终端命令', concept:'概念示意'}[block.type] || '局部片段';
    return `<div class="code-example"><div class="code-caption"><span title="${esc(block.label)}">${esc(block.label || block.language || '代码')} · ${kind}</span><button class="copy-button" data-copy="${index}" aria-label="复制 ${esc(block.label || '代码')}">${icon('copy')}<span>复制</span></button></div><pre><code>${highlight(raw)}</code></pre></div>`;
  }
  function equation(eq) {
    return `<figure class="equation"><figcaption>${inline(eq.label || '公式')}</figcaption><div class="math-scroll">${eq.mathml || esc(eq.tex)}</div><p>${inline(eq.explanation)}</p>${eq.symbols?.length ? `<div class="table-scroll"><table class="symbol-table"><thead><tr><th>符号</th><th>含义</th><th>单位／维度</th></tr></thead><tbody>${eq.symbols.map(s => `<tr><td><code>${esc(s.symbol)}</code></td><td>${inline(s.meaning)}</td><td>${inline(s.unit || '—')}</td></tr>`).join('')}</tbody></table></div>` : ''}<details class="formula-source"><summary>查看公式源码</summary><pre><code>${esc(eq.tex)}</code></pre></details></figure>`;
  }
  function apiTable(item) {
    return `<section class="api-reference${item.evidenceFile ? ' experiment-table' : ''}"><h3>${inline(item.title)}</h3><div class="table-scroll"><table><thead><tr>${item.columns.map(x => `<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${item.rows.map(row => `<tr>${row.map(x => `<td>${inline(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${item.notes?.length ? list(item.notes) : ''}</section>`;
  }
  function implementation(comparison) {
    const group = 'implementation-' + sequence++;
    return `<section class="reading-section implementation-section" id="writing-${esc(comparison.id)}"><h2>${inline(comparison.title || '同一功能的不同实现')}</h2><p class="comparison-question">${inline(comparison.question)}</p><div class="implementation" id="${group}" style="--variants:${comparison.variants.length}"><div class="implementation-toolbar"><div class="code-tabs" role="tablist" aria-label="实现语言">${comparison.variants.map((v,i) => `<button role="tab" id="${group}-tab-${i}" aria-controls="${group}-panel-${i}" aria-selected="${i === 0}" tabindex="${i === 0 ? 0 : -1}" data-tab="${i}">${esc(v.label)}</button>`).join('')}</div><button class="compare-toggle" aria-pressed="false" data-compare>${icon('columns')}<span>并排对照</span></button></div><div class="implementation-panels">${comparison.variants.map((v,i) => `<div class="implementation-pane" role="tabpanel" id="${group}-panel-${i}" aria-labelledby="${group}-tab-${i}" ${i ? 'hidden' : ''}><div class="language-label">${esc(v.label)}</div>${codeBlock({...v,label:v.label})}<div class="code-explanation">${inline(v.scope || '')}</div></div>`).join('')}</div></div>${list(comparison.notes || [])}</section>`;
  }
  function section(s, index) {
    return `<section class="reading-section" id="part-${index}"><h2>${esc(s.title.replace(/^\d+[.．]\s*/, ''))}<a class="section-anchor" href="#/${currentId}/section/part-${index}" aria-label="本节链接">#</a></h2>${(s.paragraphs || []).map(p => `<p>${inline(p)}</p>`).join('')}${s.bullets?.length ? list(s.bullets) : ''}${(s.equations || []).map(equation).join('')}${(s.tables || []).map(table => apiTable({...table,notes:table.caption ? [table.caption] : []})).join('')}${(s.codeBlocks || []).map(b => codeBlock(b) + (b.explanation ? `<p class="code-explanation">${inline(b.explanation)}</p>` : '')).join('')}</section>`;
  }
  function chapter(c) {
    currentId = c.id; state.last = c.id; save();
    const local = window.ROS2LocalEditions?.chapters?.[c.id];
    if (local) return `<article class="local-edition"><p class="notice">本地教材修订 · ${esc(local.savedAt)} · <a href="chapters/${c.id}.html" target="_blank" rel="noopener">章节文件 ↗</a></p>${local.document.html}<div class="study-actions"><button data-study="done">标记为已完成</button><button data-study="star">收藏本章</button><button data-study="export">下载本章</button><button data-print>打印</button></div></article>`;
    const index = D.lessons.indexOf(c), stage = D.stages.find(x => x.id === c.stage);
    const comparisons = D.comparisons.filter(x => x.relatedLessons?.includes(c.id));
    const api = (D.apiReferences || []).filter(x => x.lessons?.includes(c.id));
    const exercises = [...(c.exercises || []), {question:c.exercise, answer:c.exerciseAnswer}];
    const x = c.workedExample;
    return `<article><header class="chapter-header"><div class="chapter-overline">${esc(stage.title)}<span>/ CHAPTER ${String(index + 1).padStart(2,'0')}</span></div><h1>${esc(c.title)}</h1><p class="chapter-intro">${inline(c.summary)}</p><div class="chapter-meta"><span>${esc(c.version)}</span><i></i><span>原理 · API · 实验 · 答案</span></div><div class="study-actions"><button data-study="done" aria-pressed="${state.done.includes(c.id)}">${state.done.includes(c.id) ? '✓ 已完成 · 取消标记' : '标记为已完成'}</button><button data-study="star" aria-pressed="${state.stars.includes(c.id)}">${state.stars.includes(c.id) ? '★ 已收藏' : '☆ 收藏本章'}</button><button data-study="export">下载本章</button><button data-print>打印</button></div></header><details class="mini-toc"><summary>${icon('book')}本章学习目标与目录</summary>${list(c.goals)}<ol>${(c.sections || []).map((s,i) => `<li><a href="#/${c.id}/section/part-${i}" data-scroll="part-${i}">${esc(s.title)}</a></li>`).join('')}</ol></details>${c.prerequisites?.length ? `<div class="learning-goals"><p><strong>开始之前</strong>　${inline(Array.isArray(c.prerequisites) ? c.prerequisites.join('；') : c.prerequisites)}</p></div>` : ''}<section class="reading-section"><h2>建立整体认识</h2>${c.concepts.map(p => `<p>${inline(p)}</p>`).join('')}</section>${(c.sections || []).map((s,i) => section(s,i) + (i === 0 ? comparisons.map(implementation).join('') : '')).join('')}${api.length ? `<section class="reading-section" id="api-details"><h2>API 对照与调用边界</h2>${api.map(apiTable).join('')}</section>` : ''}${c.id === 'qos' ? qosWidget() : ''}${x ? `<section class="reading-section"><h2>${esc(x.title)}</h2><p>${inline(x.scenario)}</p><ol>${x.steps.map(s => `<li>${inline(s)}</li>`).join('')}</ol><div class="learning-goals"><p><strong>结果与验收</strong>　${inline(x.result)}</p></div></section>` : ''}<section class="reading-section" id="practice"><h2>动手验证</h2>${c.steps.map((s,i) => typeof s === 'string' ? `<p>${inline(s)}</p>` : `<div class="compact-example"><h3>${esc(s.title || `步骤 ${i + 1}`)}</h3><p>${inline(s.body || '')}</p>${s.code ? codeBlock({...s, label:s.label || s.title, type:s.type || 'commands'}) : ''}</div>`).join('')}${(c.commands || []).map(codeBlock).join('')}<div class="learning-goals"><p><strong>检查结果</strong>　${c.expected.map(inline).join('；')}</p></div></section><section class="reading-section"><h2>常见问题与边界</h2>${list(c.pitfalls)}</section><section class="reading-section"><h2>练习与答案</h2><div class="exercise-list">${exercises.map((q,i) => `<details class="exercise-item"><summary><span>${String(i + 1).padStart(2,'0')}</span>${inline(q.question)}</summary><p>${inline(q.answer)}</p></details>`).join('')}</div></section><details class="source-note"><summary>参考出处、版本与验证范围</summary><p>${inline(c.validation || '具体运行范围见示例验证记录。')}</p><ul>${c.sourceIds.map(id => sources.get(id)).filter(Boolean).map(s => `<li>${esc(s.title)} · ${esc(s.version)} · ${inline(s.verification)} <a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">原始出处 ↗</a></li>`).join('')}</ul>${coverageForChapter(c.id)}</details><nav class="chapter-pager" aria-label="相邻章节">${[D.lessons[index - 1], D.lessons[index + 1]].map((other,i) => other ? `<a href="#/${other.id}"><small>${i ? '下一章 →' : '← 上一章'}</small>${esc(other.title)}</a>` : '<span></span>').join('')}</nav></article>`;
  }
  function coverageForChapter(id) {
    const rows = (D.coverage?.entries || []).filter(x => x.relatedLessons?.includes(id) && x.kind !== 'auxiliary');
    return rows.length ? `<p>本章与 ${rows.length} 个参考页面存在主题对应；对应关系的深度单独记录，不等于逐段收录。</p><a href="#/coverage">查看对应关系与覆盖说明</a>` : '';
  }
  function qosWidget() {
    return `<section class="reading-section qos-widget"><h2>动手比较 QoS 请求与提供</h2><p>改变两个端点的可靠性和持久性，检查请求与提供关系。这里只验证这两个策略，仍需核对话题、类型、其他 QoS 和网络。</p><div class="qos-fields">${['offered','requested'].map((role,i) => `<fieldset><legend>${i ? '订阅者请求' : '发布者提供'}</legend><label>可靠性<select data-qos="${role}-reliability"><option value="reliable">Reliable</option><option value="best_effort">Best effort</option></select></label><label>持久性<select data-qos="${role}-durability"><option value="volatile">Volatile</option><option value="transient_local">Transient local</option></select></label></fieldset>`).join('')}</div><output id="qos-result" class="notice">这两个策略可以匹配；继续核对其余通信条件。</output></section>`;
  }
  function parseRoute() {
    try {
      const parts = location.hash.replace(/^#\/?/, '').split('/');
      const head = decodeURIComponent(parts[0] || 'home');
      if (head === 'lesson') return {view:'chapter', id:decodeURIComponent(parts[1] || ''), parts:parts.slice(1)};
      if (chapters.has(head)) return {view:'chapter', id:head, parts};
      return {view:views.has(head) ? head : 'home', id:decodeURIComponent(parts.slice(1).join('/')), parts};
    } catch { return {view:'home', id:'', parts:[]}; }
  }
  function tree(c) {
    const opened = new Set([...document.querySelectorAll('.tree-stage[open]')].map(x => x.dataset.stage));
    $('chapter-tree').innerHTML = D.stages.map((stage,i) => `<details class="tree-stage" data-stage="${stage.id}" ${stage.id === c?.stage || opened.has(stage.id) || (!c && i === 0) ? 'open' : ''}><summary>${esc(stage.title)}${icon('down')}</summary>${D.lessons.filter(x => x.stage === stage.id).map(x => `<a class="tree-link${state.done.includes(x.id) ? ' done' : ''}" href="#/${x.id}" ${x.id === c?.id ? 'aria-current="page"' : ''}><span>${String(D.lessons.indexOf(x) + 1).padStart(2,'0')}</span>${esc(x.title)}</a>`).join('')}</details>`).join('');
    document.querySelectorAll('.library-nav a').forEach(a => a.toggleAttribute('aria-current', a.hash === location.hash));
    // 只滚动章节树自己的容器，保持当前章可见；不改变正文的阅读位置。
    const active=$('chapter-tree').querySelector('[aria-current=page]');
    if(active){
      const viewport=$('chapter-tree').getBoundingClientRect(),item=active.getBoundingClientRect();
      if(item.top<viewport.top)$('chapter-tree').scrollTop-=viewport.top-item.top;
      else if(item.bottom>viewport.bottom)$('chapter-tree').scrollTop+=item.bottom-viewport.bottom;
    }
    updateProgress();
  }
  function scrollTarget(parts) {
    const target = parts[1] === 'figure' ? 'fig-' + parts[2] : parts[1] === 'section' ? parts[2] : null;
    requestAnimationFrame(() => { const node = target && $(target); if (node) node.scrollIntoView({block:'start', behavior:'instant'}); else window.scrollTo({top:0, behavior:'instant'}); });
  }
  function render(preserve = false) {
    const y = scrollY, route = parseRoute(), c = chapters.get(route.id);
    codeStore = []; sequence = 0; currentId = ''; currentRoute = route.view;
    document.querySelectorAll('dialog[open]').forEach(d => d.close());
    if (route.view === 'chapter' && c) {
      $('reading').innerHTML = chapter(c); $('breadcrumb-stage').textContent = D.stages.find(s => s.id === c.stage).title;
      document.title = c.title + ' · ROS 2 学习手册'; if(!window.ROS2LocalEditions?.chapters?.[c.id])window.PreviewFigures?.mount(c);
    } else if (route.view === 'chapter') {
      $('reading').innerHTML = '<header class="chapter-header"><h1>没有找到这个章节</h1><p>链接中的章节标识不存在。可从全书目录重新选择，既有有效章节链接仍然可用。</p><a class="button" href="#/courses">打开全书目录</a></header>';
      $('breadcrumb-stage').textContent = '章节未找到'; document.title = '章节未找到 · ROS 2 学习手册';
    } else {
      const result = window.ReaderLibrary.render(route.view, route.id, context());
      $('reading').innerHTML = result.html; $('breadcrumb-stage').textContent = result.title;
      document.title = result.title + ' · ROS 2 学习手册';
      window.ReaderLibrary.afterRender?.(route.view, route.id, context());
    }
    tree(c); setMenu(false);
    if (preserve) window.scrollTo({top:y, behavior:'instant'}); else scrollTarget(route.parts);
    document.body.dataset.theme = state.theme;
  }
  function selectTab(group, index) {
    group.classList.remove('compare'); group.querySelector('[data-compare]').setAttribute('aria-pressed','false'); group.querySelector('[data-compare] span').textContent = '并排对照';
    group.querySelectorAll('[role=tab]').forEach((tab,i) => { tab.setAttribute('aria-selected', String(i === index)); tab.tabIndex = i === index ? 0 : -1; });
    group.querySelectorAll('[role=tabpanel]').forEach((panel,i) => panel.hidden = i !== index);
  }
  function setMenu(open) {
    document.body.classList.toggle('menu-open', open); $('shade').hidden = !open; $('menu-button').setAttribute('aria-expanded', String(open));
    if (open) $('sidebar').querySelector('[aria-current=page],.brand')?.focus({preventScroll:true});
  }
  const searchDocs = [
    ...Object.values(window.ROS2LocalEditions?.chapters || {}).map(local => ({title:local.document.title,text:local.document.markdown,summary:'本地教材修订',kind:'教材修订',href:'#/' + local.chapterId})),
    ...D.lessons.map(c => ({title:c.title,text:JSON.stringify(c),summary:c.summary,kind:'教材正文',href:'#/' + c.id})),
    ...(D.apiReferences || []).map(a => ({title:a.title,text:JSON.stringify(a),summary:a.notes?.[0] || 'API 对照、单位与调用边界',kind:'API',href:'#/' + a.lessons[0] + '/section/api-details'})),
    ...D.comparisons.map(c => ({title:c.title,text:JSON.stringify(c),summary:c.question,kind:'写法对照',href:'#/compare/' + c.id}))
  ];
  function search() {
    const q = $('search-input').value.trim(), items = q ? L.search(searchDocs,q) : searchDocs.filter(x => /话题|坐标|线性|导航/.test(x.title)).slice(0,8);
    $('search-results').innerHTML = items.length ? items.slice(0,35).map(c => `<a class="search-result" href="${esc(c.href)}"><small>${esc(c.kind)}</small><strong>${esc(c.title)}</strong><small>${esc(c.summary.slice(0,140))}</small></a>`).join('') : '<div class="search-empty">没有找到匹配内容，试试话题、雅可比、rclcpp 或 Nav2。</div>';
  }
  function openSearch() { setMenu(false); $('search-dialog').showModal(); search(); $('search-input').focus(); }
  function updateStudyButtons() {
    const c = chapters.get(currentId); if (!c) return;
    const done = document.querySelector('[data-study=done]'), star = document.querySelector('[data-study=star]');
    done.textContent = state.done.includes(c.id) ? '✓ 已完成 · 取消标记' : '标记为已完成'; done.setAttribute('aria-pressed', String(state.done.includes(c.id)));
    star.textContent = state.stars.includes(c.id) ? '★ 已收藏' : '☆ 收藏本章'; star.setAttribute('aria-pressed', String(state.stars.includes(c.id))); tree(c);
  }
  document.addEventListener('click', async event => {
    const el = event.target.closest('button,a'); if (!el) return;
    if (el.classList.contains('skip-link')) { event.preventDefault(); $('reading').focus(); return; }
    if (el.dataset.close) { $(el.dataset.close).close(); return; }
    if (el.dataset.scroll) { event.preventDefault(); $(el.dataset.scroll)?.scrollIntoView(); return; }
    if (el.dataset.tab !== undefined) { selectTab(el.closest('.implementation'), Number(el.dataset.tab)); return; }
    if (el.hasAttribute('data-compare')) {
      const group = el.closest('.implementation'), open = !group.classList.contains('compare');
      if (open) { group.classList.add('compare'); el.setAttribute('aria-pressed','true'); el.querySelector('span').textContent = '单栏阅读'; group.querySelectorAll('[role=tabpanel]').forEach(p => p.hidden = false); }
      else selectTab(group, Number(group.querySelector('[aria-selected=true]').dataset.tab)); return;
    }
    if (el.dataset.copy !== undefined) {
      const raw = codeStore[Number(el.dataset.copy)];
      try { await navigator.clipboard.writeText(raw); toast('代码已复制'); }
      catch { $('copy-text').value = raw; $('copy-dialog').showModal(); $('copy-text').select(); } return;
    }
    if (el.dataset.study) {
      if (el.dataset.study === 'export') download(currentId + '.md', window.ROS2LocalEditions?.chapters?.[currentId]?.document.markdown || window.ReaderLibrary.chapterMarkdown(chapters.get(currentId), context()));
      else { const key = el.dataset.study === 'done' ? 'done' : 'stars'; state[key] = state[key].includes(currentId) ? state[key].filter(x => x !== currentId) : [...state[key],currentId]; save(); updateStudyButtons(); } return;
    }
    if (el.hasAttribute('data-export-progress')) { download('ros2-reading-progress.json', JSON.stringify({format:'ros2-atlas-v1',...state},null,2),'application/json'); return; }
    if (el.hasAttribute('data-theme')) { state.theme = state.theme === 'dark' ? 'light' : 'dark'; save(); document.body.dataset.theme = state.theme; return; }
    if (el.hasAttribute('data-print')) { window.print(); return; }
    if (el.classList.contains('search-result')) $('search-dialog').close();
    window.ReaderLibrary.click?.(event,el,context());
  });
  document.addEventListener('input', event => { if (event.target.id === 'search-input') search(); else window.ReaderLibrary.filter?.(event,context()); });
  document.addEventListener('change', async event => {
    const el = event.target;
    if (el.dataset.qos) {
      const read = role => ({reliability:document.querySelector(`[data-qos="${role}-reliability"]`).value,durability:document.querySelector(`[data-qos="${role}-durability"]`).value});
      const ok = L.qosCompatible(read('offered'),read('requested')); $('qos-result').textContent = ok ? '这两个策略可以匹配；继续核对其余通信条件。' : '策略不兼容：提供的能力无法满足订阅者请求。'; $('qos-result').classList.toggle('bad',!ok);
    } else if (el.id === 'import-progress' && el.files[0]) {
      try { if (el.files[0].size > 100000) throw new Error('size'); const raw = JSON.parse(await el.files[0].text()); if (raw.format !== 'ros2-atlas-v1') throw new Error('format'); state = L.sanitizeState(raw,[...chapters.keys()]); save(); render(true); toast('学习记录已导入'); }
      catch { toast('无法导入，请选择本站导出的进度 JSON。'); }
    } else window.ReaderLibrary.filter?.(event,context());
  });
  document.addEventListener('keydown', event => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
    if (((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') || (event.key === '/' && !typing)) { event.preventDefault(); if (!$('search-dialog').open) openSearch(); return; }
    if (event.key === 'Escape') { const dialog = document.querySelector('dialog[open]'); if (dialog) { event.preventDefault(); dialog.close(); return; } if (document.body.classList.contains('menu-open')) { setMenu(false); $('menu-button').focus(); } }
    if (event.target.matches('[role=tab]') && ['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) {
      event.preventDefault(); const group = event.target.closest('.implementation'), tabs = [...group.querySelectorAll('[role=tab]')], i = tabs.indexOf(event.target);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (i + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length; selectTab(group,next); tabs[next].focus();
    }
    if (event.key === 'Tab' && document.body.classList.contains('menu-open') && !document.querySelector('dialog[open]')) {
      const nodes = [...$('sidebar').querySelectorAll('a,button,summary')].filter(x => x.getClientRects().length), first = nodes[0], last = nodes.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
  $('search-trigger').addEventListener('click',openSearch); $('search-input').addEventListener('input',search);
  $('design-trigger').addEventListener('click',() => $('design-dialog').showModal());
  $('menu-button').addEventListener('click',() => setMenu(!document.body.classList.contains('menu-open')));
  $('shade').addEventListener('click',() => { setMenu(false); $('menu-button').focus(); });
  window.addEventListener('hashchange',() => { const route = parseRoute(); if (route.view === 'chapter' && route.id === currentId && route.parts[1]) { document.querySelectorAll('dialog[open]').forEach(d => d.close()); scrollTarget(route.parts); } else render(); });
  render();
})();
