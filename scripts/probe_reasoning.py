"""Throwaway probe: can GPT-5.5 (and Opus 4.8) have native reasoning disabled
via OpenRouter? We try a few disable strategies and report reasoning-token
usage. reasoning_tokens == 0 means reasoning is genuinely off.

Run: uv run python scripts/probe_reasoning.py
Requires OPENROUTER_API_KEY in .env.
"""

from __future__ import annotations

import json

import litellm
from dotenv import load_dotenv

load_dotenv()

PROMPT = [
    {
        "role": "user",
        "content": "What is 17 + 26? Reply with just the number.",
    }
]


def reasoning_tokens(resp) -> int | None:
    usage = getattr(resp, "usage", None)
    if usage is None:
        return None
    details = getattr(usage, "completion_tokens_details", None)
    if details is None:
        return None
    return getattr(details, "reasoning_tokens", None)


def try_call(model: str, label: str, **kwargs) -> None:
    print(f"\n--- {model} | {label} ---")
    try:
        resp = litellm.completion(model=model, messages=PROMPT, max_tokens=200, **kwargs)
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        reasoning_field = getattr(msg, "reasoning_content", None) or getattr(
            msg, "reasoning", None
        )
        rt = reasoning_tokens(resp)
        print(f"  content: {content!r}")
        print(f"  reasoning_field present: {bool(reasoning_field)}")
        print(f"  usage.reasoning_tokens: {rt}")
        try:
            print(f"  raw usage: {json.dumps(resp.usage.model_dump(), default=str)}")
        except Exception:
            print(f"  raw usage: {resp.usage}")
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR: {type(e).__name__}: {e}")


def main() -> None:
    for model in ("openrouter/openai/gpt-5.5", "openrouter/anthropic/claude-opus-4.8"):
        # Strategy A: OpenRouter unified reasoning.enabled = false (passthrough).
        try_call(model, "reasoning.enabled=false", extra_body={"reasoning": {"enabled": False}})
        # Strategy B: LiteLLM reasoning_effort minimal (maps per provider).
        try_call(model, "reasoning_effort=minimal", reasoning_effort="minimal")
        # Strategy C: baseline (no reasoning control) for comparison.
        try_call(model, "no-control (baseline)")


if __name__ == "__main__":
    main()
