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
