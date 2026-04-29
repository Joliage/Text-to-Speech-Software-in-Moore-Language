#!/usr/bin/env bash
# prepare_and_run_gui.sh — launch the Mooré TTS GUI
set -euo pipefail
cd "$(dirname "$0")"

ARPABET_DB="./Arpabet Transcription"
FILTERED_LEX=lexicon_filtered_all.json

SENTENCE_ARG="${1:-}"
SENTENCE_ENV="${SENTENCE:-}"
SENTENCE="${SENTENCE_ARG:-$SENTENCE_ENV}"

echo "=== prepare_and_run_gui.sh ==="

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  exit 1
fi

if [ ! -d "$ARPABET_DB" ]; then
  echo "ERROR: Folder not found: $ARPABET_DB"
  echo "Make sure your ARPABET-renamed WAVs are in that folder."
  exit 1
fi

if [ ! -f "$FILTERED_LEX" ]; then
  echo "ERROR: Lexicon not found: $FILTERED_LEX"
  exit 1
fi

wav_count=$(find "$ARPABET_DB" -iname "*.wav" | wc -l)
echo "DB     : $ARPABET_DB  ($wav_count WAV files)"
echo "Lexicon: $FILTERED_LEX"

LAUNCH_CMD=(python3 tonal_tts_full.py --db "$ARPABET_DB" --lexicon "$FILTERED_LEX" --gui)
if [ -n "$SENTENCE" ]; then
  LAUNCH_CMD+=(--sentence "$SENTENCE")
fi

echo "Running: ${LAUNCH_CMD[*]}"
echo ""
"${LAUNCH_CMD[@]}"
