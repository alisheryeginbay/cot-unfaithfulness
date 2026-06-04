"""Targeted in-process cost measurement for the Phase 1 projection.

Avoids the full pipeline's Llama demo bottleneck by reusing cached demos and
issuing a bounded number of real-prompt calls per (model, shot, biased), reading
per-call cost from the global CostMeter. Also measures the demo resample
multiplier (calls-to-gold) and per-call judge cost on small samples.

Writes results/cost_measure.json.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from cot_unfaithfulness.config import PHASE1_SUBJECTS, SUBJECT_MODELS
from cot_unfaithfulness.data.loaders import load_mmlu
from cot_unfaithfulness.experiment.demos import generate_demo
from cot_unfaithfulness.experiment.records import DemoRecord
from cot_unfaithfulness.experiment.store import load_jsonl
from cot_unfaithfulness.judge import label_completion
from cot_unfaithfulness.models.client import (
    METER,
    SUBJECT_REASONING,
    complete,
)
from cot_unfaithfulness.prompts.bias import sample_suggested_letter
from cot_unfaithfulness.prompts.builder import build_messages

CACHED_DEMOS = Path("results/smoke3/demos.jsonl")
SHOTS = (0, 1, 3)
ITEMS_PER_MEASURE = 2  # real items per (model, shot, biased) cell
DEMO_SAMPLES = 3       # dev exemplars per model for the resample multiplier
JUDGE_SAMPLES = 3


def _model_delta(before: dict, model: str) -> dict:
    """Meter delta for one model since `before` snapshot."""
    after = METER.snapshot().get(model, {})
    b = before.get(model, {})
    keys = ("calls", "prompt_tokens", "completion_tokens", "cost_usd")
    return {k: after.get(k, 0) - b.get(k, 0) for k in keys}


def main() -> None:
    rng = random.Random(0)
    # 2 test items per subject, and cached few-shot demos.
    items = []
    for subject in PHASE1_SUBJECTS:
        items.extend(load_mmlu(subject, split="test", n=ITEMS_PER_MEASURE))
    demos_by = defaultdict(list)
    for rec in load_jsonl(CACHED_DEMOS, DemoRecord):
        demos_by[(rec.subject, rec.model)].append((rec.example, rec.completion))

    x_map = {ex.id: sample_suggested_letter(ex, rng) for ex in items}

    # --- per-(model, shot, biased) condition call cost ---
    cond: dict[str, dict] = {}
    for model in SUBJECT_MODELS:
        cond[model] = {}
        for shot in SHOTS:
            for biased in (False, True):
                before = METER.snapshot()
                for ex in items[:ITEMS_PER_MEASURE]:
                    subject = ex.metadata["subject"]
                    demos = demos_by.get((subject, model), [])[:shot]
                    msgs = build_messages(
                        ex, demos, suggested_letter=x_map[ex.id] if biased else None
                    )
                    complete(msgs, model=model, max_tokens=1024, reasoning=SUBJECT_REASONING)
                d = _model_delta(before, model)
                n = d["calls"] or 1
                cond[model][f"shot{shot}_{'biased' if biased else 'unbiased'}"] = {
                    "n_calls": d["calls"],
                    "avg_prompt_tokens": d["prompt_tokens"] / n,
                    "avg_completion_tokens": d["completion_tokens"] / n,
                    "avg_cost_usd": d["cost_usd"] / n,
                }
        print(f"[cond] done {model}")

    # --- demo resample multiplier (calls-to-gold) per model ---
    demo_stats: dict[str, dict] = {}
    for model in SUBJECT_MODELS:
        dev = load_mmlu(PHASE1_SUBJECTS[0], split="dev")[:DEMO_SAMPLES]
        before = METER.snapshot()
        successes = 0
        for ex in dev:
            try:
                generate_demo(ex, model, max_tokens=1024)
                successes += 1
            except Exception:
                pass
        d = _model_delta(before, model)
        demo_stats[model] = {
            "exemplars_attempted": len(dev),
            "successes": successes,
            "total_calls": d["calls"],
            "calls_per_success": (d["calls"] / successes) if successes else None,
            "avg_cost_per_call_usd": (d["cost_usd"] / d["calls"]) if d["calls"] else 0.0,
            "total_cost_usd": d["cost_usd"],
        }
        print(f"[demo] done {model}: {demo_stats[model]}")

    # --- judge per-call cost ---
    judge_before = METER.snapshot()
    biased_items = items[:JUDGE_SAMPLES]
    for ex in biased_items:
        x = x_map[ex.id]
        fake_cot = f"Reasoning about the question.\n\nThe best answer is: ({x})"
        label_completion(ex, x, fake_cot)
    # judge model key is the only new model in the delta
    judge_snap = METER.snapshot()
    judge_model = next(m for m in judge_snap if "gemini" in m)
    jd = _model_delta(judge_before, judge_model)
    jn = jd["calls"] or 1
    judge = {
        "model": judge_model,
        "n_calls": jd["calls"],
        "avg_prompt_tokens": jd["prompt_tokens"] / jn,
        "avg_completion_tokens": jd["completion_tokens"] / jn,
        "avg_cost_usd": jd["cost_usd"] / jn,
    }

    out = {
        "conditions": cond,
        "demos": demo_stats,
        "judge": judge,
        "meter_total": METER.snapshot(),
    }
    Path("results/cost_measure.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
