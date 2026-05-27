"""
Regenerate fig_thermal_kernel.png with the title/annotation overlap fixed.

The bug in the v4 release: figure title 'Thermal evidence must be spatial,
temporal, and workload-specific' rendered at the same y-coordinate as the two
annotation labels ('Accept thermal evidence...' and 'Need testing...'), so all
three texts collided visually.

Fix: lay out the figure with explicit y-anchored positions and `tight_layout`
disabled, so the title sits cleanly above the annotation row.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrow
from matplotlib.lines import Line2D

fig, ax = plt.subplots(figsize=(7.4, 4.2), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.0)
ax.set_aspect("auto")
ax.axis("off")

# --- Title (top, well above annotation labels)
ax.text(5.0, 6.65, "Thermal evidence must be spatial, temporal, and workload-specific",
        ha="center", va="center", fontsize=12, fontweight="bold")

# --- Annotation labels (above the stack, well below title)
ax.text(2.05, 5.85, "Accept thermal evidence,\nnot a single lumped R″",
        ha="center", va="center", fontsize=9)
ax.text(7.95, 5.85, "Need testing,\nsensor arrays + workload pulses",
        ha="center", va="center", fontsize=9)

# --- Four horizontal tier bars
tiers = [
    ("Tier 2 active logic", 4.55, True),    # has sensor circles (P)
    ("Bond / BEOL interface", 3.40, False),
    ("Tier 1 active logic", 2.25, True),
    ("Package / heatspreader", 1.10, False),
]

for label, y, has_p in tiers:
    ax.add_patch(Rectangle((0.4, y - 0.42), 9.2, 0.84,
                           edgecolor="black", facecolor="white", linewidth=1.6))
    ax.text(5.0, y, label, ha="center", va="center", fontsize=10)
    if has_p:
        for cx in (2.4, 7.6):
            ax.add_patch(Circle((cx, y), 0.27,
                                edgecolor="black", facecolor="white", linewidth=1.4))
            ax.text(cx, y, "P", ha="center", va="center", fontsize=9, fontweight="bold")
    else:
        for cx in (2.0, 4.0, 6.0, 8.0):
            ax.plot(cx, y, marker="o", color="black", markersize=4)

# --- Arrows from left/right annotations down to the sensor circles
# Left arrow → Tier 1 active logic left sensor
ax.add_patch(FancyArrow(2.05, 5.62, 0.32, -3.05,
                        width=0.005, head_width=0.13, head_length=0.18,
                        length_includes_head=True, color="black"))
# Right arrow → Tier 2 active logic right sensor
ax.add_patch(FancyArrow(7.95, 5.62, -0.30, -0.78,
                        width=0.005, head_width=0.13, head_length=0.18,
                        length_includes_head=True, color="black"))

# --- Bottom caption: representative workloads
ax.text(5.0, 0.20,
        "Representative workloads: 10 min video encode, 10 min AI inference, "
        "20 min gaming loop, modem + camera stress",
        ha="center", va="center", fontsize=9)

plt.savefig("/tmp/memo_build/fig_thermal_kernel.png",
            dpi=300, bbox_inches="tight", pad_inches=0.1, facecolor="white")
print("wrote fig_thermal_kernel.png")
