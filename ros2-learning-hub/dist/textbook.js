(function(root){
  'use strict';
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const inline=x=>esc(x).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  const list=items=>items?.length?'<ul>'+items.map(x=>'<li>'+inline(x)+'</li>').join('')+'</ul>':'';
  const defaultCode=(code,lang,label)=>`<div class="code-block"><div class="code-head"><span>${esc(label)} · ${esc(lang)}</span></div><pre><code>${esc(code)}</code></pre></div>`;
  function renderExpanded(chapter,renderCode=defaultCode){
    if(!chapter.sections?.length)return '';
    let html=chapter.sections.map((section,index)=>`<section class="deep-section" data-depth="full"><h2 id="deep-${index}"><span class="section-number">${String(index+1).padStart(2,'0')}</span>${esc(section.title)}</h2>${(section.paragraphs||[]).map(p=>'<p>'+inline(p)+'</p>').join('')}${list(section.bullets)}${(section.codeBlocks||[]).map(b=>renderCode(b.code,b.language,b.label,b.type)+(b.explanation?`<div class="code-explanation"><strong>读懂这段代码</strong><p>${inline(b.explanation)}</p></div>`:'')).join('')}</section>`).join('');
    const example=chapter.workedExample;
    if(example)html+=`<section class="worked-example" id="worked-example"><span class="section-kicker">WALK THROUGH A COMPLETE EXAMPLE</span><h2>${esc(example.title)}</h2><p>${inline(example.scenario)}</p><ol>${(example.steps||[]).map(s=>`<li>${inline(s)}</li>`).join('')}</ol><div class="notice"><strong>结果与验收</strong><p>${inline(example.result)}</p></div></section>`;
    if(chapter.exercises?.length)html+=`<section id="deep-exercises"><h2>分层练习与参考答案</h2>${chapter.exercises.map((x,i)=>`<div class="exercise"><span>EXERCISE ${String(i+1).padStart(2,'0')}</span><p>${inline(x.question)}</p><details class="answer"><summary>展开参考答案</summary><p>${inline(x.answer)}</p></details></div>`).join('')}</section>`;
    return html;
  }
  function expandedMarkdown(chapter){
    if(!chapter.sections?.length)return '';
    const out=[];
    chapter.sections.forEach(s=>{
      out.push('## '+s.title,...(s.paragraphs||[]),...(s.bullets||[]).map(x=>'- '+x));
      (s.codeBlocks||[]).forEach(b=>out.push('### '+b.label,'类型：'+b.type,'```'+b.language+'\n'+b.code+'\n```',b.explanation||''));
    });
    const x=chapter.workedExample;
    if(x)out.push('## '+x.title,x.scenario,...x.steps.map((s,i)=>`${i+1}. ${s}`),'预期结果：'+x.result);
    if(chapter.exercises?.length){out.push('## 分层练习与答案');chapter.exercises.forEach((x,i)=>out.push(`### 练习 ${i+1}`,x.question,'参考答案：'+x.answer));}
    return out.join('\n\n');
  }
  const api={renderExpanded,expandedMarkdown};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.Textbook=api;
})(typeof window!=='undefined'?window:globalThis);
