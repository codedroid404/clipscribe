"""ClipScribe — Streamlit MVP (presentation layer only).

Upload a short screen recording, transcribe it locally with faster-whisper,
review the raw timestamped transcript with uncertainty warnings, and download
TXT / JSON / SRT / VTT. All pipeline logic lives in `clipscribe.service`.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from clipscribe import exporters, llm, service, storage
from clipscribe.exporters import format_timestamp
from clipscribe.media import SUPPORTED_EXTENSIONS, MediaValidationError
from clipscribe.tempfiles import temporary_workspace

load_dotenv()  # load optional hosted-chat config (.env) for M8; no-op if absent

# model id -> friendly label shown in the dropdown
MODEL_LABELS = {
    "tiny": "Tiny — fastest, least accurate (~75 MB)",
    "base": "Base — fast, good for clear speech (~145 MB)",
    "small": "Small — slower, more accurate · recommended (~480 MB)",
    "medium": "Medium — slowest, most accurate (~1.5 GB)",
}
UPLOAD_TYPES = ["mov", "mp4", "m4a", "mp3", "wav"]

# Hosted-LLM model choices for the ✨ AI-title feature (the one opt-in cloud touch).
AI_MODELS = {
    "Claude Opus 4.8 — most capable": "claude-opus-4-8",
    "Claude Sonnet 4.6 — balanced": "claude-sonnet-4-6",
    "Claude Haiku 4.5 — fast & cheap": "claude-haiku-4-5",
}

ASSETS = Path(__file__).parent / "docs" / "assets"
LOGO = str(ASSETS / "clipscribe-logo.svg")
MARK = str(ASSETS / "clipscribe-mark.svg")

# Selectable background tints — a small built-in theme switcher (sidebar).
TINTS = {
    # ── Original ──
    "Teal-gray": {"bg": "#e8f1ef", "sidebar": "#dfece9"},
    "Mint": {"bg": "#d4e9e4", "sidebar": "#c8e3dc"},
    "Sage": {"bg": "#e6f0e6", "sidebar": "#dce8da"},
    "Cool mist": {"bg": "#e1edf0", "sidebar": "#d9e8ec"},
    # ── Soft (gentle color) ──
    "Rose quartz": {"bg": "#f3e9ec", "sidebar": "#ecdfe3"},  # warm pink
    "Butter": {"bg": "#f4efdf", "sidebar": "#ece6d2"},  # cream-yellow
    "Lilac": {"bg": "#ece8f4", "sidebar": "#e2ddee"},  # cool lilac
    "Sky": {"bg": "#e4eef7", "sidebar": "#d8e6f2"},  # airy blue
    "Peach": {"bg": "#f6ebe3", "sidebar": "#efe0d4"},  # soft peach
    "Spring sage": {"bg": "#e6efe0", "sidebar": "#dbe7d3"},  # fresh light green
    # ── Mid (more presence) ──
    "Dusty blue": {"bg": "#d8e3ee", "sidebar": "#cbd9e8"},  # muted denim
    "Muted teal": {"bg": "#d3e6e2", "sidebar": "#c6ddd8"},  # cohesive w/ accent
    "Clay": {"bg": "#ecdfd6", "sidebar": "#e2d2c6"},  # terracotta-beige
    "Sage olive": {"bg": "#e1e6d4", "sidebar": "#d6dcc6"},  # gray-green
    "Mauve": {"bg": "#e8dde4", "sidebar": "#ddccd6"},  # purple-gray
    # ── Bold (white cards pop hardest) ──
    "Deep sage": {"bg": "#cdddd3", "sidebar": "#bfd2c7"},  # rich green
    "Slate blue": {"bg": "#cdd8e4", "sidebar": "#bfccdb"},  # blue-gray
    "Warm taupe": {"bg": "#e0d4c6", "sidebar": "#d4c5b4"},  # warm greige
    "Storm gray": {"bg": "#d6dadf", "sidebar": "#c8cdd4"},  # cool neutral
}
DEFAULT_TINT = "Teal-gray"

st.set_page_config(page_title="ClipScribe", page_icon="🎙️", layout="wide")

# Light custom CSS for the final 10% of polish. NOTE: the [data-testid] selectors
# below are version-sensitive (Streamlit internals) — keep this block small.
_CSS = """
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 4rem; max-width: 1100px; }
/* White cards float on the soft tinted canvas for depth */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15,23,42,0.07);
}
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }
/* The top header bar is empty now — make it transparent so the tint shows through */
[data-testid="stHeader"] { background: transparent; }
.stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
h1, h2, h3 { letter-spacing: -0.01em; }
</style>
"""


# --------------------------------------------------------------------------- #
# Logging — technical events + timings only, never transcript text (NFR-07)
# --------------------------------------------------------------------------- #
class _ColorFormatter(logging.Formatter):
    """Colorize console log lines by level."""

    _COLORS = {
        logging.DEBUG: "\033[36m",       # cyan
        logging.INFO: "\033[32m",        # green
        logging.WARNING: "\033[33m",     # yellow
        logging.ERROR: "\033[31m",       # red
        logging.CRITICAL: "\033[1;31m",  # bold red
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        return f"{self._COLORS.get(record.levelno, '')}{line}{self._RESET}"


def _get_logger() -> logging.Logger:
    """Return the app logger, attaching a color handler once (reruns re-import)."""
    logger = logging.getLogger("clipscribe.app")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            _ColorFormatter(
                "%(asctime)s | %(levelname)-7s | clipscribe | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


log = _get_logger()


# --------------------------------------------------------------------------- #
# Safe rendering + human-readable diagnostic labels
# --------------------------------------------------------------------------- #
# Neutralize Markdown/HTML so transcript text renders literally (never as
# headings, links, code, emphasis, or markup).
_MD_SPECIALS = re.compile(r"([\\`*_{}\[\]<>|])")


def _escape_md(text: str) -> str:
    return _MD_SPECIALS.sub(r"\\\1", text)


def _safe_display_name(name: str) -> str:
    """A display-only filename: basename, length-bounded, never used as a path."""
    base = Path(name).name.strip()
    return base[:120] if base else "uploaded-clip"


def _list_media_files() -> list[Path]:
    """Supported media already present in local media/ (for the picker)."""
    media = Path("media")
    if not media.exists():
        return []
    return sorted(
        p for p in media.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


# Aggregate result.warnings -> readable text
WARNING_LABELS = {
    "no_segments_detected": "No speech detected in this clip",
    "contains_low_confidence_segments": "Some segments have low model certainty",
    "contains_no_speech_segments": "Some segments may be silence or non-speech",
    "contains_repeated_or_looping_segments": "Some segments repeat — possible looping",
}
# Per-segment warning_codes -> short readable label
SEGMENT_FLAG_LABELS = {
    "low_confidence": "low certainty",
    "no_speech": "possible silence",
    "repetition": "repeated words",
    "repeated_segment": "repeats previous",
}


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def _settings() -> tuple[str, str | None, bool]:
    """Render sidebar controls and return (model, language, use_vad)."""
    with st.sidebar:
        st.markdown("### :material/tune: Settings")
        model = st.selectbox(
            "Model size",
            list(MODEL_LABELS),
            index=list(MODEL_LABELS).index("small"),
            format_func=lambda m: MODEL_LABELS[m],
            help=(
                "Bigger models are more accurate but slower and download more on first "
                "use. All run locally on your CPU. Small is the default (fewer quality "
                "flags than Base); drop to Base/Tiny for speed."
            ),
        )
        st.caption(
            ":material/cloud_download: First use of a model downloads it once, then works offline."
        )

        mode = st.segmented_control(
            "Language", ["Auto-detect", "Specify"], default="Auto-detect"
        )
        language = None
        if mode == "Specify":
            code = st.text_input("Language code (e.g. en, es, fr)", value="en").strip()
            language = code or None

        use_vad = st.toggle(
            "Voice activity detection (VAD)",
            value=False,
            help="Skips non-speech regions; can reduce hallucinated text during silence/music.",
        )

        st.divider()
        st.markdown(":material/auto_awesome: **Hosted AI** (for ✨ AI title)")
        ai_label = st.selectbox(
            "Model for the ✨ AI title",
            list(AI_MODELS),
            index=list(AI_MODELS.values()).index("claude-haiku-4-5"),  # cheapest by default
            key="ai_model_label",
            help=(
                "Used only for the optional ✨ AI-title button. Needs ANTHROPIC_API_KEY in "
                ".env; transcription itself always stays local."
            ),
        )
        st.session_state["ai_model"] = AI_MODELS[ai_label]
        usage = st.session_state.get("ai_usage")
        if usage and usage["calls"]:
            st.caption(
                f":material/receipt_long: {usage['calls']} call(s) · "
                f"{usage['in'] + usage['out']:,} tokens · ~${usage['cost']:.4f} this session"
            )
            if st.button(
                ":material/restart_alt: Reset usage", key="reset_usage", width="stretch"
            ):
                st.session_state.pop("ai_usage", None)
                st.rerun()
        else:
            st.caption(":material/receipt_long: No AI calls yet this session.")

        st.divider()
        st.markdown(":material/palette: **Appearance**")
        st.selectbox(
            "Background tint",
            list(TINTS),
            index=list(TINTS).index(DEFAULT_TINT),
            key="tint",
            help="Pick the app background color. Your choice persists during the session.",
        )

        st.divider()
        with st.expander(":material/info: About ClipScribe", expanded=True):
            st.markdown(
                "- **Local ASR** — runs on your machine, no API key, nothing uploaded.\n"
                "- The **raw transcript** is the source of truth; it is never rewritten "
                "by an LLM.\n"
                "- Uncertain / no-speech / repeated segments are **flagged**, not guessed.\n"
                "- Uploaded media is processed in a temporary folder and **deleted** after.\n"
                "- Built by **Sita Sanon** — [GitHub](https://github.com/codedroid404)"
            )
    return model, language, use_vad


# --------------------------------------------------------------------------- #
# Result rendering
# --------------------------------------------------------------------------- #
def _render_summary(result) -> None:
    duration = result.media_duration_seconds
    rtf = result.processing_seconds / duration if duration and duration > 0 else None
    cols = st.columns(4, gap="medium", border=True)
    cols[0].metric("Language", (result.detected_language or "?").upper())
    cols[1].metric("Duration", f"{duration:.0f}s" if duration else "?")
    cols[2].metric("Processing", f"{result.processing_seconds:.1f}s")
    cols[3].metric(
        "Real-time ×", f"{rtf:.2f}" if rtf is not None else "n/a",
        help="Processing time ÷ audio duration. Below 1.0 is faster than real time.",
    )
    if result.warnings:
        labels = [WARNING_LABELS.get(w, w) for w in result.warnings]
        st.markdown(" ".join(f":orange-badge[:material/warning: {x}]" for x in labels))
        st.caption(
            "Heuristic signals — replay the flagged timestamps below to check by ear."
        )
    else:
        st.markdown(":green-badge[:material/check_circle: No quality flags]")


def _render_reading(result) -> None:
    st.caption(
        "Raw ASR output — not cleaned or rewritten by an LLM. Flagged segments may be "
        "uncertain; replay them by ear using the timestamps."
    )
    lines = []
    for seg in result.segments:
        ts = f"{format_timestamp(seg.start_seconds)} → {format_timestamp(seg.end_seconds)}"
        icon = ":material/warning:" if seg.warning_codes else ":material/schedule:"
        flags = [SEGMENT_FLAG_LABELS.get(c, c) for c in seg.warning_codes]
        badges = " ".join(f":orange-badge[{name}]" for name in flags)
        lines.append(f"{icon} :gray-background[`{ts}`]  {_escape_md(seg.text)}  {badges}".rstrip())
    st.markdown("\n\n".join(lines) if lines else "_No speech segments detected._")


def _render_table(result) -> None:
    rows = [
        {
            "#": seg.index + 1,
            "Start": format_timestamp(seg.start_seconds),
            "End": format_timestamp(seg.end_seconds),
            "Text": seg.text,
            "Flags": ", ".join(SEGMENT_FLAG_LABELS.get(c, c) for c in seg.warning_codes),
        }
        for seg in result.segments
    ]
    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        column_config={
            "#": st.column_config.NumberColumn(width="small"),
            "Text": st.column_config.TextColumn(width="large"),
            "Flags": st.column_config.TextColumn(help="Diagnostic warning codes"),
        },
    )
    st.caption(f"{len(rows)} segments")


def _render_readable(result) -> None:
    st.caption(
        "The same words as the raw transcript, with timestamps and flags removed for "
        "easy reading and copying. Not an LLM rewrite — no words are added or changed."
    )
    text = " ".join(seg.text.strip() for seg in result.segments).strip()
    if not text:
        st.info("No speech detected.")
        return
    with st.container(border=True):
        # Plain-text display: transcript words render exactly, never as markup.
        st.text(text)


def _download_buttons(result) -> None:
    stem = Path(result.source_filename).stem
    specs = [
        ("TXT", exporters.render_txt, "txt", "text/plain"),
        ("JSON", exporters.render_json, "json", "application/json"),
        ("SRT", exporters.render_srt, "srt", "application/x-subrip"),
        ("VTT", exporters.render_vtt, "vtt", "text/vtt"),
    ]
    for label, render, ext, mime in specs:
        st.download_button(
            f":material/download: {label}",
            data=render(result),
            file_name=f"{stem}.{ext}",
            mime=mime,
            width="stretch",
        )


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
def _empty_state() -> None:
    with st.container(border=True):
        st.markdown("#### :material/mic: Start a transcription")
        st.markdown(
            "Upload a screen recording or audio clip — **MOV, MP4, M4A, MP3, WAV**. "
            "Pick a model in the sidebar (**Small** is a good balance), then click "
            "**Transcribe**."
        )


def _render_library(input_sig) -> None:
    """Saved-transcript library: list, open, delete (M6)."""
    entries = storage.list_transcripts()
    with st.expander(f":material/library_books: Library ({len(entries)})", expanded=False):
        if not entries:
            st.caption("No saved transcripts yet — transcribe a clip and click “Save to library”.")
            return
        for entry in entries:
            c1, c2, c3 = st.columns([6, 1, 1], vertical_alignment="center")
            c1.markdown(
                f"**{_escape_md(entry.title)}**  \n"
                f":small[{entry.segment_count} segments · {entry.language or '?'} · "
                f"{entry.created[:10]}]"
            )
            if c2.button("Open", key=f"open_{entry.id}", width="stretch"):
                stored = storage.get_transcript(entry.id)
                if stored is not None:
                    _reset_result_state()
                    st.session_state["result"] = storage.stored_to_result(stored)
                    st.session_state["result_sig"] = input_sig
                    st.session_state["result_library_id"] = entry.id  # opened from library
                    st.rerun()
            if c3.button("Delete", key=f"del_{entry.id}", width="stretch"):
                if st.session_state.get("result_library_id") == entry.id:
                    _reset_result_state()
                storage.delete_transcript(entry.id)
                st.rerun()

        st.divider()
        if not st.session_state.get("confirm_clear_library"):
            if st.button(
                ":material/delete_sweep: Delete all", key="lib_clear",
                help="Permanently remove every saved transcript.",
            ):
                st.session_state["confirm_clear_library"] = True
                st.rerun()
        else:
            st.warning(f"Delete all **{len(entries)}** saved transcript(s)? This can't be undone.")
            c_yes, c_no = st.columns(2)
            if c_yes.button(
                ":material/delete_forever: Yes, delete all", key="lib_clear_yes",
                type="primary", width="stretch",
            ):
                removed = storage.delete_all_transcripts()
                st.session_state.pop("confirm_clear_library", None)
                _reset_result_state()
                log.info("Library cleared: removed=%d", removed)
                st.toast(f"Deleted {removed} transcript(s)", icon=":material/delete_sweep:")
                st.rerun()
            if c_no.button("Cancel", key="lib_clear_no", width="stretch"):
                st.session_state.pop("confirm_clear_library", None)
                st.rerun()


def _reset_title() -> None:
    """Drop the cached title so the next result re-derives its auto-suggested title."""
    st.session_state.pop("save_title_value", None)
    st.session_state["title_version"] = st.session_state.get("title_version", 0) + 1


def _reset_result_state() -> None:
    """Clear all state tied to the *current* result so a new one starts clean.

    Centralized so the transcribe / library-open / stale-change paths can't drift
    (callers set the fresh ``result`` / ``result_sig`` afterwards).
    """
    for key in ("result", "result_sig", "result_library_id", "ask_messages", "ask_sources"):
        st.session_state.pop(key, None)
    _reset_title()


def _provider():
    """Build the hosted provider once for this run, or None if no API key is configured."""
    try:
        return llm.AnthropicProvider(model=st.session_state.get("ai_model"))
    except llm.ProviderNotConfigured:
        return None


def _render_save(result, provider) -> None:
    lib_id = st.session_state.get("result_library_id")
    if lib_id:
        st.caption(
            f":material/check_circle: This transcript is in your library (id `{lib_id[:8]}…`)."
        )
        return
    readable = " ".join(s.text.strip() for s in result.segments)
    # Source of truth for the title; the text_input below mirrors it. The AI-title
    # button updates this value and bumps `title_version`, which changes the widget
    # key so the input reliably re-initializes with the new value (the
    # set-session_state-before-widget trick is unreliable across reruns).
    if "save_title_value" not in st.session_state:
        st.session_state["save_title_value"] = (
            storage.suggest_title(readable)
            if readable.strip()
            else (Path(result.source_filename).stem or "Untitled")
        )
    version = st.session_state.get("title_version", 0)
    with st.container(border=True):
        st.markdown("**:material/bookmark_add: Save to library**")
        c_title, c_ai, c_save = st.columns([5, 1.3, 1], vertical_alignment="bottom")
        title = c_title.text_input(
            "Title (auto-suggested — edit if you like)",
            value=st.session_state["save_title_value"],
            key=f"save_title_{version}",
        )
        st.session_state["save_title_value"] = title
        if c_ai.button(
            "✨ AI title", key="ai_title_btn", width="stretch",
            disabled=provider is None,
            help=(
                "Sends this transcript to the hosted LLM to generate a concise title."
                if provider is not None
                else "Add ANTHROPIC_API_KEY (.env) to use AI titles."
            ),
        ):
            try:
                with st.spinner("Generating title…"):
                    suggestion = llm.suggest_title_llm(result.segments, provider=provider)
                _record_ai_usage(provider)
                st.session_state["save_title_value"] = suggestion
                st.session_state["title_version"] = version + 1  # new key → input refreshes
                st.toast(f"AI title: {suggestion}", icon="✨")
                st.rerun()
            except Exception as exc:
                _chat_error(exc)
        if c_save.button(":material/save: Save", key="save_btn", width="stretch"):
            transcript_id = storage.save_transcript(result, title)
            st.session_state["result_library_id"] = transcript_id
            st.success(f"Saved “{title}” to your library.")
            st.rerun()


def _chat_error(exc: Exception) -> None:
    import anthropic

    if isinstance(exc, anthropic.AuthenticationError):
        st.error("Authentication failed — check ANTHROPIC_API_KEY in your .env.")
    elif isinstance(exc, anthropic.RateLimitError):
        st.error("The provider rate-limited the request. Wait a moment and try again.")
    elif isinstance(exc, anthropic.APIConnectionError):
        st.error("Could not reach the provider. Check your network connection.")
    else:
        st.error("The hosted request failed. Technical details are in the server logs.")
    log.error("Hosted chat failed: %s", type(exc).__name__)


def _record_ai_usage(provider) -> None:
    """Accumulate this session's hosted-call count, tokens, and estimated cost."""
    in_tok, out_tok = getattr(provider, "last_usage", (0, 0))
    usage = st.session_state.setdefault("ai_usage", {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
    usage["calls"] += 1
    usage["in"] += in_tok
    usage["out"] += out_tok
    usage["cost"] += llm.call_cost(provider.model, in_tok, out_tok)


def _mix(hex_a: str, hex_b: str, t: float) -> str:
    """Linearly blend two #rrggbb colors (t=0 → hex_a, t=1 → hex_b)."""
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    r, g, bl = (round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return f"#{r:02x}{g:02x}{bl:02x}"


def _tint_tokens(bg: str) -> dict[str, str]:
    """Neutral border + fill derived from the active tint so they always harmonize."""
    return {
        "border": _mix(bg, "#0f172a", 0.12),  # bg nudged toward the dark text color
        "fill": _mix(bg, "#ffffff", 0.45),    # bg lightened toward white
    }


def _tint_css(name: str) -> str:
    """Recolor the canvas + sidebar, deriving neutral border/fill from the tint.

    Only the neutrals track the tint. The teal accent (#0d9488), white cards (#ffffff),
    and dark text (#0f172a) stay fixed — so e.g. the upload drop-zone reads neutral on a
    gray tint instead of looking green.
    """
    t = TINTS.get(name, TINTS[DEFAULT_TINT])
    bg, sidebar = t["bg"], t["sidebar"]
    tok = _tint_tokens(bg)
    border, fill = tok["border"], tok["fill"]
    return (
        "<style>"
        f".stApp{{background-color:{bg} !important;}}"
        # tint the top header bar too, so there's no white gap above the title
        f'[data-testid="stHeader"]{{background-color:{bg} !important;}}'
        f'[data-testid="stSidebar"]{{background-color:{sidebar} !important;}}'
        # neutral borders + fills derived from the active tint
        f'[data-testid="stVerticalBlockBorderWrapper"]{{border-color:{border} !important;}}'
        f'[data-testid="stFileUploaderDropzone"]{{border:1.5px dashed {border} !important;'
        f"background:{fill} !important;}}"
        f'[data-baseweb="input"],[data-baseweb="select"]>div{{border-color:{border} !important;}}'
        "</style>"
    )


def _render_transcribe(model: str, language: str | None, use_vad: bool, provider) -> None:
    if st.session_state.get("result") is None:
        _empty_state()

    with st.container(border=True):
        st.markdown("#### :material/upload: Upload")
        uploaded = st.file_uploader(
            "Screen recording or audio clip",
            type=UPLOAD_TYPES,
            help="Supported: .mov .mp4 .m4a .mp3 .wav",
            label_visibility="collapsed",
        )
        media_choice = None
        media_files = _list_media_files()
        if media_files:
            pick = st.selectbox(
                "…or pick a file already in media/",
                ["—"] + [p.name for p in media_files],
                index=0,
                key="media_pick",
                help="Transcribe a local file from media/ without re-uploading.",
            )
            if pick != "—":
                media_choice = next((p for p in media_files if p.name == pick), None)

        # Unify the two input sources. An upload takes priority over a media pick.
        if uploaded is not None:
            source = ("upload", uploaded, uploaded.name)
        elif media_choice is not None:
            source = ("media", media_choice, media_choice.name)
        else:
            source = None

        transcribe = st.button(
            ":material/graphic_eq: Transcribe", type="primary", disabled=source is None
        )

    # Clear a stale result when the input or key settings change, so an old transcript
    # never appears to belong to a new input. Library-loaded results (no source) stay.
    if source is None:
        file_key = None
    elif source[0] == "upload":
        u = source[1]
        file_key = getattr(u, "file_id", None) or (u.name, u.size)
    else:
        file_key = ("media", str(source[1]))
    input_sig = (file_key, model, language, use_vad)
    if (
        source is not None
        and st.session_state.get("result") is not None
        and st.session_state.get("result_sig") != input_sig
    ):
        _reset_result_state()

    if transcribe and source is not None:
        source_kind, source_obj, display_name = source
        if source_kind == "upload":
            ext, size_mb = Path(source_obj.name).suffix.lower(), source_obj.size / 1_048_576
        else:
            ext, size_mb = source_obj.suffix.lower(), source_obj.stat().st_size / 1_048_576
        # Log technical metadata only — never the filename or transcript text.
        log.info(
            "Transcription requested: source=%s ext=%s size=%.1fMB | model=%s language=%s vad=%s",
            source_kind, ext or "unknown", size_mb, model, language or "auto", use_vad,
        )
        with st.status("Transcribing locally…", expanded=True) as status:
            try:
                st.write(":material/check: Validating media and extracting audio…")
                st.write(f":material/graphic_eq: Running faster-whisper ({model})…")
                if source_kind == "upload":
                    # Randomized workspace + fixed internal stem + validated suffix:
                    # the uploaded filename never controls the on-disk path.
                    with temporary_workspace() as workspace:
                        suffix = (Path(source_obj.name).suffix.lower() or ".bin")[:10]
                        tmp_path = workspace / f"upload{suffix}"
                        tmp_path.write_bytes(source_obj.getbuffer())
                        result = service.run_pipeline(
                            tmp_path, model_name=model, language=language, use_vad=use_vad
                        )
                    log.info("Temporary media cleaned up")
                else:
                    # Local media/ file — read directly; never copied, moved, or deleted.
                    result = service.run_pipeline(
                        source_obj, model_name=model, language=language, use_vad=use_vad
                    )
                # The original name is shown to the user but is display-only.
                result.source_filename = _safe_display_name(display_name)
                duration = result.media_duration_seconds or 0
                rtf = result.processing_seconds / duration if duration else 0
                log.info(
                    "Transcription done: %.2fs | language=%s | segments=%d | real-time x=%.2f",
                    result.processing_seconds, result.detected_language,
                    len(result.segments), rtf,
                )
                if result.warnings:
                    log.warning("Quality flags: %s", ", ".join(result.warnings))
                _reset_result_state()  # clear old chat/title/saved-state before the new result
                st.session_state["result"] = result
                st.session_state["result_sig"] = input_sig
                status.update(label="Transcription complete", state="complete", expanded=False)
                st.toast("Transcription complete", icon=":material/check_circle:")
            except MediaValidationError as exc:
                log.error("Validation failed: %s", exc)
                st.session_state.pop("result", None)
                status.update(label="Could not transcribe this file", state="error")
                st.error(f"Cannot transcribe this file: {exc}")
            except Exception:  # log details safely; show an actionable message
                log.exception("Transcription failed")
                st.session_state.pop("result", None)
                status.update(label="Transcription failed", state="error")
                st.error(
                    "Transcription failed while processing this file. This can happen if the "
                    "model could not load or the audio could not be decoded. Try a smaller "
                    "model or a different clip — technical details are in the server logs."
                )

    result = st.session_state.get("result")
    if result is not None:
        st.divider()
        head_left, head_right = st.columns([3, 1], vertical_alignment="center")
        with head_left:
            st.markdown(
                f"**:material/description: {_escape_md(result.source_filename)}** "
                f"· model :blue-badge[{result.model_name}]"
            )
        with head_right:
            with st.popover(":material/download: Download", width="stretch"):
                _download_buttons(result)

        _render_summary(result)
        _render_save(result, provider)
        # Lead with the human-readable transcript; raw/technical views collapse below
        # (closed unless expanded), Timestamped last.
        st.markdown("**:material/menu_book: Readable**")
        _render_readable(result)
        with st.expander(":material/table: Segments", expanded=False):
            _render_table(result)
        with st.expander(":material/schedule: Timestamped", expanded=False):
            _render_reading(result)

    _render_library(input_sig)


def _render_ai_skeleton() -> None:
    """Placeholder for the planned local AI-analysis layer (not built yet)."""
    with st.container(border=True):
        st.markdown("#### :material/auto_awesome: AI analysis — coming soon")
        st.markdown(
            "Once a clip is transcribed and saved to your library, this is where you'll be able "
            "to **ask questions about your transcripts** and get grounded, cited answers — all "
            "kept local-first. This is a planned addition; the current MVP is a focused **local "
            "speech-to-text** tool."
        )
        st.caption(
            ":material/lock: Nothing here sends your media or transcripts anywhere — "
            "transcription stays on your machine."
        )


def main() -> None:
    st.html(_CSS)
    st.logo(LOGO, icon_image=MARK, size="large")
    if not st.session_state.get("_started"):
        log.info("ClipScribe app started")
        st.session_state["_started"] = True

    model, language, use_vad = _settings()
    provider = _provider()  # built once per run; None if no API key configured
    st.html(_tint_css(st.session_state.get("tint", DEFAULT_TINT)))

    st.title(":material/graphic_eq: ClipScribe")
    st.markdown(
        ":small[Privacy-first local speech-to-text for short screen recordings — runs on "
        "your machine, no API key, nothing sent to the cloud.]"
    )

    tab_transcribe, tab_ai = st.tabs(
        [":material/graphic_eq: Transcribe", ":material/auto_awesome: AI analysis"]
    )
    with tab_transcribe:
        _render_transcribe(model, language, use_vad, provider)
    with tab_ai:
        _render_ai_skeleton()

    st.divider()
    st.caption(
        "Built by **Sita Sanon** · [GitHub](https://github.com/codedroid404) · "
        "ClipScribe — privacy-first local ASR"
    )


if __name__ == "__main__":
    main()
