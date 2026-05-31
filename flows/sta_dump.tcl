# flows/sta_dump.tcl — 2D timing baseline dump for the LogicFolding flow.
#
# Runs inside OpenROAD (which embeds OpenSTA) and emits this flow's stable
# contract, schema "logic-folding-baseline/v0", consumed by
# logic_folding_reference.baseline.parse_baseline_report. Geometry (real routed
# wire_length) is filled in separately by flows/odb_wirelength.py +
# baseline.merge_net_lengths. STA gives the time; odb gives the space.
#
# ============================================================================
#  DRAFT — VERIFY BEFORE TRUSTING. The per-path arc walk in section 5 is written
#  against the documented OpenSTA Tcl API but has NOT been executed against a
#  live build (the repo ships no toolchain/PDK). Accessors that vary by
#  OpenROAD/OpenSTA version are marked `VERIFY:`; confirm each on your build
#  (e.g. `openroad> help get_property`) before relying on the output. See the
#  WI-2 verification checklist in flows/LIVE_RUN.md.
# ============================================================================
#
# Usage (paths below assume an OpenROAD-flow-scripts checkout; cd into ./flow):
#   openroad -no_init -exit flows/sta_dump.tcl \
#       > python/tests/fixtures/sky130_gcd_baseline.json
#   2>sta_dump.log   # warnings (empty-segment paths, etc.) go to stderr

# ---- 0. Inputs (edit for your environment) ---------------------------------
set DESIGN     "gcd"
set PDK        "sky130hd"
set CORNER     "tt_025C_1v80"
set PLATFORM   "platforms/sky130hd"
set ALL_LEFS   [list "${PLATFORM}/lef/sky130_fd_sc_hd.tlef" \
                     "${PLATFORM}/lef/sky130_fd_sc_hd_merged.lef"]
set ALL_LIBS   [list "${PLATFORM}/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"]
# Point these at the ORFS results for your design (see flows/LIVE_RUN.md):
set NETLIST    "results/${PDK}/${DESIGN}/base/1_synth.v"
set SDC        "results/${PDK}/${DESIGN}/base/1_synth.sdc"
set FLOORPLAN  "results/${PDK}/${DESIGN}/base/6_final.def" ;# routed DEF
set GROUP_COUNT 50

# ---- 1. Read the flat 2D baseline ------------------------------------------
foreach lef ${ALL_LEFS} { read_lef $lef }
foreach lib ${ALL_LIBS} { read_liberty $lib }
read_verilog $NETLIST
link_design  $DESIGN
read_def -incremental $FLOORPLAN
read_sdc $SDC

# ---- 2. Parasitics ---------------------------------------------------------
# A placed design is enough for a baseline: estimate_parasitics -placement turns
# placement into RC so report_checks has real horizontal wire delay. If you read
# a fully routed DEF you may prefer extracted SPEF; -placement is the portable
# default.
set_wire_rc -signal -layer "met3"
estimate_parasitics -placement

# ---- 3. Units: declare them so the Python parser converts to SI/fs ---------
# Must match the "units" block emitted in section 5.
set_cmd_units -time ns -resistance kohm -capacitance pF -distance um

# ---- 4. Collect the worst timing paths -------------------------------------
# VERIFY: find_timing_paths returns a list of path-end handles on current
# OpenSTA. -sort_by_slack puts the most critical first.
set paths [find_timing_paths -path_delay max -group_count $GROUP_COUNT -sort_by_slack]

# ---- 5. Emit schema logic-folding-baseline/v0 ------------------------------
proc jnum {x} { if {$x eq "" || $x eq "INF"} { return "null" } else { return $x } }
proc jstr {s} { return "\"[string map {\\ \\\\ \" \\\"} $s]\"" }

