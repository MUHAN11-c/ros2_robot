(function () {
  'use strict';
  const C=window.LearningContent, L=window.CourseLogic;
  const $=(selector,root=document)=>root.querySelector(selector);
  const $$=(selector,root=document)=>[...root.querySelectorAll(selector)];
  const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const paths={
    search:'<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/>',
    book:'<path d="M12 5v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v14c-4-1-6 0-9 2-3-2-5-3-9-2Z"/>',
    'arrow-up-right':'<path d="M6 18 18 6M6 6h12v12"/>',
    arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
    external:'<path d="M14 3h7v7m0-7L10 14M11 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-6"/>',
    menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
    close:'<path d="m6 6 12 12M6 18 18 6"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    cursor:'<path d="m5 3 14 9-7 1-3 7Z"/>',
    download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    layers:'<path d="m12 3 10 5-10 5L2 8Zm-9 10 9 5 9-5m-18 5 9 5 9-5"/>',
    bulb:'<path d="M8 16c0-2-3-3-3-7a7 7 0 0 1 14 0c0 4-3 5-3 7M8 17h8M9 21h6"/>',
    copy:'<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M15 8V3H3v13h5"/>',
    check:'<path d="m4 12 5 5L20 6"/>',
    play:'<path d="m8 4 12 8-12 8Z"/>',
    pause:'<path d="M8 4v16M16 4v16"/>',
    step:'<path d="m5 4 11 8-11 8ZM20 4v16"/>',
    reset:'<path d="M3 5v6h6M3 11a9 9 0 1 1 2.7 7"/>',
    chevron:'<path d="m9 5 7 7-7 7"/>',
    code:'<path d="m7 6-6 6 6 6m10-12 6 6-6 6M14 3l-4 18"/>',
    compass:'<circle cx="12" cy="12" r="9"/><path d="m16 8-2 6-6 2 2-6Z"/>'
  };
  const svgIcon=name=>`<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name]??paths.layers}</svg>`;
  const icon=name=>`<span class="icon">${svgIcon(name)}</span>`;
  let storage=null;
  try{storage=window.localStorage;}catch{/* 隐私模式仍然允许会话内学习。 */}
  const ids=C.lessons.map(l=>l.id),progress=L.createProgress(storage,ids);
  const state={id:'architecture',selected:'cm',mode:'all',file:'urdf',cycleStep:0,cycles:0,playing:false,timer:null,answers:new Map()};
  const copyTexts=new Map();
  let toastTimer=null;
  const sourceLink=(id,label)=>{const s=C.sources[id];return s?`<a class="code-source" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(label??s.title)}${icon('external')}</a>`:'';};
  function codeRaw(id,title,language,text,source) {
    copyTexts.set(id,text);
    return `<div class="code-block"><div class="code-top"><span class="code-title"><span class="language">${esc(language.toUpperCase())}</span>${esc(title)}</span><button class="copy-code" data-copy="${esc(id)}" aria-label="复制：${esc(title)}">${icon('copy')}<span>复制</span></button></div><pre><code>${esc(text)}</code></pre></div>${source?sourceLink(source,'查看官方出处'):''}`;
  }
  function code(id) {
    const s=C.snippets[id];
    return codeRaw(id,s.title,s.lang,s.code,s.source)+(s.note?`<p class="code-note">${esc(s.note)}</p>`:'');
  }
  const callout=(title,body,amber=false)=>`<div class="callout${amber?' amber':''}"><strong>${title}</strong><p>${body}</p></div>`;
  function lessonHeader(lesson) {
    const n=ids.indexOf(lesson.id)+1;
    return `<div class="lesson-header"><div><div class="eyebrow">${String(n).padStart(2,'0')} / ${esc(lesson.label)} <span>·</span> ${esc(lesson.en.toUpperCase())}</div><h1 id="lesson-title">${esc(lesson.title)}</h1><p class="subtitle">${esc(lesson.subtitle)}</p></div><div class="lesson-meta">${icon('clock')}${esc(lesson.time)}<span>·</span>零基础友好</div></div><div class="lesson-intro"><div class="intro-label">${icon('target')}这一节，你会学到</div><ul class="goal-list">${lesson.goals.map(g=>`<li>${esc(g)}</li>`).join('')}</ul></div>`;
  }
  function chapterEnd(lesson) {
    const index=ids.indexOf(lesson.id),next=C.lessons[index+1];
    const done=progress.has(lesson.id);
    const quizLocked=lesson.id==='quiz'&&!C.quizzes.every((q,i)=>state.answers.get(i)===q.answer);
    return `<div class="chapter-end"><button id="complete-lesson" class="button ${done?'completed':'primary'}" data-action="complete" ${quizLocked&&!done?'disabled':''}>${icon(done?'check':'check')}<span>${done?'已完成本节':quizLocked?'全部答对后，完成本节':'我已理解，标记完成'}</span></button>${next?`<a class="next-link" href="#${next.id}"><span><small>UP NEXT</small>${esc(next.title)}</span>${icon('arrow')}</a>`:`<a class="next-link" href="#architecture"><span><small>REVISIT THE MAP</small>回到架构图，重新看一遍</span>${icon('arrow')}</a>`}</div><div class="references"><span>本节参考</span>${lesson.sources.map(id=>`<a href="${esc(C.sources[id].url)}" target="_blank" rel="noopener noreferrer">${esc(C.sources[id].title.split(' · ')[0])} ↗</a>`).join('')}</div>`;
  }
  function detail() {
    const n=C.nodes[state.selected]??C.nodes.cm;
    return `<div class="panel detail-panel"><div class="detail-overline">当前选中 / COMPONENT<button class="icon-button" data-action="toggle-detail" aria-label="收起组件说明" aria-controls="detail-content" aria-expanded="true">${icon('close')}</button></div><div id="detail-content"><div class="component-symbol">${icon('layers')}</div><h2>${esc(n.title)}</h2><div class="detail-en">${esc(n.en)}</div><span class="detail-tag">${esc(n.tag)}</span><p class="detail-body">${esc(n.body)}</p><div class="analogy"><strong>换个角度理解</strong>${esc(n.analogy)}</div><div class="detail-example-label">IN PRACTICE / 实际例子</div><code class="detail-example">${esc(n.example)}</code><a class="detail-link" href="#${n.lesson}">去相关课程看看${icon('arrow')}</a><a class="detail-link" href="${esc(C.sources[n.source].url)}" target="_blank" rel="noopener noreferrer">阅读官方说明${icon('external')}</a></div></div><div class="panel note-panel"><h3>${icon('bulb')}先记住这一点</h3><p>状态回答“现在是多少”，命令回答“希望是多少”。Actuator 也可提供状态反馈，读取能力可按设备实现省略；图中以绿色虚线标出这条可选关系。</p></div>`;
  }
  function architecture() {
    return `<div class="workspace-grid"><section class="panel" aria-label="交互架构图"><div class="panel-head"><div class="panel-title"><h2>一张图，连接整个系统</h2><span class="en">THE ROS2_CONTROL ARCHITECTURE</span></div><button class="icon-button" data-action="download" title="下载当前视图 SVG" aria-label="下载当前架构图 SVG">${icon('download')}</button></div><div class="map-toolbar"><div class="segmented" role="group" aria-label="流程图视图">${[['all','架构全景'],['management','管理关系'],['state','状态反馈'],['command','命令下发']].map(([v,label])=>`<button data-mode="${v}" class="${state.mode===v?'active':''}" aria-pressed="${state.mode===v}">${label}</button>`).join('')}</div><span class="map-help">${icon('cursor')}点击节点，探索职责</span></div><div id="diagram" class="diagram-scroll">${window.LearningDiagram.render(state.mode,state.selected)}</div><div class="map-caption"><div class="legend"><span class="legend-item">管理 / 访问</span><span class="legend-item state">状态接口</span><span class="legend-item command">命令接口</span></div><span id="map-caption-text">依据官方架构重绘 · 虚线表示申领或可选关系</span></div></section><aside id="component-detail" class="detail-rail" aria-label="组件说明">${detail()}</aside></div><section class="section"><div class="section-heading"><h2>抓住这两个核心概念</h2><small>STATE ≠ COMMAND</small></div><div class="two-columns"><div class="concept-card"><div class="card-kicker">01 / STATE INTERFACE</div><h3>状态：机器人现在做到了什么</h3><p>硬件读取测量值，控制器按需读取反馈。例如：<code>left_wheel_joint/position</code> 是轮子当前的转角。</p></div><div class="concept-card amber"><div class="card-kicker">02 / COMMAND INTERFACE</div><h3>命令：我们希望机器人做什么</h3><p>控制器写入目标，硬件插件负责下发。例如：<code>left_wheel_joint/velocity</code> 是希望轮子达到的角速度。</p></div></div></section>`;
  }
  function start() {
    const basics=C.terms.filter(t=>['Node','Topic','Joint','URDF / Xacro','RViz'].includes(t.en));
    return `<div class="reading-layout"><section class="reading-card"><div class="eyebrow">MAKE THE CONNECTION</div><div class="big-sentence">你给出一个目标，<br><em>ros2_control 把算法与硬件连接起来。</em></div><p>想让机器人向前走，既要算出轮子该怎么转，也要把命令送到驱动器，再读回设备状态。ros2_control 为这些环节提供统一的接口与调度方式，帮助同一个控制器适配不同硬件。</p><div class="mini-flow"><div class="flow-item"><strong>一个目标</strong><small>“前进 0.3 m/s”</small></div>${icon('arrow')}<div class="flow-item"><strong>控制器</strong><small>换算左右轮速</small></div>${icon('arrow')}<div class="flow-item"><strong>硬件插件</strong><small>读取与下发</small></div>${icon('arrow')}<div class="flow-item"><strong>设备</strong><small>测量与执行</small></div></div><p><strong>ROS 2</strong> 提供节点、消息通信等基础能力；<strong>ros2_control</strong> 组织控制器与硬件的读写。它可以接真实设备，也可以接软件演示或仿真插件。</p><div class="tag-row"><span class="tag">中文讲解 · 英文术语保留</span><span class="tag">ROS 2 Jazzy</span><span class="tag">无需真实机器人</span></div></section><section class="reading-card"><h2>先认识几个常出现的词</h2><div class="term-list">${basics.map(t=>`<div class="term-row"><h3>${esc(t.title)}<span>${esc(t.en)}</span></h3><p>${esc(t.description)}</p></div>`).join('')}</div></section><section class="reading-card"><h2>学习前，准备好环境</h2><p>网页中的架构图、动画和测验可直接使用。实践部分需要你在自己的终端中操作：建议使用 Ubuntu 24.04 和 ROS 2 Jazzy，并先完成 ROS 2 的基本安装与环境配置。</p>${callout('网页演示与终端实验分开进行','本站不会执行 ROS 命令或连接设备。代码框中标注的命令需在自己的终端运行；课程使用的官方演示插件在软件中更新数值。')}${code('prerequisites')}<p>${sourceLink('rosinstall','尚未安装 ROS 2？先看 Jazzy 官方安装教程')}<br>${sourceLink('rosbasics','第一次接触 ROS 2？先完成基础命令行教程')}</p></section><section class="reading-card"><h2>按这个顺序，完成第一轮学习</h2><div class="path-list">${C.lessons.slice(1,7).map((l,i)=>`<a class="path-card" href="#${l.id}"><span>${String(i+1).padStart(2,'0')} / ${esc(l.en)}</span><h3>${esc(l.title)} ↗</h3><p>${esc(l.subtitle)}</p></a>`).join('')}</div></section></div>`;
  }
  const cycleDescriptions=[
    {title:'01 · read()：先知道设备现在怎样',body:'硬件组件读取设备状态，并更新 state interfaces。真实驱动可读取编码器；DiffBot 演示插件用上一轮速度与时间间隔积分位置。此时还没有执行本周期的新目标。'},
    {title:'02 · update()：由控制器计算新的目标',body:'控制器读取需要的输入和状态，执行算法，把结果写入 command interfaces。差速控制器把车体前进速度与转向速度换算成左右轮角速度。广播器也在这个阶段读取并发布状态。'},
    {title:'03 · write()：把目标交给硬件',body:'硬件插件读取 command interfaces，再向设备下发命令。DiffBot 演示只是把目标轮速镜像到软件中的速度状态；真实驱动需要在这里实现设备通信。下一轮再从 read() 开始。'}
  ];
  function cycle() {
    return `<div class="reading-layout"><section class="panel cycle-panel"><div class="section-heading"><h2>让一轮控制，慢下来</h2><span class="badge">交互演示</span></div><p class="cycle-caption"><span>点击阶段，或按顺序播放</span><span>教学动画 · 非真实频率 · 不连接机器人</span></p><div class="cycle-stage-list" role="group" aria-label="控制循环阶段">${[['read','读取状态'],['update','计算目标'],['write','下发命令']].map(([title,cn],i)=>`<button class="cycle-stage ${state.cycleStep===i?'active':''}" data-stage="${i}" aria-pressed="${state.cycleStep===i}"><span class="cycle-number">0${i+1}</span><strong>${title}()</strong><small>${cn}</small></button>`).join('')}</div><div id="cycle-description" class="cycle-description" aria-live="polite"></div><div class="cycle-controls"><button class="button primary" data-action="play" id="cycle-play">${icon('play')}播放一轮</button><button class="button secondary" data-action="step">${icon('step')}下一步</button><button class="icon-button" data-action="reset-cycle" aria-label="重置控制循环演示">${icon('reset')}</button><span class="cycle-count" id="cycle-count"></span></div></section><section class="reading-card section"><h2>把“向前”和“转向”，换算成轮速</h2><p>拖动速度滑块，观察两侧轮速如何变化。这里采用官方 DiffBot 示例的轮距 <code>0.10 m</code>、轮半径 <code>0.015 m</code>。</p><div class="simulator"><div class="sim-controls"><label for="linear-speed"><span class="range-heading"><span>前进速度 v</span><output for="linear-speed" id="linear-output">0.30 m/s</output></span><input id="linear-speed" type="range" min="-0.7" max="0.7" step="0.05" value="0.3"></label><label for="angular-speed"><span class="range-heading"><span>转向角速度 ω</span><output for="angular-speed" id="angular-output">0.50 rad/s</output></span><input id="angular-speed" type="range" min="-1" max="1" step="0.1" value="0.5"></label></div><div class="sim-values" aria-live="polite"><div class="wheel-value"><span>左轮 / LEFT WHEEL</span><strong id="left-wheel-value"></strong><small>rad/s</small></div><div class="wheel-value"><span>右轮 / RIGHT WHEEL</span><strong id="right-wheel-value"></strong><small>rad/s</small></div></div></div><div class="formula">左轮角速度 = (v − ω × 轮距 / 2) / 轮半径<br>右轮角速度 = (v + ω × 轮距 / 2) / 轮半径</div><p class="microcopy">这是理想稳态换算，未模拟加速度限制、滑移或真实动力学。左右轮半径不同时应分别换算。本地示例的 update_rate 为 10 Hz；这里的慢速动画仅用于讲解顺序。</p></section><section class="reading-card"><h2>话题通信 ≠ 内部接口</h2><p><code>/cmd_vel</code> 把外部目标送给控制器；<code>left_wheel_joint/velocity</code> 是框架内部的命令接口。它们通过控制器的计算联系起来，并不是同一个东西。</p>${callout('read → update → write 是一轮的先后顺序','真实设备的反馈会随时间更新，目标与测量值也可能不同。理解顺序后，再研究控制频率、超时、硬件延迟和控制器算法。')}</section></div>`;
  }
  const fileDescriptions={
    urdf:{label:'声明机器人能提供什么接口',body:'先找到关节，再读它下面的 command_interface 和 state_interface。硬件插件通过 plugin 字符串加载。Xacro 用宏和参数组织文件，生成的机器人描述交给 ROS 2 节点。'},
    yaml:{label:'选择控制器，告诉它怎么工作',body:'控制器实例名、插件类型、关节列表、轮距、半径、超时等都在配置里。同一个 left_wheel_joint 必须与机器人描述一致；type 选的是控制器插件，不是硬件插件。'},
    cpp:{label:'把统一接口翻译为设备通信',body:'框架负责管理接口，硬件插件负责处理设备的具体协议与数值。read() 更新状态，write() 下发命令；还需处理初始化、激活、停用和错误。这里只用伪代码说明职责。'},
    launchfile:{label:'把模型、控制节点与控制器启动起来',body:'launch 组织多个 ROS 2 节点并传递参数。官方示例的 spawner 加载控制器与 YAML；robot_state_publisher 提供机器人描述；ros2_control_node 运行管理器。'}
  };
  function fileContent() {const f=fileDescriptions[state.file];return `<div class="file-role">${esc(f.label)}</div><p>${esc(f.body)}</p>${code(state.file)}`;}
  function files() {
    return `<div class="reading-layout"><section class="reading-card"><h2>同一条控制链路，四块工程拼图</h2><p>不要一上来通读整个仓库。先选一个关节名，追踪它在模型、控制器配置与插件中的对应关系，再看 launch 如何把它们连接起来。</p><div class="file-tabs" role="tablist" aria-label="示例文件类型">${[['urdf','模型与接口','URDF / Xacro'],['yaml','控制器配置','YAML'],['cpp','硬件插件','C++'],['launchfile','组织启动','Launch']].map(([id,title,en])=>`<button role="tab" id="tab-${id}" aria-controls="file-content" aria-selected="${state.file===id}" tabindex="${state.file===id?'0':'-1'}" data-file="${id}" class="${state.file===id?'active':''}">${title}<span>${en}</span></button>`).join('')}</div><div class="file-content" id="file-content" role="tabpanel" aria-labelledby="tab-${state.file}">${fileContent()}</div></section><section class="reading-card"><h2>用一个名字把它们串起来</h2><div class="mini-flow"><div class="flow-item"><strong>URDF</strong><small>声明 left_wheel_joint</small></div>${icon('arrow')}<div class="flow-item"><strong>YAML</strong><small>选择 left_wheel_names</small></div>${icon('arrow')}<div class="flow-item"><strong>硬件插件</strong><small>读写对应接口</small></div></div>${callout('三个名字，各有分工','<code>DiffBot</code> 是硬件组件名，<code>diffbot_base_controller</code> 是控制器实例名，<code>diff_drive_controller/DiffDriveController</code> 是控制器插件类型。它们不需要一样，但各处引用必须准确。')}${callout('这些是讲解片段，不是完整工程','省略了机器人结构、参数、生命周期、导出和 imports。初次运行请使用完整的官方 example_2，点每段代码下方的源码链接逐项对照。',true)}</section><section class="reading-card"><h2>接下来读哪个示例？</h2><div class="resource-grid"><a class="resource-card" href="${C.sources.rrbot.url}" target="_blank" rel="noopener noreferrer"><small>EXAMPLE 1</small>RRBot · 对照 position 接口 ↗</a><a class="resource-card" href="${C.sources.transmission.url}" target="_blank" rel="noopener noreferrer"><small>EXAMPLE 8</small>Transmissions · 理解传动映射 ↗</a></div></section></div>`;
  }
  function diffbot() {
    const steps=[
      {title:'搭建独立练习工作空间',body:'先完成“从零开始”中的环境准备。下面仅从源码构建 demos 及其所需本地包，外部依赖由 rosdep 解析。先确保 rosdep 已初始化；切勿混入 Rolling/master 版本的核心包。',snippets:['setup'],expected:'colcon 最后显示构建成功；若失败先读第一个 error，再确认当前 ROS_DISTRO 为 jazzy。若 demos 使用了尚未发布的 API，按官方安装文档使用配套 Jazzy 核心源码，不要改用 Rolling。'},
      {title:'启动 DiffBot',body:'打开终端 A，加载环境，再启动完整示例。view_robot.launch.py 仅用于看模型，不能代替这里的 diffbot.launch.py。',snippets:['source','launch'],expected:'默认出现 RViz 中的底盘模型；启动终端持续运行。演示硬件插件已加载，不需要真实底盘。'},
      {title:'先检查，再发布',body:'打开终端 B，同样先执行环境加载命令，再检查 manager、控制器、接口和话题。顺序、空格或颜色可能不同，重点看名称和状态。',snippets:['inspect'],expected:'<ul><li><code>diffbot_base_controller</code> 与 <code>joint_state_broadcaster</code> 都为 <strong>active</strong>。</li><li>命令接口 <code>left_wheel_joint/velocity</code>、<code>right_wheel_joint/velocity</code> 为 <strong>[available] [claimed]</strong>。</li><li>左右轮各有 position、velocity 状态接口；硬件组件 <code>DiffBot</code> 为 active。</li><li><code>/cmd_vel</code> 的类型为 <code>geometry_msgs/msg/TwistStamped</code>，有控制器订阅者。</li></ul>'},
      {title:'发送车体速度目标',body:'在终端 B 持续发布。前进和转向同时存在，底盘会沿圆弧运动；加速度限制可能让速度逐步到达目标，不要要求首个周期立即得到稳态结果。',snippets:['drive'],expected:'RViz 中的演示底盘运动，启动终端出现轮速命令。稳定到达此目标后，理想左右轮角速度约为 43.33、50.00 rad/s。'},
      {title:'观察状态与里程计',body:'保持发布端运行，打开终端 C 并加载环境。分别看关节状态和里程计，不要把命令输入、状态反馈、里程计三者混为一谈。',snippets:['observe'],expected:'joint_states 的左右轮位置持续变化。这验证的是软件演示链路；默认 open_loop=true，里程计来自车体目标速度积分。'},
      {title:'停止并回顾链路',body:'先在发布终端 Ctrl+C 停掉非零命令，改发零速度，观察停止后退出。最后关闭 launch。回顾：外部话题 → 控制器 → 命令接口 → 硬件插件；硬件状态经广播器对外可见。',snippets:['stop'],expected:'停止运动并结束相关进程。能解释每个终端在做什么，比只看到模型移动更重要。'}
    ];
    return `<div class="reading-layout">${callout('本实验范围：官方软件演示，不连接实体机器人','以 Jazzy 的 example_2 Python launch 为准，核对提交 <code>'+C.commit.slice(0,12)+'</code>。网页不会代为安装、构建或执行任何 ROS 命令。')}<div class="reading-card"><h2>先看清实验里的四种名字</h2><div class="term-list">${[['manager 节点','/controller_manager'],['硬件组件','DiffBot'],['控制器实例','diffbot_base_controller'],['控制器插件','diff_drive_controller/DiffDriveController']].map(([title,value])=>`<div class="term-row"><h3>${title}</h3><p><code>${esc(value)}</code></p></div>`).join('')}</div>${callout('为什么是 /cmd_vel？','差速控制器的原始订阅是 <code>~/cmd_vel</code>。本提交的 launch 使用 <code>-r ~/cmd_vel:=/cmd_vel</code> 重映射。换用自己的 launch 时，要重新检查实际话题。',true)}</div>${steps.map((s,i)=>`<section class="step-card"><span class="step-number">${String(i+1).padStart(2,'0')}</span><h2>${s.title}</h2><p>${s.body}</p>${s.snippets.map(code).join('')}<div class="expected"><strong>你应该观察到</strong>${s.expected}</div></section>`).join('')}<section class="reading-card"><h2>拓展：换一种接口，框架仍然相同</h2><p>RRBot 使用 position 接口与位置控制器。读完 DiffBot 后，可以单独构建并运行 example_1，比较两种命令接口。</p>${code('rrbot')}</section></div>`;
  }
  function diagnose() {
    return `<div class="reading-layout"><section class="reading-card"><h2>“加载了”不等于“正在工作”</h2><p>控制器和硬件组件各有生命周期。排错时分别检查两者；不要只看进程是否存在。下面以控制器的常见流程帮助记忆，具体回调和硬件行为要以实现为准。</p><div class="lifecycles"><div class="lifecycle-step"><span class="stage-id">01</span><h3>unconfigured</h3><p>对象已初始化，尚未完成工作所需的配置。</p></div><div class="lifecycle-step"><span class="stage-id">02</span><h3>inactive</h3><p>已配置，等待激活。控制器尚未进入正常更新工作状态。</p></div><div class="lifecycle-step"><span class="stage-id">03</span><h3>active</h3><p>激活的控制器参与更新；需要的硬件与接口也必须可用。</p></div></div>${callout('分别看控制器与硬件','用 <code>list_controllers</code> 检查控制器，用 <code>list_hardware_components</code> 检查硬件。硬件 inactive 状态下的读写和停机行为与实现有关，不应把生命周期状态当作急停。',true)}<p>${sourceLink('lifecycle','了解硬件组件的具体状态与回调')}</p></section><div class="section-heading section"><h2>从现象出发，逐层检查</h2><small>OBSERVE → LOCATE → VERIFY</small></div>${C.issues.map((issue,i)=>`<details class="issue"><summary>${icon('chevron')}${esc(issue.title)}<span class="issue-en">${esc(issue.en)}</span></summary><div class="issue-content"><p>${esc(issue.body)}</p>${codeRaw('issue-'+i,'检查命令','bash',issue.code,issue.source)}<div class="expected"><strong>判断依据</strong>${esc(issue.expect)}</div></div></details>`).join('')}<section class="reading-card section"><h2>先明确“反馈正常”的证据</h2><p>话题在发、控制器 active、接口 claimed、里程计变化，都只说明控制链路中的某一层。真实底盘还要核对编码器读数、驱动器通信、实际运动与单位换算。</p>${callout('一个实用的排查顺序','环境和节点 → 控制器生命周期 → 接口名称与占用 → 消息类型和时间戳 → 硬件 read/write → 实际反馈。每次只改变一个条件，再验证现象。')}</section></div>`;
  }
  function quizCard(q,i) {
    const answer=state.answers.get(i),answered=answer!==undefined;
    return `<section class="quiz-card" id="question-${i}"><div class="quiz-kicker">QUESTION ${String(i+1).padStart(2,'0')} / ${String(C.quizzes.length).padStart(2,'0')}</div><h2>${esc(q.q)}</h2><div class="quiz-choices" role="group" aria-label="第 ${i+1} 题选项">${q.choices.map((choice,j)=>`<button class="quiz-option${answered&&j===q.answer?' correct':''}${answered&&j===answer&&answer!==q.answer?' wrong':''}" data-question="${i}" data-answer="${j}" aria-pressed="${answer===j}"><span>${String.fromCharCode(65+j)}</span><span>${esc(choice)}</span></button>`).join('')}</div><div class="quiz-feedback-area" aria-live="polite">${answered?`<div class="quiz-feedback"><strong>${answer===q.answer?'理解正确。':'再想一想，正确选项已标出。'}</strong> ${esc(q.explanation)}<br><a href="#${q.lesson}">回到相关课程复习 →</a></div>`:''}</div></section>`;
  }
  function quizSummary() {const score=C.quizzes.filter((q,i)=>state.answers.get(i)===q.answer).length;return `<div><strong>${score}<small> / ${C.quizzes.length}</small></strong><span style="margin-left:14px">${score===C.quizzes.length?'这一轮，你已经把链路连接起来了。':'可以重新选择答案，直到理解为止。'}</span></div><button class="button secondary" data-action="retry-quiz">重新自测</button>`;}
  function quiz() {return `<div class="reading-layout"><div id="quiz-summary" class="quiz-summary" aria-live="polite">${quizSummary()}</div><div id="quiz-questions">${C.quizzes.map(quizCard).join('')}</div></div>`;}
  const pages={start,architecture,cycle,files,diffbot,diagnose,quiz};
  function renderNav() {
    $('#course-nav').innerHTML=C.lessons.map((l,i)=>`<a class="nav-link ${state.id===l.id?'active':''}" href="#${l.id}" ${state.id===l.id?'aria-current="page"':''}><span class="nav-number">${String(i+1).padStart(2,'0')}</span><span class="nav-copy"><strong>${esc(l.title)}</strong><small>${esc(l.en)}</small></span>${progress.has(l.id)?'<span class="nav-check" aria-label="已完成">✓</span>':''}</a>`).join('');
    const count=progress.get().length;
    $('#progress-fraction').textContent=`${count} / ${ids.length}`;
    $('#progress-fill').style.width=`${count/ids.length*100}%`;
    $('.progress-track').setAttribute('aria-valuenow',String(count));
    $('#progress-note').textContent=count===ids.length?'第一轮完成，随时回来复习。':progress.isPersistent()?'进度保存在此浏览器。':'当前进度仅保留在本次页面会话。';
  }
  function stopCycle() {if(state.timer!==null)window.clearInterval(state.timer);state.timer=null;state.playing=false;}
  function render(focus=false) {
    stopCycle();copyTexts.clear();
    state.id=L.resolveLesson(location.hash,ids);
    if(location.hash!==`#${state.id}`)history.replaceState(null,'',`#${state.id}`);
    const lesson=C.lessons.find(l=>l.id===state.id);
    document.title=`${lesson.title} · ros2_control 学习工坊`;
    $('#breadcrumb-current').textContent=lesson.title;
    $('#main').innerHTML=lessonHeader(lesson)+pages[state.id]()+chapterEnd(lesson);
    renderNav();setMenu(false);
    if(state.id==='cycle'){updateCycle();updateSpeeds();}
    if(focus){window.scrollTo({top:0,behavior:'instant'});$('#main').focus({preventScroll:true});}
  }
  function goTo(id) {if(!ids.includes(id))return;if(location.hash===`#${id}`)render(true);else location.hash=id;}
  function toast(message) {clearTimeout(toastTimer);$('#toast').textContent=message;$('#toast').classList.add('visible');toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),3000);}
  function setMenu(open) {
    $('#sidebar').classList.toggle('open',open);$('#nav-backdrop').hidden=!open;
    $('.mobile-menu').setAttribute('aria-expanded',String(open));
    $('.mobile-menu').setAttribute('aria-label',open?'收起课程导航':'展开课程导航');
    document.body.style.overflow=open?'hidden':'';
    $('#sidebar').inert=!open&&window.matchMedia('(max-width:760px)').matches;
  }
  function renderSearch(query) {
    const key=query.trim().toLowerCase();
    const results=[...C.lessons.map(l=>({title:l.title,en:l.en,description:l.subtitle,lesson:l.id})),...C.terms].filter(t=>`${t.title} ${t.en} ${t.description}`.toLowerCase().includes(key)).slice(0,key?30:12);
    $('#search-results').innerHTML=results.length?results.map(t=>`<button class="search-result" data-result-lesson="${t.id&&C.nodes[t.id]?'architecture':t.lesson}" ${t.id&&C.nodes[t.id]?`data-result-node="${t.id}"`:''}><h3>${esc(t.title)}<small>${esc(t.en)}</small></h3><p>${esc(t.description)}</p></button>`).join(''):`<div class="search-empty">没有找到“${esc(query)}”。试试中文概念或英文关键词。</div>`;
  }
  function openSearch() {setMenu(false);$('#search-input').value='';renderSearch('');$('#search-dialog').showModal();$('#search-input').focus();}
  function openSources() {
    $('#sources-dialog').innerHTML=`<div class="dialog-top"><h2 id="sources-title">从官方资料继续深入</h2><button class="icon-button" data-close="sources-dialog" aria-label="关闭来源说明">${icon('close')}</button></div><p class="source-explainer">独立中文学习资料，并非官方翻译。正文与流程图按学习顺序重新编写；示例代码片段均注明简化范围，不能替代完整工程。版本为 ROS 2 Jazzy，资料核对日期 ${C.checked}。本地示例核对提交：<code>${C.commit.slice(0,12)}</code>。</p><div class="source-list">${Object.values(C.sources).map(s=>`<a class="source-link" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer"><span>${esc(s.title)}<small>${esc(s.url)}</small></span>${icon('external')}</a>`).join('')}</div><div class="dialog-foot"><span>基于 ros-controls 官方文档与 Apache-2.0 示例</span><span>所有命令需自行在终端操作</span></div>`;
    $('#sources-dialog').showModal();
  }
  async function copyCode(id,button) {
    const text=copyTexts.get(id);if(text===undefined)return;
    let copied=false;
    try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(text);copied=true;}}catch{/* 不支持自动复制时使用选区。 */}
    if(!copied){const area=document.createElement('textarea');area.value=text;area.style.cssText='position:fixed;left:-10000px;top:0';document.body.append(area);area.select();try{copied=document.execCommand('copy');}catch{}area.remove();button?.focus({preventScroll:true});}
    if(copied){toast('代码已复制，请在自己的终端或编辑器中使用。');return;}
    const dialog=document.createElement('dialog');dialog.className='reset-dialog';dialog.setAttribute('aria-label','手动复制代码');dialog.innerHTML=`<h2>请手动复制</h2><p>浏览器未允许自动复制。文本已选中，按 Ctrl+C 或 ⌘C。</p><textarea class="manual-copy" readonly aria-label="待复制的代码"></textarea><div class="dialog-actions"><button class="button secondary">关闭</button></div>`;document.body.append(dialog);$('textarea',dialog).value=text;$('button',dialog).onclick=()=>dialog.close();dialog.addEventListener('close',()=>{dialog.remove();button?.focus();});dialog.showModal();$('textarea',dialog).select();
  }
  function updateDiagram(focusedNode) {
    $('#diagram').innerHTML=window.LearningDiagram.render(state.mode,state.selected);
    $('#component-detail').innerHTML=detail();
    $$('[data-mode]').forEach(b=>{const active=b.dataset.mode===state.mode;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
    $('#map-caption-text').textContent=state.mode==='state'||state.mode==='command'?'教学数据流示意 · 隐去管理关系以便理解方向':'依据官方架构重绘 · 虚线表示申领或可选关系';
    if(focusedNode)$(`[data-node="${focusedNode}"]`)?.focus({preventScroll:true});
  }
  function downloadDiagram() {
    const original=$('.architecture-svg'),clone=original.cloneNode(true);
    const originals=[original,...original.querySelectorAll('*')],clones=[clone,...clone.querySelectorAll('*')];
    originals.forEach((el,i)=>{const style=getComputedStyle(el);['fill','stroke','stroke-width','stroke-dasharray','opacity','font-family','font-size','font-weight','paint-order','stroke-linecap','stroke-linejoin'].forEach(p=>clones[i].style.setProperty(p,style.getPropertyValue(p)));clones[i].style.setProperty('animation','none');clones[i].removeAttribute('tabindex');clones[i].removeAttribute('data-node');});
    clone.setAttribute('width','920');clone.setAttribute('height','963');
    const xml=new XMLSerializer().serializeToString(clone),url=URL.createObjectURL(new Blob([xml],{type:'image/svg+xml;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download=`ros2-control-jazzy-${state.mode}.svg`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);toast('已导出当前双语 SVG 视图。');
  }
  function updateCycle() {
    if(state.id!=='cycle')return;
    const d=cycleDescriptions[state.cycleStep];
    $('#cycle-description').innerHTML=`<h3>${d.title}</h3><p>${d.body}</p>`;
    $$('[data-stage]').forEach(b=>{const active=Number(b.dataset.stage)===state.cycleStep;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
    $('#cycle-play').innerHTML=icon(state.playing?'pause':'play')+(state.playing?'暂停演示':'播放循环');
    $('#cycle-count').textContent=`已演示 ${state.cycles} 轮 · 阶段 ${state.cycleStep+1} / 3`;
  }
  function nextCycle() {state.cycleStep=(state.cycleStep+1)%3;if(state.cycleStep===0)state.cycles++;updateCycle();}
  function updateSpeeds() {
    const v=Number($('#linear-speed').value),w=Number($('#angular-speed').value),speeds=L.wheelSpeeds(v,w,0.10,0.015);
    $('#linear-output').textContent=`${v.toFixed(2)} m/s`;$('#angular-output').textContent=`${w.toFixed(2)} rad/s`;
    $('#left-wheel-value').textContent=speeds.left.toFixed(2);$('#right-wheel-value').textContent=speeds.right.toFixed(2);
  }
  function chooseFile(id,focus=false) {
    if(!fileDescriptions[id])return;state.file=id;
    $$('[data-file]').forEach(b=>{const active=b.dataset.file===id;b.classList.toggle('active',active);b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
    $('#file-content').innerHTML=fileContent();$('#file-content').setAttribute('aria-labelledby',`tab-${id}`);
    if(focus)$(`[data-file="${id}"]`).focus();
  }
  function answerQuiz(i,j,focus=false) {
    if(!C.quizzes[i]||!Number.isInteger(j)||j<0||j>=C.quizzes[i].choices.length)return;
    state.answers.set(i,j);$(`#question-${i}`).outerHTML=quizCard(C.quizzes[i],i);$('#quiz-summary').innerHTML=quizSummary();
    const complete=$('#complete-lesson');if(!progress.has('quiz')){const ready=C.quizzes.every((q,index)=>state.answers.get(index)===q.answer);complete.disabled=!ready;$('span:last-child',complete).textContent=ready?'我已理解，标记完成':'全部答对后，完成本节';}
    if(focus)$(`[data-question="${i}"][data-answer="${j}"]`).focus({preventScroll:true});
  }
  document.addEventListener('click',event=>{
    const target=event.target.closest('button,a,[data-node]');if(!target)return;
    if(target.dataset.close){$( '#'+target.dataset.close).close();return;}
    if(target.dataset.copy){copyCode(target.dataset.copy,target);return;}
    if(target.dataset.node&&C.nodes[target.dataset.node]){state.selected=target.dataset.node;updateDiagram(event.detail===0?state.selected:null);return;}
    if(target.dataset.mode){state.mode=target.dataset.mode;state.selected=({state:'state',command:'command',management:'cm'})[state.mode]??state.selected;updateDiagram();return;}
    if(target.dataset.file){chooseFile(target.dataset.file);return;}
    if(target.dataset.stage!==undefined){stopCycle();state.cycleStep=Number(target.dataset.stage);updateCycle();return;}
    if(target.dataset.question!==undefined){answerQuiz(Number(target.dataset.question),Number(target.dataset.answer),true);return;}
    if(target.dataset.resultLesson){$('#search-dialog').close();if(target.dataset.resultNode){state.selected=target.dataset.resultNode;state.mode='all';}goTo(target.dataset.resultLesson);return;}
    if(target.classList.contains('nav-link')&&target.hash===location.hash){event.preventDefault();setMenu(false);$('#main').focus({preventScroll:true});return;}
    switch(target.dataset.action){
      case 'menu':setMenu(!$('#sidebar').classList.contains('open'));if($('#sidebar').classList.contains('open'))$('.nav-link.active').focus();break;
      case 'search':openSearch();break;
      case 'sources':setMenu(false);openSources();break;
      case 'reset':setMenu(false);$('#reset-dialog').showModal();break;
      case 'confirm-reset':progress.reset();state.answers.clear();$('#reset-dialog').close();renderNav();render(false);toast('学习进度已重置，可以重新开始。');break;
      case 'complete':if(target.disabled)break;progress.complete(state.id);renderNav();target.className='button completed';target.innerHTML=icon('check')+'<span>已完成本节</span>';toast(progress.isPersistent()?'已标记完成，进度保存在此浏览器。':'已标记完成；浏览器未允许保存，刷新后可能丢失。');break;
      case 'download':downloadDiagram();break;
      case 'toggle-detail':{const content=$('#detail-content');content.hidden=!content.hidden;target.setAttribute('aria-expanded',String(!content.hidden));target.setAttribute('aria-label',content.hidden?'展开组件说明':'收起组件说明');target.innerHTML=icon(content.hidden?'chevron':'close');break;}
      case 'play':if(state.playing){stopCycle();}else{state.playing=true;state.timer=setInterval(nextCycle,1600);}updateCycle();break;
      case 'step':stopCycle();nextCycle();break;
      case 'reset-cycle':stopCycle();state.cycleStep=0;state.cycles=0;updateCycle();break;
      case 'retry-quiz':state.answers.clear();$('#quiz-questions').innerHTML=C.quizzes.map(quizCard).join('');$('#quiz-summary').innerHTML=quizSummary();if(!progress.has('quiz')){$('#complete-lesson').disabled=true;$('#complete-lesson span:last-child').textContent='全部答对后，完成本节';}toast('题目已重置，可开始新一轮自测。');break;
      case 'skip':event.preventDefault();$('#main').focus();break;
    }
  });
  document.addEventListener('keydown',event=>{
    const target=event.target;
    if((event.key==='Enter'||event.key===' ')&&target.matches('[data-node]')){event.preventDefault();target.dispatchEvent(new MouseEvent('click',{bubbles:true,detail:0}));return;}
    if(target.matches('[data-file]')&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const keys=Object.keys(fileDescriptions),i=keys.indexOf(state.file);chooseFile(keys[event.key==='Home'?0:event.key==='End'?keys.length-1:(i+(event.key==='ArrowRight'?1:-1)+keys.length)%keys.length],true);return;}
    if(event.key==='/'&&!target.matches('input,textarea,[contenteditable="true"]')&&!$('dialog[open]')){event.preventDefault();openSearch();}
    if(event.key==='Escape'&&$('#sidebar').classList.contains('open')){setMenu(false);$('.mobile-menu').focus();}
    if(event.key==='Tab'&&$('#sidebar').classList.contains('open')){const items=$$('a,button', $('#sidebar')).filter(el=>!el.disabled);if(event.shiftKey&&target===items[0]){event.preventDefault();items.at(-1).focus();}else if(!event.shiftKey&&target===items.at(-1)){event.preventDefault();items[0].focus();}}
  });
  $('#search-input').addEventListener('input',e=>renderSearch(e.target.value));
  $('#main').addEventListener('input',event=>{if(['linear-speed','angular-speed'].includes(event.target.id))updateSpeeds();});
  $('#nav-backdrop').addEventListener('click',()=>{setMenu(false);$('.mobile-menu').focus();});
  window.addEventListener('hashchange',()=>render(true));
  window.addEventListener('resize',()=>{if(!window.matchMedia('(max-width:760px)').matches)setMenu(false);else if(!$('#sidebar').classList.contains('open'))$('#sidebar').inert=true;});
  window.addEventListener('pagehide',stopCycle);
  document.addEventListener('visibilitychange',()=>{if(document.hidden){stopCycle();updateCycle();}});
  $$('.icon[data-icon]').forEach(el=>el.innerHTML=svgIcon(el.dataset.icon));
  $('.skip-link').dataset.action='skip';
  render();
})();
