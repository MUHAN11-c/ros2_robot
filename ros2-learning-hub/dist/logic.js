(function(root){
  'use strict';
  function search(records,query){
    const tokens=String(query||'').trim().toLowerCase().split(/\s+/).filter(Boolean);
    if(!tokens.length)return [];
    return records.map((record,index)=>{
      const title=String(record.title||'').toLowerCase();
      const body=(title+' '+String(record.text||'')).toLowerCase();
      return {record,index,score:tokens.reduce((n,t)=>n+(title.includes(t)?10:0),0),match:tokens.every(t=>body.includes(t))};
    }).filter(x=>x.match).sort((a,b)=>b.score-a.score||a.index-b.index).map(x=>x.record);
  }
  function parseRoute(hash){
    try{
      const parts=decodeURIComponent(String(hash||'').replace(/^#\/?/,'')).split('/');
      if(!['home','courses','lesson','compare','examples','resources','ecosystem','projects','troubleshoot','saved','about'].includes(parts[0]))return {view:'home',id:''};
      return {view:parts[0],id:parts[1]||''};
    }catch{return {view:'home',id:''};}
  }
  function sanitizeState(value,ids){
    const v=value&&typeof value==='object'&&!Array.isArray(value)?value:{};
    const valid=new Set(ids);
    const clean=arr=>Array.isArray(arr)?[...new Set(arr.filter(x=>typeof x==='string'&&valid.has(x)))]:[];
    return {done:clean(v.done),stars:clean(v.stars),last:valid.has(v.last)?v.last:'',theme:v.theme==='dark'?'dark':'light'};
  }
  function qosCompatible(offered,requested){
    const reliability={best_effort:0,reliable:1},durability={volatile:0,transient_local:1};
    return reliability[offered.reliability]>=reliability[requested.reliability]&&durability[offered.durability]>=durability[requested.durability];
  }
  const api={search,parseRoute,sanitizeState,qosCompatible};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.HubLogic=api;
})(typeof window!=='undefined'?window:globalThis);