# Derive the instance path from a pin full name "a/b/inst/PORT" -> "a/b/inst".
# A timing arc INTO a pin is a *wire* arc when its instance differs from the
# previous pin's instance (output->input across a net); it is a *cell* arc when
# the instance is unchanged (input->output inside one gate). This is the
# is_wire rule the contract relies on — no STA "is this a net?" query needed.
proc inst_of {pin_full_name} {
    set parts [split $pin_full_name "/"]
    if {[llength $parts] <= 1} { return $pin_full_name }
    return [join [lrange $parts 0 end-1] "/"]
}

puts "{"
puts "  \"schema\": \"logic-folding-baseline/v0\","
puts "  \"pdk\": [jstr $PDK],"
puts "  \"design\": [jstr $DESIGN],"
puts "  \"corner\": [jstr $CORNER],"
puts "  \"units\": {\"time\": \"ns\", \"resistance\": \"kohm\", \"capacitance\": \"pF\", \"length\": \"um\"},"
puts "  \"paths\": \["

set np [llength $paths]
for {set i 0} {$i < $np} {incr i} {
    set pe [lindex $paths $i]

    # VERIFY: PathEnd properties via get_property. startpoint/endpoint are pins.
    set startp [get_full_name [get_property $pe startpoint]]
    set endp   [get_full_name [get_property $pe endpoint]]
    set slack  [get_property $pe slack]
    set arr    [get_property $pe arrival]
    set req    [expr {$arr + $slack}]

    puts "    {"
    puts "      \"startpoint\": [jstr $startp],"
    puts "      \"endpoint\": [jstr $endp],"
    puts "      \"path_group\": \"clk\","
    puts "      \"path_type\": \"max\","
    puts "      \"slack\": [jnum $slack],"
    puts "      \"arrival\": [jnum $arr],"
    puts "      \"required\": [jnum $req],"
    puts "      \"driver_resistance\": null,"
    puts "      \"load_capacitance\": null,"
    puts "      \"segments\": \["

    # VERIFY: get_property $pe points -> ordered list of path points; each point
    # exposes `pin` (a pin handle) and `arrival` (cumulative time in -time units).
    set pts [get_property $pe points]
    set prev_inst ""
    set prev_arr 0.0
    set nseg 0
    set npts [llength $pts]
    for {set j 0} {$j < $npts} {incr j} {
        set pt   [lindex $pts $j]
        set pin  [get_property $pt pin]            ;# VERIFY
        set parr [get_property $pt arrival]        ;# VERIFY (cumulative)
        set pinname [get_full_name $pin]
        set inst [inst_of $pinname]
        set incr [expr {$parr - $prev_arr}]
        # First point is the launch (clock/startpoint): a cell-side arc.
        set is_wire [expr {$prev_inst ne "" && $inst ne $prev_inst}]

        if {$is_wire} {
            # VERIFY: net at this load pin. get_property $pin net -> net handle.
            set net "null"
            if {![catch {get_property $pin net} netobj] && $netobj ne ""} {
                set net [jstr [get_full_name $netobj]]
            }
            set layer "null"   ;# STA has no per-arc routing layer; odb fills geometry
            set wirelen 0       ;# placeholder; odb_wirelength.py supplies real µm
            set seg "{\"pin\": [jstr $pinname], \"net\": $net, \"layer\": $layer, \"incr_delay\": [jnum $incr], \"wire_length\": $wirelen, \"is_wire\": true}"
        } else {
            set seg "{\"pin\": [jstr $pinname], \"net\": null, \"layer\": null, \"incr_delay\": [jnum $incr], \"wire_length\": 0, \"is_wire\": false}"
        }
        if {$nseg > 0} { puts "        ," }
        puts "        $seg"
        incr nseg
        set prev_inst $inst
        set prev_arr $parr
    }
    if {$nseg == 0} {
        puts stderr "WARNING: path $i ($endp) emitted 0 segments — verify the section-5 accessors against your OpenSTA build (see flows/LIVE_RUN.md WI-2 checklist)."
    }

    puts "      \]"
    if {$i < [expr {$np - 1}]} { puts "    }," } else { puts "    }" }
}

puts "  \]"
puts "}"
