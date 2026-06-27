"""Unit tests for transcript exporters (TXT/JSON/SRT/VTT) and timestamps."""

import json

from clipscribe.exporters import (
    format_timestamp,
    render_json,
    render_srt,
    render_txt,
    render_vtt,
    write_all,
)
from clipscribe.models import TranscriptResult, TranscriptSegment


def _sample() -> TranscriptResult:
    return TranscriptResult(
        source_filename="clip.mp4",
        media_duration_seconds=5.0,
        detected_language="en",
        language_probability=0.99,
        model_name="base",
        processing_seconds=1.0,
        segments=[
            TranscriptSegment(0, 0.0, 2.5, "hello there"),
            TranscriptSegment(1, 2.5, 5.0, "quiet bit", no_speech_prob=0.9,
                              warning_codes=["no_speech"]),
        ],
    )


def test_format_timestamp_vtt_and_srt_separators():
    assert format_timestamp(0) == "00:00:00.000"
    assert format_timestamp(3661.001) == "01:01:01.001"
    assert format_timestamp(3661.001, sep=",") == "01:01:01,001"


def test_format_timestamp_clamps_negative():
    assert format_timestamp(-5) == "00:00:00.000"


def test_render_txt_has_timestamps_and_flags():
    txt = render_txt(_sample())
    assert "[00:00:00.000 --> 00:00:02.500] hello there" in txt
    assert "[no_speech]" in txt
    assert "clip.mp4" in txt


def test_render_srt_format():
    srt = render_srt(_sample())
    assert srt.startswith("1\n00:00:00,000 --> 00:00:02,500\nhello there\n")
    assert "2\n00:00:02,500 --> 00:00:05,000\nquiet bit\n" in srt


def test_render_vtt_format():
    vtt = render_vtt(_sample())
    assert vtt.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:02.500\nhello there\n" in vtt


def test_render_json_roundtrip():
    data = json.loads(render_json(_sample()))
    assert data["source_filename"] == "clip.mp4"
    assert len(data["segments"]) == 2
    assert data["segments"][1]["warning_codes"] == ["no_speech"]


def test_write_all_creates_four_files(tmp_path):
    outputs = write_all(_sample(), tmp_path)
    assert set(outputs) == {"txt", "json", "srt", "vtt"}
    for path in outputs.values():
        assert path.exists()
        assert path.stem == "clip"
