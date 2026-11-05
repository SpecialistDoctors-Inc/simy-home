# Built-in image generation record

Generator: built-in `image_gen`, eight separate generation calls. Source images were identity/style references, not crop/edit targets. Final prompt set: the corresponding full brief in `prompts/scene-01.txt` through `scene-08.txt`, with the continuity direction below. All calls requested an opaque background.

| Scene | Reference images (in order) | Additional direction |
| --- | --- | --- |
| 01 | Engineering original | Base brief without additions. Establish physician and room. |
| 02 | Engineering original | Base brief without additions. Replay recording and mark the open question. |
| 03 | Engineering original, 01, 02 | Reference 2 establishes physician and MR clothing; reference 3 the review workspace. Only MR and SIMY physically present. |
| 04 | Engineering original, 01, 03 | Preserve exact physician, suit, hair, evening office, lamp, window and desk. Only MR physically present; physician only inside blue-framed smartphone. New side-profile camera; speaking while holding folder, raised eyebrows and sweat bead; avoid hand-on-chin pose. |
| 05 | Engineering original, 04 | New camera from phone side, MR three-quarter front, calm curious expression and open palm. Pull back to relaxed torso and both hands. Folder flat and closed on desk, phone foreground right with same physician. Same evening window and black lamp. No physical doctor or colleague, no lettering. |
| 06 | Engineering original, 01, 04 | Exact consultation room, gray swept-haired physician with rectangular glasses, MR suit, gray-suited colleague. Reverse camera with MR left and physician right. Same daylight window, medical shelf, wood desk and openly placed black recorder. MR checks patient icons; physician draws hospital above linked staff roles. Progress in listening, no triumphant success. |
| 07 | Engineering original, 06, 03 | Carry patient-group icon and hospital-role diagram into tablet screen. SIMY uses established square smiling identity. Tablet dominates scene; new waveform feeds two cards. Left: patient group. Right: same group plus hospital and linked staff, update arrow and highlighted addition. Hands visible, quiet office, no words. |
| 08 | Engineering original, 01, 07 | Preserve exact MR and gray-jacket round-glasses colleague. Wide daytime office; colleague left points at shared monitor, MR right takes notes. Monitor connects patient group and hospital roles to blue-framed physician, question icon and coaching checklist. Small SIMY. No celebration, lettering, or reused engineering screen. |

The files under `output/imagegen/pharma-manga-v2/` preserve the accepted PNG masters. `art-manifest.json` identifies the WebP exports. All eight generated outputs were visually inspected before export and again in the assembled comic.
