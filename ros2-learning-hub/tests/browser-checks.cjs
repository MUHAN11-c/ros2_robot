const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/home/mu/.local/lib/python3.10/site-packages/playwright/driver/package');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
(async()=>{
  const root=path.resolve(__dirname,'..'), qa=path.join(root,'.qa');
  await fs.mkdir(qa,{recursive:true});
  const browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1050},acceptDownloads:true});
  const page=await context.newPage(), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const base='http://127.0.0.1:8766/';
  try {
    const response=await page.goto(base);assert.equal(response.status(),200);
    await page.locator('.hero h1').waitFor();
    assert.equal(await page.locator('.stats section').count(),0,'首页章节不得被统计栅格包裹');
    await page.screenshot({path:path.join(qa,'desktop-home.png'),fullPage:true});
    const data=await page.evaluate(()=>({lessons:ROS2Hub.lessons.map(x=>x.id),comparisons:ROS2Hub.comparisons.map(x=>x.id)}));
    assert.equal(data.lessons.length,44);
    await page.getByRole('button',{name:'搜索知识、API、资料'}).click();
    await page.locator('#search-input').fill('Nav2');
    assert.ok(await page.locator('.search-result').count()>3);
    await page.locator('#search-input').fill('<img src=x onerror=alert(1)>');
    assert.equal(await page.locator('#search-results img').count(),0);
    await page.keyboard.press('Escape');
    await page.goto(base+'#/lesson/pubsub');
    await page.getByRole('button',{name:'标记为已完成',exact:true}).click();
    await page.reload();
    await page.getByRole('button',{name:'已完成 · 取消标记'}).waitFor();
    await page.getByRole('button',{name:'收藏本章',exact:true}).click();
    await page.goto(base+'#/saved');assert.equal(await page.locator('.lesson-row').count(),1);
    await page.goto(base+'#/lesson/qos');
    await page.locator('.skip').focus();await page.keyboard.press('Enter');
    assert.match(page.url(),/#\/lesson\/qos$/,'skip link must preserve the current lesson');
    assert.equal(await page.evaluate(()=>document.activeElement.id),'main');
    await page.locator('[data-qos="offered-reliability"]').selectOption('best_effort');
    assert.match(await page.locator('#qos-result').textContent(),/不兼容/);
    await page.locator('[data-qos="requested-reliability"]').selectOption('best_effort');
    assert.match(await page.locator('#qos-result').textContent(),/可以匹配/);
    await page.goto(base+'#/resources');
    await page.locator('#resource-query').fill('Nav2');
    assert.ok(await page.locator('.resource').count()>0);
    assert.ok(await page.locator('.resource').count()<20);
    await page.locator('#resource-query').fill('this-search-must-have-no-results');
    assert.equal(await page.locator('.resource').count(),0);
    await page.getByRole('button',{name:'清除筛选'}).click();
    await page.locator('.catalog-details').first().locator('summary').click();
    assert.equal(await page.locator('#catalog-zsc .catalog-item').count(),22);
    await page.goto(base+'#/compare/compare-launch');
    assert.equal(await page.locator('.variant').count(),3);
    await page.getByRole('button',{name:'YAML',exact:true}).click();
    assert.equal(await page.locator('.variant').count(),1);
    assert.match(await page.locator('.variant').innerText(),/launch:/);
    await page.goto(base+'#/lesson/architecture');
    const downloadEvent=page.waitForEvent('download');
    await page.getByRole('button',{name:'导出本章',exact:true}).click();
    const download=await downloadEvent;await download.saveAs(path.join(qa,'export.md'));
    assert.match(await fs.readFile(path.join(qa,'export.md'),'utf8'),/ROS 2 的分层/);
    await page.goto(base+'#/lesson/not-found');assert.match(await page.locator('#main').innerText(),/没有找到/);
    for(const id of data.lessons){await page.goto(base+'#/lesson/'+id);await page.locator('#goals').waitFor();assert.ok(await page.locator('#main').innerText().then(x=>x.length)>2500,id);assert.ok(await page.locator('.deep-link').count()>=5,id);}
    for(const id of data.comparisons){await page.goto(base+'#/compare/'+id);assert.ok(await page.locator('.variant').count()>=2,id);}
    await page.goto(base+'#/lesson/eco-control-framework');
    await page.screenshot({path:path.join(qa,'desktop-lesson.png'),fullPage:true});
    for(const width of [390,320]){
      await page.setViewportSize({width,height:844});
      for(const route of ['home','courses','examples','resources','ecosystem','projects','troubleshoot','saved','about',...data.lessons.map(x=>'lesson/'+x),...data.comparisons.map(x=>'compare/'+x)]){
        await page.goto(base+'#/'+route);
        const size=await page.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth}));
        assert.ok(size.scroll<=size.w+1,`${width}px overflow: ${route} (${size.scroll})`);
      }
    }
    await page.setViewportSize({width:390,height:844});await page.goto(base);
    await page.getByRole('button',{name:'展开导航'}).click();
    assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('menu-open')),true);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('menu-open')),false);
    await page.screenshot({path:path.join(qa,'mobile-home.png'),fullPage:true});
    if(!process.argv.includes('--smoke')){
      for(const file of ['book.html','downloads/chapter-code.zip','downloads/atlas_examples.zip','downloads/ros2-learning-guide.md','downloads/sources.json','downloads/bibliography.md','control-lab/index.html','THIRD_PARTY_NOTICES.md']){
        const r=await context.request.get(base+file);assert.equal(r.status(),200,file);
      }
    }
    await page.evaluate(()=>localStorage.setItem('ros2-atlas-v1','{broken'));
    await page.reload();await page.locator('.hero h1').waitFor();
    await context.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new Error('disabled')}}));
    await page.reload();await page.locator('.hero h1').waitFor();
    await page.goto(base+'#/lesson/architecture');await page.getByRole('button',{name:'标记为已完成',exact:true}).click();
    await page.getByRole('button',{name:'已完成 · 取消标记'}).waitFor();
    const offline=await browser.newContext({offline:true,viewport:{width:390,height:844}});
    const local=await offline.newPage(), external=[];
    local.on('request',request=>{if(/^https?:/.test(request.url()))external.push(request.url())});
    local.on('pageerror',error=>errors.push(error.message));
    await local.goto('file://'+path.join(root,'dist/index.html'));
    await local.locator('.hero h1').waitFor();
    await local.getByRole('button',{name:'展开导航'}).click();
    await local.getByRole('button',{name:'搜索知识、API、资料'}).click();
    await local.locator('#search-input').fill('动作块');
    assert.ok(await local.locator('.search-result').count()>0,'offline full-text search');
    await local.goto('file://'+path.join(root,'dist/index.html')+'#/lesson/learning-policy');
    assert.ok(await local.locator('.deep-link').count()>=5);
    assert.deepEqual(external,[],'normal offline reading must make no HTTP requests');
    await offline.close();
    const noScript=await browser.newContext({javaScriptEnabled:false,offline:true,viewport:{width:390,height:844}});
    const book=await noScript.newPage();
    await book.goto('file://'+path.join(root,'dist/book.html'));
    assert.equal(await book.locator('article.chapter').count(),44);
    assert.ok(await book.locator('.answer').count()>=176);
    const bookSize=await book.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth}));
    assert.ok(bookSize.scroll<=bookSize.w+1,'mobile reading edition overflow');
    await book.screenshot({path:path.join(qa,'offline-book.png'),fullPage:false});
    await noScript.close();
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({passed:true,lessons:data.lessons.length,comparisons:data.comparisons.length,mobileWidths:[390,320],browserErrors:errors,artifacts:qa}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
