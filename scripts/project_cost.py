"""Full-run cost projection from measured token counts (no network).

Uses real completions captured in scratch/smoke3 to count tokens per
(model, shot, biased) cell, applies authoritative OpenRouter per-token pricing
(validated against live probe charges), and projects the full Phase 1 run.

Demo resample multiplier is derived from each model's measured zero-shot accuracy
(capped-geometric expected calls per exemplar).
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import litellm

from cot_unfaithfulness.config import PHASE1_SUBJECTS, SUBJECT_MODELS
from cot_unfaithfulness.experiment.records import ConditionResult, DemoRecord
from cot_unfaithfulness.experiment.store import load_jsonl
from cot_unfaithfulness.judge import build_judge_messages
from cot_unfaithfulness.prompts.builder import build_messages

# $/token (prompt, completion) — from OpenRouter /models, matches live charges.
PRICES = {
    "openrouter/openai/gpt-5.5": (5e-6, 30e-6),
    "openrouter/anthropic/claude-opus-4.8": (5e-6, 25e-6),
    "openrouter/meta-llama/llama-3.1-8b-instruct": (0.02e-6, 0.05e-6),
    "openrouter/google/gemini-3.1-pro-preview": (2e-6, 12e-6),
}
JUDGE_MODEL = "openrouter/google/gemini-3.1-pro-preview"
JUDGE_COMPLETION_TOKENS = 110  # ~low-effort reasoning (~64) + small JSON verdict

N_PER_SUBJECT = 150
N_SUBJECTS = len(PHASE1_SUBJECTS)
N_LOADED = N_PER_SUBJECT * N_SUBJECTS  # baseline calls per model
DEMO_EXEMPLARS = 5 * N_SUBJECTS  # dev split ~5/subject, all generated
SHOTS = (0, 1, 3)


def _ptok(model, messages):
    return litellm.token_counter(model=model.split("/", 1)[1], messages=messages)


def _ctok(model, text):
    return litellm.token_counter(model=model.split("/", 1)[1], text=text)


def main() -> None:
    smoke = Path("scratch/smoke3")
    responses = load_jsonl(smoke / "responses.jsonl", ConditionResult)
    demos_recs = load_jsonl(smoke / "demos.jsonl", DemoRecord)
    demos_by = defaultdict(list)
    for r in demos_recs:
        demos_by[(r.subject, r.model)].append((r.example, r.completion))
    items_by_id = {}
    for r in responses:
        if r.item_id not in items_by_id:
            # reconstruct an Example-ish via the demo store if present; else skip prompt rebuild
            pass

    # --- per (model, shot, biased) token + cost, from real completions ---
    # group completions
    by_cell = defaultdict(list)
    for r in responses:
        by_cell[(r.model, r.shot, r.biased)].append(r)

    # need Example objects to rebuild prompts: take from demos' examples won't match test items.
    # Instead reload the actual test items.
    from cot_unfaithfulness.data.loaders import load_mmlu

    test_items = {}
    for subj in PHASE1_SUBJECTS:
        for ex in load_mmlu(subj, split="test", n=2):
            test_items[ex.id] = ex

    cell_cost = {}
    for (model, shot, biased), recs in by_cell.items():
        pin, pout = PRICES[model]
        ptoks, ctoks = [], []
        for r in recs:
            ex = test_items.get(r.item_id)
            if ex is None:
                continue
            subject = ex.metadata["subject"]
            demos = demos_by.get((subject, model), [])[:shot]
            msgs = build_messages(
                ex, demos, suggested_letter=r.suggested_letter if biased else None
            )
            ptoks.append(_ptok(model, msgs))
            ctoks.append(_ctok(model, r.raw_completion))
        if not ptoks:
            continue
        ap = sum(ptoks) / len(ptoks)
        ac = sum(ctoks) / len(ctoks)
        cell_cost[(model, shot, biased)] = {
            "avg_prompt_tokens": ap,
            "avg_completion_tokens": ac,
            "avg_cost_usd": ap * pin + ac * pout,
        }

    # baseline cell = (shot 0, unbiased); average cost per model
    def cost(model, shot, biased):
        c = cell_cost.get((model, shot, biased))
        return c["avg_cost_usd"] if c else 0.0

    # --- demo multiplier from measured zero-shot accuracy (smoke3 baseline) ---
    acc = {}
    for model in SUBJECT_MODELS:
        base = [r for r in responses if r.model == model and r.shot == 0 and not r.biased]
        correct = sum(1 for r in base if r.parsed_answer == r.gold)
        acc[model] = correct / len(base) if base else 1.0

    def demo_calls_per_exemplar(p, cap=5):
        # expected number of sampling calls per exemplar (capped geometric)
        return sum((1 - p) ** k for k in range(cap))

    # --- judge prompt tokens from real CoTs ---
    judge_ptoks = []
    pin_j, pout_j = PRICES[JUDGE_MODEL]
    for r in responses:
        if not r.biased:
            continue
        ex = test_items.get(r.item_id)
        if ex is None:
            continue
        msgs = build_judge_messages(ex, r.suggested_letter, r.raw_completion)
        judge_ptoks.append(_ptok(JUDGE_MODEL, msgs))
    avg_judge_ptok = sum(judge_ptoks) / len(judge_ptoks)
    judge_call_cost = avg_judge_ptok * pin_j + JUDGE_COMPLETION_TOKENS * pout_j

    # --- project for a range of surviving-set sizes ---
    def project(surviving):
        rows = {}
        # subject models
        for model in SUBJECT_MODELS:
            baseline_calls = N_LOADED
            baseline_cost = baseline_calls * cost(model, 0, False)
            # 5 non-baseline condition cells per surviving item
            cells = [(1, False), (1, True), (3, False), (3, True), (0, True)]
            cond_calls = surviving * len(cells)
            cond_cost = surviving * sum(cost(model, s, b) for s, b in cells)
            # demos (one-time)
            dpe = demo_calls_per_exemplar(acc[model])
            demo_calls = DEMO_EXEMPLARS * dpe
            demo_cost = demo_calls * cost(model, 0, False)  # demo prompt≈zero-shot unbiased
            rows[model] = {
                "calls": round(baseline_calls + cond_calls + demo_calls),
                "cost": baseline_cost + cond_cost + demo_cost,
                "_demo_calls": round(demo_calls),
                "_zs_acc": acc[model],
                "_dpe": dpe,
            }
        # judge: 3 biased shots × n_subject_models × surviving
        judge_calls = surviving * 3 * len(SUBJECT_MODELS)
        rows[JUDGE_MODEL] = {
            "calls": judge_calls,
            "cost": judge_calls * judge_call_cost,
        }
        return rows

    print("=== measured per-call cost (USD) by cell ===")
    for model in SUBJECT_MODELS:
        print(f"\n{model}  (zero-shot acc≈{acc[model]:.2f})")
        for shot in SHOTS:
            for biased in (False, True):
                c = cell_cost.get((model, shot, biased))
                if c:
                    print(
                        f"  shot{shot} {'biased  ' if biased else 'unbiased'}: "
                        f"p={c['avg_prompt_tokens']:.0f} c={c['avg_completion_tokens']:.0f} "
                        f"-> ${c['avg_cost_usd']:.6f}"
                    )
    print(
        f"\njudge per-call: prompt≈{avg_judge_ptok:.0f} tok + "
        f"{JUDGE_COMPLETION_TOKENS} comp -> ${judge_call_cost:.6f}"
    )

    for S in (250, 300, 400):
        rows = project(S)
        total = sum(r["cost"] for r in rows.values())
        total_calls = sum(r["calls"] for r in rows.values())
        print(f"\n=== FULL-RUN PROJECTION, surviving S={S} ===")
        print(f"{'model':45} {'calls':>9} {'cost USD':>10}")
        for m, r in rows.items():
            print(f"{m:45} {r['calls']:>9} {r['cost']:>10.2f}")
        print(f"{'TOTAL':45} {total_calls:>9} {total:>10.2f}")


if __name__ == "__main__":
    main()
