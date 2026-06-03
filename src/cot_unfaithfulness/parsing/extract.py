"""Answer extraction from chain-of-thought model output.

Parses the final multiple-choice letter the model commits to via the required
closing line: ``The best answer is: (X)``.
"""

from __future__ import annotations

import re

# Matches the required answer line; the letter may be wrapped in parens or not.
_ANSWER_RE = re.compile(r"the best answer is:\s*\(?([A-Ha-h])\)?", re.IGNORECASE)


def extract_answer(text: str) -> str | None:
    """Extract the final answer letter from a CoT completion.

    Returns the choice letter (upper-cased) from the **last** conforming
    ``The best answer is: (X)`` line, or ``None`` if no such line exists.
    Strict by design: non-conforming output is unparseable, not guessed.
    """
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    return matches[-1].upper()
