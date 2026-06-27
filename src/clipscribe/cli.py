"""ClipScribe command-line interface (thin presentation layer over service).

Parses arguments, invokes the transcription service, prints a concise summary,
and optionally reports word error rate against a reference transcript. All
pipeline logic lives in the service / media / transcriber / diagnostics /
exporters modules.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import service
from .media import MediaValidationError
from .models import TranscriptResult


# --------------------------------------------------------------------------- #
# Verification helpers (used only with --reference)
# --------------------------------------------------------------------------- #
def normalize_text(text: str) -> str:
    """Lowercase, drop punctuation, and collapse whitespace for fair WER."""
    lowered = text.lower()
    kept = (ch if (ch.isalnum() or ch.isspace()) else " " for ch in lowered)
    return " ".join("".join(kept).split())


def compute_wer(reference: str, hypothesis: str) -> dict[str, float | int]:
    """Word error rate and S/I/D counts between two transcripts (jiwer)."""
    import jiwer

    ref = normalize_text(reference)
    hyp = normalize_text(hypothesis)
    measures = jiwer.process_words([ref], [hyp])
    return {
        "wer": measures.wer,
        "substitutions": measures.substitutions,
        "insertions": measures.insertions,
        "deletions": measures.deletions,
        "hits": measures.hits,
        "reference_words": len(ref.split()),
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clipscribe",
        description="Transcribe a local media file with faster-whisper (local, no API key).",
    )
    parser.add_argument("input", type=Path, help="Path to a .mov/.mp4/.m4a/.mp3/.wav file")
    parser.add_argument("--model", default="base", help="faster-whisper model size (default: base)")
    parser.add_argument(
        "--language",
        default="auto",
        help="Language code (e.g. 'en') or 'auto' to detect (default: auto)",
    )
    parser.add_argument("--vad", action="store_true", help="Enable voice activity detection")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("transcripts"),
        help="Output directory (default: transcripts/)",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="Optional reference transcript (.txt) to compute word error rate",
    )
    parser.add_argument(
        "--save", action="store_true", help="Save the transcript to the local library"
    )
    parser.add_argument(
        "--title", default=None, help="Title for the saved transcript (with --save)"
    )
    return parser


def _print_summary(result: TranscriptResult, outputs: dict[str, Path]) -> None:
    duration = result.media_duration_seconds
    rtf = result.processing_seconds / duration if duration and duration > 0 else None
    print("")
    if result.language_probability is not None:
        print(f"  language     : {result.detected_language} (p={result.language_probability:.2f})")
    else:
        print(f"  language     : {result.detected_language}")
    print(f"  duration     : {duration}s")
    print(f"  processing   : {result.processing_seconds}s")
    print(f"  real-time x  : {rtf:.2f}" if rtf is not None else "  real-time x  : n/a")
    print(f"  segments     : {len(result.segments)}")
    if result.warnings:
        print(f"  warnings     : {', '.join(result.warnings)}")
    for kind in ("txt", "json", "srt", "vtt"):
        print(f"  {kind.upper():<4}         : {outputs[kind]}")


def _maybe_verify(result: TranscriptResult, reference: Path | None) -> None:
    if reference is None:
        print("\n  (no --reference provided: verify the transcript manually via timestamps)")
        return
    if not reference.exists():
        print(f"\nwarning: reference not found: {reference}", file=sys.stderr)
        return
    reference_text = reference.read_text(encoding="utf-8")
    hypothesis_text = " ".join(seg.text for seg in result.segments)
    metrics = compute_wer(reference_text, hypothesis_text)
    print("\n  --- verification (WER) ---")
    print(f"  WER          : {metrics['wer']:.3f}")
    print(f"  S / I / D    : {metrics['substitutions']} / "
          f"{metrics['insertions']} / {metrics['deletions']}")
    print(f"  ref words    : {metrics['reference_words']}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    language = None if args.language.lower() == "auto" else args.language

    print(f"Transcribing {args.input.name} with model '{args.model}' (CPU/int8)...")
    try:
        result, outputs = service.transcribe_file(
            args.input,
            model_name=args.model,
            language=language,
            use_vad=args.vad,
            out_dir=args.out,
        )
    except MediaValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # actionable error instead of a raw traceback
        print(f"error: transcription failed: {exc}", file=sys.stderr)
        return 1

    _print_summary(result, outputs)
    _maybe_verify(result, args.reference)

    if args.save:
        from . import storage

        transcript_id = storage.save_transcript(result, args.title or result.source_filename)
        print(f"\n  saved to library: id {transcript_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
