#!/usr/bin/env julia
"""
run_apc_divergence_demo.jl

Reproduces the §9 finding from the LogicFolding No-Action Decision Memo:
*"Spatial APC for folded 3D logic under sparse delayed metrology is not
merely a missing parameter; it is an unsolved control problem under
manufacturing constraints."*

The demo sweeps the metrology delay `d_k` and plots the resulting setpoint
error envelope. With small `d_k` the EWMA controller tracks; as `d_k` rises,
the closed loop divergence dominates and wafer uniformity collapses.

Run with:

    julia --project=julia julia/scripts/run_apc_divergence_demo.jl

Outputs `julia/figures/apc_divergence_sweep.png`.
"""

include(joinpath(@__DIR__, "..", "src", "thermal_apc_solver.jl"))
using .ThermalAPCSolver
using Plots
using Statistics
using Random

# Fix RNG for reproducibility.
rng = MersenneTwister(42)

# Delays to sweep, in run-step units. Memo §9: real fabs have sparse,
# delayed metrology — d_k of 5 to 20 lots is realistic for overlay/CD;
# d_k of 1 is fast inline.
delay_schedules = [
    ("d_k = 1 (inline)",       k -> 1),
    ("d_k = 5 (one-lot-ago)",  k -> 5),
    ("d_k = 15 (sparse)",      k -> 15),
    ("d_k = 25 (very sparse)", k -> 25),
    ("d_k variable 5..25",     k -> 5 + (k % 21)),
]

K_steps = 400
results = []

for (label, sched) in delay_schedules
    res = run_apc_simulation(
        K = K_steps,
        ewma_lambda = 0.3,
        d_k_schedule = sched,
        process_noise_std = 0.01,
        meas_noise_std = 0.05,
        rng = MersenneTwister(42),  # same seed → same noise across runs
    )
    push!(results, (label, res))
end

# ---- Plot setpoint-error envelopes -----------------------------------------
plt = plot(
    title = "EWMA APC: setpoint error vs metrology delay d_k\n" *
            "(LogicFolding memo §9 — divergence under sparse delayed metrology)",
    xlabel = "Run step k",
    ylabel = "Setpoint error  y_k - r",
    legend = :outertopright,
    size = (1100, 600),
    framestyle = :box,
)

for (label, res) in results
    plot!(plt, 1:length(res.setpoint_err), res.setpoint_err,
          label = label, linewidth = 1.5, alpha = 0.85)
end

hline!(plt, [0.0], color = :black, linestyle = :dash, label = "")

# Make sure the figures directory exists.
figdir = joinpath(@__DIR__, "..", "figures")
isdir(figdir) || mkdir(figdir)
fig_out = joinpath(figdir, "apc_divergence_sweep.png")
savefig(plt, fig_out)
println("Wrote: ", fig_out)

# ---- Summary statistics: variance growth as d_k increases ------------------
println("\nSetpoint error variance by delay schedule:")
println("-"^60)
for (label, res) in results
    σ² = var(res.setpoint_err)
    range_y = maximum(abs, res.setpoint_err)
    println(rpad(label, 28), "  var = ", round(σ², digits=5),
            "    max|err| = ", round(range_y, digits=3))
end
println("-"^60)
println("Per memo §9: as d_k grows, variance grows and the loop loses its ")
println("ability to track. This is the unsolved control problem the memo cites.")
