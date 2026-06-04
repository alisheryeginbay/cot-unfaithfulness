"""Unit tests for Cohen's kappa (judge validation agreement)."""

import math

from cot_unfaithfulness.metrics.agreement import cohen_kappa


def test_perfect_agreement():
    h = [True, False, True, False]
    r = cohen_kappa(h, list(h))
    assert r.observed_agreement == 1.0
    assert r.cohen_kappa == 1.0
    assert r.both_true == 2 and r.both_false == 2


def test_chance_level_agreement_is_zero_kappa():
    # 2x2 with equal marginals and off-diagonal balancing -> kappa 0
    human = [True, True, False, False]
    judge = [True, False, True, False]
    r = cohen_kappa(human, judge)
    assert r.observed_agreement == 0.5
    assert math.isclose(r.cohen_kappa, 0.0, abs_tol=1e-9)


def test_partial_agreement_known_value():
    # human: 3T/1F, judge: 2T/2F; tt=2, tf=1, ft=0, ff=1
    human = [True, True, True, False]
    judge = [True, True, False, False]
    r = cohen_kappa(human, judge)
    assert r.n_agree == 3
    assert math.isclose(r.observed_agreement, 0.75)
    # p_e = 0.75*0.5 + 0.25*0.5 = 0.5 ; kappa = (0.75-0.5)/0.5 = 0.5
    assert math.isclose(r.cohen_kappa, 0.5, abs_tol=1e-9)


def test_degenerate_single_class_kappa_none():
    # judge always False, human always False -> p_e == 1 -> kappa undefined
    r = cohen_kappa([False, False, False], [False, False, False])
    assert r.observed_agreement == 1.0
    assert r.cohen_kappa is None
