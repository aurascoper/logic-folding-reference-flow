# Teardown watch: pre-commitment rubric

**Pre-committed:** 2026-09-30, before any professional Kirin 9050 Pro teardown was located in the public record.

This file fixes the scoring bar before the next evidence event. Its purpose is to prevent either result-driven over-claiming ("a professional teardown exists, therefore LogicFolding is validated") or result-driven under-claiming ("the report lacks every memo input, therefore it counts for nothing"). A teardown can resolve some questions without resolving the thesis.

## Qualifying evidence

A report qualifies for scoring if it comes from **TechInsights, SemiAnalysis, a peer-reviewed academic analysis, or an equivalent source that performs physical or electrical measurement and publishes enough methodology to identify what was measured and how**.

Enthusiast teardowns, vendor self-reports, and analyst estimates not based on primary measurement may be logged as context, but they do not resolve an item below.

## Six Trigger A scoring dimensions

| Item | Resolved when |
|---|---|
| **Die area and layer count** | A physical cross-section or equivalent die analysis reports measured dimensions and layer structure sufficient to test the claimed density. |
| **Bond and interconnect parasitics** | Electrical measurement of relevant test structures, or extracted resistance/capacitance values with a stated extraction method, is published. The values must be specific enough to bear on path-time behavior; a process-node label alone does not resolve this item. |
| **Sustained thermal behavior** | Thermal maps or equivalent temperature/throttling measurements are reported under a workload sustained for **at least 10 minutes**, with workload and measurement method stated. |
| **Fraction of logic folded** | Netlist reconstruction, layout analysis, or equivalent physical evidence estimates how much active logic is actually folded rather than merely stacked nearby. |
| **Yield consequences** | Bonded-stack yield or inter-wafer variation data are reported. Planar SMIC N+3 yield does not resolve this item. |
| **Cost consequences** | A bill-of-materials, cost-per-good-die, or equivalent cost estimate is published with enough method and assumptions to reproduce the estimate. |

The historical trigger log also tracks **package/die height** and the **gap-narrowing claim under sustained load**. Those remain useful supplementary observations. They are not silently substituted for the six dimensions above and do not change the count unless the evidence directly resolves one of these six dimensions.

## Pre-committed outcomes

| Outcome | Rule | Trigger / memo consequence |
|---|---|---|
| **Full resolution** | All six dimensions are resolved, and the evidence satisfies the memo's Trigger A requirement for folded active logic with measured sustained thermal and path-time behavior. | **Trigger A fires.** Reopen the memo. |
| **Substantial partial** | Three or more dimensions are resolved, including at least one of **bond/interconnect parasitics** or **sustained thermal behavior**, but the formal Trigger A condition is not fully satisfied. | Mark Trigger A **near-fire**. Memo remains no-action, but the reopen threshold is close. |
| **Marginal partial** | One or two dimensions are resolved, commonly die area/layer count alone. | Trigger A remains **partial movement**. No memo change. |
| **No resolution** | No dimension above is resolved by qualifying evidence. | Log the teardown and the remaining gaps. No scoring change. |

Opening a package, confirming a part number, confirming stacked layers, or estimating a process node can be meaningful evidence without being full resolution. Conversely, missing one class of measurement does not erase measurements the report actually made.

## Adversarial read when the report arrives

Ask these before writing the response:

- What did the authors **measure directly**, and what did they **infer**?
- Do measured die area and density reconcile with Huawei's claims, or contradict them?
- If the source is vendor-adjacent, what conflict-of-interest surface exists?
- Is the methodology sufficiently described for another competent analyst to reproduce or audit the result?
- What does the report **not** cover that a reader might assume it covers?

**Over-dismissal check:** *If this teardown is good, are we prepared to say so?*

The score is assigned against this file as committed before the evidence arrived. When a qualifying teardown appears, append a dated result section here and link that score from `TRIGGER_WATCH.md`; do not rewrite these pre-commitment rules to fit the result.
