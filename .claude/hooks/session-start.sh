#!/bin/bash
# Installs render dependencies (Python packages + ffmpeg) for Claude Code on the web sessions.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
python3 -c "import cv2, numpy, scipy, PIL" 2>/dev/null || pip install -q -r requirements.txt
if ! command -v ffmpeg >/dev/null; then
  apt-get install -y -q ffmpeg >/dev/null 2>&1 || { apt-get update -q >/dev/null && apt-get install -y -q ffmpeg >/dev/null; }
fi
mkdir -p out
