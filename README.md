# logic-folding-reference-flow

An open reference flow for evaluating LogicFolding-style 3D-native logic folding claims, scoped to match §11 ("Independent reproduction requires an open reference flow") of the LogicFolding No-Action Decision Memo (v4, 2026-05-27).

**This repository does not assert that LogicFolding is viable.** Per the memo's final decision, the current public evidence state warrants `NO TRADE / NO ALLOCATION / NO ENGINEERING ADOPTION`. This codebase exists to make the methodology *falsifiable* on public PDKs (SkyWater 130 nm, GF180) and public benchmark RTL, so that the third reopen trigger — *an open reference flow demonstrating reproducible 3D partitioning, proxy thermal extraction, and verification on public benchmarks* — has a concrete starting point.

**The source memo lives in [`docs/LogicFolding-No-Action-Decision-Memo.pdf`](./docs/LogicFolding-No-Action-Decision-Memo.pdf)** (16 pages). Equation-by-equation cross-reference to this codebase: [`docs/MEMO_INDEX.md`](./docs/MEMO_INDEX.md).

**Trigger watch:** [`docs/TRIGGER_WATCH.md`](./docs/TRIGGER_WATCH.md) logs public LogicFolding developments and scores each against the memo's three reopen triggers. As of 2026-05-30, none has fired and the no-action decision stands.

