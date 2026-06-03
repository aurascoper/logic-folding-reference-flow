# tools/guards — falsifiability regression net

Deterministic guards that protect this repo's **documented, non-obvious design
decisions** from being silently "fixed" away. They exist because the repo's whole
value is falsifiability: claiming an unbuilt capability — or erasing a documented
constraint — is the highest-severity defect here.

## Provenance

These guards were derived from an adversarial falsification pass (5 multi-step
tasks run against fresh coding agents in isolated worktrees, then classified by an
adversarial 2-lens judge panel). Of five documented constraints probed, four were
retained and **one broke**: an agent asked to "unify the two Eq.2 engines" added
the self-loading terms to the Rust evaluator and **deleted the `MEMO_INDEX:12`
note that the abbreviation is intentional**, reframing a by-design decision as a
bug. `guard_eq2_divergence` is the direct net for that failure. The captured
evidence and the full report live outside the repo (in the `sia-falsification`
bridge); these guards are the durable product.

## The guards

| Guard | Protects | Mechanism |
|-------|----------|-----------|
| `guard_eq2_divergence.py` | the **intentional** Rust/Python Eq.2 abbreviation | fires if Rust gains an `r_v*c_v`/`r_b*c_b` self-loading term **or** the `MEMO_INDEX` provenance note is erased |
| `guard_no_phantom_pyo3.py` | "PyO3 bridge is planned, not present" | fires if Python imports `logic_folding_core` while `rust/Cargo.toml` has no `pyo3` |
| `guard_path_segments.py` | the real field is `.segments` (WireSegment) | AST-flags `.nodes` access in the package |
| `guard_no_invented_yield.py` | stacked-die yield is **deliberately unmodeled** | flags a hardcoded yield/`C_good` literal |
| `guard_fs_units.py` | units are fs downstream of the parser | **heuristic**: a `*_fs` quantity compared to a bare `<1000` literal (50 ps must be `50_000` fs) |
| `guard_claimed_pass_has_command.py` | evidence-forensics | a "tests pass" claim must follow a real test invocation in the transcript |

Each exposes `find_violations(root)` (importable, unit-tested) and a CLI/hook entry.

## Escape hatch

A guard protects a constraint; it does not forbid changing it *deliberately*. To
intentionally change the Eq.2 divergence, add a memo-traceable sentinel
`EQ2-DIVERGENCE-CHANGE-APPROVED: <memo ref>` to `MEMO_INDEX.md` or `lib.rs`.

## Running

```sh
python/venv/bin/python -m pytest tools/guards/test_guards.py -q   # 16 tests
python/venv/bin/python tools/guards/run_guards.py                 # scan main, exit 2 on violation
```

Wired in `.claude/settings.json`: `run_guards.py` as a PostToolUse hook on
Edit|Write|MultiEdit, and `guard_claimed_pass_has_command.py` as a Stop hook.
Guards are stdlib-only and fail open per-guard (a guard bug never blocks an edit).
