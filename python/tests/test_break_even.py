"""Tests for the path-level break-even screening engine.

These tests focus on the edge cases the memo explicitly calls out: regimes
where vertical parasitics dominate, where redundancy/thermal overheads sink
otherwise-positive margins, and where measurement-noise classification
matters. The tests exercise the equation (Eq. 2 RHS) directly; they DO NOT
test the PASS/FAIL/MARGINAL policy until the operator has implemented
``VerticalPathEvaluator._classify_decision``.

Once the policy is in place, run:

    cd python && pip install -e .[test] && pytest -v
"""

from __future__ import annotations

import math
import pytest

from logic_folding_reference import (
    DecisionLabel,
    PathDecision,
    ProcessParameters,
    VerticalPathEvaluator,
)


# ---- Helpers ---------------------------------------------------------------


def _baseline_params(**overrides) -> ProcessParameters:
    """Realistic-ish primitives. Values are illustrative only — per memo §7,
    arbitrary RC targets are not credible without measurement. These values
    are tuned to make tests' arithmetic legible, not to claim a process node.
    """
    defaults = dict(
        r_v=10.0,            # Ω
        c_v=0.5e-15,         # F  (0.5 fF)
        r_b=8.0,             # Ω
        c_b=0.4e-15,         # F  (0.4 fF)
        r_drv=200.0,         # Ω
        c_load=5.0e-15,      # F  (5 fF)
        dtau_red_fs=20.0,    # fs
        dtau_thermal_fs=15.0,# fs
        parasitic_noise_floor_fs=10.0,
    )
    defaults.update(overrides)
    return ProcessParameters(**defaults)


# ---- Constructor + dataclass invariants -----------------------------------


def test_process_parameters_rejects_negative_values():
    with pytest.raises(ValueError):
        ProcessParameters(
            r_v=-1.0, c_v=0.5e-15,
            r_b=8.0, c_b=0.4e-15,
            r_drv=200.0, c_load=5.0e-15,
            dtau_red_fs=20.0, dtau_thermal_fs=15.0,
        )


def test_process_parameters_is_frozen():
    p = _baseline_params()
    with pytest.raises(Exception):
        p.r_v = 99.0  # type: ignore[misc]


# ---- Vertical-tax arithmetic (does not depend on policy) ------------------


def test_via_contribution_includes_all_three_elmore_terms():
    """The single-via term must contain R_v·C_load + R_drv·C_v + R_v·C_v.

    This is the term the memo's red-team review made load-bearing — dropping
    R_v·C_v artificially loosens the gate.
    """
    p = _baseline_params(r_v=10.0, c_v=1e-15, r_drv=100.0, c_load=10e-15)
    ev = VerticalPathEvaluator(p)
    # R_v·C_load = 10·10e-15 = 1e-13 s = 100 fs
    # R_drv·C_v  = 100·1e-15 = 1e-13 s = 100 fs
    # R_v·C_v    = 10·1e-15  = 1e-14 s = 10  fs
    # total per via = 210 fs
    expected_one_via_fs = 100.0 + 100.0 + 10.0
    tax_one_via = ev.vertical_tax_fs(n_vertical_vias=1, n_bond_contacts=0)
    # Tax also includes Δτ_red + Δτ_T defaults from the baseline (35 fs).
    assert tax_one_via == pytest.approx(expected_one_via_fs + 35.0)


def test_vertical_tax_is_linear_in_via_count():
    p = _baseline_params()
    ev = VerticalPathEvaluator(p)
    base = ev.vertical_tax_fs(0, 0)  # only red + thermal overhead
    one_via = ev.vertical_tax_fs(1, 0)
    ten_vias = ev.vertical_tax_fs(10, 0)
    per_via = one_via - base
    assert (ten_vias - base) == pytest.approx(10.0 * per_via)


def test_vertical_tax_is_linear_in_bond_count():
    p = _baseline_params()
    ev = VerticalPathEvaluator(p)
    base = ev.vertical_tax_fs(0, 0)
    one_bond = ev.vertical_tax_fs(0, 1)
    five_bonds = ev.vertical_tax_fs(0, 5)
    per_bond = one_bond - base
    assert (five_bonds - base) == pytest.approx(5.0 * per_bond)


def test_negative_contact_counts_rejected():
    ev = VerticalPathEvaluator(_baseline_params())
    with pytest.raises(ValueError):
        ev.vertical_tax_fs(-1, 0)
    with pytest.raises(ValueError):
        ev.vertical_tax_fs(0, -1)


# ---- Edge cases: parasitics dominate --------------------------------------


def test_zero_savings_fails_by_construction():
    """If folding saves zero horizontal delay, no value of N_v ≥ 0 can produce
    a positive margin — the inequality strictly requires Δτ_save > RHS."""
    ev = VerticalPathEvaluator(_baseline_params())
    d = ev.evaluate(
        horizontal_savings_fs=0.0,
        n_vertical_vias=1,
        n_bond_contacts=1,
        l_h_meters=0.0,
    )
    assert d.margin_fs < 0
    assert d.horizontal_savings_fs == 0.0


def test_many_vias_swamp_savings():
    """100 vias on a path that only saves a few hundred fs cannot break even."""
    ev = VerticalPathEvaluator(_baseline_params())
    d = ev.evaluate(
        horizontal_savings_fs=500.0,   # generous horizontal reclaim
        n_vertical_vias=100,           # but folding chops it 100 times
        n_bond_contacts=0,
        l_h_meters=200e-6,
    )
    assert d.margin_fs < 0, (
        "100 vias must dominate a 500 fs savings under the baseline parameters."
    )


