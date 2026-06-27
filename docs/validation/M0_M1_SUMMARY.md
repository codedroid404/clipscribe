# ClipScribe — M0/M1 Validation Summary

## Scope

This document records the lightweight validation of the first two ClipScribe
milestones:

- **M0 — Repository foundation:** project structure, pinned dependencies, lint/test
  configuration, `.gitignore`, and a minimal `src/clipscribe` package.
- **M1 — CLI transcription spike:** prove that a real iPhone screen recording can be
  decoded and transcribed **locally** with `faster-whisper`, producing a timestamped
  raw transcript as TXT and JSON.

It does **not** cover the Streamlit UI, SRT/VTT export, the full module split, or a
formal accuracy benchmark — those belong to later milestones.

## Validation status

**PASSED.** All automated checks succeed and the M1 transcription spike produced a
faithful, timestamped transcript from a real iPhone `.MP4`. The reproducible evidence
is in [`m0_m1_review.txt`](m0_m1_review.txt), regenerated with:

```bash
./review.sh docs/validation/m0_m1_review.txt
```

## Checks completed

| Check | Tool | Result |
|---|---|---|
| Lint | `ruff` | Passed |
| Unit tests | `pytest` | Passed |
| Real iPhone `.MP4` decode | `faster-whisper` (PyAV) | Succeeded |
| Timestamped TXT output | exporter | Generated |
| JSON output (data contract) | exporter | Generated |
| Privacy (Git tracking) | `git add -n` | No media/transcripts tracked |

Observed transcription run (base model, CPU/int8) as recorded in the log:

- detected language: `en` (probability ≈ 1.00)
- media duration: ≈ 49.2 s
- processing time: ≈ 3.8 s
- real-time factor: ≈ 0.08 (well faster than real time)
- segments: 16

These are **observed values from one base-model run**, not guaranteed performance
figures; they will vary with model size, hardware, and clip.

## Accuracy evaluation

- The raw `faster-whisper` output is preserved unaltered as the source record. No LLM
  rewrites, cleans, or fills in unclear speech.
- **Manual faithfulness review: not recorded** — no formal human attestation was captured.
  Transcript faithfulness should be judged by replaying the source audio and attested
  explicitly; word-level accuracy is not claimed here.
- **Formal word error rate (WER) was deferred.** No human-validated *gold* reference
  transcript exists yet, so no WER figure is claimed. The `--reference` WER path is
  implemented and unit-tested, ready to activate once a vetted reference is added.

No accuracy metric is asserted here that was not actually measured.

## Privacy verification

- `media/`, `transcripts/`, and `references/` are gitignored; the privacy check
  confirms Git would not track personal media or generated transcripts.
- The automated review log ([`m0_m1_review.txt`](m0_m1_review.txt)) is a **curated,
  privacy-safe artifact**. It excludes the transcript body (replaced with a redaction
  placeholder), the source media filename, and absolute/user paths. It was inspected
  for keys, tokens, environment-variable values, usernames, media filenames,
  transcript text, and model-cache paths — none were present.
- Transcription is fully local and requires no API key (only a one-time model-weight
  download). No media or transcript leaves the machine.

## Outcome

M0 and M1 are complete and validated. The core pipeline — decode a real iPhone
screen recording locally, run `faster-whisper`, and emit a timestamped raw transcript
as TXT + JSON — works end to end, is lint/test clean, and is privacy-safe.

Most importantly, **M0 and M1 retired the central technical risk of the project:
whether short iPhone-video audio could be decoded and transcribed faithfully on local
hardware with no hosted API.** That risk is now resolved positively.

## Next milestone

**M2 — Core service layer:** split the logic into typed `media` / `transcriber` /
`diagnostics` / `exporters` modules, add SRT/VTT export, and expand unit coverage for
validation, timestamps, warnings, and subtitle formatting. A human-validated gold
reference transcript can then be introduced to activate formal WER measurement.
