"""Unit tests for the WER / normalization verification helpers."""

from clipscribe.cli import compute_wer, normalize_text


def test_normalize_text_strips_punctuation_and_case():
    assert normalize_text("Hello, WORLD!  It's me.") == "hello world it s me"


def test_compute_wer_identical_is_zero():
    metrics = compute_wer("Tell me about yourself", "tell me, about yourself!")
    assert metrics["wer"] == 0.0
    assert metrics["substitutions"] == 0
    assert metrics["reference_words"] == 4


def test_compute_wer_one_substitution():
    metrics = compute_wer("the quick brown fox", "the quick green fox")
    assert metrics["substitutions"] == 1
    assert metrics["wer"] == 0.25  # 1 error / 4 reference words
