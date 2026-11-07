/* 教材目录从已排版的正文取标题与顺序。
 * 输入为当前章 DOM 和全书章号。输出嵌套条目，并给正文写入相同的编号与锚点。
 * 普通小节连续编号，实现对照与配套学习按正文位置分组。已有锚点在再次提取时保留。
 */
(() => {
  'use strict';
  const groups = {comparison: '实现对照', study: '配套学习'};
  const study = new Set(['api-details', 'qos-practice', 'worked-example', 'practice', 'pitfalls', 'exercises', 'sources']);
  const introduction = new Set(['goals', 'prerequisites', 'overview']);
  const headings = 'h2, h3, h4, h5, h6';
  const childHeadings = ':scope > h3, :scope > .api-reference > h3, :scope > .compact-example > h3, ' +
    ':scope > .static-figure > h3, :scope > .lab-card > .lab-summary h3, :scope > .context-figure .figure-heading h3';
  const escape = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const href = (chapter, anchor) => '#/' + encodeURIComponent(chapter) + '/section/' + encodeURIComponent(anchor);
  const sectionTitle = title => title.replace(/^\d+[.．]\s*/, '').trim();

  function titleOf(heading) {
    const label = heading.cloneNode(true);
    label.querySelectorAll('.section-anchor').forEach(link => link.remove());
    return label.textContent.replace(/\s+/g, ' ').trim() || '未命名小节';
  }

  function collect(article, chapterNumber) {
    if (!article) return [];
    const draft = article.querySelector(':scope > .draft-content');
    const blocks = draft ? draft.children : article.querySelectorAll(':scope > .reading-section[id], :scope > .source-note[id]');
    const sections = [], parents = [];
    let part = 0;
    const entry = (id, heading, number, group = '') => {
      if (number) heading.dataset.sectionNumber = number;
      else delete heading.dataset.sectionNumber;
      return {id, title: titleOf(heading), number, group, children: []};
    };
    const addChild = (parent, heading) => {
      const index = parent.children.length + 1;
      if (!heading.id) {
        let id = parent.id + '-sub-' + index;
        // 草稿中的显式锚点优先于自动生成的图解锚点。
        while (article.querySelector('#' + CSS.escape(id))) id += '-copy';
        heading.id = id;
      }
      const child = entry(heading.id, heading, parent.number ? parent.number + '.' + index : '');
      parent.children.push(child);
      return child;
    };
    for (const block of blocks) {
      if (draft && !block.matches('h2[id]')) {
        if (!parents.length) continue;
        if (!block.matches(headings)) {
          const visual = block.querySelector(':scope > h3, :scope > .lab-summary h3');
          if (visual) addChild(parents[0].section, visual);
          continue;
        }
        const level = Number(block.tagName[1]);
        while (parents.length > 1 && parents.at(-1).level >= level) parents.pop();
        parents.push({level, section: addChild(parents.at(-1).section, block)});
        continue;
      }
      const heading = draft ? block : block.querySelector(':scope > h2, :scope > summary');
      if (!heading) continue;
      const group = block.id.startsWith('writing-') ? 'comparison' : study.has(block.id) ? 'study' : '';
      const numbered = /^part-\d+$/.test(block.id) || (draft && !group && !introduction.has(block.id));
      const section = entry(block.id, heading, numbered ? chapterNumber + '.' + ++part : '', group);
      sections.push(section);
      if (draft) parents.splice(0, parents.length, {level: 2, section});
      else for (const child of block.querySelectorAll(childHeadings)) addChild(section, child);
    }
    return sections;
  }

  function flatten(sections) {
    return sections.flatMap(section => [section, ...flatten(section.children)]);
  }

  function markup(sections, chapter, current) {
    const link = ({id, title, number, children}) => {
      const index = number ? escape(number) : '·';
      const selected = id === current ? ' aria-current="location"' : '';
      const indexLabel = number ? '' : ' aria-hidden="true"';
      const branch = children.length ? '<ul class="outline-children">' + children.map(link).join('') + '</ul>' : '';
      return '<li><a href="' + href(chapter, id) + '" data-section-id="' + escape(id) + '"' + selected +
        '><span class="outline-index"' + indexLabel + '>' + index + '</span><span class="outline-label">' +
        escape(title) + '</span></a>' + branch + '</li>';
    };
    // 只合并相邻的同类条目，避免实现对照与配套学习改变正文的阅读顺序。
    const runs = [];
    for (const section of sections) {
      const previous = runs.at(-1);
      if (section.group && previous?.kind === section.group) previous.entries.push(section);
      else runs.push({kind: section.group, entries: [section]});
    }
    return runs.map(({kind, entries}) => {
      const items = entries.map(link).join('');
      return kind ? '<li class="outline-group" data-outline-group="' + kind + '"><span class="outline-caption" aria-hidden="true">' +
        groups[kind] + '</span><ul aria-label="' + groups[kind] + '">' + items + '</ul></li>' : items;
    }).join('');
  }

  function select(root, current) {
    for (const link of root.querySelectorAll('a[data-section-id]')) {
      if (link.dataset.sectionId === current) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  }

  function selectTree(navigation, current, expand = false) {
    select(navigation, current);
    const branch = navigation.querySelector('.tree-subtree');
    if (expand && current && branch?.querySelector('[aria-current=location]')) branch.open = true;
    const selected = navigation.querySelector('.tree-subtree[open] [aria-current=location]');
    const chapter = navigation.querySelector('.tree-link[aria-current=page]');
    const item = selected || chapter;
    if (!item?.getClientRects().length) return;
    const firstSection = navigation.querySelector('.tree-subtree[open] a');
    const viewport = navigation.getBoundingClientRect();
    const bottom = (selected || firstSection || item).getBoundingClientRect().bottom;
    const chapterTop = chapter.getBoundingClientRect().top;
    // 目录空间足够时，同时保留章名和目标条目。只滚动目录容器。
    const top = bottom - chapterTop <= viewport.height ? chapterTop : item.getBoundingClientRect().top;
    if (top < viewport.top) navigation.scrollTop += top - viewport.top;
    else if (bottom > viewport.bottom) navigation.scrollTop += Math.min(bottom - viewport.bottom, top - viewport.top);
  }

  window.ROS2ChapterOutline = {collect, flatten, href, markup, sectionTitle, select, selectTree};
})();
