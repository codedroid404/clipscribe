#!/usr/bin/env bash
# ClipScribe environment setup — create a local virtualenv and install dependencies.
#
# Usage:
#   source setup.sh     # recommended: leaves the venv activated in your shell
#
# Re-running is safe: it reuses an existing .venv and upgrades in place.

# Detect whether the script was sourced (so `source setup.sh` keeps the venv active).
_clipscribe_sourced=0
(return 0 2>/dev/null) && _clipscribe_sourced=1

set -e

echo "🎙️  ClipScribe setup"

# 1. Create the virtualenv if it doesn't exist.
if [ ! -d ".venv" ]; then
  echo "→ creating .venv (Python $(python3 -V 2>&1 | cut -d' ' -f2))"
  python3 -m venv .venv
else
  echo "→ reusing existing .venv"
fi

# 2. Activate + install.
# shellcheck disable=SC1091
source .venv/bin/activate
echo "→ upgrading pip"
python -m pip install -U pip >/dev/null
echo "→ installing ClipScribe + dev tools (this can take a few minutes on first run)"
pip install -e ".[dev]"

# 3. Optional: scaffold .env for the (optional) ✨ AI-title feature.
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "→ created .env from .env.example (add ANTHROPIC_API_KEY to enable the ✨ AI title; optional)"
fi

set +e
echo ""
echo "✅ ClipScribe is ready. Start the app with:"
echo "     streamlit run app.py"
if [ "$_clipscribe_sourced" -eq 0 ]; then
  echo ""
  echo "ℹ️  You ran this directly, so the venv isn't active in your shell. Either:"
  echo "     source .venv/bin/activate     # then: streamlit run app.py"
  echo "   or next time run:  source setup.sh"
fi
