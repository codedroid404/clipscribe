"""Media validation, probing, and audio-stream detection.

Audio decoding itself is delegated to faster-whisper (via PyAV) at transcription
time; this module's job is to fail early and clearly on inputs that cannot be
transcribed, satisfying FR-02 (reject unsupported/empty/corrupt/oversized files)
and FR-03 (confirm a readable audio stream exists).
"""

from __future__ import annotations

from pathlib import Path

from .models import MediaInfo

SUPPORTED_EXTENSIONS = {".mov", ".mp4", ".m4a", ".mp3", ".wav"}

# Upper bound for this short-form product. Rejects oversized inputs before the
# expensive decode/transcribe step. Matches the Streamlit upload cap (512 MB).
MAX_FILE_BYTES = 512 * 1024 * 1024  # 512 MB


class MediaValidationError(Exception):
    """Raised with an actionable message when an input cannot be transcribed."""


def validate_media(path: Path, *, max_bytes: int = MAX_FILE_BYTES) -> MediaInfo:
    """Validate and probe a media file, returning typed info or raising.

    Raises:
        MediaValidationError: with a user-facing message (no stack trace needed).
    """
    if not path.exists():
        raise MediaValidationError(f"input file not found: {path}")
    if not path.is_file():
        raise MediaValidationError(f"input path is not a file: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise MediaValidationError(
            f"unsupported file type '{path.suffix}'. Supported: {supported}"
        )

    size = path.stat().st_size
    if size == 0:
        raise MediaValidationError(f"file is empty: {path}")
    if size > max_bytes:
        raise MediaValidationError(
            f"file too large ({size} bytes exceeds {max_bytes} byte limit): {path}"
        )

    duration, has_audio = _probe(path)
    if not has_audio:
        raise MediaValidationError(
            f"no audio stream found in '{path.name}'; nothing to transcribe"
        )

    return MediaInfo(
        filename=path.name,
        size_bytes=size,
        has_audio=has_audio,
        duration_seconds=duration,
    )


def _probe(path: Path) -> tuple[float | None, bool]:
    """Return (duration_seconds, has_audio) by inspecting the container.

    Uses PyAV (bundled with faster-whisper) so no system ffmpeg is required.
    A corrupt/unreadable container is reported as an actionable error.
    """
    import av

    try:
        with av.open(str(path)) as container:
            has_audio = any(stream.type == "audio" for stream in container.streams)
            duration = None
            if container.duration is not None:
                # container.duration is expressed in av.time_base (microseconds).
                duration = round(container.duration / av.time_base, 3)
            return duration, has_audio
    except Exception as exc:  # PyAV raises various error types across versions
        raise MediaValidationError(
            f"could not read media (corrupt or unsupported): '{path.name}' ({exc})"
        ) from exc
