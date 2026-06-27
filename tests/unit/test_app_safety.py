"""Unit tests for the app's privacy/safety helpers (remediation evidence)."""

import app


def test_escape_md_neutralizes_markup():
    out = app._escape_md("**bold** [x](y) <b>h</b> `c` | p")
    # Markdown/HTML special characters are backslash-escaped...
    for token in ["\\*", "\\[", "\\]", "\\<", "\\>", "\\`", "\\|"]:
        assert token in out
    # ...so no live emphasis/code remains.
    assert "**bold**" not in out
    assert "`c`" not in out


def test_safe_display_name_strips_path_and_bounds_length():
    assert app._safe_display_name("../../etc/passwd") == "passwd"      # no traversal
    assert app._safe_display_name("/abs/path/clip.mp4") == "clip.mp4"  # basename only
    assert len(app._safe_display_name("x" * 300)) <= 120               # length-bounded
    assert app._safe_display_name("") == "uploaded-clip"               # fallback


def test_warning_labels_are_human_readable():
    assert app.WARNING_LABELS["contains_low_confidence_segments"].startswith("Some segments")
    assert app.SEGMENT_FLAG_LABELS["no_speech"] == "possible silence"
