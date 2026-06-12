"""Unit tests for the markdown table formatters."""

from cot_unfaithfulness.metrics.agreement import cohen_kappa
from cot_unfaithfulness.metrics.faithfulness import FaithfulnessReport, PooledReport
from cot_unfaithfulness.metrics.tables import (
    fmt_ci,
    fmt_rate,
    judge_validation_md,
    per_model_shot_table,
    pooled_table,
)
from cot_unfaithfulness.metrics.validation import Disagreement, ValidationScore

NAMES = {"openrouter/anthropic/claude-opus-4.8": "Opus"}


def _report(model, shot, *, eligible, moved, silent, verbalized):
    return FaithfulnessReport(
        model=model,
        shot=shot,
        n_items=eligible,
        n_eligible=eligible,
        n_moved=moved,
        n_silent=silent,
        n_verbalized=verbalized,
        unfaithfulness_rate=(silent / moved if moved else None),
        susceptibility=(moved / eligible if eligible else None),
    )


def _pooled(model, *, eligible, moved, silent, verbalized, ci=None):
    return PooledReport(
        model=model,
        n_eligible=eligible,
        n_moved=moved,
        n_silent=silent,
        n_verbalized=verbalized,
        n_unmoved=eligible - moved,
        susceptibility=(moved / eligible if eligible else None),
        unfaithfulness_rate=(silent / moved if moved else None),
        ci_low=ci[0] if ci else None,
        ci_high=ci[1] if ci else None,
    )


def _score(*, key_rows, disagreements=()):
    """key_rows: list of (human, judge, moved) triples."""
    overall = cohen_kappa([h for h, _, _ in key_rows], [j for _, j, _ in key_rows])
    moved = [(h, j) for h, j, m in key_rows if m]
    return ValidationScore(
        n_labeled=len(key_rows),
        n_moved=len(moved),
        overall=overall,
        moved_only=(
            cohen_kappa([h for h, _ in moved], [j for _, j in moved]) if moved else None
        ),
        disagreements=list(disagreements),
    )


def test_fmt_rate():
    assert fmt_rate(None) == "—"
    assert fmt_rate(2 / 3) == "0.667"
    assert fmt_rate(1.0) == "1.000"


def test_fmt_ci():
    assert fmt_ci(None, None) == "—"
    assert fmt_ci(0.0614, 0.7924) == "[0.061, 0.792]"


def test_per_model_shot_table_exact_output():
    reports = [
        _report(
            "openrouter/anthropic/claude-opus-4.8", 0,
            eligible=332, moved=1, silent=1, verbalized=0,
        ),
        _report("x/y/other-model", 3, eligible=4, moved=0, silent=0, verbalized=0),
    ]
    assert per_model_shot_table(reports, NAMES) == (
        "# Per (model, shot)\n"
        "\n"
        "| model | shot | eligible | moved | susceptibility | silent | verbalized "
        "| unfaithfulness |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| Opus | 0 | 332 | 1 | 0.003 | 1 | 0 | 1.000 |\n"
        "| other-model | 3 | 4 | 0 | 0.000 | 0 | 0 | — |\n"
    )


def test_pooled_table_exact_output():
    pooled = [
        _pooled(
            "openrouter/anthropic/claude-opus-4.8",
            eligible=996, moved=3, silent=1, verbalized=2, ci=(0.0614, 0.7924),
        ),
        _pooled("x/y/other-model", eligible=10, moved=0, silent=0, verbalized=0),
    ]
    assert pooled_table(pooled, NAMES) == (
        "# Pooled across shots\n"
        "\n"
        "| model | eligible | moved | susceptibility | silent | verbalized "
        "| unfaithfulness | 95% CI |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| Opus | 996 | 3 | 0.003 | 1 | 2 | 0.333 | [0.061, 0.792] |\n"
        "| other-model | 10 | 0 | 0.000 | 0 | 0 | — | — |\n"
    )


def test_judge_validation_md_all_moved_suppresses_overall():
    score = _score(
        key_rows=[
            (True, True, True), (False, False, True),
            (True, False, True), (False, False, True),
        ],
        disagreements=[
            Disagreement(
                row=2, model="a/b/llama", shot=1, moved=True,
                human=True, judge=False, judge_evidence="",
            )
        ],
    )
    md = judge_validation_md(score)
    assert "## Moved-only\n" in md
    assert "Overall" not in md
    assert "| n | 4 |" in md
    assert "| observed agreement | 0.750 (3/4) |" in md
    assert "| human true / judge false | 1 |" in md
    assert "| 2 | llama | 1 | yes | true | false |  |" in md
    assert md.endswith("\n") and not md.endswith("\n\n")


def test_judge_validation_md_mixed_shows_both_sections():
    score = _score(
        key_rows=[(True, True, True), (False, False, True), (False, False, False)],
    )
    md = judge_validation_md(score)
    assert "## Moved-only" in md
    assert "## Overall" in md
    assert "None — perfect agreement on labeled rows." in md


def test_judge_validation_md_no_moved_rows_overall_is_primary():
    score = _score(key_rows=[(True, True, False), (False, False, False)])
    md = judge_validation_md(score)
    assert "## Overall" in md
    assert "Moved-only" not in md


def test_judge_validation_md_escapes_evidence():
    score = _score(
        key_rows=[(True, False, True), (False, False, True)],
        disagreements=[
            Disagreement(
                row=0, model="m", shot=0, moved=True,
                human=True, judge=False, judge_evidence="a | b\nc",
            )
        ],
    )
    md = judge_validation_md(score)
    assert r"a \| b c" in md
