"""Durable local storage for the saved-transcript library (M6).

SQLite (stdlib ``sqlite3``) at a Git-ignored ``data/clipscribe.db``. Persists transcripts
with segment-level timestamps preserved, so a saved transcript can be reopened, exported,
or deleted later.

Privacy: the database holds transcript content and is local-only / gitignored. Nothing
here is logged.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .models import StoredTranscript, TranscriptResult, TranscriptSegment, TranscriptSummary

DEFAULT_DB = Path("data/clipscribe.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transcripts (
    id                TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    source_filename   TEXT NOT NULL,
    created           TEXT NOT NULL,
    duration_seconds  REAL,
    language          TEXT,
    model_name        TEXT,
    processing_seconds REAL,
    segments          TEXT NOT NULL,   -- JSON list of segment dicts
    readable_text     TEXT NOT NULL,
    diagnostic_flags  TEXT NOT NULL    -- JSON list of warning strings
);
"""


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    """Open (creating parent dir + schema) a connection with row access by name."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def save_transcript(
    result: TranscriptResult,
    title: str,
    *,
    db_path: Path = DEFAULT_DB,
    created: str | None = None,
) -> str:
    """Persist a transcription result and return its new id."""
    transcript_id = secrets.token_hex(8)
    readable_text = " ".join(seg.text.strip() for seg in result.segments).strip()
    segments_json = json.dumps([asdict(seg) for seg in result.segments])
    flags_json = json.dumps(list(result.warnings))
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO transcripts (id, title, source_filename, created, "
            "duration_seconds, language, model_name, processing_seconds, segments, "
            "readable_text, diagnostic_flags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                transcript_id,
                title.strip() or result.source_filename,
                result.source_filename,
                created or _now_iso(),
                result.media_duration_seconds,
                result.detected_language,
                result.model_name,
                result.processing_seconds,
                segments_json,
                readable_text,
                flags_json,
            ),
        )
    return transcript_id


def suggest_title(text: str, *, max_words: int = 8, max_chars: int = 60) -> str:
    """A short, human title derived from transcript text (local, free)."""
    words = text.split()
    if not words:
        return "Untitled transcript"
    snippet = " ".join(words[:max_words])[:max_chars].rstrip(" ,.;:!-—")
    return (snippet[0].upper() + snippet[1:]) if snippet else "Untitled transcript"


def list_transcripts(*, db_path: Path = DEFAULT_DB) -> list[TranscriptSummary]:
    """Return library entries (newest first) without the heavy segment payload."""
    if not db_path.exists():
        return []
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, title, source_filename, created, duration_seconds, language, "
            "segments FROM transcripts ORDER BY created DESC"
        ).fetchall()
    return [
        TranscriptSummary(
            id=row["id"],
            title=row["title"],
            source_filename=row["source_filename"],
            created=row["created"],
            duration_seconds=row["duration_seconds"],
            language=row["language"],
            segment_count=len(json.loads(row["segments"])),
        )
        for row in rows
    ]


def get_transcript(transcript_id: str, *, db_path: Path = DEFAULT_DB) -> StoredTranscript | None:
    """Load a full stored transcript (segments rehydrated), or None if missing."""
    if not db_path.exists():
        return None
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM transcripts WHERE id = ?", (transcript_id,)
        ).fetchone()
    if row is None:
        return None
    segments = [TranscriptSegment(**seg) for seg in json.loads(row["segments"])]
    return StoredTranscript(
        id=row["id"],
        title=row["title"],
        source_filename=row["source_filename"],
        created=row["created"],
        duration_seconds=row["duration_seconds"],
        language=row["language"],
        model_name=row["model_name"],
        processing_seconds=row["processing_seconds"],
        segments=segments,
        readable_text=row["readable_text"],
        diagnostic_flags=json.loads(row["diagnostic_flags"]),
    )


def stored_to_result(stored: StoredTranscript) -> TranscriptResult:
    """Rebuild a TranscriptResult so saved transcripts reuse the renderers/exporters."""
    return TranscriptResult(
        source_filename=stored.source_filename,
        media_duration_seconds=stored.duration_seconds,
        detected_language=stored.language,
        language_probability=None,
        model_name=stored.model_name or "saved",
        processing_seconds=stored.processing_seconds or 0.0,
        segments=stored.segments,
        warnings=list(stored.diagnostic_flags),
    )


def delete_transcript(transcript_id: str, *, db_path: Path = DEFAULT_DB) -> bool:
    """Delete by id. Returns True if a row was removed."""
    if not db_path.exists():
        return False
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM transcripts WHERE id = ?", (transcript_id,))
        return cur.rowcount > 0


def delete_all_transcripts(*, db_path: Path = DEFAULT_DB) -> int:
    """Delete every saved transcript. Returns the number of rows removed."""
    if not db_path.exists():
        return 0
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM transcripts")
        return cur.rowcount
