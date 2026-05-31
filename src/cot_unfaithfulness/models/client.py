"""LiteLLM model client.

Thin wrapper around `litellm.completion` configured for OpenRouter. Reads
`OPENROUTER_API_KEY` from the environment (loaded via python-dotenv).
"""

from __future__ import annotations

from cot_unfaithfulness.config import ExperimentConfig


def complete(messages: list[dict], config: ExperimentConfig) -> str:
    """Send chat messages to the model and return the completion text.

    Uses `config.model` (an OpenRouter model string) plus the sampling
    parameters from `config`.
    """
    raise NotImplementedError
