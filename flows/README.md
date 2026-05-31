# flows/ — 2D baseline extraction (OpenROAD → Eq. 2)

This directory holds the operator-run recipes that turn a **flat 2D design**
(placed and routed on a public PDK by OpenROAD) into the input the path-level
break-even engine consumes. It is the live form of the memo's **Trigger C**: an
open reference flow that reproduces the 2D baseline a reviewer can independently
obtain.

Two recipes feed one contract — **STA gives the time, odb gives the space**:

```
 OpenROAD / OpenSTA        sta_dump.tcl          baseline.py            core_solver.py
 (placed DEF + Liberty) ─▶ emits timing      ─▶  parse + convert    ─▶  Eq. 2 break-even
 estimate_parasitics       logic-folding-         to SI/fs; join         PASS / FAIL /
 report_checks             baseline/v0 (JSON)     anchor + 3D tax        MARGINAL
                                                        ▲
 OpenROAD / odb            odb_wirelength.py          │ merge_net_lengths()
 (ROUTED DEF)           ─▶ emits geometry     ───────▶┘ fills segments[].wire_length
 net.getWire().getLength() logic-folding-               with real routed µm
 getDbUnitsPerMicron()     netlen/v0 (JSON)
```

## The timing contract: `logic-folding-baseline/v0`

The TCL recipe and the Python parser meet at one stable JSON schema, so the
parser never has to track OpenSTA's version-specific native output. Per path:

| field | meaning | feeds |
|-------|---------|-------|
| `startpoint`, `endpoint` | timing path ends | reporting |
| `slack`, `arrival`, `required` | 2D timing (signed) | which paths are critical |
| `segments[].incr_delay` | per-arc delay | Δτ_save (via the §7 model) |
| `segments[].wire_length` | per-net horizontal length | `l_h` |
| `segments[].is_wire` | net arc vs. cell arc | only net arcs are foldable |
| `segments[].net` | net name | join key for geometry merge |
| `driver_resistance`, `load_capacitance` | path R_drv / C_load | Eq. 2 tax |

All numbers are in the units declared by the `units` block; the parser converts
to the engine's SI / femtosecond convention at the boundary.

The vertical via/bond parasitics, redundancy, and thermal derates — the Eq. 2
*tax* — are **not** in this schema. No 2D tool can measure them; they are
supplied separately (see `params_from_path` / `screen_path` in `baseline.py`).

## The geometry sidecar: `logic-folding-netlen/v0`

`sta_dump.tcl` can carry a wire-length estimate, but the authoritative value of
`l_h` comes from real routed copper, not Half-Perimeter Wire Length (HPWL). HPWL
is a fine early-placement proxy, but it smooths over the doglegs, layer
assignment, and congestion detours that actual routing introduces.

`odb_wirelength.py` reads a **routed** DEF through OpenROAD's `odb` database and
emits per-net routed length:

```json
{ "schema": "logic-folding-netlen/v0",
  "units": {"length": "um"},
  "net_lengths": {"_088_": 41.2, "_140_": 66.4} }
```

`baseline.merge_net_lengths(report, load_net_lengths(sidecar))` joins it into the
timing contract on `segments[].net`, writing only wire arcs (`is_wire`) and
leaving cell arcs untouched. An **unrouted** net is *absent* from the sidecar —
odb's `net.getWire()` returns `None` — so a missing key means "no routed copper",
which the merge's `on_missing="error"` default surfaces loudly rather than
faking a zero.

## Running them

Both recipes need a local OpenROAD build, a public PDK (sky130hd), and a design;
none live in the repo, so they are operator steps, not CI.

```sh
# timing (placed design is enough for estimate_parasitics)
openroad -no_init -exit flows/sta_dump.tcl \
    > python/tests/fixtures/sky130_gcd_baseline.json

# geometry (needs a ROUTED .def)
openroad -python flows/odb_wirelength.py \
    --tlef <tech.lef> --lef <cells.lef> --def <routed.def> \
    --pdk sky130hd --design gcd \
    > python/tests/fixtures/sky130_gcd_netlen.json
```

Edit the file paths for your environment. In `sta_dump.tcl` one spot is
version-sensitive — the per-path accessors — and is marked `TODO(operator)`;
verify it against your OpenROAD version. The `odb` calls in `odb_wirelength.py`
are the documented Python API (`net.getWire().getLength()`,
`block.getDbUnitsPerMicron()`; OpenROAD `test/python_api.md`).

## The committed fixtures are samples, not silicon

`python/tests/fixtures/sky130_gcd_baseline.json` and `…_netlen.json` are
illustrative stand-ins in sky130hd-style units, committed so the parser, the
geometry merge, and the Eq. 2 screen have a tested target before a live OpenROAD
run exists. The `netlen` lengths are deliberately a bit longer than the
baseline's placeholders to show routed copper exceeding the estimate. Regenerate
both with the commands above to replace the samples with real extracted numbers.
