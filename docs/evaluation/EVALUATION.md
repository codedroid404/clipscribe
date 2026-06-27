# ClipScribe — Evaluation (M4)

A reproducible, privacy-safe evaluation of the local ASR pipeline: runtime across
clips and model sizes, robustness to invalid inputs, and honest known limitations.

> All figures are **observed measurements**, not guarantees — they vary with hardware,
> model, and clip. The table contains **metrics only**: no transcript text and no source
> filenames (clips are labeled generically), consistent with the project's privacy rules.

## Test environment (NFR-03 reproducibility)

| Item | Value |
|---|---|
| Machine | Apple M1 Pro, 8 cores, arm64 |
| OS | macOS 26.5.1 |
| Python | 3.11.3 |
| faster-whisper | 1.2.1 |
| CTranslate2 | 4.8.0 |
| Compute | CPU, `int8` |
| Decode | conservative settings (`temperature=0`, `beam_size=5`), VAD off |

## How to reproduce

```bash
python scripts/evaluate.py --models base small \
    --clips "Clip A (corporate ~49s)=media/<clipA>.MP4" \
            "Clip B (3-min advice ~212s)=media/<clipB>.MP4" \
    --out docs/evaluation/results.json
```

Omit `--clips` to auto-discover media in `media/` (labeled Clip A, Clip B, … in sorted
order; filenames are never printed). The harness lives in
[`scripts/evaluate.py`](../../scripts/evaluate.py).

## Transcription benchmark

Two real reference clips, each with `base` and `small`. **RTF** = processing ÷ audio
duration (below 1.0 is faster than real time). **Flagged** = segments carrying a
diagnostic warning code.

| Clip | Model | Duration (s) | Processing (s) | RTF | Segments | Flagged | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Clip A (~49s, spoken English) | base | 49.2 | 3.8 | 0.078 | 16 | 0 | — |
| Clip A (~49s, spoken English) | small | 49.2 | 8.8 | 0.179 | 18 | 0 | — |
| Clip B (~212s, spoken English) | base | 212.0 | 18.2 | 0.086 | 56 | 0 | — |
| Clip B (~212s, spoken English) | small | 212.0 | 41.3 | 0.195 | 56 | 0 | — |

(Clips are neutral identifiers; source filenames and transcript text are not published.)

Observations:

- **Comfortably faster than real time** on CPU for both models — RTF ≈ 0.08 (`base`) and
  ≈ 0.18–0.20 (`small`). `small` costs ~2.3× the processing time of `base`.
- **No quality flags** fired on these clips because both are clean, continuous speech.
  That is the expected, healthy case — it does **not** mean flags never trigger (see the
  diagnostics unit tests for low-confidence / no-speech / repetition behavior).
- On `small`, Clip A split into a couple more segments (18 vs 16).

## Robustness (invalid inputs)

The pipeline rejects bad input early with an actionable message (no stack trace), and
temporary paths are scrubbed from messages.

| Case | Result |
| --- | --- |
| Corrupt container (.mp4) | `could not read media (corrupt or unsupported): 'corrupt.mp4' (Invalid data found when processing input)` |
| Empty file (.wav) | `file is empty` |
| Unsupported type (.txt) | `unsupported file type '.txt'. Supported: .m4a, .mov, .mp3, .mp4, .wav` |

A no-audio container (video-only) is rejected by the same audio-stream check in
`media.validate_media`. These paths are covered by `tests/unit/test_media.py`.

## Accuracy notes

- The raw `faster-whisper` output is preserved unaltered as the source record; nothing is
  rewritten or guessed by the application.
- **Manual faithfulness review: not recorded.** No formal human attestation has been
  captured for these clips. The metrics above are automated; transcript faithfulness should
  be judged by a human replaying the source audio, and that result attested explicitly
  (e.g. `MANUAL_REVIEW=CONFIRMED ./review.sh`). Word-level accuracy is not claimed here.

## Diagnostics are heuristics

The quality flags are **heuristics**, not calibrated correctness measures. They exist to
draw attention to regions worth replaying, not to certify accuracy.

| Signal | Meaning | Threshold | Note |
|---|---|---|---|
| Model certainty (`avg_logprob`) | Closer to 0 = stronger model certainty | `< -1.0` flags "low certainty" | **Not** a calibrated accuracy percentage |
| No-speech probability | Likelihood a segment is non-speech | `≥ 0.6` flags "possible silence" | Heuristic; music/noise can trip it |
| Repetition | Adjacent repeated words/bigrams or a segment repeating the previous one | ≥ 4 adjacent repeats | Catches **adjacent** loops only — **not** broader A→B→A patterns |

Users should replay flagged timestamp regions to judge by ear.

## Test-evidence coverage

What is actually backed by evidence today, by type:

| Scenario | Evidence |
|---|---|
| Supported MP4 (end-to-end) | Integration test (`tests/integration/test_service.py`, auto-skips if media absent) |
| Empty / unsupported / corrupt / oversized input | Automated unit tests (`tests/unit/test_media.py`) |
| No-audio container | Same audio-stream check; covered indirectly by media validation, not a dedicated fixture |
| TXT / JSON / SRT / VTT export | Automated unit tests (`tests/unit/test_exporters.py`) |
| Low-certainty / no-speech / repetition flags | Automated unit tests (`tests/unit/test_diagnostics.py`, synthetic segments) |
| Temp cleanup after success and failure | Automated unit tests (`tests/unit/test_tempfiles.py`) |
| Runtime / RTF on real clips | This benchmark (base, small) |
| Supported MOV, long silence, background music, fast speech/accent, real looping output | **Planned, not yet covered** — no figures claimed |

## Known limitations

- **Hallucination risk is mitigated, not eliminated.** Whisper can emit plausible text
  during silence, music, or unclear audio; ClipScribe reduces and *flags* this but makes no
  claim of elimination.
- **Formal WER is deferred.** No human-validated *gold* reference transcript exists yet, so
  no WER figure is reported. The `--reference` WER path is implemented and unit-tested and
  will be activated once a vetted reference is added. The prior Apple Notes transcript is
  not treated as gold truth.
- **CPU-only timing.** Figures above are M1 Pro / `int8`; larger models and lower-end CPUs
  are substantially slower.

## Related

- Milestone validation logs: [`docs/validation/`](../validation/)
- Diagnostics behavior: `src/clipscribe/diagnostics.py` and `tests/unit/test_diagnostics.py`
