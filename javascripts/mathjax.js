window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"], ["$", "$"]],
    displayMath: [["\\[", "\\]"], ["$$", "$$"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    // 只在 arithmatex（pymdownx.arithmatex 生成的公式容器）里找公式；
    // 忽略导航/页头/搜索等 UI 区域，避免侧栏标题里的 $ 或 \ 被误当公式。
    // 旧值 ".*|" 匹配一切 class，曾导致全站公式静默不渲染。
    ignoreHtmlClass: "md-nav|md-header|md-footer|md-search|md-tabs",
    processHtmlClass: "arithmatex"
  },
  startup: {
    // navigation.instant 切页不重跑脚本:按 Material 官方配方,首次渲染
    // 完成后订阅 document$,每次站内导航对新的公式 DOM 补一次 typeset。
    // typesetClear 先清掉进行中/残留的渲染,缓解与 DOM 替换的竞态
    // (旧 DOM 上的渲染在控制台留一条已知无害的 replaceChild 噪音)。
    pageReady: function () {
      return MathJax.startup.defaultPageReady().then(function () {
        if (window.document$) {
          window.document$.subscribe(function () {
            try { MathJax.typesetClear(); } catch (e) { /* 渲染未启动时忽略 */ }
            MathJax.typesetPromise();
          });
        }
      });
    }
  }
};
