"""
thermal_apc_solver.jl

Spatial-temporal thermal kernel and EWMA run-to-run APC simulator for the
LogicFolding open reference flow (per memo §8 Eq. 3 and §9 Eq. 4).

The two halves of this file mirror the two memo sections they implement:

  §8 (thermal):    ΔT_W(r, t) = ∫₀ᵗ ∫_Ω K(r, r', t-s) p_W(r', s) dr' ds
  §9 (APC):        z_{k+1} = A_k z_k + B_k u_k + w_k
                   y_k     = C_k z_{k - d_k} + v_k     (variable delay d_k!)

This is a *reference flow* per memo §11, not a portability claim. The §9 code
demonstrates exactly the instability the memo identifies — controller
divergence under variable metrology delay — which is also why the memo
classifies APC under "Red, unsolved research blocker" (§9, Appendix C).
"""

module ThermalAPCSolver

using FFTW
using LinearAlgebra
using Random
using Statistics

export calculate_thermal_profile,
       run_apc_simulation,
       APCResult,
       generate_default_workload_pulse,
       generate_default_thermal_kernel,
       is_diverging

# =============================================================================
# §8 — Spatial thermal convolution
# =============================================================================

"""
    calculate_thermal_profile(P_matrix, K_kernel)

Compute the localised temperature delta ΔT_W(r, t) over a 2D spatial grid
using FFT-based convolution of a power-density field with a thermal kernel.

This is the spatial portion of memo Eq. 3. We separate the spatial
convolution (handled here) from the temporal integral (handled by stepping
this function over a sequence of `P_matrix` snapshots in time and accumulating
the result). FFT convolution is `O(N log N)` per snapshot, which is the only
way to make this remotely tractable at full-die resolution.

# Arguments
- `P_matrix::AbstractMatrix{<:Real}`: 2D power-density field p_W(r, t) for a
  single time snapshot, in W/m². Units are convention only — the kernel must
  match.
- `K_kernel::AbstractMatrix{<:Real}`: Thermal kernel K(r, r', t-s) for a
  fixed (t-s). Must have the same dimensions as `P_matrix`. The kernel
  embodies all stack, package, and cooling geometry per memo §8.

# Returns
- `Matrix{Float64}` of the same shape as the inputs: spatial temperature
  delta in arbitrary units (matches kernel calibration).

# Memo note
Per §8: "a single lumped area-normalized resistance cannot validate
active-on-active logic." This function is the spatial machinery that lets a
caller move past lumped-R" toward a calibrated K. It does **not** itself
constitute calibration — see §8.1 calibration requirements.
"""
function calculate_thermal_profile(
    P_matrix::AbstractMatrix{<:Real},
    K_kernel::AbstractMatrix{<:Real},
)
    size(P_matrix) == size(K_kernel) ||
        throw(DimensionMismatch(
            "P_matrix and K_kernel must share shape; got " *
            "$(size(P_matrix)) vs $(size(K_kernel))."
        ))

    # FFT-based circular convolution. For a non-periodic problem we zero-pad
    # to avoid wrap-around (see memo §8 — package boundaries are real, not
    # periodic). The pad must be at least the kernel half-width.
    pad_y, pad_x = size(K_kernel) .÷ 2
    Ny, Nx = size(P_matrix)
    pad_Ny = Ny + 2 * pad_y
    pad_Nx = Nx + 2 * pad_x

    P_pad = zeros(Float64, pad_Ny, pad_Nx)
    K_pad = zeros(Float64, pad_Ny, pad_Nx)
    P_pad[pad_y+1:pad_y+Ny, pad_x+1:pad_x+Nx] .= P_matrix
    K_pad[1:size(K_kernel, 1), 1:size(K_kernel, 2)] .= K_kernel

    # Centre the kernel so the convolution aligns to the source pixel.
    K_pad = circshift(K_pad, (-pad_y, -pad_x))

    conv = real.(ifft(fft(P_pad) .* fft(K_pad)))
    return conv[pad_y+1:pad_y+Ny, pad_x+1:pad_x+Nx]
end

"""
    generate_default_thermal_kernel(Ny, Nx; sigma=2.0)

Default Gaussian kernel for illustrative use. Spatially-symmetric, decays
like a heat-diffusion Green's function over the supplied grid.

Per memo §8.1: this is **not** a calibrated kernel — it is a smoke-test
default. A real `K` requires heater/sensor test-vehicle data.
"""
function generate_default_thermal_kernel(Ny::Integer, Nx::Integer; sigma::Real=2.0)
    cy, cx = Ny ÷ 2, Nx ÷ 2
    K = [exp(-((i - cy)^2 + (j - cx)^2) / (2 * sigma^2)) for i in 1:Ny, j in 1:Nx]
    K ./ sum(K)  # normalise so total kernel mass is 1
end

"""
    generate_default_workload_pulse(Ny, Nx; hotspot_xy=(0.5, 0.5), intensity=1.0)

Default workload power-density snapshot. Single Gaussian hotspot for
illustration. Replace with traces from a real workload (memo §8.1: 10-minute
video encode, 10-minute AI inference, 20-minute gaming loop, modem/camera
stress) to do anything that resembles a calibrated thermal evaluation.
"""
function generate_default_workload_pulse(
    Ny::Integer,
    Nx::Integer;
    hotspot_xy::Tuple{<:Real, <:Real}=(0.5, 0.5),
    intensity::Real=1.0,
    spread::Real=3.0,
)
    cy = round(Int, hotspot_xy[1] * Ny)
    cx = round(Int, hotspot_xy[2] * Nx)
    [intensity * exp(-((i - cy)^2 + (j - cx)^2) / (2 * spread^2))
     for i in 1:Ny, j in 1:Nx]
end


