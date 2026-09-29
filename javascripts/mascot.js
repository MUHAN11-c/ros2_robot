/**
 * Sakura Robotics Lab · 浮动吉祥物助手（紫樱）
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
    var h1 = document.querySelector(".md-content h1");
    if (h1) {
      var t = (h1.textContent || "").replace(/\s+/g, " ").trim();
      if (t) return t;
    }
    return (document.title || "").split(/[-·|]/)[0].trim() || "机器人教程";
  }

  /* ---- 组件初始化：每次内容区重建后调用 ---- */
  function initAssistant() {
    var root = document.getElementById("rt-assistant");
    if (!root || root.dataset.rtBound) return;
    root.dataset.rtBound = "1";

    var btn = document.getElementById("rt-assistant-button");
    var panel = document.getElementById("rt-assistant-panel");
    if (!btn || !panel) return;

    var closeBtn = document.getElementById("rt-assistant-close");
    var searchLink = document.getElementById("rt-assistant-search");
    var scrollTopBtn = document.getElementById("rt-scroll-top");
    var readingLabel = document.getElementById("rt-assistant-reading");

    if (readingLabel) readingLabel.textContent = "正在阅读：" + currentPageLabel();

    btn.addEventListener("click", function () {
      setPanel(panel.hidden);
      dismissBubble();
    });

    if (closeBtn) closeBtn.addEventListener("click", function () { setPanel(false); });

    if (searchLink) {
      searchLink.addEventListener("click", function (ev) {
        ev.preventDefault();
        setPanel(false);
        var searchBtn =
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
        window.scrollTo({ top: 0, behavior: reducedMotion ? "auto" : "smooth" });
      });
    }

    var bubble = document.getElementById("rt-assistant-bubble");
    if (bubble && !window.sessionStorage.getItem("rt-assistant-bubble")) {
      window.setTimeout(function () {
        if (document.getElementById("rt-assistant-bubble")) {
          document.getElementById("rt-assistant-bubble").hidden = false;
          window.setTimeout(dismissBubble, 6000);
        }
      }, 2500);
    }

    bindGlobal();
    btn.classList.toggle("is-reading", window.scrollY > 280);
  }

  if (window.document$) {
    window.document$.subscribe(initAssistant);
  } else {
    document.addEventListener("DOMContentLoaded", initAssistant);
  }
})();
