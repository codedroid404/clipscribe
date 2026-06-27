# Changelog

All notable changes to ClipScribe, organized by development milestone.

_ClipScribe MVP (M0–M6) — developed June 2026. Entries are ordered newest-first by
milestone; the MVP reached its [Definition of Done](docs/ClipScribe_Project_Plan_v2.pdf) in
that window._

## Library titling + optional AI-title teaser

- **Local auto-title** (`storage.suggest_title`): the Save panel pre-fills a title derived from
  the transcript (instant, no key) — no manual titling required.
- **✨ AI title** (optional, opt-in): a single hosted call (`anthropic` SDK) generates a concise
  title; gated behind an API key, model-selectable in the sidebar, with a session token-cost
  meter. This is the one cloud touch — a deliberate seed for the planned AI-analysis layer (see
  README Roadmap). Transcription always stays local.
- UI: Readable transcript leads; Segments and raw Timestamped views collapse below.

## M6 — Persistence (saved transcript library)

- Durable local store: SQLite (stdlib, no new dependency) at a Git-ignored
  `data/clipscribe.db`. New `src/clipscribe/storage.py` with save/list/get/delete.
- `Transcript` entity persists id/title/source/created/duration/language/model and the
  full segments (segment-level timestamps preserved for future semantic search),
  readable text, and diagnostic flags.
- App: **Save to library** control and a **Library** panel (open / delete) reusing the
  existing renderers/exporters. CLI: `clipscribe <clip> --save [--title "..."]`.
- Round-trip unit tests on a temporary DB.

## Pre-release remediation (M4/M5 hardening)

- **Privacy:** `review.sh` no longer hardcodes a personal clip — `CLIP` is required and
  never defaulted; uploaded filenames are sanitized (random temp name + validated suffix,
  never used as a path); logs record extension/size/model only, never the filename or
  transcript text; validation logs use neutral redaction placeholders.
- **Honesty:** manual-faithfulness review defaults to `NOT RECORDED` (explicit human
  attestation only via `MANUAL_REVIEW=`); removed transcript snippets and "verbatim"/"never
  invents" wording; diagnostics documented as heuristics (incl. `avg_logprob` caveat and
  repetition limits); WER reaffirmed as deferred.
- **UX/safety:** transcript text rendered safely (no Markdown/HTML injection); stale results
  cleared when the input or settings change; raw exceptions mapped to actionable messages;
  internal warning codes shown as readable labels.
- **Scope/docs:** upload cap lowered to 512 MB (config + `media.py`); added `LICENSE` (MIT);
  corrected dependency wording to "version-bounded" and the type-checking claim; added a
  test-evidence coverage table; safety helpers covered by unit tests.

## M5 — Portfolio polish

- README hook, architecture diagram, app screenshot, features, privacy statement.
- App: **Readable** transcript tab (clean flowing prose), built-in background-tint
  theme switcher, author footer.
- This changelog.

## M4 — Trust and evaluation

- `scripts/evaluate.py` evaluation harness (metrics-only, no transcript/filename leakage).
- `docs/evaluation/EVALUATION.md` — reproducible benchmark (runtime, RTF, robustness),
  test environment, and honest known limitations.
- Unit tests for the harness's deterministic helpers.

## M3 — Streamlit MVP

- `app.py` browser UI: upload, settings (model / language / VAD), progress, transcript
  review with uncertainty flags, and TXT/JSON/SRT/VTT downloads.
- Visual redesign: teal theme, self-hosted Inter font, branded logo, card layout,
  Reading/Segments tabs, badges + Material icons.
- Color-coded console logging (technical events/timings only; never transcript text).
- `.streamlit/config.toml`: 1 GB upload limit, telemetry disabled.
- `service.run_pipeline` (no-disk) for in-memory UI downloads.

## M2 — Core service layer

- Split into typed modules: `models`, `media`, `transcriber`, `diagnostics`, `exporters`,
  `tempfiles`, `service`; `cli.py` becomes a thin wrapper.
- Added **SRT** and **VTT** export.
- Diagnostics: low-confidence, no-speech, repetition/looping flags.
- Media validation + audio-stream probing with actionable errors.
- Unit + integration test suite.

## M1 — CLI transcription spike

- `clipscribe` CLI: decode a real iPhone clip locally with faster-whisper, emit a
  timestamped TXT + JSON transcript.
- Pending WER comparison path (`--reference`) via `jiwer`.

## M0 — Repository foundation

- `src/clipscribe` package layout, pinned dependencies, Ruff + pytest config.
- `.gitignore` (keeps personal media and transcripts out of Git).
- `review.sh` one-command review (lint, tests, transcription, app boot, privacy).
