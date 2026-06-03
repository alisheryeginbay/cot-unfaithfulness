"""LiteLLM model client (OpenRouter).

Thin wrapper around ``litellm.completion``. Native reasoning is controlled via the
OpenRouter passthrough ``extra_body={"reasoning": ...}`` rather than LiteLLM's
``reasoning_effort`` param (which errors for ``openrouter/anthropic/*``).
"""

from __future__ import annotations

import litellm

# Reasoning settings by role (see design doc).
SUBJECT_REASONING: dict = {"enabled": False}  # subjects: native reasoning off
JUDGE_REASONING: dict = {"effort": "low"}  # judge: minimized (cannot fully disable)


def complete(
    messages: list[dict],
    model: str,
    *,
    max_tokens: int = 1024,
    reasoning: dict | None = None,
) -> str:
    """Send chat messages to ``model`` and return the completion text.

    Args:
        messages: chat messages (role/content dicts).
        model: LiteLLM/OpenRouter model string.
        max_tokens: completion token cap.
        reasoning: OpenRouter reasoning control (e.g. ``{"enabled": False}`` for
            subjects, ``{"effort": "low"}`` for the judge). Omitted if None.
    """
    extra_body = {"reasoning": reasoning} if reasoning is not None else None
    response = litellm.completion(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )
    return response.choices[0].message.content or ""
