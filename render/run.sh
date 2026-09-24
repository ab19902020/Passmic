#!/bin/bash
# Renders the full video in resumable segments (in parallel, one per CPU core), then muxes the song.
# Usage (from anywhere):
#   bash render/run.sh                     1080p 24 fps  -> out/pass_mic.mp4   (renders 720p, upscales)
#   QUALITY=4k60 bash render/run.sh        native 3840x2160 at 60 fps -> out/pass_mic_4k60.mp4
#   QUALITY=1080p60 bash render/run.sh     native 1920x1080 at 60 fps -> out/pass_mic_1080p60.mp4
#   JOBS=2 bash render/run.sh              limit parallel renders (default: number of cores; 4K uses ~2 GB RAM per job)
# Segments are resumable; after changing render.py delete the matching out/<quality>/*.done files.
set -e
cd "$(dirname "$0")/.."
QUALITY=${QUALITY:-1080p}
case "$QUALITY" in
  1080p)   SCALE=1;   FPS=24; VF="scale=1920:1080:flags=lanczos"; CRF=19; OUT=out/pass_mic.mp4 ;;
  1080p60) SCALE=1.5; FPS=60; VF="null";                          CRF=18; OUT=out/pass_mic_1080p60.mp4 ;;
  4k60)    SCALE=3;   FPS=60; VF="null";                          CRF=18; OUT=out/pass_mic_4k60.mp4 ;;
  *) echo "unknown QUALITY=$QUALITY (1080p | 1080p60 | 4k60)"; exit 1 ;;
esac
W=$(python3 -c "print(int(round(1280*$SCALE)))"); H=$(python3 -c "print(int(round(720*$SCALE)))")
N=${N:-$(python3 -c "import math; print(math.ceil(225.54*$FPS))")}
SEG=${SEG:-$(( FPS * 15 ))}; JOBS=${JOBS:-$(nproc)}
DIR=out/$QUALITY; mkdir -p $DIR
export PASSMIC_SCALE=$SCALE PASSMIC_FPS=$FPS
seg() {
  f=$1; i=$2; e=$((f+SEG)); [ $e -gt $N ] && e=$N
  name=$(printf "$DIR/seg%03d" $i)
  [ -f $name.done ] && return 0
  python3 render/render.py raw $f $e | ffmpeg -y -v error -f rawvideo -pix_fmt bgr24 -s ${W}x${H} -r $FPS -i - \
    -vf "$VF" -c:v libx264 -preset medium -crf $CRF -pix_fmt yuv420p $name.mp4 && touch $name.done
  echo "$name done $(date +%T)"
}
export -f seg; export N SEG DIR W H FPS VF CRF
NSEG=$(( (N + SEG - 1) / SEG ))
echo "Rendering $QUALITY: ${W}x${H} @ ${FPS} fps, $N frames in $NSEG segments, $JOBS parallel jobs"
for ((i=0; i<NSEG; i++)); do echo "$((i*SEG)) $i"; done | xargs -P "$JOBS" -n 2 bash -c 'seg "$0" "$1"'
[ $(ls $DIR/seg*.done 2>/dev/null | wc -l) -eq $NSEG ] || { echo "some segments failed"; exit 1; }
ls $DIR/seg*.mp4 | sort | sed "s#.*/##; s/.*/file '&'/" > $DIR/list.txt
ffmpeg -y -v error -f concat -safe 0 -i $DIR/list.txt -i source/Gary__Pass_The_Microphone__.m4a -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart $OUT
echo "Wrote $OUT"
