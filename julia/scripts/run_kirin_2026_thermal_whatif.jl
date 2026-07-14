#!/usr/bin/env julia
"""
run_kirin_2026_thermal_whatif.jl

WHAT-IF thermal analysis against Huawei's claimed Kirin 2026 power data.

**WARNING: Claimed by Huawei, not independently verified.** The V2 paper
(He Tingbo, July 3, 2026) discloses power density for the Kirin 2026 chip.
This script runs the §8 FFT thermal kernel (Eq. 3) in conditional mode:

    "IF these claimed power-density numbers are accurate, here is what
     the spatial thermal response would look like under sustained workloads."

This does NOT treat Huawei's numbers as validated truth. Per the memo's
no-action decision, self-reported data does not clear the independent-evidence
bar (Trigger A: shipping teardown — not fired).

The script sweeps power densities from a conservative estimate to the claimed
value, under sustained (≥10 minute) workload pulses — the memo §8 condition
that distinguishes burst benchmarks from consumer-product viability.

Run with:
    julia --project=julia julia/scripts/run_kirin_2026_thermal_whatif.jl

Outputs summary statistics and a figure to julia/figures/.
"""

include(joinpath(@__DIR__, "..", "src", "thermal_apc_solver.jl"))
using .ThermalAPCSolver
using Statistics
using Printf

# ---- Claimed data (NOT VERIFIED) -------------------------------------------
#
# The V2 paper discloses power density for Kirin 2026. The exact numeric value
# is pending full-text extraction from the paper; we bracket it with a sweep
# from conservative mobile-class power density to the claimed range.
#
# Reference: modern flagship mobile SoCs have power densities of ~10-30 W/cm²
# at sustained workloads. Huawei claims Kirin 2026 improves efficiency by 41%,
# but the absolute power density figure needs the full paper text.
# We use 10-50 W/cm² as the sweep range, which brackets plausible mobile
# power densities and the claimed improvement.

const W_CM2_TO_W_M2 = 1e4   # W/cm² → W/m²

power_densities_w_cm2 = [10.0, 20.0, 30.0, 40.0, 50.0]

# Grid size for the thermal simulation
const Ny, Nx = 64, 64

# Sustained workload pulse (memo §8: ≥10 minutes)
# In the FFT thermal kernel, this is a single snapshot of the power-density
# field. A real sustained analysis would time-integrate over the workload
# duration; here we show the steady-state spatial response.

println("=" ^ 72)
println("WHAT-IF THERMAL ANALYSIS: Kirin 2026 claimed power density (NOT VERIFIED)")
println("=" ^ 72)
println()
println("Source: Huawei Tau Scaling Law V2 paper, He Tingbo, 2026-07-03")
println("Status: self-reported — NOT independently verified")
println()
println("WARNING: All numbers are vendor self-reported. This is a")
println("conditional analysis: 'IF claimed numbers are accurate, what")
println("would the thermal response show?'")
println()
println(@sprintf("Grid: %dx%d spatial cells", Ny, Nx))
println(@sprintf("Kernel: default Gaussian (sigma=2.0) — NOT a calibrated kernel"))
println("  (memo §8: a real K requires heater/sensor test-vehicle data)")
println()
println(@sprintf("%-20s %-15s %-15s %-15s", "Power density", "Mean ΔT (°C)", "Max ΔT (°C)", "Hotspot area %"))
println("-" ^ 72)

# Try to use Plots if available; skip gracefully if not
fig_available = true
try
    using Plots
catch
    global fig_available = false
    println("\nNOTE: Plots.jl not available — skipping figure output.")
end

results = []

for pd_w_cm2 in power_densities_w_cm2
    # Generate workload pulse at this power density
    # The hotspot is centered; the intensity is the claimed power density
    intensity_w_m2 = pd_w_cm2 * W_CM2_TO_W_M2
    P = generate_default_workload_pulse(Ny, Nx;
        hotspot_xy=(0.5, 0.5),
        intensity=intensity_w_m2,
        spread=3.0,
    )

    # Default thermal kernel (uncalibrated — memo §8 caveat)
    K = generate_default_thermal_kernel(Ny, Nx; sigma=2.0)

    # Run the FFT thermal convolution (Eq. 3)
    ΔT = calculate_thermal_profile(P, K)

    mean_ΔT = mean(ΔT)
    max_ΔT = maximum(ΔT)
    # Hotspot area: fraction of grid where ΔT > 50% of max
    hotspot_frac = count(x -> x > 0.5 * max_ΔT, ΔT) / length(ΔT) * 100

    println(@sprintf("%-20s %-15.2f %-15.2f %-15.1f",
        @sprintf("%.1f W/cm²", pd_w_cm2),
        mean_ΔT, max_ΔT, hotspot_frac))

    push!(results, (pd_w_cm2, mean_ΔT, max_ΔT, hotspot_frac, ΔT))
end

println("-" ^ 72)
println()

# ---- Interpretation ---------------------------------------------------------

println("=" ^ 72)
println("INTERPRETATION")
println("=" ^ 72)
println()
println("This is a WHAT-IF analysis, not evidence. Key observations:")
println()
println("1. The thermal response scales linearly with power density (the")
println("   kernel is linear). Higher claimed power density → higher ΔT.")
println()
println("2. The kernel used here is NOT calibrated (memo §8). A real thermal")
println("   gate requires a calibrated K from heater/sensor test-vehicle data")
println("   for the specific stack, package, and cooling envelope. The default")
println("   Gaussian kernel only shows the spatial spreading behavior.")
println()
println("3. Memo §8 requires sustained (≥10 min) workload analysis, not burst")
println("   benchmarks. Huawei has not disclosed sustained thermal data — only")
println("   vendor burst measurements. The fall 2026 teardown is the earliest")
println("   opportunity for independent sustained thermal evidence.")
println()
println("4. The actual thermal viability depends on the package cooling solution,")
println("   TIM, heat spreader, and skin-temperature limits — none of which are")
println("   disclosed in the V2 paper.")
println()
println("CONCLUSION: Even if Huawei's claimed power density is taken at face")
println("value, the thermal gate (memo §8, Eq. 3) still requires a calibrated")
println("kernel and sustained workload data to evaluate. The memo's no-action")
println("decision stands.")

# ---- Figure (if Plots available) -------------------------------------------

if fig_available
    plt = plot(
        title = "What-if thermal response: Kirin 2026 claimed power density\\n(NOT VERIFIED — vendor self-reported)",
        xlabel = "Power density (W/cm²)",
        ylabel = "Temperature rise ΔT (°C)",
        legend = :topleft,
        size = (900, 500),
        framestyle = :box,
    )

    pds = [r[1] for r in results]
    means = [r[2] for r in results]
    maxs = [r[3] for r in results]

    plot!(plt, pds, means, label="Mean ΔT", linewidth=2, color=:blue)
    plot!(plt, pds, maxs, label="Max ΔT", linewidth=2, color=:red)

    figdir = joinpath(@__DIR__, "..", "figures")
    isdir(figdir) || mkdir(figdir)
    fig_out = joinpath(figdir, "kirin_2026_thermal_whatif.png")
    savefig(plt, fig_out)
    println("\nWrote: ", fig_out)
end