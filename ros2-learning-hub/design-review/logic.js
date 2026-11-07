/* 鸣神审查版的纯数据层。输入为教材条目/浏览器记录，输出为经过约束的数据或转义后的 HTML。
 * 此文件不读写正式站存储；章节 ID 必须来自当前教材，时间使用 ISO 8601，笔记长度单位为字符。
 */
(function (root) {
  'use strict';
  const FORMAT = 'ros2-narukami-review-v1';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const object = value => value && typeof value === 'object' && !Array.isArray(value);
  const safeUrl = value => /^(https?:\/\/|#\/|\.\.\/|assets\/)/i.test(String(value)) ? String(value) : '#';
  function sanitize(raw, ids) {
    const value = object(raw) ? raw : {}, valid = new Set(ids);
    const clean = array => Array.isArray(array) ? [...new Set(array.filter(x => typeof x === 'string' && valid.has(x)))] : [];
    // 输入的章节记录不可信；字符上限分别为笔记 5 万、正文草稿 50 万。
    // 使用无原型字典，避免导入 JSON 中的特殊属性影响其他章节。
    function entries(rawEntries, field, limit) {
      const result = Object.create(null);
      for (const [id, entry] of Object.entries(object(rawEntries) ? rawEntries : {})) {
        if (!valid.has(id) || !object(entry) || typeof entry[field] !== 'string' || entry[field].length > limit) continue;
        const date = Date.parse(entry.updatedAt);
        result[id] = {[field]:entry[field], updatedAt:Number.isFinite(date) ? new Date(date).toISOString() : '1970-01-01T00:00:00.000Z'};
      }
      return result;
    }
    // 排版草稿只接受稳定字段号与有限长度的字符串；HTML在显示时由编辑器再次清理。
    const visualDrafts=Object.create(null);
    for(const [id,draft] of Object.entries(object(value.visualDrafts)?value.visualDrafts:{})){
      if(!valid.has(id)||!object(draft)||typeof draft.base!=='string'||!/^visual-v1-\d+-[a-f0-9]+$/.test(draft.base)||!object(draft.fields))continue;
      const fields=Object.create(null);let length=0;
      for(const [key,text] of Object.entries(draft.fields))if(/^f\d{1,5}-(?:h[1-6]|p|li|th|td|code|summary|figcaption|div|span)$/.test(key)&&typeof text==='string'){fields[key]=text;length+=text.length;}
      if(length>500000||Object.keys(fields).length>5000)continue;
      const date=Date.parse(draft.updatedAt);
      visualDrafts[id]={base:draft.base,fields,updatedAt:Number.isFinite(date)?new Date(date).toISOString():'1970-01-01T00:00:00.000Z'};
    }
    return {format:FORMAT, done:clean(value.done), stars:clean(value.stars), last:valid.has(value.last) ? value.last : '', theme:value.theme === 'dark' ? 'dark' : 'light', notes:entries(value.notes,'text',50000), drafts:entries(value.drafts,'markdown',500000),visualDrafts};
  }
  /* 导入只合并合法数据；旧版文件没有笔记，不得清掉当前笔记。同章冲突采用较新的保存时间。 */
  function mergeBackup(current, raw, ids) {
    if (!object(raw) || ![FORMAT,'ros2-atlas-v1'].includes(raw.format)) throw new Error('请选择本站导出的学习记录 JSON。');
    const next = sanitize(raw, ids), result = sanitize(current, ids);
    result.done = [...new Set([...result.done, ...next.done])];
    result.stars = [...new Set([...result.stars, ...next.stars])];
    result.last = next.last || result.last; result.theme = next.theme;
    for (const key of ['notes','drafts','visualDrafts']) {
      for (const [id, entry] of Object.entries(next[key])) {
        if (!result[key][id] || entry.updatedAt >= result[key][id].updatedAt) result[key][id] = entry;
      }
    }
    return result;
  }
  /* 原始 HTML 始终转义。允许的 Markdown 链接单独检查协议，代码围栏内部不再解析行内语法。 */
  function inline(raw) {
    return esc(raw).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\[([^\]]+)\]\(([^\s)]+)\)/g, (_, label, url) => /^(https?:\/\/|#\/)/i.test(url) ? `<a href="${esc(url.replace(/&amp;/g,'&'))}" target="_blank" rel="noopener noreferrer">${label}</a>` : label);
  }
  function markdown(raw) {
    const out = []; let fenced = false, code = [], list = false;
    for (const line of String(raw).split('\n')) {
      if (/^\s*```/.test(line)) {
        if (list) {out.push('</ul>'); list = false;}
        if (fenced) {out.push('<pre><code>' + esc(code.join('\n')) + '</code></pre>'); code = [];}
        fenced = !fenced; continue;
      }
      if (fenced) {code.push(line); continue;}
      if (/^\s*[-*] /.test(line)) {if (!list) out.push('<ul>'); list = true; out.push('<li>' + inline(line.replace(/^\s*[-*] /,'')) + '</li>'); continue;}
      if (list) {out.push('</ul>'); list = false;}
      const heading = line.match(/^(#{1,4})\s+(.+)/);
      if (heading) out.push(`<h${heading[1].length + 1}>${inline(heading[2])}</h${heading[1].length + 1}>`);
      else if (line.trim()) out.push('<p>' + inline(line) + '</p>');
    }
    if (fenced) out.push('<pre><code>' + esc(code.join('\n')) + '</code></pre>');
    if (list) out.push('</ul>'); return out.join('');
  }
  const tokens = query => String(query).trim().toLowerCase().split(/\s+/).filter(Boolean);
  function search(records, query, kind = '全部') {
    const terms = tokens(query); if (!terms.length) return [];
    return records.map((record, index) => {
      const title = String(record.title).toLowerCase(), text = String(record.text || ''), body = (title + ' ' + text).toLowerCase();
      if ((kind !== '全部' && record.kind !== kind) || !terms.every(t => body.includes(t))) return null;
      const score = terms.reduce((s,t) => s + (title === t ? 40 : title.includes(t) ? 20 : 1),0);
      const position = text.toLowerCase().indexOf(terms[0]), start = Math.max(0, position - 42);
      return {record:{...record, snippet:(start ? '…' : '') + text.slice(start,start + 170).replace(/\s+/g,' ')}, score,index};
    }).filter(Boolean).sort((a,b) => b.score-a.score || a.index-b.index).map(x => x.record);
  }
  function highlight(raw, query) {
    const terms = tokens(query).sort((a,b) => b.length-a.length);
    if (!terms.length) return esc(raw);
    const pattern = new RegExp('(' + terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|') + ')','gi');
    return String(raw).split(pattern).map(part => terms.includes(part.toLowerCase()) ? '<mark>' + esc(part) + '</mark>' : esc(part)).join('');
  }
  const api = {FORMAT,esc,inline,markdown,sanitize,mergeBackup,search,highlight,safeUrl};
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.NarukamiLogic = api;
})(typeof window === 'undefined' ? globalThis : window);
