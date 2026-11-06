const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/home/mu/.local/lib/python3.10/site-packages/playwright/driver/package');
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
 const context=await browser.newContext({offline:true,viewport:{width:1440,height:1000}});
 const page=await context.newPage(),errors=[],remote=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
 const base='file://'+path.resolve(__dirname,'../dist/index.html');
 await page.goto(base+'#/lesson/tf2');await page.waitForFunction(()=>window.ROS2Hub);
 assert.equal(await page.locator('#chapter-tree').count(),1,'正式入口应采用章节树双栏阅读器');
 await page.locator('#fig-tf2-transform').waitFor();
 await page.locator('[data-study="done"]').click();
 assert.match(await page.locator('[data-study="done"]').innerText(),/已完成/);
 await page.reload();await page.locator('[data-study="done"]').waitFor();
 assert.match(await page.locator('[data-study="done"]').innerText(),/已完成/);
 const navigate=async hash=>{await page.evaluate(h=>location.hash=h,hash);await page.waitForTimeout(60)};
 await navigate('#/pubsub');await page.locator('[role=tab]').first().waitFor();
 await page.locator('[role=tab]').nth(1).click();assert.equal(await page.locator('[role=tabpanel]:visible').count(),1);
 await page.locator('[data-compare]').click();assert.equal(await page.locator('[role=tabpanel]:visible').count(),2);
 const ids=await page.evaluate(()=>ROS2Hub.lessons.map(c=>c.id));
 for(const id of ids){await navigate('#/'+id);assert.equal(await page.locator('.chapter-header h1').count(),1,id);assert.equal(await page.locator('.reading-section').count()>4,true,id)}
 await navigate('#/math-rigid');assert.ok(await page.locator('math').count()>0,'离线公式存在');
 await navigate('#/resources');await page.locator('#resource-query').fill('Nav2');assert.ok(await page.locator('.resource-row:visible').count()>0);
 await navigate('#/coverage');await page.locator('#coverage-query').fill('SLAM');assert.ok(await page.locator('.coverage-row:visible').count()>0);
 await navigate('#/saved');assert.match(await page.locator('#reading').innerText(),/tf2/);
 for(const route of ['#/examples','#/projects','#/ecosystem','#/troubleshoot','#/compare','#/downloads','#/home']){
  await navigate(route);assert.ok((await page.locator('#reading').innerText()).length>150,route);
 }
 for(const width of [390,320]){
  await page.setViewportSize({width,height:844});
  for(const id of ['math-rigid','math-estimation','theory-planning','eco-model-rviz','project-navigation','resources','coverage','saved','downloads']){
   await navigate('#/'+id);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`page overflow ${width} ${id}`);
  }
 }
 await page.setViewportSize({width:1440,height:1050});await navigate('#/math-rigid');
 await page.locator('.equation').first().scrollIntoViewIfNeeded();await page.screenshot({path:path.resolve(__dirname,'../.qa/textbook-math.png')});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.resolve(__dirname,'../.qa/textbook-mobile.png')});
 await page.keyboard.press('Control+k');await page.locator('#search-input').fill('雅可比');assert.ok(await page.locator('.search-result').count()>0);await page.keyboard.press('Escape');
 assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
 const bookContext=await browser.newContext({offline:true,javaScriptEnabled:false});const book=await bookContext.newPage();
 await book.goto('file://'+path.resolve(__dirname,'../dist/book.html'));
 assert.ok(await book.locator('math').count()>30);assert.ok(await book.locator('svg').count()>15);
 console.log(JSON.stringify({passed:true,chapters:ids.length,math:await book.locator('math').count(),figures:await book.locator('svg').count(),offlineRequests:remote.length,errors}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
