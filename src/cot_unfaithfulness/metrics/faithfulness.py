"""Unfaithfulness metrics.

Compares results from a baseline (unbiased) condition against a biased condition
to quantify how often the model's answer is swayed by the biasing feature.
"""

from __future__ import annotations

from pydantic import BaseModel

from cot_unfaithfulness.experiment.runner import Result


class FaithfulnessReport(BaseModel):
    """Aggregate metrics for a baseline-vs-biased comparison."""

    n: int
    baseline_accuracy: float
    biased_accuracy: float
    flip_rate: float  # fraction of examples where the answer changed under bias
    bias_match_rate: float  # fraction where the biased answer matched the injected bias


def compute_unfaithfulness(
    baseline: list[Result],
    biased: list[Result],
) -> FaithfulnessReport:
    """Compute the unfaithfulness report from paired baseline/biased results."""
    raise NotImplementedError
