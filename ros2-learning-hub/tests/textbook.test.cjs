const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const target=path.join(__dirname,'../dist/textbook.js');
const T=fs.existsSync(target)?require(target):{};
const lesson={title:'测试章节',summary:'完整正文',sections:[{title:'创建文件',paragraphs:['第一段：`topic`。','<img src=x onerror=alert(1)>'],bullets:['含义一'],codeBlocks:[{label:'node.py',language:'python',type:'complete',code:'print("<ok>")',explanation:'运行后输出一行。'}]}],workedExample:{title:'一次完整实验',scenario:'两个终端。',steps:['先启动发布者','再启动订阅者'],result:'读到消息。'},exercises:[{question:'为何需要spin？',answer:'执行器需要调度回调。'}]};
test('深入正文显示小节、代码解释、完整案例与答案，并转义内容',()=>{
 const html=T.renderExpanded(lesson);
 assert.match(html,/id="deep-0"/);assert.match(html,/创建文件/);assert.match(html,/运行后输出一行/);
 assert.match(html,/一次完整实验/);assert.match(html,/执行器需要调度回调/);
 assert.ok(!html.includes('<img src='));assert.ok(html.includes('&lt;img'));
});
test('导出正文保留完整代码、案例和全部答案',()=>{
 const md=T.expandedMarkdown(lesson);
 assert.ok(md.includes('```python\nprint("<ok>")\n```'));
 assert.match(md,/第一段/);assert.match(md,/再启动订阅者/);assert.match(md,/执行器需要调度回调/);
});
test('已有短章节在无扩展字段时仍可阅读',()=>{
 assert.equal(T.renderExpanded({title:'旧章节'}),'');
 assert.equal(T.expandedMarkdown({title:'旧章节'}),'');
});
