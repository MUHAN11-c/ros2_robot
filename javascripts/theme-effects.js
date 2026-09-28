/* ==========================================================================
   鸣神主题 · 全局交互层
   - 顶部雷樱滚动进度条
   - 点击樱花迸发
   - 内容滚动淡入（IntersectionObserver，带兜底）
   - 首页鼠标微视差
   - 搜索占位符文案
   - prefers-reduced-motion 时自动降级
   ========================================================================== */
(() => {
  const prefersReduced = () =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const burst = (x, y) => {
    const count = 8;

    for (let index = 0; index < count; index += 1) {
      const petal = document.createElement("span");
      const angle = (Math.PI * 2 * index) / count + Math.random() * 0.6;
      const distance = 42 + Math.random() * 62;

      petal.className = "robotics-burst-petal";
      petal.style.left = `${x}px`;
      petal.style.top = `${y}px`;
      petal.style.setProperty(
        "--robotics-burst-x",
        `${(Math.cos(angle) * distance).toFixed(1)}px`,
      );
      petal.style.setProperty(
        "--robotics-burst-y",
        `${(Math.sin(angle) * distance + 26).toFixed(1)}px`,
      );
      petal.style.animationDelay = `${(Math.random() * 0.12).toFixed(2)}s`;
      document.body.appendChild(petal);
      window.setTimeout(() => petal.remove(), 1300);
    }
  };

  const initProgress = () => {
    if (document.querySelector(".robotics-progress")) {
      return;
    }

    const bar = document.createElement("div");
    bar.className = "robotics-progress";
    bar.setAttribute("aria-hidden", "true");
    document.body.appendChild(bar);

    const update = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const progress = max > 0 ? Math.min(window.scrollY / max, 1) : 0;
      bar.style.setProperty("--robotics-progress", progress.toFixed(4));
    };

    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  };

  const initSearchPlaceholder = () => {
    document
      .querySelectorAll("[data-md-component='search'] input, .md-search__input")
      .forEach((input) => {
        input.setAttribute("placeholder", "❀ 寻访秘典…");
      });
  };

  const initReveal = () => {
    const targets = document.querySelectorAll(
      [
        ".md-typeset > h2",
        ".md-typeset > h3",
        ".md-typeset .admonition",
        ".md-typeset .grid.cards > ul > li",
        ".md-typeset table:not([class])",
        ".md-typeset details",
      ].join(","),
    );

    if (!targets.length) {
      return;
    }

    if (prefersReduced() || !("IntersectionObserver" in window)) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-robotics-revealed");
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -6% 0px", threshold: 0.04 },
    );

    targets.forEach((element, index) => {
      element.classList.add("robotics-reveal");
      element.style.transitionDelay = `${Math.min(index % 6, 5) * 45}ms`;
      observer.observe(element);
    });

    // 兜底：3 秒后强制全部显示，避免观察器异常导致内容不可见
    window.setTimeout(() => {
      targets.forEach((element) => element.classList.add("is-robotics-revealed"));
    }, 3000);
  };

  const initHeroPointer = () => {
    const hero = document.querySelector("[data-robotics-parallax]");

    if (!hero || prefersReduced()) {
      return;
    }

    hero.addEventListener(
      "pointermove",
      (event) => {
        const x = (event.clientX / window.innerWidth - 0.5) * 2;
        const y = (event.clientY / window.innerHeight - 0.5) * 2;
        hero.style.setProperty("--robotics-mouse-x", `${(x * 12).toFixed(1)}px`);
        hero.style.setProperty("--robotics-mouse-y", `${(y * 9).toFixed(1)}px`);
      },
      { passive: true },
    );

    hero.addEventListener("pointerleave", () => {
      hero.style.setProperty("--robotics-mouse-x", "0px");
      hero.style.setProperty("--robotics-mouse-y", "0px");
    });
  };

  const initClickBurst = () => {
    if (prefersReduced() || document.body.dataset.roboticsBurstReady === "true") {
      return;
    }

    document.body.dataset.roboticsBurstReady = "true";
    document.addEventListener(
      "click",
      (event) => {
        burst(event.clientX, event.clientY);
      },
      { passive: true },
    );
  };

  const initialize = () => {
    initProgress();
    initSearchPlaceholder();
    initReveal();
    initHeroPointer();
    initClickBurst();
  };

  if (typeof document$ !== "undefined") {
    document$.subscribe(initialize);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
