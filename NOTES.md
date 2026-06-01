# CoT Faithfulness — working notes

## Overview

In the original paper two following conditions are used: - Prompting format / shot count: zero-shot, one-shot, few-shot
- Bias condition (or bias type): no bias, suggested answer, repeated answer

Benchmark: MMLU for Phase 1

For the Phase 1 we'll skip the repeated answer vias and focus only on the suggested answer bias for simplicity.

Also, we'll be using prompted CoT for all the queries. Further, we'll add the no-CoT as well in order to compare the faithfulness against CoT's reasoning effect.

## Status

- Basic skeleton with uv, litellm, datasets, pydantic
