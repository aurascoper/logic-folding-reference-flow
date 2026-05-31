"""Tests for the 2D-baseline ingestion contract (schema logic-folding-baseline/v0).

Two tiers, mirroring the repo's existing convention (see test_break_even.py):

* Parser/contract tests run now — they pin the schema, the SI/fs unit
  conversion, the wire-vs-cell aggregation, and the baseline->Eq. 2 join
  plumbing. None of these depend on the operator's §7 modelling choice.
* The end-to-end screening tests are skipped until the operator implements
  ``derive_foldable_savings`` (the one load-bearing §7 decision), exactly as
  the PASS/FAIL policy tests skip until ``_classify_decision`` exists.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from logic_folding_reference import (
    SCHEMA_ID,
    BaselinePath,
    DecisionLabel,
    ProcessParameters,
    WireSegment,
    derive_foldable_savings,
    load_baseline_report,
    params_from_path,
    parse_baseline_report,
    screen_path,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sky130_gcd_baseline.json"


# ---- Helpers ---------------------------------------------------------------


def _report():
    return load_baseline_report(FIXTURE)


def _critical_path() -> BaselinePath:
    """The negative-slack path in the fixture (_reg_1_ -> _reg_9_)."""
    return next(p for p in _report().paths if p.slack_fs < 0)


def _tax_params() -> ProcessParameters:
    """Illustrative 3D tax. Values legible, not a process claim (memo §7)."""
    return ProcessParameters(
        r_v=10.0, c_v=0.5e-15, r_b=8.0, c_b=0.4e-15,
        r_drv=200.0, c_load=5.0e-15,
        dtau_red_fs=20.0, dtau_thermal_fs=15.0,
        parasitic_noise_floor_fs=10.0,
    )


# ---- Contract / parser tests (run now) -------------------------------------


def test_fixture_is_schema_v0():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["schema"] == SCHEMA_ID


def test_loads_all_paths_with_metadata():
    report = _report()
    assert report.pdk == "sky130hd"
    assert report.design == "gcd"
    assert len(report.paths) == 4


def test_units_converted_to_si_and_fs():
    # First path, first wire arc: 0.244 ns -> 2.44e5 fs ; 38.6 um -> 3.86e-5 m.
    first = _report().paths[0]
    wire = next(s for s in first.segments if s.is_wire)
    assert math.isclose(wire.incr_delay_fs, 0.244 * 1e6, rel_tol=1e-12)
    assert math.isclose(wire.wire_length_m, 38.6 * 1e-6, rel_tol=1e-12)
    # slack 0.182 ns -> 1.82e5 fs
    assert math.isclose(first.slack_fs, 0.182 * 1e6, rel_tol=1e-12)


def test_resistance_and_capacitance_units_converted():
    # driver_resistance 1.95 kohm -> 1950 ohm ; load_capacitance 0.0042 pF -> 4.2e-15 F
    p = _report().paths[0]
    assert math.isclose(p.driver_resistance_ohm, 1.95 * 1e3, rel_tol=1e-12)
    assert math.isclose(p.load_capacitance_farad, 0.0042 * 1e-12, rel_tol=1e-12)


def test_negative_slack_sign_preserved_for_critical_path():
    assert _critical_path().slack_fs < 0


def test_wire_aggregation_excludes_cell_arcs():
    # Path 2 (_reg_3_ -> _reg_4_): two wire arcs (3.2 + 2.7 um), cell arcs ignored.
    p = _report().paths[1]
    assert math.isclose(p.total_wire_length_m, (3.2 + 2.7) * 1e-6, rel_tol=1e-12)
    assert math.isclose(p.total_wire_delay_fs, (0.041 + 0.038) * 1e6, rel_tol=1e-9)


def test_rejects_unknown_schema():
    with pytest.raises(ValueError, match="schema"):
        parse_baseline_report({"schema": "something/v9", "paths": []})


def test_rejects_unknown_unit():
    bad = {
        "schema": SCHEMA_ID,
        "units": {"time": "lightyears"},
        "paths": [],
    }
    with pytest.raises(ValueError, match="time unit"):
        parse_baseline_report(bad)


def test_params_from_path_pulls_driver_and_load_from_baseline():
    p = _report().paths[0]
    params = params_from_path(
        p, r_v=10.0, c_v=0.5e-15, r_b=8.0, c_b=0.4e-15,
        dtau_red_fs=20.0, dtau_thermal_fs=15.0,
    )
    # R_drv / C_load came from the 2D baseline; vertical tax came from caller.
    assert math.isclose(params.r_drv, 1950.0, rel_tol=1e-12)
    assert math.isclose(params.c_load, 4.2e-15, rel_tol=1e-12)
    assert params.r_v == 10.0


def test_params_from_path_requires_driver_and_load():
    bare = BaselinePath(
        startpoint="a", endpoint="b", slack_fs=0.0, arrival_fs=0.0,
        required_fs=0.0, segments=(WireSegment("a/X", None, None, 0.0, 0.0, False),),
    )
    with pytest.raises(ValueError, match="driver_resistance"):
        params_from_path(bare, r_v=1, c_v=1e-15, r_b=1, c_b=1e-15,
                         dtau_red_fs=0, dtau_thermal_fs=0)


def test_screen_path_accepts_injected_savings_fn():
    # The join itself is testable without the §7 model: inject a stub savings_fn.
    p = _report().paths[0]
    d = screen_path(
        p, _tax_params(), n_vertical_vias=1, n_bond_contacts=0,
        savings_fn=lambda _p: 500.0,
    )
    assert d.horizontal_savings_fs == 500.0
    assert math.isclose(d.l_h_meters, p.total_wire_length_m, rel_tol=1e-12)
    assert d.margin_fs == d.horizontal_savings_fs - d.vertical_tax_fs


# ---- End-to-end screening (skipped until §7 savings model implemented) ------


def _savings_model_implemented() -> bool:
    try:
        derive_foldable_savings(_report().paths[0])
        return True
    except NotImplementedError:
        return False
    except Exception:
        return True


pytestmark_savings = pytest.mark.skipif(
    not _savings_model_implemented(),
    reason="derive_foldable_savings not implemented yet; see baseline.py §7 TODO.",
)


@pytestmark_savings
def test_end_to_end_every_path_gets_a_valid_label():
    report = _report()
    params = _tax_params()
    for p in report.paths:
        d = screen_path(p, params, n_vertical_vias=2, n_bond_contacts=1)
        assert d.label in {DecisionLabel.PASS, DecisionLabel.FAIL, DecisionLabel.MARGINAL}
        # Sanity: a sane §7 model never reclaims more than the path's wire delay.
        assert 0.0 <= d.horizontal_savings_fs <= p.total_wire_delay_fs + 1e-6


@pytestmark_savings
def test_end_to_end_absurd_vertical_tax_forces_fail():
    # Independent of the savings policy: a huge via count must sink any path.
    p = _report().paths[0]
    d = screen_path(p, _tax_params(), n_vertical_vias=100_000, n_bond_contacts=100_000)
    assert d.margin_fs < 0
    assert d.label == DecisionLabel.FAIL


@pytestmark_savings
def test_policy2_excludes_local_paths_but_keeps_global():
    # The §7 stratification must be visible, not just asserted: a local-dominated
    # path (all net arcs below the fold threshold) reclaims zero, while a path
    # with long global wires reclaims a positive Δτ_save.
    report = _report()
    from logic_folding_reference import derive_foldable_savings

    local = next(p for p in report.paths if p.endpoint == "_loc_reg_2_/D")
    assert derive_foldable_savings(local) == 0.0

    glob = report.paths[0]  # has met4/met5 global arcs well above threshold
    assert derive_foldable_savings(glob) > 0.0
    # And never more than the path physically contains.
    assert derive_foldable_savings(glob) <= glob.total_wire_delay_fs + 1e-6
