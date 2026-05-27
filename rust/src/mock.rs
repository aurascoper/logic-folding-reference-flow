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
