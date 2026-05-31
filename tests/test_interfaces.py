"""Skeleton interface tests.

Assert the public interfaces exist and are importable. Bodies are stubs that
raise NotImplementedError, so these tests guard structure, not behavior.
"""

import inspect

import pytest


def test_config_imports():
    from cot_unfaithfulness.config import BiasType, Dataset, ExperimentConfig

    cfg = ExperimentConfig()
    assert cfg.bias_type is BiasType.NONE
    assert cfg.dataset is Dataset.BBH
    assert cfg.model.startswith("openrouter/")


def test_schema_imports():
    from cot_unfaithfulness.data.schema import Example, MCQChoice

    ex = Example(
        id="1",
        question="q",
        choices=[MCQChoice(letter="A", text="a")],
        answer="A",
    )
    assert ex.choices[0].letter == "A"


@pytest.mark.parametrize(
    "module_path,callable_name",
    [
        ("cot_unfaithfulness.data.loaders", "load_bbh"),
        ("cot_unfaithfulness.data.loaders", "load_bbq"),
        ("cot_unfaithfulness.prompts.builder", "build_prompt"),
        ("cot_unfaithfulness.prompts.bias", "apply_suggested_answer"),
        ("cot_unfaithfulness.prompts.bias", "apply_answer_always_a"),
        ("cot_unfaithfulness.models.client", "complete"),
        ("cot_unfaithfulness.parsing.extract", "extract_answer"),
        ("cot_unfaithfulness.experiment.runner", "run_experiment"),
        ("cot_unfaithfulness.metrics.faithfulness", "compute_unfaithfulness"),
    ],
)
def test_callable_exists(module_path, callable_name):
    import importlib

    module = importlib.import_module(module_path)
    fn = getattr(module, callable_name)
    assert callable(fn)
    # Each stub declares a signature even though it isn't implemented yet.
    assert inspect.signature(fn) is not None


def test_cli_parser_builds():
    from cot_unfaithfulness.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["--bias-type", "suggested_answer", "--n-samples", "5"])
    assert args.bias_type.value == "suggested_answer"
    assert args.n_samples == 5
