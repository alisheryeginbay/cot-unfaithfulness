"""HuggingFace dataset loaders.

Each loader pulls a dataset via `datasets.load_dataset` and maps raw rows onto
the normalized `Example` schema. Field-mapping is intentionally unimplemented in
the skeleton.
"""

from __future__ import annotations

from cot_unfaithfulness.data.schema import Example


def load_bbh(task: str, n_samples: int | None = None) -> list[Example]:
    """Load a BIG-Bench Hard task as normalized `Example` records.

    Args:
        task: BBH task name (e.g. "logical_deduction_three_objects").
        n_samples: Optional cap on the number of examples returned.
    """
    raise NotImplementedError


def load_bbq(category: str | None = None, n_samples: int | None = None) -> list[Example]:
    """Load the Bias Benchmark for QA (BBQ) as normalized `Example` records.

    Args:
        category: Optional BBQ social-bias category (e.g. "Age", "Gender_identity").
        n_samples: Optional cap on the number of examples returned.
    """
    raise NotImplementedError
