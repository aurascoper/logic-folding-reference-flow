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
# Stage auto-discovery: picks the most advanced .odb/.sdc present (routed
# `6_final` if routing ran, else placed `3_place`). If a SPEF is present it uses
# those REAL extracted parasitics (routed wire delay); otherwise it estimates
# from placement. So the same script gives a placement baseline OR a routed one.
#
# Usage (from the ORFS flow/ directory):
#   openroad -no_init -exit /path/to/flows/sta_dump.tcl > checks.json 2> sta_dump.log
#   python /path/to/flows/check_live.py checks.json        # auto-detects + adapts

# ---- Inputs ----------------------------------------------------------------
set PDK          "sky130hd"
set DESIGN       "gcd"
set GROUP_COUNT  50
set RESULTS      "results/$PDK/$DESIGN/base"
set LIB_GLOB     "platforms/$PDK/lib/*1v80*.lib"
set DB   [lindex [lsort [glob -nocomplain $RESULTS/*.odb]]  end]
set SDC  [lindex [lsort [glob -nocomplain $RESULTS/*.sdc]]  end]
set SPEF [lindex [lsort [glob -nocomplain $RESULTS/*.spef]] end]
puts "sta_dump: DB=$DB SDC=$SDC SPEF=$SPEF"

# ---- Load + parasitics -----------------------------------------------------
foreach lib [glob $LIB_GLOB] { read_liberty $lib }
read_db  $DB
read_sdc $SDC
if {$SPEF ne ""} {
  read_spef $SPEF          ;# real extracted parasitics (routed wire delay)
} else {
  set_wire_rc -signal -layer met3
  estimate_parasitics -placement   ;# placement estimate (wire delay ~0)
}

# ---- Emit report_checks JSON between markers (banner-proof) -----------------
puts "===LF-JSON-BEGIN==="
report_checks -path_delay max -group_count $GROUP_COUNT -fields {input_pins net} -format json
puts "===LF-JSON-END==="
