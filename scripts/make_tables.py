"""Write the Phase 1 results tables as markdown.

Generates three files in <out-dir>: per_model_shot.md, pooled.md, and
judge_validation.md (skipped with a warning when the validation files are
absent, e.g. on smoke-run dirs).

    uv run python scripts/make_tables.py --results-dir results
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cot_unfaithfulness.config import MODEL_DISPLAY_NAMES, SUBJECT_MODELS, display_name
from cot_unfaithfulness.experiment.records import ConditionResult, Label
from cot_unfaithfulness.experiment.runner import merge_labels
from cot_unfaithfulness.experiment.store import load_jsonl
from cot_unfaithfulness.metrics.faithfulness import compute_reports, pool_by_model
from cot_unfaithfulness.metrics.tables import (
    judge_validation_md,
    per_model_shot_table,
    pooled_table,
)
from cot_unfaithfulness.metrics.validation import score_validation


def _write(path: Path, content: str) -> None:
    path.write_text(content)
    print(f"wrote {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, default=Path("results"))
    ap.add_argument("--out-dir", type=Path, default=None, help="default: <results-dir>/tables")
    args = ap.parse_args()
    out_dir = args.out_dir or args.results_dir / "tables"

    responses = load_jsonl(args.results_dir / "responses.jsonl", ConditionResult)
    labels = load_jsonl(args.results_dir / "labels.jsonl", Label)
    order = {m: i for i, m in enumerate(SUBJECT_MODELS)}
    reports = sorted(
        compute_reports(merge_labels(responses, labels)),
        key=lambda r: (order.get(r.model, len(order)), r.shot),
    )
    pooled = pool_by_model(reports)

    for p in pooled:
        print(
            f"{display_name(p.model):<8} silent={p.n_silent} verbalized={p.n_verbalized}"
            f" moved={p.n_moved} eligible={p.n_eligible}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    _write(out_dir / "per_model_shot.md", per_model_shot_table(reports, MODEL_DISPLAY_NAMES))
    _write(out_dir / "pooled.md", pooled_table(pooled, MODEL_DISPLAY_NAMES))

    key_path = args.results_dir / "validation_key.json"
    answers_path = args.results_dir / "validation_answers.csv"
    missing = [p for p in (key_path, answers_path) if not p.exists()]
    if missing:
        print(f"skipping judge_validation.md: {missing[0]} not found")
        return
    try:
        score = score_validation(key_path, answers_path)
    except ValueError as e:
        print(f"skipping judge_validation.md: {e}")
        return
    _write(out_dir / "judge_validation.md", judge_validation_md(score))


if __name__ == "__main__":
    main()
