const scenarios = {
  codex: {
    source: "Request in Codex",
    prompt: "Review this release before it ships. Check the user impact, evidence, and review quality.",
    acknowledgement: "I matched this work to your release-quality pipeline. Autorun is starting the essential checks now.",
    workflow: "Your release-quality pipeline",
    steps: [
      ["Recognize the work", "Done"],
      ["Select the matching pipeline", "Done"],
      ["Run the essential checks", "Running"],
      ["Update My Actions", "Next"]
    ],
    output: "No agent chosen · pipeline selected · Autorun running"
  },
  claude: {
    source: "Request in Claude Code",
    prompt: "Investigate this regression. Trace the cause before changing code and leave evidence another engineer can review.",
    acknowledgement: "I matched this to your investigation pipeline. Autorun is tracing the cause and preserving the review evidence now.",
    workflow: "Your investigation pipeline",
    steps: [
      ["Recognize the investigation", "Done"],
      ["Select the matching pipeline", "Done"],
      ["Trace cause and evidence", "Running"],
      ["Update My Actions", "Next"]
    ],
    output: "No agent chosen · investigation pipeline selected · Autorun running"
  },
  cowork: {
    source: "Request in Cowork",
    prompt: "Turn these updates into a concise decision brief. Surface only material changes and trace every claim to evidence.",
    acknowledgement: "I matched this to your decision-brief pipeline. Autorun is applying your materiality and evidence checks now.",
    workflow: "Your decision-brief pipeline",
    steps: [
      ["Recognize the briefing task", "Done"],
      ["Select the matching pipeline", "Done"],
      ["Apply the briefing checks", "Running"],
      ["Update My Actions", "Next"]
    ],
    output: "No agent chosen · briefing pipeline selected · Autorun running"
  }
};

const scenarioButtons = Array.from(document.querySelectorAll("[data-scenario]"));
const sourceElement = document.querySelector("[data-demo-source]");
const promptElement = document.querySelector("[data-demo-prompt]");
const acknowledgementElement = document.querySelector("[data-demo-acknowledgement]");
const workflowElement = document.querySelector("[data-demo-workflow]");
const outputElement = document.querySelector("[data-demo-output]");
const stepElements = Array.from(document.querySelectorAll("[data-demo-step]"));
let activeScenario = "codex";

function translateHomeText(value) {
  return window.SIMY_HOME_I18N?.translate(value) ?? value;
}

function renderScenario(name) {
  const scenario = scenarios[name];
  if (!scenario) return;
  activeScenario = name;

  scenarioButtons.forEach((button) => {
    const selected = button.dataset.scenario === name;
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
  });

  sourceElement.textContent = translateHomeText(scenario.source);
  promptElement.textContent = translateHomeText(scenario.prompt);
  acknowledgementElement.textContent = translateHomeText(scenario.acknowledgement);
  workflowElement.textContent = translateHomeText(scenario.workflow);
  outputElement.textContent = translateHomeText(scenario.output);

  stepElements.forEach((step, index) => {
    const stepData = scenario.steps[index];
    step.querySelector("[data-step-label]").textContent = translateHomeText(stepData[0]);
    const status = step.querySelector("[data-step-status]");
    status.textContent = translateHomeText(stepData[1]);
    status.dataset.status = stepData[1].toLowerCase().replaceAll(" ", "-");
  });
}

scenarioButtons.forEach((button, index) => {
  button.addEventListener("click", () => renderScenario(button.dataset.scenario));
  button.addEventListener("keydown", (event) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    let nextIndex = index;
    if (event.key === 'ArrowLeft') nextIndex = (index - 1 + scenarioButtons.length) % scenarioButtons.length;
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % scenarioButtons.length;
    if (event.key === 'Home') nextIndex = 0;
    if (event.key === 'End') nextIndex = scenarioButtons.length - 1;
    scenarioButtons[nextIndex].focus();
    renderScenario(scenarioButtons[nextIndex].dataset.scenario);
  });
});

const menuButton = document.querySelector("[data-menu-button]");
const mobileMenu = document.querySelector("[data-mobile-menu]");

