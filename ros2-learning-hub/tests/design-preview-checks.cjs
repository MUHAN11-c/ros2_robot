const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/home/mu/.local/lib/python3.10/site-packages/playwright/driver/package');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
(async()=>{
  const root=path.resolve(__dirname,'..'),base='file://'+path.join(root,'dist/layout-preview.html');
  const browser=await chromium.launch({headless:true});
  const context=await browser.newContext({offline:true,viewport:{width:1440,height:1050}});
  const page=await context.newPage(),errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))external.push(r.url())});
  const screenshot=async name=>{await page.locator('.context-figure').first().waitFor({state:'visible'});await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await page.screenshot({path:path.join(root,'.qa','design-'+name+'.png')})};
  const change=async(selector,value)=>{await page.locator(selector).evaluate((el,v)=>{el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}))},String(value));};
  try{
    const metadata=JSON.parse(await fs.readFile(path.join(root,'source/design-figures.json'),'utf8')).figures;
    for(const figure of metadata){
      for(const placement of figure.placements){
        await page.goto(base+'#/'+placement.chapter+'/figure/'+figure.id);
        const image=page.locator('#fig-'+figure.id+' img');await image.waitFor();
        await image.evaluate(el=>el.decode());assert.ok(await image.evaluate(el=>el.naturalWidth>0));
        assert.equal(await image.evaluate(el=>el.closest('.reading-section').id),'part-'+placement.afterSection);
      }
    }
    await page.goto(base+'#/pubsub/figure/pubsub');await page.locator('#fig-pubsub img').evaluate(el=>el.decode());
    await screenshot('flow');
    await page.locator('#fig-pubsub [data-figure-expand]').click();assert.equal(await page.locator('#figure-dialog[open]').count(),1);
    await page.keyboard.press('Escape');
    const code=page.locator('.implementation').first();
    await code.getByRole('tab',{name:'Python / rclpy',exact:true}).click();
    assert.match(await code.locator('[role=tabpanel]:visible').innerText(),/self.create_publisher/);
    await code.getByRole('button',{name:'并排对照',exact:true}).click();assert.equal(await code.locator('[role=tabpanel]:visible').count(),2);
    await page.goto(base+'#/launch');assert.equal(await page.getByRole('tab').count(),3);
    await page.getByRole('tab',{name:'YAML',exact:true}).click();assert.match(await page.locator('[role=tabpanel]:visible').innerText(),/launch:/);
    await page.goto(base+'#/tf2/figure/tf2-transform');
    await page.locator('[data-transform-preset=quarter]').click();
    assert.equal(await page.locator('[data-transform-result]').innerText(),'p_B = [0.000, 1.000] m');
    await page.locator('[data-transform-preset=translation]').click();
    assert.equal(await page.locator('[data-transform-result]').innerText(),'p_B = [1.800, 0.400] m');
    await change('[data-param=angle]',90);
    assert.equal(await page.locator('[data-transform-result]').innerText(),'p_B = [0.800, 1.400] m');
    await page.locator('[data-lab-reset]').click();await screenshot('2d');
    await page.goto(base+'#/eco-model-rviz/figure/robot-model');
    const position=await page.locator('[data-robot-result]').innerText();
    const initial=await page.locator('.robot-stage').innerHTML();
    await page.locator('.robot-stage').focus();await page.keyboard.press('ArrowRight');
    assert.notEqual(await page.locator('.robot-stage').innerHTML(),initial);
    assert.equal(await page.locator('[data-robot-result]').innerText(),position,'camera rotation must not alter robot pose');
    await change('[data-param=q1]',90);assert.notEqual(await page.locator('[data-robot-result]').innerText(),position);
    const bounds=await page.locator('.robot-stage').boundingBox();
    const beforeDrag=await page.locator('.robot-stage').innerHTML();
    await page.mouse.move(bounds.x+bounds.width*.5,bounds.y+bounds.height*.5);await page.mouse.down();await page.mouse.move(bounds.x+bounds.width*.5+70,bounds.y+bounds.height*.5+20,{steps:4});await page.mouse.up();
    assert.notEqual(await page.locator('.robot-stage').innerHTML(),beforeDrag);
    await page.locator('[data-lab-reset]').click();assert.equal(await page.locator('[data-robot-result]').innerText(),position);
    await screenshot('3d');
    await page.locator('[data-figure-expand]').click();
    const duplicates=await page.evaluate(()=>{const seen=new Set();return [...document.querySelectorAll('[id]')].filter(el=>seen.has(el.id)||!seen.add(el.id)).map(el=>el.id)});
    assert.deepEqual(duplicates,[]);await page.keyboard.press('Escape');
    for(const width of [390,320]){
      await page.setViewportSize({width,height:844});
      for(const [chapter,id]of [['architecture','architecture'],['actions','action'],['tf2','tf2-transform'],['eco-model-rviz','robot-model'],['eco-control-framework','control'],['eco-nav2-stack','nav2']]){
        await page.goto(base+'#/'+chapter+'/figure/'+id);
        const size=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
        assert.ok(size.scroll<=size.width+1,`${chapter} ${JSON.stringify(size)}`);
      }
    }
    await page.setViewportSize({width:390,height:844});await page.goto(base+'#/tf2/figure/tf2-transform');await screenshot('mobile');
    await page.locator('#design-trigger').click();assert.equal(await page.locator('#design-dialog[open]').count(),1);
    await page.locator('#design-dialog a[href="#/eco-model-rviz/figure/robot-model"]').click();await page.locator('#fig-robot-model').waitFor();
    assert.equal(await page.locator('#design-dialog[open]').count(),0);
    await page.locator('#menu-button').click();await page.locator('#search-trigger').click();await page.locator('#search-input').fill('坐标');assert.ok(await page.locator('.search-result').count()>0);await page.keyboard.press('Escape');
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    console.log(JSON.stringify({passed:true,staticFigures:metadata.length,contextPlacements:metadata.reduce((n,f)=>n+f.placements.length,0),interactiveFigures:2,offlineRequests:external.length,mobileWidths:[390,320],errors}));
  }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
