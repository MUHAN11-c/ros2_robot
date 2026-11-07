/* 正式入口的行为验收：进度、查找、对照、原文、导出与全章移动布局。 */
const {chromium}=require('./browser-runtime.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');
(async()=>{
  const root=path.resolve(__dirname,'..'),qa=path.join(root,'.qa');
  await fs.mkdir(qa,{recursive:true});
  const browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1050},acceptDownloads:true,reducedMotion:'reduce'});
  const page=await context.newPage(),errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith('http://127.0.0.1:8766/'))external.push(r.url())});
  const base='http://127.0.0.1:8766/';
  // 等待 hashchange 的渲染完成；切换章节不重复下载整份内容数据。
  const navigate=async hash=>page.evaluate(async h=>{
    if(location.hash===h)return;
    await new Promise(resolve=>{addEventListener('hashchange',()=>requestAnimationFrame(resolve),{once:true});location.hash=h});
  },hash);
  try{
    assert.equal((await page.goto(base)).status(),200);
    await page.locator('.home-intro h1').waitFor();
    const data=await page.evaluate(()=>({lessons:ROS2Hub.lessons.map(c=>({id:c.id,title:c.title})),comparisons:ROS2Hub.comparisons.map(c=>c.id),resourceCount:ROS2Hub.resources.length}));
    assert.equal(data.lessons.length,60);
    await page.screenshot({path:path.join(qa,'desktop-home.png'),animations:'disabled'});
    await page.keyboard.press('Control+k');await page.locator('#search-input').fill('Nav2');
    assert.ok(await page.locator('.search-result').count()>3);
    await page.locator('#search-input').fill('<img src=x onerror=alert(1)>');
    assert.equal(await page.locator('#search-results img').count(),0);await page.keyboard.press('Escape');

    await navigate('#/lesson/pubsub');
    await page.locator('[data-study=done]').click();await page.locator('[data-study=star]').click();
    await page.reload();await page.locator('[data-study=done][aria-pressed=true]').waitFor();
    assert.equal(await page.locator('[data-study=star]').getAttribute('aria-pressed'),'true');
    await navigate('#/saved');assert.equal(await page.locator('.lesson-row').count(),2);
    let event=page.waitForEvent('download');await page.locator('[data-export-progress]').click();
    let download=await event;await download.saveAs(path.join(qa,'progress.json'));
    const progress=JSON.parse(await fs.readFile(path.join(qa,'progress.json'),'utf8'));
    assert.equal(progress.format,'ros2-atlas-v1');assert.deepEqual(progress.done,['pubsub']);
    // 未知章节、重复项、无效主题不进入真实学习状态。
    await page.locator('#import-progress').setInputFiles({name:'progress.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({format:'ros2-atlas-v1',done:['tf2','tf2','unknown'],stars:['math-rigid'],last:'tf2',theme:'invalid'}))});
    await page.waitForFunction(()=>JSON.parse(localStorage.getItem('ros2-atlas-v1')).done[0]==='tf2');
    assert.deepEqual(await page.evaluate(()=>JSON.parse(localStorage.getItem('ros2-atlas-v1')).done),['tf2']);
    await page.locator('button[data-theme]').click();await page.reload();
    assert.equal(await page.locator('body').getAttribute('data-theme'),'dark');
    await page.locator('button[data-theme]').click();

    await navigate('#/lesson/qos');await page.locator('.skip-link').focus();await page.keyboard.press('Enter');
    assert.match(page.url(),/#\/lesson\/qos$/);assert.equal(await page.evaluate(()=>document.activeElement.id),'reading');
    await page.locator('[data-qos=offered-reliability]').selectOption('best_effort');
    assert.match(await page.locator('#qos-result').innerText(),/不兼容/);
    await page.locator('[data-qos=requested-reliability]').selectOption('best_effort');
    assert.match(await page.locator('#qos-result').innerText(),/可以匹配/);
    await navigate('#/resources');await page.locator('#resource-query').fill('Nav2');
    const sourceMatches=await page.evaluate(()=>ROS2Hub.resources.filter(item=>JSON.stringify(item).toLowerCase().includes('nav2')).map(item=>item.title));
    assert.ok(sourceMatches.length>0&&sourceMatches.length<data.resourceCount);
    assert.deepEqual(await page.locator('.resource-row summary strong').allTextContents(),sourceMatches);
    await page.locator('#resource-query').fill('this-search-must-have-no-results');assert.equal(await page.locator('.resource-row').count(),0);
    await page.locator('#resource-query').fill('');assert.equal(await page.locator('.resource-row').count(),data.resourceCount);
    await navigate('#/coverage');assert.equal(await page.locator('.coverage-row').count(),627);
    await page.locator('#coverage-query').fill('SLAM');assert.ok(await page.locator('.coverage-row').count()>0);
    await navigate('#/compare/compare-launch');const group=page.locator('.implementation');
    assert.equal(await group.getByRole('tab').count(),3);
    await group.getByRole('tab',{name:'YAML',exact:true}).click();assert.match(await group.locator('[role=tabpanel]:visible').innerText(),/launch:/);
    await page.keyboard.press('Home');assert.equal(await group.getByRole('tab').first().getAttribute('aria-selected'),'true');
    await group.locator('[data-compare]').click();assert.equal(await group.locator('[role=tabpanel]:visible').count(),3);
    await navigate('#/math-rigid');event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;await download.saveAs(path.join(qa,'chapter-export.md'));
    const exported=await fs.readFile(path.join(qa,'chapter-export.md'),'utf8');assert.match(exported,/单位|维度/);assert.match(exported,/\$\$/);assert.match(exported,/输入|输出/);
    await navigate('#/parameters');event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;await download.saveAs(path.join(qa,'parameter-export.md'));
    const parameterExport=await fs.readFile(path.join(qa,'parameter-export.md'),'utf8');
    assert.match(parameterExport,/### 参数存储与应用快照分别检查/);
    assert.ok(parameterExport.includes('| 场景 | 设置结果 | 存储[lower,upper,span](m) | 快照[lower,upper,span](m) | 应用状态 |\n| --- | --- | --- | --- | --- |\n'),'单章下载的表头/分隔行必须连续');
    await navigate('#/composition');event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;await download.saveAs(path.join(qa,'composition-export.md'));
    const compositionExport=await fs.readFile(path.join(qa,'composition-export.md'),'utf8');
    assert.match(compositionExport,/同一Config的参数来源、输出与拒绝/);
    assert.ok(compositionExport.includes('| 场景 | 配置入口 | 生效gain | 输出m/s | 实际结果 |\n| --- | --- | --- | --- | --- |\n'),'组件实测表应以连续Markdown下载');
    assert.ok(compositionExport.includes('component_labs/validate_components.py'),'下载包含同源完整验收脚本');
    await navigate('#/testing');event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;await download.saveAs(path.join(qa,'testing-export.md'));
    const testingExport=await fs.readFile(path.join(qa,'testing-export.md'),'utf8');
    assert.ok(testingExport.includes('| 阶段 | 实际测试/反例 | 结果 | 能说明什么 |\n| --- | --- | --- | --- |\n'),'原例覆盖表应以连续Markdown导出');
    assert.ok(testingExport.includes('type(timeout_ns) is not int'),'单章导出使用修订后的严格纳秒合同');
    await navigate('#/time-bag');event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;await download.saveAs(path.join(qa,'bag-export.md'));
    const bagExport=await fs.readFile(path.join(qa,'bag-export.md'),'utf8');
    assert.ok(bagExport.includes('| 阶段 | 发送的input序号 | 数据订阅input/derived/static | 最终录到这组input条数 |\n| --- | --- | --- | --- |\n'),'零值clock实测表保持连续Markdown');
    assert.ok(bagExport.includes('matchedSubscriptionsAtResume'),'单章导出携带本轮同源完整实验');
    await navigate('#/eco-model-rviz');event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;await download.saveAs(path.join(qa,'model-export.md'));
    const modelExport=await fs.readFile(path.join(qa,'model-export.md'),'utf8');
    assert.ok(modelExport.includes('| 检查入口 | 本次退出码 | 实际观察 | 能支持的结论 |\n| --- | --- | --- | --- |\n'),'惯量反例表保持连续Markdown');
    assert.ok(modelExport.includes('<xacro:macro name="wheel"'),'单章导出包含同源完整Xacro宏');
    await navigate('#/eco-control-framework');event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;
    const driveExport=await fs.readFile(await download.path(),'utf8');
    assert.ok(driveExport.includes('| 阶段 | drive | reserve | 占用的轮速接口 |\n| --- | --- | --- | --- |\n'));
    assert.ok(driveExport.includes('drive_labs/validate_drive.py')&&driveExport.includes('mock_components/GenericSystem'));
    await navigate('#/eco-gazebo-simulation');event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;
    const sensorExport=await fs.readFile(await download.path(),'utf8');
    assert.ok(sensorExport.includes('gazebo_labs/sensors.sdf')&&sensorExport.includes('gazebo_labs/bridge.yaml'));
    assert.ok(sensorExport.includes('| 阶段 | ROS 时间（s） | 采样与控制回执 |\n| --- | --- | --- |\n'));
    const pinnedBridgeLink='.local-source-link[href$="ros_gz_bridge%2FREADME.md"]';
    await page.locator('.source-note summary').click();
    await page.locator(pinnedBridgeLink).click();
    await page.locator('.original-document').waitFor();
    assert.match(await page.locator('.original-document').innerText(),/parameter_bridge/);
    await page.goto(base+'design-review/index.html#/eco-gazebo-simulation');
    await page.locator('.source-note summary').click();
    await page.locator(pinnedBridgeLink).click();
    await page.locator('.original-document').waitFor();
    assert.match(await page.locator('.original-document').innerText(),/GZ_TO_ROS/);
    await page.goto(base+'#/eco-nav2-stack');
    await page.locator('#part-8').waitFor({state:'attached'});
    event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;
    const navExport=await fs.readFile(await download.path(),'utf8');
    assert.ok(navExport.includes('| 代价地图 | 路径 | 采样与服务结果 |\n| --- | --- | --- |\n'));
    assert.ok(navExport.includes('4.55 m')&&navExport.includes('4.93 m'));
    const pinnedPlannerLink='.local-source-link[href$="nav2_planner%2Fsrc%2Fplanner_server.cpp"]';
    await page.locator('.source-note summary').click();
    await page.locator(pinnedPlannerLink).click();
    await page.locator('.original-document').waitFor();
    assert.match(await page.locator('.original-document').innerText(),/PlannerServer::isPathValid/);
    await navigate('#/eco-state-estimation');
    event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;
    const localizationExport=await fs.readFile(await download.path(),'utf8');
    assert.ok(localizationExport.includes('| 阶段 | 建图节点 | 短期定位节点 | 短期约束 | 相对原图的差异格 |'));
    assert.ok(localizationExport.includes('| 定位扫描已接受 | 37 | 4 | 9 | 8 |'));
    assert.ok(localizationExport.includes('| 清空定位缓冲后重读 | 37 | 0 | 0 | 0 |'));
    const pinnedLocalization='.local-source-link[href$="src%2Fslam_toolbox_localization.cpp"]';
    await page.locator('.source-note summary').click();
    await page.locator(pinnedLocalization).click();
    await page.locator('.original-document').waitFor();
    assert.match(await page.locator('.original-document').innerText(),/clearLocalizationBuffer/);
    await navigate('#/project-navigation');
    event=page.waitForEvent('download');await page.locator('[data-study=export]').click();
    download=await event;
    const projectExport=await fs.readFile(await download.path(),'utf8');
    assert.ok(projectExport.includes('nav2_labs/validate_nav2.py')&&projectExport.includes('class NavigationLab(Lab):'));
    assert.ok(projectExport.includes('slam_labs/validate_slam.py')&&projectExport.includes('slam_labs/scan_run.py'));
    await navigate('#/lesson/not-found');assert.match(await page.locator('#reading h1').innerText(),/没有找到/);

    // 读取本地官方源码仍在本站，目录与上一级也由白名单 API 提供。
    await navigate('#/library');await page.locator('#library-source').selectOption('ros2--examples');
    await page.locator('#library-version').selectOption('jazzy');assert.equal(await page.locator('.library-row').count(),1);
    await page.locator('.library-row summary').click();await page.getByRole('link',{name:'在站内查看入口',exact:true}).click();
    await page.locator('.original-document').waitFor();assert.ok((await page.locator('.original-document').innerText()).length>100);
    await page.getByRole('link',{name:'上一级目录',exact:true}).click();await page.locator('#original-source .source-file-list').waitFor();
    assert.match(await page.locator('#original-source').innerText(),/rclcpp|rclpy/);
    assert.equal((await context.request.get(base+'api/source?path=README.md')).status(),404,'根目录非白名单文件不能由原文API读取');
    await navigate('#/downloads');
    for(const href of await page.locator('.download-row').evaluateAll(as=>as.map(a=>a.getAttribute('href'))))assert.equal((await context.request.get(base+href)).status(),200,href);

    // 每章和每组实现都在两种窄屏检查；长代码、公式、表格只能在自己的容器内滚动。
    let mobileRoutes=0;
    for(const width of [390,320]){
      await page.setViewportSize({width,height:844});
      for(const route of ['home','courses','api','examples','resources','coverage','library','projects','ecosystem','troubleshoot','saved','downloads','about',...data.lessons.map(c=>c.id),...data.comparisons.map(id=>'compare/'+id)]){
        await navigate('#/'+route);
        const size=await page.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth}));
        assert.ok(size.scroll<=size.w+1,`${width}px overflow ${route}: ${size.scroll}`);mobileRoutes++;
      }
    }
    await navigate('#/home');await page.locator('#menu-button').click();
    assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('menu-open')),true);
    await page.keyboard.press('Escape');assert.equal(await page.locator('#menu-button').getAttribute('aria-expanded'),'false');
    await page.screenshot({path:path.join(qa,'mobile-home.png'),animations:'disabled'});

    // 浏览器损坏或拒绝存储时，阅读、标记和导出仍可使用。
    for(const denied of [false,true]){
      const bad=await browser.newContext();
      await bad.addInitScript(flag=>{if(flag)Object.defineProperty(window,'localStorage',{get(){throw new Error('storage denied')}});else localStorage.setItem('ros2-atlas-v1','{broken')},denied);
      const p=await bad.newPage();p.on('pageerror',e=>errors.push(e.message));await p.goto(base+'#/architecture');
      await p.locator('[data-study=done]').click();assert.equal(await p.locator('[data-study=done]').getAttribute('aria-pressed'),'true');await bad.close();
    }
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    const report={passed:true,chapters:data.lessons.length,comparisons:data.comparisons.length,mobileRoutes,widths:[390,320],externalRequests:external.length,errors};
    await fs.writeFile(path.join(root,'validation-evidence/browser-current-validation.json'),JSON.stringify({checkedAt:'2026-11-07',iteration:'2026-11-07-r10',...report},null,2)+'\n');
    console.log(JSON.stringify(report));
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
