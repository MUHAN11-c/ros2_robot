async (page) => {
  const base='http://127.0.0.1:8765/';
  const passed=[],errors=[];
  const check=(condition,message)=>{if(!condition)throw new Error(message);};
  const onError=error=>errors.push(error.message);
  page.on('pageerror',onError);
  page.setDefaultTimeout(5000);
  const titles={start:'从零开始',architecture:'读懂系统架构',cycle:'跟随一个控制周期',files:'认识四类关键文件',diffbot:'跑通 DiffBot 示例',diagnose:'生命周期与排错',quiz:'检查你的理解'};
  const route=async id=>{await page.evaluate(id=>{location.hash=id;},id);await page.locator('#lesson-title').filter({hasText:titles[id]}).waitFor();};
  try {
    await page.setViewportSize({width:1536,height:1000});
    await page.goto(base+'?qa='+Date.now()+'#architecture');
    await page.evaluate(()=>localStorage.clear());
    await page.reload();
    check(await page.locator('.nav-link').count()===7,'课程导航应含 7 个单元');
    check(await page.locator('[data-node]').count()===12,'架构应含 12 个可选节点');
    await page.locator('[data-node="state"]').focus();await page.keyboard.press('Enter');
    check(await page.locator('#component-detail h2').innerText()==='状态接口','键盘选择应更新状态接口说明');
    check(await page.locator('[data-node="state"]').getAttribute('aria-pressed')==='true','选中节点应向辅助技术报告状态');
    await page.locator('[data-mode="command"]').click();
    check(await page.locator('#component-detail h2').innerText()==='命令接口','命令视图应显示对应接口说明');
    passed.push('双语架构图、键盘节点选择与视图切换');

    await route('files');
    await page.locator('[data-file="yaml"]').click();
    check((await page.locator('#file-content').innerText()).includes('wheel_radius'),'YAML 面板应显示实际参数');
    await page.locator('[data-file="yaml"]').focus();await page.keyboard.press('ArrowRight');
    check(await page.locator('[role="tab"][aria-selected="true"]').getAttribute('data-file')==='cpp','方向键应切换到下一文件');
    await page.context().grantPermissions(['clipboard-read','clipboard-write'],{origin:'http://127.0.0.1:8765'});
    await page.locator('[data-file="yaml"]').click();await page.locator('[data-copy="yaml"]').click();
    await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('代码已复制'));
    const copied=await page.evaluate(()=>navigator.clipboard.readText());
    check(copied.includes('left_wheel_names')&&copied.includes('open_loop: true'),'复制内容应为当前 YAML 原文');
    passed.push('文件切换、键盘选项卡、实际剪贴板复制');

    await route('cycle');
    check((await page.locator('#left-wheel-value').innerText())==='18.33','默认左轮角速度应为 18.33');
    await page.locator('#linear-speed').evaluate(el=>{el.value='0.7';el.dispatchEvent(new Event('input',{bubbles:true}));});
    await page.locator('#angular-speed').evaluate(el=>{el.value='1';el.dispatchEvent(new Event('input',{bubbles:true}));});
    check((await page.locator('#left-wheel-value').innerText())==='43.33','调整速度后左轮应为 43.33');
    check((await page.locator('#right-wheel-value').innerText())==='50.00','调整速度后右轮应为 50.00');
    await page.locator('[data-action="step"]').click();
    check(await page.locator('.cycle-stage.active').getAttribute('data-stage')==='1','单步应进入 update');
    await page.locator('#cycle-play').click();
    await page.waitForFunction(()=>document.querySelector('.cycle-stage.active').dataset.stage==='2');
    await page.locator('#cycle-play').click();
    const paused=await page.locator('#cycle-count').innerText();
    await page.waitForTimeout(1750);
    check(await page.locator('#cycle-count').innerText()===paused,'暂停后循环不得继续推进');
    await page.locator('#cycle-play').click();await route('files');await page.waitForTimeout(1750);await route('cycle');
    check(await page.locator('#cycle-count').innerText()===paused,'离开课程后应清除播放计时器');
    await page.locator('[data-action="complete"]').click();await page.reload();
    check(await page.locator('#progress-fraction').innerText()==='1 / 7','完成进度应在刷新后保留');
    passed.push('差速数值、单步、播放暂停、离页计时清理、进度持久化');

    await route('quiz');
    await page.locator('[data-question="0"][data-answer="0"]').click();
    check(await page.locator('#question-0 .wrong').count()===1,'错误答案应反馈错误');
    check(await page.locator('#complete-lesson').isDisabled(),'未通过全部自测不能完成自测单元');
    for(const [i,j] of [1,1,0,1,1,1,1].entries())await page.locator(`[data-question="${i}"][data-answer="${j}"]`).click();
    check((await page.locator('#quiz-summary strong').innerText()).includes('7'),'全部答对后应显示 7 分');
    check(await page.locator('#complete-lesson').isEnabled(),'答对全部题目后应能完成');
    await page.locator('#complete-lesson').click();
    check(await page.locator('#progress-fraction').innerText()==='2 / 7','自测完成应计入进度');
    await page.locator('[data-action="retry-quiz"]').click();
    check(await page.locator('.quiz-feedback').count()===0,'重新自测应清除本轮反馈');
    passed.push('测验错误反馈、改答、完成门槛与重新自测');

    await page.keyboard.press('/');await page.locator('#search-input').fill('System');
    await page.locator('[data-result-node="system"]').click();
    check(await page.locator('#component-detail h2').innerText()==='系统组件','搜索英文术语应能定位组件');
    await page.locator('.sidebar-resource').click();
    check(await page.locator('#sources-dialog .source-link').count()>=15,'应展示可访问的具体官方参考资料');
    await page.locator('[data-close="sources-dialog"]').click();
    await route('start');await route('files');await page.goBack();
    await page.waitForFunction(()=>location.hash==='#start');
    check(await page.locator('#lesson-title').innerText()==='从零开始','浏览器后退应同步课程');
    await page.goForward();await page.waitForFunction(()=>location.hash==='#files');
    await page.evaluate(()=>{location.hash='%E0%A4%A';});await page.waitForFunction(()=>location.hash==='#architecture');
    check(await page.locator('#lesson-title').innerText()==='读懂系统架构','损坏 hash 应回到合法课程');
    passed.push('中英文搜索、官方来源、前进后退、损坏路由恢复');

    await page.setViewportSize({width:390,height:844});
    await page.locator('.mobile-menu').click();
    check(await page.locator('#sidebar').evaluate(el=>el.classList.contains('open')),'手机菜单应展开');
    await page.locator('.brand').focus();await page.keyboard.press('Shift+Tab');
    check(await page.evaluate(()=>document.activeElement.dataset.action)==='reset','手机菜单应约束键盘焦点');
    await page.locator('.nav-link[href="#architecture"]').click();
    check(await page.locator('#sidebar').evaluate(el=>el.inert),'点击当前课程也应关闭手机导航');
    const diagramScroll=await page.locator('.diagram-scroll').evaluate(el=>({client:el.clientWidth,scroll:el.scrollWidth}));
    check(diagramScroll.scroll>diagramScroll.client,'手机架构图应可在自身容器横向滚动');
    for(const width of [390,320]){
      await page.setViewportSize({width,height:844});
      for(const id of Object.keys(titles)){
        await route(id);
        const dimensions=await page.evaluate(()=>({width:innerWidth,content:document.documentElement.scrollWidth}));
        check(dimensions.content<=dimensions.width,`${width}px 下 ${id} 页面不应整体横向溢出：${dimensions.content}`);
      }
    }
    passed.push('390/320 像素七章布局、图内滚动、折叠菜单与焦点');

    await page.evaluate(()=>localStorage.setItem('ros2-control-learning:v1','{broken'));await page.reload();
    check(await page.locator('#progress-fraction').innerText()==='0 / 7','损坏存储应恢复空进度');
    const privatePage=await page.context().newPage();
    try{
      await privatePage.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new Error('denied')}}));
      await privatePage.goto(base+'#start');await privatePage.locator('#complete-lesson').click();
      check(await privatePage.locator('#progress-fraction').innerText()==='1 / 7','拒绝存储时仍应能在会话中学习');
    }finally{await privatePage.close();}
    passed.push('损坏或拒绝存储时的容错');
    check(errors.length===0,'不应有页面运行错误：'+errors.join('; '));
    await page.setViewportSize({width:1536,height:1000});await route('architecture');
    return {passed,errors};
  } finally {page.off('pageerror',onError);}
}
