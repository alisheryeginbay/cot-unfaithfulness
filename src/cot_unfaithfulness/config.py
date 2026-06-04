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

    MMLU = "mmlu"


# Phase 1 subject slate (one per MMLU domain), and the per-subject sample size
# drawn from the test split before the clean-correct filter.
PHASE1_SUBJECTS: tuple[str, ...] = (
    "high_school_mathematics",
    "philosophy",
    "high_school_psychology",
    "professional_medicine",
)
PHASE1_SAMPLES_PER_SUBJECT = 150

# The subject models in Phase 1 (LiteLLM/OpenRouter strings).
# Opus 4.8 is the frontier subject; with native reasoning off it still composes
# its answer in visible tokens, so its prompted CoT is genuine. Llama 3.1 8B is a
# weak baseline that provides a non-empty movement/unfaithfulness denominator.
# gpt-5.5 was dropped: with reasoning off it answers directly, so any forced CoT
# is post-hoc narration, not the computation behind the answer (see design doc).
SUBJECT_MODELS: tuple[str, ...] = (
    "openrouter/anthropic/claude-opus-4.8",
    "openrouter/meta-llama/llama-3.1-8b-instruct",
)
SHOTS: tuple[int, ...] = (0, 1, 3)  # zero-, one-, few-shot


class ExperimentConfig(BaseModel):
    """All parameters for one experiment run."""

    model: str = Field(
        default="openrouter/openai/gpt-4o-mini",
        description="LiteLLM model string (OpenRouter convention: openrouter/<provider>/<model>).",
    )
    dataset: Dataset = Dataset.MMLU
    task: str | None = Field(
        default=None,
        description="MMLU subject name (e.g. 'philosophy'); None means all Phase 1 subjects.",
    )
    bias_type: BiasType = BiasType.NONE
    n_samples: int = Field(default=150, ge=1, description="Number of examples to evaluate.")
    few_shot_k: int = Field(
        default=3, ge=0, description="Number of few-shot exemplars in the prompt."
    )
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)
    seed: int = 0
