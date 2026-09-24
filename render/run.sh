#!/bin/bash
# Renders the full video in resumable segments (in parallel, one per CPU core), then muxes the song.
# Usage: bash render/run.sh   (from anywhere). Output: out/pass_mic.mp4
#   JOBS=2 bash render/run.sh   limit parallel renders (default: number of cores)
# After changing render.py delete out/*.done so segments are re-rendered.
set -e
cd "$(dirname "$0")/.."
N=${N:-5414}; SEG=${SEG:-350}; JOBS=${JOBS:-$(nproc)}
mkdir -p out
seg() {
  f=$1; i=$2; e=$((f+SEG)); [ $e -gt $N ] && e=$N
  name=$(printf "out/seg%02d" $i)
  [ -f $name.done ] && return 0
  python3 render/render.py raw $f $e | ffmpeg -y -v error -f rawvideo -pix_fmt bgr24 -s 1280x720 -r 24 -i - \
    -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset veryfast -crf 19 -pix_fmt yuv420p $name.mp4 && touch $name.done
  echo "$name done $(date +%T)"
}
export -f seg; export N SEG
NSEG=$(( (N + SEG - 1) / SEG ))
for ((i=0; i<NSEG; i++)); do echo "$((i*SEG)) $i"; done | xargs -P "$JOBS" -n 2 bash -c 'seg "$0" "$1"'
[ $(ls out/seg*.done 2>/dev/null | wc -l) -eq $NSEG ] || { echo "some segments failed"; exit 1; }
ls out/seg*.mp4 | sort | sed "s#out/##; s/.*/file '&'/" > out/list.txt
ffmpeg -y -v error -f concat -safe 0 -i out/list.txt -i source/Gary__Pass_The_Microphone__.m4a -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/pass_mic.mp4
echo "Wrote out/pass_mic.mp4"
