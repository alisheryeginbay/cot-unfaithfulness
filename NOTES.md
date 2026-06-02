# CoT Faithfulness — working notes

## Overview

In the original paper two following conditions are used: - Prompting format / shot count: zero-shot, one-shot, few-shot
- Bias condition (or bias type): no bias, suggested answer, repeated answer

Benchmark: MMLU for Phase 1

For the Phase 1 we'll skip the repeated answer vias and focus only on the suggested answer bias for simplicity.

Also, we'll be using prompted CoT for all the queries. Further, we'll add the no-CoT as well in order to compare the faithfulness against CoT's reasoning effect.

Turpin et al. (2023) used manual explanations from the Suzgun et al. as seeds. So actual CoTs are model generated, but based on the human-written explanations from the Suzgun et al. We are using MMLU which does not have any human-written explanations that we can use as a reference in generation of CoT for demos. Thus, we are cold generating CoTs and eyeballing whether the model reasons in a decent way. We lack the human-written reference, so the manual review is our only quality control on demo reasoning.

## Status

- Basic skeleton with uv, litellm, datasets, pydantic
