"""Unit tests for media validation (no real media required)."""

import pytest

from clipscribe.media import MediaValidationError, validate_media


def test_missing_file(tmp_path):
    with pytest.raises(MediaValidationError, match="not found"):
        validate_media(tmp_path / "nope.mp4")


def test_unsupported_extension(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello")
    with pytest.raises(MediaValidationError, match="unsupported file type"):
        validate_media(f)


def test_empty_file(tmp_path):
    f = tmp_path / "empty.wav"
    f.touch()
    with pytest.raises(MediaValidationError, match="empty"):
        validate_media(f)


def test_oversized_file(tmp_path):
    f = tmp_path / "big.mp3"
    f.write_bytes(b"\x00" * 1024)
    with pytest.raises(MediaValidationError, match="too large"):
        validate_media(f, max_bytes=512)


def test_corrupt_media_reports_actionable_error(tmp_path):
    # A supported extension but not real media -> probe fails cleanly.
    f = tmp_path / "fake.mp4"
    f.write_bytes(b"not really an mp4 container")
    with pytest.raises(MediaValidationError):
        validate_media(f)
