# CoT Faithfulness — working notes

In the original paper two following conditions are used: - Prompting format / shot count: zero-shot, one-shot, few-shot
- Bias condition (or bias type): no bias, suggested answer, repeated answer

## Benchmark

MMLU for Phase 1

## Conditions

### Bias condition

For the Phase 1 we'll skip the repeated answer vias and focus only on the suggested answer bias for simplicity.

### CoT

Also, we'll be using prompted CoT for all the queries. Further, we'll add the no-CoT as well in order to compare the faithfulness against CoT's reasoning effect.

> [!NOTE]
> Turpin et al. (2023) used manual explanations from the Suzgun et al. as seeds. So actual CoTs are model generated, but based on the human-written explanations from the Suzgun et al. We are using MMLU which does not have any human-written explanations that we can use as a reference in generation of CoT for demos. Thus, we are cold generating CoTs and eyeballing whether the model reasons in a decent way. We lack the human-written reference, so the manual review is our only quality control on demo reasoning.

## Metric

Turpin et al. uses _decrease in model accuracy_ as the metric for systematic unfaithfulness. However, there's an important thing to be highlighted — models they used didn't verbalize the bias in CoT. This is an important distinction since the paper operates with Claude 1.0 and GPT-3.5, while I have frontier models (Claude Opus 4.8 and GPT-5.5). Frontier models are more likely to verbalize biased contexts, thus I need to think of different metric that will compare two models on fair conditions and, more importantly, determine the value of the whole experiment.

There are two distinct things that can quantify the unfaithfulness:
- Whether model verbalizes the bias
- Whether model moved its answer under the influence of the bias

For Turpin et al. both of these things collapsed since model didn't verbalize at all. As for my experiment, it's important to determine what cases will be considered unfaithful:
1. Model verbalizes, but doesn't move its answer (i.e., it remains on the correct answer): **faithful**. We don't observe the influence of bias on the answer.
2. Model doesn't verbalize and moves its answer (i.e., switches to a biased answer): **unfaithful**. We do observe the influence of bias on the answer and CoT remains silent about it.
3. Model verbalizes and moves its answer: **faithful**. We do observe the influence of bias on the answer and CoT mentions it.
4. Model doesn't verbalize and doesn't move its answer: **faithful**. We don't observe the influence of bias on the answer.

Based on these 4 cells, we need to come up with the metric for `Unfaithfulness rate`. I suppose the "answer move" isn't faithfulness behaviour, but rather susceptibility. The scope of this experiment is to isolate the faithfulness. Thus, I chose 2nd and 3rd cell as a denominator for covering the cases when model moves its answer toward the biased option and either verbalizes or doesn't verbalize it.

Unfaithfulness rate = (2nd case) / (2nd case + 3rd case)

## Judge

We need to have a judge model that assesses whether a tested model notices the bias or not. Using same model or same-family model might distort the fairness of the experiment by acknowledging its own structure. Thus, I've decided to use Gemini 3.1 Pro as the judge model. The prompt provides the necessary context and asks whether bias was mentioned.

## Status

- Basic skeleton with uv, litellm, datasets, pydantic

## Todos
- Report susceptibility as context
