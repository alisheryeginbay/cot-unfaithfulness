"""Standalone judge runner — completes the verbalization labels for a run.

Equivalent to the runner's judge phase but in a clean, short-lived process
(the full CLI process stalled mid-judge from accumulated HTTP state; direct
calls are fast and reliable). Resumable: skips already-labelled records.

    uv run python scripts/finish_judge.py --results-dir results/phase1 --workers 8
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from cot_unfaithfulness.config import PHASE1_SUBJECTS
from cot_unfaithfulness.data.loaders import load_mmlu
from cot_unfaithfulness.experiment.records import ConditionResult, Label
from cot_unfaithfulness.experiment.store import append_jsonl, load_jsonl
from cot_unfaithfulness.judge import label_completion
from cot_unfaithfulness.models.client import METER


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n-per-subject", type=int, default=150)
    ap.add_argument("--limit", type=int, default=None, help="label at most N this process")
    ap.add_argument(
        "--moved-only",
        action="store_true",
        help="label only moved cases (the headline-metric denominator); cheapest path",
    )
    args = ap.parse_args()
    load_dotenv()

    labels_path = args.results_dir / "labels.jsonl"
    items = {}
    for s in PHASE1_SUBJECTS:
        for ex in load_mmlu(s, split="test", n=args.n_per_subject):
            items[ex.id] = ex

    done = {(lb.item_id, lb.model, lb.shot) for lb in load_jsonl(labels_path, Label)}
    todo = [
        r
        for r in load_jsonl(args.results_dir / "responses.jsonl", ConditionResult)
        if r.biased and (r.item_id, r.model, r.shot) not in done
    ]
    if args.moved_only:
        todo = [r for r in todo if r.moved_toward_bias]
    if args.limit:
        todo = todo[: args.limit]
    print(f"to label: {len(todo)} (already done: {len(done)})", flush=True)

    def work(r: ConditionResult) -> Label:
        ex = items[r.item_id]
        ref, ev = label_completion(ex, r.suggested_letter, r.raw_completion)
        return Label(
            item_id=r.item_id, model=r.model, shot=r.shot,
            references_suggestion=ref, evidence=ev,
        )

    t0 = time.time()
    n = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, r) for r in todo]
        for fut in as_completed(futures):
            append_jsonl(labels_path, fut.result())
            n += 1
            if n % 50 == 0 or n == len(todo):
                rate = n / (time.time() - t0) * 60
                print(
                    f"  {n}/{len(todo)}  {rate:.0f}/min  cost ${METER.total_cost():.3f}",
                    flush=True,
                )
    print(f"done: {n} labels in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
