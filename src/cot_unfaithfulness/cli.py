"""Command-line entry point.

Parses experiment arguments into an `ExperimentConfig` and dispatches to the
runner.
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from cot_unfaithfulness.config import BiasType, Dataset, ExperimentConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cot-unfaithfulness",
        description="Run a chain-of-thought faithfulness experiment.",
    )
    parser.add_argument("--model", default=ExperimentConfig.model_fields["model"].default)
    parser.add_argument("--dataset", type=Dataset, choices=list(Dataset), default=Dataset.MMLU)
    parser.add_argument("--task", default=None, help="MMLU subject; omit for all Phase 1 subjects.")
    parser.add_argument(
        "--bias-type", type=BiasType, choices=list(BiasType), default=BiasType.NONE
    )
    parser.add_argument("--n-samples", type=int, default=150)
    parser.add_argument("--few-shot-k", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=0.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    config = ExperimentConfig(
        model=args.model,
        dataset=args.dataset,
        task=args.task,
        bias_type=args.bias_type,
        n_samples=args.n_samples,
        few_shot_k=args.few_shot_k,
        temperature=args.temperature,
    )
    from cot_unfaithfulness.experiment.runner import run_experiment

    run_experiment(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
