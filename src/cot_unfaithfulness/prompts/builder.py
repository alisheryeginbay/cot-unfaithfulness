"""Prompt construction.

Assembles a few-shot chain-of-thought prompt for an example, optionally routing
through a bias injector based on the experiment config.
"""

from __future__ import annotations

from cot_unfaithfulness.config import ExperimentConfig
from cot_unfaithfulness.data.schema import Example


def build_prompt(
    example: Example,
    config: ExperimentConfig,
    few_shot: list[Example] | None = None,
) -> list[dict]:
    """Build the chat messages for one example.

    Returns a list of LiteLLM-style chat messages (role/content dicts), with the
    configured biasing feature applied. Few-shot exemplars are prepended as CoT
    demonstrations.
    """
    raise NotImplementedError
