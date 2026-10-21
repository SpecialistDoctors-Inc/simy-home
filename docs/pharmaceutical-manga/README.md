# Eight-scene manga delivery

Eight new full-scene originals were generated on Mac with the built-in `image_gen` tool on 2026-10-21. No API fallback or additional subscription was used.

## Artwork and sources

- Character/style reference: `site/assets/engineer-manga/release-crew-ja.webp`.
- PNG masters, outside the deployed `site/` tree: `output/imagegen/pharma-manga-v2/scene-01.png` through `scene-08.png`.
- Deployed WebP: `site/assets/pharmaceutical-companies/manga-v2/scene-01.webp` through `scene-08.webp` (1536×1024, quality 88).
- `art-manifest.json` records paths, dimensions, sizes and SHA256 values.
- `art-prompts.json` and `prompts/scene-*.txt` contain the base briefs. `generation-notes.md` records continuity references and scene-specific direction used in the built-in calls.

All eight outputs were inspected individually. Scenes 1/6 return to the same physician and hospital room, with a reverse camera and a new hospital-roles question. Scenes 4/5 keep the evening workspace and simulated doctor inside the phone, changing the MR's raised-folder, anxious posture to a relaxed question with the folder laid down. Scene 7 carries the hospital roles diagram into the updated practice card. Scene 8 connects that topic to coaching with the round-glasses colleague. The colleague also accompanies the real meetings. Images are newly generated compositions, not crops from the engineering comic.

Dialogue, narration, speaker names, and the AI-doctor distinction remain accessible localized HTML in all six languages; no translated dialogue is baked into the art. The existing hero promise remains unchanged.

## Reproduction and verification

```bash
python3 scripts/build-pharmaceutical-pages.py --require-manga-art
python3 scripts/build-pharmaceutical-pages.py --check --require-manga-art
python3 scripts/build-localized-home.py --check
python3 scripts/check-home-seo.py
python3 scripts/check-site-seo.py
node --test tests/*.test.cjs
git diff --check
```

The artwork guard rejects missing or byte-identical images. Its fixture test renders the maintained localized template before artwork injection, so it also works after the released pages contain their final art.

`tests/pharmaceutical-manga-browser.cjs` checks six languages at 1440, 390, 320 and 720 CSS pixels (the latter also models the effective width of a 1440px desktop at 200% zoom). It decodes all eight images, checks horizontal overflow and panel edges within 1px, and captures desktop/mobile evidence. `PHARMA_BASE` selects local or production origin; `PHARMA_EVIDENCE` selects the evidence directory. Browser screenshots verify simulated viewport behavior, not physical phone acceptance.

The initial NVIDIA authentication blocker and original handoff are historical context in `mac-handoff.md`; the Mac built-in tool resolved that blocker. Current verification and publication evidence is recorded in `verification.md`.
