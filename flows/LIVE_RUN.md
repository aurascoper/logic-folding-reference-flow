# LIVE_RUN — demonstrating the 2D baseline on a public PDK (Trigger C)

This is the operator runbook for taking the two recipes (`sta_dump.tcl`,
`odb_wirelength.py`) from "contract + recipe" to **"demonstrated on a real
sky130 design."** It is host-agnostic: run it wherever you have OpenROAD + a PDK
(Docker, a Linux box, a VM), then paste the outputs back.

## Success gate (4 parts — read this first)

The committed fixtures (`sky130_gcd_baseline.json`, `sky130_gcd_netlen.json`)
are **illustrative numbers, not silicon** — they will *not* match real
extraction, by design. "Success" is therefore **not** "the numbers match." It is:

1. **Runs** — both recipes complete on a real sky130 design.
2. **Schema-valid** — each emits `…/v0` JSON that loads without error.
3. **Contract holds (the real test)** — the existing Python consumer
   (`parse_baseline_report` → `merge_net_lengths` → `screen_path`) ingests the
   real output **with zero changes to the consumer code**. If the parser needs a
   change, that is a *finding* about the contract, not a pass.
4. **Fixtures replaced** — the illustrative fixtures are swapped for the real
   extracted pair, value-specific test assertions re-pointed, `pytest` green.

## Prerequisites

- OpenROAD (embeds OpenSTA + odb) and Yosys — easiest via OpenROAD-flow-scripts
  (ORFS), which also bundles the **sky130hd** PDK and the `gcd`/`aes`/`ibex`
  designs. Docker image `openroad/flow-scripts`, or a local build per ORFS
  `docs/user/BuildLocally.md`.
- This repo checked out, with `python/` installed: `cd python && pip install -e .[test]`.

## Step 1 — Generate a real routed design (ORFS)

`gcd` first (smallest/fastest); `aes` later for a richer path mix.

```sh
cd OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk
```

This runs RTL→GDS and leaves results under
`flow/results/sky130hd/gcd/base/`. List that directory and note the exact names
(they vary by ORFS version):

```sh
ls -1 flow/results/sky130hd/gcd/base/
# expect, roughly:
#   1_synth.v        <- synthesized netlist  -> sta_dump.tcl NETLIST
#   1_synth.sdc      <- constraints          -> sta_dump.tcl SDC
#   6_final.def      <- ROUTED DEF           -> odb_wirelength.py --def  (and sta_dump FLOORPLAN)
# (and 2_*..5_* intermediate stages)
```

Tech LEF / Liberty live under `flow/platforms/sky130hd/`.

## Step 2 — Bind the files

Edit the `set` lines at the top of `flows/sta_dump.tcl` (NETLIST / SDC /
FLOORPLAN / ALL_LEFS / ALL_LIBS) to the paths from Step 1. Run all commands
below from the ORFS `flow/` directory (or wherever those relative paths resolve),
with this repo's `flows/` reachable.

## Step 3 — Timing dump  →  `logic-folding-baseline/v0`

```sh
openroad -no_init -exit /path/to/repo/flows/sta_dump.tcl \
    > sky130_gcd_baseline.json 2> sta_dump.log
```

### ⚠ WI-2 verification checklist (do this once, carefully)

`sta_dump.tcl` section 5 (the per-path arc walk) is a **draft written blind** —
verify it before trusting the output:

- [ ] `sta_dump.log` has **no** `emitted 0 segments` warnings.
- [ ] Open the JSON: each path's `segments` has length ≈ (number of pins on the
      path), not empty.
- [ ] `is_wire` **alternates** sensibly: cell arc (same instance, `is_wire:false`,
      `net:null`) then wire arc (instance changes, `is_wire:true`, a real `net`).
- [ ] `segments[].net` names look like real sky130 nets and will match the keys
      `odb_wirelength.py` produces (Step 4) — this is the geometry join key.
- [ ] `slack` is signed (most paths positive; the worst may be negative).

If any `VERIFY:` accessor in section 5 is wrong for your OpenROAD version, fix it
there (e.g. how to get a path's points, a point's pin/arrival, a pin's net) and
re-run. The Python consumer does **not** change — only this producer does.

## Step 4 — Geometry dump  →  `logic-folding-netlen/v0`

```sh
openroad -python /path/to/repo/flows/odb_wirelength.py \
    --tlef flow/platforms/sky130hd/lef/sky130_fd_sc_hd.tlef \
    --lef  flow/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef \
    --def  flow/results/sky130hd/gcd/base/6_final.def \
    --pdk sky130hd --design gcd \
    > sky130_gcd_netlen.json 2> odb_wirelength.log
```

`odb_wirelength.log` reports `N routed nets, M unrouted (omitted)`. Unrouted nets
are intentionally absent — `merge_net_lengths` will surface any timed-but-
unrouted wire loudly rather than faking a 0.

## Step 5 — Validate the contract (gate #3, no consumer changes)

```sh
python - <<'PY'
import json
from logic_folding_reference import (
    parse_baseline_report, load_net_lengths, merge_net_lengths, screen_path,
    derive_foldable_savings, ProcessParameters,
)
raw = json.load(open("sky130_gcd_baseline.json"))
nl  = load_net_lengths("sky130_gcd_netlen.json")
merged = merge_net_lengths(raw, nl, on_missing="error")   # raises if a timed wire is unrouted
report = parse_baseline_report(merged)
print(f"parsed {len(report.paths)} real paths; merge + parse OK with no code changes")

# Eq.2 screen with an illustrative 3D tax (the LHS is now real silicon-grade data)
tax = ProcessParameters(r_v=10, c_v=0.5e-15, r_b=8, c_b=0.4e-15, r_drv=200,
                        c_load=5e-15, dtau_red_fs=20, dtau_thermal_fs=15,
                        parasitic_noise_floor_fs=10)
for p in report.paths[:5]:
    d = screen_path(p, tax, n_vertical_vias=2, n_bond_contacts=1)
    print(f"  {p.endpoint:24s} l_h={p.total_wire_length_m*1e6:7.1f}um "
          f"Δτ_save={derive_foldable_savings(p):8.0f}fs -> {d.label.value}")
PY
```

If this runs clean, **gate #3 is met**: the contract survived contact with real
tool output. If it raised, capture the error — that is the finding.

## Step 6 — Replace the fixtures, keep the suite green

```sh
cp sky130_gcd_baseline.json /path/to/repo/python/tests/fixtures/sky130_gcd_baseline.json
cp sky130_gcd_netlen.json   /path/to/repo/python/tests/fixtures/sky130_gcd_netlen.json
cd /path/to/repo/python && pytest -q
```

Value-specific assertions in `tests/test_baseline_ingest.py` (exact µm/ns numbers,
the `len(report.paths) == 4` count, the `_loc_reg_2_/D` local-path name) were
written for the illustrative sample and **will** need re-pointing to the real
design. Update them to the new numbers; the *structural* tests (units convert,
cell arcs untouched, merge join, on_missing policy) should pass unchanged. Drop
the now-stale `_note` "illustrative sample" lines from the fixtures.

## What to paste back

Since you're running the host, paste back so I can validate + wire the fixtures:

1. `ls -1` of `flow/results/sky130hd/gcd/base/`.
2. `sta_dump.log` and `odb_wirelength.log` (the warning/summary lines).
3. The two JSON files (or `head -c 4000` of each if large).
4. The Step-5 output (or the error/traceback if it raised).

I'll confirm the 4-part gate, fix any `VERIFY:` accessor that tripped, and
re-point the test assertions to the real numbers.
