/* 审查版端到端验收。使用隔离浏览器上下文，不读写用户浏览器数据。
 * 输入：本机HTTP审查入口与教材；输出：真实截图、范围明确的JSON报告。
 * 检查实际保存/导入/下载/定位和实验生命周期，不把页面验收当ROS运行证明。
 */
const {chromium}=require('../../tests/browser-runtime.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path'),{pathToFileURL}=require('node:url');
const {checkChapterOutline,checkSectionJumps}=require('./qa_outline.cjs');
const ROOT=path.resolve(__dirname,'..'),BASE=process.env.REVIEW_URL||'http://127.0.0.1:8767/design-review/';
const offlineFile=new URL(BASE).protocol==='file:';
const mascotAssets = require('../source/mascot-assets.json').assets;
const errors=[],externalRequests=[],badResponses=[],websockets=[],screenshots=[],checks=[];
const shot=async(page,file,title)=>{await images(page);await page.waitForFunction(()=>!document.getElementById('toast').classList.contains('show'));await page.screenshot({path:path.join(ROOT,'screenshots',file),fullPage:false});screenshots.push({file,title,width:page.viewportSize().width,height:page.viewportSize().height});};
function watch(page){page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith(new URL(BASE).origin+'/'))externalRequests.push(r.url());});page.on('response',r=>{if(r.status()>=400)badResponses.push({status:r.status(),url:r.url()});});page.on('websocket',ws=>websockets.push(ws.url()));}
async function visit(page,hash){await page.evaluate(h=>{location.hash=h;},hash);await page.waitForFunction(h=>location.hash===h,hash);await page.waitForTimeout(45);}
async function images(page){await page.locator('img').evaluateAll(imgs=>{for(const img of imgs)img.loading='eager';});await page.evaluate(()=>Promise.all([...document.images].map(i=>i.decode().catch(()=>{}))));assert.deepEqual(await page.locator('img').evaluateAll(imgs=>imgs.filter(i=>!i.naturalWidth).map(i=>i.src)),[]);}
async function noOverflow(page,label){const metric=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth}));assert.ok(metric.scroll<=metric.viewport+1,`${label}: ${JSON.stringify(metric)}`);}
async function checkMascotSpacing(page) {
  const [image, caption, stats] = await Promise.all(
    ['.hero-mascot', '.hero-caption', '.home-stats'].map(selector => page.locator(selector).boundingBox())
  );
  assert.ok(image && caption && stats, '首页缺少紫樱插画、图注或统计栏');
  assert.ok(image.y + image.height <= caption.y + 1, '紫樱插画覆盖了图注');
  assert.ok(caption.y + caption.height <= stats.y + 1, '图注覆盖了统计栏');
}
(async()=>{
  const browser=await chromium.launch({headless:true,args:['--no-sandbox']});let result;
  try{
    const context=await browser.newContext({viewport:{width:1440,height:1040},deviceScaleFactor:1,acceptDownloads:true,offline:offlineFile});
    const page=await context.newPage();watch(page);
    await page.goto(BASE);await page.locator('.hero-visual img').first().waitFor();await images(page);
    const lessons = await page.evaluate(() => window.ROS2Hub.lessons.map(c => ({id: c.id, title: c.title})));
    assert.equal(lessons.length, 60);
    assert.equal(await page.locator('.hero-visual img').count(), 1);
    assert.equal(await page.locator('.hero-mascot').getAttribute('src'), 'assets/mascots/hero.webp');
    assert.equal(await page.locator('#companion img').getAttribute('src'), 'assets/mascots/avatar-128.webp');
    assert.equal(await page.evaluate(() => window.NarukamiReview.stats().assets), mascotAssets.length);
    await noOverflow(page, '桌面首页');
    const layout=await page.evaluate(()=>{
      const header=document.querySelector('.site-header').getBoundingClientRect(),sidebar=document.getElementById('sidebar').getBoundingClientRect(),tree=document.getElementById('chapter-tree').getBoundingClientRect();
      return {headerBottom:header.bottom,sidebarTop:sidebar.top,sidebarBottom:sidebar.bottom,treeBottom:tree.bottom,height:innerHeight,navRows:[...document.querySelectorAll('.site-nav a')].map(a=>a.getBoundingClientRect().top),sidebarNavs:document.querySelectorAll('#sidebar nav').length};
    });
    assert.equal(layout.sidebarTop,layout.headerBottom);assert.equal(layout.sidebarBottom,layout.height);assert.ok(layout.height-layout.treeBottom<=10);assert.equal(new Set(layout.navRows).size,1);assert.equal(layout.sidebarNavs,1);
    checks.push('左栏只含学习目录并延伸到底，全部页面入口保持顶部同一行');
    await checkMascotSpacing(page);
    await shot(page, 'desktop-light.png', '桌面1440px · 樱粉浅色首页');
    await page.locator('[data-action="theme"]').first().click();
    assert.equal(await page.locator('body').getAttribute('data-theme'), 'dark');
    assert.equal(await page.locator('#companion img').getAttribute('src'), 'assets/mascots/avatar-128.webp');
    await shot(page, 'desktop-dark.png', '桌面1440px · 夜紫深色首页');
    await page.locator('[data-action="theme"]').first().click();
    await visit(page, '#/notes');
    assert.equal(await page.locator('#notes-results img').getAttribute('src'), 'assets/mascots/kmap-guide.webp');
    checks.push('首页紫樱、深浅主题头像、笔记空态与60章数据');
    const outlineAudit = [];
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({width, height: width === 1440 ? 1040 : 844});
      const chapters = [];
      for (const {id} of lessons) {
        await visit(page, '#/' + id);
        const chapter = await checkChapterOutline(page, id);
        if (width === 1440) chapter.jumps = await checkSectionJumps(page, id);
        chapters.push(chapter);
      }
      const numbered = chapters.reduce((sum, chapter) => sum + chapter.numbered, 0);
      const childEntries = chapters.reduce((sum, chapter) => sum + chapter.childEntries, 0);
      const numberedChildren = chapters.reduce((sum, chapter) => sum + chapter.numberedChildren, 0);
      const entries = chapters.reduce((sum, chapter) => sum + chapter.entries, 0);
      const paragraphs = chapters.reduce((sum, chapter) => sum + chapter.paragraphs, 0);
      const jumps = chapters.reduce((sum, chapter) => sum + (chapter.jumps || 0), 0);
      outlineAudit.push({width, numbered, childEntries, numberedChildren, entries, paragraphs, jumps, chapters});
      console.log(`目录 ${width}px · ${chapters.length}章 · ${numbered}主小节 · ${childEntries}下级标题 · ${entries}条目 · ${jumps}项逐条定位`);
    }
    checks.push('1440/390/320px 全60章的阶段、章名、二三级标题、编号、主小节各段正文和双目录逐条匹配，桌面实际点击全部锚点');
    await page.setViewportSize({width:1440,height:1040});
    await visit(page, '#/math-control/section/part-5');
    const longTitle = page.locator('.tree-section-list a[data-section-id=part-5]');
    const controlNumber = lessons.findIndex(lesson => lesson.id === 'math-control') + 1;
    assert.equal(await longTitle.locator('.outline-index').textContent(), `${controlNumber}.6`);
    assert.equal(await page.locator('#part-5 h2').getAttribute('data-section-number'), `${controlNumber}.6`);
    assert.equal(await page.locator('.tree-section-list [data-outline-group=study] a').first().getAttribute('data-section-id'), 'worked-example');
    const titleLines = await longTitle.locator('.outline-label').evaluate(label => {
      const range = document.createRange();
      range.selectNodeContents(label);
      return [...range.getClientRects()].map(rect => rect.left);
    });
    assert.ok(titleLines.length > 1 && titleLines.every(left => Math.abs(left - titleLines[0]) <= 1));
    const headingGap = await page.evaluate(() => document.getElementById('part-5').getBoundingClientRect().top - document.querySelector('.topbar').getBoundingClientRect().bottom);
    assert.ok(headingGap >= 12 && headingGap <= 36, `标题与顶栏间距 ${headingGap}px`);
    await shot(page, 'chapter-light.png', '控制章的小节编号与长标题换行');
    checks.push('控制章的目录与正文编号一致，长标题续行对齐，配套内容单列，定位留白正常');
    await visit(page, '#/workspace/section/writing-compare-build');
    await shot(page, 'chapter-workspace-outline.png', '工作空间 · 实现对照与代码');
    await visit(page, '#/math-estimation/section/part-1');
    await shot(page, 'chapter-estimation-outline.png', '状态估计 · 小节编号与公式');
    await visit(page, '#/eco-model-rviz/section/part-9?theme=dark');
    await page.locator('.tree-chapter').evaluate(chapter => {
      const tree = chapter.closest('#chapter-tree');
      tree.scrollTop += chapter.getBoundingClientRect().top - tree.getBoundingClientRect().top;
    });
    assert.equal(await page.locator('#part-9-sub-1').getAttribute('data-section-number'), '33.10.1');
    await shot(page, 'chapter-model-outline.png', '机器人模型 · 深色、双位数小节与下一级实测表');
    await page.setViewportSize({width:390,height:844});
    await visit(page, '#/actions/section/api-details?theme=light');
    await page.locator('#toc-trigger').click();
    assert.equal(await page.locator('#toc-list [aria-current=location]').getAttribute('data-section-id'), 'api-details');
    const apiLink = page.locator('#toc-list .outline-children a[data-section-id=api-details-sub-1]');
    await apiLink.scrollIntoViewIfNeeded();
    await shot(page, 'chapter-action-mobile-outline.png', '390px · 动作章目录中的 API 子条目');
    await page.setViewportSize({width:320,height:844});
    await apiLink.press('Enter');
    await page.locator('#api-details-sub-1.matched-section').waitFor();
    assert.equal(await page.locator('#toc-dialog').evaluate(dialog => dialog.open), false);
    assert.equal(await page.locator('.tree-section-list [aria-current=location]').getAttribute('data-section-id'), 'api-details-sub-1');
    const apiLayout = await page.locator('#api-details').evaluate(section => {
      const head = section.querySelector('h2').getBoundingClientRect();
      const subhead = section.querySelector('h3').getBoundingClientRect();
      const table = section.querySelector('.table-wrap');
      return {
        headingsVisible: head.top >= document.querySelector('.topbar').getBoundingClientRect().bottom && subhead.bottom < innerHeight,
        tableScrolls: table.scrollWidth > table.clientWidth,
        headerFits: table.querySelector('thead').getBoundingClientRect().height <= 96,
      };
    });
    assert.deepEqual(apiLayout, {headingsVisible: true, tableScrolls: true, headerFits: true});
    await noOverflow(page, '320px 的 API 子标题与表格');
    await shot(page, 'chapter-action-mobile-reading.png', '320px · 动作 API 子条目定位到正文');
    checks.push('手机用回车从目录定位 API 子条目，320px 上级标题和子标题同时可见，表格独立横向滚动');
    await page.setViewportSize({width:1440,height:1040});
    await visit(page, '#/eco-nav2-stack/section/part-8-sub-2?theme=light');
    assert.equal(await page.locator('.tree-section-list [aria-current=location] .outline-index').textContent(), '45.9.2');
    await page.locator('#fig-nav2-costmap-planning img').evaluate(img=>{img.loading='eager';return img.decode();});
    await shot(page, 'chapter-nav2-planning.png', '第 45 章 · 实测代价地图与同目标绕行');
    await visit(page, '#/eco-slam-mapping/section/part-9-sub-2?theme=light');
    assert.equal(await page.locator('.tree-section-list [aria-current=location] .outline-index').textContent(), '41.10.2');
    await page.locator('#fig-slam-mapping-trajectory img').evaluate(img=>{img.loading='eager';return img.decode();});
    await shot(page, 'chapter-slam-mapping.png', '第 41 章 · 同一圈扫描的占据图、轨迹与误差');
    await visit(page,'#/tf2');await page.locator('.chapter-header').waitFor();
    const completionButton = page.locator('[data-study="done"]');
    await completionButton.click();
    assert.equal(await page.locator('#toast img').getAttribute('src'), 'assets/mascots/complete.webp');
    await completionButton.click();
    const subsectionTree = page.locator('.tree-chapter .tree-subtree[data-chapter=tf2]');
    const subsectionLinks = subsectionTree.locator('.tree-section-list a');
    assert.equal(await subsectionTree.evaluate(node => node.open), true);
    assert.ok(await subsectionLinks.count() > 5);
    await subsectionTree.locator('summary').click();
    assert.equal(await subsectionTree.evaluate(node => node.open), false);
    assert.equal(await subsectionLinks.first().isVisible(), false);
    await subsectionTree.locator('summary').click();
    const sidebarLink = subsectionTree.locator('a[data-section-id=part-1]');
    await sidebarLink.click();
    await page.waitForFunction(() => document.querySelector('.tree-section-list [aria-current=location]')?.dataset.sectionId === 'part-1');
    assert.match(page.url(), /section\/part-1$/);
    assert.ok(await page.evaluate(() => scrollY) > 0);
    await page.locator('#toc-trigger').click();
    const linkTargets = links => links.map(link => link.getAttribute('href'));
    assert.deepEqual(await page.locator('#toc-list a').evaluateAll(linkTargets), await subsectionLinks.evaluateAll(linkTargets));
    assert.equal(await page.locator('#toc-list [aria-current=location]').getAttribute('data-section-id'), 'part-1');
    await page.locator('#toc-list a[data-section-id=part-0]').click();
    await page.waitForFunction(() => document.querySelector('.tree-section-list [aria-current=location]')?.dataset.sectionId === 'part-0');
    checks.push('当前章节子目录展开与折叠、选中状态、小节跳转及顶部目录同源');
    await visit(page,'#/home');await page.keyboard.press('Control+k');await page.locator('#search-input').fill('坐标');assert.ok(await page.locator('.search-result mark').count()>0);await shot(page,'search-results.png','搜索命中与片段高亮');await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');await page.waitForTimeout(80);assert.equal(await page.locator('#search-dialog').evaluate(d=>d.open),false);assert.ok(await page.locator('.chapter-header').count()>0);checks.push('全文搜索高亮、方向键选择和回车定位');
    await page.locator('[data-action="search"]').first().click();await page.locator('#search-input').fill('绝对不存在的词xyz');assert.equal(await page.locator('.search-result').count(),0);assert.equal(await page.locator('#search-results img').getAttribute('src'),'assets/mascots/404.webp');await shot(page,'search-empty.png','搜索空态');await page.keyboard.press('Escape');assert.equal(await page.locator('#search-dialog').evaluate(d=>d.open),false);
    await visit(page,'#/tf2');
    const originalParagraph=await page.locator('#overview p').first().textContent();
    const beforeLayout=await page.locator('#overview p').first().evaluate(el=>({font:getComputedStyle(el).fontSize,line:getComputedStyle(el).lineHeight,tables:document.querySelectorAll('.table-wrap').length,codes:document.querySelectorAll('.code-example').length,exercises:document.querySelectorAll('.exercise-item').length}));
    await page.locator('#view-mode').selectOption('edit');assert.equal(await page.locator('#chapter-editor').count(),0);assert.ok(await page.locator('#overview p[contenteditable=true]').count()>0);
    const editedParagraph='本地草稿验证词：直接在现有排版修改中文，同一个点可有不同坐标表达。';
    const richParagraph=page.locator('#overview p').first();await richParagraph.fill(editedParagraph);
    await page.waitForFunction(()=>document.getElementById('draft-status').textContent.startsWith('已暂存到浏览器'));assert.ok((await page.locator('#draft-status').textContent()).startsWith('已暂存到浏览器'));
    const afterLayout=await richParagraph.evaluate(el=>({font:getComputedStyle(el).fontSize,line:getComputedStyle(el).lineHeight,tables:document.querySelectorAll('.table-wrap').length,codes:document.querySelectorAll('.code-example').length,exercises:document.querySelectorAll('.exercise-item').length}));assert.deepEqual(afterLayout,beforeLayout);
    await richParagraph.evaluate(el=>{const range=document.createRange();range.setStart(el.firstChild,0);range.setEnd(el.firstChild,7);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);});
    await page.locator('[data-visual-format=strong]').click();assert.equal(await richParagraph.locator('strong').textContent(),'本地草稿验证词');
    await page.locator('[data-action=visual-undo]').click();assert.equal(await richParagraph.locator('strong').count(),0);await page.locator('[data-action=visual-redo]').click();assert.equal(await richParagraph.locator('strong').count(),1);
    const cell=page.locator('.table-wrap td').first(),originalCell=await cell.textContent();await cell.fill(originalCell+'（直接编辑单元格）');
    const code=page.locator('.code-example pre code').first(),originalCode=await code.textContent();await code.fill(originalCode+'\n# 直观编辑代码的中文注释');
    const heading=page.locator('#overview h2');await heading.fill('建立整体认识与自己的理解');
    const chapterTitle = 'TF 坐标变换与自己的理解';
    const apiTitle = 'tf2 API 的输入与返回坐标';
    await page.locator('.chapter-header h1').fill(chapterTitle);
    await page.locator('#api-details-sub-1').fill(apiTitle);
    await page.waitForFunction(()=>document.getElementById('draft-status').textContent.startsWith('已暂存到浏览器'));
    assert.equal(await subsectionLinks.first().locator('.outline-label').textContent(), '建立整体认识与自己的理解');
    assert.equal(await page.locator('.tree-link[aria-current=page] .tree-title').textContent(), chapterTitle);
    assert.equal(await page.locator('#breadcrumb > span:last-child').getAttribute('title'), chapterTitle);
    assert.equal(await page.locator('.tree-section-list [data-section-id=api-details-sub-1] .outline-label').textContent(), apiTitle);
    await page.locator('#toc-trigger').click();
    assert.equal(await page.locator('#toc-list a[data-section-id=overview] .outline-label').textContent(), '建立整体认识与自己的理解');
    assert.equal(await page.locator('#toc-list a[data-section-id=api-details-sub-1] .outline-label').textContent(), apiTitle);
    await page.keyboard.press('Escape');
    const editorDocument = await page.locator('#visual-document').elementHandle();
    await page.locator('.tree-section-list a[data-section-id=part-0]').click();
    await page.locator('#part-0.matched-section').waitFor();
    assert.equal(await editorDocument.evaluate(node => node.isConnected), true);
    assert.equal(await page.locator('#view-mode').inputValue(), 'edit');
    assert.ok(await page.evaluate(() => document.getElementById('part-0').getBoundingClientRect().top >= document.querySelector('.visual-editor-bar').getBoundingClientRect().bottom));
    await page.evaluate(()=>scrollTo({top:0,behavior:'instant'}));await heading.focus();await shot(page,'editor-desktop.png','1440px原排版直接编辑');
    await page.locator('#view-mode').selectOption('read');assert.equal(await page.locator('#overview p').first().textContent(),editedParagraph);assert.equal(await page.locator('#overview p strong').count(),1);assert.ok((await page.locator('.table-wrap td').first().textContent()).includes('直接编辑单元格'));assert.ok((await page.locator('.code-example pre code').first().textContent()).endsWith('直观编辑代码的中文注释'));assert.equal(await page.locator('#overview h2 .section-anchor').count(),1);
    await page.reload();await page.locator('.draft-notice').waitFor();assert.equal(await page.locator('#overview p').first().textContent(),editedParagraph);assert.equal(await page.locator('#view-mode').inputValue(),'read');
    assert.equal(await page.locator('.tree-link[aria-current=page] .tree-title').textContent(), chapterTitle);
    assert.equal(await page.locator('#api-details-sub-1').textContent(), apiTitle);
    await page.locator('#view-mode').selectOption('edit');await page.locator('[data-action=open-source]').click();const editedChapter=await page.locator('#chapter-source').inputValue();assert.ok(editedChapter.includes('直接编辑单元格'));assert.ok(editedChapter.includes('直观编辑代码的中文注释'));await page.keyboard.press('Escape');assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem(window.NarukamiReview.storageKey)).drafts.tf2),undefined);
    await page.locator('[data-action=restore-chapter]').click();assert.equal(await page.locator('#overview p').first().textContent(),originalParagraph);await page.locator('[data-action=undo-restore]').click();assert.equal(await page.locator('#overview p').first().textContent(),editedParagraph);
    const draftDownload=page.waitForEvent('download');await page.locator('[data-action=export-chapter]').first().click();const exported=await fs.readFile(await (await draftDownload).path(),'utf8');assert.ok(exported.includes('直接编辑单元格'));assert.ok(exported.includes('直观编辑代码的中文注释'));assert.match(exported,/\|[^\n]+\|\n\| ---/);
    await page.locator('#overview p').first().fill(editedParagraph+'尚未等到自动保存即离开。');await visit(page,'#/actions');assert.equal(await page.locator('#view-mode').inputValue(),'edit');assert.ok(!(await page.locator('#visual-document').textContent()).includes('本地草稿验证词'));await visit(page,'#/tf2');assert.ok((await page.locator('#overview p').first().textContent()).includes('尚未等到自动保存即离开。'));
    await page.locator('#overview p').first().fill(editedParagraph);await page.waitForFunction(()=>document.getElementById('draft-status').textContent.startsWith('已暂存到浏览器'));
    await page.locator('.header-search').click();await page.locator('#search-input').fill('本地草稿验证词');assert.ok(await page.locator('.search-result').count()>0);await page.locator('.search-result').first().click();await page.waitForTimeout(100);assert.equal(await page.locator('#view-mode').inputValue(),'read');
    checks.push('原位编辑中文段落、章名、二三级标题、表格与代码，双目录随标题更新；保留排版，验证撤销重做、自动保存、刷新恢复和真实导出');
    await visit(page,'#/tf2?note=1');await page.locator('#note-editor').waitFor();const note='## 我对坐标变换的理解\n\n- 先旋转，再平移。\n- 点的坐标包含平移；方向只旋转。\n\n`p_B = R · p_L + t`\n\n下一次实验：旋转 90°，检查两个坐标系中的同一个点。';await page.locator('#note-editor').fill(note);await page.waitForFunction(()=>document.getElementById('note-status').textContent.startsWith('已保存'));await shot(page,'note-drawer.png','章节笔记编辑抽屉');await page.locator('[data-note-mode="preview"]').click();assert.equal(await page.locator('#note-preview h3').textContent(),'我对坐标变换的理解');await page.keyboard.press('Escape');await page.reload();await page.locator('#note-editor').waitFor();assert.equal(await page.locator('#note-editor').inputValue(),note);await page.keyboard.press('Escape');checks.push('笔记自动保存、Markdown预览、刷新恢复');
    await visit(page,'#/notes');const backupEvent=page.waitForEvent('download');await page.locator('[data-action="export-backup"]').click();const backup=await backupEvent,backupData=JSON.parse(await fs.readFile(await backup.path(),'utf8'));assert.equal(backupData.notes.tf2.text,note);assert.ok(Object.keys(backupData.visualDrafts.tf2.fields).length>=4);const originalFormal=await page.evaluate(()=>localStorage.getItem('ros2-atlas-v1'));
    await page.locator('#backup-input').setInputFiles({name:'old-progress.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({format:'ros2-atlas-v1',done:[lessons[0].id],stars:['tf2'],last:'tf2',theme:'light'}))});await page.waitForTimeout(100);assert.ok(await page.evaluate(()=>JSON.parse(localStorage.getItem(window.NarukamiReview.storageKey)).done.length>0));assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem(window.NarukamiReview.storageKey)).notes.tf2.text),note);assert.equal(await page.evaluate(()=>localStorage.getItem('ros2-atlas-v1')),originalFormal);checks.push('真实JSON备份下载、旧版进度合并、正式存储隔离');
    await page.locator('#backup-input').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('{invalid')});await page.waitForTimeout(60);assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem(window.NarukamiReview.storageKey)).notes.tf2.text),note);
    await page.locator('#backup-input').setInputFiles({name:'current-backup.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(backupData))});await page.waitForTimeout(100);assert.deepEqual(await page.evaluate(()=>JSON.parse(localStorage.getItem(window.NarukamiReview.storageKey)).visualDrafts.tf2.fields),backupData.visualDrafts.tf2.fields);checks.push('实际备份含正文草稿，旧版与新版导入均保留草稿及笔记');
    await visit(page,'#/tf2/figure/tf2-transform?open=1');await page.locator('[data-lab="tf2-transform"] .lab-body').waitFor();await page.locator('[data-preset="quarter"]').click();assert.equal(await page.locator('[data-result]').textContent(),'[0.000, 1.000] m');await page.locator('[data-param="x"]').evaluate(el=>{el.value='0.5';el.dispatchEvent(new Event('input',{bubbles:true}));});assert.equal(await page.locator('[data-result]').textContent(),'[0.500, 1.000] m');await page.locator('[data-lab-wide]').click();assert.equal(await page.locator('#wide-dialog').evaluate(d=>d.open),true);await page.locator('#wide-dialog [data-param="x"]').evaluate(el=>{el.value='1';el.dispatchEvent(new Event('input',{bubbles:true}));});assert.equal(await page.locator('#wide-dialog [data-result]').textContent(),'[1.000, 1.000] m');await shot(page,'lab-wide.png','坐标实验宽屏');await page.keyboard.press('Escape');assert.equal(await page.locator('.lab-card [data-result]').textContent(),'[1.000, 1.000] m');await page.locator('.lab-summary').click();await page.waitForTimeout(50);assert.equal(await page.evaluate(()=>window.NarukamiReview.stats().mounted),0);await page.locator('.lab-summary').click();await page.locator('[data-result]').waitFor();assert.equal(await page.locator('[data-result]').textContent(),'[1.000, 1.000] m');checks.push('TF数值、宽屏可交互、状态保留与折叠释放');
    await page.locator('#view-mode').selectOption('edit');await page.locator('[data-result]').waitFor();assert.equal(await page.locator('[data-result]').textContent(),'[1.000, 1.000] m');await page.locator('#view-mode').selectOption('read');await page.locator('[data-result]').waitFor();assert.equal(await page.locator('[data-result]').textContent(),'[1.000, 1.000] m');checks.push('原排版编辑保留可交互实验，模式切换后数值状态连续');
    await visit(page,'#/eco-model-rviz/figure/robot-model?open=1');await page.locator('[data-lab="robot-model"] .lab-body').waitFor();const originalPose=await page.locator('[data-result]').textContent();await page.locator('[data-view="top"]').click();assert.equal(await page.locator('[data-result]').textContent(),originalPose);await page.locator('[data-param="q1"]').evaluate(el=>{el.value='60';el.dispatchEvent(new Event('input',{bubbles:true}));});assert.notEqual(await page.locator('[data-result]').textContent(),originalPose);await page.locator('[data-frames]').uncheck();await shot(page,'model-lab.png','机器人几何模型');await visit(page,'#/home');assert.equal(await page.evaluate(()=>window.NarukamiReview.stats().mounted),0);checks.push('模型视角与关节变化区分、坐标轴与退出释放');
    await visit(page, '#/gallery');
    assert.equal(await page.locator('.asset-card').count(), mascotAssets.length);
    await shot(page, 'gallery.png', '紫樱素材画廊');
    await page.locator('#asset-category').selectOption('avatar');
    assert.equal(await page.locator('.asset-card').count(), 1);
    await page.locator('#asset-placement').selectOption('首页');
    assert.equal(await page.locator('.asset-card').count(), 0);
    await page.locator('#asset-category').selectOption('');
    await page.locator('[data-asset="mascot-hero"]').click();
    assert.equal(await page.locator('#asset-dialog').evaluate(d => d.open), true);
    assert.equal(await page.locator('.asset-original img').getAttribute('src'), 'assets/mascots/hero.webp');
    assert.ok((await page.locator('.asset-metadata').textContent()).includes('SHA256'));
    assert.equal(await page.locator('.crop-previews img').count(), 2);
    await page.keyboard.press('Escape');
    checks.push('紫樱图库加载、类别与用途筛选、出处及裁切详情');
    await visit(page,'#/eco-model-rviz');const chapterDownload=page.waitForEvent('download');await page.locator('[data-action="export-chapter"]').click();const chapterFile=await chapterDownload,markdown=await fs.readFile(await chapterFile.path(),'utf8');assert.ok(markdown.includes('robot.urdf.xacro'));assert.match(markdown,/\|[^\n]+\|\n\| ---/);checks.push('真实单章Markdown下载与连续表格');
    const firstDocument=await page.evaluate(()=>window.ROS2LocalDocuments[0]);await visit(page,'#/resources?query='+encodeURIComponent(firstDocument.title)+'&metadata=1');assert.equal(await page.locator('#document-metadata').evaluate(d=>d.open),true);assert.ok((await page.locator('#resource-document-results').textContent()).includes(firstDocument.path));checks.push('原文元数据搜索结果有实际标题、版本与路径落点');
    const routes=['#/home','#/courses','#/visuals','#/notes','#/saved','#/resources','#/gallery','#/review','#/api','#/compare',...lessons.map(c=>'#/'+c.id)];let mobileRoutes=0;
    for(const width of [390,320]){
      await page.setViewportSize({width,height:844});
      for(const hash of routes){await visit(page,hash);await noOverflow(page,width+'px '+hash);mobileRoutes++;}
      await visit(page,'#/home');await images(page);await checkMascotSpacing(page);await shot(page,width===390?'mobile-390.png':'mobile-320.png',width+'px手机首页');
      await page.locator('#menu-button').click();assert.equal(await page.locator('body').evaluate(b=>b.classList.contains('menu-open')),true);await page.keyboard.press('Escape');assert.equal(await page.locator('#menu-button').getAttribute('aria-expanded'),'false');
      await visit(page, '#/math-control');
      await page.locator('#menu-button').click();
      assert.ok(await page.locator('#chapter-tree').evaluate(tree => tree.scrollWidth <= tree.clientWidth + 1));
      await page.locator('.tree-section-list a[data-section-id=part-5]').click();
      await page.locator('#part-5.matched-section').waitFor();
      assert.equal(await page.locator('#menu-button').getAttribute('aria-expanded'), 'false');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'reading');
    }
    checks.push('390/320px全部70路由无整页溢出，手机菜单、Esc及小节跳转');
    await page.setViewportSize({width:390,height:844});await visit(page,'#/home?theme=dark');await images(page);await checkMascotSpacing(page);await shot(page,'mobile-dark.png','390px深色首页');await visit(page,'#/tf2?note=1');await shot(page,'mobile-note.png','390px章节笔记');await page.keyboard.press('Escape');
    let editorRoutes=0;
    for(const width of [390,320]){
      await page.setViewportSize({width,height:844});await visit(page,'#/tf2');await page.locator('#view-mode').selectOption('edit');
      for(const lesson of lessons){await visit(page,'#/'+lesson.id);await noOverflow(page,width+'px直观编辑 '+lesson.id);assert.ok(await page.locator('#visual-document [contenteditable]').count()>0);editorRoutes++;}
      await visit(page,'#/tf2');await noOverflow(page,width+'px正文编辑');await page.locator('#overview p').first().fill(editedParagraph+width+'px手机直接编辑恢复。');await page.waitForFunction(()=>document.getElementById('draft-status').textContent.startsWith('已暂存到浏览器'));
      if(width===390){await page.locator('#overview p').first().focus();await shot(page,'editor-mobile.png','390px深色原排版编辑');}
      await page.locator('#view-mode').selectOption('read');assert.ok((await page.locator('#overview p').first().textContent()).includes('手机直接编辑恢复。'));
      assert.equal(await page.locator('#sidebar').evaluate(el=>el.inert),true);await page.waitForTimeout(220);assert.ok((await page.locator('#sidebar').boundingBox()).x<0);
    }
    checks.push('390/320px另120条原排版编辑路由无整页溢出，手机直接修改与目录焦点隔离');
    await context.close();
    const offline=await browser.newContext({viewport:{width:390,height:844},offline:true});const filePage=await offline.newPage();watch(filePage);await filePage.goto(pathToFileURL(path.join(ROOT,'index.html')).href+'#/tf2/figure/tf2-transform?open=1');await filePage.locator('.lab-body').waitFor();assert.equal(await filePage.evaluate(()=>window.NarukamiReview.stats().chapters),60);await filePage.locator('.header-search').click();await filePage.locator('#search-input').fill('tf2');assert.ok(await filePage.locator('.search-result').count()>0);await filePage.keyboard.press('Escape');await filePage.locator('#note-trigger').click();await filePage.locator('#note-editor').fill('断网文件协议笔记');await filePage.waitForTimeout(500);await filePage.reload();await filePage.locator('#note-trigger').click();assert.equal(await filePage.locator('#note-editor').inputValue(),'断网文件协议笔记');await filePage.keyboard.press('Escape');await filePage.locator('#view-mode').selectOption('edit');await filePage.locator('#overview p').first().fill('本地文件排版草稿可恢复。');await filePage.locator('#view-mode').selectOption('read');await filePage.reload();assert.ok((await filePage.locator('#overview p').first().textContent()).includes('本地文件排版草稿可恢复。'));await offline.close();checks.push('file://完全断网阅读、搜索、实验、笔记与正文草稿恢复');
    const limited=await browser.newContext({viewport:{width:1440,height:1040},acceptDownloads:true});
    await limited.addInitScript(()=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(key==='ros2-narukami-design-review-v1')throw new DOMException('模拟容量不足','QuotaExceededError');return original.call(this,key,value);};});
    const limitedPage=await limited.newPage();watch(limitedPage);await limitedPage.goto(BASE+'#/tf2');await limitedPage.locator('#view-mode').selectOption('edit');const unsaved='此内容尚未持久保存，仍可导出。';await limitedPage.locator('#overview p').first().fill(unsaved);await limitedPage.waitForFunction(()=>document.getElementById('draft-status').textContent.includes('浏览器暂存失败'));
    const unsavedEvent=limitedPage.waitForEvent('download');await limitedPage.locator('[data-action="export-chapter"]').first().click();assert.ok((await fs.readFile(await (await unsavedEvent).path(),'utf8')).includes(unsaved));await limitedPage.locator('#view-mode').selectOption('read');assert.ok((await limitedPage.locator('.draft-notice').textContent()).includes('尚未持久保存'));await limited.close();checks.push('存储容量不足时明确标注未持久保存，仍可真实导出当前正文');
    const boundary=await browser.newContext({viewport:{width:1440,height:1040}});
    const unsafe=JSON.parse(JSON.stringify(backupData));const paragraphKey=Object.keys(unsafe.visualDrafts.tf2.fields).find(key=>key.endsWith('-p'));
    unsafe.visualDrafts.tf2.fields[paragraphKey]='<strong onclick="window.BAD=1">安全格式</strong><script>window.BAD=2</script><img src="https://example.org/should-not-load.png"><svg onload="window.BAD=3"></svg><a href="javascript:window.BAD=4">链接文字</a>';
    await boundary.addInitScript(data=>localStorage.setItem('ros2-narukami-design-review-v1',JSON.stringify(data)),unsafe);
    const boundaryPage=await boundary.newPage();watch(boundaryPage);await boundaryPage.goto(BASE+'#/tf2');const cleanField=boundaryPage.locator(`[data-edit-key="${paragraphKey}"]`);assert.equal(await cleanField.locator('strong').textContent(),'安全格式');assert.equal(await cleanField.locator('script,img,svg,[onclick],a[href^="javascript:"]').count(),0);assert.equal(await boundaryPage.evaluate(()=>window.BAD),undefined);
    await boundaryPage.locator('#view-mode').selectOption('edit');
    await cleanField.evaluate(el=>{el.focus();const range=document.createRange();range.selectNodeContents(el);range.collapse(false);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);const data=new DataTransfer();data.setData('text/html','<img src="https://example.org/paste.png" onerror="window.BAD=5">');data.setData('text/plain',' 粘贴的<标签>中文');el.dispatchEvent(new ClipboardEvent('paste',{bubbles:true,cancelable:true,clipboardData:data}));});
    assert.equal(await cleanField.locator('img').count(),0);assert.ok((await cleanField.textContent()).includes('粘贴的<标签>中文'));
    await cleanField.evaluate(el=>{el.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));el.textContent='中文输入法完成后的整段内容';el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertCompositionText',isComposing:true}));el.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'整段内容'}));});
    await boundaryPage.waitForFunction(()=>document.getElementById('draft-status').textContent.startsWith('已暂存到浏览器'));await boundaryPage.locator('#view-mode').selectOption('read');assert.equal(await cleanField.textContent(),'中文输入法完成后的整段内容');checks.push('排版草稿清理脚本、事件、外部图片和危险链接；粘贴仅文本，中文输入法合成结束后保存');
    await boundaryPage.locator('#view-mode').selectOption('edit');
    await boundaryPage.locator('[data-action=open-source]').click();
    await boundaryPage.locator('#chapter-source').fill([
      '# 源码兼容章节', '<!-- section:part-0 -->', '## 草稿小节', '<!-- section:draft-child -->',
      '### 草稿子节', '原有Markdown草稿仍可恢复并继续直观编辑。',
      '<!-- section:draft-detail -->', '#### 草稿细项', '四级标题位于草稿子节内。',
      '## 新增小节', '新增小节继续按章编号。',
    ].join('\n\n'));
    await boundaryPage.locator('[data-action=apply-source]').click();
    assert.equal(await boundaryPage.locator('#visual-document h1').textContent(), '源码兼容章节');
    await boundaryPage.locator('#visual-document p[contenteditable]').first().fill('源码应用后继续直接编辑正文。');
    await boundaryPage.locator('#view-mode').selectOption('read');
    assert.ok((await boundaryPage.locator('.draft-content').textContent()).includes('源码应用后继续直接编辑正文。'));
    const draftLink = boundaryPage.locator('.tree-section-list a[data-section-id=draft-child]');
    const tfNumber = lessons.findIndex(lesson => lesson.id === 'tf2') + 1;
    assert.equal(await draftLink.getAttribute('href'), '#/tf2/section/draft-child');
    assert.equal(await draftLink.locator('.outline-index').textContent(), `${tfNumber}.1.1`);
    const detailLink = boundaryPage.locator('.tree-section-list li:has(> a[data-section-id=draft-child]) > .outline-children a');
    assert.equal(await detailLink.locator('.outline-index').textContent(), `${tfNumber}.1.1.1`);
    assert.equal(await boundaryPage.getByRole('heading',{name:'新增小节'}).getAttribute('data-section-number'),`${tfNumber}.2`);
    await detailLink.click();
    await boundaryPage.locator('#draft-detail.matched-section').waitFor();
    checks.push('可选源码应用后回到正文，二至四级标题保留归属与锚点，新增小节连续编号并可继续原位编辑');
    await boundary.close();
    assert.deepEqual(errors,[]);assert.deepEqual(externalRequests,[]);assert.deepEqual(badResponses,[]);assert.deepEqual(websockets,[]);
    result={passed:true,checkedAt:'2026-11-07',scope:'独立网页设计样稿',offlineFile,chapters:60,assets:mascotAssets.length,mobileRoutes,editorRoutes,outlineAudit,screenshots,checks,errors,externalRequests,badResponses,websockets};
  }catch(error){result={passed:false,error:error.stack,checks,screenshots,errors,externalRequests,badResponses,websockets};throw error;}finally{await fs.writeFile(path.join(ROOT,'validation/browser-report.json'),JSON.stringify(result,null,2)+'\n');await browser.close();}
  console.log(JSON.stringify({passed:result.passed,checks:checks.length,mobileRoutes:result.mobileRoutes,editorRoutes:result.editorRoutes,screenshots:screenshots.length}));
})().catch(error=>{console.error(error);process.exitCode=1;});