**Companion writeup:** [*The Most Useful Semiconductor Paper I Wrote This Year Says Don't Buy It*](https://aurascoper.substack.com/p/the-most-useful-semiconductor-paper) — defensive-due-diligence framing of the memo for the institutional buy-side and boutique semiconductor-analysis audience.

## Architecture

```
                  +-----------------------------------+
                  |     PYTHON REFERENCE EVALUATOR    |
                  |  - memo Eq. 2, full form (§7)     |
                  |  - in: extracted RC + mock paths  |
                  +-----------------+-----------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|     RUST ENGINE       |                       |     JULIA ENGINE      |
|  (PyO3 planned)       |                       |  (PythonCall planned) |
|                       |                       |                       |
|  - Abbreviated Eq. 2  |                       |  - FFT thermal conv.  |
|    break-even gate    |                       |    (§8, Eq. 3)        |
|  - mock-path sweep    |                       |  - APC + is_diverging |
|    (rayon-parallel)   |                       |    (§9, Eq. 4)        |
+-----------------------+                       +-----------------------+
```

> **On OpenROAD / OpenSTA.** These define the unit conventions the flow speaks
> (ohms, farads, femtoseconds) and are its intended *2D baseline anchor* — the
> flat, planar source of real per-path RC and slack. OpenROAD does flat 2D
> place-and-route; it does **not** perform the 3D folding, and the flow does not
> ask it to. The Verilog / LEF / DEF ingestion now has a **contract and recipe,
> not yet a live run**: `python/src/logic_folding_reference/baseline.py` parses
> this flow's `logic-folding-baseline/v0` schema into the Eq. 2 engine, and
> `flows/sta_dump.tcl` is the OpenROAD recipe that emits it. Producing real
> numbers still requires an operator to run OpenROAD on a public PDK; the
> committed fixture is an illustrative sample, not silicon. Closing that last
> step on a public PDK is precisely the memo's Trigger C, and the reason this
> repository exists.

> **The two engines are isolated mathematical test-beds, not a wired toolchain.**
> The Rust crate (`rlib`/`cdylib`, no `pyo3` dependency yet) sweeps the
> *abbreviated* Eq. 2 over synthetic mock paths with `rayon`; the Julia module
> runs the §8 FFT thermal kernel and the §9 EWMA APC loop, whose `is_diverging`
> screen trips on controller divergence under delayed metrology — not on thermal
> runaway. Per both files' own headers this makes the methodology *coherent*, not
> *feasible*: passing the gate is necessary, never sufficient.

## Scope of evidence this flow can produce

| Memo gate           | What this flow can do                                | What it cannot do                       |
|---------------------|------------------------------------------------------|-----------------------------------------|
| Parasitic break-even (Eq. 2) | Evaluate per-path with measured or extracted RC | Substitute for advanced-node parasitics |
| Thermal kernel (Eq. 3)       | Run FFT spatial convolution under workload pulses | Replace silicon thermal maps            |
| APC stability (Eq. 4)        | Demonstrate delay-induced divergence            | Solve spatial APC for folded 3D logic   |
| Cost / Perf-per-watt (Eq. 5) | Compose value score from supplied inputs        | Replace teardown cost data              |

The flow only answers "is the methodology coherent?" Per the memo, it does not answer "does it work at 5 nm-class active logic?"

## Deliberately unmodeled: stacked-die yield and inter-wafer variation

One physical dimension is omitted by design: yield across a bonded stack, and the parametric variation between layers that compounds when two independently processed wafers are folded together. Modeling it honestly requires per-layer parametric distributions and a bonding-yield figure, and those numbers exist only inside a foundry PDK. A public PDK disclosure for dual-active-logic stacking is precisely the memo's **Trigger B** (see [`docs/TRIGGER_WATCH.md`](./docs/TRIGGER_WATCH.md)), which has not fired. Until it does, any yield or variation term in the break-even calculation would be a slider over invented data; the value of this flow is that every input it consumes is one a reviewer can independently obtain on a public PDK.

When a teardown does arrive (**Trigger A**, expected no earlier than the fall 2026 Mate 90 / Kirin 9050 shipment), inter-wafer process variation and stacked-die yield join sustained-thermal behavior and the fraction of logic actually folded on the measurement checklist. The 2026-05-30 trigger-watch entry logs this as a teardown variable rather than a model parameter.

## Layout

- `python/` — Eq. 2 engine + 2D-baseline ingestion. `core_solver.py` holds `VerticalPathEvaluator` (the path-level break-even inequality, memo §7 Eq. 2); `baseline.py` parses the `logic-folding-baseline/v0` contract (OpenROAD / OpenSTA output) into that engine, merges real routed wire length from odb, and joins it to the 3D tax. Pytest suite included.
- `rust/` — `logic_folding_core` crate. Vectorized `PathEvaluator` with rayon-parallel evaluation across large mock path arrays; intended as a PyO3 target.
- `julia/` — `thermal_apc_solver.jl`. FFT-based spatial-temporal thermal convolution and EWMA run-to-run state-space simulation with variable metrology delay.
- `flows/` — operator-run OpenROAD recipes for the live Trigger-C step: `sta_dump.tcl` emits the `logic-folding-baseline/v0` timing contract, and `odb_wirelength.py` emits the `logic-folding-netlen/v0` routed-geometry sidecar (real per-net µm from a routed DEF, merged in by `baseline.merge_net_lengths`). See `flows/README.md`.
- `docs/` — Cross-reference to the source memo and section anchors.

## Quick start

```sh
# Python
cd python && pip install -e . && pytest

# Rust
cd rust && cargo test --release

# Julia
julia --project=julia -e 'import Pkg; Pkg.instantiate()' && julia --project=julia julia/scripts/run_apc_divergence_demo.jl
```

## Memo-grounded primitives

All physical constants used by the engines map to memo §7 / §8 / §9 / §10 symbols:

| Symbol    | Meaning                                              | Memo ref |
|-----------|------------------------------------------------------|----------|
| `Δτ_save` | Horizontal-delay saved by folding a wire of length `l_h` | §7, Eq. 2 |
| `N_v, R_v, C_v` | Vertical-via count, resistance, capacitance    | §7, Eq. 2 |
| `N_b, R_b, C_b` | F2F bond contact count, resistance, capacitance | §7, Eq. 2 |
| `R_drv, C_load` | Driver output resistance, downstream load cap  | §7, Eq. 2 |
| `Δτ_red`  | Redundancy / test / alignment overhead delay         | §7, Eq. 2 |
| `Δτ_T`    | Thermal delay derating under sustained workload      | §7, Eq. 2; §8, Eq. 3 |
| `K(r,r',t-s)` | Calibrated thermal kernel (stack + package + cooling) | §8, Eq. 3 |
| `p_W(r,t)`| Power-density field for workload `W`                 | §8, Eq. 3 |
| `A_k, B_k, C_k, d_k` | APC time-varying matrices + variable measurement delay | §9, Eq. 4 |
| `S_value` | (Perf/W)\_3D / (Perf/W)\_planar × C\_good,planar / C\_good,3D | §10, Eq. 5 |

## What this flow is, and is not

Per memo §11: *"Such a flow would only answer 'is the methodology coherent?' It would not answer 'does it work at 5 nm-class active logic?' The latter still requires foundry data and silicon."*

## License

Licensed under the [Apache License, Version 2.0](LICENSE). See `NOTICE` for attribution. The choice is intentional: Apache-2.0 includes an explicit patent grant from contributors, which matters for a flow that touches partitioning and physical-design techniques where patent encumbrance is common.
