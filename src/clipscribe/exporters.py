"""Serialize a TranscriptResult to TXT, JSON, SRT, and VTT (FR-08)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import TranscriptResult


def format_timestamp(seconds: float, sep: str = ".") -> str:
    """Format seconds as ``hh:mm:ss<sep>mmm`` (``.`` for VTT/TXT, ``,`` for SRT)."""
    if seconds < 0:
        seconds = 0.0
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def render_txt(result: TranscriptResult) -> str:
    lines = [
        f"# ClipScribe raw transcript — {result.source_filename}",
        f"# model={result.model_name} language={result.detected_language} "
        f"duration={result.media_duration_seconds}s",
        "",
    ]
    for seg in result.segments:
        flag = f"  [{','.join(seg.warning_codes)}]" if seg.warning_codes else ""
        start = format_timestamp(seg.start_seconds)
        end = format_timestamp(seg.end_seconds)
        lines.append(f"[{start} --> {end}] {seg.text}{flag}")
    return "\n".join(lines) + "\n"


def render_json(result: TranscriptResult) -> str:
    return json.dumps(asdict(result), indent=2, ensure_ascii=False) + "\n"


def render_srt(result: TranscriptResult) -> str:
    blocks = []
    for seg in result.segments:
        start = format_timestamp(seg.start_seconds, sep=",")
        end = format_timestamp(seg.end_seconds, sep=",")
        blocks.append(f"{seg.index + 1}\n{start} --> {end}\n{seg.text}\n")
    return "\n".join(blocks)


def render_vtt(result: TranscriptResult) -> str:
    blocks = ["WEBVTT\n"]
    for seg in result.segments:
        start = format_timestamp(seg.start_seconds)
        end = format_timestamp(seg.end_seconds)
        blocks.append(f"{start} --> {end}\n{seg.text}\n")
    return "\n".join(blocks)


_RENDERERS = {
    "txt": render_txt,
    "json": render_json,
    "srt": render_srt,
    "vtt": render_vtt,
}


def write_all(result: TranscriptResult, out_dir: Path) -> dict[str, Path]:
    """Write all four formats, preserving the source filename stem."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.source_filename).stem
    outputs: dict[str, Path] = {}
    for kind, render in _RENDERERS.items():
        path = out_dir / f"{stem}.{kind}"
        path.write_text(render(result), encoding="utf-8")
        outputs[kind] = path
    return outputs
