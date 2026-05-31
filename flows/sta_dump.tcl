# flows/sta_dump.tcl — 2D baseline dump for the LogicFolding reference flow.
#
# REPRODUCTION RECIPE, not a CI-exercised step. It runs inside OpenROAD
# (which embeds OpenSTA) and emits this flow's stable contract,
# schema "logic-folding-baseline/v0", consumed by
# logic_folding_reference.baseline.parse_baseline_report.
#
# Why a recipe and not wired code: per memo §11 / Trigger C, a reviewer must be
# able to reproduce the 2D baseline on a PUBLIC PDK with standard tooling. This
# script depends on a local OpenROAD build + a PDK (sky130hd) + a sample design;
# none of those live in the repo. The Python parser is what stays green in CI;
# this file is what you run to regenerate the committed sample.
#
# Commands used below are the documented OpenROAD interface
# (https://openroad.readthedocs.io): read_lef / read_liberty / read_verilog /
# link_design / read_sdc / set_wire_rc / estimate_parasitics / report_checks /
# report_wire_length. Accessor names on timing-path objects vary slightly by
# OpenROAD version — the one version-sensitive spot is flagged TODO(operator)
# below; verify it against your build, which is exactly why the schema is ours
# and not OpenSTA's native JSON.
#
# Usage:
#   openroad -no_init -exit flows/sta_dump.tcl \
#       -design gcd -pdk sky130hd \
#       > python/tests/fixtures/sky130_gcd_baseline.json
#
# (Wire the file paths below to your PDK + design, e.g. an OpenROAD-flow-scripts
#  results directory.)

# ---- 0. Inputs (edit for your environment) ---------------------------------
set DESIGN     "gcd"
set PDK        "sky130hd"
set CORNER     "tt_025C_1v80"
set ALL_LEFS   [list "platforms/sky130hd/lef/sky130_fd_sc_hd.tlef" \
                     "platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef"]
set ALL_LIBS   [list "platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"]
set NETLIST    "results/${DESIGN}.v"
set FLOORPLAN  "results/${DESIGN}.def"
set SDC        "results/${DESIGN}.sdc"
set GROUP_COUNT 50

# ---- 1. Read the flat 2D baseline ------------------------------------------
foreach lef ${ALL_LEFS} { read_lef $lef }
foreach lib ${ALL_LIBS} { read_liberty $lib }
read_verilog $NETLIST
link_design  $DESIGN
read_def -incremental $FLOORPLAN
read_sdc $SDC

# ---- 2. Parasitics from placement (no full route needed for a baseline) ----
# set_wire_rc selects the per-length R/C model; estimate_parasitics -placement
# turns placement into RC so report_checks has real horizontal wire delay.
set_wire_rc -signal -layer "met3"
estimate_parasitics -placement

# ---- 3. Units: declare them so the Python parser converts to SI/fs ---------
# Keep these in sync with the "units" block emitted in step 5.
set_cmd_units -time ns -resistance kohm -capacitance pF -distance um

# ---- 4. Collect the worst timing paths -------------------------------------
set paths [find_timing_paths -path_delay max -group_count $GROUP_COUNT -sort_by_slack]

# ---- 5. Emit schema logic-folding-baseline/v0 ------------------------------
proc jstr {s} { return "\"[string map {\\ \\\\ \" \\\"} $s]\"" }

puts "{"
puts "  \"schema\": \"logic-folding-baseline/v0\","
puts "  \"pdk\": [jstr $PDK],"
puts "  \"design\": [jstr $DESIGN],"
puts "  \"corner\": [jstr $CORNER],"
puts "  \"units\": {\"time\": \"ns\", \"resistance\": \"kohm\", \"capacitance\": \"pF\", \"length\": \"um\"},"
puts "  \"paths\": \["

set n [llength $paths]
for {set i 0} {$i < $n} {incr i} {
  set path [lindex $paths $i]

  # TODO(operator): the four accessors below are the version-sensitive spot.
  # On recent OpenROAD/OpenSTA these are available via the STA path API; verify
  # names against your build (e.g. `sta::path_*` or get_property on the path).
  # Pull the exact command for your version from the OpenROAD docs before relying
  # on this recipe. The point of the schema is that ONLY this mapping is fragile.
  set startp [get_property $path startpoint]
  set endp   [get_property $path endpoint]
  set slack  [get_property $path slack]
  set arr    [get_property $path arrival]
  set req    [expr {$arr + $slack}]

  puts "    {"
  puts "      \"startpoint\": [jstr $startp],"
  puts "      \"endpoint\": [jstr $endp],"
  puts "      \"path_group\": \"clk\","
  puts "      \"path_type\": \"max\","
  puts "      \"slack\": $slack,"
  puts "      \"arrival\": $arr,"
  puts "      \"required\": $req,"
  puts "      \"driver_resistance\": null,"
  puts "      \"load_capacitance\": null,"
  puts "      \"segments\": \["
  # TODO(operator): iterate the path's pin/net arcs and, for each net arc, emit
  #   {"pin","net","layer","incr_delay","wire_length","is_wire":true}
  # Per-net horizontal length comes from `report_wire_length -net <net>
  # -detailed_route` (or -global_route); incr_delay from the path arc delay.
  # Cell (gate) arcs get "is_wire": false and wire_length 0.
  puts "      \]"
  if {$i < [expr {$n - 1}]} { puts "    }," } else { puts "    }" }
}

puts "  \]"
puts "}"
