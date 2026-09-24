#!/bin/bash
# Renders the full video in 8 resumable segments, then muxes the song.
# Usage: bash render/run.sh   (from the repo root). Output: out/pass_mic.mp4
set -e
cd "$(dirname "$0")/.."
N=5414; SEG=700; i=0
mkdir -p out
for ((f=0; f<N; f+=SEG)); do
  e=$((f+SEG)); [ $e -gt $N ] && e=$N
  name=$(printf "out/seg%02d" $i)
  if [ ! -f $name.done ]; then
    python3 render/render.py raw $f $e | ffmpeg -y -v error -f rawvideo -pix_fmt bgr24 -s 1280x720 -r 24 -i - \
      -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset veryfast -crf 19 -pix_fmt yuv420p $name.mp4 && touch $name.done
    echo "$name done $(date +%T)"
  fi
  i=$((i+1))
done
ls out/seg*.mp4 | sort | sed "s#out/##; s/.*/file '&'/" > out/list.txt
ffmpeg -y -v error -f concat -safe 0 -i out/list.txt -i source/Gary__Pass_The_Microphone__.m4a -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/pass_mic.mp4
echo "Wrote out/pass_mic.mp4"
