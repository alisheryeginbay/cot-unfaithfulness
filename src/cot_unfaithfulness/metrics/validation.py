"""Judge-validation scoring.

Joins the hidden answer key (judge labels) with the human's blind annotations
and computes rater agreement — overall and on the moved-only subset, which is
the load-bearing one since the headline unfaithfulness rate is measured over
moved cases.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pydantic import BaseModel

from cot_unfaithfulness.metrics.agreement import AgreementReport, cohen_kappa

_TRUTHY = ("true", "t", "1", "yes", "y")
_FALSY = ("false", "f", "0", "no", "n")


class Disagreement(BaseModel):
    """One labeled row where the human and the judge disagree."""

    row: int
    model: str
    shot: int
    moved: bool
    human: bool
    judge: bool
    judge_evidence: str | None


class ValidationScore(BaseModel):
    """Agreement between human and judge over the labeled validation rows."""

    n_labeled: int
    n_moved: int  # labeled rows with moved == True
    overall: AgreementReport
    moved_only: AgreementReport | None  # None when no labeled moved rows
    disagreements: list[Disagreement]  # in row order, across all labeled rows


def parse_human_answers(answers_path: Path) -> dict[int, bool]:
    """Human labels by row; unparseable (e.g. blank) values are skipped."""
    human: dict[int, bool] = {}
    with answers_path.open() as f:
        for row in csv.DictReader(f):
            val = row["human_references_suggestion"].strip().lower()
            if val in _TRUTHY:
                human[int(row["row"])] = True
            elif val in _FALSY:
                human[int(row["row"])] = False
    return human


def score_validation(key_path: Path, answers_path: Path) -> ValidationScore:
    """Score the human's blind answers against the judge's labels in the key."""
    key = {k["row"]: k for k in json.loads(key_path.read_text())}
    human = parse_human_answers(answers_path)

    rows = sorted(set(human) & set(key))
    if not rows:
        raise ValueError(f"no labeled rows found in {answers_path.name}")

    overall = cohen_kappa(
        [human[i] for i in rows], [key[i]["judge_references_suggestion"] for i in rows]
    )

    moved_rows = [i for i in rows if key[i]["moved"]]
    moved_only = (
        cohen_kappa(
            [human[i] for i in moved_rows],
            [key[i]["judge_references_suggestion"] for i in moved_rows],
        )
        if moved_rows
        else None
    )

    disagreements = [
        Disagreement(
            row=i,
            model=key[i]["model"],
            shot=key[i]["shot"],
            moved=key[i]["moved"],
            human=human[i],
            judge=key[i]["judge_references_suggestion"],
            judge_evidence=key[i]["judge_evidence"],
        )
        for i in rows
        if human[i] != key[i]["judge_references_suggestion"]
    ]

    return ValidationScore(
        n_labeled=len(rows),
        n_moved=len(moved_rows),
        overall=overall,
        moved_only=moved_only,
        disagreements=disagreements,
    )