# =============================================================================
# §9 — APC state-space simulation with variable measurement delay
# =============================================================================

"""
    APCResult

Container for APC simulation outputs. Fields are time-aligned vectors over
the simulation horizon (length K+1 for `z`, length K for the rest).

- `z`: state trajectory `Vector{Vector{Float64}}` (each element is the n×1
  state at step k).
- `y`: observed output trajectory (`Vector{Float64}`) — scalar measurements.
- `u`: control trajectory (`Vector{Float64}`) — EWMA-derived.
- `setpoint_err`: signed deviation of `y` from setpoint each step.
- `delays`: actual `d_k` realised each step (so plots can show the delay
  variability that drives instability).
"""
struct APCResult
    z::Vector{Vector{Float64}}
    y::Vector{Float64}
    u::Vector{Float64}
    setpoint_err::Vector{Float64}
    delays::Vector{Int}
end

"""
    run_apc_simulation(; ...)

Simulate the time-varying state-space EWMA run-to-run controller from memo
Eq. 4 over K steps with a variable measurement delay `d_k`.

# Keyword arguments
- `K::Integer = 200`: number of simulation steps.
- `n::Integer = 2`: state dimension.
- `A`, `B`, `C`: time-varying matrices given as functions of `k`, each
  returning the appropriately-sized matrix. Defaults match a slowly-drifting
  process with mild excitation.
- `setpoint::Real = 0.0`: control target on `y`.
- `ewma_lambda::Real = 0.3`: EWMA smoothing on the control error.
- `d_k_schedule::Function = k -> 1`: returns the measurement delay used at
  step k. **This is the operator-controllable knob the memo flags as
  unsolved**; increasing it should destabilise the loop.
- `process_noise_std::Real = 0.01`, `meas_noise_std::Real = 0.05`: white
  Gaussian noise standard deviations.
- `rng::AbstractRNG = Random.default_rng()`: random source.

# Returns
- `APCResult` (see docstring).
"""
function run_apc_simulation(;
    K::Integer = 200,
    n::Integer = 2,
    A = k -> [0.98 0.05; 0.0 0.95],
    B = k -> reshape([0.10, 0.20], n, 1),
    C = k -> reshape([1.0, 0.0], 1, n),
    setpoint::Real = 0.0,
    ewma_lambda::Real = 0.3,
    d_k_schedule::Function = k -> 1,
    process_noise_std::Real = 0.01,
    meas_noise_std::Real = 0.05,
    rng::AbstractRNG = Random.default_rng(),
)
    z = [zeros(Float64, n) for _ in 0:K]   # z[1] = z_0
    y = zeros(Float64, K)
    u = zeros(Float64, K)
    setpoint_err = zeros(Float64, K)
    delays = zeros(Int, K)

    # Buffer of past measurements, so y_k can be drawn from z_{k - d_k}.
    # Index: k-th *element* of `z` is z_{k-1}, so z[(k - d) + 1] = z_{k-d}.
    ewma_state = 0.0  # smoothed control error

    for k in 1:K
        # 1. Determine the delay for this step.
        d = max(0, d_k_schedule(k))
        delays[k] = d

        # 2. Pull the delayed state for measurement.
        delayed_idx = max(1, k - d)   # k - d corresponds to z[(k-d)+1] = z[k-d+1]
        z_delayed = z[delayed_idx]

        # 3. Observe: y_k = C_k * z_{k - d_k} + v_k
        Ck = C(k)
        v = meas_noise_std * randn(rng)
        y[k] = (Ck * z_delayed)[1] + v

        # 4. EWMA update on the *delayed* setpoint error.
        err = setpoint - y[k]
        setpoint_err[k] = err
        ewma_state = ewma_lambda * err + (1 - ewma_lambda) * ewma_state
        u[k] = ewma_state

        # 5. Advance state: z_{k+1} = A_k z_k + B_k u_k + w_k
        Ak = A(k)
        Bk = B(k)
        w = process_noise_std * randn(rng, n)
        z[k + 1] = Ak * z[k] .+ Bk * [u[k]] .+ w
    end

    return APCResult(z, y, u, setpoint_err, delays)
end


# =============================================================================
# TODO — operator contribution
#
# `is_diverging(result; window)` is a *policy* decision, not a physics one.
# The memo (§9) says spatial APC under sparse delayed metrology is unsolved;
# it does not prescribe a single metric for "diverged." Implement this
# function (5–10 lines) using whichever criterion you find most defensible:
#
#   1. Variance-growth ratio: var(setpoint_err[end-window+1:end])
#                              / var(setpoint_err[1:window]) > threshold.
#      Cheap; tracks the most direct symptom of loss of control.
#
#   2. Spectral radius of the *effective* closed-loop matrix, accounting for
#      the average delay over `window`. More principled — links back to
#      Bing Ai et al. (arXiv:1510.08946, memo ref [7]). Harder to implement.
#
#   3. Sliding-window |setpoint_err| / process_noise_std ratio crossing a
#      multiple (e.g., 10×). Empirical; matches how a real fab engineer
#      would notice trouble.
#
# Whichever you pick, comment the rationale and cite the memo section that
# justifies the threshold values you chose.
#
# A starter signature is provided below — replace the body.
# =============================================================================

"""
    is_diverging(result::APCResult; window::Integer=50, threshold::Real=10.0)

Operator-defined divergence detector for an APC simulation. Returns `true` if
the controller has lost effective tracking under whatever criterion you
choose to implement.

TODO: implement. See the block comment above this function for the design
considerations the memo raises.
"""
function is_diverging(result::APCResult; window::Integer=50, threshold::Real=10.0)
    error("Implement is_diverging. See module-level TODO block above this function.")
end

end # module ThermalAPCSolver
