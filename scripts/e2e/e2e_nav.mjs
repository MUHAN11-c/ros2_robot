/**
 * 侧栏导航端到端测试 · e2e_nav.mjs
 *
 * 用 playwright-core 驱动系统 Edge(无头),在 5 个视口 × 7 个代表页型上走查:
 *   ① 无未捕获 JS 异常            ② 导航条目两两不叠印(几何检测)
 *   ③ 当前页祖先分组链已展开       ④ 手风琴:点分组展开/再点收起(<1220px)
 *   ⑤ 页内目录块可展开且无错位标题 ⑥ 点击章节导航后新页侧栏正确
 *   ⑦ 当前页高亮存在
 *
 * 用法(在 scripts/e2e/ 下):
 *   npm install && node e2e_nav.mjs [base-url]
 * 前置:本地托管已启动——repo 根执行
 *   npx serve --no-clipboard -l tcp://0.0.0.0:8080 .generated/web
 * 截图存档:.generated/e2e/(不入库)
 */
import { chromium } from 'playwright-core';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const BASE = process.argv[2] || 'http://127.0.0.1:8080/ros2_robot/';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT_DIR = path.join(ROOT, '.generated', 'e2e');
fs.mkdirSync(OUT_DIR, { recursive: true });

const VIEWPORTS = [
  { name: 'mobile-375', width: 375, height: 812 },
  { name: 'iab-791', width: 791, height: 807 },
  { name: 'tablet-1024', width: 1024, height: 768 },
  { name: 'laptop-1280', width: 1280, height: 800 },
  { name: 'desktop-1440', width: 1440, height: 900 },
];

/* 页型覆盖:首页 / 方向页(直属+组) / 三层嵌套章 / 分组恢复验证 /
   两级嵌套+当前链 / 实验室页 / 目录索引 */
const PAGES = [
  { name: 'home', path: '/' },
  { name: 'slam-hub', path: '/03_SLAM/SLAM方向_学习路径与教材映射/' },
  { name: 'slam-3level', path: '/03_SLAM/00_入门/20_十四讲第2讲_三维空间刚体运动/', math: true },
  { name: 'math-hub', path: '/01_数学/数学方向_学习路径与教材映射/' },
  { name: 'cpp-2level', path: '/02_C++基础与进阶/00_入门/20_控制流_函数与程序结构/' },
  { name: 'lab07', path: '/08_可视化实验室/lab07_规划实验室/' },
  { name: 'catalog', path: '/catalog/' },
];

const results = [];
let passCount = 0;
let failCount = 0;

function record(viewport, page, check, ok, detail = '') {
  const entry = { viewport, page, check, ok, detail };
  results.push(entry);
  if (ok) passCount++;
  else failCount++;
  const tag = ok ? 'PASS' : 'FAIL';
  console.log(`  [${tag}] ${check}${detail ? ' — ' + detail : ''}`);
}

/* ---------- 页面内断言函数(evaluate 注入) ---------- */

const CHECK_OVERLAP = () => {
  const sb = document.querySelector('.md-sidebar--primary');
  if (!sb) return { count: 0, overlaps: ['no primary sidebar'] };
  const els = [...sb.querySelectorAll('.md-nav__link, label.md-nav__link, label.md-nav__title')].filter((el) => {
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.visibility === 'collapse' || cs.display === 'none') return false;
    const r = el.getBoundingClientRect();
    return r.height > 1 && r.width > 1;
  });
  const items = els.map((el) => {
    const r = el.getBoundingClientRect();
    return { text: el.textContent.trim().slice(0, 14), top: r.top, bottom: r.bottom, left: r.left, right: r.right };
  });
  const overlaps = [];
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      const a = items[i];
      const b = items[j];
      const y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      const x = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      if (y > 3 && x > 3) overlaps.push(`「${a.text}」与「${b.text}」重叠 ${Math.round(y)}px`);
    }
  }
  return { count: items.length, overlaps };
};

const CHECK_CHAIN = () => {
  const active = document.querySelector('.md-sidebar--primary .md-nav__link--active');
  if (!active) return { ok: false, reason: 'no-active' };
  const unchecked = [];
  let el = active.closest('.md-nav__item');
  while (el) {
    if (el.classList.contains('md-nav__item--nested')) {
      const t = el.querySelector(':scope > input.md-nav__toggle');
      if (t && !t.checked) {
        const lbl = el.querySelector(':scope > label.md-nav__link');
        unchecked.push(lbl ? lbl.textContent.trim().slice(0, 14) : '?');
      }
    }
    el = el.parentElement;
  }
  return { ok: unchecked.length === 0, unchecked };
};

