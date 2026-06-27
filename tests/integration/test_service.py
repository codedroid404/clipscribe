"""Integration test: full pipeline on a real clip.

Discovers any supported media file in ``media/`` (no hardcoded private filename),
or honors ``CLIPSCRIBE_TEST_CLIP``. Auto-skips when none is present, so no personal
media is ever required or committed. Runs faster-whisper locally when present.
"""

import os
from pathlib import Path

import pytest

from clipscribe.media import SUPPORTED_EXTENSIONS


def _discover_clip() -> Path | None:
    env = os.environ.get("CLIPSCRIBE_TEST_CLIP")
    if env and Path(env).is_file():
        return Path(env)
    media = Path("media")
    if not media.exists():
        return None
    return next(
        (p for p in sorted(media.iterdir()) if p.suffix.lower() in SUPPORTED_EXTENSIONS),
        None,
    )


_CLIP = _discover_clip()


@pytest.mark.skipif(_CLIP is None, reason="no media clip present")
def test_transcribe_file_end_to_end(tmp_path):
    from clipscribe import service

    result, outputs = service.transcribe_file(_CLIP, model_name="base", out_dir=tmp_path)

    assert result.segments, "expected at least one transcript segment"
    assert result.detected_language
    assert result.media_duration_seconds and result.media_duration_seconds > 0
    for kind in ("txt", "json", "srt", "vtt"):
        assert outputs[kind].exists()
