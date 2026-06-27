"""Uncertainty, repetition, and no-speech diagnostics.

Implements the plan's hallucination-mitigation strategy (§7) and FR-09: flag
low-confidence, no-speech, repeated, and looping segments so the user can review
them. Diagnostics never rewrite or remove text — they only annotate.
"""

from __future__ import annotations

from .models import TranscriptResult, TranscriptSegment

# Conservative thresholds. Tunable in later milestones with golden-set evidence.
LOW_CONFIDENCE_LOGPROB = -1.0
NO_SPEECH_THRESHOLD = 0.6
MIN_CONSECUTIVE_REPEATS = 4  # e.g. "yeah yeah yeah yeah" within one segment

# Warning codes
NO_SPEECH = "no_speech"
LOW_CONFIDENCE = "low_confidence"
REPETITION = "repetition"
REPEATED_SEGMENT = "repeated_segment"


def _normalize(text: str) -> str:
    lowered = text.lower()
    kept = (ch if (ch.isalnum() or ch.isspace()) else " " for ch in lowered)
    return " ".join("".join(kept).split())


def is_internally_repetitive(text: str, min_repeats: int = MIN_CONSECUTIVE_REPEATS) -> bool:
    """True if a word or bigram repeats consecutively at least ``min_repeats`` times."""
    words = _normalize(text).split()
    if len(words) < min_repeats:
        return False

    # consecutive identical words
    run = 1
    for a, b in zip(words, words[1:], strict=False):
        run = run + 1 if a == b else 1
        if run >= min_repeats:
            return True

    # consecutive identical bigrams ("na na" repeated)
    bigrams = [f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1)]
    run = 1
    for a, b in zip(bigrams, bigrams[2:], strict=False):  # compare aligned bigrams
        run = run + 1 if a == b else 1
        if run >= min_repeats:
            return True

    return False


def segment_warnings(segment: TranscriptSegment, previous_norm: str | None) -> list[str]:
    codes: list[str] = []
    if segment.no_speech_prob is not None and segment.no_speech_prob >= NO_SPEECH_THRESHOLD:
        codes.append(NO_SPEECH)
    if segment.avg_logprob is not None and segment.avg_logprob < LOW_CONFIDENCE_LOGPROB:
        codes.append(LOW_CONFIDENCE)
    if is_internally_repetitive(segment.text):
        codes.append(REPETITION)
    norm = _normalize(segment.text)
    if norm and norm == previous_norm:
        codes.append(REPEATED_SEGMENT)
    return codes


def analyze(result: TranscriptResult) -> TranscriptResult:
    """Annotate each segment's ``warning_codes`` and aggregate ``result.warnings``.

    Mutates and returns the same ``TranscriptResult``.
    """
    previous_norm: str | None = None
    seen: set[str] = set()
    for segment in result.segments:
        codes = segment_warnings(segment, previous_norm)
        segment.warning_codes = codes
        seen.update(codes)
        previous_norm = _normalize(segment.text)

    warnings: list[str] = []
    if not result.segments:
        warnings.append("no_segments_detected")
    if LOW_CONFIDENCE in seen:
        warnings.append("contains_low_confidence_segments")
    if NO_SPEECH in seen:
        warnings.append("contains_no_speech_segments")
    if REPETITION in seen or REPEATED_SEGMENT in seen:
        warnings.append("contains_repeated_or_looping_segments")
    result.warnings = warnings
    return result
