# CoT Unfaithfulness

Reproduction of Turpin et al. 2023, *"Language Models Don't Always Say What They
Think: Unfaithful Explanations in Chain-of-Thought Prompting."*

The experiment injects a **biasing feature** into few-shot CoT prompts (e.g. a
user-suggested answer, or reordering exemplars so the answer is always option A),
then measures how often the model flips to the biased answer *without*
acknowledging the bias in its chain of thought.

> **Status:** skeleton. Project structure, typed config, and module interfaces are
> in place; experiment logic, prompts, dataset mapping, and metrics are stubs.

## Stack

- [`uv`](https://docs.astral.sh/uv/) for project & dependency management
- [`litellm`](https://docs.litellm.ai/) for model calls, via **OpenRouter**
- [`datasets`](https://huggingface.co/docs/datasets/) for BBH / BBQ data
- `pydantic` for typed config and records

## Setup

```bash
uv sync
cp .env.example .env   # then add your OPENROUTER_API_KEY
```

## Usage

```bash
uv run cot-unfaithfulness --bias-type suggested_answer --dataset bbh --n-samples 50
```

(The CLI parses into an `ExperimentConfig` and dispatches to the runner, which is
currently a stub.)

## Layout

```
src/cot_unfaithfulness/
  config.py              # ExperimentConfig, BiasType, Dataset
  data/schema.py         # Example, MCQChoice
  data/loaders.py        # load_bbh, load_bbq
  prompts/builder.py     # build_prompt
  prompts/bias.py        # apply_suggested_answer, apply_answer_always_a
  models/client.py       # complete (LiteLLM/OpenRouter)
  parsing/extract.py     # extract_answer
  experiment/runner.py   # run_experiment, Result
  metrics/faithfulness.py# compute_unfaithfulness, FaithfulnessReport
  cli.py                 # main entry point
```

See [`docs/superpowers/specs/`](docs/superpowers/specs/) for the design doc.

## Development

```bash
uv run pytest      # interface tests
uv run ruff check  # lint
```
