# Trigger watch

A dated log of public LogicFolding / Tau-Scaling developments, each scored against the three reopen triggers from the [No-Action Decision Memo](./LogicFolding-No-Action-Decision-Memo.pdf) §6. The memo's verdict (`NO TRADE / NO ALLOCATION / NO ENGINEERING ADOPTION`) holds until one of these fires:

- **Trigger A — Shipping teardown.** A shipped product is torn down and shown to contain folded *active* logic, with measured sustained thermal and path-time behavior (not vendor burst claims).
- **Trigger B — Foundry / PDK disclosure.** A foundry or IDM publicly commits to dual-active-logic stacking with disclosed or escrowed data access (design rules, parasitics for the via/bond stack).
- **Trigger C — Open reference flow.** An open flow demonstrates reproducible 3D partitioning and proxy signoff on a public PDK (SkyWater 130 nm, GF180) against public benchmark RTL. *This repository is the seed of Trigger C; it does not yet satisfy it.*

Scoring is deliberately conservative. A development advances toward a trigger without firing it; only the firing condition flips the verdict.

---

## 2026-05-29 — status: all triggers OPEN

As of this entry, none of the three reopen triggers has fired. The memo's no-action decision stands. The week's developments are consistent with — and in two places corroborate — the memo's reasoning.

### Timeline

