# CoT Faithfulness — working notes

## Overview

We have two following conditions:
- Prompting format / shot count: zero-shot, one-shot, few-shot
- Bias condition (or bias type): no bias, suggested answer, repeated answer

We're using prompted CoT for all the conditions. Further, we'll add the condition of no CoT present to compare the faithfulness against CoT's reasoning effect.

## Status

Done: basic skeleton with uv, litellm, datasets, pydantic
Next: choose the amount of queries/demos per subject/task

## Open Questions

- [ ] how many demos for always-A (repeated answer)?
