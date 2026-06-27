"""Unit tests for the evaluation harness's deterministic helpers."""

from evaluate import TABLE_KEYS, format_table, metrics_row

from clipscribe.models import TranscriptResult, TranscriptSegment


def _result() -> TranscriptResult:
    return TranscriptResult(
        source_filename="secret-clip.mp4",
        media_duration_seconds=50.0,
        detected_language="en",
        language_probability=0.99,
        model_name="base",
        processing_seconds=5.0,
        segments=[
            TranscriptSegment(0, 0.0, 1.0, "hello"),
            TranscriptSegment(1, 1.0, 2.0, "world", warning_codes=["no_speech"]),
        ],
        warnings=["contains_no_speech_segments"],
    )


def test_metrics_row_values():
    row = metrics_row("Clip A", "base", _result())
    assert row["clip"] == "Clip A"
    assert row["model"] == "base"
    assert row["duration_s"] == 50.0
    assert row["processing_s"] == 5.0
    assert row["rtf"] == 0.1  # 5 / 50
    assert row["segments"] == 2
    assert row["flagged"] == 1
    assert row["warnings"] == "contains_no_speech_segments"


def test_metrics_row_leaks_no_transcript_or_filename():
    row = metrics_row("Clip A", "base", _result())
    assert set(row) == set(TABLE_KEYS)
    blob = " ".join(str(v) for v in row.values())
    assert "hello" not in blob and "world" not in blob  # no transcript text
    assert "secret-clip" not in blob  # no source filename


def test_format_table_structure():
    table = format_table([metrics_row("Clip A", "base", _result())])
    lines = table.splitlines()
    assert lines[0].startswith("| Clip | Model |")
    assert set(lines[1].replace(" ", "")) == {"|", "-"}  # divider row
    assert "| Clip A | base |" in lines[2]
