"""Unit tests for the AI-title helper (the one opt-in cloud touch) — fake provider."""

import pytest

from clipscribe import llm
from clipscribe.models import TranscriptSegment


class _FakeProvider:
    name = "Fake"
    model = "fake-model-1"

    def __init__(self):
        self.last_system = None
        self.last_user = None

    def complete(self, system: str, user: str) -> tuple[str, str]:
        self.last_system = system
        self.last_user = user
        return '"Customer Advice Recap"', "fake-model-1"


def _segments():
    return [
        TranscriptSegment(0, 0.0, 4.0, "state the customer problem"),
        TranscriptSegment(1, 4.0, 8.0, "quantify the outcome"),
    ]


def test_provider_not_configured_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(llm.ProviderNotConfigured):
        llm.AnthropicProvider(api_key=None)


def test_suggest_title_sends_transcript_and_cleans_output():
    provider = _FakeProvider()
    title = llm.suggest_title_llm(_segments(), provider=provider)
    # transcript text is sent to the provider under the title system prompt
    assert "state the customer problem" in provider.last_user
    assert "concise" in provider.last_system
    # surrounding quotes are stripped from the returned title
    assert title == "Customer Advice Recap"


def test_call_cost():
    # Opus pricing: 1M in + 1M out = $5 + $25
    assert llm.call_cost("claude-opus-4-8", 1_000_000, 1_000_000) == 30.0
    # unknown model falls back to Opus pricing
    assert llm.call_cost("mystery", 1_000_000, 0) == 5.0
    # Haiku is the cheapest
    assert llm.call_cost("claude-haiku-4-5", 1_000_000, 0) == 1.0
