/* 本地教学可视化适配层。mount 输入容器、初始状态；输出 resize / getState / dispose。
 * 几何长度单位 m，界面角度单位 °，计算时由现有 PreviewGeometry 转为弧度。
 * 这里没有 ROS 连接、碰撞与动力学；未来 SceneView 等经独立适配器接入，不伪造实时数据。
 */
(() => {
  'use strict';
  const G = window.PreviewGeometry, E = window.NarukamiLogic.esc;
  const registry = new Map(), live = new Map(), states = new Map();
  const fmt = (n, digits = 3) => (Math.abs(n) < 1e-8 ? 0 : n).toFixed(digits);
  const frame = (x,y,title,color,counterRotate=0) => `<g transform="translate(${x} ${y})" stroke="${color}" stroke-width="2"><path d="M0 0h54m-7-5 7 5-7 5M0 0v-54m-5 7 5-7 5 7" fill="none"/><text x="60" y="5" transform="rotate(${counterRotate} 60 5)" fill="${color}" stroke="none" font-size="13">x${title}</text><text x="8" y="-56" transform="rotate(${counterRotate} 8 -56)" fill="${color}" stroke="none" font-size="13">y${title}</text></g>`;
  function preview(kind) {
    if (kind === 'transform') return `<svg class="preview-diagram" viewBox="0 0 180 105" aria-hidden="true"><path d="M22 84h132M42 99V14" fill="none" stroke="#d8ccdf"/><g transform="translate(70 65) rotate(-28)" stroke="#cf6796" stroke-width="2"><path d="M0 0h62M0 0v-47"/></g><path d="M42 84 70 65 124 36" stroke="#a992c6" stroke-dasharray="4 4" fill="none"/><circle cx="124" cy="36" r="5" fill="#8460b1"/><circle cx="70" cy="65" r="3" fill="#cf6796"/></svg>`;
    return `<svg class="preview-diagram" viewBox="0 0 180 105" aria-hidden="true"><ellipse cx="85" cy="92" rx="48" ry="7" fill="#e9e0ef"/><path d="M62 89 62 68 77 60 112 29 143 47" stroke="#9e7eb8" stroke-width="13" fill="none" stroke-linejoin="round"/><path d="M143 47 155 40" stroke="#cf6796" stroke-width="7"/><g fill="#fff7fc" stroke="#8460b1" stroke-width="2"><circle cx="62" cy="68" r="5"/><circle cx="112" cy="29" r="5"/><circle cx="143" cy="47" r="4"/></g></svg>`;
  }
  function card(id, kind, title) {
    return `<details class="lab-card" id="fig-${id}" data-lab="${id}"><summary class="lab-summary">${preview(kind)}<div><small>INTERACTIVE NOTE · 本地教学模型</small><h3>${E(title)}</h3><p>${kind === 'transform' ? '拖动参数，把公式与坐标变化放在一起看。' : '旋转视角、调整关节，观察局部坐标与末端位置。'}</p></div><span class="lab-open-label">展开实验</span></summary><div class="lab-host"></div></details>`;
  }
  function slider(key,title,min,max,step,value,unit) {
    return `<label class="lab-control"><span>${title}<output data-value="${key}">${value} ${unit}</output></span><input type="range" data-param="${key}" aria-label="${title}" min="${min}" max="${max}" step="${step}" value="${value}"><span class="range-ends"><span>${min} ${unit}</span><span>${max} ${unit}</span></span></label>`;
  }
  function toolbar(label) {
    return `<div class="lab-toolbar"><span>${label}</span><div><button data-lab-reset>↺ 复位</button><button data-lab-wide>⛶ 宽屏查看</button></div></div>`;
  }
  function controls(root, state, initial, render, signal) {
    root.addEventListener('input', event => {
      const key = event.target.dataset.param;
      if (!key || !Object.hasOwn(initial,key)) return;
      const value = Number(event.target.value); if (!Number.isFinite(value)) return;
      state[key] = value; render();
    },{signal});
    root.querySelector('[data-lab-reset]').addEventListener('click', () => {Object.assign(state, initial); render();},{signal});
  }
  function transformMount(root, options = {}) {
    const initial = {x:.8,y:.4,angle:30}, state = {...initial,...options.initialState};
    const controller = new AbortController(), {signal} = controller;
    root.innerHTML = `<div class="lab-body">${toolbar('二维刚体变换 · m / °')}<div class="lab-plot"></div><div class="lab-readout"><span>雷达坐标 <code>p_L = [1, 0] m</code></span><span>车体坐标 <output data-result></output></span></div><div class="lab-controls">${slider('x','平移 x',-.8,1.4,.05,state.x,'m')}${slider('y','平移 y',-.4,1.2,.05,state.y,'m')}${slider('angle','旋转 θ',-180,180,1,state.angle,'°')}</div><div class="lab-presets"><button data-preset="translation">只看平移</button><button data-preset="quarter">旋转 90°</button><button data-preset="identity">单位变换</button></div><p class="lab-description"><strong>p_B = R(θ) · p_L + t</strong>　先旋转、再平移。同一个点在两个坐标系中有不同坐标；此图不模拟 tf2 的时间缓存。</p></div>`;
    function render() {
      const result = G.transform2D([1,0],state);
      // 合法滑块范围内自动容纳原点、传感器与观测点，避免旋转到下方时被画布裁掉。
      const xs=[0,state.x,result[0]],ys=[0,state.y,result[1]];
      const minX=Math.min(...xs)-.55,maxX=Math.max(...xs)+.55,minY=Math.min(...ys)-.55,maxY=Math.max(...ys)+.55;
      const unit=Math.min(125,630/(maxX-minX),290/(maxY-minY));
      const ox=Math.max(40-minX*unit,Math.min(230,680-maxX*unit));
      const oy=Math.max(25+maxY*unit,Math.min(275,325+minY*unit));
      const toPx = p => [ox+p[0]*unit,oy-p[1]*unit];
      const sensor = toPx([state.x,state.y]), point = toPx(result), angle = -state.angle;
      let grid = ''; for (let x=ox-Math.ceil(ox/(unit/2))*(unit/2);x<700;x+=unit/2) grid += `<path d="M${x} 22v310"/>`;
      for (let y=oy-Math.ceil(oy/(unit/2))*(unit/2);y<335;y+=unit/2) grid += `<path d="M32 ${y}h660"/>`;
      root.querySelector('.lab-plot').innerHTML = `<svg viewBox="0 0 720 370" role="img" aria-label="二维坐标变换，先旋转再平移"><g stroke="var(--line)" fill="none">${grid}</g><path d="M32 ${oy}h658M${ox} 337V18" stroke="var(--muted)" opacity=".45" fill="none"/><g transform="translate(${sensor[0]} ${sensor[1]}) rotate(${angle})">${frame(0,0,'_L','#cf6796',state.angle)}</g>${frame(ox,oy,'_B','#7d66aa')}<path d="M${ox} ${oy}L${sensor[0]} ${sensor[1]}L${point[0]} ${point[1]}" stroke="#bc9d79" stroke-width="1.8" stroke-dasharray="5 5" fill="none"/><path d="M${point[0]} ${oy}V${point[1]}H${ox}" stroke="#9cadd1" stroke-dasharray="3 5" fill="none"/><circle cx="${sensor[0]}" cy="${sensor[1]}" r="5" fill="#cf6796"/><circle cx="${point[0]}" cy="${point[1]}" r="7" fill="#8460b1" stroke="var(--surface)" stroke-width="3"/><text x="${Math.min(636,point[0]+13)}" y="${Math.max(22,point[1]-12)}" fill="var(--purple)" font-size="14">观测点 P</text><text x="36" y="355" fill="var(--muted)" font-size="11">base_link → laser</text><text x="570" y="355" fill="var(--muted)" font-size="11">每小格 = 0.5 m</text></svg>`;
      root.querySelector('[data-result]').textContent = `[${fmt(result[0])}, ${fmt(result[1])}] m`;
      for (const [key,value] of Object.entries(state)) {
        root.querySelector(`[data-param="${key}"]`).value = value;
        root.querySelector(`[data-value="${key}"]`).textContent = fmt(value,key === 'angle' ? 0 : 2) + (key === 'angle' ? ' °' : ' m');
      }
      options.onStateChange?.({...state});
    }
    controls(root,state,initial,render,signal);
    root.querySelectorAll('[data-preset]').forEach(button => button.addEventListener('click',() => {
      Object.assign(state,button.dataset.preset === 'quarter' ? {x:0,y:0,angle:90} : button.dataset.preset === 'identity' ? {x:0,y:0,angle:0} : {x:.8,y:.4,angle:0});render();
    },{signal}));
    render(); return {resize:render,getState:() => ({...state}),dispose:() => {controller.abort();root.replaceChildren();}};
  }
  function robotMount(root, options = {}) {
    const initial = {q1:25,q2:-40,q3:70,yaw:-30,pitch:24,frames:true}, state = {...initial,...options.initialState};
    const controller = new AbortController(), {signal} = controller;
    root.innerHTML = `<div class="lab-body">${toolbar('三关节几何模型 · 拖动旋转视角')}<div class="lab-plot" aria-label="拖动旋转模型视角" tabindex="0"></div><div class="lab-readout"><span>末端位置 <output data-result></output></span><label><input type="checkbox" data-frames ${state.frames ? 'checked' : ''}> 局部坐标系</label></div><div class="lab-controls">${slider('q1','底座 q₁ · Z轴',-150,150,1,state.q1,'°')}${slider('q2','肩关节 q₂ · Y轴',-80,20,1,state.q2,'°')}${slider('q3','肘关节 q₃ · Y轴',-100,100,1,state.q3,'°')}</div><div class="lab-presets"><button data-view="front">正视</button><button data-view="top">俯视</button><button data-view="iso">默认视角</button></div><div class="model-structure">base → shoulder → elbow → tool<br>肩高 0.40 m · 上臂 0.85 m · 前臂 0.65 m · 右手坐标系</div><p class="lab-description">此处沿用教材的三关节几何教学模型，采用正交投影。模型章的 learning_description 是另一份差速车 URDF 工程；真实 URDF 浏览器显示预留给后续组件接入。此图没有 ROS 数据、碰撞检测或物理仿真。</p></div>`;
    const plot = root.querySelector('.lab-plot'); let drag = null;
    function render() {
      const pose = G.armPose(state.q1,state.q2,state.q3);
      const camera = {yaw:state.yaw,pitch:state.pitch,scale:210,cx:330,cy:220,target:[.4,0,.65]};
      // 先在单位比例下求模型包围范围，再缩放/居中；仅调整观察相机，不改关节角或末端数值。
      // 画布720×390px，关节预留60px边距和底部文字区；直臂、抬臂与俯视均应完整可见。
      const projected=[[0,0,0],pose.shoulder,pose.elbow,pose.wrist].map(p=>G.project(p,{...camera,scale:1,cx:0,cy:0}).screen);
      const xs=projected.map(p=>p[0]),ys=projected.map(p=>p[1]),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
      camera.scale=Math.min(210,600/Math.max(.4,maxX-minX),260/Math.max(.4,maxY-minY));
      camera.cx=360-(minX+maxX)*camera.scale/2;camera.cy=190-(minY+maxY)*camera.scale/2;
      const project = p => G.project(p,camera).screen;
      const point = p => project(p).map(n => fmt(n,1)).join(' ');
      let grid=''; for(let i=-4;i<=5;i++) {const n=i*.25;grid+=`<path d="M${point([n,-1,0])}L${point([n,1.25,0])}M${point([-1,n,0])}L${point([1.25,n,0])}"/>`;}
      const joint = (p,r) => {const xy=project(p);return `<circle cx="${xy[0]}" cy="${xy[1]}" r="${r}" fill="var(--surface)" stroke="#8460b1" stroke-width="4"/>`;};
      const link = (a,b,width,color) => `<path d="M${point(a)}L${point(b)}" stroke="${color}" stroke-width="${width}" stroke-linecap="round"/><path d="M${point(a)}L${point(b)}" stroke="#ffffff44" stroke-width="${width*.35}" stroke-linecap="round"/>`;
      let axes = '';
      function localAxes(origin,rotation) {
        ['#bd6864','#548b73','#6b8dbf'].forEach((color,i) => {const v=[0,0,0];v[i]=.19; const end=G.add(origin,rotation(v));const pos=project(end);axes+=`<path d="M${point(origin)}L${point(end)}" stroke="${color}" stroke-width="2"/><text x="${pos[0]+5}" y="${pos[1]-4}" fill="${color}" font-size="11">${'XYZ'[i]}</text>`;});
      }
      localAxes([0,0,0],v=>v);
      if (state.frames) {localAxes(pose.shoulder,v=>G.rotateZ(G.rotateY(v,state.q2),state.q1));localAxes(pose.elbow,v=>G.rotateZ(G.rotateY(v,state.q2+state.q3),state.q1));}
      const base=project([0,0,0]), tool=project(pose.wrist);
      plot.innerHTML=`<svg viewBox="0 0 720 390" role="img" aria-label="三关节几何模型与末端坐标"><g fill="none" stroke="var(--line)" stroke-width="1">${grid}</g><ellipse cx="${base[0]+30}" cy="${base[1]+8}" rx="70" ry="15" fill="var(--purple-soft)"/><path d="M${base[0]-30} ${base[1]}h60" stroke="#b9a8c7" stroke-width="16" stroke-linecap="round"/>${link([0,0,0],pose.shoulder,26,'#b4a0c4')}${link(pose.shoulder,pose.elbow,22,'#a883b3')}${link(pose.elbow,pose.wrist,17,'#d28cac')}${joint(pose.shoulder,10)}${joint(pose.elbow,9)}${joint(pose.wrist,6)}${axes}<text x="${Math.min(635,tool[0]+15)}" y="${Math.max(28,tool[1]-14)}" fill="var(--pink)" font-size="13">末端 tool</text><text x="35" y="366" fill="var(--muted)" font-size="11">拖动图形旋转 · 方向键调整视角</text><text x="580" y="366" fill="var(--muted)" font-size="11">单位 m / °</text></svg>`;
      root.querySelector('[data-result]').textContent=`[${pose.wrist.map(n=>fmt(n)).join(', ')}] m`;
      for(const key of ['q1','q2','q3']) {root.querySelector(`[data-param="${key}"]`).value=state[key];root.querySelector(`[data-value="${key}"]`).textContent=state[key]+' °';}
      root.querySelector('[data-frames]').checked=state.frames;options.onStateChange?.({...state});
    }
    controls(root,state,initial,render,signal);
    root.querySelector('[data-frames]').addEventListener('change',event=>{state.frames=event.target.checked;render();},{signal});
    root.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{Object.assign(state,button.dataset.view==='front'?{yaw:0,pitch:0}:button.dataset.view==='top'?{yaw:0,pitch:85}:{yaw:-30,pitch:24});render();},{signal}));
    plot.addEventListener('pointerdown',event=>{drag={x:event.clientX,y:event.clientY,yaw:state.yaw,pitch:state.pitch};plot.setPointerCapture(event.pointerId);},{signal});
    plot.addEventListener('pointermove',event=>{if(!drag)return;state.yaw=drag.yaw+(event.clientX-drag.x)*.45;state.pitch=Math.max(-30,Math.min(85,drag.pitch+(event.clientY-drag.y)*.35));render();},{signal});
    plot.addEventListener('pointerup',()=>{drag=null;},{signal});plot.addEventListener('pointercancel',()=>{drag=null;},{signal});
    plot.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))return;event.preventDefault();state.yaw+=(event.key==='ArrowRight'?5:event.key==='ArrowLeft'?-5:0);state.pitch=Math.max(-30,Math.min(85,state.pitch+(event.key==='ArrowDown'?5:event.key==='ArrowUp'?-5:0)));render();},{signal});
    render();return {resize:render,getState:()=>({...state}),dispose:()=>{controller.abort();root.replaceChildren();}};
  }
  registry.set('tf2-transform',{mount:transformMount,kind:'transform',title:'同一个点，两种坐标表达'});
  registry.set('robot-model',{mount:robotMount,kind:'robot',title:'从关节角到末端位置'});
  function mount(id,root) {
    const adapter=registry.get(id);if(!adapter)throw new Error('未注册的可视化组件：'+id);
    if(live.has(id))dispose(id);
    const instance=adapter.mount(root,{initialState:states.get(id),onStateChange:s=>states.set(id,s)});
    live.set(id,instance);return instance;
  }
  function dispose(id) {const instance=live.get(id);if(instance){states.set(id,instance.getState());instance.dispose();live.delete(id);}}
  window.NarukamiVisuals={card,preview,mount,dispose,disposeAll:()=>[...live.keys()].forEach(dispose),getState:id=>({...states.get(id)}),resize:id=>live.get(id)?.resize(),stats:()=>({registered:registry.size,mounted:live.size}),register:(id,adapter)=>{if(registry.has(id)||typeof adapter.mount!=='function')throw new Error('无效或重复的组件');registry.set(id,adapter);}};
})();
