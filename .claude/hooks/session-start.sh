#!/bin/bash
# Installs render dependencies (Python packages + ffmpeg + libEGL for skia) for Claude Code on the web sessions.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
apt_get() { apt-get install -y -q "$@" >/dev/null 2>&1 || { apt-get update -q >/dev/null && apt-get install -y -q "$@" >/dev/null; }; }
command -v ffmpeg >/dev/null || apt_get ffmpeg
# skia-python (vector renderer for the episode) needs libEGL at import time
ldconfig -p | grep -q libEGL.so.1 || apt_get libegl1
python3 -c "import cv2, numpy, scipy, PIL, soundfile, skia" 2>/dev/null || pip install -q -r requirements.txt
mkdir -p out
