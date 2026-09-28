(() => {
  const clamp = (value, min = 0, max = 1) => Math.min(Math.max(value, min), max);

  const initialize = () => {
    const root = document.querySelector("[data-robotics-parallax]");

    if (!root) {
      return;
    }

    if (root.dataset.roboticsParallaxReady === "true") {
      return;
    }

    root.dataset.roboticsParallaxReady = "true";

    let ticking = false;
    let scrollingTimer;

    const update = () => {
      const distance = Math.max(root.offsetHeight - window.innerHeight, 1);
      const progress = clamp(-root.getBoundingClientRect().top / distance);
      const dim = clamp((progress - 0.34) / 0.34);
      const solid = clamp((progress - 0.62) / 0.24);
      const content = clamp(1 - progress / 0.54);

      root.style.setProperty("--robotics-scroll", progress.toFixed(4));
      root.style.setProperty("--robotics-far-y", `${(-7 * progress).toFixed(3)}vh`);
      root.style.setProperty("--robotics-mid-y", `${(-21 * progress).toFixed(3)}vh`);
      root.style.setProperty("--robotics-grid-y", `${(-46 * progress).toFixed(3)}vh`);
      root.style.setProperty("--robotics-near-y", `${(-68 * progress).toFixed(3)}vh`);
      root.style.setProperty("--robotics-title-y", `${(-17 * progress).toFixed(3)}vh`);
      root.style.setProperty("--robotics-star-x", `${(-8 * progress).toFixed(3)}vw`);
      root.style.setProperty("--robotics-nebula-x", `${(-4 * progress).toFixed(3)}vw`);
      root.style.setProperty("--robotics-aurora-x", `${(10 * progress).toFixed(3)}vw`);
      root.style.setProperty("--robotics-moon-y", `${(-12 * progress).toFixed(3)}vh`);
      root.style.setProperty("--robotics-shade-opacity", dim.toFixed(4));
      root.style.setProperty("--robotics-solid-opacity", solid.toFixed(4));
      root.style.setProperty("--robotics-content-opacity", content.toFixed(4));
      root.style.setProperty("--robotics-robot-scale", (1 - progress * 0.08).toFixed(4));
    };

    const markScrolling = () => {
      root.classList.add("is-robotics-scrolling");
      window.clearTimeout(scrollingTimer);
      scrollingTimer = window.setTimeout(() => {
        root.classList.remove("is-robotics-scrolling");
      }, 520);
    };

    const preservePaletteScroll = () => {
      const palette = document.querySelector("[data-md-component='palette']");

      if (!palette || palette.dataset.roboticsScrollGuard === "true") {
        return;
      }

      palette.dataset.roboticsScrollGuard = "true";

      let savedY = null;
      let releaseTimer;

      const save = () => {
        savedY = window.scrollY;
      };

      const restore = () => {
        if (savedY === null) {
          return;
        }

        const y = savedY;
        window.clearTimeout(releaseTimer);

        [0, 32, 96, 180, 360, 700].forEach((delay) => {
          window.setTimeout(() => {
            window.scrollTo(window.scrollX, y);
            requestUpdate();
          }, delay);
        });

        releaseTimer = window.setTimeout(() => {
          savedY = null;
        }, 820);
      };

      palette.addEventListener("pointerdown", save, true);
      palette.addEventListener("click", () => {
        if (savedY === null) {
          save();
        }
        window.setTimeout(restore, 0);
      }, true);
      palette.addEventListener("change", restore, true);
      palette.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          save();
          window.setTimeout(restore, 0);
        }
      }, true);
    };

    const requestUpdate = () => {
      if (ticking) {
        return;
      }

      ticking = true;
      window.requestAnimationFrame(() => {
        update();
        ticking = false;
      });
    };

    window.addEventListener("scroll", () => {
      markScrolling();
      requestUpdate();
    }, { passive: true });
    window.addEventListener("resize", requestUpdate);
    preservePaletteScroll();
    requestUpdate();
  };

  if (typeof document$ !== "undefined") {
    document$.subscribe(initialize);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
