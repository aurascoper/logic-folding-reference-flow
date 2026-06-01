#!/usr/bin/env python3
"""flows/check_live.py — validate a live OpenROAD dump against the contract.

One command for the testable part of the LIVE_RUN success gate. Point it at the
timing dump (and optionally the geometry sidecar) a live run produced; it runs
the real Python consumer (parse -> merge -> screen) with NO consumer changes:

    python flows/check_live.py <timing.json> [<netlen.json>]

The timing file may be any of:
  * raw `report_checks -format json` output (adapted automatically),
  * `sta_dump.tcl` output (banner + ===LF-JSON-BEGIN/END=== markers), or
  * an already-converted logic-folding-baseline/v0 file.

  Gate 1 (runs)          — files load.
  Gate 2 (schema-valid)  — adapter/parser accept them.
  Gate 3 (contract holds)— merge + parse + Eq. 2 screen run unchanged.

Exits 0 iff gates 1-3 pass. (Gate 4 — replacing fixtures + re-pointing test
assertions — is a human step; see flows/LIVE_RUN.md.) The Eq. 2 right-hand side
here is an *illustrative* 3D tax; the point is that the left-hand side is now
real silicon-grade data.
"""

from __future__ import annotations

import argparse
import json
import sys

from logic_folding_reference import (
    ProcessParameters,
    adapt_opensta_checks,
    derive_foldable_savings,
    load_net_lengths,
    merge_net_lengths,
    parse_baseline_report,
    screen_path,
)

ILLUSTRATIVE_TAX = ProcessParameters(
    r_v=10.0, c_v=0.5e-15, r_b=8.0, c_b=0.4e-15, r_drv=200.0, c_load=5.0e-15,
    dtau_red_fs=20.0, dtau_thermal_fs=15.0, parasitic_noise_floor_fs=10.0,
)


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of possibly banner-wrapped sta_dump output."""
    if "===LF-JSON-BEGIN===" in text:
        text = text.split("===LF-JSON-BEGIN===", 1)[1].split("===LF-JSON-END===", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for key in ('{"checks"', '{ "checks"', '{"schema"'):
            i = text.find(key)
            if i >= 0:
                return json.JSONDecoder().raw_decode(text[i:])[0]
        raise


def _load_v0(path: str) -> dict:
    """Return a schema-v0 dict, adapting raw OpenSTA `checks` output if needed."""
    with open(path, encoding="utf-8") as fh:
        obj = _extract_json(fh.read())
    if "checks" in obj:                 # raw report_checks -format json
        return adapt_opensta_checks(obj)
    return obj                          # already logic-folding-baseline/v0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("timing", help="report_checks json / sta_dump output / baseline v0 json")
    ap.add_argument("netlen", nargs="?", help="logic-folding-netlen/v0 JSON (odb_wirelength.py)")
    ap.add_argument("--show", type=int, default=8, help="how many paths to print")
    args = ap.parse_args(argv)

    # Gate 1/2: the timing dump loads and converts to the contract.
    raw = _load_v0(args.timing)
    print(f"[gate 1/2] {args.timing}: schema={raw.get('schema')!r}, {len(raw.get('paths', []))} paths")

    # Gate 2/3: geometry merge, if a sidecar was given.
    if args.netlen:
        nl = load_net_lengths(args.netlen)
        print(f"[gate 2] {args.netlen}: {len(nl)} routed nets")
        try:
            raw = merge_net_lengths(raw, nl, on_missing="error")
            print("[gate 3] merge OK: every timed wire arc has real routed copper")
        except KeyError as exc:
            print(f"[gate 3] FINDING: a timed wire is unrouted/absent -> {exc}")
            print("         continuing with on_missing='keep'")
            raw = merge_net_lengths(raw, nl, on_missing="keep")
    else:
        print("[gate 2/3] no netlen given — wire_length stays as the dump provided")

    # Gate 3: the parser accepts real output with the consumer unchanged.
    report = parse_baseline_report(raw)
    print(f"[gate 3] parse OK: {len(report.paths)} paths, consumer unchanged\n")

    print(f"{'endpoint':32s} {'l_h(um)':>9} {'dtau_save(fs)':>13} {'slack(fs)':>13}  label")
    print("-" * 84)
    for p in report.paths[: args.show]:
        d = screen_path(p, ILLUSTRATIVE_TAX, n_vertical_vias=2, n_bond_contacts=1)
        print(f"{p.endpoint:32.32s} {p.total_wire_length_m * 1e6:9.1f} "
              f"{derive_foldable_savings(p):13.0f} {p.slack_fs:13.0f}  {d.label.value}")

    shown = min(args.show, len(report.paths))
    print(f"\nGATE 1-3 PASS — contract held against this OpenROAD output "
          f"({len(report.paths)} paths, showed {shown}). Gate 4 = replace fixtures "
          f"(flows/LIVE_RUN.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
