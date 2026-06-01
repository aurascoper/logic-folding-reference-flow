# flows/sta_dump.tcl — emit OpenSTA report_checks JSON for the LogicFolding flow.
#
# Runs inside OpenROAD (which embeds OpenSTA). It emits `report_checks -format
# json` between two markers; logic_folding_reference.baseline.adapt_opensta_checks()
# converts that to schema logic-folding-baseline/v0, and check_live.py does it
# for you. report_checks -format json is SI (seconds, farads, meters) — the
# adapter + parser handle units.
#
# Why this shape: the fragile part (walking a path's arcs, classifying wire vs
# cell, pulling nets) lives in TESTED Python, proven against real OpenROAD
# output (python/tests/fixtures/opensta_gcd_placed_checks.json). This Tcl uses
# only stable, documented commands. The `is_wire` rule comes free from each
# pin's `instance` field — same instance = gate arc, different = net arc.
#
# Inputs: a placed OR routed ORFS stage .odb (+ liberty + sdc). A placed
# 3_place.odb is enough for a timing baseline; routed wire-length comes
# separately from odb_wirelength.py + merge_net_lengths.
#
# Usage (from the ORFS flow/ directory):
#   openroad -no_init -exit /path/to/flows/sta_dump.tcl > checks.json 2> sta_dump.log
#   python /path/to/flows/check_live.py checks.json        # auto-detects + adapts

# ---- Inputs (edit for your design/stage) -----------------------------------
set LIB_GLOB     "platforms/sky130hd/lib/*1v80*.lib"
set DB           "results/sky130hd/gcd/base/3_place.odb"
set SDC          "results/sky130hd/gcd/base/3_place.sdc"
set GROUP_COUNT  50

# ---- Load + parasitics (placement estimate is enough for a baseline) -------
foreach lib [glob $LIB_GLOB] { read_liberty $lib }
read_db  $DB
read_sdc $SDC
set_wire_rc -signal -layer met3
estimate_parasitics -placement

# ---- Emit report_checks JSON between markers (banner-proof) -----------------
# check_live.py / adapt_opensta_checks slice between the markers, so OpenROAD's
# startup banner on stdout doesn't corrupt the JSON.
puts "===LF-JSON-BEGIN==="
report_checks -path_delay max -group_count $GROUP_COUNT -fields {input_pins net} -format json
puts "===LF-JSON-END==="
