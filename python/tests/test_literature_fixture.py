"""Tests for the literature-anchored hybrid-bond parasitic fixture.

The fixture (``fixtures/hybrid_bond_literature.json``) exists so the what-if
sweep's parasitic bracket has one corner anchored to citable public sources
instead of invented values. These tests pin the two claims that make that
anchoring defensible:

1. The published design assumption (Hier-3D, ISLPED 2022: 0.5 Ohm / 1 fF at
   a 0.5 x 0.5 um F2F pad) implies a specific contact resistance that falls
   inside the independently measured Cu-Cu range — i.e. the assumption is not
   generous relative to measurement.
2. Under Eq. 2, the bond term that dominates is ``R_drv * C_b`` (charging the
   bond's capacitance), not any resistance-side term. The published corner is
   low-R / high-C, and the gate punishes exactly the C side.

Per the fixture's provenance note these are other processes' published
numbers, not Huawei's: consuming them does not fire Trigger A or Trigger B.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from logic_folding_reference import ProcessParameters, VerticalPathEvaluator

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "hybrid_bond_literature.json"

# 1 Ohm-cm2 = 1e8 Ohm-um2 (1 cm2 = 1e8 um2).
OHM_CM2_TO_OHM_UM2 = 1.0e8


@pytest.fixture(scope="module")
def lit() -> dict:
    return json.loads(_FIXTURE.read_text())


def test_fixture_parses_and_declares_schema(lit):
    assert lit["schema"] == "logic-folding-literature/v0"
    # Provenance must state these are not Huawei's numbers and no trigger fires.
    assert "NOT Huawei" in lit["_provenance"]
    assert "Trigger B" in lit["_provenance"]


def test_bond_assumption_within_measured_contact_resistance_range(lit):
    """Hier-3D's assumed per-bond resistance, converted to specific contact
    resistance via its own pad area, must land inside the measured Cu-Cu
    range. R = rho_c / A  =>  rho_c = R * A."""
    bond = lit["f2f_bond_assumption"]
    w_um, h_um = bond["via_size_um"]
    area_um2 = w_um * h_um
    implied_ohm_um2 = bond["resistance_ohm"] * area_um2

    lo_cm2, hi_cm2 = lit["measured_specific_contact_resistance"]["range_ohm_cm2"]
    lo_um2 = lo_cm2 * OHM_CM2_TO_OHM_UM2
    hi_um2 = hi_cm2 * OHM_CM2_TO_OHM_UM2

    assert lo_um2 <= implied_ohm_um2 <= hi_um2, (
        f"Implied rho_c = {implied_ohm_um2} Ohm-um2 outside measured "
        f"[{lo_um2}, {hi_um2}] Ohm-um2 — the fixture's consistency claim fails."
    )


def test_measured_datapoints_fall_within_declared_range(lit):
    meas = lit["measured_specific_contact_resistance"]
    lo, hi = meas["range_ohm_cm2"]
    for dp in meas["datapoints"]:
        value = dp.get("value_ohm_cm2", dp.get("implied_ohm_cm2"))
        assert value is not None
        assert lo <= value <= hi


def test_bond_capacitance_term_dominates_bond_tax(lit):
    """With the literature bond values, the R_drv*C_b charging term must be
    the majority of the single-bond Elmore contribution — the sweep's stated
    reason the published low-R / high-C corner still fails local paths."""
    bond = lit["f2f_bond_assumption"]
    params = ProcessParameters(
        r_v=10.0, c_v=0.5e-15,
        r_b=bond["resistance_ohm"], c_b=bond["capacitance_f"],
        r_drv=200.0, c_load=5.0e-15,
        dtau_red_fs=0.0, dtau_thermal_fs=0.0,
    )
    ev = VerticalPathEvaluator(params)
    bond_only_tax_fs = ev.vertical_tax_fs(n_vertical_vias=0, n_bond_contacts=1)
    charging_term_fs = params.r_drv * params.c_b * 1.0e15

    assert charging_term_fs > 0.5 * bond_only_tax_fs, (
        "R_drv*C_b is expected to dominate the bond contribution under the "
        "literature values; if this fails, the sweep's interpretation text "
        "is stale."
    )
    # And the resistance-side terms are individually small next to it.
    r_side_fs = (params.r_b * params.c_load + params.r_b * params.c_b) * 1.0e15
    assert charging_term_fs > 10.0 * r_side_fs
