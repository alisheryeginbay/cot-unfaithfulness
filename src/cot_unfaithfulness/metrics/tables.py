"""Markdown table formatters for the results tables.

Pure report -> str functions: deterministic, rows rendered in the order given
(sorting is the caller's job), each document ends in a single trailing newline.
"""

from __future__ import annotations

from collections.abc import Mapping

from cot_unfaithfulness.metrics.agreement import AgreementReport
from cot_unfaithfulness.metrics.faithfulness import FaithfulnessReport, PooledReport
from cot_unfaithfulness.metrics.validation import ValidationScore

EM_DASH = "—"


def fmt_rate(x: float | None) -> str:
    return EM_DASH if x is None else f"{x:.3f}"


def fmt_ci(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return EM_DASH
    return f"[{low:.3f}, {high:.3f}]"


def _display(model: str, display_names: Mapping[str, str]) -> str:
    return display_names.get(model, model.rsplit("/", 1)[-1])


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def per_model_shot_table(
    reports: list[FaithfulnessReport], display_names: Mapping[str, str]
) -> str:
    rows = [
        [
            _display(r.model, display_names),
            str(r.shot),
            str(r.n_eligible),
            str(r.n_moved),
            fmt_rate(r.susceptibility),
            str(r.n_silent),
            str(r.n_verbalized),
            fmt_rate(r.unfaithfulness_rate),
        ]
        for r in reports
    ]
    header = [
        "model", "shot", "eligible", "moved", "susceptibility",
        "silent", "verbalized", "unfaithfulness",
    ]  # fmt: skip
    return "# Per (model, shot)\n\n" + _table(header, rows)


def pooled_table(pooled: list[PooledReport], display_names: Mapping[str, str]) -> str:
    rows = [
        [
            _display(p.model, display_names),
            str(p.n_eligible),
            str(p.n_moved),
            fmt_rate(p.susceptibility),
            str(p.n_silent),
            str(p.n_verbalized),
            fmt_rate(p.unfaithfulness_rate),
            fmt_ci(p.ci_low, p.ci_high),
        ]
        for p in pooled
    ]
    header = [
        "model", "eligible", "moved", "susceptibility",
        "silent", "verbalized", "unfaithfulness", "95% CI",
    ]  # fmt: skip
    return "# Pooled across shots\n\n" + _table(header, rows)


def _escape_cell(text: str) -> str:
    return " ".join(text.split()).replace("|", r"\|")


def _agreement_section(title: str, rep: AgreementReport) -> str:
    rows = [
        ["n", str(rep.n)],
        ["observed agreement", f"{rep.observed_agreement:.3f} ({rep.n_agree}/{rep.n})"],
        ["Cohen's kappa", fmt_rate(rep.cohen_kappa)],
        ["both true", str(rep.both_true)],
        ["both false", str(rep.both_false)],
        ["human true / judge false", str(rep.human_true_judge_false)],
        ["human false / judge true", str(rep.human_false_judge_true)],
    ]
    return f"## {title}\n\n" + _table(["metric", "value"], rows)


def judge_validation_md(score: ValidationScore) -> str:
    sections = ["# Judge validation\n"]
    if score.moved_only is not None:
        sections.append(_agreement_section("Moved-only", score.moved_only))
        if score.overall.n != score.moved_only.n:
            sections.append(_agreement_section("Overall", score.overall))
    else:
        sections.append(_agreement_section("Overall", score.overall))

    if score.disagreements:
        rows = [
            [
                str(d.row),
                d.model.rsplit("/", 1)[-1],
                str(d.shot),
                "yes" if d.moved else "no",
                str(d.human).lower(),
                str(d.judge).lower(),
                _escape_cell(d.judge_evidence or ""),
            ]
            for d in score.disagreements
        ]
        header = ["row", "model", "shot", "moved", "human", "judge", "judge evidence"]
        sections.append("## Disagreements\n\n" + _table(header, rows))
    else:
        sections.append("## Disagreements\n\nNone — perfect agreement on labeled rows.\n")

    return "\n".join(sections)
