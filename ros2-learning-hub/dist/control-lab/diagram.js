(function (root) {
  'use strict';
  const C = root.LearningContent;
  const esc = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function node(id,x,y,w,h,category,options={}) {
    const n=C.nodes[id];
    const circle=options.circle;
    const shape=circle ? `<circle cx="${x+w/2}" cy="${y+h/2}" r="${w/2}"/>` : `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${options.round??12}"/>`;
    const cy=y+h/2;
    return `<g class="map-node node-${category}" data-node="${id}" role="button" tabindex="0" aria-label="${esc(n.title+' '+n.en+'，查看说明')}" aria-pressed="false">${shape}<text class="node-cn" x="${x+w/2}" y="${cy-(options.qualifier?10:3)}" text-anchor="middle">${esc(options.title??n.title)}</text><text class="node-en" x="${x+w/2}" y="${cy+(options.qualifier?10:20)}" text-anchor="middle">${esc(options.en??n.en)}</text>${options.qualifier?`<text class="node-en" style="font-size:10px" x="${x+w/2}" y="${cy+26}" text-anchor="middle">${esc(options.qualifier)}</text>`:''}</g>`;
  }
  function edge(path,type='management',dashed=false) {
    return `<path class="map-edge edge-${type}${dashed?' dashed':''}" d="${path}" marker-end="url(#arrow-${type})"/>`;
  }
  function label(x,y,cn,en,type='management',anchor='middle') {
    return `<g class="edge-label label-${type}"><text x="${x}" y="${y}" text-anchor="${anchor}" class="edge-cn">${cn}</text><text x="${x}" y="${y+16}" text-anchor="${anchor}" class="edge-en">${en}</text></g>`;
  }
  function actuatorStateEdge() {
    const path='M 552 701 V 676 Q 552 666 542 666 H 330 Q 320 666 320 656 V 635';
    return `<path d="${path}" fill="none" stroke="#fff" stroke-width="5"/><path class="map-edge edge-state dashed" data-from="actuator" data-to="state" d="${path}" marker-end="url(#arrow-state)"><title>Actuator 可导出状态接口；读取能力可按设备实现省略</title></path>`;
  }
  function render(mode='all',selected='cm') {
    const dataMode = mode==='state'||mode==='command';
    const defs=`<defs>${[['management','#91a0ae'],['state','#1b8d80'],['command','#cf8b35'],['optional','#9a9ca9']].map(([id,color])=>`<marker id="arrow-${id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1 1L9 5L1 9Z" fill="${color}"/></marker>`).join('')}<pattern id="map-grid" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.7" fill="#dce3e7"/></pattern></defs>`;
    let lines='';
    if(!dataMode) {
      lines+=edge('M 395 245 V 216 H 183 Q 173 216 173 206 V 171');
      lines+=edge('M 395 245 V 171');
      lines+=edge('M 395 245 V 216 H 607 Q 617 216 617 206 V 171');
      lines+=label(173,190,'分配接口','grant interfaces to');
      lines+=label(395,190,'分配接口','grant interfaces to');
      lines+=label(617,190,'分配接口','grant interfaces to');
      lines+=edge('M 395 220 V 293');
      lines+=label(395,255,'请求接口','request interfaces from');
      lines+=edge('M 270 329 H 63 Q 53 329 53 319 V 109 Q 53 99 63 99 H 107');
      lines+=label(55,221,'加载','loads');
      lines+=edge('M 395 365 V 429','management',true);
      lines+=label(395,392,'申请占用接口','claim interfaces from');
      lines+=edge('M 270 465 H 39 Q 29 465 29 475 V 718 Q 29 728 39 728 H 107');
      lines+=label(30,631,'加载','loads');
      lines+=edge('M 320 501 V 563');
      lines+=edge('M 513 501 V 563');
      lines+=label(320,525,'管理','manages');
      lines+=label(513,525,'管理','manages');
    }
    if(dataMode) {
      // 教学数据流与静态的管理/接口导出关系分开显示。
      if(mode==='state') {
        lines+=edge('M 395 862 V 795 H 194 V 761','state');
        lines+=edge('M 395 862 V 761','state');
        lines+=edge('M 374 701 V 651 H 320 V 635','state');
        lines+=edge('M 194 701 V 674 Q 194 664 204 664 H 310 Q 320 664 320 654 V 635','state');
        lines+=edge('M 513 862 V 840 Q 513 830 523 830 H 588 Q 598 830 598 820 V 761','state',true);
        lines+=actuatorStateEdge();
        lines+=edge('M 320 563 V 536 H 214 V 193 Q 214 181 202 181 H 174 V 171','state');
        lines+=label(210,546,'状态反馈','read → state','state');
        lines+=label(196,674,'读取测量','read()','state');
      } else {
        lines+=edge('M 173 171 V 529 Q 173 539 183 539 H 513 V 563','command');
        lines+=edge('M 513 635 V 656 H 395 V 691','command');
        lines+=edge('M 513 635 V 656 H 598 V 691','command');
        lines+=edge('M 395 761 V 862','command');
        lines+=edge('M 598 761 V 825 H 520 V 862','command');
        lines+=label(188,404,'计算目标','update()','command','start');
        lines+=label(594,809,'下发命令','write()','command');
      }
    } else {
      // 按官方组件定义补齐原图省略的 Actuator 可选状态反馈。
      lines+=edge('M 194 701 V 660 Q 194 650 204 650 H 310 Q 320 650 320 640 V 635','state');
      lines+=edge('M 374 701 V 660 Q 374 650 364 650 H 330 Q 320 650 320 640 V 635','state');
      lines+=edge('M 416 701 V 660 Q 416 650 426 650 H 503 Q 513 650 513 640 V 635','command');
      lines+=edge('M 620 701 V 660 Q 620 650 610 650 H 523 Q 513 650 513 640 V 635','command');
      lines+=actuatorStateEdge();
      lines+=label(278,661,'导出','exports','state');
      lines+=label(545,661,'导出','exports','command');
      lines+=edge('M 194 761 V 813 Q 194 823 204 823 H 310 Q 320 823 320 833 V 862');
      lines+=edge('M 395 761 V 813 Q 395 823 385 823 H 330 Q 320 823 320 833 V 862');
      lines+=edge('M 395 761 V 813 Q 395 823 405 823 H 503 Q 513 823 513 833 V 862');
      lines+=edge('M 598 761 V 813 Q 598 823 588 823 H 523 Q 513 823 513 833 V 862');
      lines+=label(320,837,'访问','access');
      lines+=label(513,837,'访问','access');
      lines+=edge('M 439 761 V 786 Q 439 796 449 796 H 758','optional',true);
      lines+=`<path class="map-edge edge-optional dashed" d="M 642 761 V 786 Q 642 796 652 796 H 702"/>`;
      lines+=label(730,767,'可能使用','may use','optional');
    }
    const groups=`<g class="map-groups"><rect class="group-outline" x="107" y="26" width="575" height="153" rx="22"/><text x="127" y="48" class="group-caption">控制器 <tspan>Controllers</tspan></text><rect class="group-outline" x="107" y="675" width="575" height="104" rx="18"/><text x="127" y="692" class="group-caption small">硬件组件 <tspan>Hardware Components</tspan></text></g>`;
    let nodes='';
    nodes+=node('controller-a',120,65,106,106,'controller',{circle:true});
    nodes+=node('controller-b',342,65,106,106,'controller',{circle:true});
    nodes+=node('controller-c',564,65,106,106,'controller',{circle:true});
    nodes+=node('cm',270,293,250,72,'manager');
    nodes+=node('rm',270,429,250,72,'manager');
    nodes+=node('state',232,563,176,72,'state',{title:'状态接口 · 只读',en:'State Interface',qualifier:'<read only>'});
    nodes+=node('command',425,563,176,72,'command',{title:'命令接口 · 读/写',en:'Command Interface',qualifier:'<read/write>'});
    nodes+=node('sensor',126,701,136,60,'hardware',{title:'传感器',en:'Sensor'});
    nodes+=node('system',327,701,136,60,'hardware',{title:'系统',en:'System'});
    nodes+=node('actuator',530,701,136,60,'hardware',{title:'执行器',en:'Actuator',qualifier:'read optional'});
    nodes+=node('transmission',758,752,134,88,'optional',{title:'传动映射',en:'Transmissions'});
    nodes+=`<g class="map-node node-physical" data-node="hardware" role="button" tabindex="0" aria-label="物理硬件资源 Hardware Resources，查看说明" aria-pressed="false"><rect x="221" y="862" width="348" height="77" rx="15"/><g class="physical-symbol" transform="translate(241 877)" fill="none" stroke="currentColor" stroke-width="2"><rect width="27" height="30" rx="6"/><path d="M6 8h15M6 15h15M6 22h9M27 15h13m-3-3 3 3-3 3"/></g><text x="425" y="891" text-anchor="middle" class="node-cn">物理硬件资源</text><text x="425" y="915" text-anchor="middle" class="node-en">Hardware Resources</text></g>`;
    const svg=`<svg xmlns="http://www.w3.org/2000/svg" class="architecture-svg mode-${mode}" viewBox="0 0 920 963" role="group" aria-labelledby="map-title map-description">${defs}<title id="map-title">ros2_control 中英双语交互架构图</title><desc id="map-description">控制器、控制器管理器、资源管理器、状态与命令接口、三类硬件组件和物理资源。实线为管理或接口关系，虚线为申领或可选关系。按 Tab 选择节点并按 Enter 查看解释。状态与命令模式展示教学数据流。</desc><rect width="920" height="963" fill="url(#map-grid)"/>${groups}${lines}${nodes}</svg>`;
    const box=document.createElement('div');box.innerHTML=svg;
    box.querySelectorAll('[data-node]').forEach(g=>{
      const active=g.dataset.node===selected;
      g.classList.toggle('selected',active);g.setAttribute('aria-pressed',String(active));
      if(mode==='management')g.classList.toggle('subtle',!['cm','rm','controller-a','controller-b','controller-c'].includes(g.dataset.node));
      if(mode==='state')g.classList.toggle('subtle',!['controller-a','state','sensor','system','actuator','hardware'].includes(g.dataset.node));
      if(mode==='command')g.classList.toggle('subtle',!['controller-a','command','system','actuator','hardware'].includes(g.dataset.node));
    });
    return box.innerHTML;
  }
  root.LearningDiagram={render};
})(window);
