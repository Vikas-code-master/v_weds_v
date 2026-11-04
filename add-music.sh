#!/bin/bash
# Add background music to the invitation video.
#
#   ./add-music.sh song.mp3                -> vikas-vindhya-invitation-music.mp4
#   ./add-music.sh song.mp3 input.mp4 out.mp4
#
# The song loops if it is shorter than the video, fades in over 1.5s and
# fades out over the last 3s. The video itself is copied, not re-encoded.
set -euo pipefail
cd "$(dirname "$0")"

SONG="${1:?usage: ./add-music.sh song.mp3 [input.mp4] [output.mp4]}"
IN="${2:-vikas-vindhya-invitation.mp4}"
OUT="${3:-vikas-vindhya-invitation-music.mp4}"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
FADE_START=$(awk -v d="$DUR" 'BEGIN { printf "%.2f", d - 3 }')

ffmpeg -v error -y \
  -i "$IN" -stream_loop -1 -i "$SONG" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k \
  -af "afade=t=in:d=1.5,afade=t=out:st=${FADE_START}:d=3" \
  -t "$DUR" -movflags +faststart "$OUT"

echo "Saved $OUT"
