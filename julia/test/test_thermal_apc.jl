"""
test_thermal_apc.jl

Smoke tests for the thermal/APC solver. Run with:

    julia --project=julia julia/test/test_thermal_apc.jl
"""

include(joinpath(@__DIR__, "..", "src", "thermal_apc_solver.jl"))
using .ThermalAPCSolver
using Test
using Statistics
using Random

@testset "Thermal convolution" begin
    P = generate_default_workload_pulse(16, 16)
    K = generate_default_thermal_kernel(16, 16; sigma=2.0)
    T = calculate_thermal_profile(P, K)
    @test size(T) == size(P)
    @test all(isfinite, T)
    @test maximum(T) > 0  # there is a hotspot, ergo positive temperature delta
end

@testset "Thermal convolution rejects shape mismatch" begin
    P = generate_default_workload_pulse(16, 16)
    K = generate_default_thermal_kernel(32, 32)
    @test_throws DimensionMismatch calculate_thermal_profile(P, K)
end

@testset "APC simulation produces correctly-shaped traces" begin
    res = run_apc_simulation(K=50, d_k_schedule = k -> 2, rng=MersenneTwister(1))
    @test length(res.y) == 50
    @test length(res.z) == 51   # K+1
    @test length(res.u) == 50
    @test length(res.setpoint_err) == 50
    @test length(res.delays) == 50
    @test all(d -> d == 2, res.delays)
end

@testset "Sparse delayed metrology destabilises the loop (memo §9)" begin
    seed = 2026
    res_inline = run_apc_simulation(
        K=400, d_k_schedule = k -> 1, rng=MersenneTwister(seed))
    res_sparse = run_apc_simulation(
        K=400, d_k_schedule = k -> 25, rng=MersenneTwister(seed))
    tail = 100
    v_inline = var(res_inline.setpoint_err[end-tail+1:end])
    v_sparse = var(res_sparse.setpoint_err[end-tail+1:end])
    # The whole point of the memo §9 demo: variance must grow substantially
    # with delay. We require at least a 10x ratio.
    @test v_sparse / v_inline > 10.0
end