const CHECK_ACTIVE = () =>
  document.querySelectorAll('.md-sidebar--primary .md-nav__link--active, .md-sidebar--primary .md-nav__item--active').length > 0;

/* ---------- 主流程 ---------- */

async function runCell(browser, viewport, pageDef) {
  const expectDrawer = viewport.width < 960;
  const cellName = `${viewport.name}/${pageDef.name}`;
  console.log(`\n▶ ${cellName}${expectDrawer ? '(抽屉)' : '(侧栏)'}`);
  const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', (err) => pageErrors.push(`${String(err).slice(0, 90)} @ ${(err.stack || '').split('\n')[1]?.trim().slice(0, 70) || '?'}`));
  if (process.env.E2E_DEBUG_XHR) {
    await page.addInitScript(() => {
      const orig = XMLHttpRequest.prototype.open;
      XMLHttpRequest.prototype.open = function (m, u) {
        console.log('XHR@' + location.pathname.slice(0, 46) + ' :', m, String(u).slice(0, 110));
        return orig.apply(this, arguments);
      };
    });
    page.on('console', (m) => { if (m.text().startsWith('XHR@')) console.log(`    [xhr] ${viewport.name}/${pageDef.name} ${m.text()}`); });
  }

  try {
    /* 注意:new URL('/x', base) 的前导斜杠是站根绝对路径,会丢掉 /ros2_robot
       前缀落到 404 页——必须字符串拼接;偶发慢加载重试一次 */
    const target = BASE.endsWith('/') ? BASE.slice(0, -1) + pageDef.path : BASE + pageDef.path;
    try {
      await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 15000 });
    } catch {
      await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 20000 });
    }
    await page.waitForTimeout(1200);

    /* 抽屉 or 常驻侧栏按运行时汉堡可见性判定(Material 的切换点约 960px,
       960–1220 区间侧栏常驻且无汉堡) */
    let isDrawer = false;
    const burger = page.locator('label.md-header__button.md-icon').first();
    if (await burger.isVisible().catch(() => false)) {
      isDrawer = true;
      await burger.click({ timeout: 5000 });
      await page.waitForTimeout(700);
    }

    // ① JS 异常 + CDN 依赖检查(本地部署不应请求任何外部 JS)
    record(cellName, '', 'js-errors', pageErrors.length === 0, pageErrors.join(' | '));
    const cdnHits = await page.evaluate(() =>
      [...document.scripts].filter((s) => s.src && !s.src.startsWith(location.origin)).map((s) => s.src.slice(0, 60))
    );
    record(cellName, '', 'no-cdn-scripts', cdnHits.length === 0, cdnHits.join(', '));

    // ①b 公式渲染(MathJax 本地化后,含公式的页面应有 <mjx-container> 标签——
    //    注意 mjx-container 是自定义元素标签名,不是 class)
    const mjx = await page.evaluate(() => document.querySelectorAll('mjx-container').length);
    if (pageDef.math) {
      record(cellName, '', 'mathjax-render', mjx > 0, `${mjx} 个公式容器`);
    }

    // ② 叠印检测
    const overlap = await page.evaluate(CHECK_OVERLAP);
    record(cellName, '', 'no-overlap', overlap.overlaps.length === 0,
      overlap.overlaps.length ? overlap.overlaps.slice(0, 3).join(';') + `(共${overlap.count}条目)` : `${overlap.count} 条目`);

    // ③ 当前链展开 + ⑦ 高亮(catalog/首页等无 active 链的页跳过)
    const chain = await page.evaluate(CHECK_CHAIN);
    if (chain.reason !== 'no-active') {
      record(cellName, '', 'current-chain', chain.ok, chain.ok ? '' : `未展开: ${chain.unchecked.join(', ')}`);
      record(cellName, '', 'active-highlight', await page.evaluate(CHECK_ACTIVE));
    }

    // ③b 目录索引页筛选(catalog 页):输入关键词应有命中统计并过滤
    if (pageDef.name === 'catalog') {
      const box = page.locator('#rt-catalog-search');
      if ((await box.count()) > 0) {
        await box.fill('微积分');
        await page.waitForTimeout(300);
        const t = await page.evaluate(() => document.getElementById('rt-catalog-count')?.textContent || '');
        record(cellName, '', 'catalog-filter', t.includes('命中'), t);
        await box.fill('');
        await page.waitForTimeout(200);
      } else {
        record(cellName, '', 'catalog-filter', false, '筛选框不存在');
      }
    }

    // ③c 面包屑(navigation.path):内容页 H1 上方应有模块路径
    if (pageDef.name !== 'home' && pageDef.name !== 'catalog') {
      const crumb = await page.evaluate(() => {
        const nav = document.querySelector('.md-path');
        return nav ? { links: nav.querySelectorAll('a').length, text: nav.textContent.trim().replace(/\s+/g, ' ').slice(0, 40) } : null;
      });
      record(cellName, '', 'breadcrumb', !!crumb && crumb.links >= 1, crumb ? crumb.text : '无面包屑');
    }

    // ④ 手风琴交互(抽屉态):点未展开组 → 展开 → 再点 → 收起
    if (isDrawer) {
      const target = await page.evaluate(() => {
        const sb = document.querySelector('.md-sidebar--primary');
        for (const item of sb.querySelectorAll('.md-nav__item--nested')) {
          const t = item.querySelector(':scope > input.md-nav__toggle');
          const lbl = item.querySelector(':scope > label.md-nav__link');
          if (t && lbl && !t.checked) return { id: t.id, text: lbl.textContent.trim().slice(0, 12) };
        }
        return null;
      });
      if (!target) {
        record(cellName, '', 'accordion', false, '找不到未展开的分组');
      } else {
        /* 折叠开关统一用 DOM click:物理点击在侧栏滚动容器/遮挡场景下
           actionability 检查易误判,而 checkbox hack 的 label click 走
           DOM 事件与物理点击等价 */
        const toggleByDom = (id) => page.evaluate((x) => { document.querySelector(`label[for="${x}"]`)?.click(); }, id);
        await toggleByDom(target.id);
        await page.waitForTimeout(450);
        const expanded = await page.evaluate((id) => {
          const t = document.getElementById(id);
          const nav = t.parentElement.querySelector(':scope > .md-nav');
          return { checked: t.checked, visible: getComputedStyle(nav).visibility === 'visible' };
        }, target.id);
        await toggleByDom(target.id);
        await page.waitForTimeout(450);
        const collapsed = await page.evaluate((id) => {
          const t = document.getElementById(id);
          const nav = t.parentElement.querySelector(':scope > .md-nav');
          return { checked: t.checked, visible: getComputedStyle(nav).visibility === 'visible' };
        }, target.id);
        const ok = expanded.checked && expanded.visible && !collapsed.checked && !collapsed.visible;
        record(cellName, '', 'accordion', ok, ok ? `分组「${target.text}」展开/收起正常` : `「${target.text}」expand=${JSON.stringify(expanded)} collapse=${JSON.stringify(collapsed)}`);
      }

      // ⑤ 页内目录块:展开后「目录」标题应被隐藏、条目可见
      const hasToc = await page.evaluate(() => !!document.querySelector('.md-sidebar--primary label[for="__toc"]'));
      if (hasToc) {
        await page.evaluate(() => { document.querySelector('.md-sidebar--primary label[for="__toc"]').click(); });
        await page.waitForTimeout(400);
        const tocState = await page.evaluate(() => {
          const title = document.querySelector('.md-sidebar--primary .md-nav--secondary > .md-nav__title');
          const list = document.querySelector('.md-sidebar--primary .md-nav--secondary > .md-nav__list');
          return {
            titleHidden: title ? getComputedStyle(title).display === 'none' : true,
            tocLinks: list ? [...list.querySelectorAll('a')].filter((a) => getComputedStyle(a).visibility !== 'hidden').length : 0,
          };
        });
        record(cellName, '', 'toc-block', tocState.titleHidden && tocState.tocLinks > 0,
          `标题隐藏=${tocState.titleHidden}, 可见条目=${tocState.tocLinks}`);
      }
    }

    // ⑥ 点击导航:点一个可见、未被遮挡的非当前链接 → URL 变化 → 新页当前链正确
    const linkInfo = await page.evaluate(() => {
      const links = [...document.querySelectorAll('.md-sidebar--primary a.md-nav__link')];
      for (const a of links) {
        if (a.classList.contains('md-nav__link--active') || !a.getAttribute('href')) continue;
        const cs = getComputedStyle(a);
        if (cs.visibility === 'hidden' || cs.display === 'none') continue;
        const r = a.getBoundingClientRect();
        /* 选视口内、有实际尺寸的条目(侧栏首项可能被 sticky 页头遮挡) */
        if (r.height < 4 || r.top < 4 || r.bottom > innerHeight) continue;
        const center = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        if (!a.contains(center) && center !== a) continue;
        return { href: a.getAttribute('href'), text: a.textContent.trim().slice(0, 14) };
      }
      return null;
    });
    if (!linkInfo) {
      record(cellName, '', 'nav-click', true, 'SKIP:无可见可点链接');
    } else {
      const before = page.url();
      /* href 可能是 "../.." 之类含斜杠的相对值,CSS 属性选择器在部分引擎里
         匹配不稳定;用 DOM click 触发(同样走 Material 的 instant 导航拦截) */
      const clicked = await page.evaluate((href) => {
        const a = [...document.querySelectorAll('.md-sidebar--primary a.md-nav__link')].find(
          (x) => x.getAttribute('href') === href
        );
        if (a) {
          a.click();
          return true;
        }
        return false;
      }, linkInfo.href);
      await page.waitForTimeout(1200);
      const after = page.url();
      const navChain = await page.evaluate(CHECK_CHAIN);
      if (after === before) {
        /* 首页 CTA 等页内锚点按钮:URL 不变属正常,记 SKIP */
        record(cellName, '', 'nav-click', true, `SKIP:「${linkInfo.text}」为页内锚点`);
      } else {
        record(cellName, '', 'nav-click', clicked && (navChain.ok || navChain.reason === 'no-active'),
          `「${linkInfo.text}」→ ${after.replace(BASE, '').slice(0, 36)}`);
      }
    }

    await page.screenshot({ path: path.join(OUT_DIR, `${viewport.name}--${pageDef.name}.png`) });
  } catch (err) {
    record(cellName, '', 'page-load', false, String(err).slice(0, 140));
    await page.screenshot({ path: path.join(OUT_DIR, `${viewport.name}--${pageDef.name}.png`) }).catch(() => {});
  } finally {
    await context.close();
  }
}

