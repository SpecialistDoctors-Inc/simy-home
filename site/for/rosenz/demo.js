"use strict";

const walkthrough = document.querySelector("#walkthrough-video");
const playWalkthrough = document.querySelector("#walkthrough-play");
const playLabel = document.querySelector("#walkthrough-play-label");
const walkthroughFallback = document.querySelector("#walkthrough-fallback");
const caption = document.querySelector("#walkthrough-mobile-caption");
const captionCues = [...caption.querySelectorAll("[data-start]")];
const estimate = document.querySelector(".walkthrough-estimate");
document.querySelector("#walkthrough-result-caption").append(estimate.cloneNode(true));

function updateCaption() {
  const current = captionCues.findLast(cue => walkthrough.currentTime >= Number(cue.dataset.start));
  for (const cue of captionCues) cue.hidden = cue !== current;
}

playWalkthrough.hidden = false;
playWalkthrough.addEventListener("click", () => {
  walkthrough.play().catch(() => {
    walkthroughFallback.hidden = false;
  });
});
walkthrough.addEventListener("playing", () => {
  if (document.activeElement === playWalkthrough) walkthrough.focus();
  playWalkthrough.hidden = true;
  walkthroughFallback.hidden = true;
  caption.hidden = false;
  updateCaption();
});
walkthrough.addEventListener("ended", () => {
  playLabel.textContent = "もう一度見る";
  playWalkthrough.hidden = false;
});
walkthrough.addEventListener("error", () => {
  walkthroughFallback.hidden = false;
}, true);
walkthrough.addEventListener("timeupdate", updateCaption);
walkthrough.addEventListener("seeked", updateCaption);
