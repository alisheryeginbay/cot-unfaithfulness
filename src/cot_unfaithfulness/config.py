"""Experiment configuration.

Defines the typed knobs for a single faithfulness run: which model and dataset,
which biasing paradigm to apply, and sampling parameters.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BiasType(StrEnum):
    """Biasing paradigms from Turpin et al. 2023."""

    NONE = "none"
    SUGGESTED_ANSWER = "suggested_answer"
    ANSWER_ALWAYS_A = "answer_always_a"


class Dataset(StrEnum):
    """Supported source datasets."""

    BBH = "bbh"
    BBQ = "bbq"


class ExperimentConfig(BaseModel):
    """All parameters for one experiment run."""

    model: str = Field(
        default="openrouter/openai/gpt-4o-mini",
        description="LiteLLM model string (OpenRouter convention: openrouter/<provider>/<model>).",
    )
    dataset: Dataset = Dataset.BBH
    task: str | None = Field(
        default=None,
        description="Dataset-specific task/subset name (e.g. a BBH task like 'logical_deduction').",
    )
    bias_type: BiasType = BiasType.NONE
    n_samples: int = Field(default=100, ge=1, description="Number of examples to evaluate.")
    few_shot_k: int = Field(
        default=3, ge=0, description="Number of few-shot exemplars in the prompt."
    )
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)
    seed: int = 0
