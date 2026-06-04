"""Unit tests for JSONL persistence (crash-safe resumability)."""

import pytest
from pydantic import ValidationError

from cot_unfaithfulness.experiment.records import Label
from cot_unfaithfulness.experiment.store import append_jsonl, load_jsonl


def _label(item_id: str) -> Label:
    return Label(
        item_id=item_id, model="m", shot=0, references_suggestion=False, evidence=""
    )


def test_roundtrip(tmp_path):
    path = tmp_path / "labels.jsonl"
    append_jsonl(path, _label("a"))
    append_jsonl(path, _label("b"))
    loaded = load_jsonl(path, Label)
    assert [lb.item_id for lb in loaded] == ["a", "b"]


def test_missing_file_is_empty(tmp_path):
    assert load_jsonl(tmp_path / "nope.jsonl", Label) == []


def test_truncated_final_line_is_tolerated(tmp_path):
    """A crash mid-append leaves a partial final line; resume must skip it."""
    path = tmp_path / "labels.jsonl"
    append_jsonl(path, _label("a"))
    with path.open("a") as f:
        f.write('{"item_id": "b", "model": "m"')  # truncated, no newline
    with pytest.warns(UserWarning, match="truncated"):
        loaded = load_jsonl(path, Label)
    assert [lb.item_id for lb in loaded] == ["a"]


def test_malformed_non_final_line_raises(tmp_path):
    """Corruption in the middle is real damage, not a crash artifact — surface it."""
    path = tmp_path / "labels.jsonl"
    with path.open("a") as f:
        f.write('{"item_id": "bad"}\n')  # missing required fields
        f.write(_label("good").model_dump_json() + "\n")
    with pytest.raises(ValidationError):
        load_jsonl(path, Label)