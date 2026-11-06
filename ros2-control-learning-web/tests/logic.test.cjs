const {test} = require('node:test');
const assert = require('node:assert/strict');
const {wheelSpeeds, createProgress, resolveLesson} = require('../logic.js');
const ids = ['start','architecture','cycle','files','diffbot','diagnose','quiz'];

test('DiffBot 将米每秒和弧度每秒转换为正确的左右轮角速度', () => {
  const result = wheelSpeeds(0.7,1,0.1,0.015);
  assert.ok(Math.abs(result.left - 43.3333333333) < 1e-7);
  assert.ok(Math.abs(result.right - 50) < 1e-7);
  assert.deepEqual(wheelSpeeds(0,0,0.1,0.015), {left:0,right:0});
});

test('原地旋转时左右轮方向相反，后退时均为负', () => {
  assert.deepEqual(wheelSpeeds(0,1,0.4,0.1), {left:-2,right:2});
  assert.deepEqual(wheelSpeeds(-0.2,0,0.4,0.1), {left:-2,right:-2});
});

test('无效几何和非有限输入不会生成误导性的计算结果', () => {
  for (const values of [[1,0,0.4,0],[1,0,-0.4,0.1],[NaN,0,0.4,0.1],[1,Infinity,0.4,0.1]]) {
    assert.throws(() => wheelSpeeds(...values), RangeError);
  }
});

test('重复完成与重载保持进度，不保存未知课程', () => {
  const data = new Map();
  const storage = {getItem:key=>data.get(key)??null,setItem:(key,value)=>data.set(key,value)};
  const progress = createProgress(storage,ids);
  progress.complete('cycle'); progress.complete('cycle'); progress.complete('unknown');
  assert.deepEqual(createProgress(storage,ids).get(), ['cycle']);
  progress.reset();
  assert.deepEqual(createProgress(storage,ids).get(), []);
});

test('损坏、过时或包含非法值的进度可恢复', () => {
  for (const value of ['{broken','null','{"version":2,"completed":["cycle"]}','{"version":1,"completed":"cycle"}']) {
    assert.deepEqual(createProgress({getItem:()=>value,setItem(){}},ids).get(), []);
  }
  const progress = createProgress({getItem:()=>'{"version":1,"completed":["cycle","unknown","cycle",null]}',setItem(){}},ids);
  assert.deepEqual(progress.get(),['cycle']);
  const external = progress.get(); external.push('quiz');
  assert.deepEqual(progress.get(),['cycle']);
});

test('浏览器拒绝读写存储时，完成和重置仍然有效', () => {
  const storage = {getItem(){throw new Error('denied')},setItem(){throw new Error('quota')}};
  const progress = createProgress(storage,ids);
  assert.deepEqual(progress.complete('diffbot'),['diffbot']);
  assert.equal(progress.isPersistent(),false);
  assert.deepEqual(progress.reset(),[]);
  assert.deepEqual(createProgress(null,ids).complete('start'),['start']);
});

test('有效 hash 可深链访问，未知或损坏的 hash 回到架构课', () => {
  assert.equal(resolveLesson('#diffbot',ids),'diffbot');
  assert.equal(resolveLesson('#cycle',ids),'cycle');
  for (const hash of ['','#missing','#%E0%A4%A','#<script>']) {
    assert.equal(resolveLesson(hash,ids),'architecture');
  }
});
