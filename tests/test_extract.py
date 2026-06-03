"""Unit tests for answer extraction."""

from cot_unfaithfulness.parsing.extract import extract_answer


def test_extracts_simple_final_line():
    assert extract_answer("Reasoning here.\nThe best answer is: (C)") == "C"


def test_case_insensitive_and_optional_parens():
    assert extract_answer("the best answer is: B") == "B"
    assert extract_answer("THE BEST ANSWER IS: (d)") == "D"


def test_takes_last_match_when_phrase_quoted_midway():
    text = (
        'I should answer "The best answer is: (A)" format.\n'
        "After thinking, The best answer is: (D)"
    )
    assert extract_answer(text) == "D"


def test_returns_none_when_no_conforming_line():
    assert extract_answer("I think it's probably C, hard to say.") is None


def test_returns_none_on_empty():
    assert extract_answer("") is None
