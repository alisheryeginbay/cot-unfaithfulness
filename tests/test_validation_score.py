"""Unit tests for judge-validation scoring (key + human answers -> ValidationScore)."""

import json

import pytest

from cot_unfaithfulness.metrics.validation import parse_human_answers, score_validation


def _write_key(path, rows):
    path.write_text(json.dumps(rows))


def _write_answers(path, rows):
    lines = ["row,human_references_suggestion"]
    lines += [f"{r},{v}" for r, v in rows]
    path.write_text("\n".join(lines) + "\n")


def _key_row(row, *, moved=True, judge=False, evidence="", model="m", shot=0):
    return {
        "row": row,
        "item_id": f"s/test/{row}",
        "model": model,
        "shot": shot,
        "moved": moved,
        "judge_references_suggestion": judge,
        "judge_evidence": evidence,
    }


def test_score_validation_happy_path_with_one_disagreement(tmp_path):
    key_path = tmp_path / "validation_key.json"
    answers_path = tmp_path / "validation_answers.csv"
    _write_key(
        key_path,
        [
            _key_row(0, moved=True, judge=False),
            _key_row(1, moved=True, judge=True, evidence="quoted hint"),
            _key_row(2, moved=True, judge=False, model="a/b/llama", shot=1),
            _key_row(3, moved=False, judge=False),  # augment row
        ],
    )
    # human disagrees on row 2 (human=True, judge=False)
    _write_answers(answers_path, [(0, "false"), (1, "true"), (2, "true"), (3, "false")])

    score = score_validation(key_path, answers_path)

    assert score.n_labeled == 4
    assert score.n_moved == 3
    assert score.overall.n == 4
    assert score.overall.n_agree == 3
    assert score.moved_only is not None
    assert score.moved_only.n == 3
    assert score.moved_only.n_agree == 2
    [d] = score.disagreements
    assert (d.row, d.model, d.shot, d.moved) == (2, "a/b/llama", 1, True)
    assert d.human is True and d.judge is False
    assert d.judge_evidence == ""


def test_parse_human_answers_truthy_variants_and_blank_skipped(tmp_path):
    answers_path = tmp_path / "validation_answers.csv"
    _write_answers(
        answers_path,
        [(0, "TRUE"), (1, "t"), (2, "1"), (3, "Yes"), (4, "y"), (5, "False"), (6, "0"), (7, "")],
    )
    assert parse_human_answers(answers_path) == {
        0: True, 1: True, 2: True, 3: True, 4: True, 5: False, 6: False,
    }  # fmt: skip


def test_score_validation_ignores_answer_rows_missing_from_key(tmp_path):
    key_path = tmp_path / "validation_key.json"
    answers_path = tmp_path / "validation_answers.csv"
    _write_key(key_path, [_key_row(0, judge=True)])
    _write_answers(answers_path, [(0, "true"), (99, "true")])

    score = score_validation(key_path, answers_path)
    assert score.n_labeled == 1
    assert score.overall.n_agree == 1


def test_score_validation_no_moved_rows_yields_none_moved_only(tmp_path):
    key_path = tmp_path / "validation_key.json"
    answers_path = tmp_path / "validation_answers.csv"
    _write_key(key_path, [_key_row(0, moved=False), _key_row(1, moved=False, judge=True)])
    _write_answers(answers_path, [(0, "false"), (1, "true")])

    score = score_validation(key_path, answers_path)
    assert score.n_moved == 0
    assert score.moved_only is None
    assert score.overall.n == 2


def test_score_validation_raises_when_no_labeled_rows(tmp_path):
    key_path = tmp_path / "validation_key.json"
    answers_path = tmp_path / "validation_answers.csv"
    _write_key(key_path, [_key_row(0)])
    _write_answers(answers_path, [(0, "")])

    with pytest.raises(ValueError, match="no labeled rows"):
        score_validation(key_path, answers_path)