if (menuButton && mobileMenu) {
  const menuLabel = menuButton.querySelector(".sr-only");
  const pageMain = document.querySelector("main");
  const headerBrand = document.querySelector(".nav-frame > .brand");
  const menuItems = Array.from(mobileMenu.querySelectorAll("a[href], button:not([disabled]), select:not([disabled])"));
  const menuCloseItems = Array.from(mobileMenu.querySelectorAll("a[href], button:not([disabled])"));
  const setMenuOpen = (open) => {
    menuButton.setAttribute("aria-expanded", String(open));
    menuLabel.textContent = translateHomeText(open ? "Close navigation" : "Open navigation");
    mobileMenu.hidden = !open;
    pageMain.toggleAttribute("inert", open);
    headerBrand.toggleAttribute("inert", open);
    if (open) {
      pageMain.setAttribute("aria-hidden", "true");
      headerBrand.setAttribute("aria-hidden", "true");
    } else {
      pageMain.removeAttribute("aria-hidden");
      headerBrand.removeAttribute("aria-hidden");
    }
    document.body.classList.toggle("menu-open", open);
  };

  menuButton.addEventListener("click", () => {
    setMenuOpen(menuButton.getAttribute("aria-expanded") !== "true");
  });

  menuCloseItems.forEach((item) => {
    item.addEventListener("click", () => setMenuOpen(false));
  });
  mobileMenu.querySelectorAll("[data-locale-select]").forEach((select) => {
    select.addEventListener("change", () => setMenuOpen(false));
  });

  mobileMenu.addEventListener("click", (event) => {
    if (event.target === mobileMenu) setMenuOpen(false);
  });

  document.addEventListener("pointerdown", (event) => {
    const open = menuButton.getAttribute("aria-expanded") === "true";
    if (!open || menuButton.contains(event.target) || mobileMenu.contains(event.target)) return;
    setMenuOpen(false);
  });

  document.addEventListener("keydown", (event) => {
    const open = menuButton.getAttribute("aria-expanded") === "true";
    if (!open) return;

    if (event.key === "Escape") {
      setMenuOpen(false);
      menuButton.focus();
      return;
    }

    if (event.key === "Tab") {
      const firstLink = menuItems[0];
      const lastLink = menuItems[menuItems.length - 1];
      if (event.shiftKey && document.activeElement === menuButton) {
        event.preventDefault();
        lastLink.focus();
      } else if (event.shiftKey && document.activeElement === firstLink) {
        event.preventDefault();
        menuButton.focus();
      } else if (!event.shiftKey && document.activeElement === menuButton) {
        event.preventDefault();
        firstLink.focus();
      } else if (!event.shiftKey && document.activeElement === lastLink) {
        event.preventDefault();
        menuButton.focus();
      } else if (document.activeElement !== menuButton && !mobileMenu.contains(document.activeElement)) {
        event.preventDefault();
        firstLink.focus();
      }
    }
  });

  window.matchMedia("(min-width: 1440px)").addEventListener("change", (event) => {
    if (event.matches) setMenuOpen(false);
  });
}

window.addEventListener("simy:locale-change", () => renderScenario(activeScenario));

const yearElement = document.querySelector("[data-current-year]");
if (yearElement) yearElement.textContent = new Date().getFullYear();

const motionLoops = Array.from(document.querySelectorAll("[data-motion-loop]"));
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

if (motionLoops.length) {
  if (reduceMotion.matches || !("IntersectionObserver" in window)) {
    motionLoops.forEach((element) => element.classList.add("is-in-view"));
  } else {
    const motionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          entry.target.classList.toggle("is-in-view", entry.isIntersecting);
        });
      },
      { threshold: 0.22 }
    );

    motionLoops.forEach((element) => motionObserver.observe(element));
  }
}

const pricingTableWrap = document.querySelector(".pricing-table-wrap");
const featuredPricingPlan = pricingTableWrap?.querySelector(".pricing-pro");
const pricingFeatureHeader = pricingTableWrap?.querySelector("thead th:first-child");
const compactPricing = window.matchMedia("(max-width: 620px)");
let hasCenteredFeaturedPlan = false;
let centeredPricingWidth = 0;

function centerFeaturedPricingPlan() {
  if (!pricingTableWrap || !featuredPricingPlan || !compactPricing.matches || hasCenteredFeaturedPlan) return;

  window.requestAnimationFrame(() => {
    pricingTableWrap.scrollLeft = Math.max(
      0,
      featuredPricingPlan.offsetLeft - (pricingFeatureHeader?.offsetWidth ?? 0)
    );
    centeredPricingWidth = pricingTableWrap.clientWidth;
    hasCenteredFeaturedPlan = true;
  });
}

centerFeaturedPricingPlan();
compactPricing.addEventListener("change", (event) => {
  if (!event.matches) return;
  hasCenteredFeaturedPlan = false;
  centerFeaturedPricingPlan();
});
window.addEventListener("resize", () => {
  if (!compactPricing.matches || pricingTableWrap?.clientWidth === centeredPricingWidth) return;
  hasCenteredFeaturedPlan = false;
  centerFeaturedPricingPlan();
});

renderScenario("codex");
