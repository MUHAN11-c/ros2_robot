const test = require('node:test');
const assert = require('node:assert/strict');
const G = require('../dist/preview/geometry.js');
const near = (a,b) => assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);
const point = (a,b) => a.forEach((x,i)=>near(x,b[i]));
test('二维刚体变换先旋转再平移',()=>{
  point(G.transform2D([1,0],{x:.2,y:.15,angle:90}),[.2,1.15]);
  point(G.transform2D([1,2],{x:0,y:0,angle:0}),[1,2]);
});
test('二维逆变换还原不同姿态下的原始点',()=>{
  for(const angle of [-180,-93,0,47,180]){
    const pose={x:.7,y:-.3,angle};
    point(G.inverse2D(G.transform2D([1.1,-.4],pose),pose),[1.1,-.4]);
  }
});
test('三维旋转遵守右手定则',()=>{
  point(G.rotateZ([1,0,0],90),[0,1,0]);
  point(G.rotateY([1,0,0],90),[0,0,-1]);
});
test('三关节模型的已知姿态',()=>{
  point(G.armPose(0,0,0).wrist,[1.5,0,.4]);
  point(G.armPose(90,0,0).wrist,[0,1.5,.4]);
  point(G.armPose(0,-90,0).wrist,[0,0,1.9]);
});
test('关节旋转保持连杆长度',()=>{
  for(const q of [[20,-35,65],[-140,-70,-30],[160,10,100]]){
    const p=G.armPose(...q);
    near(Math.hypot(...p.elbow.map((x,i)=>x-p.shoulder[i])),.85);
    near(Math.hypot(...p.wrist.map((x,i)=>x-p.elbow[i])),.65);
  }
});
test('三维正交投影的正视和俯视',()=>{
  point(G.project([1,2,3],{yaw:0,pitch:0,scale:1,cx:0,cy:0,target:[0,0,0]}).screen,[1,-3]);
  point(G.project([1,2,3],{yaw:0,pitch:90,scale:1,cx:0,cy:0,target:[0,0,0]}).screen,[1,2]);
});
