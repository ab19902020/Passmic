# Claude handoff — unfinished Pass Mic cut-out cleanup

Date: 2026-09-24

This file records the work recovered from the previous ChatGPT/Esther session after it ran out of usage. The fixes below were reconstructed on top of the current `main`; they are not claimed to be a byte-for-byte recovery of an uncommitted local workspace.

## What has been completed in this handoff

### 1. Pose transitions no longer fade body parts independently
File: `render/render.py`

The previous pose dissolve applied partial opacity to the body, head and articulated arms separately. Because those pieces overlap, the character could look semi-transparent during a pose change.

The new implementation renders each complete puppet pose at full opacity against the same base frame, then crossfades the two completed snapshots. This preserves the opaque paper-cutout/South-Park-style look while keeping the existing short pose dissolve.

Commit: `0e13394aa7cb1876831c7596bb92d9f307d7ed85`

### 2. Jamie Carragher lower-face/chin split recovered
File: `tools/build_assets.py`

The old generic head cutoff ended too close to the neck, which could leave the bottom of Jamie's beard/chin on the body layer. When the head rotated, this could look like the lower chin had been sliced off.

All four Carra drawings now get a deeper head tail before the neck/collar reconstruction fills the hidden seam.

### 3. Gary Neville pointing/raised hands kept out of the head mask
Files: `tools/build_assets.py`, using `masks/rig.json`

Gary's broad head ellipse could capture pixels from a nearby raised or pointing arm/hand. Those pixels then moved with the head.

For Neville sprites, the traced arm polygons from `masks/rig.json` are now subtracted from the head mask before the connected head blob is selected.

Commit for items 2–3: `414557570bea944ae40590c01202c51cbceb1ece`

## IMPORTANT — still to do

The generated PNG sprites in `assets/` have **not** been rebuilt in this recovery session. The source/pipeline fixes are committed, but Claude should regenerate the assets before judging the visual result.

Run:

```bash
pip install -r requirements.txt
python3 tools/build_assets.py
```

Then inspect all 12 generated pundit poses, with particular attention to:

- Jamie/Carra A, B, C and D: beard/chin must rotate with the head, with no duplicated lower-face fragment left on the body.
- Gary/Nev A/B/C/D: raised and pointing hands must stay with the arm/body rig and must never move with the head.
- Sleeves, trouser edges, gaps between arms and torso, and chair/studio scraps: look for any remaining square/rectangular background bites.
- Shoulder rotations: look for gaps, shirt-colour fill showing outside the torso, or arm polygons exposing the old background.
- Pose-change moments: characters should remain fully opaque throughout the dissolve.

If a remaining background scrap is found, extend the relevant polygon in `masks/clean.json` rather than blurring the character edge globally.

## Fast visual QA

Targeted frames:

```bash
python3 render/render.py test 62 150
```

Whole-video contact sheet:

```bash
python3 tools/contact_sheet.py 0.5 225 3 out/sheet.jpg
```

After any change to `render/render.py` or regenerated assets, remove stale segment markers before a full render:

```bash
rm -f out/*.done
bash render/run.sh
```

Use a 1080p review render first. Only spend the time on `QUALITY=1080p60` or `QUALITY=4k60` after the cutouts and pose transitions pass visual QA.

## Known existing issue

`nev2` still loses the right edge of the word **UNITED!** on the hoodie because the source mask cuts it off. This was already documented in the README and was not solved in this recovery.

## Project constraints to preserve

- Keep the current 2.5D cut-out/cartoon visual direction.
- Keep the workflow free/offline; do not introduce Runway or another paid video-generation dependency.
- Preserve the existing lyric-driven edit, lip sync, arm rig, breakdance sections, camera work and current scene structure unless a visual fix requires a tightly scoped change.
- Do not bring back on-screen lyric/caption overlays; the current direction is no added text overlays.
- Use `main` as the continuation point after this handoff is merged. The old `claude/music-video-repo-setup-vt99ro` branch is behind `main` and should not be used as the new base.

## Recommended next Claude task

1. Pull latest `main`.
2. Run `python3 tools/build_assets.py`.
3. Render targeted frames + contact sheet.
4. Correct any remaining cutout polygons in `masks/clean.json` / `masks/rig.json`.
5. Specifically verify Jamie's chin in close-ups and Gary's pointing hand during head movement.
6. Render a short representative video section before committing to the full 3:45 render.
7. Commit any generated asset changes and final cleanup back to `main`.

No full render was completed or visually validated during this recovery session, so that QA/render pass is the main unfinished work.

## Status (Claude, follow-up)

Done:
- Rebuilt the assets with the handoff fixes. Carra's chin now rotates with his head, and Gary's hands stay on the arm/body layer during head tilts. Both were checked visually on all eight Carra/Gary drawings.
- The snapshot crossfade for pose changes still showed a double image of the whole character for ~3 frames. Drawings now swap instantly on the beat (cut-out style) with a small squash-and-stretch pop, so there is no ghosting.
- Contact sheet reviewed and full 1080p render produced.