def test_thermal_derating_can_flip_marginal_pass_to_fail():
    """A path that algebraically passes with no thermal overhead must FAIL
    once a realistic thermal derate is added — memo §8 makes this the
    central point: burst evidence is not sustained evidence.
    """
    cold = _baseline_params(dtau_thermal_fs=0.0, parasitic_noise_floor_fs=0.0)
    hot = _baseline_params(dtau_thermal_fs=300.0, parasitic_noise_floor_fs=0.0)

    cold_d = VerticalPathEvaluator(cold).evaluate(
        horizontal_savings_fs=350.0, n_vertical_vias=1, n_bond_contacts=0,
        l_h_meters=80e-6,
    )
    hot_d = VerticalPathEvaluator(hot).evaluate(
        horizontal_savings_fs=350.0, n_vertical_vias=1, n_bond_contacts=0,
        l_h_meters=80e-6,
    )
    assert cold_d.margin_fs > 0 and hot_d.margin_fs < 0


def test_redundancy_overhead_strictly_subtracts():
    """Δτ_red enters Eq. 2 RHS with a positive sign, so increasing it reduces
    the margin one-for-one."""
    base = _baseline_params(dtau_red_fs=0.0)
    bumped = _baseline_params(dtau_red_fs=50.0)
    args = dict(
        horizontal_savings_fs=500.0,
        n_vertical_vias=1,
        n_bond_contacts=1,
        l_h_meters=100e-6,
    )
    m_base = VerticalPathEvaluator(base).evaluate(**args).margin_fs
    m_bumped = VerticalPathEvaluator(bumped).evaluate(**args).margin_fs
    assert m_base - m_bumped == pytest.approx(50.0)


def test_vertical_dominated_regime_is_monotone_in_via_count():
    """Once parasitics dominate, adding vias can only hurt — the margin must
    be monotonically non-increasing in ``n_vertical_vias``.
    """
    ev = VerticalPathEvaluator(_baseline_params())
    args = dict(horizontal_savings_fs=200.0, n_bond_contacts=0,
                l_h_meters=50e-6)
    margins = [ev.evaluate(n_vertical_vias=n, **args).margin_fs
               for n in range(0, 11)]
    for i in range(1, len(margins)):
        assert margins[i] <= margins[i - 1]


def test_only_long_paths_can_plausibly_pass():
    """Memo §7: 'If only very long global paths pass, the approach may be a
    niche floorplanning technique, not a standard-cell-level scaling law.'

    Demonstrate this directly: scan l_h-proxy savings linearly; only the
    long-path end has any chance of clearing the vertical tax.
    """
    p = _baseline_params(parasitic_noise_floor_fs=0.0)
    ev = VerticalPathEvaluator(p)
    short = ev.evaluate(horizontal_savings_fs=50.0, n_vertical_vias=2,
                        n_bond_contacts=1, l_h_meters=10e-6)
    long = ev.evaluate(horizontal_savings_fs=5000.0, n_vertical_vias=2,
                       n_bond_contacts=1, l_h_meters=1000e-6)
    assert short.margin_fs < 0 < long.margin_fs


# ---- Batch evaluation -----------------------------------------------------


def test_evaluate_batch_preserves_order_and_count():
    ev = VerticalPathEvaluator(_baseline_params())
    inputs = [
        (100.0, 1, 0, 20e-6),
        (1000.0, 2, 1, 200e-6),
        (50.0, 5, 2, 10e-6),
    ]
    out = ev.evaluate_batch(inputs)
    assert len(out) == len(inputs)
    for d, (sav, nv, nb, lh) in zip(out, inputs):
        assert d.horizontal_savings_fs == sav
        assert d.n_vertical_vias == nv
        assert d.n_bond_contacts == nb
        assert d.l_h_meters == lh


def test_negative_savings_rejected():
    ev = VerticalPathEvaluator(_baseline_params())
    with pytest.raises(ValueError):
        ev.evaluate(horizontal_savings_fs=-10.0, n_vertical_vias=1,
                    n_bond_contacts=0, l_h_meters=0.0)


# ---- Policy tests (skipped until operator implements _classify_decision) --


def _policy_implemented() -> bool:
    try:
        VerticalPathEvaluator(_baseline_params())._classify_decision(0.0)
        return True
    except NotImplementedError:
        return False
    except Exception:
        return True


pytestmark_policy = pytest.mark.skipif(
    not _policy_implemented(),
    reason="_classify_decision not implemented yet; see core_solver.py TODO.",
)


@pytestmark_policy
def test_label_is_one_of_three_after_policy_implemented():
    ev = VerticalPathEvaluator(_baseline_params())
    d = ev.evaluate(horizontal_savings_fs=500.0, n_vertical_vias=1,
                    n_bond_contacts=0, l_h_meters=100e-6)
    assert d.label in {DecisionLabel.PASS, DecisionLabel.FAIL,
                        DecisionLabel.MARGINAL}


@pytestmark_policy
def test_clearly_failing_path_is_labeled_FAIL():
    ev = VerticalPathEvaluator(_baseline_params())
    d = ev.evaluate(horizontal_savings_fs=10.0, n_vertical_vias=50,
                    n_bond_contacts=10, l_h_meters=20e-6)
    assert d.margin_fs < 0
    assert d.label == DecisionLabel.FAIL
