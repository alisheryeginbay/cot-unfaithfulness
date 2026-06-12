I've been maintaining the @NOTE.md file to have a place to write down the overall picture that experiment is taking at the moment but I realized that I didn't have any file where I can go beyond just writing up the final decision but rather the *thinking* behind certain decision.

I've been using separate scratch notes to think about the matters I've been facing while doing the experiment. But I suppose it'll be better to store them as artifacts that I can reread later on. Thus, this file is a raw writing of my thoughts. This file is **append-only**.

The format is:

```md
*YYYY-MM-DD*

<note>
```

> [!IMPORTANT]
> This file is only for the personal usage, thus, AI writing isn't allowed to be used here.

---

*2026-06-12*

We have two related rates for **susceptibility** and **unfaithfulness**. Unfaithfulness is a rate that's dependent on model's susceptibility, i.e., we measure the unfaithfulness rate based on the "moved" answers and then assess whether the model verbalized them or not.

Thus, we need to find a way to show this *gated* relationship in a figure.

The susceptibility and unfaithfulness rates:

$$
\begin{aligned}
S &= \frac{N_{\text{moved}}}{N_{\text{eligible}}} \\
U &= \frac{N_{\text{silent}}}{N_{\text{moved}}}
\end{aligned}
$$

Putting the pooled results from the experiment, we can observe two rates:
- For Opus 4.8, $S$ is going to be **very low**. $S_{\text{Opus, pooled}} = 3 / 996 \approx 0.003$.
- For Llama 3.1 8B, $S$ is going to be **substantially** higher. $S_{\text{Llama, pooled}} = 224 / 996 \approx 0.225$.


As for the $U$:
- For Opus 4.8, $U_{\text{Opus, pooled}} = 1 / 3 \approx 0.333$
- For Llama 3.1 8B, $U_{\text{Llama, pooled}} = 219 / 224 \approx 0.978$

However, it should be noted that these $U$ values tell nothing about the real unfaithfulness for the Opus 4.8, since $N_{\text{moved}}$ is markedly low. This is an important factor when presenting the figure in a blog post, therefore, we need to distinctly show it.

To be honest, I had no idea what kind of chart or graph could be good in doing this work, so after chatting with Claude I decided to use Confidence interval error bars. It captures the fact that $N_{\text{moved}}$ is noticeably small and that unfaithfulness rate for the Opus 4.8 should be read with caution.

---

Okay, I probably spent more than normal on trying to come up with a visualization form for the data. However, I think it's still a good skill to develop — that is, to be able to present the results in a comprehensible way, so that it clearly shows what matters.

Let's start from labelling what kinds of data we have in our pipeline. 

We start from `eligible` items, then test them on our biasing injections. Thus, `eligible` items split further into `moved` and `unmoved` groups.

For the faithfulness, we care about whether `moved` items were verbalized or not, thus, it splits even further into `moved-silent` and `moved-verbalized`.

From these, we can see that we have 3 groups: `moved-silent`, `moved-verbalized` and `unmoved`.

---

For each model $i \in {\text{Opus}, \text{Llama}}$, let the $M_i$ and $K_i$ denote the number of moved and silent samples, respectively, among the $N = 996$ eligible ones, so that $S_i = \frac{M_i}{N}$ and $U_i = \frac{K_i}{M_i}$.

The observed values:
$$
\begin{aligned}
M_{\text{Opus}}  &= 3,   & K_{\text{Opus}}  &= 1, \\
M_{\text{Llama}} &= 224, & K_{\text{Llama}} &= 219.
\end{aligned}
$$

Let's split the figure into two panels that cover $S_i$ and $U_i$.

Panel A is going to show $S_i$ by showing `moved-silent`, `moved-verbalized` and `unmoved` groups. These groups will be represented using bar stacks per model $i$.

However, the thing that's missing from this graph is that $M_{\text{Opus}}$ being squished into a one pixel, which doesn't help to see $U_i$ clearly. Thus, we need a second panel that covers that.

Panel B is going to show $U_i$ by showing the rate for each model $i$. However, there is an issue we still need to address: **rates don't take in the factor the $M_i$**, i.e., $1 / 3$ and $100 / 300$ might be treated the same way. We can use Wilson intervals to show the level of uncertainty.

Previously, I considered representing the Panel B using bars and using its width as a proportion of `moved` sample size per model to maximum value of `moved` sample size across two models. This way I could've highlight the small sample size — however, I then realized that this geometric representation carries a small value overall since Wilson interval already cover the level of uncertainty, which, by our results, is because of the small sample size.

---

Now that the main figure is done, we can focus on supporting tables:
- Per `(model, shot)` pair information. This includes: `eligible`, `moved`, `susceptibility`, `silent`, `verbalized`, `unfaithfulness`. 
- Pooled data. The same columns as above. 
- Judge validation.

These are the things that come to my mind first, though I might be missing something.
