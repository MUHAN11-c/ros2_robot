/* Original geometry for the offline instructional diagrams. */
(function(root){
  'use strict';
  const radians=degrees=>degrees*Math.PI/180;
  const add=(a,b)=>a.map((x,i)=>x+b[i]);
  function transform2D(point,pose){
    const c=Math.cos(radians(pose.angle)),s=Math.sin(radians(pose.angle));
    return [c*point[0]-s*point[1]+pose.x,s*point[0]+c*point[1]+pose.y];
  }
  function inverse2D(point,pose){
    return transform2D([point[0]-pose.x,point[1]-pose.y],{x:0,y:0,angle:-pose.angle});
  }
  function rotateY(p,degrees){
    const c=Math.cos(radians(degrees)),s=Math.sin(radians(degrees));
    return [c*p[0]+s*p[2],p[1],-s*p[0]+c*p[2]];
  }
  function rotateZ(p,degrees){
    const c=Math.cos(radians(degrees)),s=Math.sin(radians(degrees));
    return [c*p[0]-s*p[1],s*p[0]+c*p[1],p[2]];
  }
  function armPose(q1,q2,q3){
    const shoulder=[0,0,.4];
    const elbow=add(shoulder,rotateZ(rotateY([.85,0,0],q2),q1));
    const wrist=add(elbow,rotateZ(rotateY([.65,0,0],q2+q3),q1));
    return {shoulder,elbow,wrist};
  }
  function project(point,camera){
    const p=point.map((x,i)=>x-(camera.target?.[i]||0));
    const a=radians(camera.yaw),e=radians(camera.pitch);
    const horizontal=Math.cos(a)*p[0]-Math.sin(a)*p[1];
    const along=Math.sin(a)*p[0]+Math.cos(a)*p[1];
    const vertical=Math.cos(e)*p[2]-Math.sin(e)*along;
    return {screen:[camera.cx+camera.scale*horizontal,camera.cy-camera.scale*vertical],depth:Math.cos(e)*along+Math.sin(e)*p[2]};
  }
  const api={transform2D,inverse2D,rotateY,rotateZ,armPose,project,add};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PreviewGeometry=api;
})(typeof window!=='undefined'?window:globalThis);