| Date | Event | Sources |
|------|-------|---------|
| 2026-05-25 | He Tingbo (HiSilicon / Huawei Scientist Committee) keynote at **ISCAS 2026**, Shanghai: introduces the **Tau (τ) Scaling Law** and **LogicFolding**; targets 1.4 nm-equivalent transistor density by 2031; 381 chips mass-produced over six years on the τ principle. Kirin 2026 (a.k.a. Kirin 9050) named as the first commercial LogicFolding part, shipping this fall in the Mate 90 series. | [Yicai Global](https://www.yicaiglobal.com/news/huawei-presents-tau-law-to-replace-geometric-scaling-with-time-scaling-in-semiconductor-industry), [CNBC](https://www.cnbc.com/2026/05/25/huawei-chip-logicfolding-semiconductor-nvidia-china.html), [NBC News](https://www.nbcnews.com/world/asia/chinas-huawei-touts-chip-design-breakthrough-bid-defy-us-sanctions-rcna346783) |
| 2026-05-25 | Quantitative claims attached to Kirin 2026: **+53.5% transistor density → ~238 MTr/mm²**, **+41% high-performance-core efficiency**, **+12.7% peak clock → ~3.1 GHz**, single-layer → double-layer logic. All vendor figures; no independent measurement. | [Wccftech](https://wccftech.com/huawei-adopts-logicfolding-design-for-kirin-chipsets-bringing-various-advantages/), [Gizmochina](https://www.gizmochina.com/2026/05/25/huawei-previews-kirin-2026-chip-with-higher-transistor-density-and-efficiency/) |
| 2026-05-27 | **Peking University** unveils a prototype **"true-3D" EDA tool** tailored to LogicFolding: treats a multi-layer stack as a single structure from the design stage and optimizes the whole vertical stack at once, rather than designing planar circuits and stacking afterward. | [SCMP](https://www.scmp.com/tech/tech-war/article/3355066/peking-university-unveils-3d-design-tool-power-huaweis-chip-ambitions), [DigiTimes](https://www.digitimes.com/news/a20260528VL217/huawei-eda-design-roadmap-packaging.html), [TrendForce](https://www.trendforce.com/news/2026/05/28/news-peking-univ-unveils-eda-for-huawei-logicfolding-kirin-2026-reportedly-eyes-3nm-class-performance/) |
| 2026-05-27–29 | Independent technical commentary converges on a hybrid-bonding reading: the technique is selective vertical stacking of digital/analog/memory layers, with cooling of stacked active logic unaddressed and folding applied only to critical signal paths. | [Reuters via Investing.com](https://www.investing.com/news/stock-market-news/analysishuawei-bets-on-speed-over-shrinking-transistors-to-sidestep-us-chip-sanctions-4715892), [Vik's Newsletter](https://www.viksnewsletter.com/p/huaweis-tau-scaling-is-really-hybrid-bonding-bet), [Notebookcheck](https://www.notebookcheck.net/Huawei-announces-1-4-nm-chipmaking-technology-to-compete-with-TSMC.1305174.0.html) |

### Scoring

**Trigger A — Shipping teardown: NOT FIRED.**
Kirin 2026 / Mate 90 are announced for fall 2026; nothing has shipped, so no teardown and no independent density or sustained-thermal confirmation exists. The 238 MTr/mm² / +41% / +12.7% figures are exactly the vendor-claim category the memo §8 discounts ("burst scores are not investment evidence"). A remains open.

**Trigger B — Foundry / PDK disclosure: NOT FIRED.**
No SMIC or Hua Hong PDK, design-rule set, or via/bond parasitic data has been released for the dual-active-logic stack. Everything remains at the vendor-keynote level. B remains open.

**Trigger C — Open reference flow: NOT FIRED (closest movement to date).**
Peking University's 3D EDA tool is the first real-world artifact in the same category as this repository — a 3D-native design flow. But as reported it is a prototype/academic tool: no confirmation it is open-source, runnable on a public PDK (Sky130 / GF180), or reproducible against public benchmark RTL. It advances the state of the art toward Trigger C without meeting the memo's bar. C remains open; this is the development to monitor most closely.

### Corroboration of the memo's reasoning (does not change the verdict)

Two items strengthen, rather than challenge, the existing thesis:

1. **Selective / critical-path-only folding** (Reuters, Heisener: "folding only critical signal paths," "initial efficiency gain is not a full doubling"). This is precisely the stratification memo §7 anticipates: when only long global paths clear the break-even gate, the technique sits in the floorplanning category rather than the standard-cell-level scaling-law category. Huawei's own framing lands on the floorplanning side. `core_solver.py` already reports per-path margins so a reviewer can verify this stratification on their own netlist.

2. **Unaddressed sustained cooling** (Notebookcheck: stacking active logic "will produce a lot more heat"). This is the open question memo §8 / Eq. 3 exists to interrogate; `thermal_apc_solver.jl` defaults workloads to ≥10-minute sustained pulses for exactly this reason.

### Net

No code or equation change is warranted by this news cycle: the physics and the verdict are unchanged. This entry records that the memo's monitoring is current as of 2026-05-29 and that the pre-registered triggers held under a full week of public claims.

---

## 2026-05-30 — status: all triggers OPEN (EDA-displacement update)

Prompted by the WSJ piece ["Huawei Says It Has Workaround to Match Leading Chips"](https://www.wsj.com/tech/huawei-says-it-has-workaround-to-match-leading-chips-c6075fd1) and the analyst commentary around it. No trigger fired; the 2026-05-29 verdict stands. This entry records one net-new thread (EDA-tool displacement) and a vendor self-admission that corroborates the memo.

### Timeline

| Date | Event | Sources |
|------|-------|---------|
| 2026-05-26 | On a Tau Scaling panel, **Handel H. Jones** (CEO, International Business Strategies) argues that optimizing at the system level on time "will dramatically change the capability requirements for the EDA vendors" — the tools made by **Cadence** and **Synopsys** that draw these blueprints. Frames LogicFolding as an EDA-displacement story and, for a sanctioned Huawei, a forced build-your-own-EDA dependency. | [Technology.org](https://www.technology.org/2026/05/29/huawei-tau-scaling-logicfolding-chips/), [Reuters](https://www.reuters.com/world/asia-pacific/huawei-proposes-new-path-chip-development-amid-us-sanctions-2026-05-25/) |
| 2026-05-25 | He Tingbo **acknowledges the two hurdles directly**: the need for new Tau-suited design tools, and preventing overheating "from mobile chips to large AI data centers." Vendor concession on exactly the memo's §7 (tooling / floorplanning) and §8 (thermal). | [Reuters](https://www.reuters.com/world/asia-pacific/huawei-proposes-new-path-chip-development-amid-us-sanctions-2026-05-25/) |
| 2026-05-26 | Futurum (Brendan Burke): density gain ≈ "three years of traditional scaling" at a fixed node, but toolchain / ecosystem "remain immature" and **inter-wafer process variation** is an open risk; TSMC / Intel hybrid-bonding roadmaps are "closing ground." | [Futurum](https://futurumgroup.com/insights/does-huaweis-tau-scaling-law-challenge-the-logic-leadership-of-intel-and-tsmc/) |
| 2026-05-27 | Vik's Newsletter pins the baseline: **155 → 238 MTr/mm²** for the +53.5%, and makes the node-agnostic point — folding is available to anyone, so applied on a leading-edge node by an EUV holder it widens the lead rather than closing it. | [Vik's Newsletter](https://www.viksnewsletter.com/p/huaweis-tau-scaling-is-really-hybrid-bonding-bet) |

### Scoring

**Trigger A — Shipping teardown: NOT FIRED.**
Still nothing shipped. Adds one item to the eventual teardown checklist: yield / inter-wafer process variation across the bonded stack, alongside sustained-thermal and fraction-of-logic-folded.

**Trigger B — Foundry / PDK disclosure: NOT FIRED.**
The WSJ "workaround" framing is strategy, not silicon: no foundry, node, PDK, or yield figure disclosed. B untouched.

**Trigger C — Open reference flow: NOT FIRED (still the closest movement).**
The EDA-displacement thread gives the Peking University 3D-EDA tool concrete commercial stakes — the gap Cadence / Synopsys will not fill for a sanctioned customer. But it remains a prototype on no public PDK. C moves marginally closer without meeting the bar.

### Corroboration of the memo's reasoning (does not change the verdict)

He Tingbo's own admission of the tooling and thermal hurdles restates memo §7 and §8 from the vendor side. The node-agnostic critique (Vik's Newsletter, Futurum) reinforces §7's floorplanning reading: a technique any EUV holder can also apply is co-design leverage, available to the leaders too, rather than a unilateral density law.

### Net

No code or equation change. The new content is strategic (EDA toolchain) rather than physical, and the one physical addition (inter-wafer variation) is a teardown variable to check in the fall, not a fired trigger. Monitoring current as of 2026-05-30.

---

## 2026-07-03 — status: all triggers OPEN (Tau Scaling Law V2 paper)

Huawei published a **Version 2 paper** of the Tau Scaling Law, substantially expanding the May 2026 ISCAS announcement. He Tingbo disclosed measured Kirin 2026 chip data and positioned LogicFolding as one of five "landing technologies." No trigger fired; the no-action decision stands. Self-reported data is not independent verification.

### Timeline

| Date | Event | Sources |
|------|-------|---------|
| 2026-07-03 | He Tingbo publishes **Tau Scaling Law V2 paper**: discloses measured power consumption, voltage, frequency, area, and power density for the Kirin 2026 chip. Enumerates five "landing technologies": **LogicFolding, hybrid bonding, TSV, Unified Bus, Hi-ONE optical engine**. Introduces a **"gear ratio"** concept for LogicFolding (folding ratio governing vertical-to-horizontal delay tradeoff). Outlines a **2030 roadmap** for LogicFolding to reach Ascend AI chips. | Huawei V2 paper (He Tingbo, July 3, 2026) |
| 2026-07-03 | **Kirin 9050 Pro** naming: the upcoming chip may be named Kirin 9050 Pro and is reportedly in packaging and testing. Fall 2026 Mate 90 launch window maintained. | Industry reports |
| 2026-06-15 | **IBM** announces sub-1nm "nanostack" transistor architecture at **VLSI 2026** — a separate 3D integration advance in the broader field, not LogicFolding-specific. | IBM VLSI 2026 |
| 2026-06-18 | **Samsung** demonstrates 42nm gate-pitch 3D stacked FET at **VLSI 2026** — another 3D integration datapoint in the broader field. | Samsung VLSI 2026 |

### New claims from the V2 paper

The V2 paper provides more detail than the May 2026 ISCAS keynote but remains **vendor self-reported data**, not independently verified:

1. **Kirin 2026 measured data:** power consumption, voltage, frequency, area, and power density. These are Huawei's own measurements on their own chip — not a third-party teardown.
2. **Five landing technologies:** LogicFolding is positioned alongside hybrid bonding, TSV, Unified Bus, and Hi-ONE optical engine as one of five "landing technologies" for the Tau Scaling paradigm. This frames LogicFolding as part of a broader packaging/integration suite rather than a standalone scaling law.
3. **Gear ratio concept:** The V2 paper introduces a "gear ratio" for LogicFolding — a parameter governing the vertical-to-horizontal delay tradeoff. This is conceptually related to the memo's Eq. 2 break-even ratio (Δτ_save vs. vertical tax), though Huawei's formulation and the memo's are not directly comparable without seeing the paper's exact equations.
4. **2030 Ascend AI roadmap:** Huawei outlines a path for LogicFolding to reach Ascend AI chips by 2030 — a 4-year roadmap, not a current product.
5. **Kirin 9050 Pro:** reportedly in packaging and testing; fall 2026 launch window maintained.

### Scoring

**Trigger A — Shipping teardown: PARTIAL MOVEMENT, NOT FIRED.**
Kirin 2026 power/voltage/area/frequency data is Huawei's own measured data from their own chip. This is more detail than the May keynote, but it is self-reported, not an independent teardown. No third party has measured sustained thermal behavior, path delay, or die/package cost. The fall 2026 launch is still months away. A remains open; movement is incremental.

**Trigger B — Foundry / PDK disclosure: NOT FIRED.**
No SMIC or Hua Hong PDK, design-rule set, via/bond parasitic data, or yield figure has been released for the dual-active-logic stack. The V2 paper does not name a foundry partner with auditable data rights. B remains open and unchanged.

**Trigger C — Open reference flow: NOT FIRED.**
This repository remains the only open reference flow. The Peking University 3D EDA tool (logged 2026-05-29) is still a prototype on no public PDK. The V2 paper does not disclose an open-source flow. C remains open; this repository is the seed, not the satisfaction.

### Broader 3D integration context (does not change the verdict)

IBM's sub-1nm nanostack transistor (VLSI 2026) and Samsung's 42nm gate-pitch 3D stacked FET (VLSI 2026) are significant advances in the broader 3D integration field. They are not LogicFolding-specific and do not constitute independent verification of Huawei's claims. They do reinforce the memo's broader point: 3D integration is an active field with multiple approaches, and LogicFolding is one variant whose specific claims require their own evidence.

### What the "gear ratio" concept means for this repository

The V2 paper's "gear ratio" concept is the first public framing from Huawei that maps onto the memo's Eq. 2 structure — a ratio governing when vertical folding pays off versus when it doesn't. If the paper's equations are made public in sufficient detail, they could be cross-referenced against `core_solver.py:VerticalPathEvaluator.evaluate` (the full Eq. 2) and `rust/src/lib.rs:PathEvaluator::evaluate` (the abbreviated form). Until the exact formulation is available, the memo's Eq. 2 remains the reference.

### Claimed data fixture

Kirin 2026 claimed power density, voltage, and frequency numbers have been added as a **claimed fixture** in `python/tests/fixtures/kirin_2026_claimed.json` — clearly marked as unverified vendor data. A "what-if" analysis script (`python/scripts/kirin_2026_whatif.py`) evaluates the break-even inequality against these claimed numbers in a conditional mode: *if these claimed numbers are accurate, here is what the break-even inequality would show.* This does not treat Huawei's numbers as validated truth.

### Net

No equation or verdict change is warranted. The V2 paper provides more detail but not independent verification. The memo's no-action decision stands: self-reported data does not clear the independent-evidence bar. Thermal and yield data remain not yet public. The fall 2026 Kirin 9050 Pro / Mate 90 launch remains the earliest opportunity for Trigger A to fire.

Monitoring current as of 2026-07-03.
