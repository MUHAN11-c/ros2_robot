/**
 * SakuraBot Lab · 樱机实验室 · 浮动吉祥物助手（紫樱）
 * 58px 头像按钮 + 功能面板：搜索 / 返回顶部 / 阅读状态 / 首次气泡提示。
 * 兼容 Material instant navigation：面板随内容区重建，全局监听只绑一次。
 */
(function () {
  "use strict";

  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var globalBound = false;

  function setPanel(open) {
    var panel = document.getElementById("rt-assistant-panel");
    var btn = document.getElementById("rt-assistant-button");
    if (!panel || !btn) return;
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function dismissBubble() {
    var bubble = document.getElementById("rt-assistant-bubble");
    if (bubble) bubble.hidden = true;
    try {
      window.sessionStorage.setItem("rt-assistant-bubble", "1");
    } catch (e) {
      /* 隐私模式等场景忽略 */
    }
  }

  /* ---- 全局监听：只绑一次（元素每次动态查询，防 instant nav 重建后失效/重复） ---- */
  function bindGlobal() {
    if (globalBound) return;
    globalBound = true;

    var ticking = false;
    window.addEventListener(
      "scroll",
      function () {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(function () {
          ticking = false;
          var btn = document.getElementById("rt-assistant-button");
          if (btn) btn.classList.toggle("is-reading", window.scrollY > 280);
        });
      },
      { passive: true }
    );

    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Escape") return;
      var panel = document.getElementById("rt-assistant-panel");
      if (panel && !panel.hidden) setPanel(false);
    });

    document.addEventListener("click", function (ev) {
      var root = document.getElementById("rt-assistant");
      var panel = document.getElementById("rt-assistant-panel");
      if (!root || !panel || panel.hidden) return;
      if (root.contains(ev.target)) return;
      setPanel(false);
    });
  }

  function currentPageLabel() {
    /* 首页（前缀下段数 ≤2）不显示具体标题；其余取当前页 H1 */
    var path = window.location.pathname.replace(/\/index\.html$/, "/");
    var segs = path.replace(/\/+$/, "").split("/");
    if (segs.length <= 2) return "樱机实验室";
    var h1 = document.querySelector(".md-content h1");
    if (h1) {
      var clone = h1.cloneNode(true);
      var link = clone.querySelector(".headerlink");
      if (link) link.remove();
      var t = (clone.textContent || "").replace(/\s+/g, " ").trim();
      if (t) return t;
    }
    return (document.title || "").split(/[-·|]/)[0].trim() || "机器人教程";
  }

  /* ---- 每次导航后刷新（面板持久，标签需跟当前页） ---- */
  function refreshState() {
    var readingLabel = document.getElementById("rt-assistant-reading");
    if (readingLabel) readingLabel.textContent = "正在阅读：" + currentPageLabel();
    var btn = document.getElementById("rt-assistant-button");
    if (btn) btn.classList.toggle("is-reading", window.scrollY > 280);
  }

  /* ---- 组件初始化：每次内容区重建后调用 ---- */
  function initAssistant() {
    var root = document.getElementById("rt-assistant");
    if (!root) return;
    if (!root.dataset.rtBound) {
      root.dataset.rtBound = "1";

      var btn = document.getElementById("rt-assistant-button");
      var panel = document.getElementById("rt-assistant-panel");
      if (!btn || !panel) return;

      var closeBtn = document.getElementById("rt-assistant-close");
      var searchLink = document.getElementById("rt-assistant-search");
      var scrollTopBtn = document.getElementById("rt-scroll-top");
      var bubble = document.getElementById("rt-assistant-bubble");

      btn.addEventListener("click", function () {
        setPanel(panel.hidden);
        dismissBubble();
      });

      if (closeBtn) closeBtn.addEventListener("click", function () { setPanel(false); });

      if (searchLink) {
        searchLink.addEventListener("click", function (ev) {
          ev.preventDefault();
          setPanel(false);
          /* Material 9 的搜索开关是 .md-search__icon（label），非 button */
          var searchBtn =
            document.querySelector("label.md-search__icon") ||
            document.querySelector(".md-search__icon") ||
            document.querySelector(".md-search__button") ||
            document.querySelector('.md-header__button[aria-label="Search"]');
          if (searchBtn) {
            searchBtn.click();
            return;
          }
          var input = document.querySelector(".md-search__input");
          if (input) input.focus();
        });
      }

      if (scrollTopBtn) {
        scrollTopBtn.addEventListener("click", function () {
          /* 瞬时跳转：部分内嵌浏览器不支持 smooth 滚动选项 */
          window.scrollTo(0, 0);
        });
      }

      if (bubble && !window.sessionStorage.getItem("rt-assistant-bubble")) {
        window.setTimeout(function () {
          if (document.getElementById("rt-assistant-bubble")) {
            document.getElementById("rt-assistant-bubble").hidden = false;
            window.setTimeout(dismissBubble, 6000);
          }
        }, 2500);
      }

      bindGlobal();
    }
    /* 每次调用（含 instant navigation 后）都刷新页面相关状态 */
    refreshState();
  }


  /* ---- 活体吉祥物（Live2D 风格轻量实现）：hero 视差跟随 + 点击随机反应 ----
     真 Live2D 需分层 PSD 原稿经 Cubism 绑定生成 .moc3，平面贴纸无法转化；
     此处以 3D 视差 + 呼吸 + 随机全卡司贴纸反应达到"活的"观感。 */
  var REACTION_LINES = [
    "加油，下一章更精彩！",
    "卡住了？去可视化实验室跑段代码～",
    "按 Ctrl+K 可以搜索全站哦",
    "数学不会骗人，跑一遍就懂了",
    "这个实验我自己跑过，出图很漂亮！",
    "记得做章末练习呀",
    "SLAM 的本质就是坐标系变换！",
    "PID 调参要有耐心嘛",
    "读书觉得抽象，就来实验室玩",
    "紫樱陪读中，请继续～"
  ];
  var poolManifest = null;

  function livingReact() {
    var box = document.getElementById("rt-mascot-react");
    var img = document.getElementById("rt-mascot-react-img");
    var txt = document.getElementById("rt-mascot-react-text");
    var mascotImg = document.querySelector(".rt-hero__mascot-img");
    if (!box || !img || !txt || !mascotImg) return;
    txt.textContent = REACTION_LINES[Math.floor(Math.random() * REACTION_LINES.length)];
    var base = mascotImg.src.slice(0, mascotImg.src.lastIndexOf("/")) + "/pool/";
    var showRandom = function (list) {
      var pick = list[Math.floor(Math.random() * list.length)];
      img.src = base + pick;
      box.hidden = false;
      box.classList.remove("is-pop");
      void box.offsetWidth; /* 重启动画 */
      box.classList.add("is-pop");
      window.clearTimeout(box._t);
      box._t = window.setTimeout(function () { box.hidden = true; }, 2600);
    };
    if (poolManifest) { showRandom(poolManifest); return; }
    fetch(base + "manifest.json")
      .then(function (r) { return r.json(); })
      .then(function (list) { poolManifest = list; showRandom(list); })
      .catch(function () { /* 静默：反应不可用不影响阅读 */ });
  }

  function initLivingMascot() {
    var figure = document.querySelector(".rt-hero__figure");
    if (!figure || figure.dataset.livingBound) return;
    figure.dataset.livingBound = "1";
    var mascotImg = figure.querySelector(".rt-hero__mascot-img");
    if (!mascotImg) return;

    /* 视差：hero 内鼠标移动 → 轻微 3D 倾斜（悬停设备 + 未开降级时） */
    var hero = figure.closest(".rt-hero") || figure;
    if (!reducedMotion && window.matchMedia("(hover: hover)").matches) {
      hero.addEventListener("mousemove", function (e) {
        var r = hero.getBoundingClientRect();
        var dx = (e.clientX - r.left) / r.width - 0.5;
        var dy = (e.clientY - r.top) / r.height - 0.5;
        figure.style.transform =
          "perspective(640px) rotateY(" + (dx * 7).toFixed(2) + "deg) rotateX(" +
          (-dy * 5).toFixed(2) + "deg)";
      });
      hero.addEventListener("mouseleave", function () { figure.style.transform = ""; });
    }

    /* 点击 / 键盘触发随机反应 */
    mascotImg.style.cursor = "pointer";
    mascotImg.setAttribute("role", "button");
    mascotImg.setAttribute("tabindex", "0");
    mascotImg.setAttribute("aria-label", "戳一下紫樱，有惊喜");
    mascotImg.addEventListener("click", livingReact);
    mascotImg.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        livingReact();
      }
    });
  }

  /* 订阅 instant navigation；并兜底：若脚本执行晚于 document$ 首次发射（partial 在
     scripts block 末尾、晚于主题 bundle 解析），DOM ready 后直接初始化。rtBound 守卫保证幂等。 */
  if (window.document$) {
    window.document$.subscribe(initAssistant);
    if (window.document$) window.document$.subscribe(initLivingMascot);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { initAssistant(); initLivingMascot(); });
  } else {
    initAssistant();
    initLivingMascot();
  }
})();
