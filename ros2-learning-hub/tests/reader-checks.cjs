const {chromium}=require('./browser-runtime.cjs');
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const {checkChapterOutline,checkSectionJumps}=require('../design-review/scripts/qa_outline.cjs');
(async()=>{
 fs.mkdirSync(path.resolve(__dirname,'../.qa'),{recursive:true});
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
 // 一章可以直接包含多组实现；只检查被操作的那组，其他组应保持独立。
 const implementation=page.locator('.implementation').first();
 await implementation.locator('[role=tab]').nth(1).click();assert.equal(await implementation.locator('[role=tabpanel]:visible').count(),1);
 await implementation.locator('[data-compare]').click();assert.equal(await implementation.locator('[role=tabpanel]:visible').count(),2);
 if(await page.locator('.implementation').count()>1)assert.equal(await page.locator('.implementation').nth(1).locator('[role=tabpanel]:visible').count(),1);
 const ids=await page.evaluate(()=>ROS2Hub.lessons.map(c=>c.id));
 const outlineAudit=[];
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:width===1440?1040:844});
  const chapters=[];
  for(const id of ids){
   await page.evaluate(chapter=>{location.hash='#/'+chapter;},id);
   await page.waitForFunction(chapter=>document.querySelector('.tree-subtree')?.dataset.chapter===chapter,id);
   const entry=await checkChapterOutline(page,id,true);
   if(width===1440)entry.jumps=await checkSectionJumps(page,id);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),width+'px '+id+' 整页宽度');
   chapters.push(entry);
  }
  const totals=Object.fromEntries(['numbered','childEntries','numberedChildren','entries','paragraphs','jumps'].map(
   name=>[name,chapters.reduce((sum,chapter)=>sum+(chapter[name]||0),0)],
  ));
  outlineAudit.push({width,...totals,chapters});
  console.log('正式目录 '+width+'px · '+ids.length+' 章 · '+totals.entries+' 条 · '+totals.jumps+' 次跳转');
 }
 await page.setViewportSize({width:1440,height:1040});
 await navigate('#/eco-nav2-stack/section/part-8-sub-2');
 await page.locator('#part-8-sub-2.matched-section').waitFor();
 assert.equal(await page.locator('.tree-section-list [aria-current=location] .outline-index').textContent(),'45.9.2');
 await page.locator('#fig-nav2-costmap-planning img').evaluate(img=>img.decode());
 await page.screenshot({path:path.resolve(__dirname,'../.qa/formal-nav2-outline.png'),animations:'disabled'});
 const editUrl=await page.locator('#edit-link').evaluate(link=>link.href);
 assert.ok(editUrl.endsWith('#/eco-nav2-stack/section/part-8-sub-2?mode=edit'));
 const review=await context.newPage();
 await review.goto(editUrl);
 assert.equal(await review.locator('#view-mode').inputValue(),'edit');
 assert.equal(await review.locator('#part-8-sub-2').getAttribute('data-section-number'),'45.9.2');
 await review.locator('#view-mode').selectOption('read');
 assert.equal(await review.locator('body').getAttribute('data-mode'),'read');
 await review.close();
 await navigate('#/math-rigid');assert.ok(await page.locator('math').count()>0,'离线公式存在');
 await navigate('#/qos');assert.match(await page.locator('#reading').innerText(),/七个真实端点/);
 assert.match(await page.locator('#reading').innerText(),/UNKNOWN/);
 await page.locator('#part-6 h2').evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));
 assert.ok(await page.locator('#chapter-tree').evaluate(el=>{const box=el.getBoundingClientRect(),current=el.querySelector('[aria-current=page]').getBoundingClientRect();return current.top>=box.top-1&&current.bottom<=box.bottom+1}),'长目录应保持当前章在树容器可见');
 await page.screenshot({path:path.resolve(__dirname,'../.qa/iteration-qos.png'),animations:'disabled'});
 await navigate('#/executors');assert.match(await page.locator('#reading').innerText(),/clock=self.steady_clock/);
 assert.equal(await page.locator('.experiment-table').count(),2,'执行器与Future的两份真实数据表应渲染');
 await navigate('#/parameters');assert.equal(await page.locator('.experiment-table').count(),1);
 await page.locator('.experiment-table h3').evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));
 await page.screenshot({path:path.resolve(__dirname,'../.qa/iteration2-parameters.png'),animations:'disabled'});
 await navigate('#/actions');assert.equal(await page.locator('.experiment-table').count(),1);
 assert.match(await page.locator('#reading').innerText(),/GoalStatus没有REJECTED/);
 await navigate('#/composition');assert.equal(await page.locator('.experiment-table').count(),2);
 assert.match(await page.locator('#reading').innerText(),/默认关闭管理节点自己的参数服务/);
 await page.locator('.experiment-table h3').first().evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));
 await page.screenshot({path:path.resolve(__dirname,'../.qa/iteration3-composition.png'),animations:'disabled'});
 await navigate('#/lifecycle');assert.equal(await page.locator('.experiment-table').count(),2);
 assert.match(await page.locator('#reading').innerText(),/errorprocessing/);
 await page.locator('.experiment-table h3').first().evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));
 await page.screenshot({path:path.resolve(__dirname,'../.qa/iteration4-lifecycle.png'),animations:'disabled'});
 await navigate('#/testing');assert.equal(await page.locator('.experiment-table').count(),3);
 const policy=page.locator('.code-example').filter({has:page.locator('.code-caption span[title="testing_policy/policy.py"]')});
 assert.equal(await policy.count(),1);assert.match(await policy.locator('pre').innerText(),/type\(timeout_ns\) is not int/);
 await navigate('#/deployment');assert.equal(await page.locator('.experiment-table').count(),3);
 assert.match(await page.locator('#reading').innerText(),/CMD \["\/work\/install\/lib\/hub_component\/hub_talker_node"\]/);
 await navigate('#/time-bag');assert.equal(await page.locator('.experiment-table').count(),2);
 assert.match(await page.locator('#reading').innerText(),/零值clock仍不是已启动时钟/);
 assert.match(await page.locator('#reading').innerText(),/matchedSubscriptionsAtResume/);
 await navigate('#/eco-data-observability');assert.equal(await page.locator('.experiment-table').count(),2);
 assert.match(await page.locator('#reading').innerText(),/无单独发送时间列/);
 await page.locator('.experiment-table h3').first().evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));
 await page.screenshot({path:path.resolve(__dirname,'../.qa/iteration5-bag.png'),animations:'disabled'});
 await navigate('#/eco-model-rviz');assert.equal(await page.locator('.experiment-table').count(),3);
 assert.match(await page.locator('#reading').innerText(),/合法velocity-only/);
 assert.match(await page.locator('#reading').innerText(),/joint_state/);
 await page.locator('.experiment-table h3').first().evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));
 await page.screenshot({path:path.resolve(__dirname,'../.qa/iteration6-model.png'),animations:'disabled'});
 await navigate('#/eco-control-framework');assert.equal(await page.locator('.experiment-table').count(),1);
 assert.match(await page.locator('#reading').innerText(),/管理器实际资源回执/);
 await navigate('#/eco-diff-drive-tracks');assert.equal(await page.locator('.experiment-table').count(),1);
 assert.match(await page.locator('#reading').innerText(),/1\.10 \/ 2\.90/);
 await navigate('#/eco-state-estimation');assert.equal(await page.locator('.experiment-table').count(),3);
 assert.match(await page.locator('.experiment-table').first().innerText(),/0 条新时戳原始输入/);
 assert.match(await page.locator('.experiment-table').nth(1).innerText(),/0\.30 s 扫描窗内无新位姿/);
 assert.match(await page.locator('.experiment-table').last().innerText(),/短期扫描后再清空缓冲[\s\S]*定位扫描已接受[\s\S]*8[\s\S]*清空定位缓冲后重读/);
 await page.locator('.experiment-table h3').first().evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));
 await page.screenshot({path:path.resolve(__dirname,'../.qa/iteration7-drive.png'),animations:'disabled'});
 await navigate('#/eco-gazebo-simulation');assert.equal(await page.locator('.experiment-table').count(),1);
 assert.match(await page.locator('.experiment-table').innerText(),/五类采样时戳/);
 await navigate('#/eco-perception-pipeline');assert.equal(await page.locator('.experiment-table').count(),2);
 assert.match(await page.locator('.experiment-table').nth(1).innerText(),/2\.20\d+ m/);
 const sensorFigure=page.locator('#fig-gazebo-sensor-captures img');
 await page.locator('#fig-gazebo-sensor-captures').evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));
 await sensorFigure.evaluate(img=>img.decode());
 assert.ok(await sensorFigure.evaluate(img=>img.naturalWidth>0));
 await page.screenshot({path:path.resolve(__dirname,'../.qa/iteration8-sensors.png'),animations:'disabled'});
 await navigate('#/eco-tf-frames');assert.equal(await page.locator('.experiment-table').count(),1);
 assert.match(await page.locator('#reading').innerText(),/非零origin/);
 await navigate('#/eco-nav2-stack');assert.equal(await page.locator('.experiment-table').count(),2);
 assert.match(await page.locator('.experiment-table').nth(1).innerText(),/4\.55 m[\s\S]*4\.93 m/);
 await page.locator('#fig-nav2-costmap-planning img').evaluate(img=>{img.loading='eager';return img.decode();});
 await navigate('#/eco-nav2-task-programming');
 assert.match(await page.locator('.experiment-table').innerText(),/206 · GOAL_OCCUPIED[\s\S]*208 · NO_VALID_PATH/);
 await navigate('#/eco-slam-mapping/section/part-9-sub-2');
 const slamFigure=page.locator('#fig-slam-mapping-trajectory img');
 await slamFigure.evaluate(img=>img.decode());
 assert.equal(await page.locator('.tree-section-list [aria-current=location] .outline-index').textContent(),'41.10.2');
 assert.equal(await page.locator('.experiment-table').count(),3);
 assert.match(await page.locator('.experiment-table').last().innerText(),/13426 格逐格一致[\s\S]*41 个建图节点/);
 await navigate('#/tf2');assert.match(await page.locator('#reading').innerText(),/0.414213562/);
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
 await page.locator('.equation').first().scrollIntoViewIfNeeded();await page.screenshot({path:path.resolve(__dirname,'../.qa/textbook-math.png'),animations:'disabled'});
 await page.setViewportSize({width:390,height:844});
 await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=1);
 await page.screenshot({path:path.resolve(__dirname,'../.qa/textbook-mobile.png'),animations:'disabled'});
 await page.keyboard.press('Control+k');await page.locator('#search-input').fill('雅可比');assert.ok(await page.locator('.search-result').count()>0);await page.keyboard.press('Escape');
 assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
 const bookContext=await browser.newContext({offline:true,javaScriptEnabled:false});const book=await bookContext.newPage();
 await book.goto('file://'+path.resolve(__dirname,'../dist/book.html'));
 assert.ok(await book.locator('math').count()>30);assert.ok(await book.locator('svg').count()>15);
 assert.equal(await book.locator('svg').count(),36,'连续版保留两处 SLAM 实测图');
 assert.equal(await book.locator('.experiment-table').count(),39,'无脚本连续版保留三十九张实测数据表');
 assert.equal(await book.locator('svg image[href^="data:image/png"]').count(),4);
 const report={checkedAt:'2026-11-07',iteration:'2026-11-07-r10',passed:true,chapters:ids.length,outlineAudit,math:await book.locator('math').count(),figures:await book.locator('svg').count(),evidenceTables:await book.locator('.experiment-table').count(),offlineRequests:remote.length,errors};
 fs.writeFileSync(path.resolve(__dirname,'../validation-evidence/offline-reader-current-validation.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({...report,outlineAudit:outlineAudit.map(({chapters,...totals})=>totals)}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
