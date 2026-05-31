# CoT Unfaithfulness Reproduction — Skeleton Design

**Date:** 2026-05-31
**Status:** Approved (skeleton scope)

## Goal

Reproduce the infrastructure for Turpin et al. 2023, *"Language Models Don't Always
Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting."*

The paper injects a **biasing feature** into few-shot CoT prompts and measures how
often a model flips to the biased answer *without* acknowledging the bias in its
chain of thought. This is the unfaithfulness signal.

**This deliverable is skeleton only:** project scaffolding, dependencies, typed
config, and stubbed modules with clear interfaces. No working experiment logic,
prompt text, dataset field-mapping, metric math, or model calls yet.

## Tooling

- **`uv`** project — `pyproject.toml`, `uv.lock`, Python ≥ 3.11
- **Runtime deps:** `litellm` (model calls via OpenRouter), `datasets` (HuggingFace
  data), `pydantic` (typed config/records), `python-dotenv` (API key loading)
- **Dev deps:** `pytest`, `ruff`
- **Model access:** OpenRouter through LiteLLM, using the
  `openrouter/<provider>/<model>` model-string convention and an
  `OPENROUTER_API_KEY` environment variable
- **Config files:** `.env.example` (`OPENROUTER_API_KEY`), `.gitignore`
- **Layout:** `src/` layout; CLI via plain `argparse` (no extra CLI dep)

## Package Layout

`src/cot_unfaithfulness/` — each module is a stub with typed signatures and
docstrings; bodies raise `NotImplementedError`.

| Module | Purpose / interface |
|---|---|
| `config.py` | Pydantic `ExperimentConfig` (model, dataset, task, bias_type, n_samples, few_shot_k, temperature, …) |
| `data/schema.py` | `Example`, `MCQChoice` pydantic models (normalized question representation) |
| `data/loaders.py` | `load_bbh(task)`, `load_bbq(...)` → lists of normalized `Example` records |
| `prompts/builder.py` | `build_prompt(example, config)` — assembles few-shot CoT prompt |
| `prompts/bias.py` | `apply_suggested_answer(...)`, `apply_answer_always_a(...)` — bias injectors |
| `models/client.py` | `complete(messages, config)` — thin LiteLLM/OpenRouter wrapper |
| `parsing/extract.py` | `extract_answer(text)` — pull final letter choice from CoT output |
| `experiment/runner.py` | `run_experiment(config)` — orchestrates data → prompt → model → parse → records |
| `metrics/faithfulness.py` | `compute_unfaithfulness(baseline, biased)` — flip-rate / bias-match metrics |
| `cli.py` | `main()` entry (argparse) → loads config, calls runner |

## Data Flow

```
loaders → Example → prompts.builder (+ bias injector) → models.client
        → parsing.extract → experiment.runner aggregates Result records → metrics
```

Both bias paradigms (Suggested Answer, Answer-is-Always-A) and both datasets
(BBH, BBQ) are represented as stub interfaces so future work is unblocked, even
though their bodies are not implemented now.

## Testing

`tests/` with one placeholder test per module asserting the public interface
exists and is importable. `pytest` runs green on the skeleton.

## Out of Scope (deferred)

- Actual prompt text and few-shot exemplar construction
- Real HuggingFace dataset field-mapping
- Metric computation logic
- Live model calls
- Result persistence / analysis notebooks
