# Sweep results: what-if analysis of Huawei's claimed Kirin 2026 data

**Run date:** 2026-07-28
**Script:** [`python/scripts/kirin_2026_whatif.py`](../python/scripts/kirin_2026_whatif.py)
**Fixture:** [`python/tests/fixtures/kirin_2026_claimed.json`](../python/tests/fixtures/kirin_2026_claimed.json)

This document records the output of running the break-even sweep against Huawei's claimed Kirin 2026 numbers, so a reader can see the result without cloning and running the code. It is a **what-if analysis, not evidence**: every input number is vendor self-reported (Tau Scaling Law V2 paper, He Tingbo, 2026-07-03), not an independent measurement. The conditional being evaluated is: *if these claimed numbers are accurate, what would the break-even inequality (memo §7, Eq. 2) show?*

Reproduce with:

```sh
cd python && pip install -e . && python scripts/kirin_2026_whatif.py
```

## Inputs

From the claimed fixture (all self-reported, status `NOT VERIFIED`):

| Quantity | Claimed value |
|----------|---------------|
| Frequency | 3.1 GHz (clock period 322.6 ps) |
| Transistor density | 238.0 MTr/mm² |
| Efficiency gain | +41% |

Synthetic path ensemble: 10,000 paths, 8% global / 92% local — the memo §7 right-tail structure. Because Huawei has disclosed no via/bond RC values (Trigger B has not fired), the sweep brackets the parasitic space with four scenarios rather than asserting one.

## Eq. 2 break-even gate — results by scenario

| Scenario | Via/bond RC (r_v, c_v, r_b, c_b) | Δτ_red / Δτ_T | PASS | Global passing | Local passing |
|----------|-----------------------------------|----------------|------|----------------|---------------|
| optimistic | 2 Ω, 0.2 fF, 2 Ω, 0.1 fF | 10 fs / 5 fs | 67.5% | 820/820 (100%) | 5926/9180 (64.6%) |
| moderate | 10 Ω, 0.5 fF, 8 Ω, 0.4 fF | 20 fs / 15 fs | 17.8% | 820/820 (100%) | 964/9180 (10.5%) |
| pessimistic | 25 Ω, 1.0 fF, 20 Ω, 0.8 fF | 50 fs / 100 fs | 7.5% | 749/820 (91.3%) | 0/9180 (0%) |
| thermal_stress | 10 Ω, 0.5 fF, 8 Ω, 0.4 fF | 20 fs / 300 fs | 8.1% | 812/820 (99.0%) | 0/9180 (0%) |

Marginal paths omitted from the table (7.2% optimistic, 4.1% moderate, ≈0% elsewhere); full breakdown in the script output.

## Reading the table

1. **Global paths are the only robust survivors.** The long global wires (the 8% right tail) clear the gate in every scenario. Local paths clear it only in the optimistic corner — near-ideal parasitics Huawei has not demonstrated — and collapse to 10.5% under moderate assumptions and 0% under pessimistic or thermal stress. As parasitics move from optimistic toward the literature-plausible range, the overall pass rate falls from 67.5% to ~8%, converging on the global tail.
2. **The thermal derating term dominates.** Holding parasitics at the moderate values and raising only Δτ_T to 300 fs (sustained-workload derating) drops the pass rate from 17.8% to 8.1% and zeroes the local paths. This is the memo §8 point in numbers: burst benchmarks are not sustained evidence, and Huawei has published no sustained thermal data.
3. **The decisive inputs remain undisclosed.** The spread between scenarios — 67.5% to 7.5% — is driven entirely by via/bond parasitics and thermal derating, none of which Huawei has released. The real answer requires PDK-level data (Trigger B) or a teardown (Trigger A).

## Interpretation

This is memo §7 stratification, reproduced under Huawei's own claimed numbers: folding pays on long global wires and fails as a general standard-cell-level substitute once parasitics leave the optimistic corner. Nothing in the V2 paper's disclosed data moves the break-even gate for the 92% of paths that are local. The what-if therefore does not change — and modestly reinforces — the no-action conclusion.

## Caveat

Every input is Huawei's self-reported claim. Passing or failing this sweep neither validates nor refutes the Kirin 2026 chip; it tests the *internal coherence* of the claims against the memo's physics. Per the memo, self-reported data does not clear the independent-evidence bar. `NO TRADE / NO ALLOCATION / NO ENGINEERING ADOPTION` stands. See [`TRIGGER_WATCH.md`](TRIGGER_WATCH.md) (2026-07-03 entry) for the trigger scoring of the V2 paper itself.
