"""MMLU dataset loading.

Loads MMLU subjects via `datasets.load_dataset("cais/mmlu", <subject>)` and maps
raw rows onto the normalized `Example` schema. The row->Example mapping is kept as
a pure function (`row_to_example`) so it can be tested without network access.
"""

from __future__ import annotations

from typing import Any

from datasets import load_dataset

from cot_unfaithfulness.data.schema import LETTERS, Example, MCQChoice

MMLU_PATH = "cais/mmlu"


def row_to_example(row: dict[str, Any], subject: str, split: str, index: int) -> Example:
    """Map one raw MMLU row to a normalized `Example`.

    MMLU rows are: ``{"question": str, "choices": list[str], "answer": int,
    "subject": str}`` where ``answer`` is a 0-based index into ``choices``.
    """
    choices = [MCQChoice(letter=LETTERS[i], text=text) for i, text in enumerate(row["choices"])]
    answer_letter = LETTERS[int(row["answer"])]
    return Example(
        id=f"{subject}/{split}/{index}",
        question=row["question"],
        choices=choices,
        answer=answer_letter,
        metadata={"subject": subject, "split": split},
    )


def load_mmlu(subject: str, split: str = "test", n: int | None = None) -> list[Example]:
    """Load an MMLU subject split as normalized `Example` records.

    Args:
        subject: MMLU subject/config name (e.g. "philosophy").
        split: One of "test", "validation", "dev".
        n: Optional cap on the number of examples returned (first ``n`` rows).
    """
    ds = load_dataset(MMLU_PATH, subject, split=split)
    rows = ds.select(range(min(n, len(ds)))) if n is not None else ds
    return [row_to_example(row, subject, split, i) for i, row in enumerate(rows)]
