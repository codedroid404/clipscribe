# ClipScribe — M6 Validation Summary

## Scope

**M6 — Persistence (saved transcript library).** Gives the in-memory MVP a durable local home so
transcripts survive a session, and lays the data foundation later milestones build on.

- `src/clipscribe/storage.py` — SQLite (stdlib `sqlite3`, no new dependency) at a Git-ignored
  `data/clipscribe.db`. `save_transcript` / `list_transcripts` / `get_transcript` /
  `delete_transcript` (+ `delete_all_transcripts`), with segment-level timestamps preserved in the
  stored JSON so the library can later be chunked/embedded (M10) and cited (M11).
- `models.py` — `StoredTranscript` / `TranscriptSummary` contracts; `stored_to_result` rebuilds a
  `TranscriptResult` so saved transcripts reuse the existing renderers/exporters.
- `app.py` — **Save to library** control and a **Library** panel (open / delete / delete-all).
- `cli.py` — `clipscribe <clip> --save [--title "…"]`.

## Validation status

**PASSED** (lint + automated tests). Evidence: [`m6_review.txt`](m6_review.txt).

## Checks completed

| Check | Tool | Result |
|---|---|---|
| Lint | `ruff` | Passed |
| Unit + integration tests | `pytest` | Passed — full suite green |
| Save → list → get round-trip (segments rehydrated) | `tests/unit/test_storage.py` (temp DB) | Verified |
| Blank-title fallback, delete / missing, empty library | `tests/unit/test_storage.py` | Verified |
| App boot (headless, incl. Library panel) | `streamlit` / `review.sh` | Regenerable via `./review.sh` |
| Privacy (secrets + Git) | `.gitignore`, grep | `data/` + `.env` ignored; no content/filename leak |

## Trust / privacy

- **Local-only.** The database is a plain file under the gitignored `data/`; nothing is uploaded
  and saving requires no API key — the default ASR path stays fully local.
- **No content logging.** Save/delete log counts and ids only — never transcript text or filenames.
- Segment timestamps are preserved verbatim, so the raw transcript remains the source of truth.

## Outcome

M6 is complete and validated. Transcripts persist across sessions and can be reopened, exported,
or deleted — the prerequisite for the document import (M7), hosted analysis (M8/M9), and the
saved-conversation history that followed.

## Next

**M7 (PDF documents)** then **M10 (local embeddings) → M11 (retrieval)** so relevant sources
surface without manual selection. Embeddings remain greenfield.
