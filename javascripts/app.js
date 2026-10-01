/**
 * SakuraBot Lab · app.js
 * 模块化轻交互：进度条 / 搜索增强 / 面包屑 / 阅读时长 / 已读标记 / 导航图标
 * 原则：原生 JS + IntersectionObserver，无动画库，200ms 内过渡，支持 reduced-motion
 */
(function () {
  "use strict";

  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ============ 模块：锚点纠偏 ============
     浏览器锚点跳转发生在字体/MathJax 排版完成之前，晚到的布局变化会把
     目标标题顶偏（实测可偏 200px+）。加载完成与字体就绪后按 hash 重对齐一次。 */
  function realignAnchor() {
    if (!location.hash || location.hash === "#") return;
    var id = decodeURIComponent(location.hash.slice(1));
    var el = document.getElementById(id);
    if (el) el.scrollIntoView({ block: "start", behavior: "instant" });
  }
  function initAnchorRealign() {
    if (document.readyState === "complete") {
      realignAnchor();
    } else {
      window.addEventListener("load", realignAnchor);
    }
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () {
        /* 字体换装后再纠一次，并给晚到的排版留 300ms */
        setTimeout(realignAnchor, 300);
      });
    }
  }
  initAnchorRealign();

  /* ============ 模块：阅读进度条 ============ */
  var progressBar = null;
  function initProgress() {
    if (document.querySelector(".rt-progress")) {
      progressBar = document.querySelector(".rt-progress");
    } else {
      progressBar = document.createElement("div");
      progressBar.className = "rt-progress";
      progressBar.setAttribute("aria-hidden", "true");
      document.body.appendChild(progressBar);
    }
    updateProgress();
    if (!progressBar._bound) {
      progressBar._bound = true;
      window.addEventListener("scroll", updateProgress, { passive: true });
      window.addEventListener("resize", updateProgress, { passive: true });
    }
  }
  function updateProgress() {
    if (!progressBar) return;
    var doc = document.documentElement;
    var max = doc.scrollHeight - doc.clientHeight;
    var pct = max > 0 ? (window.scrollY / max) * 100 : 0;
    progressBar.style.width = pct.toFixed(2) + "%";
  }

  /* ============ 模块：搜索体验（占位符 + Ctrl/Cmd+K） ============ */
  function initSearch() {
    document
      .querySelectorAll("[data-md-component='search'] input, .md-search__input")
      .forEach(function (input) {
        if (input._rtSearch) return;
        input._rtSearch = true;
        input.setAttribute("placeholder", "搜索文档…");
      });
    if (!window._rtSearchKeys) {
      window._rtSearchKeys = true;
      document.addEventListener("keydown", function (event) {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
          event.preventDefault();
          var el = document.querySelector("label.md-search__icon") ||
                   document.querySelector(".md-search__icon") ||
                   document.querySelector(".md-search__form");
          if (el) el.click();
          var input = document.querySelector(".md-search__input");
          if (input) input.focus();
        }
      });
    }
  }

  /* ============ 模块：面包屑（由 URL 路径推导） ============ */
  function prettify(segment) {
    return segment
      .replace(/\.html?$/, "")
      .replace(/^\d+[_.\-\s]*/, "")
      .replace(/[_-]+/g, " ")
      .trim();
  }
  function initBreadcrumb() {
    var inner = document.querySelector(".md-content__inner");
    var h1 = inner && inner.querySelector("h1");
    if (!inner || !h1 || inner.querySelector(".rt-breadcrumb")) return;
    if (document.querySelector(".rt-hero")) return; // 首页不显示

    var parts = decodeURIComponent(location.pathname)
      .split("/")
      .filter(function (seg) { return seg && seg.indexOf(".html") === -1; });

    if (!parts.length) return;
    var bc = document.createElement("nav");
    bc.className = "rt-breadcrumb";
    bc.setAttribute("aria-label", "面包屑");
    var html = "<a href='" + (window.location.protocol === "file:" ? "/" : "/") +
      "' style='text-decoration:none'>首页</a>";
    parts.forEach(function (seg) {
      var label = prettify(seg);
      if (!label) return;
      html += "<span class='rt-bc-sep'>/</span><span>" + label + "</span>";
    });
    bc.innerHTML = html;
    h1.parentNode.insertBefore(bc, h1);
  }

  /* ============ 模块：预计阅读时长（CJK ≈ 400 字/分钟，不计代码） ============ */
  function initReadingTime() {
    var inner = document.querySelector(".md-content__inner");
    var h1 = inner && inner.querySelector("h1");
    if (!inner || !h1 || inner.querySelector(".rt-meta") || document.querySelector(".rt-hero")) return;

    var clone = inner.cloneNode(true);
    clone.querySelectorAll("pre, .highlight, .mermaid, script, style").forEach(function (el) { el.remove(); });
    var chars = (clone.textContent || "").replace(/\s+/g, "").length;
    if (chars < 200) return;
    var minutes = Math.max(1, Math.round(chars / 400));

    var meta = document.createElement("div");
    meta.className = "rt-meta";
    meta.innerHTML =
      "<span class='rt-meta-item'><svg viewBox='0 0 24 24' fill='none' stroke-width='2' stroke-linecap='round'>" +
      "<circle cx='12' cy='12' r='9'/><path d='M12 7 v5 l3 2'/></svg>预计阅读 " + minutes + " 分钟</span>";
    var bc = inner.querySelector(".rt-breadcrumb");
    if (bc) bc.parentNode.insertBefore(meta, bc.nextSibling);
    else h1.parentNode.insertBefore(meta, h1.nextSibling);
  }

  /* ============ 模块：已读标记（LocalStorage，可选功能） ============ */
  var VISITED_KEY = "rt-visited";
  function getVisited() {
    try { return JSON.parse(localStorage.getItem(VISITED_KEY)) || []; }
    catch (e) { return []; }
  }
  function markVisited() {
    if (!location.pathname || location.pathname === "/") return;
    var visited = getVisited();
    if (visited.indexOf(location.pathname) === -1) {
      visited.push(location.pathname);
      try { localStorage.setItem(VISITED_KEY, JSON.stringify(visited.slice(-500))); } catch (e) {}
    }
  }
  function paintVisited() {
    var visited = getVisited();
    if (!visited.length) return;
    document.querySelectorAll("a").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (!href.endsWith("/") && !href.endsWith(".html")) return;
      var path = href.replace(/\.html?$/, "");
      var match = visited.some(function (v) {
        var norm = v.replace(/\.html?$/, "").replace(/\/$/, "");
        return norm && (path.indexOf(norm) !== -1 || norm.indexOf(path.replace(/\/$/, "")) !== -1);
      });
      if (match) a.classList.add("is-visited");
    });
  }

  /* ============ 模块：侧边栏分组图标（原创线性图标） ============ */
  var SECTION_ICONS = {
    "学习路线": "<svg viewBox='0 0 24 24'><path d='M4 19 L4 9 M9 19 L9 5 M14 19 L14 11 M19 19 L19 7'/></svg>",
    "数学": "<svg viewBox='0 0 24 24'><path d='M5 5 h14 M5 5 c7 0 4.7 7 -1.2 7 c7 0 9.4 7 1.2 7 M5 19 h14'/></svg>",
    "C++": "<svg viewBox='0 0 24 24'><path d='M9 6 L4 12 L9 18 M15 6 L20 12 L15 18'/></svg>",
    "导论": "<svg viewBox='0 0 24 24'><circle cx='12' cy='12' r='8'/><path d='M12 8 v4 l3 2'/></svg>",
    "实验室": "<svg viewBox='0 0 24 24'><path d='M10 3 v6 L4.5 18 a2 2 0 0 0 1.8 3 h11.4 a2 2 0 0 0 1.8 -3 L14 9 V3 M8 3 h8 M7 15 h10'/></svg>",
    "SLAM": "<svg viewBox='0 0 24 24'><path d='M9 4 L4 6 v14 l5 -2 l6 2 l5 -2 V4 l-5 2 z M9 4 v14 M15 6 v14'/></svg>",
    "规控": "<svg viewBox='0 0 24 24'><path d='M12 3 L14.5 8.5 L20.5 9.3 L16 13.5 L17.2 19.5 L12 16.6 L6.8 19.5 L8 13.5 L3.5 9.3 L9.5 8.5 z'/></svg>",
    "运动控制": "<svg viewBox='0 0 24 24'><circle cx='12' cy='12' r='3'/><path d='M12 3 v3 M12 18 v3 M3 12 h3 M18 12 h3 M5.6 5.6 l2.2 2.2 M16.2 16.2 l2.2 2.2 M18.4 5.6 l-2.2 2.2 M7.8 16.2 l-2.2 2.2'/></svg>",
    "具身智能": "<svg viewBox='0 0 24 24'><path d='M12 3 a7 7 0 0 1 7 7 c0 2.5 -1.2 4 -2.5 5 v3 h-9 v-3 C6.2 14 5 12.5 5 10 a7 7 0 0 1 7 -7 z M10 21 h4'/></svg>"
  };
  function initNavIcons() {
    document.querySelectorAll(".md-nav__item--nested > .md-nav__link, .md-nav__item--nested > label.md-nav__link").forEach(function (label) {
      if (label.querySelector(".rt-nav-ico")) return;
      var text = (label.textContent || "").trim();
      for (var key in SECTION_ICONS) {
        if (text.indexOf(key) !== -1) {
          var span = document.createElement("span");
          span.className = "rt-nav-ico";
          span.setAttribute("aria-hidden", "true");
          span.innerHTML = SECTION_ICONS[key];
          label.insertBefore(span, label.firstChild);
          break;
        }
      }
    });
  }

  /* ============ 模块：滚动显现（仅淡入 200ms） ============ */
  function initReveal() {
    if (reducedMotion || !("IntersectionObserver" in window)) {
      document.querySelectorAll(".rt-reveal").forEach(function (el) { el.classList.add("is-visible"); });
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -4% 0px", threshold: 0.03 });
    document.querySelectorAll(".md-typeset > h2, .rt-home-section, .rt-quick__card, .rt-path-card, .rt-stat").forEach(function (el) {
      if (!el.classList.contains("rt-reveal")) {
        el.classList.add("rt-reveal");
        observer.observe(el);
      }
    });
    window.setTimeout(function () {
      document.querySelectorAll(".rt-reveal").forEach(function (el) { el.classList.add("is-visible"); });
    }, 3000);
  }

  /* ============ TOC 阅读进度条（右侧目录顶部，随滚动推进） ============ */
  var tocBound = false;

  function initTocProgress() {
    var wrap = document.querySelector(".md-sidebar--secondary .md-sidebar__scrollwrap");
    if (!wrap || wrap.querySelector(".rt-toc-progress")) return;
    var bar = document.createElement("div");
    bar.className = "rt-toc-progress";
    wrap.appendChild(bar);
    if (tocBound) return;
    tocBound = true;
    window.addEventListener(
      "scroll",
      function () {
        var el = document.querySelector(".rt-toc-progress");
        if (!el) return;
        var h = document.documentElement;
        var max = h.scrollHeight - h.clientHeight;
        el.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + "%";
      },
      { passive: true }
    );
  }

  /* ============ 启动 ============ */
  function setup() {
    initProgress();
    initSearch();
    initBreadcrumb();
    initReadingTime();
    markVisited();
    paintVisited();
    initNavIcons();
    initReveal();
    initTocProgress();
  }

  if (window.document$) {
    document$.subscribe(setup);
  } else {
    document.addEventListener("DOMContentLoaded", setup);
  }
})();
