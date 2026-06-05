"""Unit tests for the model client (no network; litellm.completion patched)."""

import time
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
        model="openrouter/anthropic/claude-opus-4.8",
        max_tokens=256,
        reasoning=SUBJECT_REASONING,
    )

    assert out == "The best answer is: (B)"
    assert captured["model"] == "openrouter/anthropic/claude-opus-4.8"
    assert captured["max_tokens"] == 256
    assert captured["extra_body"] == {
        "usage": {"include": True},
        "reasoning": {"enabled": False},
    }
    # retries are handled by our watchdog loop, not delegated to litellm
    assert "num_retries" not in captured
    assert captured["timeout"] == client_mod.DEFAULT_TIMEOUT


def test_complete_omits_extra_body_when_no_reasoning(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _fake_response("hi")

    monkeypatch.setattr(client_mod.litellm, "completion", fake_completion)

    complete([{"role": "user", "content": "q"}], model="m")
    assert captured["extra_body"] == {"usage": {"include": True}}


def test_meter_records_usage_and_native_cost(monkeypatch):
    usage = SimpleNamespace(prompt_tokens=120, completion_tokens=40, cost=0.0033)
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))], usage=usage
    )
    monkeypatch.setattr(client_mod.litellm, "completion", lambda **kw: resp)

    meter = client_mod.CostMeter()
    monkeypatch.setattr(client_mod, "METER", meter)

    complete([{"role": "user", "content": "q"}], model="zzz")
    snap = meter.snapshot()["zzz"]
    assert snap["calls"] == 1
    assert snap["prompt_tokens"] == 120
    assert snap["completion_tokens"] == 40
    assert abs(snap["cost_usd"] - 0.0033) < 1e-9
    assert abs(meter.total_cost() - 0.0033) < 1e-9


def test_extract_cost_falls_back_to_litellm_response_cost():
    resp = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        _hidden_params={"response_cost": 0.001},
    )
    pt, ct, cost = client_mod._extract_usage_cost(resp)
    assert (pt, ct) == (10, 5)
    assert abs(cost - 0.001) < 1e-9


def test_complete_handles_none_content(monkeypatch):
    monkeypatch.setattr(
        client_mod.litellm, "completion", lambda **kw: _fake_response(None)
    )
    assert complete([{"role": "user", "content": "q"}], model="m") == ""


def test_watchdog_times_out_hung_call_then_retries(monkeypatch):
    """A call that hangs past the wall-clock cap is abandoned and retried."""
    calls = {"n": 0}

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            time.sleep(5)  # exceeds the tiny timeout below -> watchdog abandons it
        return _fake_response("recovered")

    monkeypatch.setattr(client_mod.litellm, "completion", flaky)
    out = complete(
        [{"role": "user", "content": "q"}], model="m", timeout=0.2, num_retries=2
    )
    assert out == "recovered"
    assert calls["n"] >= 2  # first attempt timed out, a later one succeeded


def test_complete_raises_after_exhausting_retries(monkeypatch):
    def boom(**kw):
        raise RuntimeError("provider down")

    monkeypatch.setattr(client_mod.litellm, "completion", boom)
    try:
        complete([{"role": "user", "content": "q"}], model="m", num_retries=1, timeout=1)
    except RuntimeError as e:
        assert "after 2 attempts" in str(e)
    else:
        raise AssertionError("expected RuntimeError after retries")
