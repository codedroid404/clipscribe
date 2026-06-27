"""Application orchestration: validate -> transcribe -> diagnose -> export.

This is the single entry point the CLI (and later the Streamlit UI) call. It
keeps presentation layers thin and free of pipeline logic.
"""

from __future__ import annotations

from pathlib import Path

from . import diagnostics, exporters, media, transcriber
from .models import TranscriptResult


def run_pipeline(
    path: Path,
    *,
    model_name: str = "base",
    language: str | None = None,
    use_vad: bool = False,
) -> TranscriptResult:
    """Validate, transcribe, and diagnose a local media file (no disk export).

    Used by the Streamlit UI, which serializes outputs in-memory for download.

    Raises:
        media.MediaValidationError: if the input cannot be transcribed.
    """
    info = media.validate_media(path)

    result = transcriber.run_asr(
        path, model_name=model_name, language=language, use_vad=use_vad
    )

    # Fall back to the probed container duration if the model did not report one.
    if result.media_duration_seconds is None and info.duration_seconds is not None:
        result.media_duration_seconds = info.duration_seconds

    diagnostics.analyze(result)
    return result


def transcribe_file(
    path: Path,
    *,
    model_name: str = "base",
    language: str | None = None,
    use_vad: bool = False,
    out_dir: Path = Path("transcripts"),
) -> tuple[TranscriptResult, dict[str, Path]]:
    """Run the full pipeline on a local media file and write all four formats.

    Used by the CLI.

    Raises:
        media.MediaValidationError: if the input cannot be transcribed.
    """
    result = run_pipeline(
        path, model_name=model_name, language=language, use_vad=use_vad
    )
    outputs = exporters.write_all(result, out_dir)
    return result, outputs
