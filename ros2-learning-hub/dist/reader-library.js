/* 学习总览、参考附录与下载。正文阅读不依赖这些外部资料入口。 */
(() => {
  'use strict';
  let C;
  const $ = id => document.getElementById(id);
  const e = value => C.esc(value), t = value => C.inline(value);
  const safe = url => /^https?:\/\//.test(url) ? e(url) : '#';
  const heading = (overline,title,intro) => `<header class="chapter-header"><div class="chapter-overline">${e(overline)}</div><h1>${e(title)}</h1><p class="chapter-intro">${t(intro)}</p></header>`;
  const notice = text => `<div class="notice">${t(text)}</div>`;
  const links = ids => (ids || []).filter(id => C.chapters.has(id)).map(id => `<a class="lesson-chip" href="#/${id}">${e(C.chapters.get(id).title)}</a>`).join('');
  const buttons = items => `<div class="button-row">${items.map(([href,label]) => `<a class="button" href="${e(href)}">${e(label)}</a>`).join('')}</div>`;
  const row = c => `<a class="lesson-row" href="#/${c.id}"><span class="lesson-number">${String(C.D.lessons.indexOf(c) + 1).padStart(2,'0')}</span><div><h3>${e(c.title)}</h3><p>${t(c.summary)}</p><small><code>${e(c.id)}</code> · ${e(c.version)}</small></div><span class="row-check">${C.state.done.includes(c.id) ? '✓' : '→'}</span></a>`;
  function courses() {
    return heading('THE LEARNING PATH','把原理、代码和实验连起来','从基础环境到通信开发，再到数学、状态估计、控制与完整项目。每章在站内展开讲解、代码、实验和答案。') + C.D.stages.map(stage => `<section class="reading-section"><div class="section-heading"><h2>${e(stage.title)}</h2><span>${C.D.lessons.filter(c => c.stage === stage.id).length} 章</span></div><p>${t(stage.description)}</p><div class="lesson-list">${C.D.lessons.filter(c => c.stage === stage.id).map(row).join('')}</div></section>`).join('');
  }
  function home() {
    const D = C.D, formulaCount = D.meta.equationCount || 0;
    return `<section class="home-intro"><div class="chapter-overline">THEORY → CODE → EXPERIMENT</div><h1>读懂原理，<br>把机器人系统做出来。</h1><p class="chapter-intro">一套可以离线连续阅读的中文 ROS 2 教材。把数学推导、API 对照、详细代码、实验结果和排错放在同一章里。</p>${buttons([['#/' + (C.state.last || 'architecture'),C.state.last ? '继续上次学习 →' : '从第一个节点开始 →'],['#/courses','浏览全书目录'],['book.html','连续阅读与打印']])}<div class="learning-chain" aria-label="学习链"><span>理解模型</span><i>→</i><span>比较实现</span><i>→</i><span>动手验证</span><i>→</i><span>解释结果</span></div></section><div class="reading-stats"><div><strong>${D.lessons.length}</strong><span>教材章节</span></div><div><strong>${D.comparisons.length}</strong><span>不同写法对照</span></div><div><strong>${formulaCount}</strong><span>附解释的公式</span></div><div><strong>${D.meta.exerciseCount}</strong><span>练习与答案</span></div></div><section class="reading-section"><h2>选择一条适合当前任务的路线</h2><div class="learning-paths">${D.paths.map(path => `<section><h3>${e(path.title)}</h3><p>${t(path.description)}</p><ol>${path.lessons.filter(id => C.chapters.has(id)).map(id => `<li><a href="#/${id}">${e(C.chapters.get(id).title)}</a></li>`).join('')}</ol></section>`).join('')}<section><h3>数学与机器人理论</h3><p>用数值例子理解坐标、概率、估计、优化、运动学、动力学与控制，再进入机器人应用。</p><ol>${D.lessons.filter(c => c.id.startsWith('math-')).map(c => `<li><a href="#/${c.id}">${e(c.title)}</a></li>`).join('')}</ol></section></div></section><section class="reading-section"><h2>怎样使用这本教材</h2><div class="editorial-grid"><section><span>01 / 原理</span><h3>先写清输入、输出和假设</h3><p>公式附符号与单位，数值案例解释计算过程；区分理想模型、数值实验和真实机器人。</p></section><section><span>02 / 实现</span><h3>在同一处比较写法</h3><p>C++、Python 和不同 launch 格式共用问题背景，可用语言标签切换，也可并排检查 API 与执行顺序。</p></section><section><span>03 / 验证</span><h3>把结果变成可检查的证据</h3><p>完整代码可复制和下载；逐项说明依赖、预期现象与边界。浏览器检查、数值实验和 ROS 运行分别记录。</p></section></div></section><section class="reading-section"><h2>从知识点走向完整项目</h2>${links(['project-navigation','project-manipulation','eco-control-framework','eco-microcontrollers'])}<div class="notice">学习主线固定为 ROS 2 Jazzy / Ubuntu 24.04。其他发行版和厂商接口在相应章节标明；参考资料集中放在章末附录，学习主流程在本站完成。</div></section>`;
  }
  function resources() {
    return heading('REFERENCE NOTES','参考出处与版本记录','教材正文已经包含主要讲解。这里用于核对出处、版本与阅读范围；来源数量不代表已逐段穷尽原始资料。') + buttons([['#/library','查看本地原始资料'],['#/coverage','查看参考内容对应'],['downloads/sources.json','下载来源清单']]) + `<div class="filters"><input id="resource-query" type="search" aria-label="筛选资料关键词" placeholder="搜索 Nav2、四元数、rclcpp…"><label>分类<select id="resource-category"><option value="">全部分类</option>${[...new Set(C.D.resources.map(r => r.category))].sort().map(x => `<option>${e(x)}</option>`).join('')}</select></label><label>版本<select id="resource-version"><option value="">全部版本</option>${['Jazzy','Humble','Rolling','Lyrical'].map(x => `<option>${x}</option>`).join('')}</select></label></div><p class="filter-count" id="resource-count" role="status"></p><div id="resource-list">${resourceRows(C.D.resources)}</div>`;
  }
  function resourceRows(items) {
    return items.length ? items.map(r => `<details class="resource-row"><summary><strong>${e(r.title)}</strong><span class="tag">${e(r.version)}</span></summary><p>${t(r.description)}</p><p class="muted">${e(r.verification)}${r.versionNote ? '；' + e(r.versionNote) : ''}</p><div class="chapter-links">${links(C.D.lessons.filter(c => c.sourceIds.includes(r.id)).map(c => c.id))}</div><a class="source-link" href="${safe(r.url)}" target="_blank" rel="noopener noreferrer">原始出处 ↗</a></details>`).join('') : '<p class="empty">没有匹配资料，可减少关键词或清除版本筛选。</p>';
  }
  function coverage() {
    const data = C.D.coverage || {}, items = data.entries || [];
    return heading('COVERAGE & READING DEPTH','参考内容与教材的对应关系','这张表说明参考页面与本站章节的主题关系，并明确覆盖深度。程序识别、实际核读、正文详解是不同层次。') + notice('“详细讲解”只针对明确标注的知识范围；主题相近不代表原教程每段内容都已写入本站。导航、规则、审核记录和占位页单独标记。') + `<div class="filters"><input id="coverage-query" type="search" aria-label="筛选参考内容对应" placeholder="搜索 SLAM、控制、数学、C++…"><label>教程<select id="coverage-site"><option value="">全部教程</option>${[...new Set(items.map(x => x.site))].map(x => `<option>${e(x)}</option>`).join('')}</select></label><label>深度<select id="coverage-depth"><option value="">全部深度</option>${['详细讲解','主题概览','延伸范围','未纳入'].map(x => `<option>${x}</option>`).join('')}</select></label></div><p class="filter-count" id="coverage-count" role="status"></p><div id="coverage-list">${coverageRows(items)}</div><details class="source-note"><summary>原始目录中的缺失目标</summary><p>这些条目存在于原始导航，但对应文件未随快照提供，不按已保存教学正文统计。</p>${C.list((data.missingTargets || []).map(x => `${x.site}：${x.label || x.target} → ${x.target}`))}</details>`;
  }
  function coverageRows(items) {
    return items.length ? items.map(r => `<article class="coverage-row"><div><span class="tag">${e(r.site)}</span><span class="tag">${e(r.depth)}</span><span class="muted">${e(r.kind || '')}</span></div><h3>${e(r.title)}</h3><p>${t(r.depthReason || '')}</p><p class="muted">核读范围：${e(r.reviewLevel || '结构与主题清点')}</p>${links(r.relatedLessons)}<details><summary>原始路径与证据</summary><p><code>${e(r.file || r.localPath)}</code></p><p>${e(r.evidence?.topicBasis || '')}</p></details></article>`).join('') : '<p class="empty">没有对应条目，试试其他关键词。</p>';
  }
  function library() {
    const library = C.D.library || {}, repositories = library.repositories || [], snapshots = library.snapshots || [];
    return heading('LOCAL SOURCE LIBRARY','已保存的原文、示例与源码','教材之外的原始资料仍按各自来源和许可证独立保存。可在这里筛选仓库、版本与文档，在本地服务中阅读原始文件。') + notice('仓库源码、教程正文、配套代码和仅记录的网页入口分别登记。部分仓库含相同归档的别名；不同分支也不能视为不同课程。') + `<div class="filters"><input id="library-query" type="search" aria-label="搜索本地资料" placeholder="搜索仓库、文件、API 或教程标题…"><label>来源<select id="library-source"><option value="">全部来源</option>${repositories.map(x => `<option value="${e(x.id)}">${e(x.title)}</option>`).join('')}</select></label><label>版本<select id="library-version"><option value="">全部版本</option>${[...new Set(snapshots.map(x => x.ref))].sort().map(x => `<option>${e(x)}</option>`).join('')}</select></label></div><p class="filter-count" id="library-count" role="status"></p><div id="library-list">${libraryRows(snapshots, '')}</div>`;
  }
  function libraryRows(snapshots, query) {
    const docs = window.ROS2LocalDocuments || [];
    const q = query.toLowerCase().trim();
    const workspace = window.ROS2Environment?.workspace !== false;
    return snapshots.map(s => {
      const documents = docs.filter(d => d.snapshot === s.id && (!q || `${d.title} ${d.path}`.toLowerCase().includes(q)));
      const entry = s.entryPath || s.localPath;
      return `<details class="library-row" ${q ? 'open' : ''}><summary><strong>${e(s.title)}</strong><span class="tag">${e(s.ref)}</span></summary><p>${t(s.description || s.contentType || '原始文档与代码快照')}</p><p class="muted"><code>${e(s.repository)}</code> · 提交 <code>${e(s.commit?.slice(0,12))}</code></p><p>许可证：${e(s.licenseLabel || '以仓库许可文件及各文件声明为准')}；${e(s.runtimeValidation || '本轮未构建、未运行')}</p>${s.duplicateOf ? notice('该快照与 ' + s.duplicateOf + ' 存在相同归档，不作为独立教程计算。') : ''}${links(s.relatedLessons)}${workspace ? `<div class="button-row"><a class="button small" href="#/source/${encodeURIComponent(entry)}">在站内查看入口</a><a class="button small" href="#/source/${encodeURIComponent(s.localPath)}">浏览源码目录</a><a class="source-link" href="${e(C.localHref(entry))}" target="_blank" rel="noopener">打开原始文件 ↗</a></div>` : notice('当前为便携阅读包；原始资料需随工作区 references 目录单独复制。')}<p class="muted">${documents.length} 个匹配文档${documents.length > 45 ? '，显示前45项；可输入更具体的文件名' : ''}</p><ul class="source-file-list">${documents.slice(0,45).map(d => `<li>${workspace ? `<a href="#/source/${encodeURIComponent(d.path)}">${e(d.title)}</a>` : `<span>${e(d.title)}</span>`}<small>${e(d.format)} · ${e(d.relativePath || d.path)}</small></li>`).join('')}</ul></details>`;
    }).join('') || '<p class="empty">没有匹配的本地资料。</p>';
  }
  function source(path) {
    const filename = path.split('/').at(-1) || '原始资料';
    if(window.ROS2Environment?.workspace===false)return heading('LOCAL ORIGINAL',filename,'当前为便携阅读包。')+notice('原始参考资料和许可证需随完整工作区另外复制；本包中的教材、代码和来源索引可继续离线阅读。')+buttons([['#/library','查看原始资料索引'],['#/courses','阅读教材']]);
    return heading('LOCAL ORIGINAL',filename,'这是独立保存的上游原始文件。其许可、注释和版本保持独立，教材中的中文讲解与教学副本另行编写。') + buttons([['#/library','返回本地资料库'],[C.localHref(path),'打开原始文件']]) + `<div id="original-source" data-path="${e(path)}"><p class="notice">正在读取本地文件…</p></div>`;
  }
  async function loadSource(path) {
    if(window.ROS2Environment?.workspace===false)return;
    const node = $('original-source');
    if (!node) return;
    if (location.protocol === 'file:') {
      node.innerHTML = `<div class="notice">当前使用文件协议。可直接打开上方的原始文件；如需在本站内阅读工作区资料，请从项目根目录启动本地阅读服务：</div>${C.codeBlock({label:'本地阅读服务',language:'bash',type:'commands',code:'# 仅监听本机；教材可直接双击打开，原始资料站内阅读通过此服务提供。\npython3 ros2-learning-hub/scripts/serve_local.py'})}`; return;
    }
    try {
      const response = await fetch('/api/source?path=' + encodeURIComponent(path));
      if (!response.ok) throw new Error('无法读取这个文件，请检查资料是否已随工作区保存。');
      const data = await response.json();
      if (!$('original-source') || $('original-source').dataset.path !== path) return;
      const parent=data.parent?`<a class="button small" href="#/source/${encodeURIComponent(data.parent)}">上一级目录</a>`:'';
      node.innerHTML = data.kind==='directory'?`${parent}<p class="muted">${e(data.path)}</p><ul class="source-file-list">${data.entries.map(item=>`<li><a href="#/source/${encodeURIComponent(item.path)}">${item.directory?'▸ ':''}${e(item.name)}</a></li>`).join('')}</ul>`:`${parent}<p class="muted">${e(data.path)} · ${data.bytes} 字节</p><pre class="original-document"><code>${e(data.text)}</code></pre>`;
    } catch (error) { if (node.isConnected) node.innerHTML = notice(error.message + ' 可使用“打开原始文件”，或按 README 启动配套的本地阅读服务。'); }
  }
  function compare(id) {
    const selected = C.D.comparisons.find(x => x.id === id);
    return heading('SAME FUNCTION, DIFFERENT IMPLEMENTATIONS','同一功能，比较不同实现','先对齐输入、输出和可观察行为，再比较语言 API、生命周期、线程和工程结构。所有对照在这里直接展开。') + (selected ? buttons([['#/compare','查看全部对照']]) + C.implementation(selected) : C.D.comparisons.map(C.implementation).join(''));
  }
  function api() {
    return heading('API IN CONTEXT','API、参数与调用边界','相同的 API 对照也放在相应章节正文中。此处集中查阅输入输出、变量单位、对象寿命和错误条件。') + (C.D.apiReferences || []).map(item => C.apiTable(item) + `<div class="chapter-links">${links(item.lessons)}</div>`).join('');
  }
  function examples() {
    return heading('SOURCE & EXECUTION','完整工程，按文件阅读','先读工程说明，再按照构建、启动、观察和验收顺序实验。章节中的“完整文件”不等于已经包含所有依赖的完整机器人系统。') + notice(C.D.meta.exampleValidation) + buttons([['downloads/atlas_examples.zip','下载原创教学工程'],['downloads/foundation_examples.zip','下载基础教学工作空间'],['downloads/chapter-code.zip','下载各章完整代码']]) + (C.D.exampleFiles || []).map(f => `<details class="project-file" ${f.path === 'README.md' ? 'open' : ''}><summary>${e(f.path)}</summary>${C.codeBlock({code:f.code,language:f.language,label:f.path,type:'complete'})}</details>`).join('');
  }
  function projects() {
    return heading('INTEGRATED PRACTICE','沿着数据链完成一个机器人项目','每个项目给出准备条件、实施步骤与可观察的里程碑。导航和机械臂的完整讲解另在项目章节中连续展开。') + links(['project-navigation','project-manipulation']) + C.D.projects.map(p => `<section class="reading-section"><h2>${e(p.title)}</h2><p>${t(p.summary)}</p><h3>执行顺序与验收</h3><ol>${p.milestones.map(x => `<li>${t(x)}</li>`).join('')}</ol>${C.codeBlock({code:p.code,language:'bash',label:'起点与检查',type:'commands'})}${notice(p.note)}<details><summary>涉及的知识章节</summary>${links(p.lessons)}</details></section>`).join('');
  }
  function ecosystem() {
    return heading('THE SYSTEM MAP','从传感器到控制反馈','按系统职责理解各个软件包：数据从哪里来、进入哪个坐标系、由谁规划、由谁执行，以及如何观测结果。') + `<div class="learning-chain"><span>感知</span><i>→</i><span>估计</span><i>→</i><span>规划</span><i>→</i><span>控制</span><i>↺</i><span>反馈</span></div>` + C.D.ecosystems.map(g => `<section class="reading-section"><h2>${e(g.title)}</h2><p>${t(g.description)}</p>${links(g.lessons)}</section>`).join('');
  }
  function troubleshoot() {
    return heading('EVIDENCE BEFORE CHANGES','从症状出发，逐层定位问题','每次改变一个条件，保留检查输出，并区分构建、发现、类型、QoS、时间、TF 和硬件链路。') + C.D.issues.map(issue => `<details class="issue"><summary>${e(issue.title)}</summary><p>${t(issue.explanation)}</p>${C.list(issue.checks)}${C.codeBlock({code:issue.code,language:'bash',label:'检查命令',type:'commands'})}<p><strong>判断依据：</strong>${t(issue.expected)}</p></details>`).join('') + `<section class="reading-section"><h2>常用术语</h2><div class="glossary">${C.D.glossary.map(g => `<section><h3>${e(g.title)}</h3><small>${e(g.en)}</small><p>${t(g.description)}</p></section>`).join('')}</div></section>`;
  }
  function saved() {
    const done = C.D.lessons.filter(c => C.state.done.includes(c.id)), stars = C.D.lessons.filter(c => C.state.stars.includes(c.id));
    return heading('YOUR READING DESK','我的进度与收藏','学习记录保存在当前浏览器。可导出 JSON 备份，再导入到另一台电脑；文件协议与本地服务通常拥有不同的浏览器存储。') + notice(`已完成 ${done.length} / ${C.D.lessons.length} 章，收藏 ${stars.length} 章。`) + (C.state.last ? buttons([['#/' + C.state.last,'继续上次阅读 →']]) : '') + `<div class="button-row"><button class="button" data-export-progress>导出进度备份</button><label class="button">导入进度备份<input type="file" id="import-progress" accept="application/json,.json" hidden></label></div><section class="reading-section"><h2>收藏的章节</h2>${stars.length ? stars.map(row).join('') : '<p class="empty">在章节上方点击“收藏本章”，可以从这里快速返回。</p>'}</section><section class="reading-section"><h2>已经完成的章节</h2>${done.length ? done.map(row).join('') : '<p class="empty">完成一章后，可以在正文上方标记。</p>'}</section>`;
  }
  function downloads() {
    const items = [['book.html','单文件连续教材','包含正文、公式、静态图解、代码和答案，关闭 JavaScript 仍可阅读。'],['downloads/ros2-learning-guide.md','Markdown 全文','可编辑正文，保留公式源码、代码、推导与答案。'],['downloads/atlas_examples.zip','原创通信与实验工程','通信包、数值与真实API实验、动作故障与组件工程，附构建和运行说明。'],['downloads/foundation_examples.zip','基础教学工作空间','基础 C++/Python 包、接口和 launch 文件。'],['downloads/chapter-code.zip','章节完整代码文件','标为完整文件的代码，保留中文注释和对应章节清单。'],['downloads/sources.json','来源与覆盖 JSON','来源元数据、版本、参考页面对应及核查范围。'],['downloads/bibliography.md','来源清单 Markdown','可检索的完整出处列表。'],['downloads/local-library.json','本地原始资料索引','原始仓库与版本元数据，不包含数 GiB 的第三方源码本体。']];
    items.push(['downloads/validation-evidence.zip','验证记录与复现范围','本机检查结果、独立审查与修订证据，区分数值、协议、仿真和硬件。']);
    return heading('TAKE THE BOOK WITH YOU','离线阅读与源码下载','阅读教材不需要网络。运行 ROS、仿真或厂商项目时，仍需按章节准备匹配的软件环境和依赖。') + `<div class="download-list">${items.map(([href,title,body]) => `<a class="download-row" href="${href}" ${href.endsWith('.html') ? '' : 'download'}><div><h2>${e(title)}</h2><p>${e(body)}</p></div><span>↓</span></a>`).join('')}</div>` + notice('原始参考仓库保持独立许可证；便携阅读包包含教材和索引，原始资料须额外复制 references 目录。示例验证范围以随包记录为准。');
  }
  function about() {
    return heading('PROVENANCE & VALIDATION','版本、出处与验证范围','正文为原创综合讲解，第三方原始材料继续按其各自许可证独立保存。对应关系与来源记录帮助读者核对，而不是代替正文。') + `<section class="reading-section"><h2>怎样理解“已验证”</h2>${notice(C.D.meta.exampleValidation)}<p>结构与语法检查只能证明文件可解析；标准库实验检查数值性质；ROS 构建和互通只覆盖运行的工程；仿真与硬件需要额外证据。各章说明适用范围，不将浏览器检查当作机器人运行验证。</p>${buttons([['VALIDATION.md','本轮验证与复现说明'],['downloads/validation-evidence.zip','下载检查记录']])}<h2>版本与兼容性</h2>${C.D.versionNotes.map(n => `<h3>${e(n.topic)}</h3><p>${t(n.detail)}</p>`).join('')}<h2>来源和许可</h2><p>社区资料用于范围参考与交叉核对；未取得明确许可的正文不作为本站重新许可内容。原始文档和源码在本机独立保存。查看源码时应同时查看其根目录和文件中的许可声明。</p>${buttons([['THIRD_PARTY_NOTICES.md','第三方说明'],['LICENSE','原创教材许可证'],['#/coverage','核对内容对应范围']])}</section>`;
  }
  function filter(event, context) {
    C = context;
    if (event.target.id.startsWith('resource-')) {
      const q = $('resource-query').value.toLowerCase().trim(), category = $('resource-category').value, version = $('resource-version').value;
      const items = C.D.resources.filter(r => (!category || r.category === category) && (!version || r.version.toLowerCase().includes(version.toLowerCase())) && (!q || JSON.stringify(r).toLowerCase().includes(q)));
      $('resource-list').innerHTML = resourceRows(items); $('resource-count').textContent = `${items.length} / ${C.D.resources.length} 个来源`;
    }
    if (event.target.id.startsWith('coverage-')) {
      const q = $('coverage-query').value.toLowerCase().trim(), site = $('coverage-site').value, depth = $('coverage-depth').value;
      const items = (C.D.coverage?.entries || []).filter(r => (!site || r.site === site) && (!depth || r.depth === depth) && (!q || JSON.stringify(r).toLowerCase().includes(q)));
      $('coverage-list').innerHTML = coverageRows(items); $('coverage-count').textContent = `${items.length} 项对应，全部列出；可按教程、深度和关键词筛选`;
    }
    if (event.target.id.startsWith('library-')) {
      const q = $('library-query').value.toLowerCase().trim(), sourceId = $('library-source').value, ref = $('library-version').value, docs = window.ROS2LocalDocuments || [];
      const matchedDocuments = new Set(docs.filter(d => !q || `${d.title} ${d.path}`.toLowerCase().includes(q)).map(d => d.snapshot));
      const items = (C.D.library?.snapshots || []).filter(s => (!sourceId || s.sourceId === sourceId) && (!ref || s.ref === ref) && (!q || JSON.stringify(s).toLowerCase().includes(q) || matchedDocuments.has(s.id)));
      $('library-list').innerHTML = libraryRows(items,q); $('library-count').textContent = `${items.length} 份快照，全部列出；可选择来源、版本或关键词缩小范围`;
    }
  }
  function afterRender(view, id, context) {
    C = context;
    const identifiers = {resources:'resource-query',coverage:'coverage-query',library:'library-query'};
    if (identifiers[view]) filter({target:{id:identifiers[view]}},context);
    if (view === 'source') loadSource(id);
  }
  function chapterMarkdown(c, context) {
    C = context;
    const fence = block => { const marker = '`'.repeat(Math.max(3,1 + Math.max(0,...[...block.code.matchAll(/`+/g)].map(x => x[0].length)))); return [marker + (block.language || 'text'),block.code,marker].join('\n'); };
    // 表格必须保持为连续的行，避免全局段落分隔符把GFM表格拆开。
    const markdownTable = item => [item.columns,item.columns.map(() => '---'),...item.rows].map(row => '| ' + row.map(cell => String(cell).replaceAll('|','\\|').replaceAll('\n','<br>')).join(' | ') + ' |').join('\n');
    const out = ['# ' + c.title,c.summary,'## 学习目标',...c.goals.map(x => '- ' + x),'## 整体认识',...c.concepts];
    for (const s of c.sections || []) { out.push('## ' + s.title,...(s.paragraphs || []),...(s.bullets || []).map(x => '- ' + x)); for (const eq of s.equations || []) out.push('### ' + eq.label,'$$\n' + eq.tex + '\n$$',eq.explanation,...(eq.symbols || []).map(x => `- ${x.symbol}：${x.meaning}；${x.unit || '—'}`)); for (const table of s.tables || []) out.push('### ' + table.title,markdownTable(table),table.caption || ''); for (const b of s.codeBlocks || []) out.push('### ' + b.label,fence(b),b.explanation || ''); }
    for (const a of C.D.apiReferences || []) if (a.lessons.includes(c.id)) out.push('## ' + a.title,markdownTable(a),...(a.notes || []));
    for (const comparison of C.D.comparisons.filter(x => x.relatedLessons?.includes(c.id))) { out.push('## ' + comparison.title,comparison.question); for (const variant of comparison.variants) out.push('### ' + variant.label,fence(variant),variant.scope || ''); out.push(...comparison.notes); }
    const x = c.workedExample; if (x) out.push('## ' + x.title,x.scenario,...x.steps.map((s,i) => `${i + 1}. ${s}`),x.result);
    out.push('## 动手验证'); for (const s of c.steps) { if (typeof s === 'string') out.push(s); else { out.push('### ' + s.title,s.body || ''); if (s.code) out.push(fence(s)); } } for (const b of c.commands || []) out.push(fence(b));
    out.push('## 预期结果',...c.expected.map(x => '- ' + x),'## 常见问题',...c.pitfalls.map(x => '- ' + x),'## 练习与答案'); for (const q of [...(c.exercises || []),{question:c.exercise,answer:c.exerciseAnswer}]) out.push(q.question,'参考答案：' + q.answer);
    out.push('## 验证范围',c.validation || '以工程验证记录为准','## 出处',...c.sourceIds.map(id => C.sources.get(id)).filter(Boolean).map(s => `- [${s.title}](${s.url}) · ${s.version}`)); return out.join('\n\n') + '\n';
  }
  function render(view,id,context) {
    C = context;
    const definitions = {home:['开始学习',home],courses:['全书目录',courses],resources:['参考资料库',resources],coverage:['参考内容对应',coverage],library:['本地原始资料',library],source:['原始文件',() => source(id)],compare:['不同写法对照',() => compare(id)],api:['API 对照',api],examples:['完整示例工程',examples],projects:['综合实践项目',projects],ecosystem:['生态与工具',ecosystem],troubleshoot:['排错与术语',troubleshoot],saved:['我的进度',saved],downloads:['离线下载',downloads],about:['来源与版本',about]};
    const [title,renderer] = definitions[view] || definitions.home; return {title,html:renderer()};
  }
  window.ReaderLibrary = {render,filter,afterRender,chapterMarkdown};
})();
