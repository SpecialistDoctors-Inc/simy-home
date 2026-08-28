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
const billingCycleButtons = Array.from(document.querySelectorAll("[data-billing-cycle]"));
const pricingPlans = Array.from(document.querySelectorAll("[data-pricing-plan]"));
const storagePrices = Array.from(document.querySelectorAll("[data-storage-capacity]"));
let activeBillingCycle = "annual";

function formatUsd(value, minimumFractionDigits = 0) {
  const rounded = Math.round((value + Number.EPSILON) * 100) / 100;
  const hasFraction = !Number.isInteger(rounded);
  return `$${rounded.toLocaleString("en-US", {
    minimumFractionDigits: Math.max(minimumFractionDigits, hasFraction ? 1 : 0),
    maximumFractionDigits: 2
  })}`;
}

function renderPricing() {
  const locale = window.SIMY_HOME_I18N?.locale || document.documentElement.lang || "en";
  const isJapanese = locale === "ja";

  billingCycleButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.billingCycle === activeBillingCycle));
  });

  document.querySelectorAll("[data-billing-copy]").forEach((element) => {
    element.hidden = element.dataset.billingCopy !== activeBillingCycle;
  });
  document.querySelectorAll("[data-annual-total]").forEach((element) => {
    element.hidden = activeBillingCycle !== "annual";
  });
  document.querySelectorAll("[data-tax-mode='exclusive']").forEach((element) => {
    element.hidden = isJapanese;
  });
  document.querySelectorAll("[data-tax-mode='inclusive']").forEach((element) => {
    element.hidden = !isJapanese;
  });
  document.querySelectorAll("[data-base-price-detail]").forEach((element) => {
    element.hidden = !isJapanese;
  });

  pricingPlans.forEach((plan) => {
    const basePriceCents = pricingCatalog.priceCents(plan.dataset.pricingPlan, activeBillingCycle);
    const displayPriceCents = isJapanese
      ? pricingCatalog.grossCents(basePriceCents, pricingCatalog.JAPAN_CONSUMPTION_TAX_BPS)
      : basePriceCents;
    const displayPrice = displayPriceCents / 100;
    const basePrice = basePriceCents / 100;
    const priceAmount = plan.querySelector("[data-price-amount]");
    const annualTotal = plan.querySelector("[data-price-total]");
    const basePriceDetail = plan.querySelector("[data-base-price]");

    if (priceAmount) priceAmount.textContent = formatUsd(displayPrice).slice(1);
    if (annualTotal) annualTotal.textContent = formatUsd(displayPriceCents * 12 / 100, 2);
    if (basePriceDetail) basePriceDetail.textContent = formatUsd(basePrice);
  });

  storagePrices.forEach((cell) => {
    const basePriceCents = pricingCatalog.storagePriceCents(cell.dataset.storageCapacity);
    const displayPriceCents = isJapanese
      ? pricingCatalog.grossCents(basePriceCents, pricingCatalog.JAPAN_CONSUMPTION_TAX_BPS)
      : basePriceCents;
    const amount = cell.querySelector("[data-storage-price-amount]");
    if (amount) amount.textContent = formatUsd(displayPriceCents / 100);
  });
}

billingCycleButtons.forEach((button) => {
  button.addEventListener("click", () => {
    activeBillingCycle = button.dataset.billingCycle === "monthly" ? "monthly" : "annual";
    renderPricing();
  });
});

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

const storageDialog = document.querySelector("[data-storage-dialog]");
const storageDialogOpenButtons = Array.from(document.querySelectorAll("[data-storage-dialog-open]"));
const storageDialogCloseButton = storageDialog?.querySelector("[data-storage-dialog-close]");
let storageDialogReturnFocus = null;

function closeStorageDialog() {
  if (!storageDialog?.open) return;
  storageDialog.close();
}

if (storageDialog) {
  storageDialogOpenButtons.forEach((button) => {
    button.addEventListener("click", () => {
      storageDialogReturnFocus = button;
      if (!storageDialog.open) storageDialog.showModal();
      document.body.classList.add("dialog-open");
      storageDialogCloseButton?.focus();
    });
  });

  storageDialogCloseButton?.addEventListener("click", closeStorageDialog);
  storageDialog.addEventListener("click", (event) => {
    if (event.target === storageDialog) closeStorageDialog();
  });
  storageDialog.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeStorageDialog();
  });
  storageDialog.addEventListener("close", () => {
    document.body.classList.remove("dialog-open");
    storageDialogReturnFocus?.focus();
    storageDialogReturnFocus = null;
  });
}

renderScenario("codex");
