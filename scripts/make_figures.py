"""Render the Phase 1 headline figure from a run's results.

Pools faithfulness counts across shots per model and draws two panels:
susceptibility as stacked silent/verbalized/unmoved bars, and the
unfaithfulness rate U = silent / moved with Wilson 95% CIs.

    uv run python scripts/make_figures.py --results-dir results
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yeginbay_palette as yp
from matplotlib.figure import Figure

from cot_unfaithfulness.config import SUBJECT_MODELS, display_name
from cot_unfaithfulness.experiment.records import ConditionResult, Label
from cot_unfaithfulness.experiment.runner import merge_labels
from cot_unfaithfulness.experiment.store import load_jsonl
from cot_unfaithfulness.metrics.faithfulness import PooledReport, compute_reports, pool_by_model

# yeginbay style: serif chrome, hidden top/right spines, transparent savefig,
# and the categorical cycle — all from palette.toml (the single color source).
PALETTE = yp.apply_style()
COLOR_SILENT = PALETTE.accent("primary")  # dusty mauve — the finding
COLOR_VERBALIZED = PALETTE.accent("secondary")  # lighter mauve — the honest thin band
COLOR_UNMOVED = PALETTE.neutral("gray_light")  # recessive context
COLOR_GRAY = PALETTE.neutral("gray")  # annotation arrow + text

plt.rcParams["svg.hashsalt"] = "cot-unfaithfulness"  # deterministic SVG element ids

# Strip run timestamps so regenerating an unchanged figure produces no git diff.
_METADATA = {"svg": {"Date": None}, "pdf": {"CreationDate": None}}


def render_figure(pooled: list[PooledReport]) -> Figure:
    names = [display_name(p.model) for p in pooled]
    x = range(len(pooled))
    n = pooled[0].n_eligible
    assert all(p.n_eligible == n for p in pooled), "models have unequal eligible sets"

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    silent = [p.n_silent for p in pooled]
    verbalized = [p.n_verbalized for p in pooled]
    unmoved = [p.n_unmoved for p in pooled]
    ax1.bar(x, silent, color=COLOR_SILENT, label="silent")
    ax1.bar(x, verbalized, bottom=silent, color=COLOR_VERBALIZED, label="verbalized")
    bottoms = [s + v for s, v in zip(silent, verbalized, strict=True)]
    ax1.bar(x, unmoved, bottom=bottoms, color=COLOR_UNMOVED, label="unmoved")
    ax1.set_xticks(list(x), names)
    ax1.set_ylabel(f"samples (of {n})")
    ax1.set_title("Susceptibility ($S_i$)")
    for i, p in enumerate(pooled):
        # call out moved stacks too thin to see against the unmoved mass
        if p.n_moved < 0.02 * n:
            ax1.annotate(
                f"moved = {p.n_moved}",
                xy=(i, p.n_moved),  # onto the sliver
                xytext=(i + 0.25, 0.11 * n),  # text in the white gutter
                ha="left",
                arrowprops=dict(arrowstyle="->", color=COLOR_GRAY),
                fontsize=9,
                color=COLOR_GRAY,
            )
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)

    measured = [(i, p) for i, p in enumerate(pooled) if p.unfaithfulness_rate is not None]
    if measured:
        xs = [i for i, _ in measured]
        rates = [p.unfaithfulness_rate for _, p in measured]
        yerr = [
            [r - p.ci_low for r, (_, p) in zip(rates, measured, strict=True)],
            [p.ci_high - r for r, (_, p) in zip(rates, measured, strict=True)],
        ]
        ax2.errorbar(
            xs, rates, yerr=yerr, fmt="o", capsize=3, color=COLOR_SILENT, ecolor=COLOR_SILENT
        )
    ax2.set_ylabel("U = silent / moved")
    ax2.set_title("Unfaithfulness ($U_i$)")
    ax2.set_xticks(
        list(x),
        [
            f"{nm}\n{p.n_silent} out of {p.n_moved} moved"
            for nm, p in zip(names, pooled, strict=True)
        ],
    )
    ax2.set_ylim(0, 1)
    ax2.set_xlim(-0.5, len(pooled) - 0.5)
    ax2.yaxis.grid(True, alpha=0.15)

    fig.tight_layout()
    return fig


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, default=Path("results"))
    ap.add_argument("--out-dir", type=Path, default=None, help="default: <results-dir>/figures")
    ap.add_argument("--formats", default="png,pdf,svg")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()
    out_dir = args.out_dir or args.results_dir / "figures"

    responses = load_jsonl(args.results_dir / "responses.jsonl", ConditionResult)
    labels = load_jsonl(args.results_dir / "labels.jsonl", Label)
    pooled = pool_by_model(compute_reports(merge_labels(responses, labels)))
    order = {m: i for i, m in enumerate(SUBJECT_MODELS)}
    pooled.sort(key=lambda p: order.get(p.model, len(order)))

    print(f"{'model':<8} {'silent':>6} {'verbalized':>10} {'moved':>6} {'eligible':>8}")
    for p in pooled:
        print(
            f"{display_name(p.model):<8} {p.n_silent:>6} {p.n_verbalized:>10}"
            f" {p.n_moved:>6} {p.n_eligible:>8}"
        )

    fig = render_figure(pooled)
    out_dir.mkdir(parents=True, exist_ok=True)
    for fmt in args.formats.split(","):
        path = out_dir / f"susceptibility_unfaithfulness.{fmt}"
        fig.savefig(path, dpi=args.dpi, metadata=_METADATA.get(fmt))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
