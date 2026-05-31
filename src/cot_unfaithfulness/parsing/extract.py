"""Answer extraction from chain-of-thought model output.

Parses the final multiple-choice letter the model commits to (e.g. from a
"the best answer is: (X)" style closing line).
"""

from __future__ import annotations


def extract_answer(text: str) -> str | None:
    """Extract the final answer letter from a CoT completion.

    Returns the choice letter (e.g. "A") or None if no answer can be parsed.
    """
    raise NotImplementedError
