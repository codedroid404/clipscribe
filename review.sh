#!/usr/bin/env bash
#
# review.sh — one-command review of the current ClipScribe iteration.
#
# Runs lint + unit tests, transcribes a real clip from media/, prints the
# transcript to the TERMINAL (local review only), and confirms no media or
# transcripts leak into Git.
#
# Usage:
#   CLIP=media/your-clip.mp4 ./review.sh                         # local review
#   CLIP=media/your-clip.mp4 ./review.sh docs/validation/out.txt # also write a log
#   MODEL=small CLIP=... ./review.sh                             # override the model
#   MANUAL_REVIEW=CONFIRMED CLIP=... ./review.sh                 # record a human attestation
#
# CLIP is REQUIRED and never defaulted — private filenames are not hardcoded.
# The optional log is a CURATED, privacy-safe subset: it never contains the
# transcript body, the source media filename, or absolute/user paths.
#
set -euo pipefail
cd "$(dirname "$0")"

LOG="${1:-}"
MODEL="${MODEL:-base}"
MILESTONE="${MILESTONE:-M0/M1}"
# Human attestation only — the script cannot verify a person listened to the clip.
MANUAL_REVIEW="${MANUAL_REVIEW:-NOT RECORDED}"
PY=".venv/bin/python"

step() { printf '\n\033[1;36m=== %s ===\033[0m\n' "$1"; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$1"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$1"; }
err()  { printf '\033[1;31m✗ %s\033[0m\n' "$1" >&2; }
die()  { err "$1"; exit 1; }

# --- sanity --------------------------------------------------------------
[ -x "$PY" ] || die "no .venv — run: python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"

# --- clip is required and never defaulted (no hardcoded private filenames) -
CLIP="${CLIP:-}"
[ -n "$CLIP" ] && [ -f "$CLIP" ] || die "set CLIP=path/to/clip.<ext> — no default; private filenames are not hardcoded"

RC=0

# --- 1. lint -------------------------------------------------------------
step "Lint (ruff)"
if .venv/bin/ruff check .; then RUFF=PASS; ok "ruff clean"; else RUFF=FAIL; RC=1; err "ruff failed"; fi

# --- 2. unit tests -------------------------------------------------------
step "Unit tests (pytest)"
if .venv/bin/pytest -q; then PYTEST=PASS; ok "tests passed"; else PYTEST=FAIL; RC=1; err "tests failed"; fi

# --- 3. transcribe a real clip -------------------------------------------
step "Transcribe [model=$MODEL]"
set +e
CAP="$(.venv/bin/clipscribe "$CLIP" --model "$MODEL" 2>&1)"
TRC=$?
set -e
printf '%s\n' "$CAP"
if [ "$TRC" -eq 0 ]; then TRANSCRIBE=SUCCESS; ok "transcription succeeded"
else TRANSCRIBE=FAILURE; RC=1; err "transcription failed"; fi

# parse summary metrics from the captured CLI output (values only; no paths)
m() { printf '%s\n' "$CAP" | sed -n "s/^  $1 *: *//p" | head -n1; }
LANGUAGE="$(m language)"; DURATION="$(m duration)"; PROCESSING="$(m processing)"
RTF="$(m 'real-time x')"; SEGMENTS="$(m segments)"

STEM="$(basename "${CLIP%.*}")"
OUTPUTS_OK=yes
for ext in txt json srt vtt; do
  [ -f "transcripts/$STEM.$ext" ] || { OUTPUTS_OK=no; RC=1; }
done

# --- 4. show transcript on TERMINAL ONLY (never written to the log) ------
step "Transcript (local terminal review only — redacted from any saved log)"
if [ -f "transcripts/$STEM.txt" ]; then cat "transcripts/$STEM.txt"; else warn "no transcript file"; fi

