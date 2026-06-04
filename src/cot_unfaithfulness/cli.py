"""Command-line entry point.

Drives the Phase 1 pipeline. Use ``--limit`` for a cheap smoke run over a few
items per subject before committing to a full run.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from cot_unfaithfulness.experiment.runner import RunConfig, run_phase1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cot-unfaithfulness",
        description="Run the Phase 1 CoT faithfulness experiment.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Smoke mode: cap items per subject (e.g. 2). Omit for the full run.",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    config = RunConfig(
        results_dir=args.results_dir,
        workers=args.workers,
        seed=args.seed,
        max_tokens=args.max_tokens,
        limit=args.limit,
    )
    reports = run_phase1(config)
    for r in sorted(reports, key=lambda x: (x.model, x.shot)):
        rate = "n/a" if r.unfaithfulness_rate is None else f"{r.unfaithfulness_rate:.2f}"
        susc = "n/a" if r.susceptibility is None else f"{r.susceptibility:.2f}"
        print(
            f"{r.model:42s} shot={r.shot} "
            f"items={r.n_items:4d} moved={r.n_moved:3d} "
            f"unfaithful={rate} susceptibility={susc}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
