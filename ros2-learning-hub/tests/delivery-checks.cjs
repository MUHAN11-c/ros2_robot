/* 验证从最终ZIP解出的便携包，而非只测试工作区中的dist。 */
const {chromium}=require('./browser-runtime.cjs');
const assert=require('node:assert/strict'),path=require('node:path');
(async()=>{
  assert.ok(process.env.PORTABLE_SITE_DIR,'先解压交付ZIP，再用PORTABLE_SITE_DIR指定其中ros2-learning-hub目录');
  const root=path.resolve(process.env.PORTABLE_SITE_DIR),browser=await chromium.launch({headless:true});
  const errors=[],external=[];
  try{
    const context=await browser.newContext({offline:true,viewport:{width:390,height:844},reducedMotion:'reduce'});
    const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))external.push(r.url())});
    await page.goto('file://'+path.join(root,'index.html')+'#/library');await page.locator('.library-row').first().waitFor();
    assert.equal(await page.locator('a[href^="#/source/"]').count(),0,'便携包不提供未复制原文的活跃入口');
    await page.goto('file://'+path.join(root,'index.html')+'#/source/test');
    assert.match(await page.locator('#reading').innerText(),/另外复制/);
    await page.goto('file://'+path.join(root,'index.html')+'#/pubsub');
    const expected=await page.locator('.code-example pre').first().innerText();
    await page.locator('[data-copy]').first().click();
    await page.waitForFunction(()=>document.querySelector('#copy-dialog').open||document.querySelector('#toast').classList.contains('show'));
    if(await page.locator('#copy-dialog[open]').count())assert.equal(await page.locator('#copy-text').inputValue(),expected);
    else assert.match(await page.locator('#toast').innerText(),/代码已复制/);
    await page.goto('file://'+path.join(root,'index.html')+'#/eco-gazebo-simulation');
    assert.equal(await page.locator('.local-source-link').count(),0,'便携包禁用章末本地原文入口');
    await page.locator('#fig-gazebo-sensor-captures img').evaluate(img=>{img.loading='eager';return img.decode();});
    await page.goto('file://'+path.join(root,'index.html')+'#/eco-nav2-stack/figure/nav2-costmap-planning');
    await page.locator('#fig-nav2-costmap-planning img').evaluate(img=>{img.loading='eager';return img.decode();});
    assert.match(await page.locator('.experiment-table').nth(1).innerText(),/4\.93 m/);
    assert.equal(await page.locator('#edit-link').isVisible(),false);
    await page.locator('#menu-button').click();
    const item=page.locator('.tree-section-list a[data-section-id=part-8-sub-1]');
    await item.press('Enter');
    await page.locator('#part-8-sub-1.matched-section').waitFor();
    assert.equal(await page.locator('#part-8-sub-1').getAttribute('data-section-number'),'45.9.1');
    assert.equal(await page.locator('#menu-button').getAttribute('aria-expanded'),'false');
    await page.goto('file://'+path.join(root,'index.html')+'#/eco-slam-mapping/section/part-9-sub-2');
    await page.locator('#fig-slam-mapping-trajectory img').evaluate(img=>img.decode());
    assert.equal(await page.locator('#part-9-sub-2').getAttribute('data-section-number'),'41.10.2');
    assert.match(await page.locator('.experiment-table').last().innerText(),/13426 格逐格一致/);
    const nojs=await browser.newContext({offline:true,javaScriptEnabled:false,viewport:{width:390,height:844}}),book=await nojs.newPage();
    book.on('request',r=>{if(/^https?:/.test(r.url()))external.push(r.url())});
    await book.goto('file://'+path.join(root,'book.html'));
    assert.equal(await book.locator('.chapter').count(),60);assert.equal(await book.locator('math').count(),49);assert.equal(await book.locator('svg').count(),36);
    const evidenceTables=await book.locator('.experiment-table').count();
    assert.equal(evidenceTables,39,'便携包保留三十九张实测数据表');
    const expectedChapters=await page.evaluate(()=>ROS2Hub.lessons.map(chapter=>({
      id:chapter.id, title:chapter.title, numbered:chapter.sections.length,
    })));
    const outline=await book.evaluate(chapters=>{
      const result={chapters:0,numbered:0,numberedChildren:0,entries:0,issues:[]};
      const norm=label=>label.replace(/\s+/g,' ').trim();
      for(const [index,{id,title,numbered}] of chapters.entries()){
        const prefix='chapter-'+id, article=document.getElementById(prefix);
        if(!article || article.querySelector('h2')?.textContent!==title){result.issues.push(prefix);continue;}
        const toc=article.querySelector('.book-chapter-toc'), links=[...(toc?.querySelectorAll('a')||[])];
        const main=article.querySelectorAll(':scope > section[id^="'+prefix+'-part-"]');
        if(main.length!==numbered||!toc)result.issues.push(prefix+' 主小节数');
        result.chapters++;
        for(const [i,section] of [...main].entries()){
          const number=(index+1)+'.'+(i+1);
          if(section.querySelector(':scope > h3 > .section-number')?.textContent!==number)result.issues.push(section.id);
          result.numbered++;
          for(const [j,child] of [...section.querySelectorAll('h4[id]')].entries()){
            if(child.querySelector('.section-number')?.textContent!==number+'.'+(j+1))result.issues.push(child.id);
            result.numberedChildren++;
          }
        }
        for(const link of links){
          const anchor=link.getAttribute('href').slice(1), target=document.getElementById(anchor);
          const title=target?.matches('h3,h4')?target:target?.querySelector(':scope > h3,:scope > summary');
          if(!title || norm(link.textContent)!==norm(title.textContent))result.issues.push(anchor);
          const parent=link.closest('ul').parentElement.querySelector(':scope > a');
          if(anchor.includes('-sub-') && parent?.getAttribute('href')!=='#'+anchor.split('-sub-')[0])result.issues.push(anchor+' 父级');
        }
        const anchors=article.querySelectorAll('section[id],h3[id],h4[id],details.sources[id]').length;
        if(anchors!==links.length || new Set(links.map(link=>link.hash)).size!==links.length)result.issues.push(prefix+' 目录覆盖');
        result.entries+=links.length;
      }
      return result;
    },expectedChapters);
    assert.deepEqual(outline.issues,[]);
    assert.equal(outline.chapters,60);
    const nav=book.locator('#chapter-eco-nav2-stack .book-chapter-toc');
    await nav.locator('summary').click();
    await nav.locator('a[href="#chapter-eco-nav2-stack-part-9-sub-2"]').press('Enter');
    assert.equal(new URL(book.url()).hash,'#chapter-eco-nav2-stack-part-9-sub-2');
    for(const width of [390,320]){
      await book.setViewportSize({width,height:844});
      const dimensions=await book.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
      assert.ok(dimensions.scroll<=width+1,'连续版整页溢出 '+JSON.stringify(dimensions));
    }
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    console.log(JSON.stringify({passed:true,portable:true,chapters:60,equations:49,svgInstances:36,evidenceTables,outline,noScript:true,widths:[390,320],externalRequests:0,errors}));
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
