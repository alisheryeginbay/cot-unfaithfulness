"""Experiment orchestration.

Ties the pipeline together: load data -> build prompt (+ bias) -> call model ->
parse answer -> collect `Result` records.
"""

from __future__ import annotations

from pydantic import BaseModel

from cot_unfaithfulness.config import ExperimentConfig


class Result(BaseModel):
    """Outcome for a single example under a single condition."""

    example_id: str
    bias_type: str
    raw_completion: str
    predicted_answer: str | None
    correct_answer: str
    biased_toward: str | None = None


def run_experiment(config: ExperimentConfig) -> list[Result]:
    """Run the full pipeline for `config` and return per-example results."""
    raise NotImplementedError
