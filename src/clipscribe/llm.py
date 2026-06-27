"""Optional hosted-LLM helper for the ✨ AI-title feature only.

The privacy boundary: transcription, diagnostics, and storage are fully local. The one
opt-in cloud touch is the ✨ AI-title button, which sends a short slice of the transcript
to the configured provider to generate a concise title. Nothing here runs by default, and
the transcript text is never logged.

(Post-MVP, this module is the seed for the planned local-first AI-analysis layer — see the
README Roadmap. The MVP itself remains a pure local ASR application.)
"""

from __future__ import annotations

import os
from typing import Protocol

from .models import TranscriptSegment

DEFAULT_MODEL = "claude-opus-4-8"

# USD per 1M tokens (input, output) — for the session cost estimate shown in the sidebar.
PRICING = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def call_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimated USD cost of one hosted call (defaults to Opus pricing if unknown)."""
    in_price, out_price = PRICING.get(model, (5.0, 25.0))
    return input_tokens / 1_000_000 * in_price + output_tokens / 1_000_000 * out_price


class ProviderNotConfigured(RuntimeError):
    """Raised when the hosted provider has no API key / is unavailable."""


class ChatProvider(Protocol):
    name: str

    def complete(self, system: str, user: str) -> tuple[str, str]:
        """Return (answer_text, model_id) for one prompt."""
        ...


TITLE_SYSTEM = (
    "You write a concise, specific 3-to-6 word title for a transcript. "
    "Output ONLY the title text — no quotes, no trailing punctuation, no preamble."
)


def suggest_title_llm(segments: list[TranscriptSegment], *, provider: ChatProvider) -> str:
    """Ask the hosted provider for a concise title (sends a slice of the transcript text)."""
    text = " ".join(seg.text.strip() for seg in segments)[:4000]
    title, _ = provider.complete(TITLE_SYSTEM, f"Transcript:\n{text}\n\nTitle:")
    return title.strip().strip('"').splitlines()[0][:80] if title.strip() else "Untitled"


class AnthropicProvider:
    """Hosted provider backed by the Anthropic Claude API (key from env)."""

    name = "Anthropic Claude"

    def __init__(self, *, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.last_usage: tuple[int, int] = (0, 0)  # (input_tokens, output_tokens)
        if not self._api_key:
            raise ProviderNotConfigured(
                "Set ANTHROPIC_API_KEY (see .env.example) to enable the AI-title feature."
            )

    def complete(self, system: str, user: str) -> tuple[str, str]:
        import anthropic  # lazy import — local-only paths never need this

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        self.last_usage = (response.usage.input_tokens, response.usage.output_tokens)
        text = "".join(block.text for block in response.content if block.type == "text")
        return text, response.model
