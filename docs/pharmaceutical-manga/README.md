# Eight-scene manga delivery

Status: implementation preparation; the eight new illustrations have not been generated.

## Ready

- `storyboard.md`: eight scenes, camera positions, acting and narrative changes.
- `art-prompts.json` and `prompts/scene-01.txt` through `scene-08.txt`: final illustration briefs, shared character identity and localized HTML lettering policy.
- `scripts/pharmaceutical_manga_art.py`: full-scene art above each localized dialogue. Repeated portraits are removed when the complete artwork set is available.
- `scripts/build-pharmaceutical-pages.py --require-manga-art`: verifies all eight originals exist and are distinct before writing any locale.
- Full-scene CSS for desktop/mobile. Existing six-language dialogue and narration remain accessible text.

## Remaining

1. Generate eight full-scene originals using the imagegen skill CLI and an authenticated image API.
2. Inspect actual output: character continuity, one physician in real/simulated meetings, body poses, surroundings, hands/devices, and visual changes between scenes 1/6 and 4/5.
3. Export the accepted originals to `site/assets/pharmaceutical-companies/manga-v2/scene-01.webp` through `scene-08.webp`. Preserve generated masters outside deployed assets.
4. Generate with `--require-manga-art`, run the locale/browser checks against the actual artwork, then merge and verify production.

The ordinary generation path keeps the existing release intact while no new artwork exists. It must not be used as evidence that the new comic is finished. Partial delivery and duplicate artwork fail validation rather than silently reusing an image.

## Image generation readiness

The user authorized the image API/CLI fallback. The standard `image_gen` tool is unavailable in this chat, and the process environment and checked SIMY/shell configurations do not provide `OPENAI_API_KEY`. Repository-level secret names did not expose an image API credential; organization secret discovery returned HTTP 403. No credential was extracted, printed, or substituted from another authentication system. Do not bypass that access boundary.

The bundled imagegen CLI and its OpenAI dependency are installed in the task's existing temporary Python environment. A dry run of scene 1 with the real reference artwork, `gpt-image-2`, 1536×1024 and high quality passed. A dry run is not an API call or a generated illustration.

Once an authorized API key is available to the process, invoke the bundled CLI directly. Example from the repository root:

```bash
/tmp/simy-ui-design-venv/bin/python \
  /home/tshiwaku/.codex/skills/.system/imagegen/scripts/image_gen.py edit \
  --model gpt-image-2 \
  --image site/assets/engineer-manga/release-crew-ja.webp \
  --prompt-file docs/pharmaceutical-manga/prompts/scene-01.txt \
  --size 1536x1024 --quality high \
  --out output/imagegen/pharma-manga-v2/scene-01.png
```

For later scenes, keep the original artwork as the first character/style reference and add the approved scene 1 image as a second identity reference for the physician and room. Give the inputs those roles explicitly in the prompt. Invoke one edit operation for each distinct scene and inspect output before selecting it. Never commit credentials or mistake a layout fixture for final artwork.
