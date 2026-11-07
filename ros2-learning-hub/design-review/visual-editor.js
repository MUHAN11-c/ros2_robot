/* 原排版上的正文编辑器，不更换阅读器的章节结构。
 * 输入：本站已渲染的章节节点、对应正文指纹、独立草稿；输出：按稳定字段编号保存的修改。
 * 仅标题/文字/单元格/代码可编辑，公式、实验、来源与导航保留组件结构。
 * 草稿中的 HTML 只允许有限行内标签，每次读取再次清理；不接受样式、事件或外部图片。
 */
(function (root) {
  'use strict';
  const L=root.NarukamiLogic, E=L.esc;
  const selector='h1,h2,h3,h4,h5,h6,p,li,th,td,pre > code,.code-explanation,.inline-notice,.exercise-question,figcaption';
  const protectedSelector='.chapter-actions,.chapter-pager,.chapter-note-link,.draft-notice,.visual-editor-bar,.chapter-meta,.source-note,.lab-card,.static-figure';
  const ignoredTags=new Set(['SCRIPT','STYLE','IFRAME','OBJECT','EMBED','IMG','SVG','MATH','INPUT','TEXTAREA','BUTTON']);

  // 指纹用于发现正文已换版，不作密码学认证；输入长度也参与，避免不同正文套用旧字段。
  function fingerprint(text) {
    text='fields-2\n'+text;
    let hash=2166136261;
    for(let i=0;i<text.length;i++)hash=Math.imul(hash^text.charCodeAt(i),16777619);
    return 'visual-v1-'+text.length+'-'+(hash>>>0).toString(16);
  }
  function inlineHtml(node) {
    if(node.nodeType===3)return E(node.nodeValue.replace(/\u00a0/g,' '));
    if(node.nodeType!==1&&node.nodeType!==11)return '';
    if(node.nodeType===1&&(node.matches('.section-anchor,[data-edit-decoration]')||ignoredTags.has(node.tagName)))return '';
    const body=[...node.childNodes].map(inlineHtml).join('');
    const tag=node.tagName;
    if(tag==='BR')return '<br>';
    if(tag==='STRONG'||tag==='B')return '<strong>'+body+'</strong>';
    if(tag==='EM'||tag==='I')return '<em>'+body+'</em>';
    if(tag==='CODE')return '<code>'+body+'</code>';
    if(tag==='A'){
      const href=node.getAttribute('href')||'';
      return /^(https?:\/\/|#\/)/i.test(href)?'<a href="'+E(href)+'" target="_blank" rel="noopener noreferrer">'+body+'</a>':body;
    }
    if(tag==='DIV'||tag==='P')return body+'<br>';
    return body;
  }
  function safeInline(value) {
    const template=document.createElement('template');template.innerHTML=String(value);
    return inlineHtml(template.content).replace(/(?:<br>)+$/,'');
  }
  function plainText(value) {
    const template=document.createElement('template');template.innerHTML=safeInline(value);
    return template.content.textContent;
  }
  function editableNodes(container) {
    const nodes=[...container.querySelectorAll(selector)].filter(node=>{
      if(node.closest(protectedSelector))return false;
      if(node.closest('.equation')&&!node.matches('p,th,td,figcaption'))return false;
      return !node.closest('math');
    });
    return nodes.filter(node=>!nodes.some(parent=>parent!==node&&parent.contains(node)));
  }
  function mount({container,base,draft,editable,onChange,renderCode}) {
    const nodes=editableNodes(container),fields=new Map(),undo=[],redo=[];
    let dirty=false,composing=false,lastEdit=null;
    const compatible=!!draft&&draft.base===base;
    nodes.forEach((node,index)=>{
      const key='f'+index+'-'+node.tagName.toLowerCase();
      node.dataset.editKey=key;
      if(node.matches('.exercise-item > summary'))node.firstElementChild?.setAttribute('data-edit-decoration','');
      const decoration=[...node.querySelectorAll('.section-anchor,[data-edit-decoration]')].map(n=>n.cloneNode(true));
      const code=node.tagName==='CODE';
      // 根段落本身不应增加一个换行；只清理它的子节点。
      const value=()=>code?node.textContent:[...node.childNodes].map(inlineHtml).join('').replace(/(?:<br>)+$/,'');
      const original=value();
      const field={key,node,code,original,current:original,decoration,value};
      function draw(text){
        if(code){if(editable)node.textContent=text;else node.innerHTML=renderCode(text);}
        else node.innerHTML=safeInline(text);
        for(const piece of decoration){const copy=piece.cloneNode(true);copy.contentEditable='false';node.append(copy);}
      }
      field.draw=draw;
      if(compatible&&typeof draft.fields[key]==='string'){draw(draft.fields[key]);field.current=value();}
      else if(code&&editable)draw(original);
      if(editable){
        node.querySelectorAll('.section-anchor,[data-edit-decoration]').forEach(piece=>piece.contentEditable='false');
        node.contentEditable=code?'plaintext-only':'true';node.spellcheck=false;
        node.setAttribute('aria-label',({H1:'章节标题',H2:'小节标题',H3:'段落标题',TH:'表头',TD:'表格单元格',CODE:'代码',LI:'列表条目',SPAN:'练习题目'})[node.tagName]||'正文文字');
        if(code)node.setAttribute('aria-multiline','true');
      }
      fields.set(key,field);
    });
    function selectedField(){
      const selection=getSelection(),node=selection?.anchorNode;
      const element=node?.nodeType===1?node:node?.parentElement;
      return fields.get(element?.closest('[data-edit-key]')?.dataset.editKey);
    }
    function changed(field){
      const next=field.value();if(next===field.current)return;
      const time=Date.now();
      if(lastEdit&&lastEdit.key===field.key&&time-lastEdit.time<750&&undo.length){undo.at(-1).after=next;lastEdit.time=time;}
      else{undo.push({key:field.key,before:field.current,after:next});lastEdit={key:field.key,time};}
      if(undo.length>100)undo.shift();redo.length=0;field.current=next;dirty=true;onChange();
    }
    function input(event){const field=fields.get(event.target.closest('[data-edit-key]')?.dataset.editKey);if(field&&!composing)changed(field);}
    function insertText(text){
      const selection=getSelection(),field=selectedField();if(!field||!selection.rangeCount)return;
      const range=selection.getRangeAt(0);
      if(!field.node.contains(range.commonAncestorContainer))return;
      range.deleteContents();const node=document.createTextNode(text);range.insertNode(node);range.setStartAfter(node);range.collapse(true);selection.removeAllRanges();selection.addRange(range);changed(field);
    }
    function paste(event){if(!selectedField())return;event.preventDefault();insertText(event.clipboardData.getData('text/plain'));}
    function drop(event){event.preventDefault();if(selectedField())insertText(event.dataTransfer.getData('text/plain'));}
    function beforeInput(event){if(event.inputType==='insertParagraph'&&selectedField()){event.preventDefault();insertText('\n');}}
    function click(event){if(event.target.closest('[data-edit-key]')&&event.target.closest('a,summary'))event.preventDefault();}
    function history(direction){
      const source=direction==='undo'?undo:redo,target=direction==='undo'?redo:undo,entry=source.pop();
      if(!entry)return false;
      const field=fields.get(entry.key),value=direction==='undo'?entry.before:entry.after;
      field.draw(value);field.current=field.value();target.push(entry);lastEdit=null;dirty=true;onChange();
      field.node.focus({preventScroll:true});const range=document.createRange();range.selectNodeContents(field.node);range.collapse(false);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);return true;
    }
    function keydown(event){
      if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'&&!event.isComposing){event.preventDefault();history(event.shiftKey?'redo':'undo');}
    }
    function compositionStart(){composing=true;}
    function compositionEnd(event){composing=false;input(event);}
    const handlers={input,paste,drop,beforeinput:beforeInput,click,keydown,compositionstart:compositionStart,compositionend:compositionEnd};
    if(editable)for(const [type,handler] of Object.entries(handlers))container.addEventListener(type,handler);
    function snapshot(){
      const changes=Object.create(null);
      for(const [key,field] of fields){const value=field.value();if(value!==field.original)changes[key]=value;}
      return {base,fields:changes};
    }
    return {
      editable,compatible,stale:!!draft&&!compatible,get dirty(){return dirty;},snapshot,
      get count(){return Object.keys(snapshot().fields).length;},
      format(tag){
        const field=selectedField(),selection=getSelection();
        if(!field||field.code||!selection.rangeCount||selection.isCollapsed)return false;
        const range=selection.getRangeAt(0);if(!field.node.contains(range.commonAncestorContainer))return false;
        const wrapper=document.createElement(tag==='code'?'code':'strong');wrapper.append(range.extractContents());range.insertNode(wrapper);range.selectNodeContents(wrapper);selection.removeAllRanges();selection.addRange(range);lastEdit=null;changed(field);return true;
      },
      undo:()=>history('undo'),redo:()=>history('redo'),
      destroy(){for(const [type,handler] of Object.entries(handlers))container.removeEventListener(type,handler);}
    };
  }

  // 源码入口和下载在需要时转换当前排版，日常保存只保存字段修改，保留原有折叠与组件结构。
  function toMarkdown(container,{figure}={}) {
    function inline(node){
      if(node.nodeType===3)return node.nodeValue.replace(/\u00a0/g,' ');
      if(node.nodeType!==1||node.matches('.section-anchor,[data-edit-decoration],button,svg'))return '';
      const text=[...node.childNodes].map(inline).join(''),tag=node.tagName;
      if(tag==='BR')return '\n';
      if(tag==='STRONG'||tag==='B')return '**'+text+'**';
      if(tag==='EM'||tag==='I')return '*'+text+'*';
      if(tag==='CODE')return '`'+text+'`';
      if(tag==='A')return '['+text.replace(/\]/g,'\\]')+']('+node.getAttribute('href').replace(/\)/g,'%29')+')';
      return text;
    }
    const fenced=(text,language='')=>{const size=Math.max(3,...[...text.matchAll(/`+/g)].map(m=>m[0].length+1)),mark='`'.repeat(size);return mark+language+'\n'+text+'\n'+mark;};
    function block(node){
      if(node.nodeType===3)return node.nodeValue.trim();
      if(node.nodeType!==1||node.matches('.chapter-actions,.chapter-pager,.chapter-note-link,.chapter-meta,.eyebrow,.draft-notice,.implementation-toolbar,.lab-host,button,svg'))return '';
      const tag=node.tagName;
      if(node.matches('.lab-card'))return figure?.(node.dataset.lab)||'';
      if(node.matches('.static-figure'))return '!['+(node.querySelector('h3')?.textContent||'图解')+']('+node.querySelector('img').getAttribute('src')+')';
      if(node.matches('.equation'))return ['### '+node.querySelector('figcaption').textContent,'$$\n'+node.querySelector('details pre').textContent+'\n$$',...[...node.children].filter(n=>n.matches('p,.table-wrap')).map(block)].join('\n\n');
      if(node.matches('.math-scroll'))return node.dataset.tex?'$$\n'+node.dataset.tex+'\n$$':'';
      if(/^H[1-6]$/.test(tag)){const id=node.closest('.reading-section')?.id||node.id;return (tag==='H2'&&id?'<!-- section:'+id+' -->\n\n':'')+'#'.repeat(Number(tag[1]))+' '+inline(node);}
      if(tag==='P'||node.matches('.code-explanation,.inline-notice'))return inline(node);
      if(tag==='UL'||tag==='OL')return [...node.children].map((li,i)=>(tag==='OL'?(i+1)+'. ':'- ')+inline(li)).join('\n');
      if(tag==='TABLE'){
        const rows=[...node.rows].map(row=>[...row.cells].map(cell=>inline(cell).replace(/\|/g,'\\|').replace(/\n/g,'<br>')));
        if(!rows.length)return '';
        rows.splice(1,0,rows[0].map(()=>'---'));return rows.map(row=>'| '+row.join(' | ')+' |').join('\n');
      }
      if(tag==='PRE')return fenced(node.textContent,node.closest('.code-example')?.dataset.language||'');
      if(tag==='SUMMARY')return '### '+inline(node);
      if(node.matches('.code-caption'))return '### '+node.querySelector('span').textContent;
      return [...node.childNodes].map(block).filter(Boolean).join('\n\n');
    }
    return block(container)+'\n';
  }
  root.NarukamiVisualEditor={mount,fingerprint,safeInline,plainText,toMarkdown};
})(window);
