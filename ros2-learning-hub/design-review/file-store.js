/* 本地教材文件保存协议。可由目录句柄或测试中的真实文件适配器执行。
 * 输入：固定教材根目录的读/写/删除接口、单章原文与修改、预期版本。
 * 顺序：校验教材目录与版本 → 原文/历史备份 → 章节文件 → 源数据 → 网页读取缓存。
 * 写入失败回滚已触及的教材文件；备份不删除。所有路径固定，章节ID不接受斜杠。
 */
(function(root){
  'use strict';
  const FORMAT='ros2-local-editions-v1';
  const empty=()=>({format:FORMAT,revision:0,chapters:{}});
  const sorted=value=>Array.isArray(value)?value.map(sorted):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,sorted(value[key])])):value;
  const encoded=value=>JSON.stringify(sorted(value))+'\n';
  async function sha(text){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(x=>x.toString(16).padStart(2,'0')).join('');}
  const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#x27;'}[c]));
  function page(document,backup=false){
    const prefix=backup?'../../../../dist/':'../',style=backup?'../../../../design-review/styles.css':'../../design-review/styles.css';
    const body=document.html.replace(/<(?:a|img)\b[^>]*>/g,tag=>tag.replaceAll('="../dist/','="'+prefix));
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(document.title)+'</title><link rel="stylesheet" href="'+style+'"></head><body><main id="reading"><p><a href="'+prefix+'index.html">返回教材</a></p>'+body+'</main></body></html>\n';
  }
  const script=registry=>'/* 本地教材文件修订；原文与历史见 backups/local-edits/。 */\nwindow.ROS2LocalEditions = '+JSON.stringify(registry,null,2).replaceAll('<','\\u003c')+';\n';
  async function commit(io,payload){
    const baseText=await io.read('dist/content.js');
    if(!baseText?.includes('window.ROS2Hub = '))throw new Error('请选择 ros2-learning-hub 教材目录，里面应有 dist/content.js。');
    const marker='window.ROS2Hub = ',data=JSON.parse(baseText.slice(baseText.indexOf(marker)+marker.length).trim().replace(/;$/,''));
    const id=payload.chapterId,chapter=data.lessons.find(c=>c.id===id);
    if(!/^[a-z0-9-]+$/.test(id)||!chapter)throw new Error('请选择有效的教材章节。');
    if(encoded(chapter)!==encoded(payload.baseChapter))throw new Error('所选目录的教材基线不同，请刷新后重新核对。');
    const raw=await io.read('source/local-edits.json'),registry=raw?JSON.parse(raw):empty();
    if(registry.format!==FORMAT)throw new Error('教材修订文件格式无效。');
    const previous=registry.chapters[id];
    if((previous?.revision??null)!==payload.expectedRevision)throw new Error('此章已被其他页面修改，请刷新后重新保存；现有文件已保留。');
    const revision=await sha(encoded(payload.document));
    if(previous?.revision===revision)return {saved:true,unchanged:true,record:previous};
    async function once(path,text){const old=await io.read(path);if(old!==null&&old!==text)throw new Error('已有原文备份不同，已停止保存：'+path);if(old===null)await io.write(path,text);}
    const backup='backups/local-edits/original/'+id;
    await once(backup+'/source.json',encoded(chapter));
    await once(backup+'/chapter.md',payload.original.markdown);
    await once(backup+'/chapter.html',page(payload.original,true));
    if(await io.read('backups/local-edits/original/content.js')===null)await once('backups/local-edits/original/content.js',baseText);
    if(previous)await once('backups/local-edits/history/'+id+'/'+previous.revision+'.json',encoded(previous));
    const record={chapterId:id,revision,savedAt:new Date().toISOString(),document:payload.document};
    registry.chapters[id]=record;registry.revision++;
    const outputs={['dist/chapters/'+id+'.md']:payload.document.markdown,['dist/chapters/'+id+'.html']:page(payload.document),'source/local-edits.json':encoded(registry),'dist/local-edits.js':script(registry)};
    const old={},touched=[];
    try{
      // 备份过程中若另一来源已提交，停止本次写入，不覆盖较新的教材。
      if((await io.read('source/local-edits.json'))!==raw)throw new Error('教材文件在保存过程中变化，请刷新后重试。');
      for(const [path,text] of Object.entries(outputs)){old[path]=await io.read(path);touched.push(path);await io.write(path,text);}
    }catch(error){
      const failures=[];
      for(const path of touched.reverse())try{if(old[path]===null)await io.remove(path);else await io.write(path,old[path]);}catch{failures.push(path);}
      if(failures.length)throw new Error('保存失败，部分文件未能回滚。原文与历史备份仍在，请检查：'+failures.join('、'));
      throw error;
    }
    return {saved:true,record,files:Object.keys(outputs),backup};
  }
  function directoryIO(directory){
    async function locate(path,create){
      const parts=path.split('/');if(parts.some(part=>!part||part==='.'||part==='..'))throw new Error('教材文件路径无效。');
      let parent=directory;for(const part of parts.slice(0,-1))parent=await parent.getDirectoryHandle(part,{create});return {parent,name:parts.at(-1)};
    }
    return {
      async read(path){try{const {parent,name}=await locate(path,false);return await(await(await parent.getFileHandle(name)).getFile()).text();}catch(error){if(error.name==='NotFoundError')return null;throw error;}},
      async write(path,text){const {parent,name}=await locate(path,true),file=await parent.getFileHandle(name,{create:true});let writer;
        try{writer=await file.createWritable();await writer.write(text);await writer.close();}catch(error){try{await writer?.abort();}catch{}throw error;}
      },
      async remove(path){try{const {parent,name}=await locate(path,false);await parent.removeEntry(name);}catch(error){if(error.name!=='NotFoundError')throw error;}}
    };
  }
  const api={FORMAT,empty,encoded,sha,page,script,commit,directoryIO};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NarukamiFileStore=api;
})(typeof window==='undefined'?globalThis:window);
