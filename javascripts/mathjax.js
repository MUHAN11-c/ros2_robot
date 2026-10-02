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
  }
};
