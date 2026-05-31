# flows/ — 2D baseline extraction (OpenROAD → Eq. 2)

This directory holds the recipe that turns a **flat 2D design** (placed on a
public PDK by OpenROAD) into the input the path-level break-even engine consumes.
It is the live form of the memo's **Trigger C**: an open reference flow that
reproduces the 2D baseline a reviewer can independently obtain.

```
 OpenROAD / OpenSTA           sta_dump.tcl            baseline.py             core_solver.py
 (placed DEF + Liberty)  ──▶  emits schema      ──▶   parses + converts  ──▶  Eq. 2 break-even
 read_def / link_design       logic-folding-           to SI / fs, joins        PASS / FAIL /
 estimate_parasitics          baseline/v0 (JSON)       2D baseline to 3D tax     MARGINAL
 report_checks
```

## The contract: `logic-folding-baseline/v0`

The TCL recipe and the Python parser meet at one stable JSON schema, so the
parser never has to track OpenSTA's version-specific native output. Per path:

| field | meaning | feeds |
|-------|---------|-------|
| `startpoint`, `endpoint` | timing path ends | reporting |
| `slack`, `arrival`, `required` | 2D timing (signed) | which paths are critical |
| `segments[].incr_delay` | per-arc delay | Δτ_save (via the §7 model) |
| `segments[].wire_length` | per-net horizontal length | `l_h` |
| `segments[].is_wire` | net arc vs. cell arc | only net arcs are foldable |
| `driver_resistance`, `load_capacitance` | path R_drv / C_load | Eq. 2 tax |

All numbers are in the units declared by the `units` block; the parser converts
to the engine's SI / femtosecond convention at the boundary.

The vertical via/bond parasitics, redundancy, and thermal derates — the Eq. 2
*tax* — are **not** in this schema. No 2D tool can measure them; they are
supplied separately (see `params_from_path` / `screen_path` in `baseline.py`).

## Running it

`sta_dump.tcl` needs a local OpenROAD build (which embeds OpenSTA), a public PDK
(sky130hd), and a placed design. None of those live in the repo, so this is an
operator step, not CI. With OpenROAD-flow-scripts results on hand:

```sh
openroad -no_init -exit flows/sta_dump.tcl \
    > python/tests/fixtures/sky130_gcd_baseline.json
```

Edit the LEF/Liberty/netlist/DEF paths at the top of the script for your
environment. One spot is version-sensitive — the per-path accessors — and is
marked `TODO(operator)`; verify it against your OpenROAD version. That fragile
mapping is deliberately the *only* such spot, which is why the schema is ours.

## The committed fixture is a sample, not silicon

`python/tests/fixtures/sky130_gcd_baseline.json` is an illustrative stand-in in
sky130hd-style units, committed so the parser, the join, and the Eq. 2 screen
have a tested target before a live OpenROAD run exists. Regenerate it with the
command above to replace the sample with real extracted numbers.
