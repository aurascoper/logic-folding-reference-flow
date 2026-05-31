#!/usr/bin/env -S openroad -python
# flows/odb_wirelength.py — routed wire length dump for the LogicFolding flow.
#
# REPRODUCTION RECIPE, not a CI-exercised step. It runs inside OpenROAD's Python
# (which embeds the `odb` database) and emits this flow's geometry sidecar,
# schema "logic-folding-netlen/v0", merged into the timing contract by
# logic_folding_reference.baseline.merge_net_lengths.
#
# Why odb and not a hand-rolled DEF parser: odb reads the *fully routed* DEF and
# exposes the actual physical copper (dbWire), so we get real per-net Manhattan
# length — including the doglegs, layer assignment, and congestion detours that
# Half-Perimeter Wire Length (HPWL) smooths over. OpenROAD also owns the brutal
# DBU scaling and orientation transforms. STA gives the time; odb gives the
# space.
#
# Usage (needs a local OpenROAD build + sky130hd tech LEF + a ROUTED .def):
#   openroad -python flows/odb_wirelength.py \
#       --tlef platforms/sky130hd/lef/sky130_fd_sc_hd.tlef \
#       --lef  platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef \
#       --def  results/gcd_route.def \
#       --pdk sky130hd --design gcd \
#       > python/tests/fixtures/sky130_gcd_netlen.json
#
# The odb calls below are the documented Python API (OpenROAD test/python_api.md):
#   db = openroad.Tech().getDB(); odb.read_lef(db, ...); chip = odb.read_def(...)
#   block = chip.getBlock(); block.getNets(); net.getWire(); wire.getLength()
#   block.getDbUnitsPerMicron()
# net.getWire() returns None for an UNROUTED net — such nets are intentionally
# OMITTED from the sidecar (a missing key means "no routed copper", which
# merge_net_lengths(on_missing="error") then surfaces loudly rather than zeroing).

import argparse
import json
import sys

try:
    from openroad import Design, Tech
except ImportError:  # not running inside OpenROAD's interpreter
    sys.stderr.write(
        "odb_wirelength.py must run under OpenROAD's Python "
        "(`openroad -python flows/odb_wirelength.py ...`).\n"
    )
    raise


def main(argv=None):
    ap = argparse.ArgumentParser(description="Emit logic-folding-netlen/v0 from a routed DEF.")
    ap.add_argument("--tlef", required=True, help="technology LEF")
    ap.add_argument("--lef", action="append", default=[], help="cell LEF(s); repeatable")
    ap.add_argument("--def", dest="def_file", required=True, help="ROUTED design DEF")
    ap.add_argument("--pdk", default=None)
    ap.add_argument("--design", default=None)
    args = ap.parse_args(argv)

    # Documented high-level entry (OpenROAD src/README.md): Tech reads LEF,
    # Design reads the routed DEF; the odb dbBlock hangs off the Design.
    tech = Tech()
    tech.readLef(args.tlef)
    for lef in args.lef:
        tech.readLef(lef)
    design = Design(tech)
    design.readDef(args.def_file)
    block = design.getBlock()

    dbu_per_micron = block.getDbUnitsPerMicron()

    net_lengths = {}
    unrouted = 0
    for net in block.getNets():
        wire = net.getWire()
        if wire is None:  # unrouted -> omit, do not fake a 0
            unrouted += 1
            continue
        net_lengths[net.getName()] = wire.getLength() / dbu_per_micron

    out = {
        "schema": "logic-folding-netlen/v0",
        "pdk": args.pdk,
        "design": args.design,
        "units": {"length": "um"},
        "net_lengths": net_lengths,
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    sys.stderr.write(
        f"odb_wirelength: {len(net_lengths)} routed nets, {unrouted} unrouted (omitted).\n"
    )


if __name__ == "__main__":
    main()