# --- 5. app boot check (streamlit headless) ------------------------------
step "App boot check (streamlit headless)"
if [ -f app.py ] && "$PY" -c 'import streamlit' >/dev/null 2>&1; then
  APP_PORT="${APP_PORT:-8599}"
  APP_LOG="$(mktemp)"
  .venv/bin/streamlit run app.py --server.headless true --server.port "$APP_PORT" \
      --browser.gatherUsageStats false >"$APP_LOG" 2>&1 &
  APP_PID=$!
  trap 'kill "$APP_PID" 2>/dev/null || true' EXIT
  APP=FAIL
  for _ in $(seq 1 20); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$APP_PORT/_stcore/health" 2>/dev/null || true)"
    if [ "$code" = "200" ]; then APP=PASS; break; fi
    sleep 1
  done
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
  trap - EXIT
  if [ "$APP" = PASS ]; then ok "app boots and serves (health 200)"
  else RC=1; err "app failed to boot"; tail -5 "$APP_LOG"; fi
  rm -f "$APP_LOG"
else
  APP=SKIPPED; warn "app.py or streamlit not present — app boot check skipped"
fi

# --- 6. privacy check ----------------------------------------------------
step "Privacy check (git ignores media/ & transcripts/)"
if git rev-parse --git-dir >/dev/null 2>&1; then
  LEAKS="$(git add -A -n 2>/dev/null | grep -iE 'media/|transcripts/|references/|\.venv/' || true)"
  if [ -n "$LEAKS" ]; then printf '%s\n' "$LEAKS"; PRIVACY=FAIL; RC=1; err "sensitive paths would be tracked"
  else PRIVACY=PASS; ok "no media/transcripts/.venv tracked by Git"; fi
else
  PRIVACY=SKIPPED; warn "not a git repo — privacy check skipped"
fi

# --- 7. optional privacy-safe log ----------------------------------------
if [ -n "$LOG" ]; then
  mkdir -p "$(dirname "$LOG")"
  RESULT=$([ "$RC" -eq 0 ] && echo "ALL CHECKS PASSED" || echo "ONE OR MORE CHECKS FAILED")
  {
    echo "========================================================================"
    echo "ClipScribe — ${MILESTONE} Automated Validation Log"
    echo "Generated (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "Model: ${MODEL} | Device: cpu/int8"
    echo "========================================================================"
    echo
    echo "[1/5] Lint (ruff)             : ${RUFF}"
    echo "[2/5] Unit tests (pytest)     : ${PYTEST}"
    echo "[3/5] Transcription (faster-whisper)"
    echo "        decode + ASR          : ${TRANSCRIBE}"
    echo "        detected language     : ${LANGUAGE:-n/a}"
    echo "        media duration        : ${DURATION:-n/a}"
    echo "        processing time       : ${PROCESSING:-n/a}"
    echo "        real-time factor      : ${RTF:-n/a}"
    echo "        segment count         : ${SEGMENTS:-n/a}"
    echo "        outputs txt/json/srt/vtt : ${OUTPUTS_OK}"
    echo "        transcript            : [TRANSCRIPT CONTENT REDACTED]"
    echo "[4/5] App boot (streamlit)    : ${APP}"
    echo "[5/5] Privacy check           : ${PRIVACY}"
    echo
    echo "Manual faithfulness review    : ${MANUAL_REVIEW}  (human attestation, not an automated check)"
    echo "Source media filename         : [MEDIA FILENAME REDACTED]"
    echo "Source / cache paths          : [LOCAL PATH REDACTED]"
    echo
    echo "Result: ${RESULT}"
    echo "========================================================================"
  } > "$LOG"
  step "Saved privacy-safe validation log"
  ok "$LOG"
fi

step "Review complete"
[ "$RC" -eq 0 ] && ok "all automated checks passed" || err "one or more checks failed"
printf '\nManual step: play the clip in media/ and read the transcript above —\n'
printf 'judge faithfulness with your own ears (not saved to any public log).\n'
exit "$RC"
