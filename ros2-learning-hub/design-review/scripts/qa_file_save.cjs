/* 实测本地教材文件保存：仅使用指定临时副本，测试内容不写进真实教材。
 * 输入：副本根目录、已启用 --editable 的本机端口；输出：真实文件/重建/浏览器检查报告。
 * 原生目录选择窗不自动点击；句柄分支用 Chromium 的隔离文件系统验证读写。
 */
const {chromium}=require('../../tests/browser-runtime.cjs');
const F=require('../file-store.js');
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');
const {pathToFileURL}=require('node:url'),{execFile}=require('node:child_process'),{promisify}=require('node:util');
const ROOT=path.resolve(__dirname,'..'),BASE=process.env.TEXTBOOK_TEST_URL||'http://127.0.0.1:8768';
const WORK=path.resolve(process.env.TEXTBOOK_TEST_ROOT||'/tmp/missing');
assert.ok(WORK.includes('/ros2-textbook-save-')&&WORK!==path.resolve(ROOT,'..'),'仅允许独立临时教材副本');
const registryFile=path.join(WORK,'source/local-edits.json'),checks=[],errors=[];
const read=relative=>fs.readFile(path.join(WORK,relative),'utf8');
const registry=async()=>JSON.parse(await read('source/local-edits.json'));
const readOnlyFiles=['dist/content.js','dist/book.html','source/core.json'];
const saveButton=page=>page.locator('[data-action=save-textbook]');
async function saved(page){await page.waitForFunction(()=>document.getElementById('file-save-status')?.textContent.startsWith('已写入教材文件'));}
async function edit(page,id,text){await page.goto(BASE+'/design-review/#/'+id);await page.locator('#view-mode').selectOption('edit');await page.locator('#overview p').first().fill(text);}
(async()=>{
  const originalFiles=await Promise.all(readOnlyFiles.map(read));
  const browser=await chromium.launch({headless:true,args:['--no-sandbox']});let result;
  try{
    const context=await browser.newContext({viewport:{width:1440,height:1040},acceptDownloads:true});
    const page=await context.newPage(),staleContext=await browser.newContext(),stale=await staleContext.newPage();
    for(const p of [page,stale])p.on('pageerror',e=>errors.push(e.message));
    await stale.goto(BASE+'/design-review/#/architecture');
    const previous=(await registry()).chapters.architecture;
    let payload;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/textbook/save'))payload=r.postDataJSON();});
    const first='文件直存验收：ROS 2 节点可通过通信图理解。';
    await edit(page,'architecture',first);await page.keyboard.press('Control+s');await saved(page);
    const firstRecord=(await registry()).chapters.architecture,base='backups/local-edits/original/architecture/';
    const originals=await Promise.all(['source.json','chapter.md','chapter.html'].map(file=>read(base+file)));
    assert.deepEqual(JSON.parse(originals[0]),payload.baseChapter);assert.ok(!originals[1].includes(first));
    assert.ok((await read('dist/chapters/architecture.md')).includes(first));assert.ok((await read('dist/chapters/architecture.html')).includes(first));
    if(previous)assert.equal(JSON.parse(await read(`backups/local-edits/history/architecture/${previous.revision}.json`)).revision,previous.revision);
    assert.deepEqual(await Promise.all(readOnlyFiles.map(read)),originalFiles);
    checks.push('Ctrl+S 真实写入章节HTML、Markdown和源修订，磁盘原教材与章节原文独立保存');

    await stale.locator('#view-mode').selectOption('edit');await stale.locator('#overview p').first().fill('过期页面不得覆盖新保存');await saveButton(stale).click();await stale.waitForFunction(()=>document.getElementById('file-save-status').textContent.includes('其他页面修改'));
    assert.equal((await registry()).chapters.architecture.revision,firstRecord.revision);await staleContext.close();checks.push('过期页面保存被拒绝，较新章节文件保留');

    const second='文件直存第二版：通信图、节点与接口。';
    const sectionTitle='节点、话题和服务如何连接';
    await page.locator('#overview p').first().fill(second);
    await page.locator('#part-0 h2').fill(sectionTitle);
    await saveButton(page).click();await saved(page);
    const secondRegistry=await registry(),secondRecord=secondRegistry.chapters.architecture;
    assert.notEqual(secondRecord.revision,firstRecord.revision);assert.equal(JSON.parse(await read(`backups/local-edits/history/architecture/${firstRecord.revision}.json`)).document.markdown,firstRecord.document.markdown);
    assert.deepEqual(await Promise.all(['source.json','chapter.md','chapter.html'].map(file=>read(base+file))),originals);
    await saveButton(page).click();await saved(page);assert.equal((await registry()).revision,secondRegistry.revision);checks.push('二次保存保留上一版，原文备份逐字节相同，重复保存不新增版本');

    const stored=await read('source/local-edits.json'),token=await page.evaluate(()=>window.NarukamiEditorService.token);
    const send=(origin,value)=>fetch(BASE+'/api/textbook/save',{method:'POST',headers:{Origin:origin,'X-Textbook-Token':token,'Content-Type':'application/json'},body:JSON.stringify(value)});
    assert.equal((await send('http://other.invalid',payload)).status,403);
    assert.equal((await send(BASE,{...payload,chapterId:'../core'})).status,409);
    assert.equal((await send(BASE,{...payload,document:{...payload.document,html:'<img src="https://example.invalid/unsafe.png">'}})).status,409);
    assert.equal(await read('source/local-edits.json'),stored);checks.push('异源、越界章节和非本地图片请求不写文件');

    // JS目录写入协议使用真实磁盘适配器，注入一次末尾提交失败，检验回滚顺序与备份。
    const outputPaths=['dist/chapters/architecture.md','dist/chapters/architecture.html','source/local-edits.json','dist/local-edits.js'];
    const before=await Promise.all(outputPaths.map(read));let injected=false;
    const io={read:async file=>{try{return await read(file);}catch(e){if(e.code==='ENOENT')return null;throw e;}},write:async(file,text)=>{if(file==='dist/local-edits.js'&&!injected){injected=true;throw new Error('验收注入的写入失败');}const target=path.join(WORK,file);await fs.mkdir(path.dirname(target),{recursive:true});await fs.writeFile(target,text);},remove:file=>fs.rm(path.join(WORK,file),{force:true})};
    const changed={...payload,expectedRevision:secondRecord.revision,document:{...payload.document,markdown:payload.document.markdown+'\n待回滚的测试文字\n'}};
    await assert.rejects(F.commit(io,changed),/验收注入/);assert.ok(injected);assert.deepEqual(await Promise.all(outputPaths.map(read)),before);
    const failBackup={...io,read:async file=>file===base+'chapter.md'?null:io.read(file),write:async(file,text)=>{if(file===base+'chapter.md')throw new Error('验收注入的备份失败');return io.write(file,text);}};
    await assert.rejects(F.commit(failBackup,changed),/备份失败/);assert.deepEqual(await Promise.all(outputPaths.map(read)),before);
    checks.push('目录写入协议与本机服务文件兼容，末尾写入失败回滚；备份失败不改教材');

    const fresh=await browser.newContext({viewport:{width:390,height:844},offline:true});const file=await fresh.newPage();file.on('pageerror',e=>errors.push(e.message));
    await file.goto(pathToFileURL(path.join(WORK,'design-review/index.html')).href+'#/architecture');assert.equal(await file.locator('#overview p').first().textContent(),second);assert.ok((await file.locator('.draft-notice').textContent()).includes('已保存的本地教材'));
    const formal=await fresh.newPage();
    await formal.goto(pathToFileURL(path.join(WORK,'dist/index.html')).href+'#/architecture/section/part-0');
    await formal.locator('#part-0.matched-section').waitFor();
    assert.equal(await formal.locator('#overview p').first().textContent(),second);
    for(const reader of [file,formal]){
      assert.match(await reader.locator('#part-0 h2').textContent(),new RegExp(sectionTitle));
      assert.equal(await reader.locator('.tree-section-list a[data-section-id=part-0] .outline-label').textContent(),sectionTitle);
      assert.equal(await reader.locator('#part-0 h2').getAttribute('data-section-number'),'1.1');
    }
    assert.ok(await file.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await fresh.close();checks.push('空白浏览器断网读取磁盘修订，两个入口的修改后标题、目录、编号与原锚点均一致');

    // 用真实浏览器目录句柄检查文件流，不自动化用户的原生选择目录窗口。
    const handles=await browser.newContext();const handlePage=await handles.newPage();handlePage.on('pageerror',e=>errors.push(e.message));
    await handlePage.goto(BASE+'/design-review/#/tf2');
    await handlePage.evaluate(async baseText=>{const dir=await navigator.storage.getDirectory();const io=window.NarukamiFileStore.directoryIO(dir);await io.write('dist/content.js',baseText);window.NarukamiEditorService=null;window.showDirectoryPicker=async()=>dir;},originalFiles[0]);
    await handlePage.locator('#view-mode').selectOption('edit');await handlePage.locator('#overview p').first().fill('目录句柄文件写入验收。');await saveButton(handlePage).click();await saved(handlePage);
    assert.ok(await handlePage.evaluate(async()=>{const io=window.NarukamiFileStore.directoryIO(await navigator.storage.getDirectory());return (await io.read('dist/chapters/tf2.md')).includes('目录句柄文件写入验收')&&!!(await io.read('backups/local-edits/original/tf2/chapter.md'));}));await handles.close();checks.push('Chromium 隔离目录句柄实际写入与原文备份，未自动化原生目录选择');

    await edit(page,'math-rigid','公式与图解的文件保存验证。');await saveButton(page).click();await saved(page);
    assert.ok((await read('dist/chapters/math-rigid.html')).includes('<math'));assert.ok((await read('dist/chapters/math-rigid.html')).includes('<img'));
    const sourceBeforeBuild=await read('source/local-edits.json');const build=await promisify(execFile)('python3',[path.join(WORK,'scripts/build_content.py'),'--require-full'],{cwd:WORK,timeout:30000});
    assert.equal(await read('source/local-edits.json'),sourceBeforeBuild);
    assert.ok((await read('dist/downloads/ros2-learning-guide.md')).includes(second));
    const book=await read('dist/book.html');assert.ok(book.includes(second));assert.ok(book.includes('公式与图解的文件保存验证'));assert.ok(book.includes('data:image/svg+xml;base64,'));
    const runtime=await read('dist/local-edits.js');assert.ok(runtime.includes(second));
    checks.push('实际重建保留源修订，并同步全文Markdown和无脚本连续版的公式与内嵌图解');
    assert.deepEqual(errors,[]);
    result={passed:true,scope:'独立副本实际文件保存、备份、断网和重建',checks,errors,fixtureRoot:WORK,build:JSON.parse(build.stdout.trim().split('\n').at(-1))};
  }catch(error){result={passed:false,checks,errors,error:error.stack,fixtureRoot:WORK};throw error;}finally{await fs.writeFile(path.join(ROOT,'validation/file-save-report.json'),JSON.stringify(result,null,2)+'\n');await browser.close();}
  console.log(JSON.stringify({passed:result.passed,checks:checks.length,fixtureRoot:WORK}));
})().catch(error=>{console.error(error);process.exitCode=1;});
