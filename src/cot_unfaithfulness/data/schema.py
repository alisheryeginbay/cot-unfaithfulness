"""Normalized data representations shared across datasets.

Both BBH and BBQ examples are mapped onto these models so the rest of the
pipeline (prompting, parsing, metrics) is dataset-agnostic.
"""

from __future__ import annotations

from pydantic import BaseModel

# Canonical option letters, indexed positionally (A=0, B=1, ...).
LETTERS = ("A", "B", "C", "D", "E", "F", "G", "H")


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

    @property
    def letters(self) -> list[str]:
        """The option letters present, in order."""
        return [c.letter for c in self.choices]

    @property
    def answer_text(self) -> str:
        """The text of the correct choice."""
        return next(c.text for c in self.choices if c.letter == self.answer)
