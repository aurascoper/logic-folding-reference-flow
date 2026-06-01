# LIVE_RUN — demonstrating the 2D baseline on a public PDK (Trigger C)

Operator runbook for taking the recipes from "contract + recipe" to
"demonstrated on a real sky130 design." Host-agnostic; the worked path below is
GitHub Codespaces (native Linux, no Apple-Silicon emulation).

## Success gate (4 parts)

The committed fixtures are illustrative numbers, not silicon — they will *not*
match real extraction, by design. Success is:

1. **Runs** — the recipe completes on a real sky130 design.
2. **Schema-valid** — output loads/adapts without error.
3. **Contract holds (the real test)** — the existing Python consumer
   (`adapt_opensta_checks` → `parse_baseline_report` → `merge_net_lengths` →
   `screen_path`) ingests the real output **with no consumer changes**. ✅ This
   is already proven in CI against a captured real dump
   (`python/tests/fixtures/opensta_gcd_placed_checks.json`).
4. **Fixtures replaced** — swap the illustrative fixtures for the real pair and
   re-point value-specific test assertions; `pytest` green.

## How the timing dump works now

`sta_dump.tcl` just emits `report_checks -format json` (a stable, documented
OpenSTA feature) between `===LF-JSON-BEGIN/END===` markers. The fragile part —
walking a path's arcs, classifying **wire vs cell** (from each pin's
`instance`), pulling nets — lives in **tested Python** (`adapt_opensta_checks`),
so there is no per-version Tcl to hand-verify. `report_checks` JSON is SI
(seconds/farads/meters); the adapter + parser handle units.

## Toolchain notes (learned the hard way)

- **Apple Silicon + Docker emulation**: don't. Use Codespaces.
- **The ORFS Codespace ships source, not built tools.** Easiest fix: run the
  prebuilt image directly (skip `util/docker_shell`, which dies on `xauth` in a
  headless box):
  ```sh
  docker run --rm -it -v /workspaces/OpenROAD-flow-scripts/flow:/OpenROAD-flow-scripts/flow openroad/orfs:latest bash
  ```
- **`illegal instruction` at CTS** = the prebuilt binary wants AVX-512 the VM
  lacks (`grep avx /proc/cpuinfo` → only `avx avx2`). Routing is blocked on the
  prebuilt image; a **from-source build** (`./build_openroad.sh --local`) targets
  this CPU and routes cleanly. Placement still completes, which is enough for the
  timing baseline.

## Step 1 — build a design

Inside the toolbox (`#` prompt):
```sh
source /OpenROAD-flow-scripts/env.sh
cd /OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk
```
If CTS crashes (AVX-512), you still have the placed stage: `3_place.odb` /
`3_place.sdc` under `results/sky130hd/gcd/base/` — enough for timing.

## Step 2 — timing dump

Edit the `LIB_GLOB`/`DB`/`SDC` vars at the top of `sta_dump.tcl` to your stage
(defaults target placed `3_place.odb`). Then:
```sh
openroad -no_init -exit /path/to/flows/sta_dump.tcl > checks.json 2> sta_dump.log
```

## Step 3 — (later, needs routing) geometry dump

Once you have a *routed* design (from a source build):
```sh
openroad -python /path/to/flows/odb_wirelength.py \
  --tlef platforms/sky130hd/lef/sky130_fd_sc_hd.tlef \
  --lef  platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef \
  --def  results/sky130hd/gcd/base/6_final.def \
  --pdk sky130hd --design gcd > netlen.json 2> odb.log
```
Caveat for the geometry merge: ORFS hierarchical synthesis can give a load
pin's net a hierarchical alias (e.g. `gcd/.../A[4]`) instead of the flat odb
name (`_029_`). If `merge_net_lengths` reports missing nets, that's the
reconciliation to do (e.g. flatten the netlist, or map aliases).

## Step 4 — validate the contract (gate #3)

`check_live.py` accepts the raw `report_checks` json, the banner-wrapped
`sta_dump.tcl` output, or an already-converted v0 file:
```sh
python /path/to/flows/check_live.py checks.json            # timing only
python /path/to/flows/check_live.py checks.json netlen.json  # + routed geometry
```
`GATE 1-3 PASS` means the contract survived contact with real OpenROAD output.

## Step 5 — replace fixtures, keep the suite green

```sh
cp checks.json  /path/to/repo/python/tests/fixtures/opensta_<design>_checks.json
cp netlen.json  /path/to/repo/python/tests/fixtures/sky130_<design>_netlen.json
cd /path/to/repo/python && pytest -q
```
Re-point value-specific assertions (exact slacks/lengths, path counts, the
`opensta_gcd_placed_checks.json` numbers) to the new design; structural tests
pass unchanged.

## What to paste back

1. `ls -1 results/sky130hd/gcd/base/`
2. `sta_dump.log` (and `odb.log` if you got routing working)
3. `checks.json` (or `head -c 4000`), and `netlen.json` if present
4. the `check_live.py` output (or the error/traceback)
