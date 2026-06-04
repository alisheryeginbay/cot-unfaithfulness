"""Unit tests for demo generation (no network; complete/load_mmlu patched)."""

import pytest

import cot_unfaithfulness.experiment.demos as demos_mod
from cot_unfaithfulness.data.schema import Example, MCQChoice
from cot_unfaithfulness.experiment.demos import (
    DemoGenerationError,
    generate_demo,
    generate_demos,
)


def _example(qid="philosophy/dev/0", answer="C"):
    return Example(
        id=qid,
        question="q?",
        choices=[
            MCQChoice(letter="A", text="a"),
            MCQChoice(letter="B", text="b"),
            MCQChoice(letter="C", text="c"),
            MCQChoice(letter="D", text="d"),
        ],
        answer=answer,
    )


def test_generate_demo_resamples_until_correct(monkeypatch):
    outputs = iter(
        [
            "wrong.\nThe best answer is: (A)",
            "still wrong.\nThe best answer is: (B)",
            "right!\nThe best answer is: (C)",
        ]
    )
    calls = {"n": 0}

    def fake_complete(messages, model, *, max_tokens=1024, reasoning=None):
        calls["n"] += 1
        return next(outputs)

    monkeypatch.setattr(demos_mod, "complete", fake_complete)

    out = generate_demo(_example(), model="m", max_attempts=5)
    assert out.endswith("(C)")
    assert calls["n"] == 3  # stopped as soon as it reached gold


def test_generate_demo_raises_after_cap(monkeypatch):
    monkeypatch.setattr(
        demos_mod,
        "complete",
        lambda *a, **k: "nope.\nThe best answer is: (A)",  # never gold (C)
    )
    with pytest.raises(DemoGenerationError):
        generate_demo(_example(), model="m", max_attempts=3)


def test_generate_demos_skips_unreachable_with_warning(monkeypatch):
    good = _example("philosophy/dev/0", answer="C")
    bad = _example("philosophy/dev/1", answer="D")
    monkeypatch.setattr(demos_mod, "load_mmlu", lambda subject, split: [good, bad])

    def fake_complete(messages, model, *, max_tokens=1024, reasoning=None):
        # always answers C: good reaches gold, bad never does
        return "reasoning.\nThe best answer is: (C)"

    monkeypatch.setattr(demos_mod, "complete", fake_complete)

    with pytest.warns(UserWarning):
        demos = generate_demos("philosophy", model="m", max_attempts=2)

    assert [ex.id for ex, _ in demos] == ["philosophy/dev/0"]
