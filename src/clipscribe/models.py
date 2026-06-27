"""Typed transcript and media contracts (the project's Core Data Contract)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TranscriptSegment:
    index: int
    start_seconds: float
    end_seconds: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    warning_codes: list[str] = field(default_factory=list)


@dataclass
class TranscriptResult:
    source_filename: str
    media_duration_seconds: float | None
    detected_language: str | None
    language_probability: float | None
    model_name: str
    processing_seconds: float
    segments: list[TranscriptSegment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MediaInfo:
    """Result of validating + probing an input media file."""

    filename: str
    size_bytes: int
    has_audio: bool
    duration_seconds: float | None = None


@dataclass
class StoredTranscript:
    """A transcript persisted in the saved library (M6)."""

    id: str
    title: str
    source_filename: str
    created: str
    duration_seconds: float | None
    language: str | None
    model_name: str | None
    processing_seconds: float | None
    segments: list[TranscriptSegment]
    readable_text: str
    diagnostic_flags: list[str]


@dataclass
class TranscriptSummary:
    """Lightweight library listing entry (no segment payload)."""

    id: str
    title: str
    source_filename: str
    created: str
    duration_seconds: float | None
    language: str | None
    segment_count: int
