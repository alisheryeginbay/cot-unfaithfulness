"""Normalized data representations shared across datasets.

Both BBH and BBQ examples are mapped onto these models so the rest of the
pipeline (prompting, parsing, metrics) is dataset-agnostic.
"""

from __future__ import annotations

from pydantic import BaseModel


class MCQChoice(BaseModel):
    """A single multiple-choice option."""

    letter: str  # "A", "B", "C", ...
    text: str


class Example(BaseModel):
    """A normalized multiple-choice question."""

    id: str
    question: str
    choices: list[MCQChoice]
    answer: str  # letter of the correct choice
    metadata: dict = {}
