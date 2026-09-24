# Pass Mic — "Gary, Pass the Microphone" music video

A 2.5D cut-out music video (South Park style) built from the original artwork in `source/`.
Everything is rendered offline with Python + OpenCV, then encoded with ffmpeg:
1920x1080, 24 fps, 3:45, with the song muxed in.

## Quick start
```bash
pip install -r requirements.txt          # plus ffmpeg on PATH (auto-installed in Claude Code web sessions)
python3 render/render.py test 62 150      # writes out/f_62.jpg, out/f_150.jpg (single frames)
bash render/run.sh                        # full render -> out/pass_mic.mp4 (~25 min on 1 CPU, resumable)
```

## Layout
| Path | What it is |
|---|---|
| `render/render.py` | The whole video: song map, choreography, camera director, scenes, effects. `render(t)` returns one frame. |
| `render/run.sh` | Renders 8 segments (skips finished ones), concatenates, adds the song. |
| `assets/` | Cut-out sprites. `<name>_body.png` / `<name>_head.png` per pose, `meta.json` (anchors), `mouths.json` (mouth positions), `groups.json` + `mgr4_*`, `mgr5_body.png` (managers), `siralex.png`, `plate_rows.png` + `hole.png` (studio backdrop). |
| `masks/` | Cut-out masks (`maskc_*.png`) and traced outlines (`poly_*.txt`) the sprites are built from. |
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

## Open issues / next steps
- **Gary's "weird shadow"**: when his head tilts, the neck fill (shirt colour painted under the head in `build_assets.py`) and the dark outline sprite (`_ol_rim` in `render.py`) can show as a dark patch beside his face. Try a smaller neck fill, skin-toned neck, or dropping `head_ol`.
- Background managers no longer lip sync (disabled on purpose). The conga line and Sir Alex never did.
- Lip sync is syllable-timed, not phoneme-accurate; mouth positions per pose are in `assets/mouths.json`.
- David Moyes is not in any source artwork, so he is not in the video.
- Render speed ~0.2 s/frame on one CPU; segments can be rendered in parallel on more cores (`render.py raw <start> <end>`).
