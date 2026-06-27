"""Unit tests for uncertainty / repetition / no-speech diagnostics."""

from clipscribe.diagnostics import analyze, is_internally_repetitive
from clipscribe.models import TranscriptResult, TranscriptSegment


def _result(segments: list[TranscriptSegment]) -> TranscriptResult:
    return TranscriptResult(
        source_filename="clip.mp4",
        media_duration_seconds=10.0,
        detected_language="en",
        language_probability=0.99,
        model_name="base",
        processing_seconds=1.0,
        segments=segments,
    )


def test_is_internally_repetitive_word_loop():
    assert is_internally_repetitive("yeah yeah yeah yeah")
    assert not is_internally_repetitive("this is a normal sentence")


def test_is_internally_repetitive_bigram_loop():
    assert is_internally_repetitive("na na na na na na na na")


def test_low_confidence_and_no_speech_flags():
    result = _result([
        TranscriptSegment(0, 0.0, 1.0, "clear speech", avg_logprob=-0.2, no_speech_prob=0.1),
        TranscriptSegment(1, 1.0, 2.0, "mumble", avg_logprob=-2.0, no_speech_prob=0.8),
    ])
    analyze(result)
    assert result.segments[0].warning_codes == []
    assert "low_confidence" in result.segments[1].warning_codes
    assert "no_speech" in result.segments[1].warning_codes
    assert "contains_low_confidence_segments" in result.warnings
    assert "contains_no_speech_segments" in result.warnings


def test_repeated_segment_flag():
    result = _result([
        TranscriptSegment(0, 0.0, 1.0, "thank you"),
        TranscriptSegment(1, 1.0, 2.0, "Thank you."),  # normalized duplicate
    ])
    analyze(result)
    assert "repeated_segment" in result.segments[1].warning_codes
    assert "contains_repeated_or_looping_segments" in result.warnings


def test_empty_result_warns():
    result = _result([])
    analyze(result)
    assert result.warnings == ["no_segments_detected"]
