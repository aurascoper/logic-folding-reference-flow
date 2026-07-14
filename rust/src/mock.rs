//! Mock path generation for stress-testing the abbreviated Rust Eq. 2 engine.
//!
//! These are deliberately synthetic path ensembles. They are useful for asking
//! whether the break-even window survives plausible parasitic sweeps, not for
//! claiming that any real folded design exists.

use rand::Rng;

use crate::PathInput;

/// Generate a bimodal local/global mock-path ensemble.
///
/// Rationale: memo §7 asks whether folding is a standard-cell-level scaling law
/// or only a global-wire floorplanning trick. A bimodal distribution exposes
/// that distinction directly: most paths are short local paths with low Δτ_save,
/// while a small right-tail population is capped at 5 ps to represent plausible
/// reclaimed global-wire delay without recreating the earlier unphysical sweep.
pub fn generate_mock_paths<R: Rng + ?Sized>(n: usize, rng: &mut R) -> Vec<PathInput> {
    (0..n)
        .map(|_| {
            let global = rng.gen_bool(0.08);
            let horizontal_savings_fs = if global {
                rng.gen_range(800.0..=5_000.0)
            } else {
                rng.gen_range(5.0..=250.0)
            };
            let n_vertical_vias = if global { rng.gen_range(1..=3) } else { 1 };
            let n_bond_contacts = if global { rng.gen_range(0..=2) } else { rng.gen_range(0..=1) };
            PathInput { horizontal_savings_fs, n_vertical_vias, n_bond_contacts }
        })
        .collect()
}

/// Generate a mock-path ensemble calibrated to Huawei's **claimed** Kirin 2026
/// operating point.
///
/// **WARNING: Claimed by Huawei, not independently verified.** The V2 paper
/// (He Tingbo, July 3, 2026) discloses a 3.1 GHz peak clock and 238 MTr/mm²
/// density. These are vendor self-reported numbers, not teardown measurements.
/// This function uses the claimed frequency to set the clock-period context
/// for the path savings distribution; the parasitic tax is still swept because
/// Huawei has not disclosed via/bond RC values (Trigger B has not fired).
///
/// The path distribution shape remains the same bimodal local/global split as
/// `generate_mock_paths` — the claimed data only shifts the scale of the
/// global path savings to match the 322.6 ps clock period at 3.1 GHz.
pub fn generate_kirin_2026_claimed_paths<R: Rng + ?Sized>(n: usize, rng: &mut R) -> Vec<PathInput> {
    // Claimed frequency: 3.1 GHz → clock period ≈ 322.6 ps.
    // Global paths in a 3.1 GHz design might reclaim up to ~30% of the clock
    // period in horizontal delay ≈ ~100 ps ≈ 100,000 fs. We cap at 50,000 fs
    // (50 ps) as a conservative upper bound on foldable savings — most global
    // paths reclaim much less.
    let max_global_savings_fs = 50_000.0_f64;
    (0..n)
        .map(|_| {
            let global = rng.gen_bool(0.08);
            let horizontal_savings_fs = if global {
                rng.gen_range(800.0..=max_global_savings_fs)
            } else {
                rng.gen_range(5.0..=250.0)
            };
            let n_vertical_vias = if global { rng.gen_range(1..=3) } else { 1 };
            let n_bond_contacts = if global { rng.gen_range(0..=2) } else { rng.gen_range(0..=1) };
            PathInput { horizontal_savings_fs, n_vertical_vias, n_bond_contacts }
        })
        .collect()
}
