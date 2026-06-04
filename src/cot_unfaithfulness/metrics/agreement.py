"""Inter-rater agreement for judge validation.

The verbalization judge produces the headline faithfulness split (silent vs
verbalized among moved cases). Before those numbers are trusted, the judge must
be validated against blind human labels on a sample of the run's actual moved
cases. This module provides the agreement statistics for that pass.
"""

from __future__ import annotations

from pydantic import BaseModel


class AgreementReport(BaseModel):
    n: int
    n_agree: int
    observed_agreement: float  # p_o
    cohen_kappa: float | None  # None if undefined (single-class degenerate marginals)
    # confusion vs human (human x judge), keys "true"/"false"
    both_true: int
    both_false: int
    human_true_judge_false: int
    human_false_judge_true: int


def cohen_kappa(human: list[bool], judge: list[bool]) -> AgreementReport:
    """Cohen's kappa for two binary raters over the same items.

    kappa = (p_o - p_e) / (1 - p_e), where p_o is observed agreement and p_e is
    the agreement expected from the raters' marginal label rates. Returns kappa
    None when p_e == 1 (a rater used a single class for every item, so chance
    agreement is total and kappa is undefined).
    """
    if len(human) != len(judge):
        raise ValueError("human and judge label lists must be the same length")
    n = len(human)
    if n == 0:
        raise ValueError("need at least one labelled item")

    tt = sum(1 for h, j in zip(human, judge, strict=True) if h and j)
    ff = sum(1 for h, j in zip(human, judge, strict=True) if not h and not j)
    tf = sum(1 for h, j in zip(human, judge, strict=True) if h and not j)
    ft = sum(1 for h, j in zip(human, judge, strict=True) if not h and j)

    n_agree = tt + ff
    p_o = n_agree / n
    # marginals
    p_human_true = (tt + tf) / n
    p_judge_true = (tt + ft) / n
    p_e = p_human_true * p_judge_true + (1 - p_human_true) * (1 - p_judge_true)
    kappa = None if p_e >= 1.0 else (p_o - p_e) / (1 - p_e)

    return AgreementReport(
        n=n,
        n_agree=n_agree,
        observed_agreement=p_o,
        cohen_kappa=kappa,
        both_true=tt,
        both_false=ff,
        human_true_judge_false=tf,
        human_false_judge_true=ft,
    )
