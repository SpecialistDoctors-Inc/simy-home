const scenarios = {
  codex: {
    source: "Request in Codex",
    prompt: "Review this release before it ships. Check the user impact, evidence, and review quality.",
    acknowledgement: "I matched this work to your release-quality workflow. Autorun is starting the essential checks now.",
    workflow: "Your release-quality workflow",
    steps: [
      ["Recognize the work", "Done"],
      ["Select the matching workflow", "Done"],
      ["Run the essential checks", "Running"],
      ["Update My Actions", "Next"]
    ],
    output: "No agent chosen · workflow selected · Autorun running"
  },
  claude: {
    source: "Request in Claude Code",
    prompt: "Investigate this regression. Trace the cause before changing code and leave evidence another engineer can review.",
    acknowledgement: "I matched this to your investigation workflow. Autorun is tracing the cause and preserving the review evidence now.",
    workflow: "Your investigation workflow",
    steps: [
      ["Recognize the investigation", "Done"],
      ["Select the matching workflow", "Done"],
      ["Trace cause and evidence", "Running"],
      ["Update My Actions", "Next"]
    ],
    output: "No agent chosen · investigation workflow selected · Autorun running"
  },
  cowork: {
    source: "Request in Cowork",
    prompt: "Turn these updates into a concise decision brief. Surface only material changes and trace every claim to evidence.",
    acknowledgement: "I matched this to your decision-brief workflow. Autorun is applying your materiality and evidence checks now.",
    workflow: "Your decision-brief workflow",
    steps: [
      ["Recognize the briefing task", "Done"],
      ["Select the matching workflow", "Done"],
      ["Apply the briefing checks", "Running"],
      ["Update My Actions", "Next"]
    ],
    output: "No agent chosen · briefing workflow selected · Autorun running"
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
const languagePicker = document.querySelector("[data-language-picker]");

if (languagePicker) {
  const languageTrigger = languagePicker.querySelector(".language-trigger");
  const languagePanel = languagePicker.querySelector("[data-language-panel]");
  const languageOptions = Array.from(languagePanel.querySelectorAll("[data-locale-option]"));
  const setLanguagePickerOpen = (open, { focusOption = false } = {}) => {
    languagePicker.open = open;
    languageTrigger.setAttribute("aria-expanded", String(open));
    languagePicker.classList.toggle("is-open", open);
    if (open && focusOption) {
      (languageOptions.find((option) => option.hasAttribute("aria-current")) || languageOptions[0])?.focus();
    }
  };

  setLanguagePickerOpen(languagePicker.open);
  languagePicker.addEventListener("toggle", () => {
    const open = languagePicker.open;
    languageTrigger.setAttribute("aria-expanded", String(open));
    languagePicker.classList.toggle("is-open", open);
  });
  languageTrigger.addEventListener("keydown", (event) => {
    if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return;
    event.preventDefault();
    setLanguagePickerOpen(true, { focusOption: true });
  });
  languageOptions.forEach((option, index) => {
    option.addEventListener("click", () => setLanguagePickerOpen(false));
    option.addEventListener("keydown", (event) => {
      if (!['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight', 'Home', 'End', 'Escape'].includes(event.key)) return;
      event.preventDefault();
      if (event.key === 'Escape') {
        setLanguagePickerOpen(false);
        languageTrigger.focus();
        return;
      }
      const columns = window.matchMedia("(max-width: 620px)").matches ? 3 : 2;
      let nextIndex = index;
      if (event.key === 'ArrowDown' && index + columns < languageOptions.length) nextIndex = index + columns;
      if (event.key === 'ArrowUp' && index - columns >= 0) nextIndex = index - columns;
      if (event.key === 'ArrowRight' && index % columns < columns - 1 && index + 1 < languageOptions.length) nextIndex = index + 1;
      if (event.key === 'ArrowLeft' && index % columns > 0) nextIndex = index - 1;
      if (event.key === 'Home') nextIndex = 0;
      if (event.key === 'End') nextIndex = languageOptions.length - 1;
      languageOptions[nextIndex].focus();
    });
  });
  languagePicker.addEventListener("focusout", () => {
    window.setTimeout(() => {
      if (!languagePicker.contains(document.activeElement)) setLanguagePickerOpen(false);
    }, 0);
  });
  document.addEventListener("pointerdown", (event) => {
    if (!languagePicker.contains(event.target)) setLanguagePickerOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !languagePicker.open) return;
    setLanguagePickerOpen(false);
    languageTrigger.focus();
  });
  window.matchMedia("(max-width: 1439px)").addEventListener("change", () => setLanguagePickerOpen(false));
}

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

const pricingCatalog = window.SIMY_PRICING;
const pricingPlans = Array.from(document.querySelectorAll("[data-pricing-plan]"));

function formatUsd(cents) {
  return "$" + (cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: cents % 100 === 0 ? 0 : 2,
    maximumFractionDigits: 2
  });
}

function renderPricing() {
  const locale = window.SIMY_HOME_I18N?.locale || document.documentElement.lang || "en";
  const isJapanese = locale === "ja";

  document.querySelectorAll("[data-tax-included-price-detail]").forEach((element) => {
    element.hidden = !isJapanese;
  });

  pricingPlans.forEach((plan) => {
    const basePriceCents = pricingCatalog.priceCents(plan.dataset.pricingPlan);
    const taxInclusivePriceCents = pricingCatalog.grossCents(
      basePriceCents,
      pricingCatalog.JAPAN_CONSUMPTION_TAX_BPS
    );
    const priceAmount = plan.querySelector("[data-price-amount]");
    const taxIncludedPrice = plan.querySelector("[data-tax-included-price]");

    if (priceAmount) priceAmount.textContent = formatUsd(basePriceCents).slice(1);
    if (taxIncludedPrice) taxIncludedPrice.textContent = formatUsd(taxInclusivePriceCents);
  });
}

window.addEventListener("simy:locale-change", renderPricing);
renderPricing();

const pricingTableWrap = document.querySelector(".pricing-table-wrap");
const featuredPricingPlan = pricingTableWrap?.querySelector(".pricing-quality");
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