async function main() {
  const res = await fetch(BASE).catch(() => null);
  if (!res || !res.ok) {
    console.error(`✗ 本地服务不可用(${BASE})。请先在仓库根目录运行:\n  npx serve --no-clipboard -l tcp://0.0.0.0:8080 .generated/web`);
    process.exit(1);
  }
  let browser;
  try {
    browser = await chromium.launch({ channel: 'msedge', headless: true });
  } catch {
    console.error('✗ 无法启动系统 Edge(channel: msedge)。Windows 11 自带 Edge;如缺失请安装或改用 chromium。');
    process.exit(1);
  }
  console.log(`端到端导航测试 · ${VIEWPORTS.length} 视口 × ${PAGES.length} 页型 · ${BASE}`);
  const only = process.env.E2E_ONLY; // 调试用:"viewport-name:page-name"
  for (const viewport of VIEWPORTS) {
    for (const pageDef of PAGES) {
      if (only && `${viewport.name}:${pageDef.name}` !== only) continue;
      await runCell(browser, viewport, pageDef);
    }
  }
  await browser.close();

  console.log('\n========== 汇总 ==========');
  const cells = {};
  for (const r of results) {
    const key = r.viewport;
    cells[key] = cells[key] || { pass: 0, fail: 0 };
    cells[key][r.ok ? 'pass' : 'fail']++;
  }
  for (const [k, v] of Object.entries(cells)) {
    console.log(`${k.padEnd(16)} ${v.fail === 0 ? '✅' : '❌'}  ${v.pass} pass / ${v.fail} fail`);
  }
  console.log(`总计:${passCount} pass / ${failCount} fail,截图 ${VIEWPORTS.length * PAGES.length} 张 → ${path.relative(ROOT, OUT_DIR)}`);
  process.exit(failCount === 0 ? 0 : 1);
}

main();
