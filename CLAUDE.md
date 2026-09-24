# Pass Mic — working notes for Claude

See `README.md` for the project overview, layout and open issues.

- Everything runs from the repo root; paths in the scripts are resolved relative to it.
- Dependencies (numpy, scipy, pillow, opencv-contrib-python, ffmpeg) are installed by `.claude/hooks/session-start.sh` in web sessions.
- Fonts are vendored in `fonts/` (Poppins, OFL licence) — don't point at system font paths.
- Iterate with single frames: `python3 render/render.py test <t_seconds> ...` → `out/f_<t>.jpg`, then look at the JPGs.
- Short clip check: `python3 render/render.py raw <f0> <f1> | ffmpeg -f rawvideo -pix_fmt bgr24 -s 1280x720 -r 24 -i - out/clip.mp4`
- Full render: `bash render/run.sh` → `out/pass_mic.mp4`. Segments are resumable via `out/segNN.done`; delete those after changing `render.py`.
- `out/` and `*.mp4` are git-ignored — rendered output is never committed.
