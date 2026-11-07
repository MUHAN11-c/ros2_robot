/* 全章目录验收。输入为当前审查页与教材章节 ID，输出为逐章条目与跳转计数。
 * 从教材数据独立推导期望顺序，再对照已渲染的标题、目录和锚点；长度以条目计，布局单位为 CSS 像素。
 */
const assert = require('node:assert/strict');

async function checkChapterOutline(page, chapterId, formal = false) {
  await page.locator(formal ? '.mini-toc > summary' : '#toc-trigger').click();
  const report = await page.evaluate(({id, formal}) => {
    const {lessons, comparisons, apiReferences} = window.ROS2Hub;
    const index = lessons.findIndex(lesson => lesson.id === id);
    const chapter = lessons[index];
    const expected = [], sourceIssues = [], partTitles = new Set(), paragraphs = [];
    const add = (anchor, title, number = '', group = '', tag = 'H2', parent = '') => expected.push({
      anchor, title: title.trim(), number, group, tag, parent, href: '#/' + id + '/section/' + anchor,
    });
    const addChildren = (parent, titles, number = '', group = '') => titles.forEach((title, i) => {
      add(parent + '-sub-' + (i + 1), title, number ? number + '.' + (i + 1) : '', group, 'H3', parent);
    });
    const figureTitles = {'tf2-static': '同一个点，两种坐标表达', 'robot-static': '从关节角到末端位置'};
    add('overview', '建立整体认识');
    chapter.sections.forEach((part, i) => {
      const anchor = 'part-' + i, number = (index + 1) + '.' + (i + 1);
      const prefix = part.title.match(/^(\d+)[.．]\s*/);
      const title = part.title.slice(prefix?.[0].length || 0).trim();
      if (!title || partTitles.has(title) || (prefix && Number(prefix[1]) !== i + 1)) sourceIssues.push({anchor, title: part.title});
      partTitles.add(title);
      const plain = text => text.replace(/`([^`]+)`/g, '$1').replace(/\*\*([^*]+)\*\*/g, '$1');
      paragraphs.push({anchor, texts: part.paragraphs.map(plain)});
      add(anchor, title, number);
      const figures = window.ROS2Hub.figures.filter(figure => figure.placements.some(
        placement => placement.chapter === id && placement.afterSection === i,
      ));
      const titles = figures.map(figure => figureTitles[figure.id] || figure.title);
      if (formal && i === 1 && ['math-rigid', 'math-kinematics'].includes(id)) titles.push(figureTitles['tf2-static']);
      addChildren(anchor, [...(part.tables || []).map(table => table.title), ...titles], number);
      if (i === 0) {
        for (const comparison of comparisons.filter(item => item.relatedLessons?.includes(id))) {
          add('writing-' + comparison.id, comparison.title, '', 'comparison');
        }
      }
    });
    const apis = apiReferences.filter(api => api.lessons.includes(id));
    if (apis.length) {
      add('api-details', 'API 对照与调用边界', '', 'study');
      addChildren('api-details', apis.map(api => api.title), '', 'study');
    }
    if (formal && id === 'qos') add('qos-practice', '动手比较 QoS 请求与提供', '', 'study');
    if (chapter.workedExample) add('worked-example', chapter.workedExample.title, '', 'study');
    add('practice', '动手验证', '', 'study');
    addChildren('practice', chapter.steps.flatMap((step, i) => typeof step === 'string' ? [] : [step.title || '步骤 ' + (i + 1)]), '', 'study');
    add('pitfalls', '常见问题与边界', '', 'study');
    add('exercises', '练习与答案', '', 'study');
    add('sources', '参考出处、版本与验证范围', '', 'study', 'SUMMARY');

    const article = document.querySelector('#reading article');
    const badges = [];
    const body = [...article.querySelectorAll('h2, h3, .source-note > summary')].map(heading => {
      const label = heading.cloneNode(true);
      label.querySelector('.section-anchor')?.remove();
      const isChild = heading.tagName === 'H3';
      const anchor = isChild ? heading.id : heading.parentElement.id;
      const number = heading.dataset.sectionNumber || '';
      if (number && getComputedStyle(heading, '::before').content !== JSON.stringify(number)) badges.push(anchor);
      return {anchor, title: label.textContent.trim(), number, tag: heading.tagName, parent: isChild ? heading.closest('.reading-section')?.id : ''};
    });
    const incorrectParagraphs = paragraphs.filter(({anchor, texts}) => {
      const visible = [...article.querySelectorAll('#' + anchor + ' > p:not(.table-caption, .code-explanation)')];
      return visible.length !== texts.length || visible.some((paragraph, i) => paragraph.textContent !== texts[i]);
    }).map(({anchor}) => anchor);
    const tree = document.querySelector('#chapter-tree');
    const branch = tree.querySelector('.tree-subtree');
    const side = branch.querySelector('.section-outline');
    const popup = document.querySelector(formal ? '.mini-toc .section-outline' : '#toc-list');
    const links = root => [...root.querySelectorAll('a')].map(link => ({
      anchor: link.dataset.sectionId,
      title: link.querySelector('.outline-label').textContent,
      number: link.querySelector('.outline-index').textContent,
      group: link.closest('[data-outline-group]')?.dataset.outlineGroup || '',
      parent: link.closest('.outline-children')?.parentElement.querySelector(':scope > a')?.dataset.sectionId || '',
      href: link.getAttribute('href'),
    }));
    const groups = root => [...root.querySelectorAll('.outline-group > ul')].map(list => list.getAttribute('aria-label'));
    const current = tree.querySelector('.tree-link[aria-current=page]');
    const chapterLabel = current.cloneNode(true);
    chapterLabel.querySelectorAll('.num, .tree-check').forEach(node => node.remove());
    const overflow = [tree, popup, ...document.querySelectorAll('.section-outline a > span')].some(
      node => node.scrollWidth > node.clientWidth + 1,
    );
    return {
      expected, body, side: links(side), popup: links(popup), overflow, sourceIssues, incorrectParagraphs, badges,
      sideGroups: groups(side), popupGroups: groups(popup),
      paragraphs: paragraphs.reduce((sum, section) => sum + section.texts.length, 0),
      chapterTitle: chapter.title, bodyTitle: article.querySelector('h1').textContent, sidebarTitle: chapterLabel.textContent.trim(),
      bodyNumber: Number(article.querySelector('.chapter-header :is(.eyebrow,.chapter-overline) span').textContent.match(/\d+/)[0]),
      breadcrumbNumber: Number(document.querySelector(formal ? '#breadcrumb-chapter' : '#breadcrumb > span:last-child').textContent.match(/\d+/)[0]),
      chapterNumber: index + 1, sidebarNumber: Number(current.querySelector('.num').textContent),
      currentHref: current.getAttribute('href'), branchId: branch.dataset.chapter,
      branchCount: tree.querySelectorAll('.tree-subtree').length, branchOpen: branch.open,
      stage: chapter.stage, activeStage: branch.closest('.tree-stage[open]')?.dataset.stage,
      entryCount: parseInt(branch.querySelector('summary small').textContent, 10),
    };
  }, {id: chapterId, formal});
  await page.locator(formal ? '.mini-toc > summary' : '#toc-dialog [data-close=toc-dialog]').click();

  const label = page.viewportSize().width + 'px ' + chapterId;
  const {expected, body} = report;
  assert.equal(report.currentHref, '#/' + chapterId, label + ' 当前章节');
  assert.equal(report.branchId, chapterId, label + ' 小节父级');
  assert.equal(report.branchCount, 1, label + ' 仅当前章显示小节');
  assert.equal(report.branchOpen, true, label + ' 当前小节目录展开');
  assert.equal(report.activeStage, report.stage, label + ' 学习阶段展开');
  assert.equal(report.sidebarNumber, report.chapterNumber, label + ' 章号');
  assert.equal(report.bodyNumber, report.chapterNumber, label + ' 正文章号');
  assert.equal(report.breadcrumbNumber, report.chapterNumber, label + ' 面包屑章号');
  assert.equal(report.bodyTitle, report.chapterTitle, label + ' 正文章名');
  assert.equal(report.sidebarTitle, report.chapterTitle, label + ' 左栏章名');
  assert.deepEqual(report.sourceIssues, [], label + ' 原小节编号与标题');
  assert.deepEqual(report.incorrectParagraphs, [], label + ' 小节各段正文');
  assert.deepEqual(report.badges, [], label + ' 正文显示编号');
  assert.equal(report.entryCount, expected.length, label + ' 目录条目数');
  assert.deepEqual(body, expected.map(({group, href, ...entry}) => entry), label + ' 正文标题');
  const expectedLinks = expected.map(({tag, number, ...entry}) => ({...entry, number: number || '·'}));
  assert.deepEqual(report.side, expectedLinks, label + ' 左栏目录');
  assert.deepEqual(report.popup, expectedLinks, label + ' 顶部目录');
  const expectedGroups = expected.some(item => item.group === 'comparison') ? ['实现对照', '配套学习'] : ['配套学习'];
  assert.deepEqual(report.sideGroups, expectedGroups, label + ' 左栏分组层级');
  assert.deepEqual(report.popupGroups, expectedGroups, label + ' 顶部目录分组层级');
  assert.equal(report.overflow, false, label + ' 目录文字无横向裁切');
  const children = expected.filter(item => item.parent);
  return {
    id: chapterId, number: report.chapterNumber, numbered: expected.filter(item => item.number && !item.parent).length,
    childEntries: children.length, numberedChildren: children.filter(item => item.number).length, entries: expected.length,
    paragraphs: report.paragraphs,
  };
}

async function checkSectionJumps(page, chapterId) {
  const report = await page.evaluate(async () => {
    const tree = document.querySelector('#chapter-tree');
    const topbar = document.querySelector('.topbar');
    const reading = document.querySelector('#reading');
    const chapter = tree.querySelector('.tree-link[aria-current=page]');
    const links = [...tree.querySelectorAll('.tree-section-list a')];
    const failures = [];
    for (const link of links) {
      const id = link.dataset.sectionId;
      // 点击实际链接，等待浏览器完成哈希导航和正文定位再测量；超时视作该锚点失败。
      const changed = await new Promise(resolve => {
        const finish = () => {clearTimeout(timer); resolve(true);};
        const timer = setTimeout(() => {removeEventListener('hashchange', finish); resolve(false);}, 500);
        addEventListener('hashchange', finish, {once: true});
        link.click();
      });
      await new Promise(resolve => requestAnimationFrame(resolve));
      const targets = reading.querySelectorAll('#' + CSS.escape(id));
      const target = targets[0];
      const title = target?.matches('h3') ? target : target?.querySelector(':scope > h2, :scope > summary');
      const heading = title?.getBoundingClientRect();
      const visible = heading && heading.top >= topbar.getBoundingClientRect().bottom - 1 && heading.bottom <= innerHeight + 1;
      const selected = tree.querySelectorAll('[aria-current=location]');
      const viewport = tree.getBoundingClientRect(), row = link.getBoundingClientRect();
      const chapterTop = chapter.getBoundingClientRect().top;
      const chapterFits = row.bottom - chapterTop <= viewport.height;
      const treeVisible = row.top >= viewport.top - 1 && row.bottom <= viewport.bottom + 1 &&
        (!chapterFits || chapterTop >= viewport.top - 1);
      if (!changed || location.hash !== link.hash || targets.length !== 1 || !visible ||
          !target.classList.contains('matched-section') || selected.length !== 1 || selected[0] !== link ||
          !treeVisible || (target.matches('details') && !target.open)) {
        failures.push({id, changed, hash: location.hash, targets: targets.length, treeVisible, top: heading?.top, bottom: heading?.bottom});
      }
    }
    return {count: links.length, failures};
  });
  assert.deepEqual(report.failures, [], chapterId + ' 逐项定位');
  return report.count;
}

module.exports = {checkChapterOutline, checkSectionJumps};
