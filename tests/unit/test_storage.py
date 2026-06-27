"""Unit tests for the saved-transcript library (M6) — temp DB, no model needed."""

from clipscribe import storage
from clipscribe.models import TranscriptResult, TranscriptSegment


def _result() -> TranscriptResult:
    return TranscriptResult(
        source_filename="clip.mp4",
        media_duration_seconds=12.0,
        detected_language="en",
        language_probability=0.99,
        model_name="base",
        processing_seconds=2.0,
        segments=[
            TranscriptSegment(0, 0.0, 4.0, "hello there", avg_logprob=-0.2, no_speech_prob=0.1),
            TranscriptSegment(1, 4.0, 8.0, "quiet bit", no_speech_prob=0.9,
                              warning_codes=["no_speech"]),
        ],
        warnings=["contains_no_speech_segments"],
    )


def test_save_list_get_roundtrip(tmp_path):
    db = tmp_path / "lib.db"
    tid = storage.save_transcript(
        _result(), "My Clip", db_path=db, created="2026-01-01T00:00:00+00:00"
    )

    summaries = storage.list_transcripts(db_path=db)
    assert len(summaries) == 1
    assert summaries[0].title == "My Clip"
    assert summaries[0].segment_count == 2

    stored = storage.get_transcript(tid, db_path=db)
    assert stored.title == "My Clip"
    assert stored.language == "en"
    assert [s.text for s in stored.segments] == ["hello there", "quiet bit"]
    assert stored.segments[1].warning_codes == ["no_speech"]
    assert stored.diagnostic_flags == ["contains_no_speech_segments"]
    # rebuilds a TranscriptResult for the renderers/exporters
    assert storage.stored_to_result(stored).source_filename == "clip.mp4"


def test_title_falls_back_to_filename(tmp_path):
    db = tmp_path / "lib.db"
    tid = storage.save_transcript(_result(), "   ", db_path=db)
    assert storage.get_transcript(tid, db_path=db).title == "clip.mp4"


def test_delete_and_missing(tmp_path):
    db = tmp_path / "lib.db"
    tid = storage.save_transcript(_result(), "X", db_path=db)
    assert storage.delete_transcript(tid, db_path=db) is True
    assert storage.delete_transcript(tid, db_path=db) is False
    assert storage.get_transcript(tid, db_path=db) is None


def test_empty_library_before_any_save(tmp_path):
    db = tmp_path / "none.db"
    assert storage.list_transcripts(db_path=db) == []
    assert storage.get_transcript("nope", db_path=db) is None


def test_suggest_title():
    assert storage.suggest_title("tell me about a time you went above and beyond for a customer") \
        == "Tell me about a time you went above"
    assert storage.suggest_title("   ") == "Untitled transcript"


def test_delete_all_transcripts(tmp_path):
    db = tmp_path / "lib.db"
    storage.save_transcript(_result(), "one", db_path=db)
    storage.save_transcript(_result(), "two", db_path=db)
    assert len(storage.list_transcripts(db_path=db)) == 2
    assert storage.delete_all_transcripts(db_path=db) == 2
    assert storage.list_transcripts(db_path=db) == []
    assert storage.delete_all_transcripts(db_path=db) == 0
    assert storage.delete_all_transcripts(db_path=tmp_path / "none.db") == 0
