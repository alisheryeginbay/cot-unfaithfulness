"""Unit tests for the model client (no network; litellm.completion patched)."""

from types import SimpleNamespace

import cot_unfaithfulness.models.client as client_mod
from cot_unfaithfulness.models.client import SUBJECT_REASONING, complete


def _fake_response(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_complete_passes_reasoning_and_returns_content(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _fake_response("The best answer is: (B)")

    monkeypatch.setattr(client_mod.litellm, "completion", fake_completion)

    out = complete(
        [{"role": "user", "content": "q"}],
        model="openrouter/openai/gpt-5.5",
        max_tokens=256,
        reasoning=SUBJECT_REASONING,
    )

    assert out == "The best answer is: (B)"
    assert captured["model"] == "openrouter/openai/gpt-5.5"
    assert captured["max_tokens"] == 256
    assert captured["extra_body"] == {"reasoning": {"enabled": False}}
    assert captured["num_retries"] == client_mod.DEFAULT_NUM_RETRIES


def test_complete_omits_extra_body_when_no_reasoning(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _fake_response("hi")

    monkeypatch.setattr(client_mod.litellm, "completion", fake_completion)

    complete([{"role": "user", "content": "q"}], model="m")
    assert captured["extra_body"] is None


def test_complete_handles_none_content(monkeypatch):
    monkeypatch.setattr(
        client_mod.litellm, "completion", lambda **kw: _fake_response(None)
    )
    assert complete([{"role": "user", "content": "q"}], model="m") == ""
