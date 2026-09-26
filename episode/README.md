# South Manchester — episode assets

South Park-style spoof episode. Everything here is built offline with Python + OpenCV.

## Characters (cut-outs)
`characters/<name>/` holds every drawing from that character's model sheet as a trimmed, transparent PNG
(soft anti-aliased edges, no grey fringe, labels and panel lines removed):

| Folder | What | Count per character |
|---|---|---|
| `turnaround/` | full body: `front`, `three_quarter_front`, `side_left`, `back`, `three_quarter_back`, `side_right` (Cartman also has `three_quarter_right`) | 6-7 |
| `head/` | head close-ups: `front`, `side` | 2 |
| `mouths/` | lip-sync heads: `a_ah`, `e_eh`, `i_ee`, `o_oh`, `u_oo`, `m_closed`, `l_tongue`, `f_v`, `th_teeth`, `w_rounded` | 10 |
| `expressions/` | `neutral`, `happy`, `angry`, `sad`, `surprised`, `confused`, `smug`, `serious`, `laughing`, `disgusted`, `shouting`, `determined` (Kyle has no `smug`) | 11-12 |
| `gestures/` | `arms_down`, `pointing_left`, `pointing_right`, `both_hands_out`, `one_hand_up`, `both_hands_up`, `shrug`, `fist_angry`, `open_palm`, `talking_1..3` | 12 |
| `poses/` | `standing`, `walk_cycle_1..3`, `running`, `sitting_front`, `sitting_side`, `lean_forward_talk`, `lean_back`, `crossed_arms`, `hands_on_hips` | 11 |
| `parts/` | separate assets: hat / hat top / hood / hair, `eyes`, `brows_normal/angry/sad`, `hand_1..6`, `mouth_1..7` | 16-19 |

`characters/<name>/index.json` lists every sprite with its source rectangle on the sheet, its size, a `feet`
anchor (bottom centre of the lowest solid rows, where the character stands) and its `center`.

The ground shadow under the feet is part of each full-body drawing (in this style it doubles as the shoes).
Mouth-shape and expression drawings are busts cropped by their sheet cells, as on the sheets.

### Rebuilding
```bash
python3 tools/cut_characters.py            # all five (about 40 s per sheet), or: ... cartman kyle
python3 tools/sprite_review.py cartman green 1.5   # out/review_cartman.png: every sprite on flat green
```
`sheets/layout.json` holds the panel layout of each sheet (header rows, panel split, label lists, Cartman's
label-strip clip rows, and one point per separate part). The cutter is deterministic.

### Known source quirks (in the sheets themselves, reproduced faithfully)
- Kenny's sheet has washed-out patches on some drawings (e.g. `mouths/a_ah`, `mouths/u_oo`, `gestures/pointing_left`).
- Butters' `parts/hand_3` has a faded second hand fused to it.
- `sheets/master.png` (the combined sheet) is kept for reference only; its panels mix characters up, so the
  individual sheets are the source.

## Audio
`audio/clip01.mp3` … `clip08.mp3`: the voice clips for the Cartman-in-his-room scene, numbered in the order
they were supplied.

## HD redraws
`python3 tools/hd_sprites.py <name> [face_px]` redraws every sprite of a character as clean flat-colour art
(palette-snapped, smooth anti-aliased edges, thin lines re-inked) at a per-panel scale so faces come out about
`face_px` (default 800) wide → `characters_hd/<name>/`, with its own `index.json` (anchors scaled, `scale` per sprite).
Scenes render from these.

## Scenes
`backgrounds/cartman_room.png` (3840x2160) is painted by `tools/draw_room.py`.

`scenes/cartman_room.json` lists the voice clips in order and the shots for each (`wide` / `medium` / `close`,
full-body `pose`/`poses` or a bust `face`). Render it with
```bash
python3 tools/render_scene.py episode/scenes/cartman_room.json            # -> out/cartman_room.mp4 (1080p24 + audio)
python3 tools/render_scene.py episode/scenes/cartman_room.json still 12.5 # -> out/cartman_room_12.5.jpg
```
Lip sync is automatic: each drawing's own mouth is painted out and one of the ten sheet mouth shapes is pasted
in, picked from the voice (loudness, brightness, hiss) and held two frames at a time. Cartman blinks every few seconds
and bobs slightly on loud syllables. Cartman's gesture drawings are cut off at the belly on his sheet, so they are
only used in waist-up shots; wide shots use his full-body turnaround and pose drawings.
