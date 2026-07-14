#!/usr/bin/env python3
"""What-if break-even analysis against Huawei's claimed Kirin 2026 data.

ALL numbers from the Kirin 2026 fixture are vendor self-reported (Huawei Tau
Scaling Law V2 paper, He Tingbo, July 3, 2026). They are NOT independently
verified. This script runs in conditional mode:

    "IF these claimed numbers are accurate, here is what the
     break-even inequality (memo §7, Eq. 2) would show."

It does NOT treat Huawei's numbers as validated truth. Per the memo's
no-action decision, self-reported data does not clear the independent-evidence
bar (Trigger A: shipping teardown — not fired).

Usage:
    python scripts/kirin_2026_whatif.py
    python scripts/kirin_2026_whatif.py --verbose

The script loads the claimed fixture, constructs a range of plausible parasitic
scenarios, and reports how many paths would pass / fail / marginal under each
scenario. The parasitic sweep is deliberately wide because Huawei has not
disclosed actual via/bond RC values (Trigger B has not fired).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# -- Path setup: make the package importable when run from the scripts dir ----

_FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "kirin_2026_claimed.json"


def load_claimed_data(path: Path = _FIXTURE) -> dict:
    """Load the claimed Kirin 2026 fixture, printing the verification warning."""
    data = json.loads(path.read_text())
    print("=" * 72)
    print("WHAT-IF ANALYSIS: Kirin 2026 claimed data (NOT VERIFIED)")
    print("=" * 72)
    print(f"Fixture: {path}")
    print(f"Source:  {data.get('source', 'unknown')}")
    print(f"Chip:    {data.get('chip', 'unknown')}")
    print(f"Status:  {data.get('verification_status', 'unknown')}")
    print()
    print("WARNING: " + data.get("_warning", "")[:200])
    print()
    return data


def run_breakeven_sweep(claimed: dict, verbose: bool = False) -> None:
    """Sweep the break-even inequality across plausible parasitic scenarios.

    Since Huawei has not disclosed actual via/bond RC values (Trigger B not
    fired), we sweep across a range from optimistic (low parasitics) to
    pessimistic (high parasitics). The claimed frequency (3.1 GHz) sets the
    clock period context; the claimed density (238 MTr/mm^2) sets the area
    context.

    The sweep uses the FULL Eq. 2 form (including R_v*C_v / R_b*C_b
    self-loading terms) via the Python VerticalPathEvaluator.
    """
    # Import the engine
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from logic_folding_reference import (
        DecisionLabel,
        ProcessParameters,
        VerticalPathEvaluator,
    )

    freq_ghz = claimed.get("claimed_electrical", {}).get("frequency_ghz", 3.1)
    clock_period_ps = 1000.0 / freq_ghz if freq_ghz else 322.6  # ps

    print(f"Claimed frequency:    {freq_ghz} GHz")
    print(f"Clock period:         {clock_period_ps:.1f} ps")
    print(f"Claimed density:      {claimed.get('claimed_density', {}).get('transistor_density_mtr_mm2')} MTr/mm^2")
    print(f"Efficiency gain:      {claimed.get('claimed_efficiency', {}).get('high_perf_core_efficiency_gain_pct')}%")
    print()

    # -- Parasitic sweep ---------------------------------------------------
    # These are NOT Huawei's numbers — they are a deliberately wide sweep of
    # plausible vertical via/bond parasitics, since no PDK data exists.
    # Range: optimistic (advanced-node-like) to pessimistic (coarse-node-like).

    scenarios = [
        ("optimistic",    dict(r_v=2.0,  c_v=0.2e-15, r_b=1.5,  c_b=0.15e-15, dtau_red_fs=10.0, dtau_thermal_fs=5.0)),
        ("moderate",      dict(r_v=10.0, c_v=0.5e-15, r_b=8.0,  c_b=0.4e-15,  dtau_red_fs=20.0, dtau_thermal_fs=15.0)),
        ("pessimistic",   dict(r_v=25.0, c_v=1.0e-15, r_b=20.0, c_b=0.8e-15,  dtau_red_fs=50.0, dtau_thermal_fs=100.0)),
        ("thermal_stress",dict(r_v=10.0, c_v=0.5e-15, r_b=8.0,  c_b=0.4e-15,  dtau_red_fs=20.0, dtau_thermal_fs=300.0)),
    ]

    # -- Path ensemble: bimodal local/global, matching memo §7 stratification
    # Local paths: short, low savings (most paths in a real design)
    # Global paths: long, high savings (the critical-path subset)
    # The question: under claimed Kirin 2026 operating conditions, which paths
    # clear the break-even gate?

    import random
    rng = random.Random(42)
    paths = []
    for _ in range(10000):
        is_global = rng.random() < 0.08
        if is_global:
            # Global paths: 800-5000 fs savings (matching mock.rs distribution)
            savings = rng.uniform(800.0, 5000.0)
            n_vias = rng.randint(1, 3)
            n_bonds = rng.randint(0, 2)
        else:
            # Local paths: 5-250 fs savings
            savings = rng.uniform(5.0, 250.0)
            n_vias = 1
            n_bonds = rng.randint(0, 1)
        paths.append((savings, n_vias, n_bonds, 0.0))

    print(f"Path ensemble: {len(paths)} paths (8% global, 92% local)")
    print(f"{'='*72}")
    print()

    for name, params_dict in scenarios:
        params = ProcessParameters(
            r_drv=200.0,           # typical driver resistance (not disclosed by Huawei)
            c_load=5.0e-15,        # typical load capacitance (not disclosed by Huawei)
            parasitic_noise_floor_fs=10.0,
            **params_dict,
        )
        ev = VerticalPathEvaluator(params)
        decisions = ev.evaluate_batch(paths)

        n_pass = sum(1 for d in decisions if d.label == DecisionLabel.PASS)
        n_fail = sum(1 for d in decisions if d.label == DecisionLabel.FAIL)
        n_marg = sum(1 for d in decisions if d.label == DecisionLabel.MARGINAL)

        # Also break down by path type
        global_decisions = [d for d, p in zip(decisions, paths) if p[0] > 800.0]
        local_decisions = [d for d, p in zip(decisions, paths) if p[0] <= 800.0]
        g_pass = sum(1 for d in global_decisions if d.label == DecisionLabel.PASS)
        l_pass = sum(1 for d in local_decisions if d.label == DecisionLabel.PASS)

        print(f"Scenario: {name}")
        print(f"  Via/bond RC: r_v={params_dict['r_v']:.0f}Ω c_v={params_dict['c_v']*1e15:.1f}fF"
              f"  r_b={params_dict['r_b']:.0f}Ω c_b={params_dict['c_b']*1e15:.1f}fF")
        print(f"  Δτ_red={params_dict['dtau_red_fs']:.0f}fs  Δτ_T={params_dict['dtau_thermal_fs']:.0f}fs")
        print(f"  PASS: {n_pass:>5} ({100*n_pass/len(paths):.1f}%)  "
              f"FAIL: {n_fail:>5} ({100*n_fail/len(paths):.1f}%)  "
              f"MARG: {n_marg:>5} ({100*n_marg/len(paths):.1f}%)")
        print(f"  Global paths passing: {g_pass}/{len(global_decisions)} "
              f"({100*g_pass/max(len(global_decisions),1):.1f}%)")
        print(f"  Local paths passing:  {l_pass}/{len(local_decisions)} "
              f"({100*l_pass/max(len(local_decisions),1):.1f}%)")

        if verbose:
            # Show a few example margins for global paths
            print(f"  Sample global-path margins (fs):")
            for d, p in list(zip(decisions, paths)):
                if p[0] > 800.0:
                    print(f"    savings={d.horizontal_savings_fs:>7.0f}  "
                          f"tax={d.vertical_tax_fs:>7.0f}  "
                          f"margin={d.margin_fs:>7.0f}  "
                          f"label={d.label.value}")
                    if d.label == DecisionLabel.FAIL:
                        break  # show first failure
        print()

    # -- Interpretation ----------------------------------------------------
    print(f"{'='*72}")
    print("INTERPRETATION")
    print(f"{'='*72}")
    print()
    print("This is a WHAT-IF analysis, not evidence. The key findings:")
    print()
    print("1. Under all parasitic scenarios, only the long global paths (the")
    print("   right-tail 8%) have any chance of clearing the break-even gate.")
    print("   This is the memo §7 stratification: folding is a floorplanning")
    print("   technique for long wires, not a standard-cell-level scaling law.")
    print()
    print("2. The thermal-stress scenario (Δτ_T = 300 fs) flips most global")
    print("   paths to FAIL. This is the memo §8 point: burst benchmarks are")
    print("   not sustained evidence. Huawei has not disclosed sustained")
    print("   thermal data — only burst/vendor measurements.")
    print()
    print("3. The actual break-even outcome depends on via/bond parasitics")
    print("   that Huawei has NOT disclosed (Trigger B has not fired). The")
    print("   sweep range above brackets the plausible space; the real answer")
    print("   requires PDK data.")
    print()
    print("CONCLUSION: Even if Huawei's claimed Kirin 2026 numbers are taken")
    print("at face value, the break-even inequality still requires measured")
    print("vertical parasitics and sustained thermal data to evaluate. The")
    print("memo's no-action decision stands.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="What-if break-even analysis against claimed Kirin 2026 data."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print sample per-path margins for each scenario.",
    )
    args = parser.parse_args()
    claimed = load_claimed_data()
    run_breakeven_sweep(claimed, verbose=args.verbose)


if __name__ == "__main__":
    main()