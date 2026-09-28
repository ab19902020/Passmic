# Episode 1 — "International Break Emergency"

Mark Goldbridge, Gary Neville and Roy Keane in the studio. The whole episode is
built from the files in this folder by the tools in `tools/ep/`; nothing is
hand-animated.

```
python3 tools/ep/render.py 4k          # -> out/ep01/ep01_4k.mp4   (3840x2160, 24 fps)
python3 tools/ep/render.py 1080p       # -> out/ep01/ep01_1080p.mp4
python3 tools/ep/render.py still 9 121 # -> out/ep01/still_<t>.jpg  single 4K frames
python3 tools/ep/render.py sheet 0 330 2.5 out/ep01/sheet.jpg   # contact sheet of the whole episode
python3 tools/ep/render.py timings     # every line's start, length and whether it has a recording
```

Rendering runs as many workers as memory allows (~4.5 GB per 4K worker; `JOBS=n`
to set it). Finished segments are kept, so if a render is interrupted just run it
again; delete `out/ep01/seg_4k/` after changing anything in the episode.

## Replacing or adding a voice line

Every line is recorded. To replace one, drop the new file into
`series/ep01/audio/` named by its line ID (`RK_05.wav`, `GN_12.mp3`, …;
`.wav .mp3 .m4a .aac .flac .ogg` all work) and re-align it:
`python3 tools/ep/align.py RK_05`. The line's slot takes the recording's real
length, everything after it moves along, and the mouth follows the words. A
brand-new file (an ID with no alignment yet) is aligned automatically on the
next render.

A take that holds several lines in a row is cut into one file per line with
`tools/ep/split_voice.py <clip> RK_09 RK_10 ...` (how Roy's four clips and
Gary's last three were cut; `audio/manifest.json` records the source and times).

## Where things are

| | |
|---|---|
| `script.py` | Every line (`MG_nn` Mark, `GN_nn` Gary, `RK_nn` Roy — each numbered on its own), `DELIVERY` (the same lines formatted for the voice generator: emotion tag, pauses, CAPS emphasis) and `ORDER`, the conversation with its stage beats (`@gary_enters`, `@roy_enters`, `@board`, …). |
| `voice_script.txt` | `DELIVERY` as a paste-ready list, one line per file ID. |
| `episode.py` | The staging: camera set-ups, per-line shot / pose / close-up face and word-timed cuts (`STAGE`), reaction shots, Gary's and Roy's walks, the recruitment-board insert and the end card. |
| `audio/` | The voice lines cut and labelled from the zips (`manifest.json` says which source file and times each came from), and `alignment.json` (word and phone timings). |
| `raw/` | The original voice clips as supplied. Gary's last three clips were cut at word boundaries into GN_14–18, GN_19–24 and GN_25–29; Roy's four into RK_01–08, RK_09–17, RK_18–24 and RK_25–26. |
| `sheets/`, `production/`, `backgrounds/src/` | The supplied character sheets, production sheets and studio backgrounds. |
| `x4/` | The sheets and studio backgrounds AI-upscaled 4x (Real-ESRGAN anime model) — `tools/ep/upscale.py`. |
| `sheets/layout.json` | Where each drawing sits on the sheets; `tools/ep/cut_sheet.py` cuts them out into `characters/<name>/<panel>/<drawing>.png` with an `index.json`. |
| `characters_x16/` | A second 4x pass on the drawings seen large (expressions, heads, busts, standing and walking bodies) — `tools/ep/upscale_parts.py`. The renderer prefers these. |
| `characters/roy/` | Roy, cut from his own sheet (`sheets/roy.png`) by `tools/ep/cut_roy.py` — AI matting (rembg), since his black clothes sit on dark panels: 10 expressions, the head detail, 4 poses, the turnaround and his 11 mouth shapes. His sheet has no walk, so `tools/ep/make_roy.py` puts his head on Gary's (black-clad) walk cycle. |
| `characters/<name>/rig.json` | Hand corrections for the face rig where automatic mouth finding misses (`mouth: [cx, cy, w(, h)]` as fractions of the drawing). |
| `backgrounds/<name>.json` | Per studio view: the desk / mic / props drawn in front of the characters (shapes, edge-snapped into a matte by `tools/ep/bgmatte.py`), seats and standing spots. |

## How the characters move

* **Lip sync** — each recorded line is force-aligned to its text (pocketsphinx),
  the phones map to the sheet's mouth shapes (rest, a, e, i, o, u, smile, frown,
  wide shout; held on twos), and the mouth is swapped on whichever drawing is on
  screen: the drawn mouth is filled with the surrounding skin and the new mouth
  pasted and recoloured to that drawing's skin, never past the jaw line. Roy's
  sheet has 11 mouth shapes (A, E, I, O, U, C/D/G, F/V, L, M/B/P, R, TH), each a
  patch of lips, moustache and beard: the patch goes over his mouth, tone-matched
  and feathered into the beard.
* **Delivery** — the performance follows the tags in `DELIVERY`: each line's
  close-up face and pose come from its tag (frustrated, dry, deadpan, smug, …)
  and stay mostly serious; CAPS words get a small nod, a `[sigh]` closes the
  eyes, and the written pauses get a blink. No line is played as a shout.
* **Close-ups** use the expression drawings (x16) over the medium body drawing
  (the calm arms-down one, so no hands poke out from behind the bust), with only
  the bust's cut-off edges faded.
* **Pacing** — lines follow each other tightly; punchlines get a beat of silence
  first (`BEAT` in `episode.py`) and land on a held reaction shot (`REACT`).
* **Blinks**, a small talking bob, walk cycles at 8 drawings a second with
  footsteps, the desk kept in front of everyone, and a locked camera per shot.
