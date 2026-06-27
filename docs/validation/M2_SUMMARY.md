# ClipScribe — M2 Validation Summary

## Scope

**M2 — Core service layer.** Refactors the single-module M1 spike into the typed,
modular architecture from `CLAUDE.md`, adds the remaining export formats, and
introduces real quality diagnostics:

- `models.py` — typed `TranscriptResult`, `TranscriptSegment`, `MediaInfo`.
- `media.py` — input validation + audio-stream probing (FR-02/03), actionable errors.
- `transcriber.py` — faster-whisper loading and ASR inference.
- `diagnostics.py` — low-confidence, no-speech, repetition, and repeated-segment flags (FR-09, plan §7).
- `exporters.py` — TXT and JSON **plus new SRT and VTT** (FR-08).
- `tempfiles.py` — randomized temp-workspace lifecycle with guaranteed cleanup (FR-10; groundwork for the M3 upload flow).
- `service.py` — orchestrates validate → transcribe → diagnose → export.
- `cli.py` — now a thin presentation layer over `service`.

Out of scope for M2: the Streamlit UI (M3) and formal WER benchmarking (still
deferred — no gold reference transcript yet).

## Validation status

**PASSED.** All automated checks succeed. Reproducible evidence is in
[`m2_review.txt`](m2_review.txt), regenerated with:

```bash
MILESTONE=M2 ./review.sh docs/validation/m2_review.txt
```

## Checks completed

| Check | Tool | Result |
|---|---|---|
| Lint | `ruff` | Passed |
| Unit + integration tests | `pytest` | Passed — **23 tests** |
| Media validation + audio probe | `media.py` (PyAV) | Covered (missing/unsupported/empty/oversized/corrupt) |
| Diagnostics | `diagnostics.py` | Covered (low-confidence, no-speech, repetition, repeated-segment) |
| Subtitle/text exporters | `exporters.py` | Covered (TXT/JSON/SRT/VTT formatting + timestamps) |
| Temp-file lifecycle | `tempfiles.py` | Covered (cleanup on success and on exception) |
| End-to-end pipeline (real clip) | `service.transcribe_file` | Succeeded (integration test; auto-skips when media absent) |
| Privacy (Git tracking) | `git add -n` | No media/transcripts tracked |

Observed transcription run (base model, CPU/int8) as recorded in the log:

- detected language: `en` (probability ≈ 1.00)
- media duration: ≈ 49.2 s
- processing time: ≈ 3.7 s
- real-time factor: ≈ 0.07 (well faster than real time)
- segments: 16

These are **observed values from one base-model run**, not guaranteed figures.

## Accuracy evaluation

- The raw `faster-whisper` output is still preserved unaltered. Diagnostics only
  **annotate** segments with `warning_codes`; they do not rewrite, remove, or guess text.
- **Manual faithfulness review: not recorded.** M2 changed only structure and export, not
  the transcription itself; no formal human attestation is claimed.
- **Formal WER remains deferred.** No human-validated gold reference transcript
  exists yet, so no WER figure is claimed. The `--reference` WER path is
  implemented and unit-tested, ready to activate once a vetted reference is added.

No accuracy metric is asserted here that was not actually measured.

## Privacy verification

- `media/`, `transcripts/`, and `references/` remain gitignored; the privacy check
  confirms Git would not track personal media or generated transcripts.
- [`m2_review.txt`](m2_review.txt) is a curated, privacy-safe artifact: the
  transcript body is redacted, and the source filename and absolute/user paths are
  excluded. It was inspected for keys, tokens, environment-variable values,
  usernames, media filenames, transcript text, and model-cache paths — none present.

## Outcome

M2 is complete and validated. ClipScribe now has a clean, typed, tested service
layer that validates input, transcribes locally, flags uncertain/repeated/no-speech
segments, and exports all four required formats (TXT, JSON, SRT, VTT). The CLI is a
thin wrapper, leaving the pipeline ready to be driven by a UI.

## Next milestone

**M3 — Streamlit MVP:** upload, model/language/VAD settings, progress, raw
timestamped transcript display with warnings, and TXT/JSON/SRT/VTT downloads —
reusing `service.transcribe_file` and the `tempfiles` lifecycle for uploaded media.
