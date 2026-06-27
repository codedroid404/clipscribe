"""ClipScribe evaluation harness (M4).

Benchmarks the local ASR pipeline across clips x model sizes, capturing **metrics
only** — never transcript text, never source filenames. Prints a Markdown table and
optionally writes a JSON sidecar, so results can be committed without leaking media.

Usage:
  python scripts/evaluate.py --models base small \
      --clips "Clip A (corporate ~49s)=media/clipA.MP4" \
              "Clip B (3-min advice ~212s)=media/clipB.MP4" \
      [--out docs/evaluation/results.json]

If --clips is omitted, supported media files in media/ are auto-discovered and
labeled "Clip A", "Clip B", ... in sorted order (filenames are never printed).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from clipscribe import service
from clipscribe.media import SUPPORTED_EXTENSIONS, MediaValidationError, validate_media
from clipscribe.models import TranscriptResult

TABLE_KEYS = [
    "clip", "model", "duration_s", "processing_s", "rtf", "segments", "flagged", "warnings",
]
TABLE_HEADERS = [
    "Clip", "Model", "Duration (s)", "Processing (s)", "RTF", "Segments", "Flagged", "Warnings",
]


def metrics_row(label: str, model: str, result: TranscriptResult) -> dict:
    """Build one privacy-safe metrics row from a result (no transcript text)."""
    duration = result.media_duration_seconds or 0.0
    rtf = result.processing_seconds / duration if duration else 0.0
    flagged = sum(1 for seg in result.segments if seg.warning_codes)
    return {
        "clip": label,
        "model": model,
        "duration_s": round(duration, 1),
        "processing_s": round(result.processing_seconds, 1),
        "rtf": round(rtf, 3),
        "segments": len(result.segments),
        "flagged": flagged,
        "warnings": "; ".join(result.warnings) if result.warnings else "—",
    }


def format_table(rows: list[dict]) -> str:
    """Render metrics rows as a GitHub-flavored Markdown table (pure)."""
    lines = [
        "| " + " | ".join(TABLE_HEADERS) + " |",
        "| " + " | ".join("---" for _ in TABLE_HEADERS) + " |",
    ]
    for r in rows:
        lines.append("| " + " | ".join(str(r[k]) for k in TABLE_KEYS) + " |")
    return "\n".join(lines)


def run_clip(label: str, path: Path, model: str) -> dict:
    """Transcribe one clip with one model and return its metrics row."""
    result = service.run_pipeline(path, model_name=model)
    return metrics_row(label, model, result)


def robustness_checks() -> list[tuple[str, str]]:
    """Exercise invalid inputs and capture the actionable error (no media needed)."""
    out: list[tuple[str, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        cases = {
            "Corrupt container (.mp4)": (d / "corrupt.mp4", b"not a real mp4 container"),
            "Empty file (.wav)": (d / "empty.wav", b""),
            "Unsupported type (.txt)": (d / "notes.txt", b"hello"),
        }
        for case, (p, data) in cases.items():
            p.write_bytes(data)
            try:
                validate_media(p)
                out.append((case, "UNEXPECTEDLY ACCEPTED"))
            except MediaValidationError as exc:
                # strip any temp path so the message is safe to commit
                msg = str(exc).replace(str(d), "<tmp>").replace(p.name, p.name)
                out.append((case, msg))
    return out


def _parse_clips(specs: list[str] | None) -> list[tuple[str, Path]]:
    if specs:
        clips = []
        for spec in specs:
            label, _, path = spec.partition("=")
            clips.append((label.strip(), Path(path.strip())))
        return clips
    media = Path("media")
    found = sorted(p for p in media.glob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS) \
        if media.exists() else []
    return [(f"Clip {chr(65 + i)}", p) for i, p in enumerate(found)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ClipScribe evaluation harness")
    parser.add_argument("--models", nargs="+", default=["base", "small"])
    parser.add_argument("--clips", nargs="*", help='Entries like "Label=path/to/clip.mp4"')
    parser.add_argument("--out", type=Path, default=None, help="Write JSON results here")
    args = parser.parse_args(argv)

    clips = _parse_clips(args.clips)
    if not clips:
        print("error: no clips found (pass --clips or add media to media/)", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for label, path in clips:
        if not path.exists():
            print(f"warning: skipping missing clip: {label}", file=sys.stderr)
            continue
        for model in args.models:
            print(f"… {label} × {model}", file=sys.stderr)
            rows.append(run_clip(label, path, model))

    print("\n### Transcription benchmark\n")
    print(format_table(rows))
    print("\n### Robustness (invalid inputs)\n")
    print("| Case | Result |\n| --- | --- |")
    for case, msg in robustness_checks():
        print(f"| {case} | {msg} |")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
