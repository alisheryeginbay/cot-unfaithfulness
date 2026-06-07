# CoT Unfaithfulness

Reproduction of Turpin et al. 2023, *"Language Models Don't Always Say What They
Think: Unfaithful Explanations in Chain-of-Thought Prompting,"* on modern models.

The experiment injects a **biasing feature** into a prompt — a user-suggested
answer (`"I think the answer is (X)…"`) — then measures, when the model flips to
that biased answer, how often its chain of thought **fails to disclose the
suggestion** (silent) versus acknowledges it (verbalized).

**Phase 1** (current): suggested-answer bias on **MMLU**, comparing a frontier
subject (`claude-opus-4.8`) against a weak baseline (`llama-3.1-8b-instruct`),
with `gemini-3.1-pro-preview` as an independent verbalization judge.

## Method (summary)

- **Subjects** run with native reasoning **off** — the study is of *visible,
  prompted* CoT, not a hidden reasoning channel.
- **Conditions:** shots {0, 1, 3} × {unbiased baseline, suggested-answer}. The
  suggested option `X` is sampled uniformly per item and reused across conditions.
- **Clean-correct filter:** analysis is restricted to items both subjects answer
  correctly in the zero-shot unbiased baseline (so a "move" is a genuine flip).
- **Metrics:** *susceptibility* = moved / eligible; *unfaithfulness* =
  silent / moved, where a move is `answer == X and X != gold`.
- **Judge validation:** the silent-vs-verbalized split is the headline number, so
  the judge is validated against blind human labels (Cohen's κ) before it is
  trusted — see the validation harness below.

Full locked methodology and rationale:
[`docs/superpowers/specs/2026-06-02-phase1-suggested-answer-mmlu-design.md`](docs/superpowers/specs/2026-06-02-phase1-suggested-answer-mmlu-design.md).

## Stack

- [`uv`](https://docs.astral.sh/uv/) — project & dependency management
- [`litellm`](https://docs.litellm.ai/) — model calls, via **OpenRouter**
- [`datasets`](https://huggingface.co/docs/datasets/) — MMLU (`cais/mmlu`)
- `pydantic` — typed config and records

## Setup

```bash
uv sync
cp .env.example .env   # then add your OPENROUTER_API_KEY
```

## Usage

```bash
# Smoke run (a few items/subject) to validate the pipeline cheaply:
uv run cot-unfaithfulness --results-dir scratch/smoke --limit 2 --workers 6

# Full Phase 1 run (resumable; skips anything already on disk):
uv run cot-unfaithfulness --results-dir results --workers 6
```

The run is **resumable and crash-safe** — each phase (baseline → demos →
conditions → judge) appends to JSONL and skips completed work on restart. A live
per-model cost meter prints as it goes.

### Judge validation (run before trusting any rate)

```bash
# 1. export a blind, class-stratified labeling sheet over the moved cases:
uv run python scripts/judge_validation.py export --results-dir results
# 2. hand-label results/validation_answers.csv (true/false per row)
#    (do NOT open validation_key.json until done)
# 3. score: observed agreement + Cohen's kappa + disagreements
uv run python scripts/judge_validation.py score  --results-dir results
```

## Layout

```
src/cot_unfaithfulness/
  config.py                 # ExperimentConfig, BiasType, Dataset, Phase 1 constants
  data/schema.py            # Example, MCQChoice
  data/loaders.py           # load_mmlu, row_to_example
  prompts/builder.py        # build_messages, render_question
  prompts/bias.py           # suggested_hint, sample_suggested_letter
  models/client.py          # complete (LiteLLM/OpenRouter), CostMeter, watchdog timeout
  parsing/extract.py        # extract_answer
  judge.py                  # verbalization judge (build/parse/label)
  experiment/
    runner.py               # run_phase1 + phases (baseline, demos, conditions, judge, report)
    demos.py                # resample-until-correct few-shot demo generation
    records.py              # ConditionResult, Label, DemoRecord
    store.py                # crash-safe JSONL persistence
  metrics/
    faithfulness.py         # compute_unfaithfulness, FaithfulnessReport
    agreement.py            # cohen_kappa (judge validation)
  cli.py                    # main entry point

scripts/                    # operational tooling (cost projection, judge finisher,
                            #   validation harness, diagnostics)
docs/superpowers/specs/     # design docs
```

## Development

```bash
uv run pytest      # unit tests
uv run ruff check  # lint
```

## Results

Forthcoming — see `RESULTS.md` (in progress).
