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

Rendering uses one worker per CPU (`JOBS=n` to limit — each 4K worker needs
about 3 GB of memory).

## Adding Roy's voice (and GN_09)

Drop the recordings into `series/ep01/audio/` named by line ID — `RK_01.wav`,
`RK_02.mp3`, … (`.wav .mp3 .m4a .aac .flac .ogg` all work) — and render again.
That's all: the renderer aligns any new recording to its line of the script
(`tools/ep/align.py`, saved in `audio/alignment.json`), the line's slot takes the
recording's real length, everything after it moves along, and his mouth follows
the words.

Until then, every line without a recording keeps a silent slot sized from its
syllable count, and the character mouths the words in time with it. That covers
all 26 of Roy's lines and **GN_09** ("Mark, you don't fix a football club with a
shopping list.") — there was no recording of GN_09 in `gaz.zip`.

To re-align a line after replacing its file: `python3 tools/ep/align.py GN_05`.

## Where things are

| | |
|---|---|
| `script.py` | Every line (`MG_nn` Mark, `GN_nn` Gary, `RK_nn` Roy — each numbered on its own) and `ORDER`, the conversation with its stage beats (`@gary_enters`, `@roy_enters`, `@board`, …). |
| `episode.py` | The staging: camera set-ups, per-line shot / pose / close-up face and word-timed cuts (`STAGE`), reaction shots, Gary's and Roy's walks, the recruitment-board insert and the end card. |
| `audio/` | The voice lines cut and labelled from the zips (`manifest.json` says which source file and times each came from), and `alignment.json` (word and phone timings). |
| `raw/` | The original voice clips as supplied. Gary's last three clips each held several lines; they were cut at word boundaries into GN_14–18, GN_19–24 and GN_25–29. |
| `sheets/`, `production/`, `backgrounds/src/` | The supplied character sheets, production sheets and studio backgrounds. |
| `x4/` | The sheets and studio backgrounds AI-upscaled 4x (Real-ESRGAN anime model) — `tools/ep/upscale.py`. |
| `sheets/layout.json` | Where each drawing sits on the sheets; `tools/ep/cut_sheet.py` cuts them out into `characters/<name>/<panel>/<drawing>.png` with an `index.json`. |
| `characters_x16/` | A second 4x pass on the drawings seen large (expressions, heads, busts, standing and walking bodies) — `tools/ep/upscale_parts.py`. The renderer prefers these. |
| `characters/roy/` | Roy stand-in: his head from production sheet C (`src/`) on Gary's black-clad body drawings, plus a standing arms-folded pose and a high-res close-up — `tools/ep/make_roy.py`. |
| `characters/<name>/rig.json` | Hand corrections for the face rig where automatic mouth finding misses (`mouth: [cx, cy, w(, h)]` as fractions of the drawing). |
| `backgrounds/<name>.json` | Per studio view: the desk / mic / props drawn in front of the characters (shapes, edge-snapped into a matte by `tools/ep/bgmatte.py`), seats and standing spots. |

## How the characters move

* **Lip sync** — each recorded line is force-aligned to its text (pocketsphinx),
  the phones map to the sheet's mouth shapes (rest, a, e, i, o, u, smile, frown,
  wide shout; held on twos), and the mouth is swapped on whichever drawing is on
  screen: the drawn mouth is filled with the surrounding skin and the new mouth
  pasted and recoloured to that drawing's skin. Roy has no mouth sheet, so his
  openings are drawn over his own lips, leaving his beard and moustache.
* **Close-ups** use the expression drawings (x16) blended onto the medium body
  drawing, so the bust's cut-off chest never shows.
* **Blinks**, a small talking bob, walk cycles at 8 drawings a second with
  footsteps, the desk kept in front of everyone, and a locked camera per shot.
