/* Contextual diagrams for the design review, with no network or rendering dependency. */
(() => {
  'use strict';
  const G=window.PreviewGeometry;
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=(x,n=2)=>(Math.abs(x)<.00001?0:x).toFixed(n);
  const point=p=>p.map(x=>fmt(x)).join(',');
  const palette={x:'#b16d4e',y:'#398465',z:'#587fa6',point:'#b97c42'};
  const arrow=(id,color)=>`<marker id="${id}" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill="${color}"/></marker>`;
  const label=(x,y,text,color='#66786e',size=15)=>`<text x="${fmt(x)}" y="${fmt(y)}" fill="${color}" font-size="${size}">${esc(text)}</text>`;
  const line=(a,b,color,width=1.5,extra='')=>`<line x1="${fmt(a[0])}" y1="${fmt(a[1])}" x2="${fmt(b[0])}" y2="${fmt(b[1])}" stroke="${color}" stroke-width="${width}" ${extra}/>`;
  const slider=(name,title,min,max,step,value,unit)=>`<label class="lab-control"><span>${title}<output data-output="${name}">${value}${unit}</output></span><input type="range" data-param="${name}" min="${min}" max="${max}" step="${step}" value="${value}" aria-label="${title}"><span class="range-ends"><span>${min}${unit}</span><span>${max}${unit}</span></span></label>`;

  function frame(id,title,kind,body,caption,number,interactive=false){
    return `<figure class="context-figure ${interactive?'interactive-figure':''}" id="fig-${id}" data-figure-id="${id}"><div class="figure-heading"><div><span class="figure-kind">${kind}</span><h3>${esc(title)}</h3></div><div class="figure-tools">${interactive?'<button data-lab-reset>复位</button>':''}<button data-figure-expand aria-label="放大 ${esc(title)}">放大 ↗</button></div></div>${body}<figcaption><span class="figure-number">图 ${number}</span>${esc(caption)}</figcaption></figure>`;
  }

  function staticFigure(item,number){
    return frame(item.id,item.title,item.kind,`<div class="figure-static"><img src="${esc(item.file)}" alt="${esc(item.alt)}" decoding="async"></div>`,item.caption,number);
  }

  function transformFigure(number){
    return frame('tf2-transform','同一个点，在两个坐标系中是什么坐标？','二维 · 交互图',`<div class="lab-stage tf-stage" role="img" aria-label="二维坐标变换图"></div><div class="lab-result"><span><i class="legend-dot source-dot"></i>雷达坐标 <code>p_L = [1, 0] m</code></span><span><i class="legend-dot world-dot"></i>车体坐标 <output data-transform-result></output></span></div><div class="lab-controls">${slider('x','平移 x',-.8,1.4,.05,.8,' m')}${slider('y','平移 y',-.4,1.2,.05,.4,' m')}${slider('angle','旋转 θ',-180,180,1,30,'°')}</div><div class="lab-bottom"><code>p_B = R(θ) · p_L + t</code><div class="lab-presets"><button data-transform-preset="translation">只看平移</button><button data-transform-preset="quarter">旋转 90°</button></div></div>`,'橙色坐标轴随雷达安装姿态变化，蓝色点表示它观测到的同一个点在车体中的位置。先旋转再平移；图中只展示平面刚体变换，不涉及时间缓存。试着将旋转设为 90°，再检查结果。',number,true);
  }

  function robotFigure(number){
    return frame('robot-model','从 link 与 joint，看懂机器人的三维结构','三维 · 可旋转模型',`<div class="model-toolbar"><span>拖动旋转 · 键盘方向键调整视角</span><div class="lab-presets"><button data-camera="iso" aria-pressed="true">斜视</button><button data-camera="front" aria-pressed="false">正视</button><button data-camera="top" aria-pressed="false">俯视</button></div></div><div class="lab-stage robot-stage" tabindex="0" role="img" aria-label="可旋转的三维关节模型。用方向键调整视角，Home 复位视角；下方滑块调整关节角。"></div><div class="lab-result robot-result"><span>末端位置 <output data-robot-result></output></span><label><input type="checkbox" data-model-frames>显示连杆坐标系</label></div><div class="lab-controls">${slider('q1','底座 q₁ · Z 轴',-150,150,1,25,'°')}${slider('q2','肩关节 q₂ · Y 轴',-80,20,1,-40,'°')}${slider('q3','肘关节 q₃ · Y 轴',-100,100,1,70,'°')}</div><div class="lab-bottom"><span class="axis-legend"><b class="axis-x">X</b><b class="axis-y">Y</b><b class="axis-z">Z</b>右手坐标系</span><span>正交投影 · 单位 m</span></div>`,'连杆是刚体，关节规定父子连杆的相对运动。旋转视角不会改变模型姿态；调整关节角才会改变末端位置。本图是三关节几何教学模型，使用局部关节轴和右手定则，不包含碰撞检测、物理仿真或 ROS 连接。',number,true);
  }

  function renderTransform(el){
    const pose=Object.fromEntries([...el.querySelectorAll('[data-param]')].map(input=>[input.dataset.param,Number(input.value)]));
    const compact=el.getBoundingClientRect().width<560;
    const width=compact?360:720,height=compact?310:390;
    const ox=compact?150:260,oy=compact?175:245,unit=compact?68:92;
    const pixel=p=>[ox+p[0]*unit,oy-p[1]*unit];
    const origin=pixel([0,0]),sensor=pixel([pose.x,pose.y]),p=G.transform2D([1,0],pose),out=pixel(p);
    let svg=`<svg class="lab-svg" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="p_B等于旋转后的p_L加平移"><defs>${arrow('tf-base','#8b9b92')}${arrow('tf-source','#bc8552')}</defs><rect width="${width}" height="${height}" fill="#fafcfb"/>`;
    for(let x=compact?14:76;x<=(compact?354:628);x+=unit/2)svg+=line([x,compact?5:32],[x,compact?278:358],'#e8efea',1);
    for(let y=compact?5:61;y<=(compact?277:337);y+=unit/2)svg+=line([compact?14:76,y],[compact?354:628,y],'#e8efea',1);
    svg+=line([compact?18:95,origin[1]],[compact?340:610,origin[1]],'#b3c1b8',1.5,'marker-end="url(#tf-base)"');
    svg+=line([origin[0],compact?280:350],[origin[0],compact?10:40],'#b3c1b8',1.5,'marker-end="url(#tf-base)"');
    svg+=label(compact?312:606,origin[1]+24,'x_B','#6c8174')+label(origin[0]+13,compact?21:47,'y_B','#6c8174');
    svg+=label(origin[0]-36,origin[1]+23,'B','#6c8174',16);
    svg+=line(origin,sensor,'#bdbcb0',1.8,'stroke-dasharray="5 5"');
    svg+=label((origin[0]+sensor[0])/2-16,(origin[1]+sensor[1])/2-8,'t','#9a9483',18);
    const xAxis=pixel(G.transform2D([.72,0],pose)),yAxis=pixel(G.transform2D([0,.72],pose));
    svg+=line(sensor,xAxis,'#bc8552',2.2,'marker-end="url(#tf-source)"')+line(sensor,yAxis,'#bc8552',2.2,'marker-end="url(#tf-source)"');
    svg+=label(xAxis[0]+8,xAxis[1]+7,'x_L','#a86f3b')+label(yAxis[0]+8,yAxis[1]-6,'y_L','#a86f3b');
    svg+=`<circle cx="${sensor[0]}" cy="${sensor[1]}" r="5" fill="#bc8552"/>`+label(sensor[0]-22,sensor[1]+23,'L','#a86f3b',16);
    svg+=line(sensor,out,'#be945c',1.7,'stroke-dasharray="5 4"');
    svg+=line(out,[out[0],origin[1]],'#86a2b5',1,'stroke-dasharray="3 5"')+line(out,[origin[0],out[1]],'#86a2b5',1,'stroke-dasharray="3 5"');
    svg+=`<circle cx="${out[0]}" cy="${out[1]}" r="8" fill="#5c829c" stroke="white" stroke-width="3"/>`+label(compact?Math.min(width-78,out[0]+13):out[0]+15,Math.max(23,out[1]-13),'观测点 P','#4c748c',compact?13:16);
    const arc=[];for(let i=0;i<=30;i++){const a=pose.angle*i/30*Math.PI/180;arc.push(pixel([pose.x+.35*Math.cos(a),pose.y+.35*Math.sin(a)]))}
    if(Math.abs(pose.angle)>8)svg+=`<polyline points="${arc.map(point).join(' ')}" fill="none" stroke="#cba778" stroke-width="1.5"/>`;
    svg+=label(compact?14:95,compact?299:32,'base_link → laser','#7b8d80',compact?10:14)+label(compact?245:503,compact?299:370,'1 格 = 0.5 m','#89998e',compact?10:13)+'</svg>';
    el.querySelector('.lab-stage').innerHTML=svg;
    el.querySelector('[data-transform-result]').textContent=`p_B = [${fmt(p[0],3)}, ${fmt(p[1],3)}] m`;
    for(const [key,value]of Object.entries(pose))el.querySelector(`[data-output="${key}"]`).textContent=fmt(value,key==='angle'?0:2)+(key==='angle'?'°':' m');
  }

  const subtract=(a,b)=>a.map((x,i)=>x-b[i]);
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const scale=(a,s)=>a.map(x=>x*s);
  const norm=a=>scale(a,1/Math.hypot(...a));
  function beam(a,b,width){
    const direction=norm(subtract(b,a));let u=cross(direction,[0,0,1]);
    if(Math.hypot(...u)<.0001)u=cross(direction,[0,1,0]);
    u=scale(norm(u),width/2);const v=scale(norm(cross(direction,u)),width/2);
    return [a,b].flatMap(p=>[[-1,-1],[1,-1],[1,1],[-1,1]].map(([su,sv])=>G.add(p,G.add(scale(u,su),scale(v,sv)))));
  }
  function cube(a,b){return [[a[0],a[1],a[2]],[b[0],a[1],a[2]],[b[0],b[1],a[2]],[a[0],b[1],a[2]],[a[0],a[1],b[2]],[b[0],a[1],b[2]],[b[0],b[1],b[2]],[a[0],b[1],b[2]]]}
  function mountRobot(el){
    const initial={yaw:-30,pitch:24,scale:215,cx:345,cy:210,target:[.42,0,.65]};
    let camera={...initial},drag=null;
    const stage=el.querySelector('.robot-stage');
    const faceIndices=[[0,1,2,3],[4,5,6,7],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0]];
    function draw(){
      const q=[...el.querySelectorAll('[data-param]')].map(x=>Number(x.value));
      const pose=G.armPose(...q),proj=p=>G.project(p,camera),screen=p=>proj(p).screen;
      const faces=[];
      function solid(vertices,colors){faceIndices.forEach((indices,i)=>faces.push({points:indices.map(j=>screen(vertices[j])),depth:indices.reduce((v,j)=>v+proj(vertices[j]).depth,0)/4,fill:colors[i%colors.length]}))}
      solid(cube([-.2,-.2,0],[.2,.2,.10]),['#cad7ce','#e3ebe5','#aebfb4']);
      solid(cube([-.105,-.105,.1],[.105,.105,.4]),['#d5e2d9','#edf3ee','#bbcebf']);
      solid(beam(pose.shoulder,pose.elbow,.13),['#5b9274','#98baa3','#387b57']);
      solid(beam(pose.elbow,pose.wrist,.10),['#94b4a0','#d3e3d8','#74a088']);
      const tipDirection=G.rotateZ(G.rotateY([1,0,0],q[1]+q[2]),q[0]);
      const tip=G.add(pose.wrist,scale(tipDirection,.12));
      solid(beam(pose.wrist,tip,.07),['#778c80','#a4b6a9','#5a7564']);
      let svg=`<svg class="lab-svg" viewBox="0 0 720 410" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="三关节机械臂几何结构"><defs>${Object.entries(palette).slice(0,3).map(([key,color])=>arrow('robot-'+key,color)).join('')}</defs><rect width="720" height="410" fill="#fafcfb"/>`;
      for(let i=-4;i<=5;i++){const n=i*.25;svg+=line(screen([n,-1,0]),screen([n,1.25,0]),'#e1eae3',1)+line(screen([-1,n,0]),screen([1.25,n,0]),'#e1eae3',1)}
      svg+=`<ellipse cx="${screen([.35,0,0])[0]}" cy="${screen([.35,0,0])[1]+4}" rx="104" ry="18" fill="#d1dfd529"/>`;
      faces.sort((a,b)=>a.depth-b.depth).forEach(f=>{svg+=`<polygon points="${f.points.map(point).join(' ')}" fill="${f.fill}" stroke="#3c6c511f" stroke-width="1.1" stroke-linejoin="round"/>`});
      for(const [name,p]of [['shoulder',pose.shoulder],['elbow',pose.elbow],['wrist',pose.wrist]]){
        const [x,y]=screen(p);svg+=`<circle cx="${x}" cy="${y}" r="${name==='wrist'?5:8}" fill="#456e55" stroke="#edf5ef" stroke-width="2"/>`;
      }
      function axes(origin,rotation,size,prefix,labels){
        Object.entries(palette).slice(0,3).forEach(([axis,color],i)=>{
          const vector=[0,0,0];vector[i]=size;const end=G.add(origin,rotation(vector));
          svg+=line(screen(origin),screen(end),color,1.7,`marker-end="url(#robot-${axis})"`);
          const p=screen(end);if(labels)svg+=label(p[0]+7,p[1]-4,prefix+axis.toUpperCase(),color,13);
        });
      }
      axes([-.40,-.36,0],p=>p,.33,'',true);
      if(el.querySelector('[data-model-frames]').checked){
        axes(pose.shoulder,p=>G.rotateZ(p,q[0]),.3,'',true);
        axes(pose.elbow,p=>G.rotateZ(G.rotateY(p,q[1]),q[0]),.25,'',false);
        axes(pose.wrist,p=>G.rotateZ(G.rotateY(p,q[1]+q[2]),q[0]),.23,'',false);
      }
      const base=screen([-.2,-.12,.15]),elbow=screen(pose.elbow),wrist=screen(pose.wrist);
      svg+=label(base[0]-64,base[1]-11,'base_link','#6f8176',14);
      svg+=label(elbow[0]-7,elbow[1]-22,'upper_link','#54765e',14);
      svg+=label(wrist[0]+17,wrist[1]+3,'tool0','#54765e',14);
      svg+=label(24,30,'link = 刚体 · joint = 相对运动','#87988d',13);
      svg+=label(480,390,'几何示意 / 无物理仿真','#87988d',12)+'</svg>';
      stage.innerHTML=svg;
      el.querySelector('[data-robot-result]').textContent=`[${pose.wrist.map(x=>fmt(x,3)).join(', ')}] m`;
      q.forEach((v,i)=>el.querySelector(`[data-output="q${i+1}"]`).textContent=v+'°');
    }
    el.addEventListener('input',draw);
    el.addEventListener('click',event=>{
      const target=event.target.closest('button');if(!target)return;
      if(target.hasAttribute('data-lab-reset')){camera={...initial};[25,-40,70].forEach((n,i)=>el.querySelector(`[data-param="q${i+1}"]`).value=n);el.querySelector('[data-model-frames]').checked=false;el.querySelectorAll('[data-camera]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.camera==='iso')));draw()}
      if(target.dataset.camera){
        const views={iso:[-30,24],front:[0,0],top:[0,90]};[camera.yaw,camera.pitch]=views[target.dataset.camera];
        el.querySelectorAll('[data-camera]').forEach(b=>b.setAttribute('aria-pressed',String(b===target)));draw();
      }
    });
    stage.addEventListener('pointerdown',event=>{if(event.button!==0)return;stage.focus({preventScroll:true});drag={x:event.clientX,y:event.clientY,yaw:camera.yaw,pitch:camera.pitch};stage.setPointerCapture(event.pointerId);stage.classList.add('dragging')});
    stage.addEventListener('pointermove',event=>{if(!drag)return;camera.yaw=drag.yaw+(event.clientX-drag.x)*.45;camera.pitch=Math.max(-10,Math.min(88,drag.pitch+(event.clientY-drag.y)*.35));el.querySelectorAll('[data-camera]').forEach(b=>b.setAttribute('aria-pressed','false'));draw()});
    const stop=()=>{drag=null;stage.classList.remove('dragging')};stage.addEventListener('pointerup',stop);stage.addEventListener('pointercancel',stop);
    stage.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home'].includes(event.key))return;event.preventDefault();if(event.key==='Home')camera={...initial};else{if(event.key==='ArrowLeft')camera.yaw-=8;if(event.key==='ArrowRight')camera.yaw+=8;if(event.key==='ArrowUp')camera.pitch=Math.min(88,camera.pitch+6);if(event.key==='ArrowDown')camera.pitch=Math.max(-10,camera.pitch-6)}draw()});
    draw();
  }

  function mountTransform(el){
    el.addEventListener('input',()=>renderTransform(el));
    el.addEventListener('click',event=>{
      const b=event.target.closest('button');if(!b)return;
      let values;
      if(b.hasAttribute('data-lab-reset'))values=[.8,.4,30];
      if(b.dataset.transformPreset==='translation')values=[.8,.4,0];
      if(b.dataset.transformPreset==='quarter')values=[0,0,90];
      if(values){['x','y','angle'].forEach((key,i)=>el.querySelector(`[data-param="${key}"]`).value=values[i]);renderTransform(el)}
    });renderTransform(el);
  }

  function mount(chapter){
    let number=0;
    const chapterNumber=window.ROS2Hub.lessons.findIndex(c=>c.id===chapter.id)+1;
    const insert=(html,index)=>{const section=document.getElementById('part-'+index);if(section)section.insertAdjacentHTML('beforeend',html)};
    const matched=(window.PreviewFigureData||[]).map(item=>({item,placement:item.placements.find(x=>x.chapter===chapter.id)})).filter(x=>x.placement).sort((a,b)=>a.placement.afterSection-b.placement.afterSection);
    for(const {item,placement} of matched){
      insert(staticFigure(item,`${chapterNumber}.${++number}`),placement.afterSection);
    }
    if(['tf2','eco-tf-frames'].includes(chapter.id)){
      insert(transformFigure(`${chapterNumber}.${++number}`),chapter.id==='tf2'?2:1);
      mountTransform(document.getElementById('fig-tf2-transform'));
    }
    if(['eco-model-rviz','eco-moveit-planning'].includes(chapter.id)){
      insert(robotFigure(`${chapterNumber}.${++number}`),1);mountRobot(document.getElementById('fig-robot-model'));
    }
  }

  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-figure-expand]');if(!button)return;
    const source=button.closest('.context-figure'),dialog=document.getElementById('figure-dialog');
    dialog.querySelector('h2').textContent=source.querySelector('h3').textContent;
    const image=source.querySelector('.figure-static img');
    dialog.querySelector('.figure-dialog-body').innerHTML=image?image.outerHTML:source.querySelector('.lab-svg').outerHTML.replace(/id="([^"]+)"/g,'id="zoom-$1"').replace(/url\(#([^)]+)\)/g,'url(#zoom-$1)');
    dialog.querySelector('.figure-dialog-caption').textContent=source.querySelector('figcaption').textContent+(image?'':'（当前参数快照；关闭后可继续调整。）');
    dialog.showModal();
  });
  window.addEventListener('resize',()=>{const figure=document.getElementById('fig-tf2-transform');if(figure)renderTransform(figure)});
  window.PreviewFigures={mount};
})();
