(() => {
  const source = document.getElementById("experience-data");
  if (!source) return;
  const copy = JSON.parse(source.textContent);
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const controllers = [];
  const frameDuration = 4200;

  document.querySelectorAll("[data-demo]").forEach((demo) => {
    const frames = [...demo.querySelectorAll("[data-frame]")];
    const steps = [...demo.querySelectorAll("[data-step]")];
    const control = demo.querySelector("[data-motion]");
    let index = 0;
    let visible = false;
    let pausedByUser = false;
    let timer;
    function show(next) {
      index = next;
      frames.forEach((frame, i) => {
        frame.hidden = i !== index;
      });
      steps.forEach((step, i) =>
        step.setAttribute("aria-pressed", String(i === index)),
      );
    }
    function sync() {
      clearInterval(timer);
      const playing =
        visible && !document.hidden && !reduced.matches && !pausedByUser;
      demo.dataset.playing = String(playing);
      control.textContent = reduced.matches
        ? copy.next
        : pausedByUser
          ? copy.play
          : copy.pause;
      if (playing)
        timer = setInterval(
          () => show((index + 1) % frames.length),
          frameDuration,
        );
    }
    control.addEventListener("click", () => {
      // OS reduced motion remains authoritative; manual step selection still works.
      if (reduced.matches) {
        show((index + 1) % frames.length);
        return;
      }
      pausedByUser = !pausedByUser;
      sync();
    });
    steps.forEach((step, i) =>
      step.addEventListener("click", () => {
        pausedByUser = true;
        show(i);
        sync();
      }),
    );
    new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting;
        sync();
      },
      { threshold: 0.25 },
    ).observe(demo);
    // Do not replace a frame while a user is focusing its full-size link.
    demo.querySelector(".demo-stage").addEventListener("focusin", () => {
      pausedByUser = true;
      sync();
    });
    controllers.push(sync);
    show(0);
    sync();
  });
  // A short illustrative comparison; settles on the readable result in under 2 seconds.
  const hero = document.querySelector("[data-hero-demo]");
  if (hero) {
    const replay = hero.querySelector("[data-hero-replay]");
    let played = false;
    let finish;
    const stop = () => {
      clearTimeout(finish);
      hero.dataset.heroRunning = "false";
    };
    const play = () => {
      stop();
      if (reduced.matches || document.hidden) return;
      // Restart CSS animation when the reader replays it.
      void hero.offsetWidth;
      hero.dataset.heroRunning = "true";
      finish = setTimeout(stop, 1900);
    };
    const syncHero = () => {
      replay.hidden = reduced.matches;
      if (reduced.matches || document.hidden) stop();
    };
    replay.addEventListener("click", play);
    new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) stop();
        else if (
          entry.intersectionRatio >= 0.6 &&
          !played &&
          !document.hidden
        ) {
          played = true;
          play();
        }
      },
      { threshold: 0.6 },
    ).observe(hero.querySelector(".hero-comparison"));
    controllers.push(syncHero);
    syncHero();
  }
  document.addEventListener("visibilitychange", () =>
    controllers.forEach((sync) => sync()),
  );
  reduced.addEventListener("change", () =>
    controllers.forEach((sync) => sync()),
  );

  document.querySelectorAll("[data-share]").forEach((button) => {
    const section = button.closest(".experience-story");
    const status = section.querySelector("[data-share-status]");
    const fallback = section.querySelector(".share-fallback");
    const input = fallback.querySelector("input");
    let generation = 0;
    button.addEventListener("click", async () => {
      const current = ++generation;
      const url = new URL(location.pathname, location.origin);
      url.hash = `scene-${button.dataset.share}`;
      fallback.hidden = true;
      status.textContent = "";
      try {
        if (!navigator.clipboard?.writeText)
          throw new Error("Clipboard unavailable");
        await navigator.clipboard.writeText(url.href);
        if (generation === current) status.textContent = copy.copied;
      } catch {
        if (generation !== current) return;
        status.textContent = copy.copyFailed;
        input.value = url.href;
        fallback.hidden = false;
        input.focus();
        input.select();
      }
    });
  });
  document.querySelectorAll("[data-enhancement]").forEach((element) => {
    element.hidden = false;
  });
  const aliases = {
    "#scene-outcome": "#scene-build",
    "#scene-decision": "#scene-progress",
    "#delivery": "#scene-build",
    "#sqm": "#scene-knowledge",
    "#example": "#scene-build",
  };
  function restoreAlias() {
    const target = aliases[location.hash];
    if (target) {
      history.replaceState(null, "", target);
    }
    const scene = document.getElementById((target || location.hash).slice(1));
    const folded = scene?.closest("details.manga-more");
    if (folded) folded.open = true;
    if (target || folded) scene?.scrollIntoView();
  }
  restoreAlias();
  window.addEventListener("hashchange", restoreAlias);
})();
