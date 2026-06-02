"""Unit tests for MMLU row->Example mapping (no network)."""

from cot_unfaithfulness.data.loaders import row_to_example


def _row():
    return {
        "question": "Aesthetics deals with objects that are_____.",
        "subject": "philosophy",
        "choices": [
            "essential to our existence",
            "unimportant to most people",
            "not essential to our existence",
            "rarely viewed",
        ],
        "answer": 2,  # 0-based index -> "C"
    }


def test_row_to_example_maps_letters_and_answer():
    ex = row_to_example(_row(), subject="philosophy", split="test", index=7)

    assert ex.id == "philosophy/test/7"
    assert ex.question.startswith("Aesthetics")
    assert ex.letters == ["A", "B", "C", "D"]
    assert ex.answer == "C"
    assert ex.answer_text == "not essential to our existence"
    assert ex.metadata == {"subject": "philosophy", "split": "test"}


def test_row_to_example_choice_text_aligns_with_letters():
    ex = row_to_example(_row(), subject="philosophy", split="dev", index=0)

    assert ex.choices[0] == ex.choices[0].__class__(letter="A", text="essential to our existence")
    assert ex.choices[3].letter == "D"
