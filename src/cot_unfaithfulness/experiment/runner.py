"""Phase 1 experiment orchestration.

Pipeline (each phase resumable via JSONL on disk):

  baseline  -> zero-shot unbiased on every item, for every model
  filter    -> clean-correct intersection across models (in-memory)
  demos     -> frozen few-shot demonstrations per (subject, model)
  conditions-> all (shot x biased) completions on surviving items
  judge     -> verbalization labels for biased completions
  report    -> join responses + labels, compute unfaithfulness reports

Concurrency is a bounded thread pool over API calls; resumability skips any
record whose key already exists on disk.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from cot_unfaithfulness.config import PHASE1_SUBJECTS, SHOTS, SUBJECT_MODELS
from cot_unfaithfulness.data.loaders import load_mmlu
from cot_unfaithfulness.data.schema import Example
from cot_unfaithfulness.experiment.demos import generate_demos
from cot_unfaithfulness.experiment.records import ConditionResult, DemoRecord, Label
from cot_unfaithfulness.experiment.store import append_jsonl, load_jsonl
from cot_unfaithfulness.judge import label_completion
from cot_unfaithfulness.metrics.faithfulness import FaithfulnessReport, compute_reports
from cot_unfaithfulness.models.client import METER, SUBJECT_REASONING, complete, format_meter
from cot_unfaithfulness.parsing.extract import extract_answer
from cot_unfaithfulness.prompts.builder import Demo, build_messages


@dataclass
class RunConfig:
    """Top-level configuration for a Phase 1 run."""

    models: tuple[str, ...] = SUBJECT_MODELS
    subjects: tuple[str, ...] = PHASE1_SUBJECTS
    n_per_subject: int = 150
    few_shot_k: int = 3
    results_dir: Path = field(default_factory=lambda: Path("results"))
    workers: int = 8
    seed: int = 0
    max_tokens: int = 1024
    limit: int | None = None  # smoke mode: cap items per subject

    @property
    def responses_path(self) -> Path:
        return self.results_dir / "responses.jsonl"

    @property
    def labels_path(self) -> Path:
        return self.results_dir / "labels.jsonl"

    @property
    def demos_path(self) -> Path:
        return self.results_dir / "demos.jsonl"


# ----- pure helpers (unit-tested) -------------------------------------------


def sample_x_map(items: list[Example], seed: int) -> dict[str, str]:
    """Sample the suggested option X per item (uniform over its letters).

    Deterministic given ``seed`` and item set: items are processed in id order so
    the mapping does not depend on load order.
    """
    rng = random.Random(seed)
    return {ex.id: rng.choice(ex.letters) for ex in sorted(items, key=lambda e: e.id)}


def clean_correct_intersection(
    baseline: list[ConditionResult], models: tuple[str, ...]
) -> set[str]:
    """Item ids that are parseable AND correct in the zero-shot baseline of *every* model."""
    per_model: dict[str, set[str]] = {m: set() for m in models}
    for r in baseline:
        if not r.biased and r.shot == 0 and r.parsed_answer == r.gold and r.model in per_model:
            per_model[r.model].add(r.item_id)
    if not per_model:
        return set()
    return set.intersection(*per_model.values())


def demos_for_shot(demos: list[Demo], shot: int) -> list[Demo]:
    """The first ``shot`` demonstrations (0 -> none)."""
    return demos[:shot]


# ----- concurrency ----------------------------------------------------------


def _execute(tasks: list, fn: Callable, out_path: Path, workers: int, label: str = "") -> list:
    """Run ``fn`` over ``tasks`` in a thread pool, appending each result as it lands.

    Logs a running cost total every 25 completions so spend can be watched live.
    """
    results = []
    if not tasks:
        return results
    total = len(tasks)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fn, t) for t in tasks]
        for future in as_completed(futures):
            record = future.result()
            append_jsonl(out_path, record)
            results.append(record)
            if len(results) % 25 == 0 or len(results) == total:
                print(
                    f"  [{label}] {len(results)}/{total}  running cost "
                    f"${METER.total_cost():.4f}",
                    flush=True,
                )
    return results


# ----- phases ---------------------------------------------------------------


def load_items(config: RunConfig) -> list[Example]:
    """Load test items for all subjects (respecting the smoke ``limit``)."""
    n = config.limit if config.limit is not None else config.n_per_subject
    items: list[Example] = []
    for subject in config.subjects:
        items.extend(load_mmlu(subject, split="test", n=n))
    return items


def run_baseline(config: RunConfig, items: list[Example], x_map: dict[str, str]) -> None:
    """Zero-shot unbiased completion for every item x model (resumable)."""
    done = {
        (r.item_id, r.model)
        for r in load_jsonl(config.responses_path, ConditionResult)
        if r.shot == 0 and not r.biased
    }
    tasks = [
        (model, ex)
        for model in config.models
        for ex in items
        if (ex.id, model) not in done
    ]

    def work(task) -> ConditionResult:
        model, ex = task
        return _complete_condition(config, model, ex, shot=0, biased=False, demos=[], x_map=x_map)

    _execute(tasks, work, config.responses_path, config.workers, label="baseline")


def build_all_demos(config: RunConfig) -> dict[tuple[str, str], list[Demo]]:
    """Generate (or load cached) frozen demos per (subject, model)."""
    cached = load_jsonl(config.demos_path, DemoRecord)
    demos: dict[tuple[str, str], list[Demo]] = {}
    for rec in cached:
        demos.setdefault((rec.subject, rec.model), []).append((rec.example, rec.completion))

    for subject in config.subjects:
        for model in config.models:
            if (subject, model) in demos:
                continue
            generated = generate_demos(subject, model, max_tokens=config.max_tokens)
            for ex, completion in generated:
                append_jsonl(
                    config.demos_path,
                    DemoRecord(subject=subject, model=model, example=ex, completion=completion),
                )
            demos[(subject, model)] = generated
    return demos


def run_conditions(
    config: RunConfig,
    items_by_id: dict[str, Example],
    surviving: set[str],
    x_map: dict[str, str],
    demos: dict[tuple[str, str], list[Demo]],
) -> None:
    """All (shot x biased) completions on surviving items (resumable).

    The zero-shot unbiased cell is already produced by ``run_baseline`` and skipped.
    """
    done = {
        (r.item_id, r.model, r.shot, r.biased)
        for r in load_jsonl(config.responses_path, ConditionResult)
    }
    tasks = []
    for model in config.models:
        for item_id in surviving:
            for shot in SHOTS:
                for biased in (False, True):
                    if shot == 0 and not biased:
                        continue  # produced by baseline
                    if (item_id, model, shot, biased) in done:
                        continue
                    tasks.append((model, item_id, shot, biased))

    def work(task) -> ConditionResult:
        model, item_id, shot, biased = task
        ex = items_by_id[item_id]
        subject = ex.metadata["subject"]
        shot_demos = demos_for_shot(demos.get((subject, model), []), shot)
        return _complete_condition(config, model, ex, shot, biased, shot_demos, x_map)

    _execute(tasks, work, config.responses_path, config.workers, label="conditions")


def run_judge(config: RunConfig, items_by_id: dict[str, Example]) -> None:
    """Label all biased completions with the verbalization judge (resumable)."""
    done = {(lb.item_id, lb.model, lb.shot) for lb in load_jsonl(config.labels_path, Label)}
    biased = [
        r
        for r in load_jsonl(config.responses_path, ConditionResult)
        if r.biased and (r.item_id, r.model, r.shot) not in done
    ]

    def work(r: ConditionResult) -> Label:
        ex = items_by_id[r.item_id]
        references, evidence = label_completion(ex, r.suggested_letter, r.raw_completion)
        return Label(
            item_id=r.item_id,
            model=r.model,
            shot=r.shot,
            references_suggestion=references,
            evidence=evidence,
        )

    _execute(biased, work, config.labels_path, config.workers, label="judge")


def build_report(config: RunConfig) -> list[FaithfulnessReport]:
    """Join biased responses with judge labels and compute per-(model, shot) reports.

    Every biased response is passed through so susceptibility (moved / eligible) is
    counted over the *full* eligible set; judge labels are merged where present. Only
    moved rows need a label — compute_unfaithfulness enforces that — and the judge
    pass labels every moved case. Filtering to labeled rows here would silently
    collapse the eligibility denominator onto the moved set.
    """
    responses = load_jsonl(config.responses_path, ConditionResult)
    labels = {
        (lb.item_id, lb.model, lb.shot): lb for lb in load_jsonl(config.labels_path, Label)
    }
    biased: list[ConditionResult] = []
    for r in responses:
        if not r.biased:
            continue
        lb = labels.get((r.item_id, r.model, r.shot))
        if lb is not None:
            r = r.model_copy(
                update={
                    "references_suggestion": lb.references_suggestion,
                    "evidence": lb.evidence,
                }
            )
        biased.append(r)
    return compute_reports(biased)


def _complete_condition(
    config: RunConfig,
    model: str,
    ex: Example,
    shot: int,
    biased: bool,
    demos: list[Demo],
    x_map: dict[str, str],
) -> ConditionResult:
    """Run a single (model, item, shot, biased) completion into a ConditionResult."""
    x = x_map[ex.id]
    messages = build_messages(ex, demos, suggested_letter=x if biased else None)
    completion = complete(
        messages, model=model, max_tokens=config.max_tokens, reasoning=SUBJECT_REASONING
    )
    return ConditionResult(
        item_id=ex.id,
        subject=ex.metadata["subject"],
        model=model,
        shot=shot,
        biased=biased,
        gold=ex.answer,
        suggested_letter=x,
        raw_completion=completion,
        parsed_answer=extract_answer(completion),
    )


def run_phase1(config: RunConfig) -> list[FaithfulnessReport]:
    """Execute the full pipeline end to end and return the reports."""
    items = load_items(config)
    items_by_id = {ex.id: ex for ex in items}
    x_map = sample_x_map(items, config.seed)

    run_baseline(config, items, x_map)
    print(f"[phase] baseline done; cost so far ${METER.total_cost():.4f}", flush=True)

    baseline = load_jsonl(config.responses_path, ConditionResult)
    surviving = clean_correct_intersection(baseline, config.models)
    print(f"[phase] surviving (clean-correct intersection): {len(surviving)} items", flush=True)

    demos = build_all_demos(config)
    print(f"[phase] demos done; cost so far ${METER.total_cost():.4f}", flush=True)

    run_conditions(config, items_by_id, surviving, x_map, demos)
    print(f"[phase] conditions done; cost so far ${METER.total_cost():.4f}", flush=True)

    run_judge(config, items_by_id)
    print(f"[phase] judge done; cost so far ${METER.total_cost():.4f}", flush=True)

    print("[cost] per-model spend this run:")
    print(format_meter(), flush=True)
    return build_report(config)
