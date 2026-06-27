"""faster-whisper model loading and ASR inference.

Produces the raw, source-of-truth transcript. Diagnostics (warning codes) are
applied separately so this layer stays a faithful record of what the model said.
"""

from __future__ import annotations

import time
from pathlib import Path

from .models import TranscriptResult, TranscriptSegment


def run_asr(
    path: Path,
    *,
    model_name: str = "base",
    language: str | None = None,
    use_vad: bool = False,
) -> TranscriptResult:
    """Transcribe a local media file with faster-whisper (CPU/int8).

    The original file is read directly; faster-whisper decodes its audio
    in-memory via PyAV, so no temporary audio file is created.
    """
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")

    started = time.monotonic()
    segments_iter, info = model.transcribe(
        str(path),
        language=language,
        beam_size=5,
        temperature=0.0,  # deterministic; never sample to "fill in" unclear speech
        vad_filter=use_vad,
    )

    segments: list[TranscriptSegment] = []
    for i, seg in enumerate(segments_iter):  # iterating drives the transcription
        segments.append(
            TranscriptSegment(
                index=i,
                start_seconds=round(seg.start, 3),
                end_seconds=round(seg.end, 3),
                text=seg.text.strip(),
                avg_logprob=seg.avg_logprob,
                no_speech_prob=seg.no_speech_prob,
            )
        )
    processing_seconds = time.monotonic() - started

    return TranscriptResult(
        source_filename=path.name,
        media_duration_seconds=round(info.duration, 3) if info.duration else None,
        detected_language=info.language,
        language_probability=info.language_probability,
        model_name=model_name,
        processing_seconds=round(processing_seconds, 3),
        segments=segments,
        warnings=[],
    )
