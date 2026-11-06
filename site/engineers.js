(() => {
  const source = document.getElementById("engineering-data");
  if (!source) return;
  const examples = JSON.parse(source.textContent);
  const buttons = [...document.querySelectorAll("[data-example]")];
  buttons.forEach((button, index) => {
    button.addEventListener("click", () => {
      const example = examples[index];
      document.querySelector("[data-request]").textContent = example.request;
      document.querySelector("[data-hint]").textContent = example.hint;
      document.querySelector("[data-benefit]").textContent = example.benefit;
      example.outputs.forEach((text, i) => {
        document.querySelector(`[data-output="${i}"]`).textContent = text;
      });
      buttons.forEach((item, i) =>
        item.setAttribute("aria-pressed", String(i === index)),
      );
      document.querySelector("[data-announcement]").textContent =
        `${example.request} ${example.outputs.join("。")}`;
    });
  });
  document.querySelectorAll("[data-enhancement]").forEach((element) => {
    element.hidden = false;
  });
})();
