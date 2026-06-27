# ClipScribe — M5 Validation Summary

## Scope

**M5 — Portfolio polish.** Make the repository understandable and demonstrable without
verbal explanation, and round out the app's review experience.

- **README** — hook, badges, app screenshot, "what it demonstrates", feature list,
  **architecture diagram** (Mermaid) + module table, privacy/trust statement, limitations,
  and a changelog link.
- **`CHANGELOG.md`** — milestone-organized history (M0–M5).
- **App** — new **Readable** transcript tab (clean flowing prose; same words, timestamps
  removed — not an LLM rewrite), plus the earlier theme switcher and author footer.

Out of scope: formal WER (still deferred — no gold reference yet) and the optional
post-MVP roadmap (LLM-assisted analysis, RAG, agents).

## Validation status

**PASSED.** Evidence in [`m5_review.txt`](m5_review.txt).

## Checks completed

| Check | Tool | Result |
|---|---|---|
| Lint | `ruff` | Passed |
| Unit + integration tests | `pytest` | Passed — 26 tests |
| Transcription (real clip) | `service` + CLI | Succeeded |
| App boot (headless, incl. Readable tab + footer) | `streamlit` | Served HTTP 200 |
| Privacy (Git + artifacts) | `git add -n`, grep | No media/transcripts/filenames tracked |
| Review tabs render | standalone page screenshot | Timestamped / Segments / Readable all render |

## Accuracy / trust

- No transcription behavior changed in M5 — additions are presentation and docs only.
- Raw output preserved unaltered; the Timestamped / Segments / Readable views present the
  same ASR segments, never an LLM-rewritten transcript.
- **Formal WER remains deferred** — no human-validated gold reference yet.

## Privacy verification

- The README screenshot is the app's **empty home state** — no transcript content shown.
- No new media/transcript paths enter Git; `m5_review.txt` is the curated, redacted log.

## Outcome

M5 is complete. The repository now presents itself accurately as a **local ASR
application** with a clear architecture, honest limitations, reproducible evaluation, and a
polished UI — demonstrable end to end without explanation. This completes the planned MVP
milestones M0–M5.

## Definition of Done — met

`streamlit run app.py` → upload a real iPhone clip → transcribe locally (no API key) →
review a raw timestamped transcript with uncertainty flags (Timestamped / Segments / Readable)
→ download TXT/JSON/SRT/VTT, with temporary media cleaned up and tests passing.

## After the MVP (optional)

A human-validated gold reference activates WER. The plan's roadmap (LLM-assisted analysis,
RAG over a transcript library, tool-using/agentic research) remains explicitly out of scope
and must keep its honest terminology.
