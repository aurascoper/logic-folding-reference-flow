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

Compute the localised temperature delta ΔT_W(r, t) over a 2D spatial grid using
FFT-based convolution of a power-density field with a thermal kernel.
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

    # FFT-based circular convolution. For a non-periodic problem we zero-pad to
    # avoid wrap-around (see memo §8 — package boundaries are real, not periodic).
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

Default Gaussian kernel for illustrative use. Per memo §8.1 this is not a
calibrated kernel; a real K requires heater/sensor test-vehicle data.
"""
function generate_default_thermal_kernel(Ny::Integer, Nx::Integer; sigma::Real=2.0)
    cy, cx = Ny ÷ 2, Nx ÷ 2
    K = [exp(-((i - cy)^2 + (j - cx)^2) / (2 * sigma^2)) for i in 1:Ny, j in 1:Nx]
    K ./ sum(K)
end

"""
    generate_default_workload_pulse(Ny, Nx; hotspot_xy=(0.5, 0.5), intensity=1.0)

Default workload power-density snapshot. Replace with traces from a real
sustained workload before treating the output as evidence.
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

Container for APC simulation outputs. Fields are time-aligned vectors over the
simulation horizon.
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

Simulate the time-varying state-space EWMA run-to-run controller from memo Eq. 4
over K steps with a variable measurement delay d_k.
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
    z = [zeros(Float64, n) for _ in 0:K]
    y = zeros(Float64, K)
    u = zeros(Float64, K)
    setpoint_err = zeros(Float64, K)
    delays = zeros(Int, K)
    ewma_state = 0.0

    for k in 1:K
        d = max(0, d_k_schedule(k))
        delays[k] = d

        delayed_idx = max(1, k - d)
        z_delayed = z[delayed_idx]

        Ck = C(k)
        v = meas_noise_std * randn(rng)
        y[k] = (Ck * z_delayed)[1] + v

        err = setpoint - y[k]
        setpoint_err[k] = err
        ewma_state = ewma_lambda * err + (1 - ewma_lambda) * ewma_state
        u[k] = ewma_state

        Ak = A(k)
        Bk = B(k)
        w = process_noise_std * randn(rng, n)
        z[k + 1] = Ak * z[k] .+ Bk * [u[k]] .+ w
    end

    return APCResult(z, y, u, setpoint_err, delays)
end

"""
    is_diverging(result::APCResult; window::Integer=50, threshold::Real=10.0)

Detect loss of effective tracking using a variance-growth ratio:
`var(last window of setpoint_err) / var(first window) > threshold`.

Rationale: memo §9 frames sparse, delayed APC as an unsolved manufacturing
control blocker. A variance-growth gate is intentionally empirical and visible:
it measures the symptom a process engineer would first see when delayed
metrology causes the EWMA loop to amplify, rather than suppress, error. The
threshold is a screening policy, not a stability theorem.
"""
function is_diverging(result::APCResult; window::Integer=50, threshold::Real=10.0)
    n = length(result.setpoint_err)
    window > 1 || throw(ArgumentError("window must be greater than 1"))
    n >= 2 * window || throw(ArgumentError("need at least 2*window error samples"))
    threshold > 0 || throw(ArgumentError("threshold must be positive"))

    early = result.setpoint_err[1:window]
    late = result.setpoint_err[end-window+1:end]
    early_var = max(var(early; corrected=false), eps(Float64))
    late_var = var(late; corrected=false)
    return late_var / early_var > threshold
end

end # module ThermalAPCSolver
