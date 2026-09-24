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
- `EDL` (edit decision list): one shot per lyric line, cut on the line and framed on whoever the line is about. Gary is the default, Jamie's lines go on Carra, Roy's lines on Keane, and the comedy breakdown cuts to each speaker. Cuts get a 4-frame crossfade, scene changes a 0.6 s dissolve. The camera frames each pundit from his smoothed position and a fixed head height (`cam_anchor`), so it never chases the dance bounce.
- `SECTIONS` follow the song's structure: intro, verse, chorus, verse 2, chorus 2 (`big`), verse 3 (synthwave, "Anger creates engagement"), comedy breakdown, bridge (pitch, "You and Keane at Old Trafford"), a blackout drop, the final chorus, and the outro. Choruses are the hot sections, with bigger moves and more light. Verses move less.
- `TOSSES`: the mic follows the story. Gary passes it to Carra for Jamie's lines, Carra to Keane for Roy's, Keane back to Gary for the England days, then the outro handoffs. Each pass gets its own two-shot.
- `GARY`: Gary spotlight + the others lean in. `CHAMP`: champagne pop on each "champagne socialist" line.
- Drawn poses are held for 2 beats (choruses) or 4 beats (verses) and dissolve into each other over 3 frames, so the cut-outs don't flicker between drawings.
- Nothing is written on screen: no lyrics, captions, name cards or titles. The only text is what's painted in the original artwork.
- Pundits blink (`BLINKS`), and when one pundit sings or speaks a solo line the other two tilt their heads towards him (`listen_dir`). In single close-ups the others are dimmed slightly.
- An awkward Inbetweeners-style trio dance (`inbet_*` moves) plays in the reveal (beats 16-32), with a callback at beats 368-376.
- Polish: glossy floor reflections (studio/grid), an LED board of moving light (no text) on the pitch rail, and a sparkle trail on mic tosses.

## Checking changes
`python3 tools/contact_sheet.py 0.5 225 3 out/sheet.jpg` renders a labelled thumbnail every 3 s (time, beat, section, shot) across all cores. It's the fastest way to review the whole video.

## Open issues / next steps
- Fixed: Gary's "weird shadow". `build_assets.py` now paints a short skin-toned neck and collar under each head (it used to paint a dark shirt-coloured block), extends the head over the head/body seam, and trims hair slivers. Background scraps are erased via `masks/clean.json`.
- Lip sync: `data/mouth_curve.npz` is built by `tools/build_mouth_curve.py` from the demucs-isolated vocal stem (real syllables, mouth shuts between them) plus the lyric track for who sings: the mic holder sings verses, everyone sings choruses, and quoted/spoken lines (intro, "here's the thing", "Standards! Hunger! Pride!", the comedy breakdown, outro) go to the right pundit. The others keep their mouths shut. Carra/Gary are drawn mid-shout, so `mouth_shape()` squeezes the drawn mouth shut below `MOUTH_REST` and opens the jaw above it. Mouth anchors are in `assets/mouths.json`.
- Background managers no longer lip sync (disabled on purpose). The conga line and Sir Alex never did.
- Gary's pointing fist (pose A) had a fingernail that read as a talking mouth; it is painted out via `retouch` in `masks/clean.json`.
- `nev2` (Gary, pose B) loses the right edge of "UNITED!" on the hoodie. The source mask cuts it off.
- David Moyes is not in any source artwork, so he is not in the video.
- Render speed ~0.27 s/frame per core; `run.sh` renders 350-frame segments in parallel (`JOBS=n` to limit). Delete `out/*.done` after changing `render.py`.
