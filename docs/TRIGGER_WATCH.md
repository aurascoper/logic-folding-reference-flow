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
