/* 章节草稿的离线 Markdown 排版器。
 * 输入：纯文本 Markdown 和本站提供的可信代码/公式/图解渲染回调。
 * 输出：已转义的 HTML；用户 HTML 不执行，图片只允许匹配教材图解清单。
 * 不访问网络，不读写存储。章节锚点使用导出文本中的 section 标记保持稳定。
 */
(function (root) {
  'use strict';
  const L = typeof module !== 'undefined' && module.exports ? require('./logic.js') : root.NarukamiLogic;
  const {esc, inline} = L;

  // 管道符前的反斜线表示单元格正文；只有未转义的管道才分隔列。
  function cells(line) {
    const result = []; let cell = '', escaped = false;
    for (const character of line.trim().replace(/^\|/, '').replace(/\|$/, '')) {
      if (escaped) {cell += character === '|' ? '|' : '\\' + character; escaped = false;}
      else if (character === '\\') escaped = true;
      else if (character === '|') {result.push(cell.trim()); cell = '';}
      else cell += character;
    }
    result.push((cell + (escaped ? '\\' : '')).trim());
    return result;
  }

  function render(raw, options = {}) {
    const lines = String(raw).replace(/\r\n?/g, '\n').split('\n'), out = [];
    const seen = new Set(); let index = 0, pendingId = '', headingIndex = 0;
    const isTable = i => i + 1 < lines.length && lines[i].trim().startsWith('|') && /^\s*\|?[\s:|-]+\|\s*$/.test(lines[i + 1]);
    const isBlock = i => !lines[i]?.trim() || /^(#{1,6}\s|\s*(?:`{3,}|~{3,})|\s*\$\$\s*$|\s*[-*+]\s|\s*\d+[.)]\s|>\s|<!-- section:|!\[)/.test(lines[i]) || isTable(i);
    while (index < lines.length) {
      const line = lines[index];
      if (!line.trim()) {index++; continue;}
      const marker = line.match(/^<!-- section:([a-zA-Z0-9_-]+) -->$/);
      if (marker) {pendingId = marker[1]; index++; continue;}
      const fence = line.match(/^\s*(`{3,}|~{3,})(.*)$/);
      if (fence) {
        const code = [], delimiter = fence[1][0], length = fence[1].length;
        index++;
        while (index < lines.length && !new RegExp('^\\s*' + delimiter + '{' + length + ',}\\s*$').test(lines[index])) code.push(lines[index++]);
        if (index < lines.length) index++;
        const block = {code:code.join('\n'), language:fence[2].trim(), type:'草稿代码', label:fence[2].trim() || '代码'};
        out.push(options.code ? options.code(block) : '<pre><code>' + esc(block.code) + '</code></pre>');
        continue;
      }
      if (/^\s*\$\$\s*$/.test(line)) {
        const tex = []; index++;
        while (index < lines.length && !/^\s*\$\$\s*$/.test(lines[index])) tex.push(lines[index++]);
        if (index < lines.length) index++;
        const source = tex.join('\n');
        out.push(options.math?.(source) || '<pre class="math-source"><code>' + esc(source) + '</code></pre>');
        continue;
      }
      const title = line.match(/^(#{1,6})\s+(.+)/);
      if (title) {
        let id = pendingId || 'draft-heading-' + headingIndex++;
        while (seen.has(id)) id += '-copy';
        seen.add(id); pendingId = '';
        const level = title[1].length;
        out.push(`<h${level} id="${id}" class="draft-heading">${inline(title[2])}</h${level}>`);
        index++; continue;
      }
      if (isTable(index)) {
        const columns = cells(line), rows = []; index += 2;
        while (index < lines.length && lines[index].trim().startsWith('|')) rows.push(cells(lines[index++]));
        const text = value => String(value ?? '').split(/<br\s*\/?\s*>/i).map(inline).join('<br>');
        out.push('<div class="table-wrap"><table><thead><tr>' + columns.map(c => '<th>' + text(c) + '</th>').join('') + '</tr></thead><tbody>' + rows.map(row => '<tr>' + columns.map((_,i) => '<td>' + text(row[i]) + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>');
        continue;
      }
      const image = line.match(/^!\[([^\]]*)\]\(([^\s)]+)\)\s*$/);
      if (image) {
        out.push(options.figure?.(image[2], image[1]) || '<p>' + esc(line) + '</p>');
        index++; continue;
      }
      const item = line.match(/^\s*(?:([-*+])|\d+[.)])\s+(.+)/);
      if (item) {
        const ordered = !item[1], tag = ordered ? 'ol' : 'ul', values = [];
        while (index < lines.length) {
          const next = lines[index].match(/^\s*(?:([-*+])|\d+[.)])\s+(.+)/);
          if (!next || Boolean(next[1]) === ordered) break;
          values.push('<li>' + inline(next[2]) + '</li>'); index++;
        }
        out.push('<' + tag + '>' + values.join('') + '</' + tag + '>'); continue;
      }
      if (/^>\s?/.test(line)) {
        const quote = [];
        while (index < lines.length && /^>\s?/.test(lines[index])) quote.push(inline(lines[index++].replace(/^>\s?/, '')));
        out.push('<blockquote>' + quote.join('<br>') + '</blockquote>'); continue;
      }
      const paragraph = [line]; index++;
      while (index < lines.length && !isBlock(index)) paragraph.push(lines[index++]);
      out.push('<p>' + inline(paragraph.join(' ')) + '</p>');
    }
    return out.join('') || '<p class="small-note">正文暂为空白，切换到编辑模式继续整理。</p>';
  }
  const api = {render, cells};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.NarukamiEditor = api;
})(typeof window === 'undefined' ? globalThis : window);
