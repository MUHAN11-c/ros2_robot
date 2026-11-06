const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const target = path.join(__dirname, '../dist/logic.js');
const L = fs.existsSync(target) ? require(target) : {};
test('英文包名不区分大小写，并与中文关键词共同匹配', () => {
  const docs = [{id:'a',title:'QoS 通信',text:'rclcpp 可靠性'}, {id:'b',title:'消息',text:'rclpy'}];
  assert.deepEqual(L.search(docs,'RCLCPP 可靠性').map(x=>x.id), ['a']);
});
test('标题命中排在正文命中之前', () => {
  assert.deepEqual(L.search([{id:'body',title:'基础',text:'tf2'}, {id:'title',title:'tf2 坐标',text:''}],'tf2').map(x=>x.id),['title','body']);
});
test('特殊字符是文字；空关键词不搜索整个数据库', () => {
  const docs = [{id:'a',title:'array[0]',text:'<script>'}];
  assert.equal(L.search(docs,'[').length,1);
  assert.equal(L.search(docs,'<script>').length,1);
  assert.equal(L.search(docs,'   ').length,0);
});
test('深链接解析和非法路由安全返回首页',()=>{
  assert.deepEqual(L.parseRoute('#/lesson/qos'),{view:'lesson',id:'qos'});
  assert.deepEqual(L.parseRoute('#/compare/launch'),{view:'compare',id:'launch'});
  assert.deepEqual(L.parseRoute('#/bad/%E0%A4'),{view:'home',id:''});
  assert.deepEqual(L.parseRoute(''),{view:'home',id:''});
});
test('学习进度去重并剔除不存在的章节',()=>{
  const s=L.sanitizeState({done:['a','a','evil'],stars:['b',null],last:'evil'},['a','b']);
  assert.deepEqual(s.done,['a']); assert.deepEqual(s.stars,['b']); assert.equal(s.last,'');
});
test('损坏存储及错误类型降级为可读默认状态',()=>{
  for(const v of [null,[],17,'broken',{done:'a',stars:{},theme:'evil'}]) {
    const s=L.sanitizeState(v,['a']); assert.deepEqual(s.done,[]); assert.equal(s.theme,'light');
  }
});
test('可靠发布能满足尽力订阅，反向不兼容',()=>{
  assert.equal(L.qosCompatible({reliability:'reliable',durability:'volatile'},{reliability:'best_effort',durability:'volatile'}),true);
  assert.equal(L.qosCompatible({reliability:'best_effort',durability:'volatile'},{reliability:'reliable',durability:'volatile'}),false);
});
test('持久性也必须满足订阅请求',()=>{
  assert.equal(L.qosCompatible({reliability:'reliable',durability:'volatile'},{reliability:'reliable',durability:'transient_local'}),false);
  assert.equal(L.qosCompatible({reliability:'reliable',durability:'transient_local'},{reliability:'reliable',durability:'volatile'}),true);
});
