# ClipScribe — M4 Validation Summary

## Scope

**M4 — Trust and evaluation.** A repeatable, privacy-safe evaluation of the local ASR
pipeline: runtime across clips and model sizes, robustness to invalid inputs, documented
reproducibility, and honest known limitations.

- `scripts/evaluate.py` — evaluation harness; benchmarks clips × models and emits a
  **metrics-only** Markdown table + JSON (no transcript text, no source filenames).
- `docs/evaluation/EVALUATION.md` — the reproducible results table, test environment,
  robustness behavior, accuracy notes, and known limitations.
- `tests/unit/test_evaluate.py` — unit tests for the deterministic metrics/table builders,
  including assertions that **no transcript text or filename leaks** into a row.

Out of scope for M4: portfolio polish (M5) and formal WER (still deferred — no gold
reference yet).

## Validation status

**PASSED.** Reproducible evidence in [`m4_review.txt`](m4_review.txt); full results in
[`../evaluation/EVALUATION.md`](../evaluation/EVALUATION.md).

## Checks completed

| Check | Tool | Result |
|---|---|---|
| Lint | `ruff` | Passed |
| Unit + integration tests | `pytest` | Passed — **26 tests** (+3 for the harness) |
| Benchmark (2 clips × base/small) | `scripts/evaluate.py` | Produced real metrics |
| Robustness (corrupt / empty / unsupported) | `media.validate_media` | Rejected with clear errors |
| App boot (headless) | `streamlit` | Served HTTP 200 |
| Privacy (Git + artifacts) | `git add -n`, grep | No media/transcripts/filenames tracked |

## Results (observed, M1 Pro · CPU/int8)

| Clip | Model | Duration (s) | Processing (s) | RTF | Segments |
|---|---|---|---|---|---|
| Clip A (corporate ~49s) | base | 49.2 | 3.8 | 0.078 | 16 |
| Clip A (corporate ~49s) | small | 49.2 | 8.8 | 0.179 | 18 |
| Clip B (3-min advice ~212s) | base | 212.0 | 18.2 | 0.086 | 56 |
| Clip B (3-min advice ~212s) | small | 212.0 | 41.3 | 0.195 | 56 |

Both models run comfortably faster than real time on CPU; `small` costs ~2.3× `base`.
No quality flags fired (clean, continuous speech — the healthy case).

## Accuracy evaluation

- Raw output preserved unaltered; diagnostics only annotate.
- **Manual faithfulness review: not recorded** — no formal human attestation captured.
  Word-level accuracy is not claimed; transcript faithfulness should be judged by replaying
  the source audio and attested explicitly.
- **Formal WER deferred** — no human-validated gold reference yet; the `--reference` WER
  path is implemented and unit-tested, ready to activate.

## Privacy verification

- The benchmark table and JSON contain **metrics only** — no transcript text, no source
  filenames (clips labeled generically); temp paths scrubbed from robustness messages.
- `media/` and `transcripts/` remain gitignored; `m4_review.txt` is the curated, redacted
  log. Artifacts were grepped for usernames, paths, filenames, and tokens — none present.

## Outcome

M4 is complete and validated. ClipScribe now has a reproducible evaluation workflow and a
committed, honest evaluation document (runtime, robustness, limitations) — satisfying the
milestone's exit criterion. No metric is claimed that was not measured.

## Next milestone

**M5 — Portfolio polish:** README hook + architecture diagram, app screenshots, privacy
statement, and changelog. A human-validated gold reference can be added to activate WER.
