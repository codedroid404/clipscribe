# ClipScribe — M3 Validation Summary

## Scope

**M3 — Streamlit MVP.** Adds the browser UI that completes the project's Definition
of Done: upload a clip, transcribe locally, review the raw timestamped transcript
with uncertainty warnings, and download all four formats — no command line required.

- `app.py` — presentation-only Streamlit app (no pipeline logic): upload, sidebar
  settings (model size, language auto/override, VAD), Transcribe action with progress,
  summary metrics, flagged transcript display, and TXT/JSON/SRT/VTT download buttons.
- `service.py` — added `run_pipeline()` (validate → ASR → diagnose, **no disk export**)
  reused by the app for in-memory downloads; `transcribe_file()` (CLI) calls it.
- `review.sh` — extended with a headless **app boot check** and a four-format output check.

Out of scope for M3: formal WER benchmarking (still deferred — no gold reference yet)
and portfolio polish (M5).

### Usability refinements

- **Visual redesign** — calm teal + slate theme (`.streamlit/config.toml`), self-hosted
  Inter font, branded logo/icon, rounded white "cards" on a soft tinted canvas, and a
  results area split into **Reading view** + sortable **Segments** tabs, with quality
  signals shown as colored badges and Material icons.
- **Background-tint theme switcher** — an Appearance control in the sidebar to recolor
  the canvas live (Teal-gray / Mint / Sage / Cool mist), persisted per session.
- Model dropdown shows friendly labels with the speed/accuracy/download trade-off
  (e.g. "Small — slower, more accurate · recommended").
- Color-coded console logging of technical events and timings (NFR-07) — upload
  received, transcription done, quality flags, errors — **never** the transcript text.
- `.streamlit/config.toml` raises the default 200 MB upload cap to 1 GB (so the
  406 MB 3-minute clip uploads) and disables Streamlit usage telemetry.

## Validation status

**PASSED.** All automated checks succeed, including a headless boot of the app.
Reproducible evidence is in [`m3_review.txt`](m3_review.txt), regenerated with:

```bash
MILESTONE=M3 ./review.sh docs/validation/m3_review.txt
```

## Checks completed

| Check | Tool | Result |
|---|---|---|
| Lint | `ruff` | Passed |
| Unit + integration tests | `pytest` | Passed — 23 tests |
| Transcription (real clip) | `service` | Succeeded |
| Four-format export | `exporters` | TXT/JSON/SRT/VTT generated |
| **App boot (headless)** | `streamlit` | **Served HTTP 200 on `/_stcore/health`** |
| Privacy (Git tracking) | `git add -n` | No media/transcripts tracked |

Observed transcription run (base model, CPU/int8) as recorded in the log:

- detected language: `en` (probability ≈ 1.00)
- media duration: ≈ 49.2 s
- processing time: ≈ 3.9 s
- real-time factor: ≈ 0.08
- segments: 16

These are **observed values from one base-model run**, not guaranteed figures.

## Accuracy evaluation

- The raw `faster-whisper` output remains the unaltered source record; the UI marks
  low-confidence/no-speech/repeated segments with ⚠️ but does not rewrite text.
- M3 changed only presentation and orchestration, not the transcription itself.
- **Formal WER remains deferred** — no human-validated gold reference transcript exists
  yet. The `--reference` WER path is implemented and unit-tested, ready to activate.

No accuracy metric is asserted here that was not actually measured.

## Privacy verification

- The app processes uploaded media in a randomized temporary workspace and deletes it
  on success or failure (`tempfiles.temporary_workspace`); downloads are served
  in-memory, so the UI writes no transcript to disk.
- `media/`, `transcripts/`, and `references/` remain gitignored.
- Console logging records technical events/timings only — never transcript text
  (NFR-07); Streamlit usage telemetry is disabled in `.streamlit/config.toml`.
- [`m3_review.txt`](m3_review.txt) is a curated, privacy-safe artifact: transcript body
  redacted; source filename and absolute/user paths excluded. It was inspected for keys,
  tokens, environment-variable values, usernames, media filenames, transcript text, and
  model-cache paths — none present.

## Outcome

M3 is complete and validated. ClipScribe meets its **Definition of Done**: a user can
run `streamlit run app.py`, upload a real iPhone `.MOV`/`.MP4`, transcribe locally with
no API key, review a raw timestamped transcript with uncertainty warnings, and download
TXT/JSON/SRT/VTT — with temporary media cleaned up and tests passing.

The headless boot check confirms the app starts and serves; the full interactive
upload→download walkthrough remains a manual step (no browser in the automated harness).

## Next milestone

**M4 — Trust and evaluation:** a repeatable golden-set workflow, model-size comparison,
and a documented evaluation table with runtime, observed errors, and known limitations
(README). Introducing a human-validated gold reference here activates formal WER.
