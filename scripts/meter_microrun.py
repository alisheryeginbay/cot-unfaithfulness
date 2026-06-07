"""Metered micro-run: measure real per-model / per-phase cost for projection.

Runs the Phase 1 pipeline at limit=2 items/subject, snapshotting the global
CostMeter between phases so demo-generation cost (with its resample multiplier)
is separable from conditions and judge cost. Writes scratch/meter/cost.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from cot_unfaithfulness.experiment.records import ConditionResult
from cot_unfaithfulness.experiment.runner import (
    RunConfig,
    build_all_demos,
    clean_correct_intersection,
    load_items,
    run_baseline,
    run_conditions,
    run_judge,
    sample_x_map,
)
from cot_unfaithfulness.experiment.store import load_jsonl
from cot_unfaithfulness.models.client import METER


def _delta(after: dict, before: dict) -> dict:
    out = {}
    for model, a in after.items():
        b = before.get(model, {})
        out[model] = {k: a[k] - b.get(k, 0) for k in a}
    return out


def main() -> None:
    config = RunConfig(results_dir=Path("scratch/meter"), limit=2, workers=4)
    config.results_dir.mkdir(parents=True, exist_ok=True)

    items = load_items(config)
    items_by_id = {ex.id: ex for ex in items}
    x_map = sample_x_map(items, config.seed)

    snaps: list[tuple[str, dict]] = [("start", METER.snapshot())]

    run_baseline(config, items, x_map)
    snaps.append(("baseline", METER.snapshot()))

    baseline = load_jsonl(config.responses_path, ConditionResult)
    surviving = clean_correct_intersection(baseline, config.models)

    demos = build_all_demos(config)
    snaps.append(("demos", METER.snapshot()))

    run_conditions(config, items_by_id, surviving, x_map, demos)
    snaps.append(("conditions", METER.snapshot()))

    run_judge(config, items_by_id)
    snaps.append(("judge", METER.snapshot()))

    phases = {}
    for (_prev_name, prev), (name, cur) in zip(snaps, snaps[1:], strict=True):
        phases[name] = _delta(cur, prev)

    out = {
        "n_per_subject": config.limit,
        "n_subjects": len(config.subjects),
        "n_items_loaded": len(items),
        "n_surviving": len(surviving),
        "models": list(config.models),
        "phases": phases,
        "total_by_model": METER.snapshot(),
        "total_cost_usd": METER.total_cost(),
    }
    out_path = config.results_dir / "cost.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
