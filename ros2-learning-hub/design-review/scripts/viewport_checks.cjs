/* 回归实际发现的视口裁切：只调整视图，参数与几何结果仍由原教学模型计算。 */
const {chromium}=require('../../tests/browser-runtime.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..');
(async()=>{
  const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
  try{
    const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8767/design-review/#/eco-model-rviz/figure/robot-model?open=1');await page.locator('.lab-body').waitFor();
    const model=await page.evaluate(()=>{
      const cases=[];
      for(const q1 of [-150,0,150])for(const q2 of [-80,0,20])for(const q3 of [-100,0,100]){
        for(const [key,value]of Object.entries({q1,q2,q3})){const el=document.querySelector('[data-param="'+key+'"]');el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));}
        for(const view of ['front','top','iso']){
          document.querySelector('[data-view="'+view+'"]').click();
          const joints=[...document.querySelectorAll('.lab-plot circle')].map(c=>[Number(c.getAttribute('cx')),Number(c.getAttribute('cy'))]);
          cases.push({q1,q2,q3,view,joints,within:joints.every(([x,y])=>x>=12&&x<=708&&y>=12&&y<=350)});
        }
      }
      return cases;
    });
    assert.equal(model.length,81);assert.equal(model.filter(c=>!c.within).length,0);
    await page.evaluate(()=>{location.hash='#/tf2/figure/tf2-transform?open=1';});await page.locator('[data-param="angle"]').waitFor();
    const transform=await page.evaluate(()=>{
      const cases=[];for(const x of [-.8,1.4])for(const y of [-.4,1.2])for(const angle of [-180,-90,0,90,180]){
        for(const [key,value]of Object.entries({x,y,angle})){const el=document.querySelector('[data-param="'+key+'"]');el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));}
        const points=[...document.querySelectorAll('.lab-plot circle')].map(c=>[Number(c.getAttribute('cx')),Number(c.getAttribute('cy'))]);
        cases.push({x,y,angle,points,within:points.every(([px,py])=>Number.isFinite(px)&&Number.isFinite(py)&&px>=9&&px<=711&&py>=9&&py<=340)});
      }return cases;
    });
    assert.equal(transform.length,20);assert.equal(transform.filter(c=>!c.within).length,0);assert.deepEqual(errors,[]);
    const report={passed:true,scope:'教学SVG的有限视口样本，非全部连续姿态或物理模型验收',previousFinding:'初版固定相机81样本有31样本关节超出取景范围；改为按投影包围范围居中缩放。',modelCases:model,transformCases:transform,errors};
    await fs.writeFile(path.join(ROOT,'validation/viewport-report.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({passed:true,modelCases:model.length,transformCases:transform.length}));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
