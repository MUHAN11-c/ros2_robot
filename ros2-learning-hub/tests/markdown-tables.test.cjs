/* 单章下载走浏览器库，不能只让Python全文导出通过。 */
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
test('单章Markdown同时保留连续的实测表和API表，并转义单元格分隔符',()=>{
 const sandbox={window:{}};vm.createContext(sandbox);
 vm.runInContext(fs.readFileSync(path.resolve(__dirname,'../dist/reader-library.js'),'utf8'),sandbox);
 const table={title:'实测结果',columns:['输入','单位'],rows:[['a|b','m/s'],['第二行\n继续','s']],caption:'有限输入'};
 const chapter={id:'x',title:'案例',summary:'说明',goals:[],concepts:[],sections:[{title:'实验',tables:[table]}],steps:[],commands:[],expected:[],pitfalls:[],exercises:[],exercise:'问题',exerciseAnswer:'答案',sourceIds:[]};
 const context={D:{apiReferences:[{...table,lessons:['x']}],comparisons:[]},sources:new Map()};
 const markdown=sandbox.window.ReaderLibrary.chapterMarkdown(chapter,context);
 const block='| 输入 | 单位 |\n| --- | --- |\n| a\\|b | m/s |\n| 第二行<br>继续 | s |';
 assert.equal(markdown.split(block).length-1,2);
 assert.ok(!markdown.includes('| 输入 | 单位 |\n\n| ---'));
});
