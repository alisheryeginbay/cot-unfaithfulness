"""Unit tests for the runner's pure helpers (no network)."""

from cot_unfaithfulness.data.schema import Example, MCQChoice
from cot_unfaithfulness.experiment.records import ConditionResult
from cot_unfaithfulness.experiment.runner import (
    clean_correct_intersection,
    demos_for_shot,
    sample_x_map,
)


def _example(qid, answer="A"):
    return Example(
        id=qid,
        question="q",
        choices=[MCQChoice(letter=c, text=c) for c in "ABCD"],
        answer=answer,
    )


def _baseline(item_id, model, parsed, gold="A"):
    return ConditionResult(
        item_id=item_id,
        subject="s",
        model=model,
        shot=0,
        biased=False,
        gold=gold,
        suggested_letter="B",
        raw_completion="...",
        parsed_answer=parsed,
    )


def test_sample_x_map_deterministic_and_valid():
    items = [_example("s/test/2"), _example("s/test/0"), _example("s/test/1")]
    m1 = sample_x_map(items, seed=0)
    m2 = sample_x_map(items, seed=0)
    assert m1 == m2  # deterministic
    assert set(m1) == {"s/test/0", "s/test/1", "s/test/2"}
    assert all(v in set("ABCD") for v in m1.values())
    # independent of input ordering (sorted by id internally)
    shuffled = sample_x_map(list(reversed(items)), seed=0)
    assert shuffled == m1


def test_clean_correct_intersection_requires_all_models_correct():
    models = ("gpt", "opus")
    baseline = [
        _baseline("i1", "gpt", parsed="A"),  # correct
        _baseline("i1", "opus", parsed="A"),  # correct -> i1 survives
        _baseline("i2", "gpt", parsed="A"),  # correct
        _baseline("i2", "opus", parsed="B"),  # wrong -> i2 excluded
        _baseline("i3", "gpt", parsed=None),  # unparseable -> excluded
        _baseline("i3", "opus", parsed="A"),
    ]
    assert clean_correct_intersection(baseline, models) == {"i1"}


def test_demos_for_shot_slices():
    demos = [("a", "x"), ("b", "y"), ("c", "z")]
    assert demos_for_shot(demos, 0) == []
    assert demos_for_shot(demos, 1) == [("a", "x")]
    assert demos_for_shot(demos, 3) == demos
