# Memo cross-reference

Source: `LogicFolding-No-Action-Decision-Memo.pdf` (v4, 2026-05-27).

This index maps the codebase to the memo so anyone reviewing the implementation can verify it faithfully encodes the memo's equations rather than reinterpreting them.

## Equation map

| Memo eq. | File:line                                                              | Notes |
|----------|------------------------------------------------------------------------|-------|
| Eq. 2 (path break-even)   | `python/src/logic_folding_reference/core_solver.py:VerticalPathEvaluator.evaluate` | Full form with R_v·C_v and R_b·C_b self-loading terms |
| Eq. 2 (path break-even)   | `rust/src/lib.rs:PathEvaluator::evaluate`                              | Note: per the user-provided Rust task spec, omits R_v·C_v / R_b·C_b self-loading; see code comment |
| Eq. 3 (thermal kernel)    | `julia/src/thermal_apc_solver.jl:calculate_thermal_profile`            | FFT-based spatial convolution |
| Eq. 4 (APC state-space)   | `julia/src/thermal_apc_solver.jl:run_apc_simulation`                   | Time-varying A_k, B_k, C_k with variable delay d_k |
| Eq. 5 (value score)       | not implemented (out of scope for v0)                                  | Memo §10 — see future-work in README |

## Decision-policy anchors

- Memo §7: "If only very long global paths pass, the approach may be a niche floorplanning technique, not a standard-cell-level scaling law." — `core_solver.py` reports per-path margins so callers can stratify by `l_h` themselves.
- Memo §8: "the same chip can pass burst benchmarks and fail sustained workloads. Therefore burst scores are not investment evidence." — `thermal_apc_solver.jl` workloads default to >= 10-minute sustained pulses.
- Memo §9: "Spatial APC for folded 3D logic under sparse delayed metrology is not merely a missing parameter; it is an unsolved control problem." — APC code is illustrative, demonstrates divergence, does not claim to be a portability proof. Matches memo's stance.

## Reopen-trigger position

Per memo §6, this codebase addresses **Trigger C: Open reference flow** ("Open-source 3D-native partitioning and proxy signoff runnable on public PDKs and benchmarks"). It does not address Triggers A (shipping teardown) or B (foundry disclosure).
