//! Integration tests verifying that, as vertical parasitic bounds scale up,
//! the LogicFolding execution window collapses to zero pass-rate.
//!
//! These match the user's Rust task spec acceptance criterion:
//! "verifying that when vertical parasitic bounds scale up, the execution
//! window collapses to zero".

use logic_folding_core::{DecisionLabel, PathEvaluator, PathInput, ProcessParameters};

/// Realistic-ish primitives. Numbers are illustrative; memo §7 forbids
/// treating arbitrary RC targets as credible without measurement.
fn baseline() -> ProcessParameters {
    ProcessParameters {
        r_v: 10.0,
        c_v: 0.5e-15,
        r_b: 8.0,
        c_b: 0.4e-15,
        r_drv: 200.0,
        c_load: 5.0e-15,
        dtau_red_fs: 20.0,
        dtau_thermal_fs: 15.0,
        parasitic_noise_floor_fs: 0.0, // strict gate for tests
    }
}

fn deterministic_paths(n: usize) -> Vec<PathInput> {
    // Deterministic mock path generator for tests. Linear sweep of Δτ_save
    // across a *physically plausible* range — horizontal wire delays in real
    // designs span roughly 10 fs (short local) to a few ps (long global).
    // We sweep [0, 5000 fs] = [0, 5 ps] which envelopes the realistic regime
    // without inflating into "infinite-length wire" territory that would
    // mask the parasitic-dominance effect the memo warns about.
    let max_savings_fs = 5_000.0_f64;
    (0..n)
        .map(|i| PathInput {
            horizontal_savings_fs: (i as f64) * max_savings_fs / (n as f64),
            n_vertical_vias: 2,
            n_bond_contacts: 1,
        })
        .collect()
}

#[test]
fn zero_savings_path_always_fails() {
    let ev = PathEvaluator::new(baseline());
    let r = ev.evaluate(&PathInput {
        horizontal_savings_fs: 0.0,
        n_vertical_vias: 1,
        n_bond_contacts: 1,
    });
    assert_eq!(r.label, DecisionLabel::Fail);
    assert!(r.margin_fs < 0.0);
}

#[test]
fn parallel_evaluation_matches_serial() {
    let ev = PathEvaluator::new(baseline());
    let paths = deterministic_paths(10_000);
    let serial: Vec<_> = paths.iter().map(|p| ev.evaluate(p).margin_fs).collect();
    let parallel: Vec<_> = ev
        .evaluate_parallel(&paths)
        .into_iter()
        .map(|r| r.margin_fs)
        .collect();
    assert_eq!(serial, parallel);
}

#[test]
fn hundred_thousand_paths_evaluate_without_panic() {
    let ev = PathEvaluator::new(baseline());
    let paths = deterministic_paths(100_000);
    let (pass, fail, marginal) = ev.tally_parallel(&paths);
    assert_eq!(pass + fail + marginal, 100_000);
}

/// Memo §7: "If only very long global paths pass, the approach may be a
/// niche floorplanning technique, not a standard-cell-level scaling law."
///
/// Demonstrate this directly: scale up R_v and the pass count collapses,
/// even though the path Δτ_save distribution is unchanged.
#[test]
fn execution_window_collapses_as_via_resistance_scales_up() {
    let paths = deterministic_paths(100_000);
    let mut prior_pass_count: u64 = u64::MAX;
    // Sweep R_v across three decades; pass count must be monotonically
    // non-increasing.
    for scale in [1.0_f64, 10.0, 100.0, 1000.0, 10_000.0] {
        let mut p = baseline();
        p.r_v *= scale;
        p.r_b *= scale;
        let ev = PathEvaluator::new(p);
        let (pass, _fail, _marginal) = ev.tally_parallel(&paths);
        assert!(
            pass <= prior_pass_count,
            "pass count rose from {prior_pass_count} to {pass} as parasitics scaled to {scale}x; \
             must be monotone non-increasing"
        );
        prior_pass_count = pass;
    }
    // After the final 1000x scale-up, the window must be empty.
    assert_eq!(prior_pass_count, 0, "execution window did not collapse to zero");
}

#[test]
fn execution_window_collapses_as_via_capacitance_scales_up() {
    let paths = deterministic_paths(100_000);
    let mut prior_pass_count: u64 = u64::MAX;
    for scale in [1.0_f64, 10.0, 100.0, 1000.0, 10_000.0] {
        let mut p = baseline();
        p.c_v *= scale;
        p.c_b *= scale;
        let ev = PathEvaluator::new(p);
        let (pass, _, _) = ev.tally_parallel(&paths);
        assert!(pass <= prior_pass_count);
        prior_pass_count = pass;
    }
    assert_eq!(prior_pass_count, 0);
}

#[test]
fn thermal_derating_squeezes_window() {
    let paths = deterministic_paths(100_000);
    let mut prior_pass_count: u64 = u64::MAX;
    for dtau_t in [0.0_f64, 100.0, 500.0, 2000.0, 10_000.0] {
        let mut p = baseline();
        p.dtau_thermal_fs = dtau_t;
        let ev = PathEvaluator::new(p);
        let (pass, _, _) = ev.tally_parallel(&paths);
        assert!(pass <= prior_pass_count);
        prior_pass_count = pass;
    }
    assert_eq!(prior_pass_count, 0);
}

#[test]
fn marginal_label_appears_only_when_noise_floor_nonzero() {
    let paths = deterministic_paths(1_000);
    let strict = PathEvaluator::new(baseline());
    let (_, _, marginal_strict) = strict.tally_parallel(&paths);
    assert_eq!(marginal_strict, 0);

    let mut p = baseline();
    p.parasitic_noise_floor_fs = 500.0;
    let noisy = PathEvaluator::new(p);
    let (_, _, marginal_noisy) = noisy.tally_parallel(&paths);
    assert!(marginal_noisy > 0);
}
