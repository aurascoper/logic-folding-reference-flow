# logic-folding-reference-flow

An open reference flow for evaluating LogicFolding-style 3D-native logic folding claims, scoped to match §11 ("Independent reproduction requires an open reference flow") of the LogicFolding No-Action Decision Memo (v4, 2026-05-27).

**This repository does not assert that LogicFolding is viable.** Per the memo's final decision, the current public evidence state warrants `NO TRADE / NO ALLOCATION / NO ENGINEERING ADOPTION`. This codebase exists to make the methodology *falsifiable* on public PDKs (SkyWater 130 nm, GF180) and public benchmark RTL, so that the third reopen trigger — *an open reference flow demonstrating reproducible 3D partitioning, proxy thermal extraction, and verification on public benchmarks* — has a concrete starting point.

📄 **The source memo lives in [`docs/LogicFolding-No-Action-Decision-Memo.pdf`](./docs/LogicFolding-No-Action-Decision-Memo.pdf)** (16 pages). Equation-by-equation cross-reference to this codebase: [`docs/MEMO_INDEX.md`](./docs/MEMO_INDEX.md).

📝 **Companion writeup:** [*The Most Useful Semiconductor Paper I Wrote This Year Says Don't Buy It*](https://aurascoper.substack.com/p/the-most-useful-semiconductor-paper) — defensive-due-diligence framing of the memo for the institutional buy-side and boutique semiconductor-analysis audience.

## Architecture

```
                  +-----------------------------------+
                  |  PYTHON ORCHESTRATOR / OpenROAD   |
                  |  - Ingests Verilog, LEF/DEF       |
                  |  - Extracts timing path arrays    |
                  +-----------------+-----------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|     RUST ENGINE       |                       |     JULIA ENGINE      |
|  (Via PyO3 bindings)  |                       |  (Via PythonCall)     |
|                       |                       |                       |
|  - Discrete Graph     |                       |  - Continuous Thermal |
|    Partitioning       |                       |    Convolution        |
|  - Math-constrained   |                       |  - APC State-Space    |
|    Path-Level Loops   |                       |    Stability Model    |
+-----------------------+                       +-----------------------+
```

## Scope of evidence this flow can produce

| Memo gate           | What this flow can do                                | What it cannot do                       |
|---------------------|------------------------------------------------------|-----------------------------------------|
| Parasitic break-even (Eq. 2) | Evaluate per-path with measured or extracted RC | Substitute for advanced-node parasitics |
| Thermal kernel (Eq. 3)       | Run FFT spatial convolution under workload pulses | Replace silicon thermal maps            |
| APC stability (Eq. 4)        | Demonstrate delay-induced divergence            | Solve spatial APC for folded 3D logic   |
| Cost / Perf-per-watt (Eq. 5) | Compose value score from supplied inputs        | Replace teardown cost data              |

The flow only answers "is the methodology coherent?" Per the memo, it does not answer "does it work at 5 nm-class active logic?"

## Layout

- `python/` — Orchestrator. Houses `VerticalPathEvaluator` (`src/logic_folding_reference/core_solver.py`) implementing the path-level break-even inequality from memo Eq. 2, plus a pytest suite.
- `rust/` — `logic_folding_core` crate. Vectorized `PathEvaluator` with rayon-parallel evaluation across large mock path arrays; intended as a PyO3 target.
- `julia/` — `thermal_apc_solver.jl`. FFT-based spatial-temporal thermal convolution and EWMA run-to-run state-space simulation with variable metrology delay.
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
