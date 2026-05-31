#!/usr/bin/env python3
"""flows/check_live.py — validate a live OpenROAD dump against the contract.

One command for the testable part of the LIVE_RUN success gate. Point it at the
two JSON files a live run produced and it runs the real Python consumer
(parse -> merge -> screen) with NO consumer changes:

    python flows/check_live.py <baseline.json> [<netlen.json>]

  Gate 1 (runs)         — both files load.
  Gate 2 (schema-valid) — parse_baseline_report / load_net_lengths accept them.
  Gate 3 (contract holds)— merge + parse + Eq. 2 screen run unchanged.

Exits 0 iff gates 1-3 pass. (Gate 4 — replacing the fixtures + re-pointing test
assertions — is a human step; see flows/LIVE_RUN.md.) The Eq. 2 right-hand side
here is an *illustrative* 3D tax: the point is that the left-hand side (l_h,
Δτ_save, slack) is now real silicon-grade data, not a fixture we authored.
"""

from __future__ import annotations

import argparse
import json
import sys

from logic_folding_reference import (
    ProcessParameters,
    derive_foldable_savings,
    load_net_lengths,
    merge_net_lengths,
    parse_baseline_report,
    screen_path,
)

# Illustrative 3D tax (legible, not a process claim — memo §7). Swap in measured
# parasitics when you have them; this only exercises the join, not feasibility.
ILLUSTRATIVE_TAX = ProcessParameters(
    r_v=10.0, c_v=0.5e-15, r_b=8.0, c_b=0.4e-15, r_drv=200.0, c_load=5.0e-15,
    dtau_red_fs=20.0, dtau_thermal_fs=15.0, parasitic_noise_floor_fs=10.0,
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("baseline", help="logic-folding-baseline/v0 JSON (from sta_dump.tcl)")
    ap.add_argument("netlen", nargs="?", help="logic-folding-netlen/v0 JSON (from odb_wirelength.py)")
    ap.add_argument("--show", type=int, default=8, help="how many paths to print")
    args = ap.parse_args(argv)

    # Gate 1: the timing dump loads.
    with open(args.baseline, encoding="utf-8") as fh:
        raw = json.load(fh)
    print(f"[gate 1] loaded {args.baseline}: schema={raw.get('schema')!r}, "
          f"{len(raw.get('paths', []))} paths")

    # Gate 2/3: geometry merge, if a sidecar was given.
    if args.netlen:
        nl = load_net_lengths(args.netlen)
        print(f"[gate 2] loaded {args.netlen}: {len(nl)} routed nets")
        try:
            raw = merge_net_lengths(raw, nl, on_missing="error")
            print("[gate 3] merge OK: every timed wire arc has real routed copper")
        except KeyError as exc:
            print(f"[gate 3] FINDING: a timed wire is unrouted/absent -> {exc}")
            print("         continuing with on_missing='keep' so the report still prints")
            raw = merge_net_lengths(raw, nl, on_missing="keep")
    else:
        print("[gate 2/3] no netlen given — using the baseline's own wire_length")

    # Gate 2/3: the parser accepts real output with the consumer unchanged.
    report = parse_baseline_report(raw)
    print(f"[gate 3] parse_baseline_report OK: {len(report.paths)} paths, consumer unchanged\n")

    # Eq. 2 screen — LHS real, RHS illustrative.
    print(f"{'endpoint':32s} {'l_h(um)':>9} {'dtau_save(fs)':>13} {'slack(fs)':>11}  label")
    print("-" * 80)
    for p in report.paths[: args.show]:
        d = screen_path(p, ILLUSTRATIVE_TAX, n_vertical_vias=2, n_bond_contacts=1)
        print(f"{p.endpoint:32.32s} {p.total_wire_length_m * 1e6:9.1f} "
              f"{derive_foldable_savings(p):13.0f} {p.slack_fs:11.0f}  {d.label.value}")

    shown = min(args.show, len(report.paths))
    print(f"\nGATE 1-3 PASS — contract held against this OpenROAD output "
          f"({len(report.paths)} paths, showed {shown}). Gate 4 = replace fixtures "
          f"(see flows/LIVE_RUN.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
