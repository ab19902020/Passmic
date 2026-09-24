# Pass Mic — "Gary, Pass the Microphone" music video

A 2.5D cut-out music video (South Park style) built from the original artwork in `source/`.
Everything is rendered offline with Python + OpenCV, then encoded with ffmpeg:
1920x1080, 24 fps, 3:45, with the song muxed in.

## Quick start
```bash
pip install -r requirements.txt          # plus ffmpeg on PATH (auto-installed in Claude Code web sessions)
python3 render/render.py test 62 150      # writes out/f_62.jpg, out/f_150.jpg (single frames)
bash render/run.sh                        # full render -> out/pass_mic.mp4 (parallel over all cores, resumable)
```

## Layout
| Path | What it is |
|---|---|
| `render/render.py` | The whole video: song map, choreography, camera director, scenes, effects. `render(t)` returns one frame. |
| `render/run.sh` | Renders 8 segments (skips finished ones), concatenates, adds the song. |
| `assets/` | Cut-out sprites. `<name>_body.png` / `<name>_head.png` per pose, `meta.json` (anchors), `mouths.json` (mouth positions), `groups.json` + `mgr4_*`, `mgr5_body.png` (managers), `siralex.png`, `plate_rows.png` + `hole.png` (studio backdrop). |
| `masks/` | Cut-out masks (`maskc_*.png`), traced outlines (`poly_*.txt`) and `clean.json` (hand-traced polygons erasing background scraps from the pundit sprites). |
| `data/` | `audio_feat.npz` (vocal/energy envelopes), `mouth_curve.npz` (syllable-timed lip sync). |
| `fonts/` | Poppins Bold / Bold Italic (OFL) used for the title card and placards. |
| `source/` | Original artwork (18306, 18307, 18346, 18348, 18349) and the song. |
| `tools/` | Asset pipeline: `build_assets.py` (pundit sprites + head split), `groups_build.py` (dancing managers), `fix_conga.py` (conga line incl. Amorim + Carrick 2026 placard), `build_mouth_curve.py`, and the segmentation helpers (`trimap.py`, `mgr.py`, `grid.py`, ...). |

## Poses
Each pundit has four poses: A = `*1` (18306), B = `*2` (18307), C = `*5` (18346 squat), D = `*4` (18349 beer).
Pose choice lives in `pose()` in `render.py` (`pose=0..3`).

## Song-driven events (in `render.py`)
- `MICEV`: mic passes, timed to the "pass the microphone" lines and the "Gary" call-outs.
- `GARY`: Gary spotlight + the others lean in.
- `CHAMP`: champagne pop on each "champagne socialist" line.
- `SECTIONS` (in beats, 145.09 BPM): drives moves, lighting, scenes (`scene_for`: studio / grid / pitch).
- No lyrics are drawn on screen.
- Polish: glossy floor reflections (studio/grid), a scrolling LED board on the pitch rail, a sparkle trail on mic tosses, and an RGB-split kick on the beat in the big sections.

## Checking changes
`python3 tools/contact_sheet.py 0.5 225 3 out/sheet.jpg` renders a labelled thumbnail every 3 s (time, beat, section, shot) across all cores. It's the fastest way to review the whole video.

## Open issues / next steps
- Fixed: Gary's "weird shadow". `build_assets.py` now paints a short skin-toned neck and collar under each head (it used to paint a dark shirt-coloured block), extends the head over the head/body seam, and trims hair slivers. Background scraps are erased via `masks/clean.json`.
- Lip sync: mouth anchors in `assets/mouths.json` sit on each pose's drawn mouth, so the jaw opens there. It is syllable-timed, not phoneme-accurate.
- Background managers no longer lip sync (disabled on purpose). The conga line and Sir Alex never did.
- `nev2` (Gary, pose B) loses the right edge of "UNITED!" on the hoodie. The source mask cuts it off.
- David Moyes is not in any source artwork, so he is not in the video.
- Render speed ~0.27 s/frame per core; `run.sh` renders 350-frame segments in parallel (`JOBS=n` to limit). Delete `out/*.done` after changing `render.py`.
